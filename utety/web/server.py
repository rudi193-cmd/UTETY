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

import contextlib
import re
import secrets
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from ..content.model import Course
from ..content.register import register_course
from ..core.loop import LessonSession
from ..core.store import Store
from ..knowledge import KnowledgeSeam, SourcedCard
from . import render

# Learner ids come off the wire; bound them before they touch the store
# (audit bite-4, W4 — no drive-by junk rows).
_LEARNER_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_MAX_SESSIONS = 64
_MAX_BODY = 64 * 1024          # far above any real form; caps hostile bodies
_HTML = "text/html; charset=utf-8"
_PLAIN = "text/plain; charset=utf-8"


class App:
    """Holds the store, course, per-learner sessions, and the (optional) seam."""

    def __init__(self, store: Store, course: Course, seam: KnowledgeSeam | None = None) -> None:
        self.store = store
        self.course = course
        self.seam = seam
        register_course(store, course)
        self._sessions: dict[str, LessonSession] = {}
        # Per-run CSRF token: embedded in the page shell, required (as the
        # X-Utety-Csrf header) on every POST. The custom header also forces a
        # CORS preflight, which this server never grants — so a hostile page
        # can't even blind-fire writes cross-origin (audit bite-4, W2).
        self.csrf = secrets.token_urlsafe(32)

    # ── session bookkeeping ────────────────────────────────────────────────
    def _session(self, learner: str) -> LessonSession:
        if self.store.get_learner(learner) is None:
            self.store.add_learner(learner, "Explorer")
        if learner not in self._sessions:
            if len(self._sessions) >= _MAX_SESSIONS:
                # Sessions are cheap bookkeeping over durable store state
                # (acks reload from the disclosure log) — evict the oldest.
                self._sessions.pop(next(iter(self._sessions)))
            self._sessions[learner] = LessonSession(self.store, self.course, learner)
        return self._sessions[learner]

    # ── the pure router ────────────────────────────────────────────────────
    def handle(self, method: str, path: str, params: dict, body: str,
               headers: dict | None = None) -> tuple[int, str, str]:
        learner = _one(params, "learner", "kid1")
        try:
            if not _LEARNER_RE.match(learner):
                return 400, _PLAIN, "bad learner id"
            # Header names are case-insensitive on the wire (urllib sends
            # X-utety-csrf); normalize before comparing. Constant-time compare
            # (independent audit 2026-07-14, N2).
            hdrs = {k.lower(): v for k, v in (headers or {}).items()}
            token = hdrs.get("x-utety-csrf", "")
            if method == "POST" and not secrets.compare_digest(
                token.encode("utf-8"), self.csrf.encode("utf-8")
            ):
                return 403, _PLAIN, "missing or wrong csrf token"

            if method == "GET" and path == "/":
                # Side-effect free: the learner row is created on the first
                # POST, never by a GET (audit bite-4, W4).
                return 200, _HTML, render.page_shell(self.course, learner, csrf=self.csrf)

            if method == "POST" and path == "/step":
                return self._step(params)

            if method == "POST" and path == "/answer":
                return self._answer(params, body)

            return 404, _PLAIN, "not found"
        except Exception:  # a child should never see a stack trace
            # learner is regex-validated before any exception can arise, but
            # escape anyway — this is the one sink that isn't a render.*
            # function (independent audit 2026-07-14, N1).
            return 500, _HTML, (
                f'<section class="card"><p class="hanz">Something went quiet in the '
                f"back shelves. Let's try that again.</p>"
                f'<button class="primary" data-post="/step?learner={escape(learner)}">'
                f"Keep going</button></section>"
            )

    def _step(self, params: dict) -> tuple[int, str, str]:
        learner = _one(params, "learner", "kid1")
        sess = self._session(learner)
        ack = _one(params, "ack", "")
        if ack:
            # A stale/crafted ack must not 500 the child; the real next step
            # is the answer either way.
            with contextlib.suppress(ValueError):
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
            return 404, _PLAIN, "unknown item"

        qs = parse_qs(body)
        if item.kind == "multi":
            response: object = qs.get("response", [])
        else:
            response = qs.get("response", [""])[0]

        # Absence is never graded (audit bite-4, W1): a stray "Check" with
        # nothing selected re-presents the item — no outcome reaches BKT.
        empty = not response if item.kind == "multi" else not str(response).strip()
        if empty:
            return 200, _HTML, render.item_fragment(
                sess.present(item_id), item, learner,
                nudge="Pick an answer first — then Check.",
            )

        # Out-of-set values aren't answers either (independent audit
        # 2026-07-14, F3): a value outside the item's choices would be graded
        # as a wrong-distractor pick and poison the mastery signal.
        if item.kind in ("single", "multi"):
            valid = set(item.choices)
            picked = set(response) if item.kind == "multi" else {response}
            if not picked <= valid:
                return 200, _HTML, render.item_fragment(
                    sess.present(item_id), item, learner,
                    nudge="Pick one of the options first — then Check.",
                )

        try:
            result = sess.answer(item_id, response)
        except ValueError:
            # Malformed or out-of-order request (crafted body, answer before
            # its experience). Grade nothing; surface the learner's real next
            # step instead of a dead-end error (audit bite-4, W1).
            return self._step({"learner": [learner]})
        cards = self._cards_for(result)
        return 200, _HTML, render.feedback_fragment(result, cards, learner)

    def _cards_for(self, result) -> list[SourcedCard]:
        """Best-effort sourcing: the seam if configured, else the local citation."""
        if self.seam is not None:
            try:
                cards = self.seam.back(result.source_query)
                if cards:
                    return cards
            except Exception:  # noqa: S110 — deliberate: offline/no-endpoint falls
                # through to the local citation so Rule 1 holds without a network.
                # Known gap: failures are invisible (audit bite-4, smaller notes);
                # route seam errors to the disclosure spine in the W-fix round.
                pass
        return [SourcedCard(source=result.citation, snippet="", confidence="")]


