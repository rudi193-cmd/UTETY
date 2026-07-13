# UTETY — Research Brief №1: What a classroom-grade learning product must be

*Oakenscroll · 2026-07-13 · draft for external execution + return-verification*

## Purpose & method

**Product under design:** UTETY — an interactive, fun, *challenging* learning product for
any learner, whose bar is **adoptable in any classroom** (a teacher with no prior context
can put it in front of students and it holds — pedagogically, legally, technically).

**This document is a research brief, not a plan.** It is executed by an external research
agent and returned for verification by the Professor. Therefore every lane names:
- **Q** — the precise questions to answer,
- **Good looks like** — what a complete, useful answer contains,
- **Verify against** — the authoritative primary source a finding must trace to (so the
  return can be checked, not trusted).

**Rules for the executing agent:**
1. **Primary sources over blogs.** The standards body, the statute, the spec — not a vendor
   summary of it. Vendor pages are acceptable only as *examples of practice*, labeled as such.
2. **Date everything.** Law and standards move. Every finding carries the version/date it
   reflects and states whether it is *current as of 2026*.
3. **Distinguish requirement from convention.** "Legally required," "de-facto required for
   adoption," and "nice to have" are three different columns. Say which.
4. **No synthesis-as-fact.** Where the agent infers or generalizes, mark it. The Professor
   verifies claims to source on return; unsourced claims are quarantined, not shelved.
5. **Map-to-fleet where noted.** Several lanes end with "does willow-mcp already provide
   this?" — answer the external requirement; the Professor maps it to existing fleet
   governance/consent/guardian capability during verification.

---

## Lane A — Pedagogy & learning design *(the soul: fun + interactive + challenging)*

**Q**
- What does learning science say actually makes practice *effective*: retrieval practice,
  spaced repetition, interleaving, desirable difficulty, the testing effect — mechanisms,
  effect sizes, and the conditions under which each works?
- How is **"challenging"** made productive rather than discouraging — scaffolding, the zone
  of proximal development, mastery learning, adaptive difficulty, productive failure?
- Formative vs. summative assessment: what distinguishes assessment that *teaches* from
  assessment that only *measures*? What feedback timing/specificity drives learning?
- What makes a learning experience *engaging* without being a slot machine — intrinsic vs.
  extrinsic motivation, the evidence for/against gamification, flow.

**Good looks like** — named mechanisms with the primary research behind each, effect sizes
where they exist, and explicit failure modes (when the technique backfires). A short list of
design principles UTETY can commit to, each traceable to evidence.

**Verify against** — peer-reviewed learning science (e.g. Roediger & Karpicke on the testing
effect; Bjork on desirable difficulties; Black & Wiliam on formative assessment; Bloom on
mastery learning; CAST/UDL for universal design; meta-analyses over single studies). Cite the
paper, not a summary of it.

---

## Lane B — Standards & interoperability *(the plumbing: joining a classroom that exists)*

**Q**
- **LTI 1.3 / LTI Advantage** (IMS/1EdTech): what does a tool implement to launch inside
  Canvas, Schoology, Moodle, Blackboard? Required services (Names & Roles, Deep Linking,
  Assignment & Grade Services). What is the current certified version?
- **Rostering & SSO:** OneRoster (spec + the CSV vs. API modes), and the SSO/rostering
  channels teachers actually use — Clever, ClassLink, Google Classroom, Microsoft. What
  does each require of a tool to be listed/integrated?
- **Learning analytics:** Caliper Analytics vs. xAPI (Experience API) — what each captures,
  when to use which, and what an LRS is.
- **Assessment & content portability:** QTI (question/test interoperability), Common
  Cartridge, and the state of SCORM vs. xAPI for packaged content.
- **Certification:** what 1EdTech certification/registration actually gates marketplace
  listing and district procurement?

**Good looks like** — a table: standard → what it's for → is it *required* / *de-facto
required* / *optional* for "adoptable in any classroom" → current version → the conformance/
certification step. Enough that we can pick a v1 subset with reasons.

**Verify against** — 1EdTech (formerly IMS Global) specifications directly; Clever/ClassLink/
Google/Microsoft partner documentation; the ADL xAPI spec. Spec pages, not vendor blogs.

---

## Lane C — Compliance & student-data privacy *(the room that sinks products quietly)*

> **Map-to-fleet lane.** willow-mcp already carries consent/guardian/governance. Research the
> external *requirement*; the Professor maps each to existing fleet capability on return.

**Q**
- **FERPA** — what obligations attach to student "education records," the school-official
  exception a vendor operates under, and the contractual terms districts require (data
  ownership, deletion, subprocessors).
- **COPPA** — triggered by learners **under 13**: verifiable parental consent, the
  school-consent pathway, data-minimization, and the 2025–2026 amendments' current state.
- **State student-data-privacy laws** — SOPIPA (California) as the archetype and the ~40-state
  patchwork; the **Student Data Privacy Consortium (SDPC)** national data-privacy agreement
  as the de-facto contracting instrument.
