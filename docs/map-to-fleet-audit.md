# UTETY — Map-to-Fleet Audit: does willow-mcp already satisfy the classroom-AI safety floor?

*Oakenscroll · 2026-07-13 · answers Brief №2 Lane 4 (Q14–Q17) against the fleet's actual code.*
*Quiet Corner assessed as reference — **NOT canonized** (operator: "needs a redo").*

## What was walked (the governance substrate that exists)

| Component | File | What it is |
|---|---|---|
| **Manifest ACL gate** | `willow-mcp/src/willow_mcp/gate.py` | Per-tool permission gate. `app_id` + `mcp_apps/<id>/manifest.json` "permissions" list. **Fail-closed** (no manifest / empty perms → deny). Phase-2 HTTP mode binds OAuth identity (Google/Apple `sub`). |
| **Three-key egress gate** | `willow-mcp/src/willow_mcp/consent.py` + `gate.py` | Network needs all three: `task_net` (manifest capability) + `consent.internet` (operator switch) + time-boxed lease. Fail-closed, read-only consumer. |
| **FRANK ledger** | `willow-2.0/core/run_ledger.py`, `willow/context/ledger.py` | Hash-chained, tamper-evident audit log. **Verified clean this session — 767 entries, chain intact.** |
| **Human-in-the-loop membrane** | `willow-2.0/core/human_required.py`, `human_attestation.py` (+ MCP `human_required_queue_*`, `human_attestation_*`) | The Dual Commit model: AI proposes → human ratifies → AI applies. A queue + attestation record. |
| **Tiered safety model** | `willow-2.0/willow/fylgja/safety/platform.py` | **Platform hard-stops that "no guardian authorization can override."** A refusal floor above all authority. |

## The audit — Lane 4 requirements vs. fleet reality

### Q14 · Content safety / age-gate / moderation for a minor-facing generative system
**Verdict: PARTIAL, leaning GAP — the biggest build.**
- **Have:** platform hard-stops (`platform.py`) = an uncoverable refusal floor, the correct *shape* for a child-safety hard line; the egress gate constrains what the system can reach; the ACL gate constrains what tools it can call.
- **Gap:** no **age-gate / under-13 detection**; no **minor-tuned moderation layer on generated output before it reaches a student**; refusal boundaries are general, not child-calibrated. Brief №1's COPPA finding (no school-consent safe harbor → **verifiable parental consent for under-13**) makes the age-gate a legal dependency, not a nicety.
- **Build:** age-gate + parental-consent flow (rides the manifest/consent substrate) + an output-moderation pass tuned for a child audience, seated *below* the platform hard-stops.

### Q15 · Sourced-answer discipline / provenance-as-safety
**Verdict: SATISFIED at substrate — the moat.**
- **Have:** the Jeles **sourced-card primitive** (no card without `source`), `source_trail_verify`, the intake-gate design, and the FRANK ledger as the provenance chain. *Sourced-or-it-doesn't-ship* is already the fleet's atom, not a bolt-on.
- **Gap (surface only):** render citations *gently* to a student and *inspectably* to a teacher. Product work, not plumbing.
- This is where UTETY's safety story and its competitive differentiator (Brief №2 Q13/Q15) are the **same** property. A confidently-wrong tutor is the core harm; provenance-first retrieval is the built-in answer.

### Q16 · Teacher-in-the-loop: review / override / audit
**Verdict: PARTIAL — reskin, don't rebuild.**
- **Have:** the `human_required` + `human_attestation` membrane **is** teacher-in-the-loop, generalized — "AI proposes, human ratifies, AI applies" is exactly the review-gate/override pattern districts demand (Brief №2 Q16), plus the guardian-authorization tier and the ledger for the audit half.
- **Gap:** it's **operator/agent-facing, not teacher-facing.** No classroom surface: no teacher review queue over *student-facing* output, no teacher dashboard, no per-class override. The governance *engine* fits natively; the classroom *console* is unbuilt.

