#!/usr/bin/env python3
"""Fail-closed consent gate (box audit B7 / A1 / A2).

Before this, utety's consent chain was dead-wired: a guardian's revoke() had zero
runtime effect, and a child could be driven through lessons with consent still
'pending'. The runtime now gates on the single authoritative subject_consent
chain, fail-closed: no verified grant → no session, no recorded outcome.
"""
import unittest

from utety.content.courses import build_neva_and_theo
from utety.content.register import register_course
from utety.core.loop import LessonSession
from utety.core.store import ConsentError, Store, StoreError
from utety.web.server import App


def _store_with_course():
    store = Store(":memory:")
    course = build_neva_and_theo()
    register_course(store, course)
    store.add_learner("kid1", "Theo")            # deliberately NOT consented
    return store, course


class TestRuntimeGate(unittest.TestCase):
    def test_session_refused_without_consent(self):
        store, course = _store_with_course()
        with self.assertRaises(ConsentError):
            LessonSession(store, course, "kid1")

    def test_outcome_refused_without_consent(self):
        store, _ = _store_with_course()
        store.add_skill("sci.3-5.forces", "science", "Forces")
        with self.assertRaises(ConsentError):
            store.record_outcome("kid1", "sci.3-5.forces", correct=True)

    def test_session_opens_after_grant(self):
        store, course = _store_with_course()
        store.grant_consent("kid1", "parent:sean")
        sess = LessonSession(store, course, "kid1")     # no raise
        self.assertIsNotNone(sess.next_step())

    def test_revoke_has_runtime_effect(self):
        # A1: the whole finding — a guardian's revoke must actually deny.
        store, course = _store_with_course()
        store.grant_consent("kid1", "parent:sean")
        self.assertTrue(store.consent_permitted("kid1"))
        store.revoke_consent("kid1", "parent:sean")
        self.assertFalse(store.consent_permitted("kid1"))
        with self.assertRaises(ConsentError):
            LessonSession(store, course, "kid1")


class TestConsolidation(unittest.TestCase):
    def test_chain_is_authoritative_and_mirror_agrees(self):
        # A2: one source of truth. The flat learners.consent_status column is a
        # derived mirror of the chain, written from the same call — they agree.
        store, _ = _store_with_course()
        self.assertEqual(store.get_learner("kid1")["consent_status"], "pending")
        self.assertFalse(store.consent_permitted("kid1"))

        store.grant_consent("kid1", "parent:sean")
        self.assertEqual(store.get_learner("kid1")["consent_status"], "granted")
        self.assertTrue(store.consent_permitted("kid1"))

        store.revoke_consent("kid1", "parent:sean")
        self.assertEqual(store.get_learner("kid1")["consent_status"], "revoked")
        self.assertFalse(store.consent_permitted("kid1"))

    def test_set_consent_shim_routes_to_the_chain(self):
        store, _ = _store_with_course()
        store.set_consent("kid1", "granted", granted_by="parent:sean")
        self.assertTrue(store.consent_permitted("kid1"))     # landed on the chain
        with self.assertRaises(StoreError):                  # pending is not settable
            store.set_consent("kid1", "pending")

    def test_consent_survives_reopen(self):
        import os
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".utety.db")
        os.close(fd)
        try:
            with Store(path) as s:
                s.add_learner("kid1", "Theo")
                s.grant_consent("kid1", "parent:sean")
            with Store(path) as s2:                          # chain persisted in-DB
                self.assertTrue(s2.consent_permitted("kid1"))
        finally:
            os.unlink(path)


class TestWebGate(unittest.TestCase):
    def _post(self, app, path, params):
        return app.handle("POST", path, params, "", {"X-Utety-Csrf": app.csrf})

    def test_unconsented_learner_gets_consent_required_not_a_lesson(self):
        app = App(Store(":memory:"), build_neva_and_theo())
        status, _, html = self._post(app, "/step", {"learner": ["kid1"]})
        self.assertEqual(status, 403)
        self.assertIn("grown-up", html)
        # fail-closed: no outcome, and the auto-provisioned learner is not served
        self.assertFalse(app.store.consent_permitted("kid1"))


if __name__ == "__main__":
    unittest.main()
