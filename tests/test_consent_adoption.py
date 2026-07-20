"""tests/test_consent_adoption.py — UTETY consumes the shared subject_consent core.

Guardian-consent adoption: instead of a private consent/disclosure implementation,
UTETY vendors the shared stdlib-only core (the primitive it was the reference for)
and plugs its own SQLite backend. These tests prove the shared core runs correctly
over UTETY's SQLite storage — the full lifecycle, the tail-truncation anchor
(UTETY's own audit-B4 guard, now shared), and the transactional atomicity a
filesystem backend can't offer. unittest, matching the rest of tests/.
"""
import sqlite3
import unittest

from utety.core.consent_backend import SqliteBackend
from utety.subject_consent import (
    ChainTamperError,
    grant,
    permitted,
    read_disclosures,
    record_disclosure,
    revoke,
    verify_consent_chain,
)
from utety.subject_consent.core import Backend


def _backend() -> SqliteBackend:
    return SqliteBackend(":memory:")


class TestConsentAdoption(unittest.TestCase):
    # ── the backend satisfies the shared protocol ─────────────────────────────
    def test_sqlite_backend_is_a_backend(self):
        self.assertIsInstance(_backend(), Backend)

    # ── the shared lifecycle, over UTETY's SQLite ─────────────────────────────
    def test_consent_lifecycle_over_sqlite(self):
        b = _backend()
        self.assertFalse(permitted(b, "learner-1", "process_analysis"))  # absent → deny
        grant(b, "learner-1", "process_analysis", "parent")
        self.assertTrue(permitted(b, "learner-1", "process_analysis"))
        revoke(b, "learner-1", "process_analysis", "parent")
        self.assertFalse(permitted(b, "learner-1", "process_analysis"))  # revoked → deny
        grant(b, "learner-1", "process_analysis", "parent")              # re-grant
        self.assertTrue(permitted(b, "learner-1", "process_analysis"))
        verify_consent_chain(b)  # intact → no raise

    def test_scopes_are_independent_over_sqlite(self):
        b = _backend()
        grant(b, "learner-1", "process_analysis", "parent")
        self.assertTrue(permitted(b, "learner-1", "process_analysis"))
        self.assertFalse(permitted(b, "learner-1", "kb_promotion"))  # a different scope

    def test_disclosure_roundtrips_over_sqlite(self):
        b = _backend()
        record_disclosure(b, "learner-1", "item_presented", "fractions/3")
        record_disclosure(b, "learner-1", "feedback_given", "gentle hint")
        rows = read_disclosures(b, "learner-1")
        self.assertEqual([r["action"] for r in rows], ["item_presented", "feedback_given"])

    def test_disclosure_is_per_subject_over_sqlite(self):
        b = _backend()
        record_disclosure(b, "learner-1", "lesson", "A")
        record_disclosure(b, "learner-2", "lesson", "B")
        self.assertEqual([r["detail"] for r in read_disclosures(b, "learner-1")], ["A"])
        self.assertEqual([r["detail"] for r in read_disclosures(b, "learner-2")], ["B"])

    # ── tamper + truncation over SQLite (the audit-B4 guard, now shared) ───────
    def test_midchain_tamper_detected_over_sqlite(self):
        b = _backend()
        grant(b, "learner-1", "kb_promotion", "parent")
        # rewrite a stored row's content without fixing its hash
        b._conn.execute("UPDATE sc_chain SET row = REPLACE(row, 'granted', 'revoked')")
        b._conn.commit()
        self.assertFalse(permitted(b, "learner-1", "kb_promotion"))

    def test_truncation_detected_over_sqlite(self):
        b = _backend()
        grant(b, "learner-1", "kb_promotion", "parent")
        grant(b, "learner-1", "person_inference", "parent")
        # delete the newest consent row; the shorter chain still LINKS cleanly…
        b._conn.execute("DELETE FROM sc_chain WHERE chain='consent' AND seq=2")
        b._conn.commit()
        # …but the anchor (count/head) no longer matches → tampered, fail-closed
        self.assertFalse(permitted(b, "learner-1", "kb_promotion"))
        with self.assertRaises(ChainTamperError):
            verify_consent_chain(b)

    def test_disclosure_truncation_detected_over_sqlite(self):
        b = _backend()
        for d in ("A", "B", "C"):
            record_disclosure(b, "learner-1", "lesson", d)
        chain = b._conn.execute(
            "SELECT chain FROM sc_chain WHERE chain LIKE 'disclosure/%' LIMIT 1"
        ).fetchone()[0]
        b._conn.execute("DELETE FROM sc_chain WHERE chain=? AND seq=3", (chain,))
        b._conn.commit()
        with self.assertRaises(ChainTamperError):
            read_disclosures(b, "learner-1")

    # ── atomicity: a row and its anchor commit together (the SQLite win) ───────
    def test_append_and_anchor_are_one_transaction(self):
        conn = sqlite3.connect(":memory:")
        b = SqliteBackend(conn)
        grant(b, "learner-1", "kb_promotion", "parent")
        rows = b._conn.execute(
            "SELECT COUNT(*) FROM sc_chain WHERE chain='consent'"
        ).fetchone()[0]
        anchor = b._conn.execute(
            "SELECT count FROM sc_anchor WHERE chain='consent'"
        ).fetchone()[0]
        self.assertEqual((rows, anchor), (1, 1))

    # ── consent can share the learner's own connection (beside the learner) ────
    def test_backend_shares_a_connection_with_the_store(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE learners(id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO learners(id) VALUES('learner-1')")
        conn.commit()
        b = SqliteBackend(conn)
        grant(b, "learner-1", "local_only", "parent")
        self.assertTrue(permitted(b, "learner-1", "local_only"))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM learners").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM sc_chain").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