- **GDPR / GDPR-K** — the moment a European child logs in: lawful basis, age of consent by
  member state, data-subject rights.
- **AI-with-minors, 2026 frontier** — the newest and least-settled floor: state AI-in-education
  guidance, disclosure/transparency requirements, restrictions on training on student data,
  and duty-of-care expectations when a generative system converses with a child.

**Good looks like** — for each regime: who it protects, what it requires of a *vendor*, the
contractual artifact that proves compliance (DPA, SDPC agreement, VPAT for §508), and a
current-as-of-2026 note on anything in flux (COPPA amendments, new state AI laws).

**Verify against** — the statutes/regulations themselves and the enforcing body (US Dept. of
Education / Student Privacy Policy Office for FERPA; FTC for COPPA; the state AG texts; EDPB
for GDPR; SDPC for the national DPA). Primary legal text, dated.

---

## Lane D — Accessibility *(the floor that is both legal and moral)*

**Q**
- **WCAG 2.2 Level AA** — the concrete success criteria a learning product must meet
  (keyboard operability, contrast, captions/transcripts, focus, timing, motion, forms/labels).
- **Section 508 & ADA** — how they apply to edtech sold to public schools; the **VPAT/ACR**
  as the artifact districts demand.
- **UDL (Universal Design for Learning)** — the CAST framework as the *design* posture that
  makes accessibility native rather than retrofitted (ties back to Lane A).
- **AI-specific access:** captioning generated media, screen-reader behavior of dynamic/AI
  content, cognitive-load and reading-level controls.

**Good looks like** — a checklist of WCAG 2.2 AA criteria most relevant to an interactive
learning UI, the VPAT expectation, and the UDL principles UTETY should design *from* (not
bolt on).

**Verify against** — W3C WCAG 2.2 Recommendation; Section 508 (Access Board / ICT Refresh);
CAST UDL Guidelines. The standards directly.

---

## Lane E — Market & competitive landscape *(so we build what's unclaimed)*

**Q**
- The 2026 classroom-AI field: MagicSchool, SchoolAI, Khanmigo (Khan Academy), Brisk,
  Diffit, Curipod, and peers — **what each actually does**, who it's *for* (teacher-facing
  vs. student-facing), and its business/adoption model.
- **What are they certified/compliant for** (LTI listing, SOC 2, SDPC signatory, FERPA/COPPA
  posture, WCAG/VPAT) — the badges that gate district procurement.
- **Adoption channels** — how a classroom tool actually gets into classrooms (district
  procurement, teacher-led bottom-up, marketplace listings, free-tier land-and-expand).
- **The gap** — following the Jeles method: where is the field thin? What does "fun +
  interactive + *challenging*, student-facing, sourced" leave genuinely unclaimed?

**Good looks like** — a comparison table (tool → audience → what it does → compliance badges →
model) and an explicit, evidenced statement of the open territory UTETY could own.

**Verify against** — the products' own docs/trust pages and independent 2026 reviews; label
marketing claims as claims. Date the landscape (it moves fast).

---

## Lane F — AI-in-the-classroom safety & governance *(the newest floorboards)*

> **Map-to-fleet lane.** This is where the fleet's built-in consent/guardian/governance is
> most likely to be a moat rather than a cost. Research the requirement; map on return.

**Q**
- Content safety when a generative system faces minors: moderation, age-appropriate output,
  refusal boundaries, and the current expectations/guidance (frameworks, not just vibes).
- **Hallucination & accuracy controls** for instructional content — where sourced-answer /
  citation discipline (the Jeles primitive) becomes a *pedagogical* requirement, not a nicety.
- **Teacher-in-the-loop / human oversight** — what governance shape do districts and emerging
  policy expect over AI that instructs or assesses students?
- **Transparency & disclosure** — AI-use disclosure obligations to students/parents; academic-
  integrity implications; auditability of what the AI told a student and why.

**Good looks like** — a requirements list for "AI that is allowed to teach a child in 2026,"
each tagged *legal requirement / de-facto expectation / best practice*, ending with the
explicit map question: **which of these does willow-mcp's consent/guardian/governance already
satisfy, and which are genuine gaps?**

**Verify against** — published AI-in-education frameworks and guidance (e.g. US Dept. of Ed
office of ed-tech AI guidance; UNESCO guidance; state education-agency AI guidance); the FTC's
positions on AI + children; primary framework text, dated 2025–2026.

---

## Return format (so verification is mechanical)

For each lane, return findings as rows:

| claim | requirement class (legal / de-facto / best-practice) | source (name + URL + date/version) | current-2026? | confidence |
|---|---|---|---|---|

The Professor verifies each row to its source on return. Rows that don't resolve to their
stated source are **quarantined, not shelved** — same discipline as the intake gate.

*Filed. Send the wave.*
