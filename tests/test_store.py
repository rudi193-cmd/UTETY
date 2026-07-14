#!/usr/bin/env python3
"""Tests for utety/core/store.py — the local-first student-data store."""
import sqlite3
import unittest

from utety.core.mastery import BKTParams
from utety.core.store import Store, StoreError


class _FailingDB:
    """Connection proxy that raises on statements containing a marker —
    simulates 'disk full' / 'database is locked' mid-write."""

    def __init__(self, real, fail_on: str):
        self._real = real
        self._fail_on = fail_on

    def execute(self, sql, *args):
        if self._fail_on in sql:
            raise sqlite3.OperationalError("simulated disk I/O error")
        return self._real.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._real, name)


class TestLearners(unittest.TestCase):
    def setUp(self):
        self.s = Store(":memory:")

    def tearDown(self):
        self.s.close()

    def test_add_and_get_learner(self):
        self.s.add_learner("kid1", "Neva", birth_year=2016)
        row = self.s.get_learner("kid1")
        self.assertEqual(row["display_name"], "Neva")
        self.assertEqual(row["birth_year"], 2016)
        self.assertEqual(row["consent_status"], "pending")

    def test_consent_flow(self):
        self.s.add_learner("kid1", "Neva")
        self.s.set_consent("kid1", "granted", granted_by="parent:sean")
        row = self.s.get_learner("kid1")
        self.assertEqual(row["consent_status"], "granted")
        self.assertEqual(row["consent_by"], "parent:sean")
        self.assertIsNotNone(row["consent_at"])

    def test_invalid_consent_status_rejected(self):
        self.s.add_learner("kid1", "Neva")
        with self.assertRaises(StoreError):
            self.s.set_consent("kid1", "sure_why_not")

    def test_consent_for_unknown_learner_rejected(self):
        with self.assertRaises(StoreError):
            self.s.set_consent("ghost", "granted")

    def test_revocation_keeps_a_timestamp(self):
        # Audit B2: erasing WHEN consent was withdrawn guts the audit trail.
        self.s.add_learner("kid1", "Neva")
        self.s.set_consent("kid1", "granted", granted_by="parent:sean")
        self.s.set_consent("kid1", "revoked", granted_by="parent:sean")
        row = self.s.get_learner("kid1")
        self.assertEqual(row["consent_status"], "revoked")
        self.assertIsNotNone(row["consent_at"])

    def test_consent_transitions_enter_the_disclosure_chain(self):
        # Audit B2: consent history must be tamper-evident, not a mutable cell.
        self.s.add_learner("kid1", "Neva")
        self.s.set_consent("kid1", "granted", granted_by="parent:sean")
        self.s.set_consent("kid1", "revoked", granted_by="parent:sean")
        changes = [r for r in self.s.disclosure_log("kid1")
                   if r["kind"] == "consent_changed"]
        self.assertEqual([c["payload"]["status"] for c in changes],
                         ["granted", "revoked"])
        self.assertTrue(self.s.verify_disclosure_chain())

    def test_duplicate_learner_raises_store_error(self):
        self.s.add_learner("kid1", "Neva")
        with self.assertRaises(StoreError):
            self.s.add_learner("kid1", "Neva again")


