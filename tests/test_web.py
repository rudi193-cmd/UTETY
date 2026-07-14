#!/usr/bin/env python3
"""Tests for utety/web — render fragments, the pure App router, and the real
socket adapter (Host check, Content-Length handling — independent audit F2)."""
import re
import socket
import threading
import typing
import unittest
import urllib.error
import urllib.request

from utety.content.courses import build_neva_and_theo
from utety.core.loop import Presentation, Result
from utety.knowledge import KnowledgeSeam, SourcedCard
from utety.core.store import Store
from utety.web import render
from utety.web.server import App, serve


def post(app: App, path: str, params: dict, body: str = ""):
    """POST through the router with the app's own CSRF token (as the page does)."""
    return app.handle("POST", path, params, body, {"X-Utety-Csrf": app.csrf})


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

    def test_card_html_links_only_https(self):
        # Audit bite-4 W3: cards are external input; escaping doesn't stop a
        # javascript: scheme, so anything non-https renders unlinked.
        for url in ("javascript:alert(1)", "http://plain.example", "data:text/html,x"):
            html = render.card_html(SourcedCard(url=url, source="s"))
            self.assertNotIn("href", html, f"{url!r} must not become a link")
        linked = render.card_html(SourcedCard(url="https://ok.example", source="s"))
        self.assertIn('href="https://ok.example"', linked)

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
        _, _, html = post(self.app, "/step", {"learner": ["kid1"]})
        self.assertIn("First, your hands", html)

    def test_unknown_path_404(self):
        status, _, _ = self.app.handle("GET", "/nope", {}, "")
        self.assertEqual(status, 404)

    def test_unknown_item_404(self):
        status, _, _ = post(self.app, "/answer",
                            {"learner": ["kid1"], "item": ["ghost"]}, "response=a")
        self.assertEqual(status, 404)

    def test_offline_source_falls_back_to_citation(self):
        # No seam configured → the feedback card carries the item's local citation.
        self.app.handle("GET", "/", {"learner": ["kid1"]}, "")
        post(self.app, "/step", {"learner": ["kid1"], "ack": ["exp.ramp"]})
        _, _, html = post(self.app, "/answer",
                          {"learner": ["kid1"], "item": ["ip1"]}, "response=a")
        self.assertIn("sourced", html)
        self.assertIn("NGSS 3-5-ETS1-1", html)

    def test_seam_cards_used_when_configured(self):
        seam = KnowledgeSeam(transport=lambda u, p: {"cards": [
            {"url": "https://galileo", "source": "Two New Sciences", "confidence": "high"}]},
            base_url="https://knowledge.utety")
        app = App(Store(":memory:"), build_neva_and_theo(), seam=seam)
        app.handle("GET", "/", {"learner": ["kid1"]}, "")
        post(app, "/step", {"learner": ["kid1"], "ack": ["exp.ramp"]})
        _, _, html = post(app, "/answer",
                          {"learner": ["kid1"], "item": ["ip1"]}, "response=a")
        self.assertIn("Two New Sciences", html)
        self.assertIn("badge hi", html)


class TestAbsenceIsNeverGraded(unittest.TestCase):
    """Audit bite-4 W1: a stray Check click must not touch the mastery signal."""

    def setUp(self):
        self.app = App(Store(":memory:"), build_neva_and_theo())
        post(self.app, "/step", {"learner": ["kid1"]})
        post(self.app, "/step", {"learner": ["kid1"], "ack": ["exp.ramp"]})

    def _outcomes(self):
        return self.app.store.outcome_history("kid1", "sci.3-5.inclined-plane")

    def test_empty_single_represents_instead_of_grading(self):
        status, _, html = post(self.app, "/answer",
                               {"learner": ["kid1"], "item": ["ip1"]}, "")
        self.assertEqual(status, 200)
        self.assertIn('class="card item"', html)      # the item again, not feedback
        self.assertIn("Pick an answer first", html)
        self.assertEqual(self._outcomes(), [], "no outcome may be recorded")

    def test_empty_boolean_represents_instead_of_500(self):
        status, _, html = post(self.app, "/answer",
                               {"learner": ["kid1"], "item": ["ip2"]}, "")
        self.assertEqual(status, 200)
        self.assertIn('class="card item"', html)
        self.assertEqual(self._outcomes(), [])

    def test_empty_multi_represents_instead_of_grading(self):
        post(self.app, "/step", {"learner": ["kid1"], "ack": ["exp.lever"]})
        status, _, html = post(self.app, "/answer",
                               {"learner": ["kid1"], "item": ["lf1"]}, "")
        self.assertEqual(status, 200)
        self.assertIn('class="card item"', html)
        self.assertEqual(
            self.app.store.outcome_history("kid1", "sci.3-5.lever-fulcrum"), [])

    def test_out_of_set_single_not_graded(self):
        # Independent audit F3: a value outside the choice set is not a wrong
        # answer — it's a malformed request, and must not reach BKT.
        status, _, html = post(self.app, "/answer",
                               {"learner": ["kid1"], "item": ["ip1"]},
                               "response=ZZZ_not_a_choice")
        self.assertEqual(status, 200)
        self.assertIn('class="card item"', html)
        self.assertEqual(self._outcomes(), [])

    def test_out_of_set_multi_not_graded(self):
        post(self.app, "/step", {"learner": ["kid1"], "ack": ["exp.lever"]})
        status, _, html = post(self.app, "/answer",
                               {"learner": ["kid1"], "item": ["lf1"]},
                               "response=nonsense1&response=nonsense2")
        self.assertEqual(status, 200)
        self.assertIn('class="card item"', html)
        self.assertEqual(
            self.app.store.outcome_history("kid1", "sci.3-5.lever-fulcrum"), [])

    def test_crafted_garbage_boolean_records_nothing(self):
        status, _, _ = post(self.app, "/answer",
                            {"learner": ["kid1"], "item": ["ip2"]}, "response=banana")
        self.assertEqual(status, 200)
        self.assertEqual(self._outcomes(), [])

    def test_answer_before_gate_redirects_to_real_next_step(self):
        # lf1 requires exp.lever, not yet acked: no 500, no outcome — the
        # learner's actual next step comes back instead.
        status, _, html = post(self.app, "/answer",
                               {"learner": ["kid1"], "item": ["lf1"]}, "response=arm")
        self.assertEqual(status, 200)
        self.assertNotIn("went quiet", html)
        self.assertEqual(
            self.app.store.outcome_history("kid1", "sci.3-5.lever-fulcrum"), [])


