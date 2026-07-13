#!/usr/bin/env python3
"""Course: "Neva and Theo: A Story About Simple Machines" (science 3–5).

Authored from community/lessons/science-3-5-neva-and-theo.md (Emerging Rule,
CC BY 4.0, contributor rudi193-cmd). The prose lesson stays the reading; this
module is its driveable form — two skills, two hands-first experiences, and the
retrieval items derived from the lesson's exit ticket, wrap-up, and
differentiation. Feedback is task-focused and anchored in the story (Rule 2);
every item carries a source (Rule 1).

Sequencing is the lesson's whole point: each item ``requires_experience`` its
skill's physical experiment, so the loop cannot surface vocabulary before the
learner has met the phenomenon in their hands.
"""
from __future__ import annotations

from ..model import Course, Experience, Item, Skill

# ── skills ─────────────────────────────────────────────────────────────────────
S_RAMP = Skill(
    id="sci.3-5.inclined-plane",
    subject="science",
    name="Inclined plane — trading distance for force",
    standard="NGSS 3-5-ETS1-1",
    description=(
        "A ramp spreads the work of raising a load across a longer distance, so "
        "the force needed at any single moment is smaller. Same work, gentler shape."
    ),
)
S_LEVER = Skill(
    id="sci.3-5.lever-fulcrum",
    subject="science",
    name="Lever — fulcrum position multiplies force",
    standard="NGSS MS-PS2-2",
    description=(
        "A lever has an arm, a fulcrum, and a load. Placing the fulcrum closer to "
        "the load turns a small movement on your end into a larger force on the load."
    ),
)

# ── experiences (the hands-before-vocabulary gates) ────────────────────────────
EXP_RAMP = Experience(
    id="exp.ramp",
    skill_ids=[S_RAMP.id],
    title="Slide it, don't lift it",
    instructions=(
        "Find a heavy book and something to tilt (another book, cardboard, a "
        "folder). Lift the book straight up — feel that. Now prop your surface into "
        "a ramp and slide the book up instead. Make the ramp steeper, then "
        "shallower. Notice when the sliding gets easier, and how far you have to push."
    ),
)
EXP_LEVER = Experience(
    id="exp.lever",
    skill_ids=[S_LEVER.id],
    title="Move the pivot",
    instructions=(
        "Take a ruler or stick, a rock or thick book as a pivot, and a heavy object "
        "to move. Try lifting the object with the stick, pivot close to the object. "
        "Then move the pivot close to your hands and try again. Notice what your "
        "hands feel change."
    ),
)

# ── items: inclined plane ──────────────────────────────────────────────────────
IP1 = Item(
    id="ip1",
    skill_id=S_RAMP.id,
    kind="single",
    prompt=(
        "You slid the heavy book up the ramp instead of lifting it straight up. "
        "What did the ramp change about your push?"
    ),
    choices={
        "a": "It made the push smaller, but you had to push over a longer distance",
        "b": "It meant you needed no force at all",
        "c": "It made the book weigh less",
        "d": "It removed gravity while the book was on the ramp",
    },
    answer="a",
    difficulty=0.35,
    requires_experience=EXP_RAMP.id,
    citation="NGSS 3-5-ETS1-1",
    source_query="why does an inclined plane reduce the force needed to raise a load",
    feedback={
        "b": "You still pushed — you felt it. The ramp made the push smaller at each "
             "moment, not zero. Slide the book again and notice: your hand is still working.",
        "c": "The book weighs the same on the ramp as off it. Something else got smaller — "
             "the push you needed at any one moment. What did you trade to get that?",
        "d": "Gravity never left — that's what your push was working against the whole time. "
             "The ramp just let you fight it a little at a time.",
    },
    feedback_default="Slide the book up the ramp once more and feel your hand: the push is "
                     "smaller, but it lasts over a longer distance. That trade is the ramp.",
    feedback_correct="Exactly what your hands felt: a smaller push, spread over more distance.",
)
IP2 = Item(
    id="ip2",
    skill_id=S_RAMP.id,
    kind="boolean",
    prompt="A steeper ramp is easier to push a heavy object up than a gentle ramp.",
    answer=False,
    difficulty=0.45,
    requires_experience=EXP_RAMP.id,
    citation="NGSS 3-5-ETS1-1",
    source_query="does a steeper inclined plane require more force than a shallower one",
    feedback={
        "true": "Remember Neva could only walk out the *gentle* side of the ravine, not the "
                "cliff. Make your ramp steeper and push again — feel the push grow.",
    },
    feedback_default="Try both: a steep ramp needs a bigger push, a gentle one a smaller push "
                     "over a longer slide. Gentle is the easier climb.",
    feedback_correct="Right — the gentle slope is the easier climb, which is why Neva took it.",
)
IP3 = Item(
    id="ip3",
    skill_id=S_RAMP.id,
    kind="single",
    prompt="Theo used the ramp to move the food with less force. What did he trade to get that?",
    choices={"a": "Distance", "b": "Time", "c": "The food's weight", "d": "Gravity"},
    answer="a",
    difficulty=0.6,
    scaffold="Think about your ramp: the push got smaller, but you had to push the book "
             "*farther* along the slope than if you'd lifted it straight up.",
    requires_experience=EXP_RAMP.id,
    citation="NGSS 3-5-ETS1-1 · lesson wrap-up",
    source_query="what does a simple machine trade to reduce force distance work",
    feedback={
        "b": "Not time — the trade is about how *far* you push. A smaller push, but over a "
             "longer path along the ramp.",
        "c": "The weight didn't change. What changed was how far Theo had to move things to "
             "get the same job done with less force.",
        "d": "Gravity is what he was working against, not what he traded. Look at the *path* — "
             "the ramp is longer than a straight lift.",
    },
    feedback_default="A simple machine gives the same work in a more manageable shape: less "
                     "force, but more distance. Distance is the trade.",
    feedback_correct="Yes — distance for force. The same work, in a shape his hands could manage.",
)

