# UTETY — Research Brief №2: The soul — pedagogy, the field, and AI that's allowed to teach

*Oakenscroll · 2026-07-13 · draft for external execution + return-verification*

## Purpose & continuity

Brief №1 surveyed the **law, the plumbing, and the procurement gate** — what lets UTETY *into*
a classroom. It verified well (see `research-brief-1-verification.md`) but never entered the
room that matters most for the product: **what makes UTETY teach, and makes a student not want
to leave.** This brief researches that room — the pedagogy — plus the two lanes the first wave
skipped (competitive field, AI-in-classroom safety), and closes five loose threads №1 left
unverified.

**Same execution rules as Brief №1** (they are non-negotiable — repeat for the executing agent):
1. **Primary sources over blogs.** The peer-reviewed paper, the standards body, the statute —
   not a vendor or SEO summary of it. Secondary sources allowed only as labeled *examples*.
2. **Date/version everything.** State whether current as of 2026.
3. **Requirement class where applicable:** *evidence-backed* / *contested* / *marketing claim*
   for pedagogy; *legal / de-facto / best-practice* for safety. Say which.
4. **Mark inference.** `[AGENT NOTE]` on anything generalized beyond a source. The Professor
   verifies to source on return; unresolved rows are quarantined, not shelved.
5. **Map-to-fleet where flagged.** Lane 4 ends each item with "does willow-mcp's
   consent/guardian/governance already satisfy this?" — answer the external requirement; the
   Professor maps to fleet capability on return.
6. **Effect sizes and failure modes, not just names.** For every learning technique: how big
   is the effect, under what conditions, and *when does it backfire?* A technique with no stated
   failure mode is an unfinished finding.

---

## Lane 1 — Learning science: what actually makes practice work

**Q1 — The core memory/retrieval mechanisms.** For each: mechanism, evidence base, effect size,
boundary conditions, failure mode.
- **Retrieval practice / the testing effect** — recall-to-learn vs. re-study.
- **Spaced repetition / distributed practice** — spacing effect, expanding vs. fixed intervals,
  the algorithms that operationalize it (Leitner, SM-2/SuperMemo, FSRS) and their evidence.
- **Interleaving** vs. blocked practice — where it helps (discrimination) and where it hurts.
- **Elaboration & self-explanation**; **dual coding** (words + visuals).

**Q2 — Desirable difficulty & the challenge curve** *(the "challenging" mandate, made rigorous)*.
- Bjork's **desirable difficulties** — the principle and its limits.
- **Cognitive Load Theory** (Sweller): intrinsic/extraneous/germane load; the **expertise-
  reversal effect**; worked examples → faded scaffolding → independent practice.
- **Zone of Proximal Development** & scaffolding; **productive failure** (Kapur) — struggle
  *before* instruction. When does difficulty motivate, when does it defeat?

