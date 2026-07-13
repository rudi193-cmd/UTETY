#!/usr/bin/env python3
"""utety/content/register.py — load a Course's skills into a local Store.

The single place the content model touches the core: it maps each Skill's plain
``bkt`` dict onto ``utety.core.mastery.BKTParams`` and registers it via
``store.add_skill``. Idempotent per store — registering a course whose skills
already exist is a no-op (safe to call on every open).
"""
from __future__ import annotations

from ..core.mastery import BKTParams
from ..core.store import Store
from .model import Course


def register_course(store: Store, course: Course) -> list[str]:
    """Register every skill in ``course`` into ``store``. Returns skill ids added.

    Idempotent per store, and parameter drift is repaired: a skill already
    present whose course-shipped BKT params have changed gets its params
    updated in place (params are content, not learner state — mastery rows are
    untouched; audit 2026-07-13, B6). Does not add items or experiences to the
    store — those live in the content layer, not the student-data store (the
    store holds the *learner*, the content model holds the *material*).
    """
    added: list[str] = []
    for s in course.skills:
        params = BKTParams(**s.bkt)
        existing = store.get_skill(s.id)
        if existing is None:
            store.add_skill(
                s.id, s.subject, s.name, standard=s.standard, params=params,
            )
            added.append(s.id)
            continue
        stored = BKTParams(
            prior=existing["prior"], learn=existing["learn"],
            guess=existing["guess"], slip=existing["slip"],
            forget=existing["forget"],
        )
        if stored != params:
            store.update_skill_params(s.id, params)
    return added
