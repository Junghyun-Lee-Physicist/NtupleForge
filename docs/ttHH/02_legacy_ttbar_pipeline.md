# Legacy tt+jets Categorization Pipeline — Full Record

> **Why this document exists.** NtupleForge no longer produces `ttCat_*`
> branches; categorization moved to the main analyzer and the pipeline now
> ships full NanoAOD unchanged. But the old setup was a complete, working
> example of a recurring pattern — *write a custom `Module`, declare custom
> branches, optionally apply a skim cut, slim the output, and run it at scale
> through CRAB.* That pattern will be needed again. This document records the
> whole thing in enough detail to rebuild an equivalent from scratch, and
> points at the verbatim source preserved under
> [`legacy/code/`](legacy/code/).

**Verbatim source preserved (do not edit; copy out to rebuild):**

| File | What it is |
|------|------------|
| [`legacy/code/modules/ttbarCategorizer.py`](legacy/code/modules/ttbarCategorizer.py) | The categorizer module (962 lines, final 5-category version). |
| [`legacy/code/modules/_nanoaod_compat.py`](legacy/code/modules/_nanoaod_compat.py) | PyROOT compat shim it depended on (see [`../06_nanoaod_branch_access.md`](../06_nanoaod_branch_access.md)). |
| [`legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt`](legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt) | The slimming keep/drop list (output branches + required gen inputs). |
| [`legacy/code/branches/branch_2017UL/`](legacy/code/branches/branch_2017UL/) | MC-vs-data branch inventories used to build the keep list. |
| [`legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml`](legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml) | The CRAB campaign config that ran the categorizer over all datasets. |
| [`legacy/code/tools/validate_events.py`](legacy/code/tools/validate_events.py) | Skim-efficiency / bookkeeping checker (see §8 below). |

The other standalone QA scripts that accompanied this pipeline were removed
(`inspect_weights`, `compare_branches`, `dump_branches`, and the stale
`test_ttbar_categorizer`). The current live module example,
[`../modules/jetsMETcut.py`](../../modules/jetsMETcut.py), still demonstrates the
**skim-cut** half of the pattern.

---

## 1. Physics — see `01_physics.md`

The full physics rationale (why categorize tt+jets, 5FS/4FS sample stitching,
the five-category definitions, the `genTtbarId` encoding, and why five
categories and not seven) now lives in its own document:
**[`01_physics.md`](01_physics.md)**. This file covers only the *implementation* of
that scheme. A one-paragraph recap, so this document stands alone:

> The analysis is **ttHH → 4b, fully hadronic, 2017 UL**. The tt+jets
> background is split by the heavy-flavour content of jets **not** from the
> top decay (acceptance pT > 20 GeV, |η| < 2.4) into five mutually-exclusive
> categories — `ttCat_LightFlavour` (tt+LF), `ttCat_AddCjet` (tt+cc),
> `ttCat_Add1Bjet_1Had` (tt+b), `ttCat_Add1Bjet_2Had` (tt+2b), and
> `ttCat_Add2Bjet` (tt+bb, also absorbing tt+bbb/tt+4b). The labels enable
> per-category 5FS/4FS stitching and per-category systematics.

## 2. Two algorithms, two parallel branch sets

The final design ran **both** algorithms on every event and wrote **two
parallel branch namespaces**, so any downstream consumer could compare them
event-by-event without re-running anything.

### Primary path — `ttCat_*`, from `genTtbarId`

The NanoAOD `genTtbarId` integer is the serialized output of the official CMS
GenHFHadronMatcher → GenTtbarCategorizer plugin chain. **This is the AN-cited
tool and the only path that downstream stitching / histogram-splitting may
use.** The category is fully determined by `genTtbarId % 100`:

```python
def decode_genttbarid(genttbarid: int) -> Optional[str]:
    if genttbarid is None or genttbarid < 0:
        return None                       # not ttbar
    code = genttbarid % 100
    if code == 0:            return CAT_LIGHTFLAVOUR     # tt+LF
    if 41 <= code <= 45:     return CAT_ADDCJET         # tt+cc
    if code == 51:           return CAT_ADD1BJET_1HAD   # tt+b
    if code == 52:           return CAT_ADD1BJET_2HAD   # tt+2b
    if 53 <= code <= 55:     return CAT_ADD2BJET        # tt+bb
    return None                           # unrecognized → sample-level error
```

