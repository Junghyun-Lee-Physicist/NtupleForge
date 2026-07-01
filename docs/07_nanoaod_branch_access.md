# NanoAOD branch access (`nanoaod_branch_access.py`) — the PyROOT gotchas it guards

> **Status: ACTIVE.** `modules/nanoaod_branch_access.py` provides the two
> mandatory PyROOT-level read helpers (`to_int`, `safe_len`) used by
> `modules/ssbGenCategorizer.py`. It was originally written for the retired
> ttbar categorizer under the name `_nanoaod_compat.py` (kept verbatim at
> [`legacy/code/modules/_nanoaod_compat.py`](legacy/code/modules/_nanoaod_compat.py))
> and **re-instated under this clearer name** when the CPV gen categorizer began
> reading NanoAOD vector branches again. The two bugs it fixes **recur** for any
> new module that reads vector branches from Python — always import from this
> module, never re-discover them the hard way.

---

## The setting

NanoAOD stores many fields in **compact ROOT types** for disk efficiency:
`UChar_t` (1-byte unsigned int) for ID/flavour fields, flat C-style arrays
for vector branches. The C++ analyzer never sees this: `treestream` /
`makeClass` bind these branches to `int` / `vector<int>` and ROOT widens the
storage type transparently at read time via typed `SetBranchAddress<int>`.

**The Python side is different.** When NanoAOD-tools exposes the same
branches through its `Event` wrapper in newer CMSSW (observed in
`CMSSW_14_2_1`, ROOT ≥ 6.30), some vector branches come back as **raw
`ROOT.TTreeReaderArray<T>` proxies** rather than wrapped Python lists. Those
raw proxies have two surprising behaviours, each of which produced a real
silent-failure bug in this project.

---

## Pitfall 1 — `UChar_t` elements are `bytes`, not `int`

PyROOT exposes an element of a `UChar_t` branch not as a Python `int` but as
a single-byte `bytes` object, e.g. `b'\x05'`. Direct comparison with an
integer literal **always returns `False`**:

```python
event.GenJet_hadronFlavour[j] == 5      # b'\x05' == 5  →  False, always
```

The comparison silently fails for every element, the cut kills every event,
and the downstream logic collapses to the wrong answer with **no error
raised**. This is exactly the bug that, on 2026-04-06, put **1000/1000**
`TTHHTo4b` signal events into `tt+LF`: the `GenJet_hadronFlavour[j] == 5`
b-jet test never matched, so the categorizer saw zero additional b-jets in
every event.

Branches affected (non-exhaustive): `GenJet_hadronFlavour`,
`GenJet_partonFlavour`, `Jet_hadronFlavour`, `Jet_partonFlavour`,
`Jet_jetId`, `Jet_puId`, `FatJet_hadronFlavour`, `FatJet_jetId`,
`SubJet_hadronFlavour`, `GenJetAK8_hadronFlavour`, and some `Muon_*Id` /
`Electron_*Id` fields.

**Diagnosis.** Check a suspect branch's leaf type — `UChar_t` is the danger
flag:

```python
leaf = tree.GetBranch(name).GetLeaf(name)
print(leaf.GetTypeName())   # 'UChar_t'  →  needs coercion
```

**Fix.** Coerce at every comparison site with `to_int()`:

```python
# CRAB imports the analysis module flat, so make the sibling helper importable:
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nanoaod_branch_access import to_int

if to_int(event.Jet_jetId[j]) < 4:
    continue
if to_int(event.GenJet_hadronFlavour[j]) == 5:
    ...
```

`to_int()` is idempotent and a no-op on values that are already `int` (fast
path), so wrapping every `UChar_t` access costs essentially nothing. It
handles four element shapes: already-`int`; 1-byte `bytes`/`bytearray` (the
`UChar_t` case → first byte); multi-byte `bytes` (little-endian decode,
defensive); and 1-char `str` (some PyROOT builds → `ord`).

---

## Pitfall 2 — raw `TTreeReaderArray` has no `len()`

Python `len()` raises `TypeError` on a raw `TTreeReaderArray<T>` proxy. The
proxy *does* support ROOT's `GetSize()` and integer indexing, so the length
has to be obtained through a fallback path. Worse, the matching scalar
counter branch (`nGenPart`, `nGenJet`) **cannot be trusted as a length** in
this access mode — relying on `range(nGenJet)` returned `range(0)` in the
broken case, so the categorizer iterated over nothing and again classified
everything as `tt+LF`.

**Fix.** Use `safe_len()` instead of `len()`, and use the **array length**,
never the counter:

```python
from nanoaod_branch_access import safe_len

n = safe_len(event.GenPart_pdgId, branch_name="GenPart_pdgId")
for i in range(n):
    ...
```

`safe_len()` is a 3-tier fallback: `len()` (fast path for wrapped arrays) →
`GetSize()` (works on raw proxies) → integer-indexing probe (last resort,
capped at 100k). The first time the fast path fails for a given branch
type/name it emits one stderr warning, then stays quiet.

---

## Why a shim, not a patch to NanoAOD-tools

The "correct" fix would patch nanoAOD-tools' `Event` wrapper to auto-convert
`UChar_t` elements and expose `__len__` on its raw proxies. We deliberately
did **not**, because:

- Patching upstream creates a fork to maintain across CMSSW versions.
- The shim is tiny (~100 lines, two functions, no dependencies).
- Future bugs of the same shape (other compact ROOT types behaving oddly
  under PyROOT) can be added to the same module without touching CMSSW.

If a future CMSSW release ships a fixed `Event` wrapper, both helpers degrade
to no-ops via their fast paths and no calling code needs to change.

---

## Relevance to the current direction

The current pipeline is a full-NanoAOD passthrough with no gen-level Python
reads, so neither pitfall can bite today. The risk returns the instant a new
Python module touches vector branches. The rule for that future module is
simple: **never write `int(event.SomeBranch[i])` or `len(event.SomeVector)`
raw — import `to_int` / `safe_len` from the shim.** The verbatim source and
its self-test are at
[`legacy/code/modules/_nanoaod_compat.py`](legacy/code/modules/_nanoaod_compat.py)
(run the active module directly — `python -m nanoaod_branch_access` — to execute the self-test; the archived copy retains the old name).

---

## History

Discovered during ttbarCategorizer debugging (project transcript
2026-04-06/07). Five distinct infrastructure bugs were found in sequence;
the two captured in the shim are the ones that recur outside categorization.
The other three (input-branch zombie state, `hasattr` raising `RuntimeError`,
and the broken scalar counters) are documented where they were fixed — see
[`05_architecture.md`](05_architecture.md) §7 and
[`09_legacy_ttbar_pipeline.md`](09_legacy_ttbar_pipeline.md).
