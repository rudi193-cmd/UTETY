#!/usr/bin/env python3
"""utety/knowledge.py — the UTETY→Jeles knowledge seam (Phase 1 bite 3).

The one place anything leaves the device. Build-plan §5b.2: UTETY owns the
learner; Jeles owns the sources. When the tutor needs to back a claim, it sends
Jeles a *de-identified question about the concept* and gets *sourced cards*
back. Student data never crosses — Jeles sees concept queries, never learners.

This module lives OUTSIDE utety/core ON PURPOSE. utety/core is guaranteed
network-free (see utety/core/README.md); the egress path is quarantined here.

The privacy control is STRUCTURAL, not merely policy:

  * The send path (`KnowledgeSeam.back`) takes a single concept-query string.
    There is no learner_id, no Store, no learner object anywhere in scope — so
    student PII *cannot* be transmitted; it is not a parameter.
  * `deidentify` scrubs any identifier that accidentally lands in a query
    (email / phone / SSN / card / secret) as defense-in-depth.
  * Egress rides UTETY's OWN identity — WILLOW_UTETY_KNOWLEDGE_URL +
    WILLOW_UTETY_SECRET, the `utety` app_id and its manifest `integration_net`
    grant (the founding rule; never the `jeles` adapter). The willow-mcp
    three-key egress gate (post-B-37) governs the actual send.

Transport is injected so the seam is testable with no live backend. The default
transport is a thin stdlib HTTPS POST under UTETY's identity; tests pass a fake.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Callable, Protocol

# ── de-identification (vendored, compact; primary control is structural) ───────
_REDACTED = "[redacted]"
_SCRUBBERS = (
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),          # email
    re.compile(r"\b(?:\+?\d[\d\-().\s]{7,}\d)\b"),                          # phone
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                    # SSN
    re.compile(r"\b(?:\d[ -]?){13,16}\b"),                                   # card-ish
    re.compile(r"\b(?:sk|pk|ghp|xox[bp])[-_][A-Za-z0-9]{8,}\b"),            # secret prefixes
)


def deidentify(text: str) -> str:
    """Scrub identifiers from a query before it can leave the device."""
    out = text
    for rx in _SCRUBBERS:
        out = rx.sub(_REDACTED, out)
    return " ".join(out.split())


def contains_pii(text: str) -> bool:
    """True iff any scrubber matches — used to assert a payload is clean."""
    return any(rx.search(text) for rx in _SCRUBBERS)


# ── the sourced card (the Jeles card_view contract — keep identical) ───────────
@dataclass
class SourcedCard:
    """A single sourced result: {url, source, snippet, confidence, date}."""

    url: str = ""
    source: str = ""
    snippet: str = ""
    confidence: str = ""          # high | medium | low (badge)
    date: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "SourcedCard":
        return cls(
            url=d.get("url", ""), source=d.get("source", ""),
            snippet=d.get("snippet", ""), confidence=d.get("confidence", ""),
            date=d.get("date", ""),
        )


# ── transport ──────────────────────────────────────────────────────────────────
# A transport takes (url, payload) and returns the raw JSON response dict.
Transport = Callable[[str, dict], dict]


class KnowledgeProvider(Protocol):
    def search(self, query: str) -> list[SourcedCard]: ...


def _http_transport(url: str, payload: dict) -> dict:
    """Default transport: HTTPS POST under UTETY's own identity.

    Rides WILLOW_UTETY_SECRET (the `utety` app credential). The willow-mcp
    egress gate authorizes the send by UTETY's app_id + integration_net grant.
    """
    # HTTPS only: the app secret rides a header, and a plaintext scheme (typo
    # or hostile env var) would leak it on the wire (audit 2026-07-13, B5).
    if not url.startswith("https://"):
        raise RuntimeError(f"knowledge endpoint must be https, got: {url!r}")
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "utety/knowledge"}
    secret = os.environ.get("WILLOW_UTETY_SECRET")
    if secret:
        headers["X-Utety-Secret"] = secret
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")  # noqa: S310 (https enforced above)
    with urllib.request.urlopen(req, timeout=30) as resp:   # noqa: S310 (https enforced above; own identity, gated)
        return json.loads(resp.read())


class KnowledgeSeam:
    """De-identify a concept query, send it out, return sourced cards.

    Note the shape of ``back``: its ONLY input is a concept-query string. No
    learner is reachable from here — that is the privacy guarantee in the type
    signature, not just the docstring.
    """

    def __init__(self, transport: Transport | None = None, base_url: str | None = None) -> None:
        self._transport = transport or _http_transport
        # UTETY's OWN knowledge endpoint — not the jeles lane (founding rule).
        self._base_url = (base_url or os.environ.get("WILLOW_UTETY_KNOWLEDGE_URL", "")).rstrip("/")

    def back(self, query: str) -> list[SourcedCard]:
        """Fetch sourced cards backing a concept query. De-identifies first."""
        if not self._base_url:
            raise RuntimeError(
                "WILLOW_UTETY_KNOWLEDGE_URL is not set — the knowledge endpoint "
                "UTETY's adapter points at must be configured before the seam can send."
            )
        clean = deidentify(query)
        # Belt-and-suspenders: never send a payload that still trips a scrubber.
        # A real raise, not an assert — asserts are stripped under `python -O`,
        # and a privacy control must not be optional (audit 2026-07-13, A4).
        if contains_pii(clean):
            raise RuntimeError("de-identification failed to clean the query")
        payload = {"query": clean}          # no learner field exists to add
        raw = self._transport(f"{self._base_url}/search", payload)
        cards = raw if isinstance(raw, list) else raw.get("cards", [])
        # The backend is external input: skip anything that isn't a card-shaped
        # dict rather than crashing on it (independent audit 2026-07-14, N3).
        return [SourcedCard.from_dict(c) for c in cards if isinstance(c, dict)]
