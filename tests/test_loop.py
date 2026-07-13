#!/usr/bin/env python3
"""Tests for utety/core/loop.py — the core learning loop."""
import unittest

from utety.content.courses import build_neva_and_theo
from utety.content.register import register_course
from utety.core.loop import LessonSession, NOVICE_THRESHOLD
from utety.core.store import Store


def _fresh():
    """A store with the course registered and one learner, plus the course."""
    store = Store(":memory:")
    course = build_neva_and_theo()
    register_course(store, course)
    store.add_learner("kid1", "Theo")
    return store, course


class TestConstruction(unittest.TestCase):
    def test_unknown_learner_rejected(self):
        store, course = _fresh()
        with self.assertRaises(ValueError):
            LessonSession(store, course, "ghost")

    def test_unregistered_skill_rejected(self):
        store = Store(":memory:")
        course = build_neva_and_theo()          # skills NOT registered
        store.add_learner("kid1", "Theo")
        with self.assertRaises(ValueError):
            LessonSession(store, course, "kid1")


class TestGating(unittest.TestCase):
    def setUp(self):
        self.store, self.course = _fresh()
        self.sess = LessonSession(self.store, self.course, "kid1")

    def test_first_step_is_an_experience(self):
        step = self.sess.next_step()
        self.assertEqual(step.kind, "experience")
        self.assertIsNotNone(step.experience)

    def test_no_item_before_its_experience(self):
        # Answering a gated item before acknowledging its experiment is refused.
        with self.assertRaises(ValueError):
            self.sess.answer("ip1", "a")

    def test_item_flows_after_acknowledgment(self):
        step = self.sess.next_step()
        self.sess.acknowledge_experience(step.experience.id)
        step2 = self.sess.next_step()
        self.assertEqual(step2.kind, "item")
        self.assertIsNotNone(step2.present)
        self.assertTrue(step2.present.answer_hidden)

    def test_acknowledge_unknown_experience_rejected(self):
        with self.assertRaises(ValueError):
            self.sess.acknowledge_experience("exp.ghost")


class TestPersistenceOfAcknowledgment(unittest.TestCase):
    def test_acknowledgment_survives_new_session(self):
        store, course = _fresh()
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")
        # A brand-new session over the same store must remember the gate is done.
        sess2 = LessonSession(store, course, "kid1")
        step = sess2.next_step()
        # exp.ramp is done, so the ramp skill should now offer an item (not the
        # ramp experience again).
        self.assertFalse(step.kind == "experience" and step.experience.id == "exp.ramp")


class TestPresentationScaffold(unittest.TestCase):
    def setUp(self):
        self.store, self.course = _fresh()
        self.sess = LessonSession(self.store, self.course, "kid1")
        self.ip3 = next(i for i in self.course.items if i.id == "ip3")  # has a scaffold

    def test_novice_sees_scaffold(self):
        pres = self.sess._present(self.ip3, "sci.3-5.inclined-plane")
        self.assertIsNotNone(pres.scaffold)

    def test_competent_learner_scaffold_faded(self):
        # Drive mastery above the novice threshold, then the scaffold hides.
        self.sess.acknowledge_experience("exp.ramp")
        for _ in range(10):
            self.sess.answer("ip1", "a")
        self.assertGreater(
            self.store.get_mastery("kid1", "sci.3-5.inclined-plane")["p_known"],
            NOVICE_THRESHOLD,
        )
        pres = self.sess._present(self.ip3, "sci.3-5.inclined-plane")
        self.assertIsNone(pres.scaffold)


class TestAnswerAndFeedback(unittest.TestCase):
    def setUp(self):
        self.store, self.course = _fresh()
        self.sess = LessonSession(self.store, self.course, "kid1")
        self.sess.acknowledge_experience("exp.ramp")

    def test_correct_answer_result(self):
        r = self.sess.answer("ip1", "a")
        self.assertTrue(r.correct)
        self.assertGreater(r.mastery, 0.25)
        self.assertTrue(r.citation)
        self.assertTrue(r.source_query)

    def test_wrong_answer_gets_task_focused_feedback(self):
        r = self.sess.answer("ip1", "b")
        self.assertFalse(r.correct)
        self.assertIn("push", r.feedback.lower())   # about the work, not the learner

    def test_answer_advances_bkt(self):
        before = self.store.get_mastery("kid1", "sci.3-5.inclined-plane")
        self.assertIsNone(before)
        self.sess.answer("ip1", "a")
        after = self.store.get_mastery("kid1", "sci.3-5.inclined-plane")
        self.assertEqual(after["opportunities"], 1)


