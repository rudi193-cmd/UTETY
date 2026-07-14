# UTETY — Independent full-scope re-audit (second auditor)

*2026-07-14 · tree at `674d40f` (post-merge of PR #6). Performed by an
independent auditor (read-only mandate: findings and proposed fixes only, no
edits) with instructions to re-verify the prior audits' fixes by reproduction
rather than trusting their outcome sections, and to hunt for what they missed.
Report reproduced below essentially verbatim.*

---

## Verdict

The tree at `674d40f` is in good shape and the prior audits' fixes hold up
under re-verification: A1–A5, B2–B6, and W1–W4 were regression-checked by
reproduction (not by trusting the docs) and **every one is genuinely fixed** —
the BKT math is sound across extreme params and division guards, the
structural privacy of the seam is real (the learner is not in scope of
`back()`, and a learner's free-text answer is never the thing sent — only the
item's authored `source_query`), the disclosure chain catches edits, mid-chain
deletion, and tail truncation, and every HTML sink is escaped with the
`javascript:`-scheme hole closed. What the prior audits **missed** is narrower
and mostly below the waterline: one genuine data-integrity defect
(`record_outcome` is documented "Transactional" but is not, and a mid-sequence
SQLite failure permanently desyncs the append-only outcome log from mastery),
a test-coverage blind spot over the entire security-critical socket adapter
(the W2 Host check, Content-Length parsing, and B5's https-refusal have *no*
automated test and only work by manual verification), and a cluster of
low-severity hardening gaps. Nothing is architectural; nothing rises to high.

## Findings (ranked)

| # | Severity | File:line | Class | Status |
|---|---|---|---|---|
| F1 | Medium | `utety/core/store.py:273, 295–309` | Correctness / durability | CONFIRMED |
| F2 | Medium | `utety/web/server.py:175–215`; `utety/knowledge.py:89–106` | Test quality / regression risk | CONFIRMED |
| F3 | Low | `utety/web/server.py:118–138` | Correctness (signal integrity) | CONFIRMED |
| F4 | Low | `utety/web/server.py:193` | Robustness (DoS / malformed HTTP) | CONFIRMED (primitive); SUSPECTED (live hang) |
| F5 | Low | `utety/core/store.py:212–221`; `utety/core/loop.py:201–216` | Robustness (cross-method atomicity) | SUSPECTED |
| N1–N5 | Nit | various | — | mixed |

---

## F1 — `record_outcome` is not transactional; a mid-sequence failure desyncs the outcome log from mastery (Medium, CONFIRMED)

**Anchor.** `utety/core/store.py:273` (docstring: *"Transactional: writes the
append-only outcome row … applies one BKT `update` … and upserts the new
mastery state"*) vs. the body.

**Evidence.** `record_outcome` executes the `INSERT INTO outcomes …` then the
`INSERT INTO mastery … ON CONFLICT …` then a single `commit()`. There is no
`with self._db:` wrapper and no `rollback()` on failure. Python's `sqlite3`
(default `isolation_level=""`) opens an implicit transaction on the first DML
and **does not auto-roll-back on an exception** — the pending write stays live
on the connection and is flushed by the *next* `commit()` anywhere in the
process.

**Repro** (mastery UPSERT forced to raise as a "disk full / database is
locked" would):

```
record_outcome raised as expected: simulated disk/lock failure mid-record_outcome
outcome_history right after failure (uncommitted): [1]
outcome_history AFTER unrelated later commit: [1]      <- phantom, now durable
mastery row: None                                       <- never updated
```

The outcome row (`[1]`) becomes permanent when a later unrelated
`log_disclosure` commits, but the mastery row was never written. The
append-only ground truth BKT traces over now diverges permanently from the
mastery state (`opportunities`/`p_known` are off by one relative to
`outcome_history`, forever).

**Scope check (verified, not assumed).** The same partial-write pattern
against `log_disclosure` is **self-healing** — the disclosure row carries its
own `prev_hash`+`hash`, so a lagged `meta` anchor is repaired by the next
append and the chain still verifies. So the defect is specific to
`record_outcome`, where the outcome row and mastery row are a *semantically
paired* write. `set_consent` is a separate concern (F5).

**Realistic trigger.** `sqlite3.OperationalError: database is locked` (a
second `Store` handle or an external reader/writer on the same file — the
documented single-owner posture is a convention, not enforced) and
`disk I/O error` / `database or disk is full` on a child's device. The first
INSERT takes the write lock and succeeds; a page-allocation failure on the
second surfaces exactly this.

**Proposed fix.** Wrap the paired write in a transaction that rolls back
atomically:

```python
try:
    with self._db:  # commits on success, rolls back on any exception
        self._db.execute("INSERT INTO outcomes(...) VALUES(...)", (...))
        self._db.execute("INSERT INTO mastery(...) VALUES(...) ON CONFLICT(...) DO UPDATE ...", (...))
except sqlite3.Error as exc:
    raise StoreError("record_outcome failed; no partial write committed") from exc
return p_new
```

Do the same for `log_disclosure` (defensive, even though currently
self-healing) and audit every method that issues >1 `execute` before
`commit()`.

---

## F2 — The security-critical socket adapter and B5's https-refusal have zero automated coverage (Medium, CONFIRMED)

**Anchor.** `utety/web/server.py:175–215` (`serve()` + the `Handler` class)
and `utety/knowledge.py:89–106` (`_http_transport`).

**Evidence.** `python -m coverage report -m` shows `web/server.py` lines
**178–215 missing** and `knowledge.py` lines **97–106 missing**. That is the
*entire* real-socket path: the W2 DNS-rebinding **Host check**, Content-Length
parsing, body read/decode, and status/header writing — none of it is exercised
by any test. The suite tests the pure `App.handle()` router and the *isolated
helpers* `_allowed_hosts`/`_host_ok`, but never asserts that the `Handler`
actually calls them or returns 403 for a foreign Host. Likewise B5's
`if not url.startswith("https://"): raise` has **no test** — the audit docs say
the socket flow was "verified end-to-end over a real socket" *manually*, but
nothing pins it.

**Consequence.** A future edit that drops the Host check, mis-parses
Content-Length, or relaxes the https guard passes CI green — the coverage
floor (90%, currently 91%) already tolerates these lines being uncovered, so
the gate cannot catch a regression in code it never runs. Spot-check confirms
the code *currently works*: B5 refuses `http://`, `ftp://`, and even
`HTTPS://` (case-sensitive), and the seam-failure path falls back to the local
citation. But "works today, untested" is exactly the A1-class trap the CI
section of the repo warns against.

**Proposed fix.** Add three regression tests:

1. Drive `serve()`'s `Handler` over a real loopback socket: assert a request
   with `Host: attacker.example` → 403, a valid `Host` → 200, and that a POST
   body of a given `Content-Length` is read intact.
2. `test_http_transport_refuses_non_https` — assert
   `_http_transport("http://x/search", {...})` raises `RuntimeError`
   (pins B5).
3. `test_seam_failure_falls_back_to_local_citation` — a seam whose transport
   raises still yields a card carrying `result.citation` (pins Rule 1 under
   backend failure; the current `test_offline_source_falls_back_to_citation`
   only covers `seam=None`, not `seam.back()` raising).

Consider adding `--branch` to the coverage job (currently line-only) so
untested branches inside covered lines also count against the floor.

---

## F3 — Out-of-set choice values are graded as wrong outcomes (Low, CONFIRMED)

**Anchor.** `utety/web/server.py:118–138` (`_answer`) →
`LessonSession.answer` → `Item.check`.

**Evidence.** W1/A2 established the principle "never feed a non-answer into
the mastery signal," but the fix only covers *empty* responses. A non-empty
value that isn't a valid choice id is still graded:

```
invalid-single-choice status: 200 outcome_history: [0]   # "response=ZZZ_not_a_choice" recorded as WRONG
invalid-multi   status: 200 outcome_history: [0]          # "response=nonsense1&nonsense2" recorded as WRONG
```

For `single`/`multi`, a value outside `item.choices` is indistinguishable from
a real wrong-distractor pick, so it lands as `correct=0` in BKT and the
disclosure log — the same signal-poisoning class as W1, arriving through
invalid rather than absent input.

**Reachability (why Low).** State-changing POSTs require the per-run CSRF
token, which only same-origin script can read (Host check blocks rebinding, no
CORS is granted), so a hostile remote page cannot reach this — only a buggy
front or a local process (which already owns the device). The legitimate JS
island only submits real radio/checkbox values.

**Proposed fix.** In `_answer`, validate membership before grading and treat
non-members as a non-answer (re-present, like the empty case). Text items have
no `choices`, so skip them:

```python
if item.kind in ("single", "multi"):
    valid = set(item.choices)
    picked = set(response) if item.kind == "multi" else {response}
    if not picked <= valid:                      # out-of-set value → not a real answer
        return 200, _HTML, render.item_fragment(
            sess.present(item_id), item, learner,
            nudge="Pick one of the options first — then Check.")
```

---

## F4 — Malformed / negative `Content-Length` is unhandled in the socket adapter (Low; primitive CONFIRMED, live-hang SUSPECTED)

**Anchor.** `utety/web/server.py:193` —
`length = int(self.headers.get("Content-Length", 0) or 0)` then
`self.rfile.read(length)`, both **before** and **outside** the `try` in
`App.handle`.

**Evidence.** Confirmed primitives: `int("abc")` raises `ValueError`;
`int("-5") == -5`; `BufferedReader.read(-5)` reads until EOF. So:

- A non-numeric `Content-Length` raises in `_dispatch` (not wrapped) → the
  exception escapes `do_POST`; `socketserver.handle_error` prints a traceback
  to stderr and drops the connection. The server survives, but the child sees
  a failed request and the operator gets noise.
- A **negative** `Content-Length` makes `rfile.read(-n)` block until EOF.
  Because `HTTPServer` is single-threaded, a client that sends
  `Content-Length: -1` and holds the socket open stalls the whole reading room
  (classic Slowloris-shaped hang). Marked SUSPECTED for the live hang: the
  read primitive is confirmed but no socket was stood up to hold it open, and
  reachability is limited — a browser cannot set a negative/invalid
  Content-Length, so the actor is a local process (already privileged) rather
  than the hostile-page threat model.

**Proposed fix.** Parse defensively and cap the body:

```python
try:
    length = int(self.headers.get("Content-Length", 0) or 0)
except ValueError:
    length = -1
if length < 0 or length > _MAX_BODY:           # e.g. _MAX_BODY = 64 * 1024
    self.send_response(400); self.end_headers(); return
body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
```

---

## F5 — Cross-method writes are non-atomic (consent/answer ↔ disclosure) (Low, SUSPECTED)

**Anchor.** `set_consent` (`store.py`): `UPDATE learners …` + `commit()`, then
a *separate* `log_disclosure()` with its own commit. Same shape in
`LessonSession.answer` (`loop.py`): `record_outcome()` commits, then
`log_disclosure()` commits separately.

**Evidence / reasoning.** These are two independent transactions. A crash (or
the F1-class failure) between them leaves the state change durable but the
paired tamper-evident disclosure entry missing. The B2 fix's guarantee —
*"every transition … appended to the tamper-evident disclosure chain"* — then
quietly does not hold for that one transition, and `verify_disclosure_chain()`
still returns `True` (the chain is internally consistent; it just
under-counts). SUSPECTED because it requires crash timing; reproducing would
need a process kill between the two commits.

**Proposed fix.** Fold the state change and its disclosure append into one
transaction (single `with self._db:` spanning both the `UPDATE`/outcome write
and the disclosure-row insert), so either both land or neither does.

---

## Regression re-check of prior audits (spot-checked by reproduction, not trusted)

All still fixed:

- **A1** (egress-test granularity): suite green on 3.11 incl. `test_no_egress`;
  the subprocess check forbids full module names (`urllib.request`, not
  `urllib`). ✓
- **A2** (boolean garbage): `Item(answer=False).check("banana")` raises
  `ValueError`; the loop records no outcome. ✓
- **A3** (JSON round-trip): `json.dumps(build_neva_and_theo().to_dict())`
  succeeds; multi `set` answers become sorted lists and `check` stays
  set-wise. ✓
- **A4** (assert→raise): the seam guard is a real `raise`; no bare `assert` in
  `utety/`; full suite passes under `python -O`. ✓
- **A5** (false complete): `Course._validate` rejects item-less skills;
  `next_step` falls through the whole preference order. ✓
- **B2** (consent chained): `set_consent` appends `consent_changed`; timestamp
  kept on revocation. ✓
- **B3** (`subprocess`/`ctypes`): present in both `_FORBIDDEN` and
  `_NETWORK`. ✓
- **B4** (tail truncation): anchored head in `meta`; independently confirmed
  deletion of the newest row, of a middle row, of the first row, and of all
  rows are each detected, and the empty-no-anchor case verifies. ✓
- **B5** (https transport): `_http_transport` refuses
  `http://`/`ftp://`/`HTTPS://` — works, but **untested** (see F2).
  ✓ (functionally)
- **B6** (dup→StoreError, newer-schema refused, param propagation): all
  present and tested. ✓
- **W1** (absence never graded): empty single/boolean/multi re-present with no
  outcome. ✓ (but see F3 — invalid non-empty still graded)
- **W2** (CSRF + Host): CSRF enforced in `handle()` for all POSTs; Host
  enforced in the socket `Handler`. ✓ (Host wiring **untested** — F2)
- **W3** (`javascript:` links): only `https://` URLs become links; confirmed
  unlinked for `javascript:`/`http:`/`data:`. ✓
- **W4** (mutating GET, unbounded sessions): `GET /` is side-effect-free;
  learners bounded by `_LEARNER_RE`; sessions capped at 64. ✓

## Nits

- **N1** — 500 fragment: `learner` is interpolated **unescaped** into
  `data-post="/step?learner={learner}"`. Not exploitable — `_LEARNER_RE`
  (`^[A-Za-z0-9._-]{1,64}$`) is checked before any exception can reach the
  handler, so no HTML metacharacters can arrive — but it is the one unescaped
  sink; escape it for defense-in-depth.
- **N2** — CSRF compared with `!=` (not `secrets.compare_digest`). Negligible
  over loopback with a per-run secret; use a constant-time compare anyway.
- **N3** — `SourcedCard.from_dict` / `back()` don't guard non-dict cards from
  a hostile backend — `{"cards": ["evil", 123]}` raises `AttributeError`
  inside `back()`. Caught by the web layer's blanket `except`, but any direct
  caller would see it; guard with `isinstance(c, dict)`.
- **N4** — Coverage gate is line-only (no `--branch`), so untested branches
  inside covered lines don't count against the 90% floor.
- **N5** — The store is unencrypted at rest by design (local-first); the
  disclosure chain is tamper-*evident*, not tamper-*proof* (an on-device
  attacker who rewrites both a row and the `meta` anchor coherently defeats
  it — already acknowledged as the accepted threat model). Worth keeping
  stated in the eventual teacher-view/export spec.

---

*Filed by the session steward on the independent auditor's behalf; the
auditor's mandate was read-only and no repository file was modified during
the audit itself.*
