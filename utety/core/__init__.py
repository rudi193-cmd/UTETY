"""UTETY core — local-first student-data primitives.

Modules here are the on-device foundation (build-plan §4, Phase 0, item 3):

    store    — SQLite local-first store; ZERO network imports by design.
    mastery  — dependency-free BKT inference (vendored from the fleet's
               core/bkt.py) so mastery updates run on-device without a
               cross-repo dependency.

Ground rule 3 (non-negotiable): student data stays on-device unless an
optional, consented sync is explicitly enabled. The store enforces this
*structurally* — it imports no networking library, so there is no code path
by which student PII can leave the device.
"""
