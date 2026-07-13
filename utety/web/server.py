#!/usr/bin/env python3
"""utety/web/server.py — the on-device reading-room server.

Routing is a pure function — ``App.handle(method, path, params, body)`` returns
``(status, content_type, text)`` — so the entire flow is unit-testable without a
socket. ``serve`` adapts it to ``http.server`` for real use on the device.

Runs where the store lives (on-device). The seam is best-effort: if no knowledge
endpoint is configured (offline demo), sourced cards fall back to the item's
local citation, so Rule 1 (every claim sourced) still holds and the front still
runs.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from ..content.model import Course
from ..content.register import register_course
from ..core.loop import LessonSession
from ..core.store import Store
from ..knowledge import KnowledgeSeam, SourcedCard
from . import render


class App:
    """Holds the store, course, per-learner sessions, and the (optional) seam."""

    def __init__(self, store: Store, course: Course, seam: KnowledgeSeam | None = None) -> None:
        self.store = store
        self.course = course
        self.seam = seam
        register_course(store, course)
        self._sessions: dict[str, LessonSession] = {}

    # ── session bookkeeping ────────────────────────────────────────────────
    def _session(self, learner: str) -> LessonSession:
        if self.store.get_learner(learner) is None:
            self.store.add_learner(learner, "Explorer")
        if learner not in self._sessions:
            self._sessions[learner] = LessonSession(self.store, self.course, learner)
        return self._sessions[learner]

    # ── the pure router ────────────────────────────────────────────────────
    def handle(self, method: str, path: str, params: dict, body: str) -> tuple[int, str, str]:
        try:
            if method == "GET" and path == "/":
                learner = _one(params, "learner", "kid1")
                self._session(learner)
                return 200, "text/html; charset=utf-8", render.page_shell(self.course, learner)

            if method == "POST" and path == "/step":
                return self._step(params)

            if method == "POST" and path == "/answer":
                return self._answer(params, body)

            return 404, "text/plain; charset=utf-8", "not found"
        except Exception as exc:  # a child should never see a stack trace
            return 500, "text/html; charset=utf-8", (
                f'<section class="card"><p class="hanz">Something went quiet in the '
                f'back shelves. Let\'s try that again.</p><!-- {type(exc).__name__} --></section>'
            )

    def _step(self, params: dict) -> tuple[int, str, str]:
        learner = _one(params, "learner", "kid1")
        sess = self._session(learner)
        ack = _one(params, "ack", "")
        if ack:
            sess.acknowledge_experience(ack)
        step = sess.next_step()
        if step.kind == "experience":
            html = render.experience_fragment(step.experience, learner)
        elif step.kind == "item":
            html = render.item_fragment(step.present, step.item, learner)
        else:
            html = render.complete_fragment(sess.progress(), self.course)
        return 200, "text/html; charset=utf-8", html

    def _answer(self, params: dict, body: str) -> tuple[int, str, str]:
        learner = _one(params, "learner", "kid1")
        item_id = _one(params, "item", "")
        sess = self._session(learner)
        item = next((i for i in self.course.items if i.id == item_id), None)
        if item is None:
            return 404, "text/plain; charset=utf-8", "unknown item"

        qs = parse_qs(body)
        if item.kind == "multi":
            response: object = qs.get("response", [])
        else:
            response = qs.get("response", [""])[0]

        result = sess.answer(item_id, response)
        cards = self._cards_for(result)
        return 200, "text/html; charset=utf-8", render.feedback_fragment(result, cards, learner)

    def _cards_for(self, result) -> list[SourcedCard]:
        """Best-effort sourcing: the seam if configured, else the local citation."""
        if self.seam is not None:
            try:
                cards = self.seam.back(result.source_query)
                if cards:
                    return cards
            except Exception:
                pass  # offline / no endpoint — fall through to the local citation
        return [SourcedCard(source=result.citation, snippet="", confidence="")]


def serve(app: App, port: int = 8799, host: str = "127.0.0.1") -> HTTPServer:
    """Start the reading room on the device. Blocks in serve_forever."""

    class Handler(BaseHTTPRequestHandler):
        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            length = int(self.headers.get("Content-Length", 0) or 0)
            body = self.rfile.read(length).decode("utf-8") if length else ""
            status, ctype, text = app.handle(method, parsed.path, params, body)
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def log_message(self, *args) -> None:
            pass  # quiet

    httpd = HTTPServer((host, port), Handler)
    return httpd


def _one(params: dict, key: str, default: str) -> str:
    v = params.get(key)
    if isinstance(v, list):
        return v[0] if v else default
    return v if v else default


def _demo_app() -> App:
    """A ready-to-serve app over an in-memory store and the neva-and-theo course."""
    from ..content.courses import build_neva_and_theo
    return App(Store(":memory:"), build_neva_and_theo())


if __name__ == "__main__":  # pragma: no cover
    import os

    store_path = os.environ.get("UTETY_STORE", ":memory:")
    from ..content.courses import build_neva_and_theo

    seam = KnowledgeSeam() if os.environ.get("WILLOW_UTETY_KNOWLEDGE_URL") else None
    app = App(Store(store_path), build_neva_and_theo(), seam=seam)
    port = int(os.environ.get("UTETY_PORT", "8799"))
    httpd = serve(app, port=port)
    print(f"UTETY reading room on http://127.0.0.1:{port}  (store: {store_path})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
