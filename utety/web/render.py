#!/usr/bin/env python3
"""utety/web/render.py — server-side HTML fragments for the reading room.

Pure functions: each returns an HTML string. No I/O, no server, no network — so
every fragment is unit-testable directly. UTETY chrome; the sourced-card grammar
(corner brackets + confidence badge) is the one Jeles-derived element.

The persona voice lives here, server-side, so it can't be bypassed (Jeles
ui-plan §2). ``html.escape`` guards every interpolated value.
"""
from __future__ import annotations

from html import escape

from ..content.model import Course, Experience, Item
from ..core.loop import Presentation, Result
from ..knowledge import SourcedCard

_PERSONA_NAME = "Hanz"


# ── the page shell (loaded once; #stage is swapped by the JS island) ───────────
def page_shell(course: Course, learner: str, csrf: str = "") -> str:
    q = escape(learner)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="csrf" content="{escape(csrf)}">
<title>{escape(course.title)} · UTETY</title>
<style>{_CSS}</style>
</head>
<body>
<header class="masthead">
  <div class="crest">UTETY</div>
  <div class="titles">
    <h1>{escape(course.title)}</h1>
    <p class="byline">with {_PERSONA_NAME} · University of Precausal Studies</p>
  </div>
</header>
<main>
  <div id="stage" class="stage">
    <section class="card intro">
      <p class="hanz">Hello, friend. I'm {_PERSONA_NAME}. Copenhagen is on the desk —
      he's an orange, and he's been thinking about levers for quite some time.</p>
      <p>Before we name anything, we'll do a little with our hands. {escape(course.objective)}</p>
      <button class="primary" data-post="/step?learner={q}">Begin</button>
    </section>
  </div>
</main>
<script>{_ISLAND}</script>
</body>
</html>"""


# ── the hands-first experiment gate ────────────────────────────────────────────
def experience_fragment(exp: Experience, learner: str) -> str:
    q = escape(learner)
    return f"""<section class="card experience">
  <span class="eyebrow">First, your hands</span>
  <h2>{escape(exp.title)}</h2>
  <p>{escape(exp.instructions)}</p>
  <p class="hanz">Take your time. Come back when your hands have felt it — the
  words will make a different kind of sense then.</p>
  <button class="primary" data-post="/step?learner={q}&amp;ack={escape(exp.id)}">I tried it</button>
</section>"""


# ── a retrieval item (answer hidden; scaffold only for novices) ────────────────
def item_fragment(present: Presentation, item: Item, learner: str,
                  nudge: str = "") -> str:
    q = escape(learner)
    scaffold = ""
    if present.scaffold:
        scaffold = f'<p class="scaffold">{escape(present.scaffold)}</p>'
    nudge_html = f'<p class="nudge">{escape(nudge)}</p>' if nudge else ""
    return f"""<section class="card item">
  <span class="eyebrow">Now, what did you notice?</span>
  <form data-post="/answer?learner={q}&amp;item={escape(item.id)}">
    <p class="prompt">{escape(present.prompt)}</p>
    {nudge_html}
    {scaffold}
    <div class="choices">{_choices_html(item, present)}</div>
    <button class="primary" type="submit">Check</button>
  </form>
</section>"""


def _choices_html(item: Item, present: Presentation) -> str:
    if item.kind == "boolean":
        opts = {"true": "True", "false": "False"}
        return "".join(_radio(v, label) for v, label in opts.items())
    if item.kind == "text":
        return '<input type="text" name="response" autocomplete="off" placeholder="in your own words">'
    inputs = "checkbox" if item.kind == "multi" else "radio"
    return "".join(
        _input(inputs, cid, label) for cid, label in present.choices.items()
    )


def _radio(value: str, label: str) -> str:
    return (f'<label class="choice"><input type="radio" name="response" '
            f'value="{escape(value)}"> {escape(label)}</label>')


def _input(kind: str, value: str, label: str) -> str:
    return (f'<label class="choice"><input type="{kind}" name="response" '
            f'value="{escape(value)}"> {escape(label)}</label>')


# ── feedback + the sourced card ────────────────────────────────────────────────
def feedback_fragment(result: Result, cards: list[SourcedCard], learner: str) -> str:
    q = escape(learner)
    verdict = "right" if result.correct else "not yet"
    cls = "correct" if result.correct else "retry"
    cards_html = "".join(card_html(c) for c in cards) or ""
    mastered = ('<p class="mastered">You\'ve got this one. '
                "Neva would be pleased.</p>") if result.mastered else ""
    return f"""<section class="card feedback {cls}">
  <span class="eyebrow">{verdict}</span>
  <p class="hanz">{escape(result.feedback)}</p>
  {mastered}
  <div class="sources">
    <h3>Where this comes from</h3>
    {cards_html}
  </div>
  <button class="primary" data-post="/step?learner={q}">Keep going</button>
