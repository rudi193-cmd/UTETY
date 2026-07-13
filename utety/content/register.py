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

    Skips skills already present (idempotent). Does not add items or experiences
    to the store — those live in the content layer, not the student-data store
    (the store holds the *learner*, the content model holds the *material*).
    """
    added: list[str] = []
    for s in course.skills:
        if store.get_skill(s.id) is not None:
            continue
        store.add_skill(
            s.id, s.subject, s.name, standard=s.standard,
            params=BKTParams(**s.bkt),
        )
        added.append(s.id)
    return added
