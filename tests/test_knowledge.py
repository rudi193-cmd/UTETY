#!/usr/bin/env python3
"""Tests for utety/knowledge.py — the UTETY→Jeles knowledge seam.

The load-bearing tests here are the privacy ones: the only thing that leaves the
device is a de-identified concept query, and no learner identifier can ride
along — proven structurally (the send path has no learner parameter) and
end-to-end (a real loop Result's query produces a clean payload).
"""
import inspect
import unittest

from utety.content.courses import build_neva_and_theo
from utety.content.register import register_course
from utety.core.loop import LessonSession
from utety.core.store import Store
from utety.knowledge import (
    KnowledgeSeam,
    SourcedCard,
    contains_pii,
    deidentify,
)


class TestDeidentify(unittest.TestCase):
    def test_scrubs_email(self):
        self.assertNotIn("@", deidentify("ask about neva@example.com and ramps"))

    def test_scrubs_ssn(self):
        self.assertIn("[redacted]", deidentify("student 123-45-6789 asked"))

    def test_scrubs_phone(self):
        self.assertNotIn("555", deidentify("call 555-123-4567 about levers"))

    def test_scrubs_secret_prefix(self):
        self.assertIn("[redacted]", deidentify("key sk-abc12345 leaked"))

    def test_leaves_concept_query_intact(self):
        q = "why does an inclined plane reduce the force needed to raise a load"
        self.assertEqual(deidentify(q), q)

    def test_contains_pii(self):
        self.assertTrue(contains_pii("reach me at a@b.com"))
        self.assertFalse(contains_pii("what is a fulcrum"))


class TestSourcedCard(unittest.TestCase):
    def test_from_dict_defaults(self):
        c = SourcedCard.from_dict({"url": "u", "source": "s"})
        self.assertEqual(c.url, "u")
        self.assertEqual(c.confidence, "")

    def test_full_card_contract(self):
        c = SourcedCard.from_dict({
            "url": "https://x", "source": "NGSS", "snippet": "a ramp...",
            "confidence": "high", "date": "2026-07-13",
        })
        self.assertEqual(c.confidence, "high")


class TestSeamStructuralPrivacy(unittest.TestCase):
    def test_back_signature_carries_no_learner(self):
        # The privacy guarantee in the type signature: only a query goes in.
        params = list(inspect.signature(KnowledgeSeam.back).parameters)
        self.assertEqual(params, ["self", "query"])

    def test_payload_contains_only_the_query(self):
        seen = {}

        def fake(url, payload):
            seen["url"] = url
            seen["payload"] = payload
            return {"cards": []}

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety")
        seam.back("why does a lever multiply force")
        self.assertEqual(set(seen["payload"].keys()), {"query"})
        self.assertTrue(seen["url"].endswith("/search"))

    def test_query_is_deidentified_before_send(self):
        seen = {}

        def fake(url, payload):
            seen["payload"] = payload
            return {"cards": []}

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety")
        seam.back("student neva@example.com asks why the fulcrum matters")
        self.assertFalse(contains_pii(seen["payload"]["query"]))
        self.assertNotIn("@", seen["payload"]["query"])


class TestSeamBehavior(unittest.TestCase):
    def test_parses_cards(self):
        def fake(url, payload):
            return {"cards": [
                {"url": "https://galileo", "source": "Two New Sciences",
                 "snippet": "gravity acts equally", "confidence": "high",
                 "date": "1638"},
            ]}

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety")
        cards = seam.back("do heavier objects fall faster")
        self.assertEqual(len(cards), 1)
        self.assertIsInstance(cards[0], SourcedCard)
        self.assertEqual(cards[0].confidence, "high")

    def test_accepts_bare_list_response(self):
        def fake(url, payload):
            return [{"url": "u", "source": "s"}]

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety")
        self.assertEqual(len(seam.back("q")), 1)

    def test_raises_without_endpoint(self):
        seam = KnowledgeSeam(transport=lambda u, p: {}, base_url="")
        with self.assertRaises(RuntimeError):
            seam.back("q")


class TestEndToEndWithLoop(unittest.TestCase):
    def test_loop_result_query_leaves_without_learner_id(self):
        # A real loop Result feeds the seam. The outgoing payload must carry the
        # concept query and NOTHING that identifies the learner.
        store = Store(":memory:")
        course = build_neva_and_theo()
        register_course(store, course)
        store.add_learner("kid1", "Theo Q. Student")
        sess = LessonSession(store, course, "kid1")
        sess.acknowledge_experience("exp.ramp")
        result = sess.answer("ip1", "a")

        seen = {}

        def fake(url, payload):
            seen["payload"] = payload
            return {"cards": [{"url": "u", "source": "NGSS 3-5-ETS1-1"}]}

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety")
        cards = seam.back(result.source_query)

        self.assertTrue(cards)
        blob = str(seen["payload"]).lower()
        self.assertNotIn("kid1", blob)
        self.assertNotIn("theo", blob)
        self.assertIn("inclined plane", seen["payload"]["query"])


if __name__ == "__main__":
    unittest.main()
