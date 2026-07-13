#!/usr/bin/env python3
"""Tests for utety/web — render fragments and the pure App router."""
import re
import unittest

from utety.content.courses import build_neva_and_theo
from utety.core.loop import Presentation, Result
from utety.knowledge import KnowledgeSeam, SourcedCard
from utety.core.store import Store
from utety.web import render
from utety.web.server import App


class TestRender(unittest.TestCase):
    def setUp(self):
        self.course = build_neva_and_theo()

    def test_page_shell_has_title_and_begin(self):
        html = render.page_shell(self.course, "kid1")
        self.assertIn(self.course.title, html)
        self.assertIn("/step?learner=kid1", html)
        self.assertIn("<div id=\"stage\"", html)

    def test_experience_fragment_posts_ack(self):
        exp = self.course.experiences[0]
        html = render.experience_fragment(exp, "kid1")
        self.assertIn(f"ack={exp.id}", html)
        self.assertIn("Slide it,", html)   # title, minus the escaped apostrophe

    def test_item_fragment_hides_answer_shows_choices(self):
        item = next(i for i in self.course.items if i.id == "ip1")
        pres = Presentation(item_id="ip1", prompt=item.prompt, choices=item.choices)
        html = render.item_fragment(pres, item, "kid1")
        self.assertIn(item.prompt, html)
        self.assertIn('name="response"', html)
        self.assertIn("item=ip1", html)
        # The correct-answer value appears as a choice, but never marked correct.
        self.assertNotIn("correct", html.lower())

    def test_scaffold_only_shown_when_present(self):
        item = next(i for i in self.course.items if i.id == "ip3")
        with_s = render.item_fragment(
            Presentation("ip3", item.prompt, item.choices, scaffold=item.scaffold), item, "k")
        without_s = render.item_fragment(
            Presentation("ip3", item.prompt, item.choices, scaffold=None), item, "k")
        self.assertIn("scaffold", with_s)
        self.assertNotIn('class="scaffold"', without_s)

    def test_card_html_has_badge_and_corners(self):
        card = SourcedCard(url="https://x", source="NGSS", snippet="a ramp",
                           confidence="high", date="2026")
        html = render.card_html(card)
        self.assertIn("badge hi", html)
        self.assertIn("corner", html)
        self.assertIn("NGSS", html)
        self.assertIn("https://x", html)

    def test_feedback_fragment_shows_feedback_and_source(self):
        r = Result("ip1", "sci.3-5.inclined-plane", correct=True,
                   feedback="that's what your hands felt", mastery=0.5,
                   mastered=False, citation="NGSS 3-5-ETS1-1", source_query="q")
        html = render.feedback_fragment(r, [SourcedCard(source="NGSS 3-5-ETS1-1")], "kid1")
        self.assertIn("what your hands felt", html)   # feedback, minus escaped apostrophe
        self.assertIn("sourced", html)


class TestAppRouting(unittest.TestCase):
    def setUp(self):
        self.app = App(Store(":memory:"), build_neva_and_theo())

    def test_root_serves_page(self):
        status, ctype, html = self.app.handle("GET", "/", {"learner": ["kid1"]}, "")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("Begin", html)

    def test_first_step_is_experience(self):
        self.app.handle("GET", "/", {"learner": ["kid1"]}, "")
        _, _, html = self.app.handle("POST", "/step", {"learner": ["kid1"]}, "")
        self.assertIn("First, your hands", html)

    def test_unknown_path_404(self):
        status, _, _ = self.app.handle("GET", "/nope", {}, "")
        self.assertEqual(status, 404)

    def test_unknown_item_404(self):
        status, _, _ = self.app.handle("POST", "/answer",
                                       {"learner": ["kid1"], "item": ["ghost"]}, "response=a")
        self.assertEqual(status, 404)

    def test_offline_source_falls_back_to_citation(self):
        # No seam configured → the feedback card carries the item's local citation.
        self.app.handle("GET", "/", {"learner": ["kid1"]}, "")
        self.app.handle("POST", "/step", {"learner": ["kid1"], "ack": ["exp.ramp"]}, "")
        _, _, html = self.app.handle("POST", "/answer",
                                     {"learner": ["kid1"], "item": ["ip1"]}, "response=a")
        self.assertIn("sourced", html)
        self.assertIn("NGSS 3-5-ETS1-1", html)

    def test_seam_cards_used_when_configured(self):
        seam = KnowledgeSeam(transport=lambda u, p: {"cards": [
            {"url": "https://galileo", "source": "Two New Sciences", "confidence": "high"}]},
            base_url="https://knowledge.utety")
        app = App(Store(":memory:"), build_neva_and_theo(), seam=seam)
        app.handle("GET", "/", {"learner": ["kid1"]}, "")
        app.handle("POST", "/step", {"learner": ["kid1"], "ack": ["exp.ramp"]}, "")
        _, _, html = app.handle("POST", "/answer",
                                {"learner": ["kid1"], "item": ["ip1"]}, "response=a")
        self.assertIn("Two New Sciences", html)
        self.assertIn("badge hi", html)


class TestFullPlaythroughOverHTTP(unittest.TestCase):
    BODY = {"ip1": "response=a", "ip2": "response=false", "ip3": "response=a",
            "lf1": "response=arm&response=fulcrum&response=load",
            "lf2": "response=a", "lf3": "response=a"}

    def test_plays_to_completion_through_the_router(self):
        app = App(Store(":memory:"), build_neva_and_theo())
        app.handle("GET", "/", {"learner": ["kid1"]}, "")
        _, _, html = app.handle("POST", "/step", {"learner": ["kid1"]}, "")

        for _ in range(300):
            if "card complete" in html:
                break
            if 'class="card item"' in html:
                iid = re.search(r"item=([\w.]+)", html).group(1)
                _, _, html = app.handle("POST", "/answer",
                                        {"learner": ["kid1"], "item": [iid]}, self.BODY[iid])
            else:
                m = re.search(r"ack=([\w.]+)", html)
                params = {"learner": ["kid1"]}
                if m and 'class="card experience"' in html:
                    params["ack"] = [m.group(1)]
                _, _, html = app.handle("POST", "/step", params, "")

        self.assertIn("card complete", html)
        self.assertEqual(html.count("✓"), 2)   # both skills marked mastered
        self.assertNotIn("·", html)            # none left unmastered


if __name__ == "__main__":
    unittest.main()
