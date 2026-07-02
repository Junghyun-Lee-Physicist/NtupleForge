# NanoAOD branch access (`nanoaod_branch_access.py`) — the PyROOT gotchas it guards

> **Status: ACTIVE. Updated: 2026-07-01** (Pitfall 2 rewritten after the CRAB
> segfault A12 — the length rule is now **"use the count branch"**, reversing the
> earlier "derive length from the array" advice, which was itself a
> mis-attribution; see the corrected history below).
> `modules/nanoaod_branch_access.py` provides the mandatory PyROOT-level read
> helpers (`to_int`, `count`/`opt_count`; `safe_len` is deprecated for
> collections) used by `modules/topCPVCategorizer.py`. It was originally written
> for the retired ttbar categorizer under the name `_nanoaod_compat.py` (kept
> verbatim at
> [`ttHH/legacy/code/modules/_nanoaod_compat.py`](ttHH/legacy/code/modules/_nanoaod_compat.py))
> and re-instated under this clearer name when the TopCPV gen categorizer began
> reading NanoAOD vector branches again. These bugs **recur** for any new module
> that reads vector branches from Python — always import from this module, never
> re-discover them the hard way.

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
raw proxies have surprising behaviours, each of which produced a real bug in
this project — two silent misclassifications and one hard segfault.

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

## Pitfall 2 — collection length: USE THE COUNT BRANCH, never probe the array

Python `len()` raises `TypeError` on a raw `TTreeReaderArray<T>` proxy. The
tempting recovery — asking the array itself (`GetSize()`, or indexing upward
until an exception) — is **exactly wrong**, and the second half of it is
**fatal**: `TTreeReaderArray::At(i)` for `i >= size` is **undefined behaviour**
in ROOT. It does not raise a catchable Python exception; it dereferences an
unconfigured `TBranchProxy` and **segfaults the process**. This killed the
first TopCPV CRAB production on 2026-07-01 (TTZToQQ, `*** Break ***
segmentation violation` in `TBranchProxy::Setup` ← `TObjectArrayReader::At`;
incident [`05_troubleshooting.md`](05_troubleshooting.md) A12).

**The correct length is the NanoAOD count branch.** Every collection `X`
carries a scalar `nX` with the format-level guarantee `nX == len(X_*)`.
Scalars read cleanly through the wrapper — no raw-proxy pathology applies.

```python
from nanoaod_branch_access import count, opt_count

n = count(event, "GenPart")            # reads event.nGenPart
for i in range(n):                     # elements: IN-BOUNDS indexing only
    pid = event.GenPart_pdgId[i]
nvt = opt_count(event, "GenVisTau")    # 0 if the branch is absent
```

`count()` is equivalent to the standard nanoAOD-tools idiom
`len(Collection(event, "GenPart"))` — `Collection` reads the same `nGenPart`
internally — minus the per-event `Object` construction in the hot loop. Either
form is acceptable; **what is not acceptable is deriving a length from the
array**.

### Corrected history — why the old advice said the opposite

Earlier revisions of this document (and of the retired categorizer) claimed
the `nX` counters were "unreliable as lengths" and instructed callers to take
the length from the array via `safe_len()`. That claim was a
**mis-attribution**. The zero-length counters observed on 2026-04-06 were a
symptom of a *different* bug active in the same session: the driver applied
the keep/drop file to the **input** tree (`branchsel=<file>`), which left
gen branches — counters included — in a zombie state
([`05_troubleshooting.md`](05_troubleshooting.md) A4). Once A4 was fixed
(`branchsel=None`; the input tree is always read in full,
[`04_architecture.md`](04_architecture.md) §7), the counters were reliable
again — but the "don't trust `nX`" advice survived, and the array-probe
workaround it mandated is what segfaulted in A12. Both the advice and the
probe are now retired: `safe_len()` no longer probes (it fails fast with
`TypeError` instead) and is **deprecated for collection lengths**.

---

## Pitfall 3 — branch presence detection (beginFile guards)

Two APIs that look right are wrong:

- `hasattr(event, name)` — the wrapper raises `RuntimeError` (not
  `AttributeError`) on a missing branch, which `hasattr` does not swallow;
  the job dies ([`05_troubleshooting.md`](05_troubleshooting.md) A5).
- `inputTree.GetBranch(name) is None` — through the nanoAOD-tools `InputTree`
  wrapper this did **not** report absence on a real data file, so an MC-only
  guard silently passed and the job crashed later inside `analyze`
  ([`05_troubleshooting.md`](05_troubleshooting.md) A11).

**Fix.** Read the branch list directly in `beginFile`:

```python
existing = {b.GetName() for b in inputTree.GetListOfBranches()}
self._has_genpart = "GenPart_pdgId" in existing
```

---

## Why a shim, not a patch to NanoAOD-tools

The "correct" fix would patch nanoAOD-tools' `Event` wrapper to auto-convert
`UChar_t` elements and expose `__len__` on its raw proxies. We deliberately
did **not**, because:

- Patching upstream creates a fork to maintain across CMSSW versions.
- The shim is tiny (two hot functions, no dependencies).
- Future bugs of the same shape (other compact ROOT types behaving oddly
  under PyROOT) can be added to the same module without touching CMSSW.

If a future CMSSW release ships a fixed `Event` wrapper, the helpers degrade
to no-ops via their fast paths and no calling code needs to change.

---

## History

`UChar_t`-as-bytes and the counter confusion were discovered during the ttbar
categorizer debugging (2026-04-06/07; five infrastructure bugs in sequence).
The out-of-bounds-probe segfault (Pitfall 2) surfaced in the first TopCPV CRAB
production on 2026-07-01 and prompted the count-branch rule and the corrected
history above. The archived original shim is at
[`ttHH/legacy/code/modules/_nanoaod_compat.py`](ttHH/legacy/code/modules/_nanoaod_compat.py)
(run the active module directly — `python3 modules/nanoaod_branch_access.py` —
to execute the self-test; the archived copy retains the old name and the old,
now-retired probing `safe_len`).
