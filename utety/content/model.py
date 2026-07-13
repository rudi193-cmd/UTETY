#!/usr/bin/env python3
"""utety/content/model.py — the course/skill/item content model.

Dataclasses only, stdlib only (same local-first ethos as utety/core). A Course
is JSON-serializable (``to_dict``/``from_dict``) so content can move to a data
file later without touching the loop; for v1 courses are authored as code under
``utety/content/courses/``.

The item taxonomy is deliberately small — everything auto-checks to a clean 0/1
(the settled grading decision), no grader model:

    single   one correct choice        answer = choice id (str)
    boolean  true/false                 answer = bool
    multi    select-all / label-parts   answer = set of choice ids
    text     exact (normalized) string  answer = str | list[str] of accepted

Each Item carries BOTH a local ``citation`` (Rule 1 fallback — e.g. the NGSS
standard) and a de-identified ``source_query`` the knowledge seam (bite 3) sends
to Jeles to fetch a sourced card. The query is about the *concept*, never the
learner — it is safe to leave the device.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


# ── the four BKT parameters, mirrored from utety.core.mastery ──────────────────
# Kept as a plain dict on the Skill so the content model has no import cycle with
# the core; register.py maps it onto utety.core.mastery.BKTParams.
def default_bkt() -> dict:
    """Neutral BKT priors for a 3–5 conceptual STEM skill.

    guess ≈ 0.25 reflects the ~4-way retrieval items; slip low; a modest learn
    rate. Fitted values from upstream EM can replace these per skill later.
    """
    return {"prior": 0.25, "learn": 0.15, "guess": 0.25, "slip": 0.10, "forget": 0.0}


def _normalize_text(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


@dataclass
class Skill:
    """A masterable skill — the unit BKT tracks."""

    id: str
    subject: str
    name: str
    standard: str | None = None
    description: str = ""
    bkt: dict = field(default_factory=default_bkt)


@dataclass
class Experience:
    """A hands-first physical experiment — the productive-failure gate.

    Presented (and acknowledged) BEFORE the retrieval items for its skill, so the
    learner meets the phenomenon in their hands before any vocabulary arrives
    (the lesson's load-bearing sequencing principle).
    """

    id: str
    skill_ids: list[str]
    title: str
    instructions: str


@dataclass
class Item:
    """A single auto-checkable retrieval-practice opportunity.

    feedback: maps a wrong answer (choice id / "false" / normalized text) to a
    task-focused, error-specific, next-step message. feedback_default backs any
    wrong answer without a specific entry. feedback_correct is an optional
    task-focused acknowledgement — NEVER self-directed praise (Rule 2).
    """

    id: str
    skill_id: str
    kind: str                     # single | boolean | multi | text
    prompt: str
    answer: object                # shape depends on kind (see module docstring)
    choices: dict = field(default_factory=dict)   # id -> label (single/multi)
    citation: str = ""            # Rule 1 fallback (e.g. "NGSS 3-5-ETS1-1")
    source_query: str = ""        # de-identified question the seam asks Jeles
    difficulty: float = 0.5       # 0..1, for ~85%-success selection + scaffolding
    scaffold: str | None = None   # worked-example / faded prompt for novices
    requires_experience: str | None = None        # Experience.id gating this item
    feedback: dict = field(default_factory=dict)
    feedback_default: str = ""
    feedback_correct: str = ""

    def __post_init__(self) -> None:
        if self.kind not in ("single", "boolean", "multi", "text"):
            raise ValueError(f"unknown item kind: {self.kind!r}")

    # ── auto-checking (deterministic, on-device) ───────────────────────────
    def check(self, response) -> bool:
        """True iff ``response`` is correct. Deterministic; no model call.

        Raises ValueError on a malformed response (free text to a boolean item,
        a bare string to a multi item): a malformed response is a front-end bug,
        and grading it would feed a spurious 0/1 into the mastery signal.
        """
        if self.kind == "single":
            return response == self.answer
        if self.kind == "boolean":
            return _coerce_bool(response) == bool(self.answer)
        if self.kind == "multi":
            if isinstance(response, (str, bytes)) or not hasattr(response, "__iter__"):
                raise ValueError(
                    f"multi item expects a collection of choice ids, got {response!r}"
                )
            return set(response) == set(self.answer)
        if self.kind == "text":
            accepted = self.answer if isinstance(self.answer, (list, tuple, set)) else [self.answer]
            return _normalize_text(response) in {_normalize_text(a) for a in accepted}
        raise ValueError(f"unknown item kind: {self.kind!r}")  # pragma: no cover

    def feedback_for(self, response) -> str:
        """Task-focused feedback for a response (correct or not)."""
        if self.check(response):
            return self.feedback_correct
        key = self._feedback_key(response)
        return self.feedback.get(key, self.feedback_default)

    def _feedback_key(self, response) -> str:
        if self.kind == "boolean":
            return "true" if _coerce_bool(response) else "false"
        if self.kind == "multi":
            return ",".join(sorted(str(r) for r in response))
        if self.kind == "text":
            return _normalize_text(response)
        return str(response)


@dataclass
class Course:
    """A single lesson rendered as a driveable course."""

    id: str
    title: str
    grade: str
    subject: str
    language: str = "English"
    contributor: str = ""
    license: str = "CC BY 4.0"
    objective: str = ""
    standards: list[str] = field(default_factory=list)
    persona: str = ""             # the UTETY faculty voice for this course
    skills: list[Skill] = field(default_factory=list)
    experiences: list[Experience] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        skill_ids = {s.id for s in self.skills}
        if len(skill_ids) != len(self.skills):
            raise ValueError("duplicate skill id in course")
        item_ids = {i.id for i in self.items}
        if len(item_ids) != len(self.items):
            raise ValueError("duplicate item id in course")
        exp_ids = {e.id for e in self.experiences}
        for e in self.experiences:
            for sid in e.skill_ids:
                if sid not in skill_ids:
                    raise ValueError(f"experience {e.id!r} references unknown skill {sid!r}")
        for it in self.items:
            if it.skill_id not in skill_ids:
                raise ValueError(f"item {it.id!r} references unknown skill {it.skill_id!r}")
            if it.requires_experience and it.requires_experience not in exp_ids:
                raise ValueError(
                    f"item {it.id!r} gated on unknown experience {it.requires_experience!r}"
                )
        # Every skill needs at least one item: BKT mastery only moves on item
        # outcomes, so an item-less skill can never be mastered and would leave
        # the course permanently incompletable (audit 2026-07-13, A5).
        itemless = skill_ids - {i.skill_id for i in self.items}
        if itemless:
            raise ValueError(f"skills have no items (unmasterable): {sorted(itemless)}")

    # ── lookups the loop uses ──────────────────────────────────────────────
    def items_for(self, skill_id: str) -> list[Item]:
        return [i for i in self.items if i.skill_id == skill_id]

    def experiences_for(self, skill_id: str) -> list[Experience]:
        return [e for e in self.experiences if skill_id in e.skill_ids]

    def skill(self, skill_id: str) -> Skill | None:
        return next((s for s in self.skills if s.id == skill_id), None)

    # ── serialization ──────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        """A JSON-serializable dict. Multi answers (sets) become sorted lists;
        ``check`` compares set-wise, so the round-trip is behavior-preserving
        (audit 2026-07-13, A3)."""
        d = asdict(self)
        for it in d["items"]:
            if isinstance(it["answer"], (set, frozenset)):
                it["answer"] = sorted(it["answer"])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Course":
        return cls(
            id=d["id"], title=d["title"], grade=d["grade"], subject=d["subject"],
            language=d.get("language", "English"), contributor=d.get("contributor", ""),
            license=d.get("license", "CC BY 4.0"), objective=d.get("objective", ""),
            standards=list(d.get("standards", [])), persona=d.get("persona", ""),
            skills=[Skill(**s) for s in d.get("skills", [])],
            experiences=[Experience(**e) for e in d.get("experiences", [])],
            items=[Item(**i) for i in d.get("items", [])],
        )


_TRUE_TOKENS = frozenset(("true", "t", "yes", "y", "1"))
_FALSE_TOKENS = frozenset(("false", "f", "no", "n", "0"))


def _coerce_bool(response) -> bool:
    """Coerce a boolean-item response; raise on anything unrecognizable.

    Anything outside the explicit true/false token sets is a malformed
    response, NOT a "false" — mapping garbage to False silently graded any
    nonsense as correct on answer=False items (audit 2026-07-13, A2).
    """
    if isinstance(response, bool):
        return response
    if isinstance(response, (int, float)):
        return bool(response)
    token = _normalize_text(response)
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    raise ValueError(f"boolean item expects true/false, got {response!r}")
