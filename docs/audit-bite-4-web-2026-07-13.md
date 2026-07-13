# UTETY — Audit of Phase 1 bite 4: the student reading room (`utety/web`)

*2026-07-13 · covers PR #5 (`4b1624a`, merged as `0165142`) — `utety/web/render.py`,
`utety/web/server.py`, `tests/test_web.py` (+572 lines).*
*Method: full read; suite executed; every finding below reproduced with a concrete
request before filing. Companion to `docs/full-audit-2026-07-13.md`.*

## Headline

The architecture is right: routing is a pure function (fully testable without a
socket), rendering is pure string functions, every interpolated value goes through
`html.escape`, the answer key never reaches the HTML (finding B1 from the first
audit is resolved *by design* here — the front is server-rendered, so `Item`
never leaves the process), and the offline citation fallback keeps Rule 1 intact.
The playthrough test drives the real router to completion.

The defects are at the *edges* the tests didn't reach: what a child's stray click
sends, what a hostile web page can send, and what a hostile knowledge backend can
return. Four confirmed, plus one deliberate policy event.

## The policy tripwire fired (working as designed)

`tests/test_boundaries.py::TestSeamIsTheOnlyDoor` failed on the rebase:
`web/server.py` imports `http`/`urllib` and is not allowlisted. This is the
review the test exists to force. **Audit verdict: legitimate.** The imports are
`http.server` (a *listener*, not a client) and `urllib.parse` (string parsing);
the server binds loopback by default and is the local-first posture's delivery
mechanism, not an egress path. Resolution shipped with this audit:
`web/server.py` added to the allowlist with justification, **plus a new policy
test pinning `serve()`'s default bind to `127.0.0.1`** — changing it to
`0.0.0.0` (exposing a child's tutor to the LAN) now fails CI.

## Confirmed defects

### W1 · A stray click poisons the mastery signal — or dead-ends the child
**Reproduced both ways.** A child clicking **Check** without selecting anything:

- **single/text/multi item:** the empty response reaches `sess.answer` and is
  graded — a **wrong outcome is recorded into BKT** (`outcome_history` gains a
  `0`). Mastery drops, item selection recalibrates, the disclosure log records
  an answer the child never gave. Same defect class as A2 (noise in the signal),
  arriving through the UI instead of the grader.
- **boolean item:** the empty string now (correctly, post-A2) raises
  `ValueError` — but the router turns it into a **500** whose error fragment has
  **no button**: the JS island swaps it into `#stage` and the child is stranded
  on "Something went quiet in the back shelves" with nothing to click. Recovery
  requires a full page reload — a lot to ask of a nine-year-old.

**Fix:** treat an empty/malformed response as "not an answer": re-present the
item (200, no outcome recorded), and give the 500 fragment a
"try again" button as a backstop. `required` on the radio inputs helps but is
front-only; the router must not grade absence.

### W2 · No Host-header check, no CSRF defense — a remote page can reach the tutor
**Confirmed by code read** (`serve()`'s handler never inspects `Host`; the
router accepts any form-encoded POST). Binding 127.0.0.1 stops direct remote
connections, but not a browser on the same device:

- **DNS rebinding:** a page the child visits resolves its own domain to
  `127.0.0.1` and can then **read** responses from the tutor (progress,
  step content) and **write** (acknowledge experiences, submit answers,
  pollute mastery) — same-origin from the browser's point of view.
- **Plain CSRF:** cross-origin form POSTs to localhost need no preflight, so a
  malicious page can blind-fire `/step` and `/answer` even without rebinding.

For a product whose whole promise is "student data stays on this device," the
data being readable by any web page the child opens is the finding.
**Fix (small):** reject requests whose `Host` is not `127.0.0.1:<port>` /
`localhost:<port>` (kills rebinding); add a per-session token embedded in the
page shell and required on POSTs (kills blind CSRF). Both fit the stdlib server.

### W3 · A hostile knowledge backend can inject `javascript:` links
**Reproduced:** `card_html(SourcedCard(url="javascript:alert(1)", ...))` renders
a clickable `href="javascript:alert(1)"` — `html.escape` neutralizes markup but
not URL *schemes*. Sourced cards are external input (the seam's whole point);
a compromised or MITM'd backend gets script execution in the reading room, whose
origin holds the disclosure UI. **Fix:** render the link only when the URL
starts with `https://` (matching the transport's own rule); otherwise show the
source name unlinked. One `if`.

### W4 · `GET /` has side effects; sessions grow unbounded
**Reproduced:** `GET /?learner=anything` **creates a learner row** — a mutating
GET, and (combined with W2) a way for a hostile page to spray junk learners into
a child's store. `App._sessions` also grows one entry per distinct learner id,
unbounded. **Fix:** only `POST` may create; `GET /` for an unknown learner
should 404 (or render a neutral shell), and creation should move behind an
explicit action. (Proper identity is Phase 2's consent work; this just stops
drive-by writes.)

## Smaller notes

- The 500 fragment leaks the exception class name in an HTML comment
  (`<!-- ValueError -->`). Harmless today; drop it anyway — error taxonomy is
  operator information, and the disclosure log is where diagnostics belong.
- `serve()`'s docstring says "Blocks in serve_forever" but it *returns* the
  server; the caller blocks. Fix the docstring.
- Gate violations (`answer` before ack) surface as 500s; 4xx is the honest
  status and keeps real 500s meaningful.
- No `Content-Security-Policy` / `X-Content-Type-Options` headers. A one-line
  CSP (`default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'`
  or hash-based) would also blunt W3-class issues by policy.
- The consent field still gates nothing — a learner with `consent_status =
  'revoked'` gets tutored like any other. Phase 2 owns the real flow; noting it
  here so the student-facing surface's launch checklist has it. (Build-plan
  ground rule 4.)
- `_cards_for` swallows every seam exception silently. Falling back to the
  local citation is right; logging *nothing* about a failing/misbehaving
  backend hides exactly the events a parent-facing disclosure spine would want.

## What bite 4 got right

- **Pure router + pure renderers** — the 100-test suite drives the entire flow
  with no socket; this is the most testable shape a web layer can take.
- **Escaping discipline** — every interpolation is escaped at the point of use;
  the confirmed injection (W3) is a scheme problem, not an escaping lapse.
- **The answer key stays server-side** — first audit's B1 resolved by
  architecture rather than by care.
- **Rule 1 held under failure** — no seam, seam error, empty cards: the child
  still sees a sourced citation (and the tests prove the fallback).
- **Loopback default, quiet logs, persona server-side** — the right defaults
  for a child's device.

## Verdict

| Finding | Severity | Class |
|---|---|---|
| W1 · empty response graded / dead-end 500 | **High** (core signal integrity + child UX) | correctness |
| W2 · no Host check / no CSRF token | **High** (local-first privacy promise) | security |
| W3 · `javascript:` card links | Medium (needs hostile backend) | security |
| W4 · mutating GET, unbounded sessions | Low-medium | hardening |
| policy trip: `web/server.py` allowlisted + loopback pin | resolved with this audit | boundary |

Recommended order: W1 and W2 before this front meets a real child; W3 is one
line alongside; W4 rides the same diff. The CI growth plan (docs/ci.md) already
reserved a phase-1-front row: with this bite landed, its checks are W1's
"absence is never graded" test, the loopback pin (shipped now), and a
router-level test that no response ever contains an item's answer or feedback
for unanswered items.

*Filed after rebasing `claude/full-audit-kqozzy` onto `0165142`. The tripwire
test caught the boundary change on first contact — the gate is doing its job.*

## Outcome (same day)

W1–W4 fixed on this branch, with 13 regression tests, and verified end-to-end
over a real socket (shell → token → step → 403s for missing token and foreign
Host). Fix highlights: empty responses re-present with a nudge (nothing reaches
BKT); malformed/out-of-order answers fall back to the learner's real next step;
per-run CSRF token embedded in the shell and required (case-insensitively) on
every POST; Host allowlist in the HTTP adapter; card links render only for
`https://` URLs; `GET /` is side-effect free; learner ids validated
(`[A-Za-z0-9._-]{1,64}`); sessions capped; the error card carries a
"Keep going" button and no exception taxonomy. Still open from the smaller
notes: seam-failure visibility (deliberately suppressed, marked in code) and
the consent gate (Phase 2).
