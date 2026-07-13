# utety/core — the local-first student-data core

*Build-plan §4, Phase 0, item 3. The store that owns the learner.*

Per the settled seam (build-plan §5b.2): **UTETY owns the learner; Jeles owns
the sources.** Everything about a student — profile, BKT mastery, practice
history, disclosure log — lives here, on the device, and by default nowhere
else. The only thing that ever moves off-device is a *de-identified knowledge
query* to the library, built later as an explicit spine.

## Modules

| Module | Role |
|---|---|
| `store.py` | SQLite local-first store. Learner profile, per-skill BKT mastery, append-only outcome log, hash-chained disclosure log. **Zero network imports.** |
| `mastery.py` | Dependency-free BKT inference (vendored from the fleet's `core/bkt.py`) so mastery updates run on-device. Inference only; EM fit stays upstream. |

## The load-bearing guarantee (Ground rule 3)

Student data stays on-device unless an optional, consented sync is *explicitly*
enabled later. This is enforced **structurally, not by policy**: the core
imports no networking library and no process/FFI escape hatch, and tests keep
it that way. `tests/test_no_egress.py` proves it two ways — an AST scan of
every `utety/core/*.py`, and a subprocess check that importing the store loads
no network-capable module into `sys.modules` — and `tests/test_boundaries.py`
extends the ban (including `subprocess`/`ctypes`) to the whole package, with
the knowledge seam as the single allowlisted door.

**When the consented-sync spine is built, it must live OUTSIDE `utety/core/`**
so this guarantee continues to hold for the store.

## Shape

```python
from utety.core.store import Store
from utety.core.mastery import BKTParams

with Store("~/.utety/neva.db") as s:
    s.add_learner("neva", "Neva", birth_year=2016)
    s.set_consent("neva", "granted", granted_by="parent:sean")  # rule 4: verifiable parental consent
    s.add_skill("sci.3-5.forces", "science", "Forces & Motion",
                standard="NGSS 3-PS2-1", params=BKTParams(prior=0.3))

    p = s.record_outcome("neva", "sci.3-5.forces", correct=True)   # → new P(mastered)
    s.log_disclosure("neva", "source_cited",
                     payload={"claim": "gravity acts equally on all masses"},
                     citation="Galileo, Two New Sciences")

    s.is_mastered("neva", "sci.3-5.forces")     # BKT threshold (0.95)
    s.verify_disclosure_chain()                 # tamper-evident audit spine
```

## What's next (not in this core)

- **Phase 1** wires responses → this store → the presentation layer (retrieval
  practice, worked-example fade) and the Jeles knowledge seam.
- The **consented-sync spine** (a separate module, outside this package).
- The **Phase-3 teacher disclosure view** reads `disclosure_log()` — the
  human-readable "what the tutor discussed with your child".
