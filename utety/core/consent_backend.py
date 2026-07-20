"""utety/core/consent_backend.py — UTETY's SQLite backend for the shared
subject_consent core.

This is UTETY's half of the guardian-consent adoption. The consent + disclosure
*logic* (statuses, the hash chain, the tail-truncation anchor, de-identify-or-
refuse) lives once in the shared, stdlib-only ``utety.subject_consent`` core
(vendored from safe-app-store/libs/subject-consent — the primitive UTETY itself
was the reference for). This module is the ``Backend`` that lands those chains in
UTETY's on-device SQLite store, *beside the learner*, so a child's consent record
is one file, backed up and audited as a unit — the thing a filesystem backend
can't give and the reason the core was made storage-pluggable.

ATOMICITY. The file backend appends a row then writes the anchor as two separate,
non-atomic writes (a crash between them fails closed, but wedges the chain). Here
the pair is ONE SQLite transaction: ``append_row`` inserts without committing and
``write_anchor`` commits, so a row and its anchor land together or not at all. The
core always calls the two in that order inside one ``_append``; this backend
relies on exactly that contract.

Stdlib only (``sqlite3`` + ``json``): it holds the same no-egress, on-device line
as the rest of ``utety/core`` and passes tests/test_boundaries.py unchanged.
"""
from __future__ import annotations

import json
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sc_chain (
    chain TEXT NOT NULL,
    seq   INTEGER NOT NULL,
    row   TEXT NOT NULL,          -- the core's hash-chained row, verbatim JSON
    PRIMARY KEY (chain, seq)
);
CREATE TABLE IF NOT EXISTS sc_anchor (
    chain TEXT PRIMARY KEY,
    hash  TEXT NOT NULL,
    count INTEGER NOT NULL
);
"""


class SqliteBackend:
    """A subject_consent Backend over a sqlite3 connection.

    Pass an existing connection (UTETY's Store shares its own, so consent lands in
    the same on-device DB as the learner) or a path/':memory:'. The four Backend
    methods — read_rows / append_row / read_anchor / write_anchor — map each
    logical chain (``"consent"`` or ``"disclosure/<hash>"``) onto rows keyed by
    (chain, seq); the core supplies the chain names and the already-hashed rows.
    """

    def __init__(self, conn: sqlite3.Connection | str = ":memory:") -> None:
        self._conn = sqlite3.connect(conn) if isinstance(conn, str) else conn
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ── Backend protocol ────────────────────────────────────────────────────
    def read_rows(self, chain: str) -> list[dict] | None:
        cur = self._conn.execute(
            "SELECT row FROM sc_chain WHERE chain = ? ORDER BY seq", (chain,)
        )
        rows = [json.loads(r[0]) for r in cur.fetchall()]
        return rows or None  # None == "chain absent", distinct from [] for the core

    def append_row(self, chain: str, row: dict) -> None:
        # No commit here: the anchor write commits the pair as one transaction.
        nxt = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM sc_chain WHERE chain = ?", (chain,)
        ).fetchone()[0]
        self._conn.execute(
            "INSERT INTO sc_chain(chain, seq, row) VALUES(?, ?, ?)",
            (chain, nxt, json.dumps(row, sort_keys=True)),
        )

    def read_anchor(self, chain: str) -> dict | None:
        row = self._conn.execute(
            "SELECT hash, count FROM sc_anchor WHERE chain = ?", (chain,)
        ).fetchone()
        return {"hash": row[0], "count": row[1]} if row else None

    def write_anchor(self, chain: str, anchor: dict) -> None:
        self._conn.execute(
            "INSERT INTO sc_anchor(chain, hash, count) VALUES(?, ?, ?) "
            "ON CONFLICT(chain) DO UPDATE SET hash = excluded.hash, count = excluded.count",
            (chain, anchor["hash"], int(anchor["count"])),
        )
        self._conn.commit()  # commits this write AND the preceding append_row
