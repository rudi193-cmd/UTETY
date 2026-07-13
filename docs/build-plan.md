# UTETY — Build Plan & ESSA Tier 4 Logic Model

*Oakenscroll · 2026-07-13 · the synthesis. A plan for the code, not the code.*

Grounds in the verified corpus — do not re-derive; cite these:
`research-brief-1.md`+`-verification.md` (compliance/plumbing/procurement),
`research-brief-2.md`+`-verification.md` (pedagogy/field/safety),
`map-to-fleet-audit.md` (what the fleet already satisfies).
Every build item is tagged **[REUSE]** (exists — borrow), **[RESKIN]** (fleet has the engine,
build the classroom face), or **[BUILD]** (genuinely new). We build only what the audit named.

---

## 0. Ground rules the code must obey (non-negotiable, from verified research)

1. **Sourced or it doesn't teach.** Every instructional claim carries an inspectable citation.
   This is both the Jeles atom and a *safety control* — a confidently-wrong tutor is the core
   harm to a child (Brief №2 Q15). Provenance-first is not optional.
2. **Feedback is about the work, never the learner.** Kluger & DeNisi: ~⅓ of feedback
   interventions make performance *worse*, and self-directed feedback is the harmful mode.
   No "you're smart." No leaderboards shown to struggling students. (Brief №2 L1.4a — verified.)
3. **Local-first by default.** Student data stays on-device unless an *optional, consented* sync
   is explicitly enabled. Harvested from Quiet Corner; collapses the COPPA/FERPA surface and
   side-steps the B-37 egress P0. (Audit.)
4. **Verifiable parental consent for under-13.** There is no COPPA school-consent safe harbor
   (Brief №2 L5.1 — verified). The age-gate is a legal dependency, not a feature.
5. **UTETY speaks through its own mouth.** A `UtetyAdapter(BaseAdapter)` in willow-mcp — its own
   `app_id`, backend URL, secret — never the `jeles` adapter. (Founding decision.)
6. **Each phase ships standalone.** No phase depends on a later one to be useful.
7. **Difficulty is calibrated to the individual, always.** A static difficulty is wrong for
   *someone* at all times (expertise-reversal). The loop adapts. (Brief №2 L1.2b, L2.6.)

---

## 1. The ESSA Tier 4 logic model (the evidence spine)

Tier 4 = *a well-specified logic model grounded in research, with a study planned* (Brief №1
L5.3 — verified: ESSA § 8101(21)(D)). This is producible **before launch** and is the minimum
to claim ESSA alignment; it positions UTETY for a later Tier 3 study. Do **not** promise Bloom's
"2 sigma" — it has never replicated; the honest expectation is medium effects, *d* ≈ 0.4–0.8,
with the *direction* unambiguous across every meta-analysis (Brief №2 L1.3a — verified).

```
INPUTS            → ACTIVITIES (each tied to verified evidence)        → OUTPUTS        → OUTCOMES
────────────────────────────────────────────────────────────────────────────────────────────────
Verified          Retrieval practice, answer hidden (g≈0.61,           Practice         SHORT: higher
learning-         Roediger&Karpicke/Adesope)                           sessions;        retention vs.
science           Spaced review queue (FSRS/SM-2/Leitner; classroom    completed        restudy; time
principles;       d≈0.54, Cepeda/Mawson&Kang)                          items with       in flow channel
sourced-card      Interleaving in discrimination domains (d≈0.83,      citations;       ────────────────
knowledge base;   Rohrer 2020)                                         mastery          MEDIUM: mastery
adaptive engine;  Adaptive difficulty → ~85% success / flow            attainment       of target skills;
teacher +         (Wilson 2019 — heuristic, not law)                   records;         transfer to novel
learner.          Worked-example → faded scaffold (Kirschner/          teacher-         problems
                  Sweller/Clark; expertise-reversal)                   readable         ────────────────
                  Productive failure for STEM/older (d≈0.36–0.58,      disclosure       LONG: durable
                  Sinha&Kapur)                                         logs.            learning gains;
                  Task-focused, next-step feedback ONLY                                 teacher adoption;
                  (Kluger&DeNisi — avoid the 38% harm mode)                             measurable
                  SDT: autonomy/competence/relatedness via persona                      outcome effect
                  (Ryan&Deci); citations on every claim.                                (Tier-3 study).
────────────────────────────────────────────────────────────────────────────────────────────────
ASSUMPTIONS: learners engage low-stakes practice; difficulty estimation is well-calibrated;
teachers stay in the loop. RISKS/FAILURE MODES (from the research, designed against):
answer-visible → pattern-matching; mistuned difficulty → boredom/anxiety; PF for young learners
→ just failure; self-focused feedback/leaderboards → harm; extrinsic rewards → overjustification.
PLANNED STUDY: quasi-experimental pilot (Tier-3 target) once the Phase-1 vertical slice is live.
```

