# UTETY — Full Repository Audit

*2026-07-13 · covers everything on `main` as of `e90a8aa` (Phase 1 bites 1–3 merged).*
*Method: every source and test file read in full; the suite executed; each suspected
defect reproduced with a concrete input before being filed. Nothing below is speculative —
items marked **CONFIRMED** were demonstrated running.*

## Scope

| Layer | Files | Verdict at a glance |
|---|---|---|
| Local-first core | `utety/core/store.py`, `mastery.py`, `loop.py` | Sound design; 2 confirmed defects (one latent, one in the guarantee test) |
| Content layer | `utety/content/model.py`, `register.py`, `courses/neva_and_theo.py` | 2 confirmed defects (grading, serialization) |
| Knowledge seam | `utety/knowledge.py` | Structural privacy holds; 2 hardening gaps |
| Tests | `tests/` (77 tests) | Good coverage; **suite is RED on Python 3.11** (1 failure) |
| Repo hygiene | — | No CI, no code license, no packaging metadata |

**Headline:** the architecture does what the build plan promised — the privacy controls are
genuinely structural, the BKT math checks out against hand computation, and the
hands-before-vocabulary gate is enforced in both the selection and the answer path. The
defects found are real but contained: one failing test, one grading hole that inflates
mastery, and a set of contract/hardening gaps listed by severity below.

---

## A. Confirmed defects (each reproduced)

### A1 · The no-egress guarantee test fails on Python 3.11/3.12 — suite is red
`tests/test_no_egress.py::test_importing_store_does_not_load_network_modules` — **CONFIRMED**
(ran the suite: 77 tests, 1 failure).

The subprocess check asserts that importing `utety.core.store` pulls no member of
`{socket, ssl, urllib, http, ...}` into `sys.modules`. On Python 3.11 (and 3.12), the
stdlib's `pathlib` imports `urllib.parse` at module level (for `Path.as_uri`), so the check
trips on `urllib` — imported by the *standard library*, not by the core. Python 3.13+ made
that import lazy, which is why the test passed when written.

- `urllib.parse` is pure string manipulation; it cannot move bytes. The network-capable
  member is `urllib.request`.
