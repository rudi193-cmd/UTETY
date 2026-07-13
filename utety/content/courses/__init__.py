"""Authored courses (content-as-code for v1).

Each module exposes ``build() -> Course``. A registry could enumerate these
later; for the Phase-1 vertical slice there is one:

    neva_and_theo — "Neva and Theo: A Story About Simple Machines" (science 3–5)
"""
from .neva_and_theo import build as build_neva_and_theo

__all__ = ["build_neva_and_theo"]