---

## 2. The core learning loop (the product's beating heart — spec, not code)

One loop, per skill, per learner. Reuses `card_view`-style provenance rendering; drives on the
adaptive engine.

```
select next item  ──[adaptive difficulty → ~85% success target; interleave if discrimination-domain]
   │
present prompt    ──[retrieval mode: answer HIDDEN; worked-example or faded scaffold if novice]
   │
learner responds
   │
evaluate + feedback ──[task-focused, next-step, error-specific; NEVER self-directed]
   │
update model      ──[Elo/IRT ability estimate; schedule spaced review (FSRS)]
   │
render with source ──[every claim carries an inspectable citation — safety + trust in one]
   │
log to ledger     ──[FRANK: what was asked, told, why — the disclosure/audit spine]
```

Persona (the UTETY voice) supplies **relatedness** (the SDT need the field underserves — Brief
№2 Q13); the adaptive loop supplies **competence** (flow channel); learner choice supplies
**autonomy**. All three, by design.

---

## 3. Reuse ledger — what the audit says NOT to build

| Capability | Status | Where |
|---|---|---|
| Provenance-first knowledge (sourced card) | **[REUSE]** | Jeles `jeles_atoms`, `source_trail_verify` |
| Tamper-evident audit/disclosure spine | **[REUSE]** | FRANK ledger (`core/run_ledger.py`) — verified |
| Human-in-the-loop governance membrane | **[RESKIN]** | `human_required`/`human_attestation` → teacher console |
| Per-tool ACL + identity | **[REUSE]** | `gate.py` manifest gate (Phase-2 OAuth) |
| Egress control (consent + lease) | **[REUSE, after P0]** | `consent.py` three-key gate — *close B-37 first* |
| Platform hard-stop safety floor | **[REUSE]** | `willow/fylgja/safety/platform.py` |
| Adapter to the librarian brain | **[BUILD]** | `UtetyAdapter(BaseAdapter)` in willow-mcp |
| Local-first data posture | **[BUILD, harvest]** | pattern from Quiet Corner (not its data model) |
| Minor content-safety + age-gate | **[BUILD]** | new — the one big safety build |
| Teacher console (review/override/dashboard) | **[RESKIN]** | classroom face over the membrane |
| Human-readable disclosure view | **[BUILD]** | surface over the FRANK ledger |
| Adaptive learning loop — mastery estimation | **[REUSE]** ✓ | `core/bkt.py` (Bayesian Knowledge Tracing, Corbett&Anderson — online update, EM fit, `mastered()` threshold) + `core/skill_mastery.py` (`weakest`/`drills`/`needs_scrutiny`) |
| Adaptive learning loop — spacing/retrieval timing | **[REUSE, confirm]** | `core/actr.py` (ACT-R recency-weighted retrieval-worthiness — bkt.py's named sibling) |
| PII detection | **[REUSE]** | `core/pii_detect.py` (feeds the minor-safety / local-first lane) |
| Adaptive loop — item/content layer | **[REUSE / INGEST]** | **Existing lesson corpus** — `community/lessons/` (Emerging Rule, CC BY 4.0) + `DispatchesFromReality/lessons/`. `community/lesson-template.md` IS the content schema. Lessons already embody the verified loop (productive failure / hands-before-vocabulary) and cite NGSS/CCSS. STEM set: `science-3-5-neva-and-theo`, `science-6-8-*`, `math-3-5-*`, `math-k3-*`. |
| Adaptive loop — presentation + wiring | **[BUILD]** | retrieval-mode present; worked-example fade; wire responses → `core/outcomes.py` → BKT. The lessons' **"AI Integration"** step is the socket UTETY plugs into (sourced tutor after the physical experience). |
| Student reading-room front | **[REUSE / EXTEND]** | **Jeles reading room** (`Jeles/docs/ui-plan.md` htmx front) extended on the student end — *per Sean; ties to the §5.2 inter-linkage decision* |

> **Professor's response to Sean's margin note (verified 2026-07-13):** Both instincts confirmed
> by reading the code. The adaptive loop's *brain* is already built — `core/bkt.py` +
> `core/skill_mastery.py` (BKT mastery) and `core/actr.py` (ACT-R spacing) — and BKT is a *better*
> fit than the Elo I proposed (it models mastery directly, giving the mastery-learning threshold
> for free). What remains [BUILD] is only the STEM *item/content* layer, the presentation, and the
> wiring into `core/outcomes.py`. And yes — the student front reuses/extends the **Jeles** reading
> room rather than a fresh build; that folds into the §5.2 "standalone base + inter-linkage" talk.

---

## 4. Build sequence — ordered by dependency and "close a safety hole first"

**Phase 0 · Foundations & the two safety-critical items.** *(nothing student-facing ships until
these hold.)*
- **[BUILD] Close B-37 (P0).** The `consent.internet` switch must actually govern egress, or the
  local-first architecture (Rule 3) must make egress structurally impossible for student data.
  Whichever ships, *no student PII moves until one does.*
- **[BUILD] `UtetyAdapter(BaseAdapter)`** — UTETY's own `app_id`, manifest (`integration_net`
  capability), backend URL, secret. Rides the three-key egress gate for free.