class TestOutcomesAndMastery(unittest.TestCase):
    def setUp(self):
        self.s = Store(":memory:")
        self.s.add_learner("kid1", "Theo")
        self.s.add_skill(
            "sci.3-5.forces", "science", "Forces & Motion",
            standard="NGSS 3-PS2-1",
            params=BKTParams(prior=0.3, learn=0.15, guess=0.2, slip=0.1),
        )

    def tearDown(self):
        self.s.close()

    def test_first_outcome_seeds_from_prior(self):
        p = self.s.record_outcome("kid1", "sci.3-5.forces", correct=True)
        self.assertGreater(p, 0.3)  # correct answer raises above the prior
        m = self.s.get_mastery("kid1", "sci.3-5.forces")
        self.assertEqual(m["opportunities"], 1)
        self.assertAlmostEqual(m["p_known"], p, places=10)

    def test_mastery_climbs_with_correct_streak(self):
        last = 0.0
        for _ in range(15):
            last = self.s.record_outcome("kid1", "sci.3-5.forces", correct=True)
        self.assertTrue(self.s.is_mastered("kid1", "sci.3-5.forces"))
        self.assertGreater(last, 0.95)

    def test_outcome_history_is_ordered_sequence(self):
        for c in (True, False, True, True):
            self.s.record_outcome("kid1", "sci.3-5.forces", correct=c)
        self.assertEqual(
            self.s.outcome_history("kid1", "sci.3-5.forces"), [1, 0, 1, 1]
        )

    def test_opportunities_accumulate(self):
        for _ in range(4):
            self.s.record_outcome("kid1", "sci.3-5.forces", correct=True)
        m = self.s.get_mastery("kid1", "sci.3-5.forces")
        self.assertEqual(m["opportunities"], 4)

    def test_unknown_learner_rejected(self):
        with self.assertRaises(StoreError):
            self.s.record_outcome("ghost", "sci.3-5.forces", correct=True)

    def test_unknown_skill_rejected(self):
        with self.assertRaises(StoreError):
            self.s.record_outcome("kid1", "no.such.skill", correct=True)

    def test_mastery_state_lists_all_skills(self):
        self.s.add_skill("math.3-5.frac", "math", "Fractions", params=BKTParams())
        self.s.record_outcome("kid1", "sci.3-5.forces", correct=True)
        self.s.record_outcome("kid1", "math.3-5.frac", correct=False)
        state = self.s.mastery_state("kid1")
        self.assertEqual({r["skill_id"] for r in state},
                         {"sci.3-5.forces", "math.3-5.frac"})


class TestAtomicity(unittest.TestCase):
    """Independent audit F1/F5: paired writes land together or not at all."""

    def setUp(self):
        self.s = Store(":memory:")
        self.s.add_learner("kid1", "Neva")
        self.s.add_skill("sci.3-5.forces", "science", "Forces", params=BKTParams())

    def tearDown(self):
        self.s.close()

    def _fail_on(self, marker):
        self._real = self.s._db
        self.s._db = _FailingDB(self._real, marker)

    def _restore(self):
        self.s._db = self._real

    def test_failed_record_outcome_leaves_no_phantom_row(self):
        # F1's repro: mastery upsert fails after the outcome insert. The
        # outcome row must roll back — not linger to be flushed durable by a
        # later unrelated commit.
        self._fail_on("INSERT INTO mastery")
        with self.assertRaises(StoreError):
            self.s.record_outcome("kid1", "sci.3-5.forces", correct=True)
        self._restore()
        self.s.log_disclosure("kid1", "unrelated", payload={})  # later commit
        self.assertEqual(self.s.outcome_history("kid1", "sci.3-5.forces"), [],
                         "phantom outcome row survived a failed record_outcome")
        self.assertIsNone(self.s.get_mastery("kid1", "sci.3-5.forces"))

    def test_failed_disclosure_rolls_back_consent_flip(self):
        # F5: the consent UPDATE and its chain entry are one atomic unit.
        self._fail_on("INSERT INTO disclosure")
        with self.assertRaises(sqlite3.OperationalError):
            self.s.set_consent("kid1", "granted", granted_by="parent:sean")
        self._restore()
        row = self.s.get_learner("kid1")
        self.assertEqual(row["consent_status"], "pending",
                         "consent flipped without its disclosure entry")
        self.assertEqual(self.s.disclosure_log("kid1"), [])
        self.assertTrue(self.s.verify_disclosure_chain())

    def test_failed_disclosure_rolls_back_the_graded_answer(self):
        # F5 at loop level: an answer whose disclosure append fails must not
        # leave a graded outcome the disclosure spine never saw.
        from utety.content.courses import build_neva_and_theo
        from utety.content.register import register_course
        from utety.core.loop import LessonSession

        store = Store(":memory:")
        course = build_neva_and_theo()
        register_course(store, course)
        store.add_learner("kid1", "Theo")
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")

        real = store._db
        store._db = _FailingDB(real, "INSERT INTO disclosure")
        with self.assertRaises(sqlite3.OperationalError):
            sess.answer("ip1", "a")
        store._db = real
        self.assertEqual(
            store.outcome_history("kid1", "sci.3-5.inclined-plane"), [],
            "outcome recorded without its disclosure entry")