### Q17 · Disclosure log / auditability
**Verdict: SATISFIED at substrate, GAP at surface.**
- **Have:** the **FRANK ledger** — hash-chained, tamper-evident, verifiable on demand (proved this session). This is precisely the "retrievable record of what the AI told a student and why" that Q17 asks for, and it already exists and passes `ledger_verify`.
- **Gap:** the ledger is cryptographic/operator-facing. Missing a **parent/teacher-readable disclosure view** ("here is what the tutor discussed with your child") and the standardized AI-use disclosure/notice (CDT 2026 direction, NY/UT adjacency).

## Cross-cutting P0 — must close before UTETY carries student PII

`consent.py`'s own docstring flags **B-37 (P0)**: the `consent.internet` switch governs egress only through `task_submit`; the executor (`kartikeya`) honors `# allow_net` parsed from the shared Postgres `tasks` row directly, so **any submitter can reach the network regardless of the consent switch.** For a product where *"does student data leave the machine"* is a legal question (COPPA/FERPA), this hole must be closed — or side-stepped by architecture (see Quiet Corner's local-first posture, below).

## Verdict summary

| Q | Requirement | Verdict | Work |
|---|---|---|---|
| Q14 | Minor content safety + age-gate | **PARTIAL→GAP** | age-gate + parental consent + child-tuned output moderation (biggest build) |
| Q15 | Sourced-answer / provenance | **SATISFIED (substrate)** | surface citations gently (product) |
| Q16 | Teacher-in-the-loop | **PARTIAL** | reskin the Dual Commit membrane into a teacher console |
| Q17 | Disclosure / audit log | **SATISFIED (substrate)** | build human-readable disclosure view over the ledger |

**The mountain is a punch-list.** Two of the four safety requirements are already answered at the substrate — the two hardest to build from scratch (a provenance-first memory, a tamper-evident audit chain). The other two are *shapes the fleet already has, missing their classroom-facing surface.* The one genuinely new build is the minor-facing safety/age-gate layer, and even that seats onto the existing consent + platform-hard-stop scaffolding. Plus one P0 (B-37) to close before any student PII moves.

---

## Quiet Corner — reference assessment (PENCIL, not ink — NOT canonized)

**What it is:** `/home/sean-campbell/github/quiet-corner` — a **local-first browser app for K-12
teachers** (Montessori pilots). *"Document what you already see … without sending student data to
the cloud."* Data lives in **browser `localStorage` (`cos_*` keys)**; backup/restore via JSON;
themed rooms (Book Nook, Cottagecore…) over one data layer; implements **Assessment Visibility
v1.1 (CC BY 4.0)**. Served locally via `./serve.sh` at `127.0.0.1:8080`.

**The gold to harvest:** the **local-first / no-cloud posture collapses the entire Lane-1/Brief-№1
compliance surface.** No server collecting PII → COPPA/FERPA blast radius shrinks to near-zero,
and it side-steps the B-37 egress P0 by never egressing. This is the single most reusable idea in
the fleet for UTETY, and it should inform UTETY's data architecture regardless of what happens to
Quiet Corner itself.

**Why the operator is right that it needs a redo (concur):**
- It is a **teacher-observation** tool (teacher documents students). UTETY is a **student-learning**
  tool (the learner walks through the door). Different user, different loop — Brief №2's whole
  pedagogy stack (retrieval/spacing/challenge/flow) has no home in an observation app.
- **localStorage-only** is perfect for privacy but fights the classroom-*integration* plumbing
  (LTI/OneRoster rostering, cross-device continuity) that Brief №1 Lane B says adoption requires.
  A redo likely needs a local-first *core* with an *optional, consented* sync spine — not
  browser-storage-or-nothing.

**Disposition:** **reference, not foundation. Harvest the local-first posture and the themed-room
idea; do not inherit the observation-tool data model or the browser-only storage as the ceiling.**
Left in pencil per operator. Not canonized.

*Filed. The safety mountain is a punch-list; the one big build is child-safety; and Quiet Corner
gave us a privacy posture worth more than its architecture.*