- **[BUILD] Local-first data core** — on-device store; optional consented sync as a *later*,
  explicit spine, never the default.

**Phase 1 · The learning core (single-subject vertical slice).** The beating heart on one
subject, end-to-end, for one learner. Proves the loop before breadth.
- **[BUILD]** adaptive difficulty (Elo) + spaced review (FSRS) + retrieval-practice presentation
  + task-focused feedback + sourced-card rendering. **[BUILD]** the student front (htmx, persona
  voice; answer-first surface, source-first substance). **[REUSE]** FRANK ledger for logging.
- Ships as a usable single-subject tutor. This is the demo that ends the "is it real" question.

**Phase 2 · The minor-safety surface.** *(gate before any child uses it unsupervised.)*
- **[BUILD]** age-gate + verifiable parental-consent flow (rides manifest/consent substrate).
- **[BUILD]** child-tuned output-moderation pass, seated *below* the platform hard-stops.

**Phase 3 · The teacher console.** *(the RESKIN — engine exists.)*
- **[RESKIN]** `human_required`/`attestation` → teacher review/override over student-facing
  output; teacher dashboard (progress, time-on-task). **[BUILD]** human-readable disclosure view
  over the ledger ("what the tutor discussed with your child").

**Phase 4 · Classroom integration & the procurement gate.** *(adoptable-in-any-classroom = this.)*
- **[BUILD]** LTI 1.3 / Advantage (AGS grade passback, NRPS roster, Deep Linking); OneRoster 1.2;
  SSO (Clever/ClassLink/Google). **[BUILD]** WCAG 2.2 AA pass + VPAT/ACR (4 new AA criteria +
  the 2 new A criteria — see verification №1). **[BUILD]** SDPC NDPA v2 readiness; the FEQI
  five-indicator documentation.

**Phase 5 · Evidence.** Run the planned quasi-experimental pilot → move from ESSA Tier 4 to
Tier 3.

