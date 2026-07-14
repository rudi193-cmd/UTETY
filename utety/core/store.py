#!/usr/bin/env python3
"""utety/core/store.py — the local-first, on-device student-data store.

Build-plan §4, Phase 0, item 3. This is the store that owns the learner:
learner profile, per-skill BKT mastery state, the append-only outcome log
(the ground-truth opportunity sequence BKT traces over), and a hash-chained
local disclosure log ("what the tutor discussed with your child").

NON-NEGOTIABLE — Ground rule 3 (local-first by default): student data stays
on-device unless an optional, consented sync is *explicitly* enabled later.
This module enforces that STRUCTURALLY, not by policy: it imports no
networking library (no urllib, socket, http, requests, ...) and no process/
FFI escape hatch (subprocess, ctypes), and the boundary tests enforce exactly
that (tests/test_no_egress.py for this package; tests/test_boundaries.py
repo-wide). The consented-sync spine, when it is built, will be a *separate*
module that reads from this one — never a capability of the store itself.

Everything is stdlib. No numpy/pandas/ORM — Termux/Windows parity, and small
enough to audit in one sitting.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from .mastery import BKTParams, mastered, update

SCHEMA_VERSION = 1
_GENESIS_HASH = "0" * 64

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- The learner. Lives here, on the device, and nowhere else by default.
CREATE TABLE IF NOT EXISTS learners (
    id             TEXT PRIMARY KEY,
    display_name   TEXT NOT NULL,
    birth_year     INTEGER,              -- age-gate input (build-plan rule 4); Phase 2 enforces
    consent_status TEXT NOT NULL DEFAULT 'pending',  -- pending | granted | revoked
    consent_by     TEXT,                 -- who granted verifiable parental consent
    consent_at     REAL,
    created_at     REAL NOT NULL
);

-- A STEM skill and its BKT parameters (fitted upstream or neutral defaults).
CREATE TABLE IF NOT EXISTS skills (
    id       TEXT PRIMARY KEY,
    subject  TEXT NOT NULL,
    name     TEXT NOT NULL,
    standard TEXT,                       -- NGSS / CCSS citation
    prior    REAL NOT NULL,
    learn    REAL NOT NULL,
    guess    REAL NOT NULL,
    slip     REAL NOT NULL,
    forget   REAL NOT NULL DEFAULT 0.0
);

-- Running BKT mastery state, one row per (learner, skill).
CREATE TABLE IF NOT EXISTS mastery (
    learner_id    TEXT NOT NULL REFERENCES learners(id),
    skill_id      TEXT NOT NULL REFERENCES skills(id),
    p_known       REAL NOT NULL,
    opportunities INTEGER NOT NULL DEFAULT 0,
    updated_at    REAL NOT NULL,
    PRIMARY KEY (learner_id, skill_id)
);

-- Append-only ground truth: one row per practice opportunity.
CREATE TABLE IF NOT EXISTS outcomes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id  TEXT NOT NULL REFERENCES learners(id),
    skill_id    TEXT NOT NULL REFERENCES skills(id),
    item_id     TEXT,
    correct     INTEGER NOT NULL,        -- 0 | 1
    response_ms INTEGER,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outcomes_learner_skill
    ON outcomes(learner_id, skill_id, id);

-- Hash-chained local disclosure log: tamper-evident, on-device, per device.
CREATE TABLE IF NOT EXISTS disclosure (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL REFERENCES learners(id),
    kind       TEXT NOT NULL,            -- item_presented | feedback_given | source_cited | ...
    payload    TEXT NOT NULL,            -- JSON
    citation   TEXT,                     -- inspectable source (build-plan rule 1)
    created_at REAL NOT NULL,
    prev_hash  TEXT NOT NULL,
    hash       TEXT NOT NULL
);
"""


class StoreError(RuntimeError):
    """Raised on invariant violations (unknown learner/skill, tamper, ...)."""


def _now() -> float:
    return time.time()