def _allowed_hosts(host: str, port: int) -> frozenset[str]:
    """Host-header values a local reading room may be addressed by."""
    return frozenset({
        host, f"{host}:{port}",
        "127.0.0.1", f"127.0.0.1:{port}",
        "localhost", f"localhost:{port}",
    })


def _host_ok(header_host: str, allowed: frozenset[str]) -> bool:
    return header_host in allowed


def serve(app: App, port: int = 8799, host: str = "127.0.0.1") -> HTTPServer:
    """Build the reading-room server (loopback by default). The caller runs
    ``serve_forever()`` on the returned server."""

    class Handler(BaseHTTPRequestHandler):
        def _dispatch(self, method: str) -> None:
            # DNS-rebinding guard (audit bite-4, W2): a page that points its
            # own domain at 127.0.0.1 arrives with its domain in Host. Only
            # names that genuinely mean this device are served.
            if not _host_ok(self.headers.get("Host", ""), allowed):
                self._reply(403, b"unrecognized host")
                return
            # Malformed, negative, or absurd Content-Length must not crash the
            # handler or block the single-threaded server on an endless read
            # (independent audit 2026-07-14, F4).
            try:
                length = int(self.headers.get("Content-Length", 0) or 0)
            except ValueError:
                length = -1
            if length < 0 or length > _MAX_BODY:
                self._reply(400, b"bad content length")
                return
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
            status, ctype, text = app.handle(
                method, parsed.path, params, body, headers=dict(self.headers)
            )
            data = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _reply(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", _PLAIN)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def log_message(self, *args) -> None:
            pass  # quiet

    httpd = HTTPServer((host, port), Handler)
    # Compute from the BOUND port so port=0 (ephemeral, used by tests) works;
    # `allowed` is a closure variable of Handler._dispatch, resolved at
    # request time, so assigning it here is safe.
    allowed = _allowed_hosts(host, httpd.server_address[1])
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