- **Fix:** test at full-module granularity — forbid `urllib.request`, `urllib.error`,
  `http.client`, `socket`, `ssl` in `sys.modules` rather than the top-level `urllib`/`http`
  names. (The AST-scan half of the test is fine as-is: it checks what *core* imports,
  and core imports neither `urllib` nor `pathlib`... it does import `pathlib`, but the AST
  scan correctly doesn't treat that as a network import.)
- Until fixed, any contributor on 3.11/3.12 sees the load-bearing test fail and may be
  trained to ignore it — the worst outcome for a tripwire.

### A2 · Boolean items grade arbitrary garbage as "false" — mastery inflates on noise
`utety/content/model.py::_coerce_bool` — **CONFIRMED**:

```python
Item("ip2", "s", "boolean", "...", answer=False).check("banana")  # → True
```

`_coerce_bool` returns `True` only for `{"true","t","yes","y","1"}` and `False` for
*everything else* — including nonsense. Every boolean item whose answer is `False`
(the live course's `ip2` is one) therefore scores any unrecognized response as **correct**,
feeds a spurious `correct=1` into `record_outcome`, and BKT mastery climbs on noise. It
also selects the `feedback_correct` branch, so the learner is told they were right.

**Fix:** recognize an explicit false-set (`"false","f","no","n","0"`) and treat anything
outside both sets as an invalid response (raise, or return incorrect-with-default-feedback —
raising is better; a UI should never submit free text to a boolean item).
Relatedly, `check()` for `multi` called with a string (`check("arm")`) silently iterates
characters into `{'a','r','m'}` — a type guard on `multi`/`boolean` responses closes both.

### A3 · `Course.to_dict()` is not JSON-serializable, contradicting its contract
`utety/content/model.py` — **CONFIRMED**: `json.dumps(build_neva_and_theo().to_dict())`
raises `TypeError: Object of type set is not JSON serializable`.

The module docstring promises "JSON-serializable (`to_dict`/`from_dict`) so content can
move to a data file later." A `multi` item's `answer` is a `set` and `asdict` preserves it.
The round-trip test passes only because it never crosses JSON.

**Fix:** in `to_dict`, convert set answers to sorted lists (`from_dict`/`check` already
handle lists — `set(response) == set(self.answer)` is type-agnostic). Add a test that
actually round-trips through `json.dumps`/`loads`.

### A4 · The seam's PII backstop is an `assert` — it vanishes under `python -O`
`utety/knowledge.py::KnowledgeSeam.back` — **CONFIRMED**: ran a scrubber-failure
simulation under `-O`; the payload was sent with no guard fired.

The belt-and-suspenders check (`assert not contains_pii(clean)`) is compiled out when
Python runs optimized. The *primary* control (no learner in scope of the send path) still
holds, but the documented defense-in-depth silently isn't there in `-O` deployments.

**Fix:** replace with a real exception (`raise RuntimeError(...)` / a `SeamError`).
Security controls must never live in `assert`.

### A5 · Latent: the loop reports a false "complete" when the selected skill has no items
`utety/core/loop.py::next_step` — **CONFIRMED** with a two-skill course where one skill
has no items: `next_step().kind == "complete"` while `is_complete() == False`.

`next_step` picks the single least-practised unmastered skill; if that skill yields no
gate-eligible items, it returns `Step(kind="complete")` even when *other* unmastered
skills still have practice available. Because an item-less skill has zero opportunities,
it is selected forever — the session wedges into a false "complete" on the first call.
Latent today (every skill in the live course has items) but it will bite the moment a
course ships a skill before its items, and nothing in `Course._validate` prevents that.

**Fix (either or both):** on empty selection, fall through to the next unmastered skill
instead of completing; and/or make `Course._validate` reject a skill with no items.

---

## B. Design and hardening gaps (not yet exploited, worth closing)

### B1 · `Step` hands the front the raw `Item` — including the answer
`Presentation` is carefully answer-free (`answer_hidden=True`), but `Step.item` carries the
full `Item` with `answer`, `feedback`, and every wrong-answer explanation alongside it. The
retrieval-practice guarantee ("answer HIDDEN") currently holds only if the front is polite.
A front that naively serializes `Step` into a web page ships the answer key to the student.
**Recommend:** the loop's public step should expose `Presentation` (plus experience text)
only; keep `Item` internal, keyed by id at `answer()` time.

### B2 · Consent transitions are mutable and unlogged
`set_consent` is a plain `UPDATE`: no history, no entry in the tamper-evident disclosure
chain, and a `revoked` transition **nulls `consent_at`**, erasing when anything happened.
For the one COPPA-relevant state in the store, transitions should be (a) timestamped in
all states, and (b) appended to the disclosure chain (`kind="consent_changed"`), so the
Phase-2 age-gate has an auditable trail to enforce against.

### B3 · The no-egress claim is broader than the check
README/docstrings say there is "no code path by which student PII can leave the device."
The enforcement is an import tripwire: `_FORBIDDEN` covers network libraries but not
`subprocess`, `os` (`os.system`), or `ctypes` — any of which can move bytes. The core
doesn't use them today, so the *fact* is true; the *guarantee* is narrower than the prose.
**Recommend:** add `subprocess`/`ctypes` to the core's forbidden AST set (core has no
legitimate use for either) and soften the prose to "no network imports, enforced by test."

### B4 · Disclosure chain: tail truncation is undetectable
Hash-chaining detects edits and mid-chain deletions, but deleting the *newest* rows leaves
a chain that still verifies. Classic fix within the local-first constraint: persist the
current head hash (and count) into `meta` on every append; `verify_disclosure_chain`
then also checks the stored head matches the last row. (An on-device attacker can rewrite
`meta` too, but it raises the bar from "DELETE one row" to "rewrite the anchor coherently,"
and gives the Phase-3 teacher view an anchor to export.)

### B5 · Transport does not require HTTPS
`_http_transport` posts to whatever `WILLOW_UTETY_KNOWLEDGE_URL` says, attaching
`X-Utety-Secret`. An `http://` value (typo or hostile env) sends the app secret and the
query in cleartext. **Recommend:** refuse non-`https` schemes in the transport (allow an
explicit localhost exception for development if needed).

### B6 · Smaller items
- `register_course` skips existing skills, so **updated BKT params never propagate** to a
  store that registered an older course version — silent drift once upstream ships fitted
  params. Consider comparing and updating params (they are content, not learner state).
- `add_learner`/`add_skill` leak raw `sqlite3.IntegrityError` on duplicates instead of
  `StoreError` — inconsistent with the store's own error contract.
- `meta.schema_version` is written but never read: opening a future-versioned DB proceeds
  blindly. Check it on open; refuse or migrate on mismatch.
- Two `Store` instances on the same file can interleave `log_disclosure`'s
  read-prev-hash → insert; the explicit-`seq` insert makes the loser fail with an
  `IntegrityError` (safe, but ugly). Single-owner is the documented posture; fine for now.
- `deidentify` can't catch *names* (the highest-value child PII). The structural control —
  queries are authored content constants — is what actually protects this; keep authored
  `source_query` strings as the only thing that crosses, and keep saying so in review.

---

## C. Repo hygiene

- **No CI.** The suite is 77 tests and runs in ~0.1 s, but nothing runs it. A1 would have
  been caught the day the repo met a 3.11 runner. Add a GitHub Actions workflow running
  `python -m unittest discover -s tests` across 3.11–3.13 (three interpreter versions ×
  0.1 s is free; the version matrix is exactly what A1 needed).
- **No code license.** The course *content* declares CC BY 4.0 (inherited from the lesson),
  but the repository's *code* has no license file at all. Unlicensed code defaults to
  all-rights-reserved, which contradicts the project's reuse posture. Add a LICENSE.
- **No packaging metadata** (`pyproject.toml`). Fine for the current stdlib-only slice;
  becomes necessary the moment anything (the student front, willow-mcp) needs to
  `pip install` this. Note only.

## D. What the audit found *right* (kept short, but earned)

- **The structural-privacy idea survives inspection.** `KnowledgeSeam.back(query: str)`
  really has no learner in scope; the store really imports no network module; the
  quarantine of the egress path outside `utety/core` is real, and the tests prove the
  interesting halves of it (signature check, payload-shape check, end-to-end clean-payload
  check).
- **The BKT implementation is correct.** Posterior and learning-step verified against the
  hand-computed value in `test_mastery.py` (which itself checks to 10 decimal places);
  identifiability caps on guess/slip are enforced at the dataclass boundary.
- **Gating is enforced twice** — in selection (`next_step` won't surface a gated item) and
  in the answer path (`answer()` refuses an item whose experience isn't acknowledged) — so
  a misbehaving front can't skip hands-before-vocabulary.
- **Feedback discipline is linted, not just promised** (`test_no_self_directed_praise`),
  and the live course's feedback is uniformly task-focused and error-specific.
- **Tamper-evidence works for its designed threat**: edits and mid-chain deletions are
  caught (proved by test); B4 above is the one uncovered edge.

## E. Plan conformance (build-plan §4, Phase 1)

| Planned | Status |
|---|---|
| Content layer (bite 1) | ✅ shipped, validated, tested |
| Core learning loop (bite 2) | ✅ shipped (A5 latent edge) |
| Knowledge seam (bite 3) | ✅ shipped (A4/B5 hardening) |
| **Spaced review (FSRS)** | ❌ **not present** — §2's "schedule spaced review" step has no implementation or stub yet; the loop is pure mastery-driven selection. Flagging so it doesn't silently drop out of Phase 1. |
| Student front (htmx) | not started (expected; B1 should be fixed before it starts) |
| Consent *enforcement* | Phase 2 by design; B2 should land first so the gate has a trail |

## F. Recommended order of work

1. **A1** — fix the egress test's granularity (unbreaks the suite everywhere) and add CI with a 3.11–3.13 matrix.
2. **A2** — close the boolean grading hole (it corrupts the mastery signal, the product's core).
3. **A4 + B5** — one small hardening pass on the seam (raise instead of assert; require https).
4. **A5 + B1** — loop correctness edge + stop exporting the answer key; both are cheap now and expensive after a front exists.
5. **A3, B2, B3, B4, B6, license** — batch as a cleanup bite.

*Filed as `docs/full-audit-2026-07-13.md`. Five confirmed defects, none architectural;
the load-bearing ideas held. The mountain is, once again, a punch-list.*

## Outcome (same day, on this branch)

- **A1–A5**: all fixed with regression tests (A1 with the CI matrix that would
  have caught it; A2 also hardened at the web layer — see the bite-4 audit).
- **B1**: resolved by bite 4's architecture (server-side rendering; the answer
  key never leaves the process).
- **B2**: consent transitions timestamped in every state and appended to the
  tamper-evident disclosure chain (`kind="consent_changed"`).
- **B3**: prose aligned with enforcement; `subprocess`/`ctypes` added to both
  the core scan and the package-wide boundary test.
- **B4**: chain head anchored in `meta` on every append; tail truncation now
  fails `verify_disclosure_chain` (proved by test).
- **B5**: transport refuses non-https endpoints.
- **B6**: duplicate learner/skill raise `StoreError`; newer-schema stores are
  refused on open; `register_course` propagates re-fitted BKT params (content,
  not learner state).
- **Open**: code LICENSE (project decision for Sean); FSRS spaced review
  (Phase-1 feature work, not a defect); Phase-2 consent *enforcement*.