**Q3 — Mastery & progression.**
- **Mastery learning** (Bloom's 2-sigma) — what it claims, what replicates, what doesn't.
- Competency-based progression; setting a mastery threshold; the risk of gaming/over-practice.

**Q4 — Feedback & formative assessment.**
- Feedback **timing** (immediate vs. delayed) and **specificity**; Hattie & Timperley's model;
  Black & Wiliam on formative assessment; when feedback *harms* (praise, normative comparison).

**Q5 — Motivation & engagement without the slot machine.**
- **Self-Determination Theory** (autonomy/competence/relatedness); intrinsic vs. extrinsic.
- **Flow** (Csikszentmihalyi) as the challenge/skill balance — the design target for UTETY.
- **Gamification: the honest evidence, both sides** — where points/badges/leaderboards help,
  where they crowd out intrinsic motivation (overjustification effect) and decay. Distinguish
  *game-based learning* (mechanics serve the content) from *gamification* (rewards bolted on).

**Good looks like** — a compact set of design principles UTETY can *commit to*, each with: the
mechanism, the primary citation, an effect-size band, the condition under which it holds, and
its failure mode. Enough to write a defensible **ESSA Tier 4 logic model** (Brief №1, Lane 5)
directly from it.

**Verify against** — the primary literature, not summaries: Roediger & Karpicke (2006) testing
effect; Cepeda et al. (2006) spacing meta-analysis; Rohrer & Taylor on interleaving; Bjork &
Bjork desirable difficulties; Sweller/Kirschner cognitive load; Kapur productive failure;
Bloom (1984) 2-sigma; Hattie & Timperley (2007) feedback; Black & Wiliam (1998); Deci & Ryan
SDT; the FSRS algorithm's published evaluation. Meta-analyses over single studies; name the
study.

---

## Lane 2 — Turning learning science into interactive challenge design

*(Bridges Lane 1's evidence to what UTETY actually builds. The "interactive + challenging" part.)*

**Q6 — Adaptive difficulty & item selection.**
- **Item Response Theory / adaptive testing** (CAT) basics; Elo-style difficulty rating for
  learning (as used by Duolingo/Khan); how to keep a learner in the flow channel (~85%-correct
  "sweet spot" — verify the "85% rule," Wilson et al. 2019).

**Q7 — Hints, scaffolds, and error handling that teach.**
- Intelligent-tutoring-system findings (Cognitive Tutor / ASSISTments / ALEKS): hint design,
  bottom-out hints, error-specific feedback, worked-example fading. Evidence for ITS effect
  sizes (VanLehn's review).

**Q8 — Assessment *for* learning vs. *of* learning in software.**
- Formative low-stakes checks vs. summative; retrieval-based quizzing as instruction; how to
  assess without triggering test anxiety or gaming.

**Q9 — Engagement mechanics that don't corrupt the learning.**
- Streaks, spaced-review queues, progress visualization, narrative/goal framing — which are
  evidenced to *support* (not just retain) learning, and which are pure retention hooks. Be
  honest about the difference.

**Good looks like** — a mapping table: *learning goal → the interaction that serves it →
evidence → failure mode.* This is the spec seed for UTETY's core loop.

**Verify against** — VanLehn (2011) ITS meta-review; Wilson et al. (2019) "85% rule"; published
evaluations of ALEKS/ASSISTments/Cognitive Tutor; Duolingo/Khan engineering papers where
peer-reviewed or preprinted (label preprints).

---

## Lane 3 — The competitive field (2026), so we build the unclaimed thing

**Q10 — Map the field.** For each tool: primary audience (teacher-facing vs. **student-facing**),
what it actually does, business/adoption model, and compliance badges (LTI listing, SDPC
signatory, SOC 2, FERPA/COPPA posture, WCAG/VPAT).
- **AI teacher-assistants:** MagicSchool, SchoolAI, Brisk, Diffit, Curipod.
- **Student-facing tutors:** Khanmigo (Khan Academy), Khan Academy core, Squirrel AI, others.
- **Game/challenge-based learning:** Quizizz, Kahoot!, Blooket, Gimkit, Prodigy, Duolingo (as
  the consumer-engagement benchmark), CENTURY Tech (adaptive).

**Q11 — The compliance/adoption badges that actually gate procurement** — cross-reference to
Brief №1's FEQI/DPA findings: which competitors carry which, and what that signals.

**Q12 — Adoption channels.** District top-down procurement vs. teacher-led bottom-up vs.
marketplace listing vs. free-tier land-and-expand — how each of the above actually got *in*.

**Q13 — The gap (the Jeles move).** Given the field, where is "**fun + interactive +
challenging + sourced/cited, student-facing**" genuinely thin or unclaimed? What does UTETY's
sourced-card + persona + MCP-portability posture let it own that the field can't easily copy?

**Good looks like** — a comparison table (tool → audience → does-what → badges → model →
channel) plus one evidenced paragraph naming the open territory and *why* it's open.

**Verify against** — each product's own docs/trust/pricing pages (label marketing as claims) +
independent 2026 reviews/analyst coverage; date the landscape (it moves monthly).

---

## Lane 4 — AI that is allowed to teach a child in 2026 *(map-to-fleet — likely the moat)*

> Every item ends: **"Does willow-mcp's built-in consent/guardian/governance already satisfy
> this?"** Research the external requirement; the Professor maps on return.

**Q14 — Content safety for a minor-facing generative system.** Moderation, age-appropriate
output, refusal boundaries, jailbreak resistance. What frameworks/guidance define "safe enough"
for a child audience (not vibes — cite the framework)?

**Q15 — Accuracy / hallucination controls as *pedagogy*.** Where sourced-answer + citation
discipline (the Jeles sourced-card primitive) stops being a nicety and becomes a *requirement*
for instructional content. Retrieval-grounding, "show your work," confidence signaling, and
the harm model of a confidently-wrong tutor.

**Q16 — Human oversight / teacher-in-the-loop.** What governance shape do districts and emerging
policy expect over AI that *instructs or assesses* — review gates, override, audit of what the
AI told a student and why.

**Q17 — Transparency, disclosure & auditability.** AI-use disclosure to students/parents;
academic-integrity implications; the emerging state AI-in-education disclosure requirements and
any federal movement; logging/audit expectations.

**Good looks like** — a requirements list for "minor-facing instructional AI, 2026," each tagged
*legal / de-facto / best-practice*, each ending in the explicit map-to-fleet question, so the
Professor can mark **satisfied-by-fleet / partial / gap** on return.

**Verify against** — U.S. Dept. of Education Office of Ed Tech AI guidance (2023 "AI and the
Future of Teaching and Learning" + any 2024–2026 updates); UNESCO guidance on generative AI in
education; FTC statements/actions on AI + children; state education-agency AI guidance
(California, and any state with binding disclosure rules); named safety frameworks. Dated
2023–2026 primary text.

---

## Lane 5 — Close the loose threads from Brief №1 *(verify, don't re-summarize)*

Five rows the first wave left unverified. Resolve each to primary source, one line each:

1. **COPPA school-authorization/consent exception** — was it finalized in the 2025 amendments,
   or only proposed and dropped? Can a *school* consent on behalf of parents for edtech, and
   under what CFR text or FTC guidance? *(Decides whether UTETY needs direct parental consent —
   high priority.)* → 16 CFR Part 312; FTC Final Rule Statement of Basis & Purpose (2025-04-22);
   FTC COPPA FAQ / EdTech guidance.
2. **ISO/IEC 40500:2025** — did WCAG 2.2 become this ISO standard, approved 2025-10-21? → ISO
   catalogue / W3C WAI.
3. **ESSA four tiers** — confirm the Tier 1–4 definitions and the Tier 4 "logic model + study
   planned" bar. → ESSA § 8101(21)(A)–(D); ED non-regulatory guidance; WWC.
4. **1EdTech versions** — is **LTI 1.3 / Advantage** the current certified release and
   **OneRoster 1.2** current? → standards.1edtech.org.
5. **SDPC National DPA** — confirm it exists as the de-facto national vendor–district template
   and its current form/version. → privacy.a4l.org (Student Data Privacy Consortium).

---

## Return format (unchanged, so verification stays mechanical)

Per lane, rows:

| claim | class (evidence: backed/contested/marketing · or legal/de-facto/best-practice) | primary source (name + URL + date/version) | effect size or requirement detail | current-2026? | confidence |
|---|---|---|---|---|---|

Pedagogy rows **must** carry an effect-size band and a failure mode, or they return incomplete.

*Filed. Go find the soul. Bring it back and I'll run every citation down to the paper.*
