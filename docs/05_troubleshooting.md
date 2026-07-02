# Troubleshooting Log & Validation

This is the consolidated record of **every problem hit during development**,
with its symptom, the actual error/log signature, the root cause, the fix,
and how the fix was validated — followed by how the pipeline's **validation**
mechanisms work. When you hit a new problem, add an entry here (see
[`07_DeveloperGuideline.md`](07_DeveloperGuideline.md)).

Many of these surfaced together during the 2026-04-06/07 ttbarCategorizer
debugging session ("five infrastructure bugs in sequence"); two of them are
also captured in code as the [`_nanoaod_compat.py`](ttHH/legacy/code/modules/_nanoaod_compat.py)
shim (deep dive: [`06_nanoaod_branch_access.md`](06_nanoaod_branch_access.md)).

---

## Part A — Incident log

### A0. Renamed PyROOT helper not shipped to CRAB worker → import fails

- **Symptom.** First `config_CPV2017UL` CRAB submission: every job fails fast
  (~16 s, exit 195). `run_postproc` log shows
  `Failed to import module 'topCPVCategorizer': attempted relative import with no
  known parent package`. The branch-selection file loads fine just before.
- **Signature.** The module's flat import `from nanoaod_branch_access import …`
  raised `ImportError` (helper absent on the worker), so the relative fallback
  `from .nanoaod_branch_access import …` ran and raised *"attempted relative import
  with no known parent package"* — because CRAB imports the analysis module **flat**
  (top-level, no parent package).
- **Root cause (two coupled bugs).** (1) **Shipping:** `crab/submit_crab.py`
  auto-included helpers by globbing `modules/_*.py` — a *single-underscore*
  convention. Renaming `_nanoaod_compat.py` → `nanoaod_branch_access.py` (dropping
  the underscore, for a clearer name) silently removed it from that glob, so the
  helper was never put in the sandbox. (2) **Import:** the module tried a relative
  import as fallback, which can never work in CRAB's flat import context.
- **Fix.** (1) `submit_crab.py` now ships **every** sibling `.py` in the module's
  directory (except the analysis module and dunders), decoupling a helper's name
  from whether it ships. (2) `topCPVCategorizer.py` puts its own directory on
  `sys.path` via `__file__` before importing, so the flat import resolves the
  sibling regardless of package context:
  ```python
  import os, sys
  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
  from nanoaod_branch_access import to_int, safe_len
  ```