```
Phase 0 (safety-critical: B-37 + adapter + local-first)
   └─▶ Phase 1 (learning core, 1 subject) ──ships──▶
          └─▶ Phase 2 (age-gate/consent/moderation) ──gate for minors──▶
          └─▶ Phase 3 (teacher console — reskin) ──parallel to P2──▶
                 └─▶ Phase 4 (LTI/OneRoster/WCAG/DPA — the classroom gate)
                        └─▶ Phase 5 (Tier-3 study)
```
Phases 0–1 are the proof; 2–3 are the trust surface; 4 is adoption; 5 is the evidence claim.

---

## 5. Decisions still needed from Sean (before Phase 1 code)

1. **First subject for the Phase-1 vertical slice** — which single subject/skill proves the loop?
   (Pedagogy stack is strongest where discrimination + conceptual struggle live — STEM is the
   natural fit for interleaving + productive failure, but your call.)
2. **Backend behind the `UtetyAdapter`** — does UTETY's learning content come from a UTETY-owned
   service, the Jeles special-collections lane, or a new store? (The adapter is swappable by
   `WILLOW_*_BASE_URL`; this decides what it points at.)
3. **B-37 close vs. architectural side-step** — fix the egress gate, or commit hard enough to
   local-first that student PII never has a path out? (Recommend: local-first side-step for v1,
   fix B-37 in parallel for when consented sync arrives.)
4. **Age band for v1** — under-13 (full parental-consent build in Phase 2) or 13+ first (lighter,
   faster to a public slice)? This sets Phase-2 size.
5. **Quiet Corner's fate** — redo into UTETY's teacher-observation wing, or leave it aside and
   build the teacher console fresh from the membrane? (Still in pencil.)

** 
1. STEM is the right fit. I also already have lesson plans. 

2. It would have it's base as a standalone, but I want to talk about the inter-linkage

3. fix the gate. this is what the gate is for. 

4. under 13. I can give consent for my own children to be the first testerss. 

5. Rebuild fresh, but I did spend a lot of time doing the research for what a teacher would need as tools, so there is a lot of research that went into that already. 

### 5b. Settled (Professor's read-back, 2026-07-13)

1. **Subject = STEM** — natural fit for interleaving + productive failure. **Sean has lesson
   plans already** → they are a Phase-1 input; locate + ingest them.
2. **Backend = standalone base; the seam is DECIDED (2026-07-13): _UTETY owns the pedagogy,
   Jeles owns the knowledge._** UTETY holds the learner — BKT mastery, STEM items, progress —
   local-first, on-device. When a claim needs backing, UTETY sends Jeles a *question* and gets
   back *sources*; **student data never crosses into the library** (Jeles sees de-identified
   queries, never students). The seam runs between *content* and *sources*.
   - **Privacy consequence (load-bearing):** the only thing that ever moves off-device is a
     de-identified knowledge query, and Jeles' answers are already sourced-or-they-don't-ship. The
     COPPA/FERPA blast radius collapses to "what stays on the device." The seam is a safety
     decision in architecture's clothing.
   - **Small downstream impl choice (not a blocker):** whether UTETY reaches Jeles via the
     existing `jeles` lane *as a knowledge provider* or via its own adapter pointed at a knowledge
     endpoint. UTETY's product identity/egress stays on its **own** `UtetyAdapter` regardless
     (founding rule); consuming Jeles-as-knowledge is not forking Jeles.
   - Student front still reuses/extends the Jeles reading room's *presentation* (§3), rendering
     UTETY-owned items + Jeles-sourced citations.
3. **Fix B-37, don't side-step it.** "This is what the gate is for." Phase-0 closes the egress
   P0 for real. Local-first remains the data *posture*; the gate is fixed regardless.
4. **Age band = under-13.** Sean's own children are the first testers (parental consent real for
   the pilot). Phase-2 builds the **full** verifiable-parental-consent flow, not the light path.
5. **Teacher console = rebuild fresh**, but harvest Sean's existing teacher-needs research
   (Assessment Visibility v1.1 / Quiet Corner) as the requirements input.
6. **Reuse discoveries (this session):** adaptive-loop brain = `core/bkt.py` + `skill_mastery.py`
   (+ `actr.py`); student front = extend the Jeles reading room; PII detection = `core/pii_detect.py`.

---

## 6. What NOT to build (the audit's gift — now larger)