class TestWebHardening(unittest.TestCase):
    def setUp(self):
        self.app = App(Store(":memory:"), build_neva_and_theo())

    def test_post_without_csrf_token_403(self):
        # Audit bite-4 W2: no cross-origin page can blind-fire writes.
        status, _, _ = self.app.handle("POST", "/step", {"learner": ["kid1"]}, "")
        self.assertEqual(status, 403)
        status, _, _ = self.app.handle("POST", "/step", {"learner": ["kid1"]}, "",
                                       {"X-Utety-Csrf": "wrong"})
        self.assertEqual(status, 403)

    def test_page_shell_carries_the_csrf_token(self):
        _, _, html = self.app.handle("GET", "/", {"learner": ["kid1"]}, "")
        self.assertIn(self.app.csrf, html)

    def test_get_root_creates_no_learner(self):
        # Audit bite-4 W4: GET is side-effect free.
        self.app.handle("GET", "/", {"learner": ["driveby"]}, "")
        self.assertIsNone(self.app.store.get_learner("driveby"))

    def test_invalid_learner_id_400(self):
        for bad in ("<script>", "a" * 65, "kid one", ""):
            status, _, _ = self.app.handle("GET", "/", {"learner": [bad]}, "")
            self.assertEqual(status, 400, f"learner {bad!r} must be rejected")

    def test_error_page_offers_recovery(self):
        # Force a genuine 500: a session whose next_step explodes.
        post(self.app, "/step", {"learner": ["kid1"]})
        self.app._sessions["kid1"].next_step = None  # not callable → TypeError
        status, _, html = post(self.app, "/step", {"learner": ["kid1"]})
        self.assertEqual(status, 500)
        self.assertIn("data-post", html, "the child must have a way onward")
        self.assertNotIn("TypeError", html, "no error taxonomy for the child")

    def test_host_allowlist_blocks_rebinding(self):
        # Audit bite-4 W2: only names that mean this device are served.
        from utety.web.server import _allowed_hosts, _host_ok
        allowed = _allowed_hosts("127.0.0.1", 8799)
        for good in ("127.0.0.1:8799", "localhost:8799", "127.0.0.1", "localhost"):
            self.assertTrue(_host_ok(good, allowed), good)
        for evil in ("attacker.example", "attacker.example:8799",
                     "127.0.0.1.attacker.example:8799", ""):
            self.assertFalse(_host_ok(evil, allowed), evil)


class TestSeamFailureFallback(unittest.TestCase):
    def test_seam_error_falls_back_to_local_citation(self):
        # Independent audit F2 gap 3: Rule 1 must hold when the backend RAISES,
        # not only when no seam is configured.
        def boom(url, payload):
            raise RuntimeError("backend down")

        seam = KnowledgeSeam(transport=boom, base_url="https://knowledge.utety")
        app = App(Store(":memory:"), build_neva_and_theo(), seam=seam)
        post(app, "/step", {"learner": ["kid1"]})
        post(app, "/step", {"learner": ["kid1"], "ack": ["exp.ramp"]})
        _, _, html = post(app, "/answer",
                          {"learner": ["kid1"], "item": ["ip1"]}, "response=a")
        self.assertIn("NGSS 3-5-ETS1-1", html,
                      "local citation must back the claim when the seam fails")


