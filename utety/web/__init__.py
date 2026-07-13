"""UTETY web — the on-device student reading room (build-plan §1, Phase 1 bite 4).

A small stdlib ``http.server`` front that runs where the store lives — on the
learner's device — and renders server-side htmx-style fragments (so the persona
voice is un-bypassable). UTETY's own chrome and Hanz's voice; the one element
borrowed from the Jeles reading room is the sourced-card grammar (corner
bracket + confidence badge + provenance), honoring the §7 boundary.

Routing lives in ``App.handle`` as a pure function of (method, path, params,
body) so the whole flow is unit-testable without opening a socket. ``serve``
wraps it in a BaseHTTPRequestHandler for real use.
"""