# ── items: lever ───────────────────────────────────────────────────────────────
LF1 = Item(
    id="lf1",
    skill_id=S_LEVER.id,
    kind="multi",
    prompt="A lever has three parts. Which three are they?",
    choices={
        "arm": "The arm (the stick)",
        "fulcrum": "The fulcrum (the pivot point)",
        "load": "The load (the thing you move)",
        "gravity": "Gravity",
        "wheel": "A wheel",
    },
    answer={"arm", "fulcrum", "load"},
    difficulty=0.4,
    requires_experience=EXP_LEVER.id,
    citation="lesson exit ticket · simple machines",
    source_query="what are the three parts of a lever arm fulcrum load",
    feedback={},
    feedback_default="Look at what Theo used: the branch (the arm), the stone under it (the "
                     "fulcrum), and the rock he was moving (the load). Those three — no gravity, "
                     "no wheel.",
    feedback_correct="Arm, fulcrum, load — exactly the three pieces Theo put together.",
)
LF2 = Item(
    id="lf2",
    skill_id=S_LEVER.id,
    kind="single",
    prompt="When you move the fulcrum closer to the load, the load becomes ___ to move.",
    choices={"a": "easier", "b": "harder", "c": "no different"},
    answer="a",
    difficulty=0.45,
    requires_experience=EXP_LEVER.id,
    citation="NGSS MS-PS2-2",
    source_query="how does moving a lever's fulcrum closer to the load change the force needed",
    feedback={
        "b": "Try it again: slide the pivot close to the heavy object. Theo moved the stone "
             "toward the rock, not toward himself — and *that's* when it shifted.",
        "c": "It does change — a lot. Move the pivot right up against the load and push. Feel "
             "how much less effort it takes than with the pivot in the middle.",
    },
    feedback_default="Move the pivot close to the load and push. That's the arrangement that "
                     "made Neva's rock finally move.",
    feedback_correct="Right — fulcrum near the load is the arrangement that freed Neva's foot.",
)
LF3 = Item(
    id="lf3",
    skill_id=S_LEVER.id,
    kind="single",
    prompt="Why did moving the fulcrum closer to the rock help Theo free Neva?",
    choices={
        "a": "A small push on his end became a larger force on the load's end",
        "b": "The rock got lighter",
        "c": "The branch got longer",
        "d": "Gravity reversed under the rock",
    },
    answer="a",
    difficulty=0.65,
    scaffold="Remember what your hands felt: with the pivot near the load, you pushed your end "
             "a long way and the load moved a short way — but with much more force.",
    requires_experience=EXP_LEVER.id,
    citation="NGSS MS-PS2-2 · lesson wrap-up",
    source_query="how does a lever multiply force when the fulcrum is near the load",
    feedback={
        "b": "The rock weighed the same the whole time. The lever didn't change the rock — it "
             "changed how Theo's push arrived at it.",
        "c": "Same branch, start to finish. What changed was where the *pivot* sat under it.",
        "d": "Gravity stayed put. The branch multiplied Theo's push — that's where the extra "
             "force came from, not from gravity.",
    },
    feedback_default="The lever multiplied Theo: a long push on his end, a short but much "
                     "stronger push on the load's end. The branch was multiplying him.",
    feedback_correct="Yes — the branch multiplied his push. Not magic, physics.",
)


def build() -> Course:
    """Return the driveable Neva-and-Theo course."""
    return Course(
        id="sci.3-5.neva-and-theo",
        title="Neva and Theo: A Story About Simple Machines",
        grade="3-5",
        subject="science",
        language="English",
        contributor="rudi193-cmd",
        license="CC BY 4.0",
        objective=(
            "Identify a ramp and a lever as simple machines and explain, after "
            "feeling it, how each trades distance for force."
        ),
        standards=["NGSS 3-5-ETS1-1", "NGSS MS-PS2-2", "CCSS.ELA RI.4.3"],
        persona="hanz",
        skills=[S_RAMP, S_LEVER],
        experiences=[EXP_RAMP, EXP_LEVER],
        items=[IP1, IP2, IP3, LF1, LF2, LF3],
    )