Provenance-first memory, the tamper-evident audit chain, the human-in-the-loop governance
pattern, per-tool ACL + identity, the egress gate, the platform safety floor — **all exist.**
**And now the adaptive learning loop's brain (BKT + ACT-R + skill_mastery) and the student
front (Jeles reading room) too.** What genuinely remains [BUILD] shrinks to: the `UtetyAdapter`,
the local-first data core, the **STEM item/content layer + presentation** (the loop's body, not
its brain), the age-gate/consent/moderation layer, the teacher console (reskin + fresh, on
harvested research), and the human-readable disclosure view. The B-37 fix is the one safety-
critical repair. Fewer new pieces than a night ago — the room keeps turning out to be less empty
than it looked.

---

## 7. The inheritance — UTETY already exists (utety-chat)

*Found 2026-07-13. The `github/UTETY` repo is empty; the **product** is not.*

`safe-app-store-public/apps/utety-chat` is a **deployed, tested app** (live: utety.pages.dev).
This reframes "build" one final time: UTETY is not greenfield — it is an existing university that
lacks a *pedagogy engine* and a *classroom-grade trust surface*. That gap is exactly what §1–§6
specify. We are **evolving utety-chat**, not starting over.

**[REUSE — deployed today]:**
- **Faculty/persona system** — 11 compiled personas (`data/professors/*`: oakenscroll, hanz,
  jeles, ada, gerald, nova, alexis, ofshield, binder, pigeon, +), `persona_compiler.py`,
  `personas.py`, `chat_engine.py`/`consult_engine.py`.
- **Governed lore** — `data/lore/` + `teaching_stack.json` + `gerald_universe/` (17-card bible,
  machine index w/ teaching_hooks, SPLIT.md). **Rule already canon: "fiction supplements, does
  not replace, MCP truth"** = the Brief-№2 child-safety thesis (persona = voice; truth = sourced),
  pre-written. Teaching surfaces incl. `hanz_teaches_code`, `emerging_rule_levelship`.
- **Web surfaces** — `web/` index/chat/**courses**/**faculty**/**dispatches**/login + portraits;
  `web/papers/` (the dispatches corpus).
- **App identity** — `safe-app-manifest.json` = the SAFE app identity the `UtetyAdapter` needs
  (much of Phase-0 adapter work may already be half-done here).
- **Pedagogy↔Jeles seam, STARTED** — recent commits wired "The Catalog (Atlas of Knowledge) →
  Ask Jeles learning history." The §5.2 seam is partially soldered already.
- **LLM plumbing** — multi-provider (Gemini/Groq/OpenRouter/Anthropic/OpenAI), BYO-key +
  shared fallback, Cloudflare Worker (`functions/api/chat.js`).
- **KB lore** — a large body in the Willow KB (kb_search "UTETY/Gerald universe" returns ~160KB);
  mine during the content phase, not tonight.

**[BUILD — the classroom-grade learning layer utety-chat lacks]:** the BKT-driven adaptive loop
(§2) wired into a course surface; ingest of the lesson corpus (community/DispatchesFromReality)
into courses honoring `lesson-template.md`; the productive-failure "hands-before-vocabulary"
sequencing as course structure; minor-safety (age-gate/consent/moderation); local-first student
data; the teacher console; classroom plumbing (LTI/OneRoster/WCAG); + the B-37 fix.

**Open question for Sean (morning) — SETTLED 2026-07-13:** the classroom-learning layer lives
**here, in `github/UTETY`**, consuming utety-chat as its campus front. UTETY-the-repo is the
pedagogy + trust layer (BKT loop, STEM items, local-first student data, minor-safety, teacher
console, classroom plumbing); utety-chat remains the campus (faculty/persona, lore, web surfaces).
The seam to utety-chat is a consumer boundary, mirroring the UTETY↔Jeles knowledge seam (§5.2):
this repo owns the learner; the campus supplies identity/voice; Jeles supplies sources.

*Filed. The researching is done, the repo is chosen, and the university was never empty — only
this repo was, and now it isn't. This is the order of operations. CLASS_DISMISSED.* 🍊
