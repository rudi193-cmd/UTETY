#!/usr/bin/env python3
"""utety/core/mastery.py — on-device BKT mastery inference.

A dependency-free vendored copy of the *inference path* of the fleet's
``core/bkt.py`` (Bayesian Knowledge Tracing, Corbett & Anderson 1995). UTETY is
a separate repo consuming utety-chat as its campus front (build-plan §7); it
does not import the fleet's Python across the repo boundary. Vendoring the ~40
lines of BKT inference keeps mastery estimation running fully on-device — no
network, no cross-repo dependency, Termux/Windows parity.

Scope: the *inference* path only — predict + posterior + update. The EM/
Baum-Welch parameter *fit* stays in the fleet (it runs over many learners'
sequences and is not needed on a child's device). Per-skill BKTParams are
either the neutral defaults below or values fitted upstream and shipped with
the skill definition.

Provenance: reimplemented from the algorithm in willow-2.0 core/bkt.py, itself
a dependency-free reimplementation of pyBKT (CAHLR, MIT). No source copied.
"""
from __future__ import annotations

from dataclasses import dataclass

_EPS = 1e-9


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp x into [lo, hi]."""
    return lo if x < lo else hi if x > hi else x


@dataclass
class BKTParams:
    """The four (plus one) BKT parameters for a single skill.

    prior  P(mastered before any practice)
    learn  P(unmastered -> mastered) per opportunity
    guess  P(correct | not mastered)      — held < 0.5 for identifiability
    slip   P(incorrect | mastered)        — held < 0.5 for identifiability
    forget P(mastered -> unmastered) per opportunity (default 0.0)
    """

    prior: float = 0.25
    learn: float = 0.15
    guess: float = 0.20
    slip: float = 0.10
    forget: float = 0.0

    def __post_init__(self) -> None:
        self.prior = _clamp(self.prior)
        self.learn = _clamp(self.learn)
        self.forget = _clamp(self.forget)
        # Identifiability cap: 0 <= guess, slip < 0.5
        self.guess = _clamp(self.guess, 0.0, 0.5 - _EPS)
        self.slip = _clamp(self.slip, 0.0, 0.5 - _EPS)


def predict_correct(p_known: float, params: BKTParams) -> float:
    """P(next response correct) given current P(mastered).

    correct = mastered & no-slip  OR  not-mastered & lucky-guess.
    """
    return p_known * (1.0 - params.slip) + (1.0 - p_known) * params.guess


def _posterior(p_known: float, correct: bool, params: BKTParams) -> float:
    """P(mastered | this observation) via Bayes, *before* the learning step."""
    if correct:
        num = p_known * (1.0 - params.slip)
        den = num + (1.0 - p_known) * params.guess
    else:
        num = p_known * params.slip
        den = num + (1.0 - p_known) * (1.0 - params.guess)
    if den <= _EPS:
        return p_known
    return num / den


def update(p_known: float, correct: bool, params: BKTParams) -> float:
    """Posterior mastery after observing ``correct``, including the learning step.

    Bayes-conditions on the observation, then applies the latent transition:
    an unmastered skill may be learned (``learn``); a mastered one may be
    forgotten (``forget``, default 0).
    """
    cond = _posterior(p_known, bool(correct), params)
    return cond * (1.0 - params.forget) + (1.0 - cond) * params.learn


def mastered(p_known: float, threshold: float = 0.95) -> bool:
    """True once estimated mastery reaches ``threshold`` (Corbett & Anderson use 0.95)."""
    return p_known >= threshold
