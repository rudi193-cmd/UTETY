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
    ConsentDenied,
    EnvConsent,
    KnowledgeSeam,
    SourcedCard,
    StaticConsent,
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

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety",
                             consent=StaticConsent(True))
        seam.back("why does a lever multiply force")
        self.assertEqual(set(seen["payload"].keys()), {"query"})
        self.assertTrue(seen["url"].endswith("/search"))

    def test_query_is_deidentified_before_send(self):
        seen = {}

        def fake(url, payload):
            seen["payload"] = payload
            return {"cards": []}

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety",
                             consent=StaticConsent(True))
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

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety",
                             consent=StaticConsent(True))
        cards = seam.back("do heavier objects fall faster")
        self.assertEqual(len(cards), 1)
        self.assertIsInstance(cards[0], SourcedCard)
        self.assertEqual(cards[0].confidence, "high")

    def test_accepts_bare_list_response(self):
        def fake(url, payload):
            return [{"url": "u", "source": "s"}]

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety",
                             consent=StaticConsent(True))
        self.assertEqual(len(seam.back("q")), 1)

    def test_raises_without_endpoint(self):
        seam = KnowledgeSeam(transport=lambda u, p: {}, base_url="",
                             consent=StaticConsent(True))
        with self.assertRaises(RuntimeError):
            seam.back("q")


class TestConsentGovernsEgress(unittest.TestCase):
    """B-37 (P0): consent.internet must actually govern egress. With consent
    off, no bytes leave the device — the transport is never even reached."""

    def test_consent_off_refuses_and_never_touches_transport(self):
        calls = []

        def spy(url, payload):
            calls.append((url, payload))     # must never run
            return {"cards": []}

        seam = KnowledgeSeam(transport=spy, base_url="https://knowledge.utety",
                             consent=StaticConsent(False))
        with self.assertRaises(ConsentDenied):
            seam.back("why does a ramp reduce force")
        self.assertEqual(calls, [])          # nothing egressed

    def test_default_is_fail_closed(self):
        # No consent argument, env unset → deny. The switch defaults to OFF.
        import os
        old = os.environ.pop("UTETY_CONSENT_INTERNET", None)
        try:
            seam = KnowledgeSeam(transport=lambda u, p: {"cards": []},
                                 base_url="https://knowledge.utety")
            with self.assertRaises(ConsentDenied):
                seam.back("what is a fulcrum")
        finally:
            if old is not None:
                os.environ["UTETY_CONSENT_INTERNET"] = old

    def test_consent_checked_before_endpoint_and_deidentify(self):
        # Consent denial must precede every other step: even with no endpoint
        # and a PII-laden query, the failure is ConsentDenied, and nothing is
        # prepared or sent.
        seam = KnowledgeSeam(transport=lambda u, p: {}, base_url="",
                             consent=StaticConsent(False))
        with self.assertRaises(ConsentDenied):
            seam.back("student neva@example.com asks about ramps")

    def test_consent_on_sends(self):
        seen = {}

        def fake(url, payload):
            seen["ok"] = True
            return {"cards": [{"url": "u", "source": "s"}]}

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety",
                             consent=StaticConsent(True))
        self.assertEqual(len(seam.back("what is a lever")), 1)
        self.assertTrue(seen.get("ok"))

    def test_env_consent_fail_closed_semantics(self):
        import os
        gate = EnvConsent()
        cases = {"": False, "  ": False, "false": False, "0": False, "off": False,
                 "no": False, "maybe": False, "granted": True, "true": True,
                 "1": True, "yes": True, "ON": True, "Allow": True}
        old = os.environ.get("UTETY_CONSENT_INTERNET")
        try:
            for val, expected in cases.items():
                os.environ["UTETY_CONSENT_INTERNET"] = val
                self.assertEqual(gate.internet_allowed(), expected, f"{val!r}")
            os.environ.pop("UTETY_CONSENT_INTERNET", None)
            self.assertFalse(gate.internet_allowed())   # unset → deny
        finally:
            if old is not None:
                os.environ["UTETY_CONSENT_INTERNET"] = old
            else:
                os.environ.pop("UTETY_CONSENT_INTERNET", None)

    def test_denial_is_a_raise_not_a_return(self):
        # A privacy control that could be swallowed is not a control. back()
        # raises; it never returns [] on denial (which a caller might ignore).
        seam = KnowledgeSeam(transport=lambda u, p: {"cards": []},
                             base_url="https://knowledge.utety",
                             consent=StaticConsent(False))
        with self.assertRaises(ConsentDenied):
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

        seam = KnowledgeSeam(transport=fake, base_url="https://knowledge.utety",
                             consent=StaticConsent(True))
        cards = seam.back(result.source_query)

        self.assertTrue(cards)
        blob = str(seen["payload"]).lower()
        self.assertNotIn("kid1", blob)
        self.assertNotIn("theo", blob)
        self.assertIn("inclined plane", seen["payload"]["query"])


if __name__ == "__main__":
    unittest.main()