class TestDisclosureChain(unittest.TestCase):
    def setUp(self):
        self.s = Store(":memory:")
        self.s.add_learner("kid1", "Neva")

    def tearDown(self):
        self.s.close()

    def test_log_and_read(self):
        self.s.log_disclosure(
            "kid1", "item_presented",
            payload={"item": "why do heavier things not fall faster?"},
            citation="NGSS 3-PS2-1",
        )
        self.s.log_disclosure(
            "kid1", "source_cited", payload={"claim": "gravity acts equally"},
            citation="Galileo, Two New Sciences",
        )
        log = self.s.disclosure_log("kid1")
        self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["kind"], "item_presented")
        self.assertEqual(log[0]["payload"]["item"],
                         "why do heavier things not fall faster?")

    def test_chain_intact_by_default(self):
        for i in range(5):
            self.s.log_disclosure("kid1", "feedback_given", payload={"n": i})
        self.assertTrue(self.s.verify_disclosure_chain())

    def test_tamper_is_detected(self):
        for i in range(3):
            self.s.log_disclosure("kid1", "feedback_given", payload={"n": i})
        # Reach past the API and rewrite a payload — the chain must catch it.
        self.s._db.execute(
            "UPDATE disclosure SET payload = ? WHERE seq = 2",
            ('{"n":999}',),
        )
        self.s._db.commit()
        self.assertFalse(self.s.verify_disclosure_chain())

    def test_tail_truncation_is_detected(self):
        # Audit B4: deleting the NEWEST rows used to leave a chain that still
        # verified. The anchored head catches it now.
        for i in range(3):
            self.s.log_disclosure("kid1", "feedback_given", payload={"n": i})
        self.assertTrue(self.s.verify_disclosure_chain())
        self.s._db.execute("DELETE FROM disclosure WHERE seq = 3")
        self.s._db.commit()
        self.assertFalse(self.s.verify_disclosure_chain())

    def test_empty_chain_with_no_anchor_verifies(self):
        self.assertTrue(Store(":memory:").verify_disclosure_chain())

    def test_disclosure_requires_known_learner(self):
        with self.assertRaises(StoreError):
            self.s.log_disclosure("ghost", "item_presented")


class TestSchemaVersion(unittest.TestCase):
    def test_newer_schema_refused(self):
        # Audit B6: opening a store written by newer code must fail loudly,
        # not proceed blindly over an unknown layout.
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".utety.db")
        os.close(fd)
        try:
            s = Store(path)
            s._db.execute(
                "UPDATE meta SET value = '999' WHERE key = 'schema_version'")
            s._db.commit()
            s.close()
            with self.assertRaises(StoreError):
                Store(path)
        finally:
            os.unlink(path)


class TestPersistence(unittest.TestCase):
    def test_survives_reopen(self):
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix=".utety.db")
        os.close(fd)
        try:
            with Store(path) as s:
                s.add_learner("kid1", "Neva")
                s.add_skill("sci.3-5.forces", "science", "Forces", params=BKTParams())
                s.record_outcome("kid1", "sci.3-5.forces", correct=True)
            with Store(path) as s2:
                self.assertIsNotNone(s2.get_learner("kid1"))
                self.assertEqual(
                    s2.outcome_history("kid1", "sci.3-5.forces"), [1]
                )
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