class TestNoFalseComplete(unittest.TestCase):
    def test_blocked_skill_falls_through_to_next_instead_of_completing(self):
        # Audit A5: if the preferred skill has nothing selectable right now
        # (its items gated on ANOTHER skill's experience), the loop used to
        # report "complete" while unmastered work remained. It must fall
        # through and surface the gate instead.
        from utety.content.model import Course, Experience, Item, Skill

        sk_a = Skill("s.a", "science", "A")
        sk_b = Skill("s.b", "science", "B", bkt={"prior": 0.1, "learn": 0.15,
                                                 "guess": 0.25, "slip": 0.1,
                                                 "forget": 0.0})
        exp_a = Experience("exp.a", ["s.a"], "do A", "hands first")
        course = Course(
            "c", "t", "3-5", "science",
            skills=[sk_a, sk_b],
            experiences=[exp_a],
            items=[
                Item("ia", "s.a", "single", "?", answer="a",
                     choices={"a": "A"}, requires_experience="exp.a"),
                # B's item is gated on A's experience: B is preferred (lower
                # prior) but has nothing selectable until exp.a is done.
                Item("ib", "s.b", "single", "?", answer="a",
                     choices={"a": "A"}, requires_experience="exp.a"),
            ],
        )
        store = Store(":memory:")
        register_course(store, course)
        store.add_learner("kid1", "Theo")
        sess = LessonSession(store, course, "kid1")

        step = sess.next_step()
        self.assertEqual(step.kind, "experience",
                         "loop must surface the blocking gate, not complete")
        self.assertEqual(step.experience.id, "exp.a")
        self.assertFalse(sess.is_complete())


class TestMalformedResponse(unittest.TestCase):
    def test_garbage_boolean_response_records_no_outcome(self):
        # Audit A2 at loop level: a malformed response must raise BEFORE any
        # outcome is recorded — never feed noise into the mastery signal.
        store, course = _fresh()
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")
        with self.assertRaises(ValueError):
            sess.answer("ip2", "banana")
        self.assertEqual(
            store.outcome_history("kid1", "sci.3-5.inclined-plane"), [],
            "malformed response must not create a practice opportunity",
        )


class TestDisclosure(unittest.TestCase):
    def test_answers_and_acks_are_logged_and_chained(self):
        store, course = _fresh()
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")
        sess.answer("ip1", "a")
        sess.answer("ip2", "false")
        log = store.disclosure_log("kid1")
        kinds = [row["kind"] for row in log]
        self.assertIn("experience_acknowledged", kinds)
        self.assertEqual(kinds.count("item_answered"), 2)
        self.assertTrue(store.verify_disclosure_chain())

    def test_answer_disclosure_carries_citation(self):
        store, course = _fresh()
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")
        sess.answer("ip1", "a")
        answered = [r for r in store.disclosure_log("kid1") if r["kind"] == "item_answered"]
        self.assertTrue(answered[0]["citation"])


class TestFullPlaythrough(unittest.TestCase):
    def test_answering_correctly_reaches_completion(self):
        store, course = _fresh()
        sess = LessonSession(store, course, "kid1")
        answers = {"ip1": "a", "ip2": False, "ip3": "a",
                   "lf1": {"arm", "fulcrum", "load"}, "lf2": "a", "lf3": "a"}

        steps = 0
        while steps < 300:
            step = sess.next_step()
            if step.kind == "complete":
                break
            if step.kind == "experience":
                sess.acknowledge_experience(step.experience.id)
            else:
                sess.answer(step.item.id, answers[step.item.id])
            steps += 1

        self.assertTrue(sess.is_complete(), "loop never reached mastery on both skills")
        prog = sess.progress()
        self.assertTrue(prog["sci.3-5.inclined-plane"]["mastered"])
        self.assertTrue(prog["sci.3-5.lever-fulcrum"]["mastered"])

    def test_both_skills_get_practised_interleaved(self):
        # After both gates are open, practice should touch both skills, not block
        # one entirely before the other.
        store, course = _fresh()
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")
        sess.acknowledge_experience("exp.lever")
        answers = {"ip1": "a", "ip2": False, "ip3": "a",
                   "lf1": {"arm", "fulcrum", "load"}, "lf2": "a", "lf3": "a"}
        seen_skills = set()
        for _ in range(6):
            step = sess.next_step()
            if step.kind != "item":
                break
            seen_skills.add(step.item.skill_id)
            sess.answer(step.item.id, answers[step.item.id])
        self.assertEqual(seen_skills,
                         {"sci.3-5.inclined-plane", "sci.3-5.lever-fulcrum"})


if __name__ == "__main__":
    unittest.main()