| `genTtbarId % 100` | Category | Meaning |
|--------------------|----------|---------|
| 0 | tt+LF | no additional heavy-flavour jets |
| 41–45 | tt+cc | additional c-jets (variants by c-hadron multiplicity) |
| 51 | tt+b | 1 additional b-jet, 1 b-hadron |
| 52 | tt+2b | 1 additional b-jet, ≥2 b-hadrons (collinear g→bb) |
| 53–55 | tt+bb | ≥2 additional b-jets (variants by hadron multiplicity) |

### Cross-check path — `ttCatXval_*`, from raw GenPart/GenJet

An independent Python re-derivation, used **only** for validation and a
possible algorithmic systematic — **never** for stitching or histograms. It
uses a genuinely different strategy than POG ghost-clustering, so the two
paths are independent estimators; they typically agree on >97% of ttbar
events, with residual disagreement concentrated at the 51/52/53 boundary
(1 vs 2 b-jets, single vs overlapping hadrons). The algorithm:

1. **Find additional B-hadrons in GenPart**: PDG-ID is a B hadron, the
   particle `isLastCopy` (`statusFlags >> 13 & 1`), and it has **no top-quark
   ancestor** in its mother chain.
2. **Find gen b-jets in acceptance**: `GenJet_hadronFlavour == 5`,
   `pT > 20`, `|η| < 2.4`. (`GenJet_hadronFlavour` is `UChar_t` → must be
   read through `to_int()`; see [`../06_nanoaod_branch_access.md`](../06_nanoaod_branch_access.md).)