def _chain_hash(seq: int, learner_id: str, kind: str, payload: str,
                citation: str | None, created_at: float, prev_hash: str) -> str:
    """Deterministic sha256 over a disclosure row's content + the previous hash."""
    blob = json.dumps(
        {
            "seq": seq,
            "learner_id": learner_id,
            "kind": kind,
            "payload": payload,
            "citation": citation,
            "created_at": created_at,
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class Store:
    """A local-first SQLite student-data store.

    Open with a filesystem path (a child's device holds one file) or
    ``":memory:"`` for tests. Usable as a context manager.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self._tx_depth = 0
        # check_same_thread stays True (default): one device, one owner.
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)
        self._db.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._db.commit()
        # Refuse a store written by a NEWER schema: proceeding blindly could
        # corrupt a child's data. Older versions migrate here when migrations
        # exist (audit 2026-07-13, B6).
        found = int(self._db.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()["value"])
        if found > SCHEMA_VERSION:
            self._db.close()
            raise StoreError(
                f"store schema v{found} is newer than this code (v{SCHEMA_VERSION}) "
                "— update UTETY before opening this store"
            )

    # ── transactions ───────────────────────────────────────────────────────
    @contextlib.contextmanager
    def transaction(self):
        """Make a group of writes atomic: all land or none do.

        Every writing method on this store runs inside one of these, so a
        sqlite failure mid-method (disk full, database locked) can never leave
        a partial write pending to be flushed by a later unrelated commit
        (independent audit 2026-07-14, F1). Nested uses join the outermost
        transaction — commit/rollback happen only at depth zero — so callers
        can compose semantically paired writes (an outcome and its disclosure
        row; a consent flip and its chain entry) into one atomic unit (F5).

        Caution: a nested block is NOT independently atomic (no SAVEPOINTs) —
        do not catch an inner block's exception and continue writing in the
        outer transaction, or the inner block's partial writes will commit
        with it (final-loop audit 2026-07-14, S3).
        """
        if self._tx_depth == 0:
            self._db.execute("BEGIN IMMEDIATE")
        self._tx_depth += 1
        try:
            yield
        except BaseException:
            self._tx_depth -= 1
            if self._tx_depth == 0:
                # A failing rollback must not mask the original error (S2);
                # the handle is torn either way, and the cause matters more.
                with contextlib.suppress(Exception):
                    self._db.rollback()
            raise
        else:
            self._tx_depth -= 1
            if self._tx_depth == 0:
                try:
                    self._db.commit()
                except BaseException:
                    # Commit is where pages flush, so disk-full strikes HERE.
                    # Roll back so the transaction isn't left open — otherwise
                    # this handle can never write again ("cannot start a
                    # transaction within a transaction") and reads would see
                    # uncommitted rows until close() (final-loop audit, S1).
                    with contextlib.suppress(Exception):
                        self._db.rollback()
                    raise

    # ── lifecycle ──────────────────────────────────────────────────────────
    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── learners ───────────────────────────────────────────────────────────
    def add_learner(self, learner_id: str, display_name: str,
                    birth_year: int | None = None) -> None:
        try:
            with self.transaction():
                self._db.execute(
                    "INSERT INTO learners(id, display_name, birth_year, created_at) "
                    "VALUES(?, ?, ?, ?)",
                    (learner_id, display_name, birth_year, _now()),
                )
        except sqlite3.IntegrityError as exc:
            raise StoreError(f"learner already exists: {learner_id!r}") from exc

    def get_learner(self, learner_id: str) -> dict | None:
        row = self._db.execute(
            "SELECT * FROM learners WHERE id = ?", (learner_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_learners(self) -> list[dict]:
        rows = self._db.execute(
            "SELECT * FROM learners ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    def set_consent(self, learner_id: str, status: str,
                    granted_by: str | None = None) -> None:
        """Record verifiable-parental-consent state (build-plan rule 4).

        status: 'pending' | 'granted' | 'revoked'. The store persists it; the
        Phase-2 age-gate is what *enforces* it before any child uses the tutor.

        Every transition is timestamped (revocation included — erasing *when*
        consent was withdrawn would gut the audit trail) and appended to the
        tamper-evident disclosure chain, so the consent history is inspectable
        and unforgeable after the fact (audit 2026-07-13, B2).
        """
        if status not in ("pending", "granted", "revoked"):
            raise StoreError(f"invalid consent status: {status!r}")
        if self.get_learner(learner_id) is None:
            raise StoreError(f"unknown learner: {learner_id!r}")
        # One transaction: the consent flip and its chain entry land together
        # or not at all — a crash between them must not leave an unchained
        # transition (independent audit 2026-07-14, F5).
        with self.transaction():
            self._db.execute(
                "UPDATE learners SET consent_status = ?, consent_by = ?, consent_at = ? "
                "WHERE id = ?",
                (status, granted_by, _now(), learner_id),
            )
            self.log_disclosure(
                learner_id, "consent_changed",
                payload={"status": status, "by": granted_by},
            )

    # ── skills ─────────────────────────────────────────────────────────────
    def add_skill(self, skill_id: str, subject: str, name: str,
                  standard: str | None = None,
                  params: BKTParams | None = None) -> None:
        p = params or BKTParams()
        try:
            with self.transaction():
                self._db.execute(
                    "INSERT INTO skills(id, subject, name, standard, prior, learn, guess, slip, forget) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (skill_id, subject, name, standard, p.prior, p.learn, p.guess, p.slip, p.forget),
                )
        except sqlite3.IntegrityError as exc:
            raise StoreError(f"skill already exists: {skill_id!r}") from exc

    def update_skill_params(self, skill_id: str, params: BKTParams) -> None:
        """Replace a skill's BKT parameters (content, not learner state).

        Used when upstream ships re-fitted values; mastery rows are untouched —
        the new parameters simply govern updates from here on.
        """
        if self.get_skill(skill_id) is None:
            raise StoreError(f"unknown skill: {skill_id!r}")
        with self.transaction():
            self._db.execute(
                "UPDATE skills SET prior = ?, learn = ?, guess = ?, slip = ?, forget = ? "
                "WHERE id = ?",
                (params.prior, params.learn, params.guess, params.slip, params.forget, skill_id),
            )

    def get_skill(self, skill_id: str) -> dict | None:
        row = self._db.execute(
            "SELECT * FROM skills WHERE id = ?", (skill_id,)
        ).fetchone()
        return dict(row) if row else None

    def _skill_params(self, skill_id: str) -> BKTParams:
        row = self.get_skill(skill_id)
        if row is None:
            raise StoreError(f"unknown skill: {skill_id!r}")
        return BKTParams(
            prior=row["prior"], learn=row["learn"], guess=row["guess"],
            slip=row["slip"], forget=row["forget"],
        )

    # ── outcomes + mastery ─────────────────────────────────────────────────
    def record_outcome(self, learner_id: str, skill_id: str, correct: bool,
                       item_id: str | None = None,
                       response_ms: int | None = None) -> float:
        """Append a practice opportunity and advance BKT mastery.

        Transactional: writes the append-only outcome row, loads the current
        mastery (seeding from the skill's BKT prior on the first opportunity),
        applies one BKT ``update``, and upserts the new mastery state.
        Returns the new P(mastered).
        """
        if self.get_learner(learner_id) is None:
            raise StoreError(f"unknown learner: {learner_id!r}")
        params = self._skill_params(skill_id)
        c = 1 if correct else 0
        now = _now()

        # The outcome row and the mastery upsert are a semantically paired
        # write: a failure between them (disk full, database locked) must roll
        # back BOTH, or the append-only log permanently desyncs from mastery
        # state (independent audit 2026-07-14, F1).
        try:
            with self.transaction():
                cur = self._db.execute(
                    "SELECT p_known, opportunities FROM mastery "
                    "WHERE learner_id = ? AND skill_id = ?",
                    (learner_id, skill_id),
                ).fetchone()
                p_prev = cur["p_known"] if cur else params.prior
                opps = (cur["opportunities"] if cur else 0) + 1

                p_new = update(p_prev, bool(c), params)

                self._db.execute(
                    "INSERT INTO outcomes(learner_id, skill_id, item_id, correct, response_ms, created_at) "
                    "VALUES(?, ?, ?, ?, ?, ?)",
                    (learner_id, skill_id, item_id, c, response_ms, now),
                )
                self._db.execute(
                    "INSERT INTO mastery(learner_id, skill_id, p_known, opportunities, updated_at) "
                    "VALUES(?, ?, ?, ?, ?) "
                    "ON CONFLICT(learner_id, skill_id) DO UPDATE SET "
                    "p_known = excluded.p_known, opportunities = excluded.opportunities, "
                    "updated_at = excluded.updated_at",
                    (learner_id, skill_id, p_new, opps, now),
                )
        except sqlite3.Error as exc:
            raise StoreError(
                "record_outcome failed; no partial write committed"
            ) from exc
        return p_new

    def get_mastery(self, learner_id: str, skill_id: str) -> dict | None:
        row = self._db.execute(
            "SELECT * FROM mastery WHERE learner_id = ? AND skill_id = ?",
            (learner_id, skill_id),
        ).fetchone()
        return dict(row) if row else None

    def is_mastered(self, learner_id: str, skill_id: str,
                    threshold: float = 0.95) -> bool:
        row = self.get_mastery(learner_id, skill_id)
        return bool(row) and mastered(row["p_known"], threshold)

    def mastery_state(self, learner_id: str) -> list[dict]:
        rows = self._db.execute(
            "SELECT * FROM mastery WHERE learner_id = ? ORDER BY skill_id",
            (learner_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def outcome_history(self, learner_id: str, skill_id: str) -> list[int]:
        """The ordered 0/1 opportunity sequence — what BKT/analytics trace over."""
        rows = self._db.execute(
            "SELECT correct FROM outcomes "
            "WHERE learner_id = ? AND skill_id = ? ORDER BY id",
            (learner_id, skill_id),
        ).fetchall()
        return [r["correct"] for r in rows]

    # ── disclosure log (hash-chained, on-device) ───────────────────────────
    def log_disclosure(self, learner_id: str, kind: str,
                       payload: dict | None = None,
                       citation: str | None = None) -> str:
        """Append a tamper-evident disclosure row. Returns the row's hash.

        This is the local spine for the Phase-3 human-readable disclosure view.
        Chained device-wide (one chain, filter by learner) so any edit to a
        past row is detectable by ``verify_disclosure_chain``.
        """
        if self.get_learner(learner_id) is None:
            raise StoreError(f"unknown learner: {learner_id!r}")
        payload_json = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        now = _now()
        with self.transaction():
            prev = self._db.execute(
                "SELECT hash FROM disclosure ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev["hash"] if prev else _GENESIS_HASH

            # seq is assigned by AUTOINCREMENT; reserve it explicitly so the
            # hash can bind to it deterministically.
            next_seq = self._db.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM disclosure"
            ).fetchone()["n"]
            row_hash = _chain_hash(
                next_seq, learner_id, kind, payload_json, citation, now, prev_hash
            )
            self._db.execute(
                "INSERT INTO disclosure(seq, learner_id, kind, payload, citation, created_at, prev_hash, hash) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (next_seq, learner_id, kind, payload_json, citation, now, prev_hash, row_hash),
            )
            # Anchor the head: an edit or mid-chain delete breaks the hash
            # links, but deleting the NEWEST rows would otherwise leave a chain
            # that still verifies. Persisting head+count on every append makes
            # truncation detectable too (audit 2026-07-13, B4).
            self._db.execute(
                "INSERT INTO meta(key, value) VALUES('disclosure_head', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (json.dumps({"hash": row_hash, "count": next_seq}),),
            )
        return row_hash

    def disclosure_log(self, learner_id: str | None = None) -> list[dict]:
        """Return disclosure rows (all, or for one learner), payload decoded."""
        if learner_id is None:
            rows = self._db.execute(
                "SELECT * FROM disclosure ORDER BY seq"
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM disclosure WHERE learner_id = ? ORDER BY seq",
                (learner_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"])
            out.append(d)
        return out

    def verify_disclosure_chain(self) -> bool:
        """Recompute the device-wide hash chain; True iff intact.

        Checks both directions of tamper: rewritten/deleted middle rows (the
        hash links break) and deleted tail rows (the last row no longer matches
        the anchored head in ``meta``).
        """
        rows = self._db.execute(
            "SELECT seq, learner_id, kind, payload, citation, created_at, prev_hash, hash "
            "FROM disclosure ORDER BY seq"
        ).fetchall()
        prev_hash = _GENESIS_HASH
        for r in rows:
            if r["prev_hash"] != prev_hash:
                return False
            expect = _chain_hash(
                r["seq"], r["learner_id"], r["kind"], r["payload"],
                r["citation"], r["created_at"], r["prev_hash"],
            )
            if expect != r["hash"]:
                return False
            prev_hash = r["hash"]
        anchor_row = self._db.execute(
            "SELECT value FROM meta WHERE key = 'disclosure_head'"
        ).fetchone()
        if not rows:
            return anchor_row is None
        if anchor_row is None:
            return False
        anchor = json.loads(anchor_row["value"])
        return anchor["hash"] == rows[-1]["hash"] and anchor["count"] == rows[-1]["seq"]


def skill_params_dict(params: BKTParams) -> dict:
    """Convenience: BKTParams -> plain dict (e.g. for shipping skill defs)."""
    return asdict(params)
