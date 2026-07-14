# UTETY — What the ground rules don't cover yet (early-stage gaps)

*2026-07-14 · a different kind of audit. The code audits keep answering "is it
built right?" — everything in this file is the other question: "is it the right
thing, and does it survive contact with a family?" Six gaps, ranked by worry,
each with the cheapest honest close.*

---

## 1. No child has touched it — the biggest untested assumption is now the product

Every finding to date has been about the machine, and the machine is in good
shape. Nothing yet tests the product: does a 9-year-old actually do the
experiment before tapping "I tried it"? Is the ~85% flow target fun or boring
*for this child*? Does Hanz's voice land or grate? Does the sourced card get
read, or scrolled past? These answers invalidate engineering decisions faster
than bugs do, and they are only available at a kitchen table.

The pieces exist: working software, a consent field, consenting first testers
in the house (build-plan §5.4).

**Close:** run the first session this week. One laptop, one kid, one lesson.
Don't help. Watch for: skipped experiments, guess-spam on retrieval items,
scaffold read vs ignored, where they laugh, where they quit. Twenty minutes of
observation will reorder the roadmap more than a month of engineering.
Everything else in this file can wait behind it.

## 2. Local-first has an unpaid bill: durability (and the COPPA export)

The child's device holds the **only copy** of their learning history. A dropped
tablet erases a learner. There is no export, backup, or restore path in the
store — the privacy posture quietly made durability the family's problem.

This is also a compliance thread, not just a resilience one: a parent's COPPA
right to **review and delete** their child's data effectively requires an
export surface anyway. One mechanism, two obligations.

**Close:** a local, file-based export/import spine — `Store.export(path)` /
`Store.import_(path)` (JSON, human-readable, chain hashes included so an import
is verifiable). Quiet Corner already proved the backup/restore-as-JSON pattern.
Must live **outside** `utety/core`'s no-egress boundary? No — file I/O on the
same device is not egress; it can live in core. What must NOT exist is anything
that moves the export off-device automatically. Ship before real history
accumulates.

## 3. The threat model lives in audit docs and one auditor's head

Security so far has been reactive: build, audit, catch, fix. It has worked, but
each bite gets designed without a written adversary list and then patched
against one. Worth one page, written once, designed against thereafter. The
list for a child's tutor:

| Adversary | Status |
|---|---|
| Malicious webpage in the same browser (CSRF / DNS rebinding) | covered (bite-4 W2 fixes) |
| Hostile/compromised knowledge backend | covered (W3, https-only, sourced-card hygiene) |
| Network observer | covered (https transport rule) |
| **A sibling on the same device** | *undiscussed* — no per-learner separation beyond an id in a URL |
| **The learner themselves** | *undiscussed* — a curious kid can open their own SQLite file and set `p_known = 0.99` everywhere |

The last one deserves an explicit decision, and "out of scope, and that's fine"
is a legitimate answer — a child hacking their own tutor's mastery file has
arguably learned something better than levers. But it should be a *decision in
writing*, because the answer changes Phase-3 (can a teacher trust the mastery
dashboard?) and the disclosure chain's evidentiary weight.

**Close:** `docs/threat-model.md`, one page: adversaries, what each can reach,
what we defend, what we explicitly don't. New bites cite it the way they cite
the build plan.

## 4. Measurement isn't built in — and Phase 5 is a measurement phase

The ESSA ambition is Tier 4 → Tier 3, which means the pilot has to produce
*usable evidence*, decided in advance — or it produces anecdotes. Concrete
proof the gap is real: the outcomes schema has carried a `response_ms` column
since Phase 0, and nothing has ever populated it — not the loop, not the web
layer. The instrument was designed and the wire was never connected.

**Close:** before the first real pilot (item 1 is exploratory; the pilot is
not), decide the study's minimum measures — per-opportunity response time,
session length/count, retention on re-test after N days — and make the loop
record them as it goes. Retrofitting measurement after the data you needed
wasn't captured is the one mistake a Tier-3 aspiration can't recover from.

## 5. No stopping rule — the tutor never says "enough"

The ground rules guard against bad feedback, bad difficulty, unsourced claims —
but nothing anywhere says **the tutor ends a session**. For an under-13
product, "when does it tell the child to go do something else" is a
child-wellbeing ground rule, and it is precisely the one commercial edtech
omits on purpose. UTETY's differentiators are trust-shaped; this is the
cheapest trust feature that exists, and it gets culturally harder to add after
anyone starts admiring engagement numbers.

**Close:** add ground rule 8 to build-plan §0 — proposed wording: *"Sessions
end. The tutor stops the session after a mastery event or a time/opportunity
budget, celebrates the stop, and does not offer 'one more'. Overuse is a harm,
not a metric."* Enforcement is a session opportunity/minute budget in the loop
plus a closing fragment in the front — small build, big statement.

## 6. Three one-click process gaps

- **Branch protection on `main`.** CI exists and is green, but it is
  *advisory* — nothing forces a PR to pass it before merge. Make the seven
  checks required in repo settings. (docs/ci.md rule 3 — "no advisory checks"
  — currently isn't true at the repo level.)
- **Content-id stability rule.** `outcomes.item_id` and `skill_id` are strings
  referencing content-as-code; renaming an item id silently orphans every
  outcome recorded against it. Write the rule now: *ids are forever; renames
  are new ids plus a deliberate migration.* One paragraph in the content
  package docstring.
- **Accessibility + reading level as review criteria now, not Phase 4.** WCAG
  lands in Phase 4, but the web front is already shipping HTML, and
  accessibility retrofits onto shipped markup are notoriously expensive.
  Hold the cheap floor from this point on: labels on inputs (already mostly
  there), contrast, keyboard operability, no color-only meaning — and feedback
  text held to a grade 3–5 reading level (the item prose is currently good;
  keep it a criterion, not an accident).

---

*The pattern across all six: the project has been excellent at "is it built
right?" — these gaps all live in "is it the right thing?" Item 1 outranks
everything, including the next code audit: the machine is ready enough to
learn from a child, and nothing else on this list teaches what that will.*
