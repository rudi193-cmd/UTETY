# UTETY

**The classroom-grade pedagogy + trust layer.** Local-first, stdlib-only, on-device.

BKT mastery tracking, STEM practice items, and the student-data store — all of it living on the learner's own device. It is the pedagogy engine behind the UTETY campus (utety-chat), built against the settled seam: **UTETY holds the learner and the content; Jeles (the library) holds the
sources.** When the tutor needs to back a claim, it sends the library a
de-identified question about a *concept* and gets sourced cards back. Student
data never crosses off the device.

## Ground rules (non-negotiable, from verified research)

1. **Sourced or it doesn't teach** — every instructional claim carries an inspectable citation.
2. **Feedback is about the work, never the learner** — no "you're smart", no leaderboards.
3. **Local-first by default** — student data stays on-device; any future sync is optional, consented, and explicit.
4. **Verifiable parental consent for under-13** — the age gate is a legal dependency, not a feature.

The full rationale, evidence citations, and build sequence live in
[`docs/build-plan.md`](docs/build-plan.md).

## Layout — the folders encode the architecture

The structure below is load-bearing: the privacy guarantees are *structural*
(enforced by which module is allowed to import what), and the test suite keeps
them that way. Don't move things without reading the notes.

```
utety/
├── core/              The local-first student-data core: SQLite store, BKT
│                      mastery inference, the learning loop, and the consent
│                      backend. ZERO network imports — enforced by
│                      tests/test_no_egress.py (AST scan + subprocess import
│                      check). See utety/core/README.md.
├── knowledge.py       The UTETY→Jeles knowledge seam — the ONE place anything
│                      leaves the device. Deliberately OUTSIDE core/ so the
│                      no-egress guarantee on the store stays absolute. The
│                      send path takes only a concept-query string: student
│                      PII cannot be transmitted because it is not a parameter.
├── content/           The course/skill/item layer: the model, the idempotent
│                      course registrar, and courses/ (the STEM item sets).
├── web/               The on-device student reading room — a stdlib
│                      http.server front with server-side fragments. Routing
│                      is a pure function (App.handle), unit-testable without
│                      a socket.
└── subject_consent/   VENDORED from rudi193-cmd/safe-app-store
                       libs/subject-consent (MIT). Canonical lives upstream;
                       keep this copy in sync. UTETY consumes it through the
                       SQLite backend in utety/core/consent_backend.py.
                       Style-linted and coverage-counted upstream, not here
                       (see pyproject.toml) — but boundary tests here still
                       cover it.

tests/                 Unit tests AND policy tests. test_no_egress.py and
                       test_boundaries.py enforce the privacy architecture;
                       test_content.py lints feedback against self-directed
                       praise (ground rule 2).
docs/                  Research briefs (+ verifications), audits, the build
                       plan, and CI design notes.
```

## Running it

There is nothing to install — UTETY is deliberately **stdlib-only**
(`dependencies = []` in `pyproject.toml`, enforced by
`tests/test_boundaries.py`). Python 3.11+.

```sh
# the test suite (unit + policy tests)
python -m unittest discover -s tests -v

# the same suite with asserts stripped — safety controls must not live in asserts
python -O -m unittest discover -s tests

# the student reading room (on-device)
python -c "from utety.web.server import serve; serve()"
```

CI runs the suite across Python 3.11–3.13 on Linux and Windows (Termux/Windows
parity), plus a pinned ruff correctness + security gate. See
[`docs/ci.md`](docs/ci.md).

## License

Apache License 2.0 — see [`LICENSE`](LICENSE). The vendored
`utety/subject_consent/` package is MIT-licensed from its upstream,
`rudi193-cmd/safe-app-store`.
