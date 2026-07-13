"""UTETY content — the course/skill/item layer (build-plan §3, Phase 1 bite 1).

The verified lesson corpus is *prose* (community/lessons/*.md). BKT needs a
stream of discrete, auto-checkable practice opportunities. This package is the
curated bridge: a Course carries Skills (what BKT tracks), Experiences (the
physical, hands-before-vocabulary gates — productive failure), and Items (the
retrieval-practice checks that produce the 0/1 signal `store.record_outcome`
consumes).

Two ground rules are enforced structurally here:
  * Rule 1 (sourced or it doesn't teach) — every Item carries a source: a local
    citation and a de-identified ``source_query`` the Phase-1 knowledge seam
    asks Jeles to back.
  * Rule 2 (feedback about the work, never the learner) — Item feedback is
    task-focused and error-specific; ``tests/test_content.py`` lints against
    self-directed praise.
"""