- **Validated by.** In-container simulation of CRAB's `importlib.import_module(
  "topCPVCategorizer")` (flat, helper dir not pre-on-path) now imports cleanly; the
  sandbox helper-glob now lists `nanoaod_branch_access.py`. Confirm on lxplus with a
  real resubmission.

### A1. `UChar_t` branches compare as `bytes`, silently → wrong category

- **Symptom.** 1000/1000 `TTHHTo4b` signal events classified as `tt+LF`. No
  error, no warning — the categorizer simply saw zero additional b-jets in
  every event.
- **Signature.** `event.GenJet_hadronFlavour[j] == 5` is **always `False`**.
  The element is a 1-byte `bytes` object `b'\x05'`, and `b'\x05' == 5` is
  `False` in Python.
- **Root cause.** PyROOT exposes `UChar_t` elements (NanoAOD ID/flavour
  fields) as `bytes`, not `int`, when read through the NanoAOD-tools `Event`
  wrapper on the raw-proxy access path (ROOT ≥ 6.30).
- **Fix.** Coerce at every `UChar_t` comparison site with `to_int()`:
  `if to_int(event.GenJet_hadronFlavour[j]) == 5:`. Idempotent, free on real
  ints. Affected branches include all `*_hadronFlavour`, `*_partonFlavour`,
  `Jet_jetId`, `Jet_puId`, `FatJet_jetId`, some lepton IDs.
- **Validated by.** Category distribution became physical; the GenPart
  cross-check confusion-matrix diagonal recovered to >97%.

### A2. Raw `TTreeReaderArray` has no `len()`

- **Symptom.** `TypeError` raised on `len(event.GenPart_pdgId)`.
- **Root cause.** The raw `ROOT.TTreeReaderArray<T>` proxy does not implement
  `__len__`; it only supports `GetSize()` and integer indexing.
- **Fix (as of 2026-04).** Use `safe_len(branch, branch_name=...)` — a 3-tier
  fallback (`len()` → `GetSize()` → indexing probe) instead of raw `len()`.
- **⚠️ SUPERSEDED 2026-07-01.** The indexing-probe tier of that fallback is
  ROOT undefined behaviour and segfaulted in production (**A12**). The current
  rule is: collection lengths come from the **count branch** via
  `count(event, "X")`; `safe_len` is de-fanged (no probe) and deprecated for
  collections. See A12 and `06_nanoaod_branch_access.md` Pitfall 2.
- **Validated by (historical).** Loops iterated over the true element count;
  self-test in the shim.

### A3. Scalar counters (`nGenPart`, `nGenJet`) are not a reliable length

- **Symptom.** Everything classified `tt+LF`; the categorizer found zero
  gen-jets in events that clearly had them.
- **Signature.** `range(nGenJet)` evaluated to `range(0)`, so the gen-jet
  loop body never ran. The standalone diagnostic printed:
  `*** nGenJet counter is BROKEN in N events! *** range(nGenJet)=range(0) so
  NO GenJets were found -> everything classified as tt+LF`.
- **Root cause.** On the raw-proxy access path the scalar `n<Coll>` counter
  branch cannot be trusted as the array length.
- **Fix (as of 2026-04**, commit `1fb657b`**).** Use the **array length** via
  `safe_len()` on the vector branch (`safe_len(event.GenJet_pt)`), never the
  `n<Coll>` counter, for loop bounds.
- **⚠️ SUPERSEDED 2026-07-01 — the diagnosis was a mis-attribution.** The
  broken counters were a *symptom of A4* (input keep/drop → zombie branches),
  observed in the same session. Once A4 was fixed (`branchsel=None`, input
  read in full), the `n<Coll>` counters became reliable again; and the
  array-length workaround this entry mandated is what segfaulted in **A12**.
  Current rule: lengths from the **count branch** (`count(event, "X")`);
  never probe the array. See A12, `06_nanoaod_branch_access.md` Pitfall 2, and
  `03_DECISIONS.md` → D-2026-07-01-count-branch-length.
- **Validated by (historical).** A diagnostic that compared `counter` vs
  `array size` per event went to 0 mismatches after the fix — consistent with
  A4 being the true cause: after `branchsel=None` both sides read correctly.

### A4. Keep/drop file applied to the input tree → zombie branches

- **Symptom.** 1000/1000 events fell into the categorizer's `NO_GENTTBARID`
  path **despite** `keep genTtbarId` being present in the branch file.
- **Root cause.** The driver passed the keep/drop file as *both* `branchsel`
  (input) and `outputbranchsel` (output). `drop *` thus hit the input tree;
  re-enabling only the listed `keep` branches, combined with how nanoAOD-tools
  normalizes wildcard vs explicit rules, left vector branches
  (`genTtbarId`, `GenPart_*`) in a `hasattr=True / len()=0` **zombie state**
  on input — present but empty.
- **Fix.** Never filter the input tree: `branchsel=None` (read everything),
  `outputbranchsel=<keep/drop file>` (filter only the output). See
  [`04_architecture.md`](04_architecture.md) §7.
- **Validated by.** endJob source distribution showed `GENTTBARID` ≈ 100% on
  MC ttbar, and the per-category counts matched expectations.

### A5. `hasattr` crashes the job on data NanoAOD

- **Symptom.** Job crashes when processing data files (which have no gen
  branches at all).
- **Signature.** A `RuntimeError` propagates out of the `Event` wrapper on
  access to a missing branch. Python's `hasattr` only swallows
  `AttributeError`, **not** `RuntimeError`, so the exception escapes and
  kills the job — the opposite of the intended "branch absent → skip".
- **Root cause.** Branch-presence detection via `hasattr(event, name)`.
- **Fix.** Detect presence by reading the input tree's branch list directly
  in `beginFile`: `existing = {b.GetName() for b in inputTree.GetListOfBranches()}`;
  `self._has_genttbarid = "genTtbarId" in existing`. This avoids the wrapper
  entirely.
- **Validated by.** Data jobs run to completion; gen-dependent paths
  short-circuit cleanly (source code 3).

### A6. `tt+2b` (code 52) misclassification

- **Symptom.** Events with one additional b-jet containing ≥2 b-hadrons were
  assigned to the wrong category.
- **Root cause.** The `(n_add_bjet, hadron-multiplicity)` decision did not
  correctly route `n_add_bjet == 1 and n_had ≥ 2` to `tt+2b`.
- **Fix** (commit `619b5eb`). Decision: `n_add_bjet == 1` → `Add1Bjet_1Had`
  if exactly one b-hadron else `Add1Bjet_2Had`; `n_add_bjet ≥ 2` →
  `Add2Bjet`. Also added the debug mode and the GenPart cross-validation in
  the same commit.
- **Validated by.** The debug CSV `agree` column and the confusion matrix at
  the 51/52/53 boundary.

### A7. CRAB stageout filename mismatch (exit 60302)

- **Symptom** (reported 2025-12-15). The job processed successfully but
  failed during **stageout**.
- **Signature.**
  ```
  ====== Starting to check if user output files exist.
  Output file slimmed.root exists.
  Output file crab_args.txt exists.
  ERROR: Output file tree.root does not exist.
  Setting stageout wrapper exit info to {'exit_code': 60302, 'exit_acronym': 'FAILED', ...}
  ```
- **Root cause.** The YAML/driver produced `slimmed.root`, but CRAB's
  internal config (derived from `crab/PSet.py`'s `PoolOutputModule` fileName)
  still expected the default `tree.root`. CRAB validates the staged output
  against the PSet output name and flagged the job failed.
- **Fix.** Make the output filename agree on both sides. Currently
  `crab/PSet.py` (`fileName`) and `crab/submit_crab.py` (`out_name`) both use
  `slimmedNtuple.root`.
- **Status / permanent fix (open).** The value is still **hardcoded in two
  places**. The robust fix is to have `submit_crab.py` override the PSet
  output filename from the YAML at submission time (single source of truth).
  Until then: if you change one, change the other.

### A8. `NO_GENTTBARID > 5%` warning fires on every data job (cosmetic)

- **Symptom.** The endJob warning box ("> 5% of events lack genTtbarId …
  check the input file production config") prints on **every** data job.
- **Root cause.** Data has no gen branches → `ttCatSource = 3` for 100% of
  events. The warning was designed to flag *abnormal MC ttbar* samples, and
  does not special-case data.
- **Status.** Cosmetic; not fixed. If reinstating the categorizer, gate the
  warning on "MC and not 100%".

### A9. `jetsMETcut.py` doc/default mismatch (cosmetic)

- **Symptom.** Confusion about the active thresholds. The docstring and
  `__init__` defaults say `njet ≥ 4, MET > 150`, but the shipped `MODULES`
  constructs `JetsMETCut(njet_thr=6, met_thr=300.0)`.
- **Status.** Harmless (the `MODULES` value is what runs); align the
  docstring/defaults when convenient.

### A10. CRAB resubmit keeps failing on memory / walltime

- **Symptom.** A handful of jobs stay `failed`; re-running submit (or
  `--resubmit`) resubmits them and they fail again the same way. Typical
  CRAB/HTCondor exit codes: **50660** (job used too much memory), **50664**
  (job ran past the wall-clock limit), **50661** (too much disk).
- **Cause.** `submit_crab.py` issues a **plain** `crabCommand('resubmit', …)`
  with **default** resources — by design, to keep the tool simple. A plain
  resubmit re-runs the job under the *same* limits, so a memory/walltime
  failure recurs.
- **Fix.** Resubmit those tasks **by hand** with raised limits, directly in the
  CRAB project dir:
  ```bash
  crab resubmit -d <workArea>/crab_<reqName> \
    --maxmemory=4000 --maxjobruntime=2700
  ```
  Tune `--maxmemory` (MB) / `--maxjobruntime` (min) to the failure. Transient
  site/stageout failures (not resource-related) do *not* need this — a plain
  resubmit is enough.
- **Note.** `submit_crab.py` prints this reminder at the end of every
  submit/resubmit run so it is hard to miss. `--report` makes the failing
  tasks easy to spot (non-zero `fail` column).


### A11. MC-only guard passed a data file → `Unknown branch GenPart_pdgId` crash

- **When.** 2026-07-01, first `config_CPV2017UL` CRAB production
  (SingleElectron_Run2017B, T2_US_Wisconsin).
- **Symptom.** Every data job fails with exit 195 (long code 50115). The
  event loop *starts* (`Pre-select 2026227 entries`) and dies on the first
  event.
- **Signature.**
  ```
  File "/srv/topCPVCategorizer.py", line 180, in analyze
    n = safe_len(event.GenPart_pdgId, branch_name="GenPart_pdgId")
  File ".../framework/treeReaderArrayTools.py", line 80, in readBranch
    raise RuntimeError("Unknown branch %s" % branchName)
  RuntimeError: Unknown branch GenPart_pdgId
  ```
- **Root cause (two coupled mistakes).** (1) **Config:** the data samples were
  submitted with the MC branch list *and* the MC-only gen module
  (`-b branch_CPV_Run2_MC.txt -I topCPVCategorizer:MODULES`) — the per-tier
  `branch_file`/module split tracked as OPEN in `01_STATUS.md` was not yet
  wired. (2) **Guard:** the module's `beginFile` protection —
  `if inputTree.GetBranch("GenPart_pt") is None: raise` — **did not fire** on
  the data file: through the nanoAOD-tools `InputTree` wrapper, `GetBranch`
  did not report the branch as absent, so the job proceeded into `analyze`
  and crashed on the first gen read. Same family as A5 (`hasattr` also cannot
  be trusted for presence).
- **Fix.** (1) Presence detection moved to the branch list, the A5 pattern:
  ```python
  existing = {b.GetName() for b in inputTree.GetListOfBranches()}
  self._has_genpart = "GenPart_pdgId" in existing
  ```
  (2) Behaviour on absence changed from *raise* to a logged **no-op for that
  file**: `beginFile` defines no output branches and `analyze` early-returns
  `True`. Gen content is a property of the *input*, not a code bug, and a
  crash only makes CRAB burn its 3 automatic retries on the same file. The
  config-level split (data configs without the gen module, using
  `branch_CPV_Run2_Data.txt`) remains the real fix and stays OPEN in
  `01_STATUS.md`.
- **Validated by.** In-container stub run: a branch list without `GenPart_*`
  → `_has_genpart=False`, zero branches defined, zero filled, events pass.
  **Unverified on real data — rerun one data task on lxplus/CRAB to confirm.**

### A12. `safe_len` out-of-bounds indexing probe → segfault on MC (raw `TTreeReaderArray`)

- **When.** 2026-07-01, same campaign (TTZToQQ_TuneCP5_13TeV_amcatnlo,
  T1_US_FNAL). Every MC job dies in ~20 s, exit 195 (50115).
- **Symptom / signature.** The tell-tale pair of lines:
  ```
  [nanoaod_branch_access.safe_len] len() unsupported for 'GenPart_pdgId', falling back to GetSize()/probe.
  *** Break *** segmentation violation
  ```
  with the crash stack in ROOT:
  ```
  #6 ROOT::Detail::TBranchProxy::Setup()
  #7 (anonymous namespace)::TObjectArrayReader::At(TBranchProxy*, unsigned long)
  ```
- **Root cause.** In `CMSSW_14_2_1` (ROOT 6.30) the wrapper hands back
  `GenPart_pdgId` as a **raw `TTreeReaderArray` proxy**: `len()` raises
  `TypeError`, so `safe_len` fell through to its fallbacks — `GetSize()` and,
  ultimately, an **indexing probe** that increments `branch[i]` until an
  exception. But `TTreeReaderArray::At(i)` for `i >= size` is **undefined
  behaviour**: it dereferences an unconfigured `TBranchProxy` and segfaults.
  There is no Python exception to catch; the probe was a loaded gun by design.
  The probe existed because of A3's advice ("`nGenPart` is unreliable, use
  the array length") — which itself was a **mis-attribution**: the broken
  counters A3 observed were a symptom of A4 (input keep/drop zombie
  branches). A4's fix (`branchsel=None`) restored the counters; the stale
  advice and its dangerous workaround survived until they crashed here.
- **Fix.** Lengths now come from the **count branch** — the scalar the
  NanoAOD format guarantees equals the array length and that reads cleanly as
  an `int`:
  ```python
  n   = count(event, "GenPart")        # event.nGenPart
  ngj = count(event, "GenJet")         # event.nGenJet
  nvt = opt_count(event, "GenVisTau")  # 0 if absent
  ```
  `count`/`opt_count` were added to `modules/nanoaod_branch_access.py`;
  `safe_len` was **de-fanged** (no more probing; it fails fast with
  `TypeError`) and deprecated for collection lengths. Element access stays
  in-bounds (`arr[i]` for `i in range(n)`), which is safe. Equivalent to the
  standard `len(Collection(event, "GenPart"))` (same `nGenPart` read) without
  per-event `Object` construction in the hot loop. A3's guidance is
  superseded — see the corrected history in
  [`06_nanoaod_branch_access.md`](06_nanoaod_branch_access.md) Pitfall 2 and
  `03_DECISIONS.md` → D-2026-07-01-count-branch-length.
- **Validated by.** In-container stub run over a synthetic ttbar event: 46
  branches written, `isSignal=True`, `GenPar_Count=12`, `GenBJet_Count=1`,
  UChar_t coercion intact. **Unverified against real NanoAOD — no ROOT in the
  dev container.** On lxplus: run `-N 10` locally on a TTZToQQ file, then
  `script/validate_topcpvcat.py` for byte-identity, then resubmit.

---

## Part B — Validation

How correctness was (and can again be) checked. Two layers: **physics-content
validation** of the categorization, and **bookkeeping validation** of the
skim/job output.

### B1. Two independent estimators + confusion matrix

The categorizer ran two genuinely different algorithms and wrote both to the
ntuple: the primary `genTtbarId` decode (`ttCat_*`) and an independent
raw-GenPart re-derivation (`ttCatXval_*`). At endJob it printed a **5×5
confusion matrix** (rows = primary decision, columns = GenPart cross-check).

- **Read it like this.** Diagonal = agreement. A healthy ttbar run is >97% on
  the diagonal, with the small off-diagonal mass concentrated at the
  `1Bjet ↔ 2Bjet` (51/52/53) boundary — where the two algorithms legitimately
  disagree on single-vs-overlapping hadrons.
- **What a bad matrix tells you.** A large off-diagonal block, or a collapsed
  column/row, signals a real bug (e.g. all of A1/A3/A4 produced a degenerate
  matrix — everything in the `LightFlavour` row/column).

### B2. Per-event debug CSV

`--ttcat-debug-csv` wrote one row per ttbar event with both algorithms'
decisions side by side (`cat_production`, `cat_xval`, `agree` ∈ {Y,N,n/a}),
plus `run/lumi/event` and `genTtbarId`. It added nothing beyond the two
branch sets — purely an offline awk/diff convenience for chasing specific
disagreements. **Off by default; never staged out by CRAB.**

### B3. endJob source distribution

The source-code histogram (`GENTTBARID` / `NO_TTBAR` / `NO_GENTTBARID`)
catches abnormal samples at a glance — e.g. a misconfigured ttbar sample
missing `genTtbarId`, or the A4 zombie-branch failure (which showed 100%
`NO_GENTTBARID`).

### B4. Analyzer ↔ ntuplizer cross-check is trivial by construction

Because both algorithms live in the ntuple, the analyzer-side check is a
per-event branch comparison — **no re-running** the categorizer:

```cpp
if (event.ttCat_Add2Bjet != event.ttCatXval_Add2Bjet) { /* record */ }
```

Architectural rule: **the ntuplizer is the single source of truth.** Any
analyzer-side category function must *read* the `ttCat_*` branches, never
re-implement the algorithm (that would create a third source of truth).

### B5. Skim-efficiency / bookkeeping (archived tool)

When a skim is in use, output bookkeeping was validated by comparing surviving
events against generated events: `skim_eff = Events.num_entries / Σ
Runs.genEventCount`, summed across all output files (the post-processor copies
the `Runs` tree through, so each file carries the partial `genEventCount` for
its lumi-blocks). The tool that did this, its method, and its important limits
(unweighted count only; full-run only; cannot detect entirely-missing jobs)
are documented with the now-archived
[`ttHH/02_legacy_ttbar_pipeline.md`](ttHH/02_legacy_ttbar_pipeline.md) §8 →
[`ttHH/legacy/code/tools/validate_events.py`](ttHH/legacy/code/tools/validate_events.py).
The current full-passthrough pipeline has no skim to measure; copy the tool
back into `script/` if you reintroduce one.
