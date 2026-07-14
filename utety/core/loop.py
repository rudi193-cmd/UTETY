#!/usr/bin/env python3
"""utety/core/loop.py — the core learning loop (build-plan §2, Phase 1 bite 2).

One loop, per skill, per learner:

    select next item ─ adaptive difficulty → ~85% success (flow); interleave skills
    present prompt   ─ retrieval mode: answer HIDDEN; worked-example scaffold if novice
    learner responds
    evaluate+feedback─ task-focused, error-specific, next-step — NEVER self-directed
    update model     ─ store.record_outcome advances BKT mastery
    render w/ source ─ every item carries a citation + a de-identified source_query
    log to ledger    ─ store.log_disclosure — the on-device disclosure spine

This module is pure orchestration over the local store and the content model.
It stays network-free by design: it never fetches sources itself, it only hands
the front a ``source_query`` to send through the Phase-1 knowledge seam (which
lives OUTSIDE utety/core so the store's no-egress guarantee holds). See
utety/core/README.md.

The lesson's load-bearing rule — hands before vocabulary — is enforced here:
an item is never selected until its gating Experience has been acknowledged.
Acknowledgment persists via the disclosure log, so a session survives reopen.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..content.model import Course, Experience, Item
from .mastery import BKTParams, predict_correct
from .store import Store

TARGET_SUCCESS = 0.85      # Wilson 2019 flow-channel heuristic (not a law)
NOVICE_THRESHOLD = 0.40    # below this mastery, show the worked-example scaffold

_ACK_KIND = "experience_acknowledged"
_ANSWER_KIND = "item_answered"


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


@dataclass
class Presentation:
    """How an item is shown: answer hidden; scaffold only for novices."""

    item_id: str
    prompt: str
    choices: dict = field(default_factory=dict)
    scaffold: str | None = None       # populated only when the learner is a novice
    answer_hidden: bool = True


@dataclass
class Step:
    """The next thing to put in front of the learner."""

    kind: str                          # experience | item | complete
    experience: Experience | None = None
    item: Item | None = None
    present: Presentation | None = None


@dataclass
class Result:
    """The outcome of answering an item."""

    item_id: str
    skill_id: str
    correct: bool
    feedback: str
    mastery: float
    mastered: bool
    citation: str
    source_query: str                  # hand this to the knowledge seam (bite 3)


class LessonSession:
    """Drives one learner through one course's loop against the local store.

    The store holds all durable state (mastery, outcomes, disclosure); this
    object holds only a little in-session bookkeeping (recent items, to avoid
    immediate repeats). Experience acknowledgment is read back from the
    disclosure log on construction, so resuming is transparent.
    """

    def __init__(self, store: Store, course: Course, learner_id: str) -> None:
        self.store = store
        self.course = course
        self.learner_id = learner_id
        if store.get_learner(learner_id) is None:
            raise ValueError(f"unknown learner: {learner_id!r} — add_learner first")
        # skills must be registered in the store (register_course) before driving.
        for s in course.skills:
            if store.get_skill(s.id) is None:
                raise ValueError(
                    f"skill {s.id!r} not registered in store — call register_course first"
                )
        self._recent: list[str] = []
        self._acked: set[str] = {
            row["payload"].get("experience")
            for row in store.disclosure_log(learner_id)
            if row["kind"] == _ACK_KIND
        }

    # ── selection ──────────────────────────────────────────────────────────
    def next_step(self) -> Step:
        """Pick the next experience or item, or report completion."""
        unmastered = [
            s for s in self.course.skills
            if not self.store.is_mastered(self.learner_id, s.id)
        ]
        if not unmastered:
            return Step(kind="complete")

        # Interleave: prefer the least-practised unmastered skill (round-robin
        # emerges naturally), tie-breaking on lowest mastery. In a discrimination
        # domain (ramp vs lever), interleaving beats blocking (Rohrer 2020).
        # Walk the whole preference order: a skill with nothing selectable right
        # now (e.g. its items gated on another skill's experience) must fall
        # through to the next skill, not end the session (audit 2026-07-13, A5).
        ordered = sorted(unmastered, key=lambda s: (self._opps(s.id), self._mastery(s.id)))
        for target in ordered:
            # Gate: the physical experiment comes first (hands before vocabulary).
            for exp in self.course.experiences_for(target.id):
                if exp.id not in self._acked:
                    return Step(kind="experience", experience=exp)
            item = self._select_item(target.id)
            if item is not None:
                return Step(kind="item", item=item, present=self._present(item, target.id))
        # Unmastered skills remain but nothing is selectable for any of them.
        # Course validation guarantees every skill has items, so this is only
        # reachable via cross-skill gating; report completion of *available* work.
        return Step(kind="complete")

    def _select_item(self, skill_id: str) -> Item | None:
        """The item whose estimated success is closest to the ~85% flow target."""
        params = self._params(skill_id)
        p_known = self._mastery(skill_id)
        candidates = [
            i for i in self.course.items_for(skill_id)
            if self._gate_ok(i)
        ]
        if not candidates:
            return None
        # Avoid immediately repeating the last item when alternatives exist.
        non_recent = [i for i in candidates if i.id not in self._recent[-1:]]
        pool = non_recent or candidates

        def fit(item: Item) -> float:
            est = self._estimated_success(item, p_known, params)
            return abs(est - TARGET_SUCCESS)

        return min(pool, key=fit)

    def _estimated_success(self, item: Item, p_known: float, params: BKTParams) -> float:
        """Estimate P(correct) for this item: skill prediction, minus difficulty."""
        base = predict_correct(p_known, params)
        return _clamp(base - (item.difficulty - 0.5) * 0.5)

    def _present(self, item: Item, skill_id: str) -> Presentation:
        novice = self._mastery(skill_id) < NOVICE_THRESHOLD
        return Presentation(
            item_id=item.id,
            prompt=item.prompt,
            choices=dict(item.choices),
            scaffold=item.scaffold if (novice and item.scaffold) else None,
            answer_hidden=True,
        )

    def present(self, item_id: str) -> Presentation:
        """Re-present a known item (e.g. after an empty response) without grading."""
        item = next((i for i in self.course.items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"unknown item: {item_id!r}")
        return self._present(item, item.skill_id)

    # ── acknowledgment (the hands-first gate) ──────────────────────────────
    def acknowledge_experience(self, exp_id: str) -> None:
        """Record that the learner has done the physical experiment."""
        if not any(e.id == exp_id for e in self.course.experiences):
            raise ValueError(f"unknown experience: {exp_id!r}")
        self._acked.add(exp_id)
        self.store.log_disclosure(
            self.learner_id, _ACK_KIND, payload={"experience": exp_id}
        )

    # ── answering ──────────────────────────────────────────────────────────
    def answer(self, item_id: str, response) -> Result:
        """Evaluate a response: check → record_outcome (BKT) → feedback → disclosure."""
        item = next((i for i in self.course.items if i.id == item_id), None)
        if item is None:
            raise ValueError(f"unknown item: {item_id!r}")
        if not self._gate_ok(item):
            raise ValueError(
                f"item {item_id!r} answered before its experience "
                f"{item.requires_experience!r} was acknowledged"
            )

        correct = item.check(response)
        # One transaction: the outcome and its disclosure entry land together
        # or not at all (independent audit 2026-07-14, F5) — a failure must
        # not leave a graded answer the disclosure spine never saw.
        with self.store.transaction():
            p_new = self.store.record_outcome(
                self.learner_id, item.skill_id, correct=correct, item_id=item_id
            )
            # Render-with-source + log-to-ledger: record what was asked and
            # how it went, with the item's citation, into the disclosure spine.
            self.store.log_disclosure(
                self.learner_id, _ANSWER_KIND,
                payload={
                    "item": item_id, "skill": item.skill_id,
                    "correct": correct, "mastery": p_new,
                },
                citation=item.citation or None,
            )
        feedback = item.feedback_for(response)
        is_mastered = self.store.is_mastered(self.learner_id, item.skill_id)

        self._recent.append(item_id)
        return Result(
            item_id=item_id, skill_id=item.skill_id, correct=correct,
            feedback=feedback, mastery=p_new, mastered=is_mastered,
            citation=item.citation, source_query=item.source_query,
        )

    # ── progress ───────────────────────────────────────────────────────────
    def progress(self) -> dict:
        """Per-skill mastery summary for the whole course."""
        out = {}
        for s in self.course.skills:
            m = self.store.get_mastery(self.learner_id, s.id)
            out[s.id] = {
                "p_known": m["p_known"] if m else self._params(s.id).prior,
                "opportunities": m["opportunities"] if m else 0,
                "mastered": self.store.is_mastered(self.learner_id, s.id),
            }
        return out

    def is_complete(self) -> bool:
        return all(
            self.store.is_mastered(self.learner_id, s.id) for s in self.course.skills
        )

    # ── helpers ────────────────────────────────────────────────────────────
    def _gate_ok(self, item: Item) -> bool:
        return item.requires_experience is None or item.requires_experience in self._acked

    def _mastery(self, skill_id: str) -> float:
        m = self.store.get_mastery(self.learner_id, skill_id)
        return m["p_known"] if m else self._params(skill_id).prior

    def _opps(self, skill_id: str) -> int:
        m = self.store.get_mastery(self.learner_id, skill_id)
        return m["opportunities"] if m else 0

    def _params(self, skill_id: str) -> BKTParams:
        row = self.store.get_skill(skill_id)
        return BKTParams(
            prior=row["prior"], learn=row["learn"], guess=row["guess"],
            slip=row["slip"], forget=row["forget"],
        )
