# UTETY — The governmental-scale lens

*2026-07-14 · the operator's stated aspiration: usable "all the way up to
governmental scale" — districts, states, ministries. This doc records what
that means for the architecture, what it changes today (almost nothing, on
purpose), and the decisions it makes strategic rather than cosmetic. A
decision record in the §5b tradition: written before it's needed, so nobody
improvises it later.*

---

## 1. The thesis: local-first inverts the scaling problem

The standard edtech scaling story: more students → bigger central database →
bigger breach surface → the vendor becomes a national honeypot, and every
procurement review is a fight about it. UTETY structurally cannot tell that
story. A million students is a million SQLite files on a million devices and
**zero new central PII**. The consequences compound in government's favor:

- **Data sovereignty is the default posture, not a compliance add-on.**
  Student data residency is "the child's device," in every jurisdiction, by
  construction. The thing ministries fight vendors hardest over is pre-won.
- **No mass-breach scenario exists.** There is no central store to breach.
  The worst single compromise is one device — which was already the family's
  or school's physical-custody problem.
- **Offline is native.** Rural schools, intermittent connectivity, developing
  regions: the tutor's core loop needs no network at all (the seam degrades
  to local citations and the tests prove it).
- **Per-student infrastructure cost rounds to zero.** The only shared
  infrastructure is the knowledge endpoint, which serves de-identified
  concept queries — cacheable, learner-free, cheap.
- **The audit discipline is procurement evidence.** Zero runtime
  dependencies (the SBOM is "Python"), a core auditable in one sitting,
  boundary guarantees enforced by tests rather than promised by policy, and
  a filed audit trail with two independent auditors. These are the artifacts
  a state security review asks for, already in the repo.

**Standing rule this creates:** the zero-dependency / auditable-in-one-sitting
/ structurally-enforced-boundary discipline is a **product feature at
governmental scale**, not an engineering preference. It is never traded away
for convenience. A proposed dependency or boundary exception must argue
against this doc, not just against the linter.

## 2. What genuinely breaks or goes missing at that scale

### 2.1 Aggregate reporting — the missing architectural piece (the third seam)

A district or ministry buys *outcomes*: "is this working across 40,000
students?" Local-first makes that hard by design — and government demands it
anyway. The answer is a third seam, sibling to the knowledge seam, and it
deserves the same paper-first treatment §5b.2 gave that one:

> **The reporting seam (decided in principle, built later):** population-level
> reporting is computed as **de-identified rollups on-device** (counts,
> mastery distributions, time-on-task aggregates — never learner records),
> aggregated upward class → school → district. Raw learner data never leaves
> the device on this path either. The rollup format is versioned, inspectable,
> and small enough to audit by eye.

The danger is not that this is hard to build — it's that, designed late, an
integrator will "just sync the databases" and destroy the entire privacy story
in one sprint. Writing the rule down now is the defense. Phase 3's teacher
console should be designed with this hierarchy in mind (per-class today,
rollup-shaped tomorrow).

### 2.2 Fleet identity — the shared secret is a scale bomb

`WILLOW_UTETY_SECRET` is one credential in an env var. Right for one device;
catastrophic for a fleet, where one leaked tablet burns every device's
credential and rotation is a national incident. **Rule: per-device (or at
minimum per-site) credentials arrive when the knowledge seam goes live beyond
the family pilot.** Noted now because credential schemes are cheap to design
early and miserable to retrofit.

### 2.3 Evidence becomes the product gate

Governments do not buy Tier-4 logic models; they buy Tier 1–2 studies and
independent evaluations. Under this aspiration, Phase 5 stops being "the last
phase" and becomes the business plan — which is why measurement wired in from
the start (early-stage gaps doc, item 4) is load-bearing: pilot data that
cannot support a study pushes the procurement timeline back by years, not
weeks.

### 2.4 Content governance doesn't scale as courses-as-code

One author merging lessons via PR is right for now. A ministry needs review
workflows, versioning, and **provenance on content**: who approved this lesson
for these students, and when. The disclosure-chain instinct applies to content
too — signed, versioned courses with an approval trail. Later build; its
foundation is the ids-are-forever rule (early-stage gaps, item 6), which is
why that rule is written down already.

### 2.5 The license decision is now strategic

Governments increasingly mandate open source or code escrow for public money
("public money, public code"). The missing LICENSE is not hygiene — it is a
fork in how this can be sold: permissive (Apache-2.0) maximizes adoption and
integrator friendliness; copyleft (AGPL) guarantees improvements return and
resists proprietary capture; dual-licensing keeps both doors open. **Decide
with the government lens on, before external contributors exist** — relicensing
after contributions requires every contributor's consent.

### 2.6 The knowledge seam becomes critical infrastructure

Millions of concept queries against one endpoint means caching (the queries
are learner-free and repeat heavily — cache hit rates will be enormous),
availability engineering, and, at national scale, data-residency questions
even for de-identified queries (some jurisdictions will want the knowledge
endpoint in-country). The seam's *shape* survives unchanged; its deployment
story needs a design pass when a real fleet exists. The offline fallback
already guarantees the tutor degrades gracefully when the seam is down —
that property is also a procurement answer ("what happens when your service
has an outage during exams?" — "nothing; the tutor doesn't need it").

### 2.7 Mandated conformance (already sequenced, restated under this lens)

Phase 4's list — LTI 1.3/Advantage, OneRoster, SSO, WCAG 2.2 AA + VPAT/ACR,
SDPC NDPA — is the district gate. Governmental scale adds: Section 508 /
EN 301 549 (accessibility is *statutory*, not aspirational, for public
buyers), localization (the `language` field exists; the persona voice and
feedback corpus are English-shaped — translation is content work, plan it as
such), and standards alignment beyond NGSS/CCSS (the free-text `standard`
field already accommodates other frameworks; curriculum mapping is content
work, not schema work).

## 3. What changes right now

Almost nothing — and that is the point. The build plan's sequencing (kitchen
table → classroom → district) is already correct, and skipping ahead to
gov-scale engineering now would be building for a customer who hasn't
validated the product. The lens changes exactly three present-tense things:

1. **The license decision gets made with this lens** (§2.5) — it's already on
   the open list; now it has a strategic weight.
2. **The reporting seam is decided on paper** (§2.1) — this doc is that
   decision; Phase 3 designs the teacher console rollup-shaped.
3. **The discipline is protected explicitly** (§1) — zero dependencies,
   auditable core, structural boundaries: now recorded as a product feature
   that outranks convenience.

Everything else in §2 has a correct *later* (fleet identity at first
non-family deployment; content governance at first external author;
localization at first non-English pilot; seam infrastructure at first fleet).
The failure mode this doc exists to prevent is doing those things
*accidentally* — a synced database here, a shared credential there — instead
of deliberately, when their time comes.

---

*Filed alongside `early-stage-gaps-2026-07-14.md`. The short version: the
architecture already chose the one shape that scales to government without
becoming a honeypot. Guard the shape.*