</section>"""


def card_html(card: SourcedCard) -> str:
    """The one Jeles-derived element: a corner-bracketed sourced card."""
    badge = escape(card.confidence or "sourced")
    badge_cls = {"high": "hi", "medium": "med", "low": "lo"}.get(card.confidence, "src")
    title = escape(card.source or "source")
    snippet = escape(card.snippet or "")
    date = f'<span class="date">{escape(card.date)}</span>' if card.date else ""
    # Cards are external input (the seam returns them). html.escape neutralizes
    # markup but not URL schemes — link only https, or a hostile backend could
    # hand the child a javascript: link (audit bite-4, W3).
    link = (f'<a href="{escape(card.url)}" target="_blank" rel="noopener">check the source</a>'
            if card.url.startswith("https://") else "")
    return f"""<article class="sourced">
    <span class="corner tl"></span><span class="corner tr"></span>
    <span class="corner bl"></span><span class="corner br"></span>
    <div class="src-head"><span class="src-name">{title}</span>
      <span class="badge {badge_cls}">{badge}</span></div>
    <p class="snippet">{snippet}</p>
    <div class="src-foot">{link}{date}</div>
</article>"""


# ── course complete ────────────────────────────────────────────────────────────
def complete_fragment(progress: dict, course: Course) -> str:
    rows = ""
    for s in course.skills:
        p = progress.get(s.id, {})
        pct = round(float(p.get("p_known", 0.0)) * 100)
        mark = "✓" if p.get("mastered") else "·"
        rows += (f'<li><span class="mark">{mark}</span> {escape(s.name)} '
                 f'<span class="pct">{pct}%</span></li>')
    return f"""<section class="card complete">
  <span class="eyebrow">The long way home</span>
  <h2>You did it — with your hands first, then the words.</h2>
  <ul class="progress">{rows}</ul>
  <p class="hanz">Theo got home before dark. He didn't tell anyone what happened.
  Some things are for keeping, at first. But his hands remembered. They always will. 🍊</p>