3. **ΔR-match** each additional B-hadron to the closest b-jet within ΔR < 0.4.
4. **Count** distinct matched b-jets, and b-hadrons per jet.
5. **C-jets** are handled the same way, but only if there is no additional
   b-jet (the AN's "tt+C only if no additional b").
6. **Decide** the category from `(n_add_bjet, hadron multiplicity)`.

Core of the decision (from the matched-jet map):

```python
n_add_bjet = len(jet_bh_map)
if n_add_bjet == 1:
    n_had = next(iter(jet_bh_map.values()))
    return CAT_ADD1BJET_1HAD if n_had == 1 else CAT_ADD1BJET_2HAD
if n_add_bjet >= 2:
    return CAT_ADD2BJET
# else fall through to the c-jet check, then CAT_LIGHTFLAVOUR
```

The top-ancestor test is a known weak point (a simple mother-chain walk,
`max_depth=30`, vs the POG's parton-history walker) and is the reason
`genTtbarId` is primary and this path is only the cross-check:

```python
def _has_top_ancestor(event, idx, nGP, max_depth=30):
    cur = idx
    for _ in range(max_depth):
        mother = event.GenPart_genPartIdxMother[cur]
        if mother < 0 or mother >= nGP:
            return False
        if abs(event.GenPart_pdgId[mother]) == 6:
            return True
        cur = mother
    return False
```

### Output: twelve branches per event

```
Primary set (genTtbarId)                Cross-check set (GenPart)
ttCat_LightFlavour      : Bool          ttCatXval_LightFlavour   : Bool
ttCat_AddCjet           : Bool          ttCatXval_AddCjet        : Bool
ttCat_Add1Bjet_1Had     : Bool          ttCatXval_Add1Bjet_1Had  : Bool
ttCat_Add1Bjet_2Had     : Bool          ttCatXval_Add1Bjet_2Had  : Bool
ttCat_Add2Bjet          : Bool          ttCatXval_Add2Bjet       : Bool
ttCatSource             : Int           ttCatXvalSource          : Int
```

Exactly one Bool is True per ttbar event in each set. Source codes:

| `ttCatSource` | meaning | | `ttCatXvalSource` | meaning |
|---|---|---|---|---|
| 0 | genTtbarId decoded OK | | 0 | GenPart algorithm ran OK |
| 2 | `genTtbarId == -1`, not ttbar | | 2 | primary said not-ttbar, xval skipped |
| 3 | `genTtbarId` branch missing | | 3 | `GenPart_*`/`GenJet_*` missing |

(Code 1 was a removed fallback path, kept reserved.) **Note on data:** real
data has no gen branches, so it produced `ttCatSource = 3` and
`ttCatXvalSource = 3` (not 2). A known cosmetic consequence was that the
endJob `NO_GENTTBARID > 5%` warning fired on every data job.

---

## 3. Module skeleton — the reusable shape

This is the part worth internalizing for the next custom module. The full
source is [`legacy/code/modules/ttbarCategorizer.py`](legacy/code/modules/ttbarCategorizer.py);
the load-bearing structure is:

```python
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
try:
    from ._nanoaod_compat import to_int, safe_len   # local
except ImportError:
    from _nanoaod_compat import to_int, safe_len    # CRAB flat cwd

CATEGORIES  = ("ttCat_LightFlavour", "ttCat_AddCjet", "ttCat_Add1Bjet_1Had",
               "ttCat_Add1Bjet_2Had", "ttCat_Add2Bjet")
XCATEGORIES = tuple("ttCatXval_" + c.split("ttCat_")[1] for c in CATEGORIES)

class TtbarCategorizer(Module):
    def __init__(self, *, debug_csv=False, debug_csv_path=None, quiet=False):
        super().__init__()
        # ... store options, init endJob counters ...

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        # (a) defense in depth: re-enable required INPUT branches
        existing = {b.GetName() for b in inputTree.GetListOfBranches()}
        for name in REQUIRED_INPUTS:
            if name in existing:
                inputTree.SetBranchStatus(name, 1)
        # (b) detect branch presence by reading the branch list directly,
        #     NOT hasattr(event, ...) — the Event wrapper raises RuntimeError
        #     (which hasattr does NOT catch) when a branch is missing.
        self._has_genttbarid = "genTtbarId"    in existing
        self._has_genpart    = "GenPart_pdgId" in existing
        self._has_genjet     = "GenJet_pt"     in existing
        # (c) the base class does NOT inject self.out — capture it yourself
        self.out = wrappedOutputTree
        # (d) declare OUTPUT branches
        for cat in CATEGORIES:  wrappedOutputTree.branch(cat, "O")   # Bool
        wrappedOutputTree.branch("ttCatSource", "I")                 # Int
        for x in XCATEGORIES:   wrappedOutputTree.branch(x, "O")
        wrappedOutputTree.branch("ttCatXvalSource", "I")

    def analyze(self, event) -> bool:
        for cat in CATEGORIES:  self.out.fillBranch(cat, False)      # reset
        for x   in XCATEGORIES: self.out.fillBranch(x, False)
        label, source = self._classify_primary(event)               # genTtbarId
        if label in CATEGORIES: self.out.fillBranch(label, True)
        self.out.fillBranch("ttCatSource", source)
        xlabel, xsource = self._classify_xval(event, source)        # GenPart
        if xlabel in XCATEGORIES: self.out.fillBranch(xlabel, True)
        self.out.fillBranch("ttCatXvalSource", xsource)
        # ... bookkeeping for the endJob confusion matrix ...
        return True            # categorizer never drops events
```

Four reusable lessons embedded above, each from a real bug:

1. Declare branches in `beginFile`; **capture `self.out` yourself**.
2. Detect input-branch presence via `inputTree.GetListOfBranches()`, **not
   `hasattr(event, ...)`** — the wrapper raises `RuntimeError` on a missing
   branch and `hasattr` does not catch it, crashing the job (this is how the
   categorizer broke on data NanoAOD).
3. Re-enable required input branches with `SetBranchStatus(name, 1)` as
   defense in depth against driver-level `branchsel` regressions.
4. **Reset all output branches at the top of `analyze`**, then set the chosen
   one — otherwise an unset branch keeps a stale value.

### CLI flags via the env-var + factory pattern

The module took three optional debug flags **without coupling the driver to
its class**: the driver set environment variables from its argparse flags,
and a factory read them at import time when building `MODULES`.

```python
def make_default_module():
    import os
    return TtbarCategorizer(
        debug_csv      = os.environ.get("TTCAT_DEBUG_CSV") == "1",
        debug_csv_path = os.environ.get("TTCAT_DEBUG_CSV_PATH") or None,
        quiet          = os.environ.get("TTCAT_QUIET") == "1",
    )
MODULES = [make_default_module()]
```

Driver side (`run_postproc.py`) set `os.environ["TTCAT_*"]` from
`--ttcat-debug-csv` / `--ttcat-debug-csv-path` / `--ttcat-quiet` **before
importing the module**. The three flags controlled only diagnostics; the
production branches were always written. Use this pattern for any future
module that needs CLI knobs.

---

## 4. endJob report and the confusion matrix

At endJob (unless `--ttcat-quiet`) the module printed to stderr: total events
and rate (Hz); the source-code distribution (with the `NO_GENTTBARID > 5%`
warning box); per-category counts from the primary path; and a **5×5
confusion matrix** (rows = primary genTtbarId decision, columns = GenPart
xval decision). The diagonal is agreements. A healthy ttbar run shows >97% on
the diagonal with small off-diagonal entries near the 1Bjet↔2Bjet boundary —
this matrix was the primary tool for spotting algorithmic discrepancies.

The optional per-event debug CSV (`--ttcat-debug-csv`, **off by default,
never staged out by CRAB**) wrote one row per ttbar event:

```
run, lumi, event, ttCatSource, ttCatXvalSource,
genTtbarId, genTtbarId_mod100, cat_production, cat_xval, agree
```

It contained nothing beyond what the two branch sets already held; it existed
purely for offline awk/diff convenience.

---

## 5. Output slimming — the keep/drop list

The categorizer ran with an aggressive **slimming** list (in contrast to the
current `keep *`). The full list is preserved at
[`legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt`](legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt);
its shape was:

```
drop *
# global event info: run, luminosityBlock, event, PV_*, fixedGridRhoFastjetAll
# AK4 jets: Jet_pt/eta/phi/mass/jetId/puId/btagDeepFlav*/bRegCorr/...
# AK8 fatjets: FatJet_* (mass, tau, subjet links)
# MET, leptons (Muon_*, Electron_*), Flag_*, HLT_* (signal + reference)
# gen weights: genWeight, Generator_weight, LHEPdfWeight, LHEScaleWeight
# pileup: Pileup_nTrueInt, Pileup_nPU
# --- required INPUTS for the categorizer ---
keep genTtbarId
keep nGenPart GenPart_pt/eta/phi/mass/pdgId/status/statusFlags/genPartIdxMother
keep GenJet_hadronFlavour
# --- the categorizer OUTPUTS ---
keep ttCat_*           # 5 primary bools + ttCatSource
keep ttCatXval_*       # 5 cross-check bools + ttCatXvalSource
```

Two things to copy for a future slimming module: (1) you must **keep the gen
input branches the module reads**, or it silently misclassifies / fails on
output writing; (2) you must **keep the output branches the module writes**,
listed explicitly. The MC-vs-data branch inventories used to build this list
are in [`legacy/code/branches/branch_2017UL/`](legacy/code/branches/branch_2017UL/)
(they were produced by a branch-diff tool that has since been removed; the inventories themselves are preserved here).

---

## 6. Optional skim cut — the gatekeeper pattern

Separately from categorization, NtupleForge could apply an event **skim**.
The recommended way was a `Module` whose `analyze` returns `False` to drop an
event — see the still-live [`../modules/jetsMETcut.py`](../../modules/jetsMETcut.py):

```python
class JetsMETCut(Module):
    def analyze(self, event):
        if self._read_or(event, "MET_pt", 0.0) < self.met_thr:  return False
        if self._read_or(event, "nJet", 0)   < self.njet_thr:   return False
        return True
MODULES = [JetsMETCut(njet_thr=6, met_thr=300.0)]
```

Design rule observed there: **the skim is a gatekeeper only — it drops whole
events, it does NOT filter object collections.** "Good jet" definitions
change between analysis phases (pT cuts, ID working points), so hardcoding
object selection at production time would force a full ntuple re-production
on every definition change. Object-level selection belongs in the analyzer
(compiled C++ / RDataFrame), which is also faster and preserves rejected
objects for sideband and fake-rate studies.

(The driver's hardcoded `CUT_STRING` is an alternative for *simple* TTree
cuts, but complex cut strings are avoided on the command line to prevent CRAB
submission quoting errors — put non-trivial logic in a module.)

---

## 7. Running it — local and CRAB

**Local validation** (writes both branch sets; per-event CSV for inspection):

```bash
python3 script/run_postproc.py <input.root> \
  -I modules.ttbarCategorizer:MODULES \
  -b branches/branch_ttHHto4b_hadronic_2017UL.txt \
  -N 1000 \
  --ttcat-debug-csv --ttcat-debug-csv-path /tmp/ttcat_check.csv
```

**CRAB campaign** — driven by
[`legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml`](legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml),
whose two load-bearing fields were:

```yaml
analysis_module: ["modules/ttbarCategorizer.py", "MODULES"]
branch_file:     "branches/branch_ttHHto4b_hadronic_2017UL.txt"
```

`submit_crab.py` shipped `script/run_postproc.py`, the module file, every
`modules/_*.py` helper (so `_nanoaod_compat.py` rode along), and the branch
file; the worker reconstructed the command from `crab_args.txt`. The dataset
list in that YAML (signal, ttbar, QCD HT-binned, single-top, diboson,
V+jets, the 4FS `TTbb_4f` stitching samples, and data) is still useful and
was carried into the live passthrough config.

---

## 8. Validation against the analyzer

Because both algorithms were written into the ntuple, the
analyzer↔ntuplizer cross-check reduced to a per-event branch comparison
inside the analyzer — there was **no need to re-run the categorizer** on the
analyzer side:

```cpp
bool prod_a2b = event.ttCat_Add2Bjet;
bool xval_a2b = event.ttCatXval_Add2Bjet;
if (prod_a2b != xval_a2b) { /* record discrepancy */ }
```

The architectural rule was: **the ntuplizer is the single source of truth for
categorization.** Any analyzer-side `computeTtCategory` had to be a thin
reader of the `ttCat_*` branches, never a third re-implementation.

### Skim-efficiency / bookkeeping QA — `validate_events.py`

Separately from the physics-content checks above, the archived
[`legacy/code/tools/validate_events.py`](legacy/code/tools/validate_events.py)
verified, after a production run, how many generated events survived a skim:

```
skim_eff = Events.num_entries  /  Σ Runs.genEventCount   (summed over files)
```

It works because the post-processor slims only the `Events` tree and copies
the `Runs` tree (per-lumi-block accounting) through untouched; each output
file holds the partial `genEventCount` for the lumi-blocks it processed, so
the totals must be **summed across all files**
(`python3 validate_events.py "output_dir/*.root"`). It also flagged
unreadable/zombie files and auto-detected data (no `genEventCount`).

Its limits — important to keep in mind if a future skim reuses it:

* **Unweighted count only** (`genEventCount`, not `genEventSumw`). For NLO
  samples with negative weights (amcatnlo: `TTZToBB`, `TTTT`, single-top
  `s`-channel, …) this is a raw event-count ratio, **not** a physical
  efficiency — normalize those by `genEventSumw`.
* **Full-run only.** With `-N`/`--first-entry` the numerator is capped but the
  denominator is the file's full `genEventCount`, giving a fake-small ratio.
* **Cannot detect missing jobs.** A failed job that produced no output is
  simply absent from the glob; numerator and denominator drop together, so the
  ratio looks fine while the total yield is wrong. Cross-check the job
  count / DAS expected total separately (e.g. via
  [`../script/parse_crab_status.py`](../../script/parse_crab_status.py)).
* **No physics-content check** — that is §3–§5 and the cross-check above.

The tool is archived rather than live because the current pipeline is a full
passthrough (no skim to measure). Copy it back into `script/` if you
reintroduce a skim.

---

## 9. How to rebuild an equivalent (checklist)

1. Copy [`legacy/code/modules/ttbarCategorizer.py`](legacy/code/modules/ttbarCategorizer.py)
   and [`legacy/code/modules/_nanoaod_compat.py`](legacy/code/modules/_nanoaod_compat.py)
   into `modules/`.
2. Copy [`legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt`](legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt)
   into `branches/` (or write a new keep list: gen inputs + your outputs).
3. Point a CRAB config at the module + branch file (template:
   [`legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml`](legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml)).
4. Validate locally with `--ttcat-debug-csv` on ~1k events of a known
   sample; confirm the endJob confusion-matrix diagonal is >97% and the
   source distribution looks sane (no spurious `NO_GENTTBARID` on MC ttbar).
5. Submit, then check job status (`submit_crab.py --status`, or parse logs
   with the live `script/parse_crab_status.py`).

For the framework mechanics underlying every step above, see
[`04_architecture.md`](../04_architecture.md). For the compat shim, see
[`06_nanoaod_branch_access.md`](../06_nanoaod_branch_access.md).