class TestOverRealSocket(unittest.TestCase):
    """Independent audit F2: the socket adapter — Host check wiring,
    Content-Length handling, body pass-through — pinned by tests instead of
    manual verification. The store and server live on one thread (as in
    production); requests come from the test thread."""

    @classmethod
    def setUpClass(cls):
        ready = threading.Event()
        cls.holder = {}

        def run():
            app = App(Store(":memory:"), build_neva_and_theo())
            httpd = serve(app, port=0)          # ephemeral port
            cls.holder["app"] = app
            cls.holder["httpd"] = httpd
            ready.set()
            httpd.serve_forever()

        cls.thread = threading.Thread(target=run, daemon=True)
        cls.thread.start()
        if not ready.wait(5):   # a real raise — asserts vanish under -O (A4!)
            raise RuntimeError("server thread failed to start")
        cls.port = cls.holder["httpd"].server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.holder["httpd"].shutdown()
        cls.holder["httpd"].server_close()

    def _raw(self, request_bytes: bytes) -> str:
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as s:
            s.sendall(request_bytes)
            return s.recv(4096).decode("utf-8", "replace")

    def test_valid_host_serves_shell_with_token(self):
        html = urllib.request.urlopen(f"{self.base}/?learner=kid1").read().decode()
        self.assertIn(self.holder["app"].csrf, html)

    def test_foreign_host_gets_403(self):
        req = urllib.request.Request(
            f"{self.base}/", headers={"Host": f"attacker.example:{self.port}"})
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 403)

    def test_post_body_arrives_intact_and_flows(self):
        token = self.holder["app"].csrf
        def post_url(path, body=b""):
            req = urllib.request.Request(
                f"{self.base}{path}", data=body,
                headers={"X-Utety-Csrf": token}, method="POST")
            return urllib.request.urlopen(req).read().decode()

        step = post_url("/step?learner=sockkid")
        self.assertIn("First, your hands", step)
        post_url("/step?learner=sockkid&ack=exp.ramp")
        feedback = post_url("/answer?learner=sockkid&item=ip1", b"response=a")
        self.assertIn("hands felt", feedback)   # correct-answer feedback text

    def test_post_without_token_403_over_socket(self):
        req = urllib.request.Request(
            f"{self.base}/step?learner=kid1", data=b"", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 403)

    def test_malformed_content_length_400(self):
        resp = self._raw(
            b"POST /step?learner=kid1 HTTP/1.1\r\n"
            + f"Host: 127.0.0.1:{self.port}\r\n".encode()
            + b"Content-Length: abc\r\n\r\n")
        self.assertIn(" 400 ", resp.splitlines()[0])

    def test_negative_content_length_400(self):
        resp = self._raw(
            b"POST /step?learner=kid1 HTTP/1.1\r\n"
            + f"Host: 127.0.0.1:{self.port}\r\n".encode()
            + b"Content-Length: -5\r\n\r\n")
        self.assertIn(" 400 ", resp.splitlines()[0])

    def test_oversized_content_length_400(self):
        resp = self._raw(
            b"POST /step?learner=kid1 HTTP/1.1\r\n"
            + f"Host: 127.0.0.1:{self.port}\r\n".encode()
            + b"Content-Length: 999999999\r\n\r\n")
        self.assertIn(" 400 ", resp.splitlines()[0])


class TestFullPlaythroughOverHTTP(unittest.TestCase):
    BODY: typing.ClassVar[dict] = {
        "ip1": "response=a", "ip2": "response=false", "ip3": "response=a",
        "lf1": "response=arm&response=fulcrum&response=load",
        "lf2": "response=a", "lf3": "response=a"}

    def test_plays_to_completion_through_the_router(self):
        app = App(Store(":memory:"), build_neva_and_theo())
        app.handle("GET", "/", {"learner": ["kid1"]}, "")
        _, _, html = post(app, "/step", {"learner": ["kid1"]})

        for _ in range(300):
            if "card complete" in html:
                break
            if 'class="card item"' in html:
                iid = re.search(r"item=([\w.]+)", html).group(1)
                _, _, html = post(app, "/answer",
                                  {"learner": ["kid1"], "item": [iid]}, self.BODY[iid])
            else:
                m = re.search(r"ack=([\w.]+)", html)
                params = {"learner": ["kid1"]}
                if m and 'class="card experience"' in html:
                    params["ack"] = [m.group(1)]
                _, _, html = post(app, "/step", params)

        self.assertIn("card complete", html)
        self.assertEqual(html.count("✓"), 2)   # both skills marked mastered
        self.assertNotIn("·", html)            # none left unmastered


if __name__ == "__main__":
    unittest.main()
