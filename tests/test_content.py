#!/usr/bin/env python3
"""Tests for utety/content — the course/skill/item layer."""
import unittest

from utety.content.courses import build_neva_and_theo
from utety.content.model import Course, Item, Skill
from utety.content.register import register_course
from utety.core.store import Store


class TestItemChecking(unittest.TestCase):
    def test_single_choice(self):
        it = Item("i1", "s", "single", "pick a", answer="a",
                  choices={"a": "A", "b": "B"})
        self.assertTrue(it.check("a"))
        self.assertFalse(it.check("b"))

    def test_boolean_coercion(self):
        it = Item("i2", "s", "boolean", "t/f", answer=False)
        self.assertTrue(it.check("false"))
        self.assertTrue(it.check(False))
        self.assertFalse(it.check("true"))
        self.assertFalse(it.check(1))

    def test_multi_is_order_independent(self):
        it = Item("i3", "s", "multi", "which", answer={"arm", "fulcrum", "load"})
        self.assertTrue(it.check(["load", "arm", "fulcrum"]))
        self.assertFalse(it.check(["arm", "fulcrum"]))
        self.assertFalse(it.check(["arm", "fulcrum", "load", "gravity"]))

    def test_text_normalized(self):
        it = Item("i4", "s", "text", "word", answer=["Fulcrum", "pivot"])
        self.assertTrue(it.check("  fulcrum "))
        self.assertTrue(it.check("PIVOT"))
        self.assertFalse(it.check("lever"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            Item("i5", "s", "essay", "write", answer="x")


class TestFeedback(unittest.TestCase):
    def setUp(self):
        self.it = Item(
            "i", "s", "single", "why", answer="a",
            choices={"a": "A", "b": "B"},
            feedback={"b": "look again at the ramp"},
            feedback_default="try it with your hands",
            feedback_correct="that's what your hands felt",
        )

    def test_correct_gets_correct_feedback(self):
        self.assertEqual(self.it.feedback_for("a"), "that's what your hands felt")

    def test_specific_wrong_answer_feedback(self):
        self.assertEqual(self.it.feedback_for("b"), "look again at the ramp")

    def test_falls_back_to_default(self):
        self.assertEqual(self.it.feedback_for("z"), "try it with your hands")


class TestCourseValidation(unittest.TestCase):
    def test_item_referencing_unknown_skill_rejected(self):
        with self.assertRaises(ValueError):
            Course("c", "t", "3-5", "science",
                   skills=[Skill("s1", "science", "S1")],
                   items=[Item("i", "no-skill", "single", "?", answer="a")])

    def test_item_gated_on_unknown_experience_rejected(self):
        with self.assertRaises(ValueError):
            Course("c", "t", "3-5", "science",
                   skills=[Skill("s1", "science", "S1")],
                   items=[Item("i", "s1", "single", "?", answer="a",
                               requires_experience="exp.ghost")])

    def test_duplicate_skill_id_rejected(self):
        with self.assertRaises(ValueError):
            Course("c", "t", "3-5", "science",
                   skills=[Skill("s1", "science", "A"), Skill("s1", "science", "B")])

    def test_roundtrip_dict(self):
        course = build_neva_and_theo()
        rebuilt = Course.from_dict(course.to_dict())
        self.assertEqual(rebuilt.id, course.id)
        self.assertEqual(len(rebuilt.items), len(course.items))
        self.assertEqual(rebuilt.items[0].check("a"), course.items[0].check("a"))


class TestNevaAndTheoCourse(unittest.TestCase):
    def setUp(self):
        self.course = build_neva_and_theo()

    def test_two_skills(self):
        self.assertEqual(
            {s.id for s in self.course.skills},
            {"sci.3-5.inclined-plane", "sci.3-5.lever-fulcrum"},
        )

    def test_every_item_gated_by_experience(self):
        # The lesson's whole point: hands before vocabulary. No ungated item.
        for it in self.course.items:
            self.assertIsNotNone(it.requires_experience,
                                 f"item {it.id} is not gated behind an experience")

    def test_every_item_has_a_source(self):
        # Rule 1: sourced or it doesn't teach.
        for it in self.course.items:
            self.assertTrue(it.citation, f"item {it.id} has no citation")
            self.assertTrue(it.source_query, f"item {it.id} has no source_query")

    def test_every_gate_maps_to_its_skill(self):
        for it in self.course.items:
            exps = {e.id for e in self.course.experiences_for(it.skill_id)}
            self.assertIn(it.requires_experience, exps)

    def test_known_answers_check_correct(self):
        answers = {"ip1": "a", "ip2": False, "ip3": "a",
                   "lf1": {"arm", "fulcrum", "load"}, "lf2": "a", "lf3": "a"}
        by_id = {it.id: it for it in self.course.items}
        for iid, ans in answers.items():
            self.assertTrue(by_id[iid].check(ans), f"{iid} should accept its key answer")

    def test_no_self_directed_praise(self):
        # Rule 2: feedback is about the work, never the learner. Lint the corpus.
        banned = ["you're smart", "you are smart", "so smart", "genius", "you're brilliant",
                  "good girl", "good boy", "you're gifted", "natural talent"]
        for it in self.course.items:
            blobs = [it.feedback_correct, it.feedback_default, *it.feedback.values()]
            for text in blobs:
                low = text.lower()
                for phrase in banned:
                    self.assertNotIn(phrase, low,
                                     f"item {it.id} feedback uses self-directed praise: {phrase!r}")


class TestRegistration(unittest.TestCase):
    def test_register_course_adds_skills(self):
        course = build_neva_and_theo()
        with Store(":memory:") as s:
            added = register_course(s, course)
            self.assertEqual(set(added),
                             {"sci.3-5.inclined-plane", "sci.3-5.lever-fulcrum"})
            skill = s.get_skill("sci.3-5.inclined-plane")
            self.assertEqual(skill["standard"], "NGSS 3-5-ETS1-1")
            self.assertAlmostEqual(skill["guess"], 0.25)

    def test_register_is_idempotent(self):
        course = build_neva_and_theo()
        with Store(":memory:") as s:
            register_course(s, course)
            added_again = register_course(s, course)
            self.assertEqual(added_again, [])

    def test_registered_skill_drives_the_store_loop(self):
        # End-to-end: register content, then record outcomes against a real skill.
        course = build_neva_and_theo()
        with Store(":memory:") as s:
            register_course(s, course)
            s.add_learner("kid1", "Neva")
            for _ in range(15):
                s.record_outcome("kid1", "sci.3-5.lever-fulcrum", correct=True)
            self.assertTrue(s.is_mastered("kid1", "sci.3-5.lever-fulcrum"))


if __name__ == "__main__":
    unittest.main()