</section>"""


# ── the minimal htmx-style JS island (vendored; no CDN) ────────────────────────
# Just enough of htmx for this front: any [data-post] click POSTs (serializing an
# enclosing <form> if present) and swaps the response into #stage. Real htmx
# (~14kb) can replace this drop-in later without touching the fragments.
_ISLAND = r"""
const CSRF = (document.querySelector('meta[name="csrf"]') || {}).content || '';
document.addEventListener('click', async (e) => {
  const el = e.target.closest('[data-post]');
  if (!el) return;
  e.preventDefault();
  const form = el.closest('form');
  let body = '';
  if (form) {
    const data = new FormData(form);
    body = new URLSearchParams(data).toString();
  }
  const res = await fetch(el.getAttribute('data-post'), {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded',
              'X-Utety-Csrf': CSRF},
    body,
  });
  const html = await res.text();
  document.getElementById('stage').innerHTML = html;
});
document.addEventListener('submit', (e) => {
  const el = e.target.closest('form[data-post]');
  if (el) { e.preventDefault(); el.querySelector('[type=submit]').click(); }
});
"""

_CSS = r"""
:root { --ink:#2c2620; --cream:#f6f0e4; --paper:#fffbf3; --rust:#a8452a;
  --gold:#b8860b; --green:#3f7d4e; --amber:#b8860b; --line:#d8cdb6; }
* { box-sizing: border-box; }
body { margin:0; background:var(--cream); color:var(--ink);
  font-family: Georgia, 'Times New Roman', serif; line-height:1.55; }
.masthead { display:flex; gap:1rem; align-items:center; padding:1.1rem 1.4rem;
  background:var(--ink); color:var(--cream); }
.crest { font-weight:bold; letter-spacing:.28em; border:2px solid var(--gold);
  padding:.35rem .6rem; border-radius:3px; font-size:.85rem; }
.titles h1 { margin:0; font-size:1.25rem; }
.byline { margin:.15rem 0 0; font-size:.82rem; opacity:.8; font-style:italic; }
main { max-width:640px; margin:1.6rem auto; padding:0 1rem; }
.card { background:var(--paper); border:1px solid var(--line); border-radius:6px;
  padding:1.4rem 1.5rem; box-shadow:0 1px 0 rgba(0,0,0,.04); }
.eyebrow { display:inline-block; font-size:.72rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--rust); margin-bottom:.5rem; }
h2 { margin:.1rem 0 .6rem; }
.hanz { font-style:italic; color:#5a5040; }
.scaffold { background:#fdf6e6; border-left:3px solid var(--gold);
  padding:.5rem .8rem; margin:.6rem 0; font-size:.94rem; }
.nudge { color:var(--rust); font-style:italic; margin:.3rem 0 .6rem; }
.prompt { font-size:1.08rem; margin:.2rem 0 .8rem; }
.choices { display:flex; flex-direction:column; gap:.5rem; margin-bottom:1rem; }
.choice { display:flex; gap:.55rem; align-items:flex-start; padding:.55rem .7rem;
  border:1px solid var(--line); border-radius:5px; cursor:pointer; background:#fff; }
.choice:hover { border-color:var(--gold); }
input[type=text] { width:100%; padding:.55rem; border:1px solid var(--line);
  border-radius:5px; font-family:inherit; font-size:1rem; }
button.primary { background:var(--rust); color:#fff; border:none; border-radius:5px;
  padding:.6rem 1.2rem; font-size:1rem; font-family:inherit; cursor:pointer; }
button.primary:hover { background:#8f3a24; }
.feedback.correct .eyebrow { color:var(--green); }
.mastered { color:var(--green); font-weight:bold; }
.sources h3 { font-size:.85rem; text-transform:uppercase; letter-spacing:.1em;
  color:#8a7d63; margin:1rem 0 .5rem; }
.sourced { position:relative; background:#fffef9; border:1px solid var(--line);
  padding:.9rem 1rem; margin:.6rem 0; border-radius:2px; }
.corner { position:absolute; width:9px; height:9px; border:2px solid var(--gold); }
.corner.tl{top:4px;left:4px;border-right:0;border-bottom:0}
.corner.tr{top:4px;right:4px;border-left:0;border-bottom:0}
.corner.bl{bottom:4px;left:4px;border-right:0;border-top:0}
.corner.br{bottom:4px;right:4px;border-left:0;border-top:0}
.src-head { display:flex; justify-content:space-between; align-items:center; }
.src-name { font-weight:bold; }
.badge { font-size:.68rem; text-transform:uppercase; letter-spacing:.08em;
  padding:.15rem .5rem; border-radius:10px; color:#fff; background:#8a7d63; }
.badge.hi{background:var(--green)} .badge.med{background:var(--amber)}
.badge.lo{background:var(--rust)}
.snippet { margin:.5rem 0; font-size:.95rem; }
.src-foot { display:flex; justify-content:space-between; font-size:.82rem; }
.src-foot a { color:var(--rust); }
.progress { list-style:none; padding:0; }
.progress li { display:flex; align-items:center; gap:.6rem; padding:.4rem 0;
  border-bottom:1px dashed var(--line); }
.progress .mark { color:var(--green); font-weight:bold; width:1rem; }
.progress .pct { margin-left:auto; color:#8a7d63; }
"""
