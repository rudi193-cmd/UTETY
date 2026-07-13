# UTETY — CI design

*2026-07-13 · why each check exists, and how the gate grows with the project.*
*Prompted by the full audit: five defects reached `main` with a 77-test suite,
because nothing ran it and nothing checked the classes those defects belong to.*

## The principle

Every job in `.github/workflows/ci.yml` exists because a **class** of error was
found (or nearly found) in the 2026-07-13 audit. A CI gate that doesn't map to a
real failure class is theater; a failure class without a gate is a repeat
incident waiting. When a new defect class appears, the response is a new check —
not a longer review checklist.

## The layers

| Layer | Job | Failure class it blocks | Audit evidence |
|---|---|---|---|
| Unit + policy tests | `test` (matrix) | behavior regressions; boundary violations | the 77 existing tests, +3 policy tests |
| Version matrix (3.11/3.12/3.13) | `test` | stdlib behavior drift between Python versions | **A1** — suite was red on 3.11/3.12 for months of commits, green on the author's 3.13 |
| Windows cells | `test` | path/encoding/locale divergence | build-plan ground rule: Termux/Windows parity; `read_text()` without `encoding=` was a live Windows failure |
| `python -O` re-run | `test` | controls that silently vanish when asserts strip | **A4** — the seam's PII backstop was an `assert` |
| Ruff (`F,E,B,S1,S3,S5,S6,RUF`) | `lint` | dead/undefined names, bugbear traps, assert-as-control, injection-shaped code | **A4** again (S101); two dead imports found on first run; S310 forced the https fix (**B5**) |
| Coverage floor (90%) | `coverage` | new modules landing with no tests at all | the audit's confirmed bugs (A2, A3, A5) were all in *untested* behavior |

### The policy tests (the part designed to scale)

Plain unit tests check what code *does*; the policy tests in `tests/` check what
code *is allowed to be*, and they re-apply automatically to every file any
future phase adds:

- **`test_no_egress.py`** — `utety/core` imports no network-capable module
  (AST scan + a subprocess import check at full-module granularity).
- **`test_boundaries.py::TestSeamIsTheOnlyDoor`** — across the *whole* package,
  only the allowlisted seam (`utety/knowledge.py`) may import network/exec
  libraries. Opening a second door requires editing the allowlist in a reviewed
  diff — it cannot happen by accident. This is the structural-privacy claim as
  an executable, growing invariant.
- **`test_boundaries.py::TestStdlibOnly`** — no third-party runtime imports
  anywhere in `utety/`. A new dependency starts life as a failing CI run and a
  conversation, not an import statement.

## Reliability rules (why CI itself can be trusted)

1. **Everything is pinned.** Ruff and coverage are pinned to exact versions; a
   tool release adding new rules must never redden CI. Bumps are deliberate
   PRs that include the diff of new findings.
2. **`fail-fast: false`.** A1 was version-specific; if one red cell cancelled
   the rest, the matrix would hide exactly the signal it exists to produce.
3. **No advisory checks.** Every job is a required gate. A check that can be
   ignored trains people to ignore checks — the audit showed what happens when
   a failing test is normal.
4. **The suite must stay fast.** ~0.16 s today. Policy tests are AST-based (no
   network, no sleeps). Keep it this way; a slow gate gets skipped locally.
5. **Floors ratchet up, never down.** The coverage floor (90) may be raised as
   real coverage rises; lowering it to make a PR pass is the one forbidden move.

## How the gate grows with the build plan

Each phase adds code with a new failure class — so each phase adds its check
*in the same PR as the first code of that phase*:

| Phase (build-plan §4) | New surface | Add to CI |
|---|---|---|
| Phase 1 remainder: FSRS spacing, student front | scheduling math; an htmx surface | property-style tests for the scheduler (monotonicity, bounds); a smoke test that renders each step-kind; **assert the front never receives `Item.answer`** (audit B1) as a policy test |
| Phase 2: age-gate, consent, moderation | legally-load-bearing branching | branch-coverage on the gate module specifically (100%, not 90 — a consent branch with no test is a compliance bug); golden tests for moderation refusals |
| Phase 3: teacher console, disclosure view | rendering of chained records | round-trip test: every disclosure `kind` renders; chain-verification stays green after every new writer |
| Phase 4: LTI/OneRoster/SSO | protocol conformance | contract tests against recorded fixtures; WCAG checks (axe-core) on the web surfaces |
| Any phase | a module that must egress | an entry in `_EGRESS_ALLOWED` + a dedicated test that its payloads pass `contains_pii` — the same pair `knowledge.py` has |

## Running the gate locally

```bash
python -m unittest discover -s tests   # the whole suite, ~0.2 s
python -O -m unittest discover -s tests
pip install ruff==0.15.8 && ruff check .
pip install coverage && python -m coverage run -m unittest discover -s tests \
  && python -m coverage report --include='utety/*' --fail-under=90
```

*Filed with the first green run. The audit found the defects; this is the
machinery that makes their classes unrepresentable on `main`.*
