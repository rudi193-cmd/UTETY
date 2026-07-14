# UTETY — Final-loop audit (fifth pass, second independent auditor)

*2026-07-14 · tree at `5d4b2d1` (post F/N fix batch). Independent read-only
pass with the priority target on the newest, never-audited code: the
transaction manager, the reworked socket handler, and the failure-injection
tests themselves. Report reproduced essentially verbatim; outcome appended.*

---

## Verdict

The tree at `5d4b2d1` is in strong shape and the auditor could not break the
core invariants. Every module read in full; suite green on Python
3.11/3.12/3.13 and under `python -O` (135 passed each); the transaction
manager's exception/nesting/BEGIN-failure paths reproduced directly; ruff and
the 90% branch-coverage floor pass (94%). The new `Store.transaction()` is
correct for every actual call path — depth bookkeeping stays balanced on
nested exceptions, a failing `BEGIN IMMEDIATE` leaves no dangling transaction
and correct depth, and a `StoreError` from `record_outcome` nested inside
`loop.answer()`'s outer transaction rolls back *both* the outcome and the
disclosure write (verified by failure injection). F1–F5 and N1–N4 are all
genuinely fixed and test-pinned. The one real gap is at the **commit
boundary**: a commit-time failure (the realistic `SQLITE_FULL` case — the
exact disk-full scenario F1/F5 targeted) leaves the SQLite transaction *open*,
which bricks the Store handle for all subsequent writes and lets reads briefly
see uncommitted rows. Recoverable (nothing becomes durable; `close()` rolls
back) so it is Low, but a legitimate hole in the F1/F5 robustness story, in
the newest code. Two nits round it out.

## Findings (ranked)

| # | Severity | File:line | Class | Status |
|---|---|---|---|---|
| S1 | Low | `utety/core/store.py` (`transaction()` else-branch) | Robustness / durability at commit boundary | CONFIRMED (repro) |
| S2 | Nit | `utety/core/store.py` (`transaction()` except-branch) | Diagnostics (rollback masks original error) | CONFIRMED (repro) |
| S3 | Nit | `utety/core/store.py` (`transaction()`) | Documented limitation (savepoint-less nesting) | CONFIRMED (repro) |

## S1 — A commit-time failure leaves the transaction open, bricking the Store handle (Low, CONFIRMED)

When `commit()` raises at depth 0 (`sqlite3.OperationalError: database or
disk is full` — commit is precisely when pages flush, so it is the *most*
likely point for disk-full to strike), depth has already been decremented to
0 but SQLite's transaction is never rolled back and remains open. Reproduced:

```
1st record_outcome -> StoreError (as designed)
2nd record_outcome BRICKED: StoreError (cannot start a transaction within a transaction)
outcome_history: [1]   depth: 0        <- phantom visible to reads, not durable
```

Consequences on the same handle: every subsequent write fails (the web
layer's `App` holds one `Store` for its lifetime, so every write-bearing POST
500s until restart), and reads see uncommitted state until `close()` rolls it
back. **Fix:** roll back on commit failure so the handle stays usable and
reads stay consistent; pin with a failure-injection test (a proxy whose
`commit()` raises once) asserting a *following* write succeeds.

## S2 — A failing `rollback()` masks the original business error (Nit, CONFIRMED)

In the `except BaseException` path, `rollback()` runs before `raise`; if
rollback itself raises, the caller sees the rollback error instead of the
original exception. Depth stays correct. **Fix:** suppress the rollback error
so the original propagates.

## S3 — Savepoint-less nesting: a swallowed inner-transaction exception does not roll back the inner writes (Nit, CONFIRMED)

Rollback happens only at depth 0, so a caller that opens an inner
`transaction()`, catches its exception, and *keeps writing in the outer
transaction* commits the inner block's partial writes with the outer. No code
in the repo does this — all current callers propagate — and the docstring
accurately says commit/rollback happen "only at depth zero." **Fix:** a
one-line docstring caution ("a nested block is not independently atomic — do
not catch-and-continue across one") unless SAVEPOINTs are adopted.

## Priority-target sweep (clean)

- **`transaction()`** — nested depth bookkeeping balanced; `BEGIN IMMEDIATE`
  failing at depth 0 leaves no dangling tx and a fresh transaction succeeds;
  `except BaseException` correctly covers `KeyboardInterrupt`/`GeneratorExit`;
  `isolation_level=""` + explicit BEGIN/commit/rollback is version-robust
  across 3.11/3.12/3.13.
- **`loop.answer()`** — nested `StoreError` rolls back outcome *and*
  disclosure (verified by injection); `StoreError` is not `ValueError`, so it
  correctly bypasses `_answer`'s malformed-response fallback and lands in the
  friendly 500.
- **`server.py`** — the `allowed` closure is genuinely race-free
  (`serve_forever()` runs only after `serve()` returns with `allowed`
  assigned); F3 validation cannot be dodged (set-wise membership; duplicates
  collapse; boolean/text guarded downstream); CSRF compare handles any header
  bytes; Content-Length guard ordering is fine; the 500-fragment escape is
  belt-and-suspenders.
- **Tests** — the failure-injection proxy lands failures exactly where
  claimed; no test found that would pass if its fix regressed; the socket
  tests assert status codes off the wire; `setUpClass` uses a real raise
  (survives `-O`).

## Regression spot-check — F1–F5 / N1–N4 all genuinely fixed at `5d4b2d1` ✓

(Each re-verified by reproduction: F1 phantom-rollback, F2 socket/https/seam
pins + `--branch`, F3 out-of-set re-present, F4 Content-Length 400s, F5
atomic pairs, N1 escape, N2 constant-time compare, N3 non-dict cards, N4
branch coverage.)

## Closing nits (no action required)

- `mastery.update()` output is provably in [0,1] without an explicit clamp —
  correct, just implicit.
- An empty-string choice id would be un-gradeable (treated as "absent"); no
  course does this; purely theoretical.
- The seam's best-effort `except Exception` still silently drops backend
  errors — acknowledged in-code, deferred to the disclosure-spine work.

---

## Outcome (same day)

S1 fixed: `transaction()` now rolls back on a commit-time failure, so the
handle survives disk-full and reads never see uncommitted state — pinned by a
failure-injection test (commit raises once; the next write on the same handle
must succeed, which fails against the pre-fix code). S2 fixed: a rollback
failure is suppressed so the original error propagates (pinned by test
asserting the original cause surfaces). S3: docstring caution added. After
five audit passes (three first-party, two independent), the finding curve —
5 confirmed → 4+5 → 5 low/nit → 1 low + 2 nits, severity strictly falling —
says the codebase has converged. The next milestone is a kid and a lever, not
a sixth pass.
