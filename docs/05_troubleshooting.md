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
  `forgedNtuple.root` (renamed from `slimmedNtuple.root` on 2026-07-26, D-F;
  file discovery downstream still accepts both prefixes).
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
  `branch_CPV_Run2_Data.txt`) is the real fix — **done 2026-07-02**:
  per-tier `config_CPV<era>_{Data,MC}.yaml`, combined configs removed
  (`03_DECISIONS.md` → D-2026-07-02-per-tier-configs).
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


### A13. Reader objects invalidated by mid-loop lazy creation → null-pointer / segfault on in-bounds access

- **When.** 2026-07-02, first CRAB run of the A11/A12-fixed module
  (`config_CPV2017UL_MC`). Every MC job dies on the first event.
- **Symptom / signature.** Two faces of the same corpse:
  - DYJetsToLL: a *catchable* error on a plainly **in-bounds** element read —
    ```
    File "/srv/topCPVCategorizer.py", line 225, in analyze
      m = mom[i]
    ReferenceError: ... TTreeReaderArray<int>::operator[] ...
      attempt to access a null-pointer
    ```
  - QCD_HT2000toInf: hard segfault, stack ending in
    `TObjectArrayReader::At(TBranchProxy*, unsigned long)` (no
    `safe_len` fallback message — this is NOT A12 recurring).
- **Root cause (proved from the framework source,
  `PhysicsTools/NanoAODTools/python/postprocessing/framework/treeReaderArrayTools.py`
  @ CMSSW_14_2_X).** `readBranch()` creates readers lazily on first access, and
  `_makeArrayReader`/`_makeValueReader` call **`_remakeAllReaders(tree)`**
  whenever the TTreeReader is already reading: a **brand-new TTreeReader** is
  built, every known reader is **recreated as a new object**, and
  `tree._ttras`/`_ttrvs`/`_ttreereader` are **replaced**. The old TTreeReader
  loses its last reference and is destructed; every reader object handed out
  *before* the remake now dangles. Our `analyze()` bound locals back-to-back —
  ```python
  pdg = event.GenPart_pdgId      # remake; pdg on reader v_k
  flg = event.GenPart_statusFlags  # remake -> pdg dangles
  mom = event.GenPart_genPartIdxMother  # remake -> flg dangles
  ... 5 more ...                 # by the loop, pdg..phi ALL dangle
  for i in range(n): m = mom[i]  # first element read -> boom
  ```
  Eight first-accesses = seven remakes on event 0; the first element access hits
  a dangling proxy (ReferenceError or segfault depending on teardown timing).
  Note the entry list is NOT involved (the "Pre-select ... (100.00%)" line
  prints unconditionally, `elist=None` here), and this is
  **environment-independent** — a local lxplus run of the same code crashes the
  same way on the first MC event.
- **Why A12's fix didn't cover it.** A12 removed the out-of-bounds *probe*
  (length source). This is the orthogonal hazard: *holding* reader objects
  across later first-accesses. `count()` itself is immune (it re-fetches the
  value reader from the live dict on every call and never stores it).
- **Fix (canonical declare-then-read).**
  1. **Pre-register every reader in `beginFile`** via
     `inputTree.arrayReader(b)` / `inputTree.valueReader(c)` for all branches in
     `GEN_ARRAY_BRANCHES` / `GEN_COUNTER_BRANCHES` — `eventLoop` calls
     `beginFile` *before* the first `gotoEntry`, so the TTreeReader is still
     clean and readers are added **without any remake**; afterwards no branch
     access ever creates a reader, so the loop is remake-free and bound locals
     stay valid.
  2. Also fail fast in `beginFile` if GenPart is present but any required gen
     branch is missing (partial input), instead of dying mid-loop.
  3. Safety net `_read_arrays(event, *names)`: binds a batch and, if the reader
     version changed during the pass (i.e. a future edit reads an unregistered
     branch), re-binds once on the fresh readers and warns to extend the
     registration list.
- **Validated by.** Framework-level test in the dev container (`/tmp/fw_test.py`)
  running the **actual CMSSW_14_2_X** `treeReaderArrayTools.py` / `datamodel.py`
  / `eventloop.py` over a mock ROOT with cppyy lifetime semantics (weakref
  proxies): the old access pattern **reproduces the exact error**
  (`ReferenceError: attempt to access a null-pointer
  (GenPart_genPartIdxMother)` after 7 remakes), and the fixed module runs the
  real `eventLoop` with reader version 1 → 1 (zero remakes), 46 branches,
  correct signal quantities; data no-op intact.
  **Unverified against real ROOT — rerun on lxplus (`-N 10` on a TTZToQQ/DY
  file, then `validate_topcpvcat.py`) before resubmitting.**

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

## A20 — Data 의 processing string 이 NanoAOD 버전마다 형태가 다르다 (2026-08-31)

**증상.** `das_scan.sh --era 2017UL --nano v15` 가 Data 3 종을 전부 NOT_FOUND 로
보고했습니다:

```
### DATA JetHT
RESULT|JetHT|NOT_FOUND|0
### DATA BTagCSV
RESULT|BTagCSV|NOT_FOUND|0
### DATA SingleMuon
RESULT|SingleMuon|NOT_FOUND|0
```

여기서 "Run2 UL NanoAODv15 는 MC 전용 캠페인이므로 ttHH v15 분석은 불가능하다" 는
결론이 나왔습니다. **틀렸습니다.**

**원인.** era table 이 `DATA_PROC="UL2017_MiniAODv2_NanoAOD@V@"` 로 조립하는데,
v15 는 그 자리에서 `MiniAODv2_` 를 **뺍니다**:

```
v9   /JetHT/Run2017B-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
v15  /JetHT/Run2017B-UL2017_NanoAODv15-v1/NANOAOD
```

즉 존재하지 않는 데이터셋을 조회한 것입니다. 실제로는 **Run2017B–F 전부**
있습니다 (JetHT, BTagCSV; SingleMuon 은 B–H). MC 쪽 캠페인 접두(`@V@` 치환)는
v9→v15 에서 형태가 같아 잘 동작했기 때문에 Data 쪽만 어긋난 것을 놓쳤습니다.

**수정.** `scan_data()` 에 MC 경로가 이미 갖고 있던 것과 같은 relaxed 재조회를
추가했습니다 — `_MiniAODv<N>_` 를 `*` 로 치환해 다시 조회하고, 그때는
`RESULT|<key>|RELAXED|<n>` 으로 보고합니다. era table 주석에 위 두 줄을 실측으로
박아 두었습니다.

**규칙 — A19 와 같은 종류의 실수입니다.** 하나의 가정된 질의 패턴이 비었다는 것은
**부재의 증거가 아닙니다.** `NOT_FOUND` 를 결론으로 쓰기 전에 최소한 한 번은 넓혀서
확인하십시오:

```bash
dasgoclient -query="dataset=/<PD>/<RunEra>*<VER>*/NANOAOD"     # 형태 불문
bash script/das_scan.sh --era <ERA> --probe                    # 캠페인 열거
```

2026-08-30~31 사이에 같은 실수를 세 번 했습니다: HLT 3 경로(A19), Data v15(여기),
그리고 그 사이에 "TT4b 에 v15 가 없다" — 마지막 것만 재확인 후에도 참으로 남았습니다.

---

## A19 — 한 파일의 인벤토리로 branch 의 "부재" 를 단정했다 (2026-08-30)

**증상.** `check_branchlist.py --era 2017 --profile main` 이 v15 인벤토리에 대해
2017 hadronic 트리거 3 개를 (C) "파일에 없음" 으로 보고했습니다:

```
HLT_HT300PT30_QuadJet_75_60_45_40_TripeCSV_p07
HLT_PFHT430_SixJet40_BTagCSV_p080
HLT_PFHT380_SixJet32_DoubleBTagCSV_p075
```

여기서 "v15 가 hadronic 트리거를 3 개 잃었다 ⇒ 트리거 효율과 SF 를 다시 유도해야
한다" 는 결론이 나왔습니다. **전부 틀렸습니다.**

**원인.** HLT branch 집합은 **그 dataset 이 덮는 run 범위의 HLT 메뉴**입니다. 따라서
primary dataset 마다, run era 마다, Data/MC 사이에서 다릅니다. 다른 branch 처럼
"한 파일에 없으면 그 버전에 없다" 로 다룰 수 없습니다. 실측:

| 인벤토리 | Events | HLT | 위 3 경로 |
|---|---|---|---|
| 2017UL v9 MC (`TTToSemiLeptonic`) | 1666 | 569 | 없음 |
| 2017UL v15 MC (동일 primary) | 1903 | 569 | 없음 |
| **Data `Run2017B`** | **1208** | **269** | **전부 존재** |
| Data `Run2017C` | 1523 | 479 | 없음 |
| Data `Run2017D` | 1570 | 526 | 없음 |
| Data `Run2017E` | 1612 | 526 | 없음 |
| Data `Run2017F` | 1666 | 580 | 없음 |

**Run B 에만 있습니다.** Run B 는 Run F 의 절반도 안 되는 HLT 를 갖고 있고 (269 vs
580), 같은 2017UL v9 안에서 MC 569 / Data 526 (MC-only 43) 입니다.

**진상.** 세 경로는 **2017 Run B** 경로입니다 — Run B 는 HLT 에서 calo 기반
b-tagging 을 썼고 Run C 부터 PF 기반(`SixPFJet40_PFBTagCSV_1p5` 등)으로 교체됐습니다.
분석은 이 둘을 era 별로 OR 합니다. `tempTTHH/include/eventBuffer.h` 는 2017+2018 을
함께 덮는 **의도된 superset 헤더**(mkanalyzer 생성, HLT 583 개)이고,
`input->present()` 가드로 없는 branch 를 `missingBranches` 로 넘깁니다 — MC 와
Run C–F 에서 해당 항이 0 이 되는 것은 **물리적으로 옳은 동작**입니다. 분석에 버그는
없었습니다.

**부수 확인.** v9 MC 와 v15 MC 의 HLT 집합은 569 개로 **완전히 동일**합니다
(차집합 0). v15 마이그레이션의 트리거 영향은 0 입니다 — 원래 답은 맞았지만 이유가
틀렸습니다.

**수정.** `script/check_branchlist.py` 에 `HLT_ERA_CONDITIONAL` 을 도입했습니다.
`HLT_REQUIRED["2017"]` 은 8 → 5 개로 줄었고, Run B 4 경로는 conditional 로 옮겨
(C) 에서 실패가 아니라 정보 줄로 보고됩니다.

**규칙.** "분석기가 읽는다" 와 "이 파일에 반드시 있어야 한다" 는 다릅니다. era 나
primary dataset 에 따라 존재가 갈리는 branch 는 **여러 인벤토리로 교차 확인**하기
전에는 부재를 주장하지 마십시오. 이를 위한 도구가 있습니다:

```bash
bash script/sweep_inventories.sh                       # tier x era x version 전수 덤프
python3 script/branch_presence_matrix.py --inventory-dir script/inventory \
    --profile main --mc --era 2017 --partial-only      # PARTIAL 이 위험 집합
```

절차: [08](08_branch_schema_migration.md) 2절 Step 3b.

---

## A18 — A branch list with a leading `drop *` silently discards the module's OWN branches (2026-08-30)

**Symptom.** A validation run finishes clean and the module reports success:

```
[topCPVCategorizer] processed=2000 signal(ttbar)=2000 unclassifiable(...)=0 (0.000%)
Total time 6.4 sec. to process 2000 events. Rate = 312.7 Hz.
```

but the output file has **15 branches and zero `TopCPVCat_*`**. No error, no
warning. Every event was categorized and every result was thrown away.

**Cause.** `outputbranchsel` governs **module-created branches as well as
copied input branches**. It had been argued — in this repo, in writing, in the
first draft of `branches/branch_CPV_validation.txt` — that the selection is
applied to the cloned *input* tree while the module adds its branches
afterwards, so a `keep` for them would be a pattern matching nothing. That
reasoning is **wrong**. A list that starts with `drop *` and does not name the
module's prefix produces a file with the entire point of the job missing.

The production lists (`branch_CPV_Run2_MC.txt`, `..._v15.txt`) never hit this
because they have **no leading `drop *`** — they are "drop these collections"
lists, so `TopCPVCat_*` is unmatched and therefore kept by default. The bug only
appears the moment someone writes a minimal allow-list.

**Fix.** `branches/branch_CPV_validation.txt` now ends with

```
keep TopCPVCat_*
```

**Rule.** Any branch list with a leading `drop *` MUST explicitly `keep` the
prefix of every module in the chain. `script/check_branchlist.py` check (B)
already simulates the rule chain for these (they are flagged `produced` in the
profile's required set, which excludes them from check (C) — the *input* schema
test — but NOT from (B)). Run it before every campaign:

```bash
python3 script/check_branchlist.py branches/branch_CPV_validation.txt \
    --inventory script/inventory/inv_2017UL_v9_MC.tsv --mc --profile cpv
```

**How it was caught.** A 2000-event smoke test run *before* the two ~15-minute
production runs, precisely because the claim above was an assumption and not a
measurement. Cost of catching it early: 30 seconds. Cost of not: two long runs
plus a comparison that would have failed with "no branches in common".
See also `docs/08_branch_schema_migration.md` 2절 Step 6 — schema checks passing
does not mean the run does what you think.

---

## A17 — A CRAB submit transcript was committed to a PUBLIC repo; it embeds a pre-signed S3 credential (2026-07-27, found 2026-08-17)

**Symptom.** Nothing breaks. That is the problem — this failure is silent and is
only ever found by someone reading the repo.

**What happened.** A history audit (2026-08-17) found **two** such blobs, not one:

| blob | added by | size | signed URLs | all expired at |
|---|---|---|---|---|
| `submit_UL18_full_20260727_1120.log` | `33e3030` (2026-07-27, "log") | 1.52 MB / 16,715 lines | 172 `AWSAccessKeyId`, 5+ `Signature=` | **2026-07-27T10:20:5xZ** |
| `ttbar_SemiLeptonic_v1/crab_.../crab.log` | `c72a711` (2025-12-12) | **6.71 MB** | 4 `AWSAccessKeyId`, 2 `Signature=` | **2025-12-11T09:24:0xZ** |

(The same audit also surfaced two ~3 MB `*Skim.root` blobs from `8542dea`
"Setup codes" — no credentials, but they are why `*.root` is the first rule in
`.gitignore`.) Both logs are out of HEAD now; **on a public repo, history is
still served**, so any blob URL of the form
`.../blob/33e3030/submit_UL18_full_20260727_1120.log#L13517` resolves.

The transcript is the full stdout of the 85-task UL18 submission. Around line
13517 it contains the **pre-signed S3 POST policy CRAB uses to upload the task
sandbox** to `crabcache_prod`:

```json
{ "expiration": "2026-07-27T10:23:37Z",
  "conditions": [ {"bucket": "crabcache_prod"},
                  {"key": "junghyun/sandboxes/<sha256>.tar.gz"} ] }
```

together with its signature, and the S3 GET URLs carry `Expires=<unix ts>`.

**Impact assessment — no rotation required.** Every signature in both blobs was
already dead long before discovery (table above; verified by decoding the
`Expires=` epochs). Each is scoped to one `bucket` plus a single sandbox `key`,
so even while live it granted nothing but the upload/fetch of one sandbox
object. **No CERN/CMS/grid credential of the user is exposed** — the VOMS proxy
itself is never printed; the ~1,000 `proxy` hits in the transcript are path and
lifetime chatter, not key material. Nothing to rotate.

**Why it still matters.** The *pattern* is the hazard: `crab submit` prints a
credential every single time, so any future transcript commit is another
exposure, and next time it may be noticed while still live. Bulk logs also
bloat the repo and make diffs useless.

**Fix (done 2026-08-17).** `.gitignore` now blocks `submit_*.log`,
`submit_*_20*.log`, `crab_status_*.log`, `crab_status_*_20*.log`,
`localcheck_*/`, `local_test_*.log`, `preflight_*.log`, with an inline comment
stating why, and an explicit carve-out for `script/das/das_ul18_scan_*.log` (DAS
query output, no credentials, and the documented input of
`script/build_ul18_from_log.py`). Policy: `03_DECISIONS.md`
**D-2026-08-17-no-logs-in-git**.

**Fix NOT done — purging history.** Deliberately deferred (see the decision
entry). If it is ever wanted, the recipe is:

```bash
# 0. make a mirror backup first -- this rewrites every SHA after 33e3030
git clone --mirror git@github.com:Junghyun-Lee-Physicist/NtupleForge.git backup.git

pip install git-filter-repo
git filter-repo --invert-paths \
    --path submit_UL18_full_20260727_1120.log \
    --path ttbar_SemiLeptonic_v1 \
    --path localcheck_UL18 \
    --path script/logs

git push --force --all && git push --force --tags
# then: everyone re-clones. Old clones and any fork still hold the blob.
# GitHub caches unreachable blobs -- open a support request to purge them.
```

Note this breaks `devExtendedTtbarId` and `main` for every existing clone, which
is why it is not worth doing for an already-expired, single-object credential.

**Re-audit (2026-10-06, after the user asked whether committing the CRAB run records
is safe; CMS had once written to the user about CRAB information pushed to git).**
`git log --all -G'AWSAccessKeyId|X-Amz-Signature|X-Amz-Credential|[?&]Signature='` over the
whole history (clone at `d79e120`) finds exactly the two blobs of the table (added by `c72a711`
and `33e3030`, removed by `c6a770a` and `3eb6913`) and the 2026-08-26 edit of this file
(`4bd3238`); no other commit ever added such a line, and in HEAD only this file names them.
The run records committed since 2026-09-16 hold no credential: `crab_report_*.txt` is
`submit_crab.py --report`'s own table (job counts per sample; no CRAB output, no URL; the
workspace RUNBOOK greps each new one before its commit); `pf_*.txt` are preflight checks; the DAS
and inventory runs do not call crab. Every command that mentions crab is logged under `script/runlogs/nocommit/`
(`script/runlog.sh`), and `.gitignore` blocks `submit_*`, `crab_status_*`, `campaign_*` and
`crab.log`. The lxplus commit `d79e120` (12 files) was scanned for
`AWSAccessKeyId|signature=|x-amz-|policy|bearer|token|password|BEGIN ...|x509up|/DC=ch`: 0.
The purge stays deferred unless CMS asks for the history itself to be cleaned. If it does: run
the recipe above and **keep `.git/filter-repo/commit-map`** (old → new SHA) in the repo, because
the ntuples' ForgeProvenance and these docs name commits by their old SHAs (for example
`d626a55004b1` of the 2024 jobs and `c168206686db` of ParkingHH); re-clone (or fetch and
`reset --hard`) the lxplus and Mac checkouts; ask GitHub support to drop the cached views.

**Checking for others before any future push:**

```bash
# any tracked log?
git ls-files | grep -i '\.log$'
# anything that looks like a signature/policy in the working tree?
git grep -nI -E '"expiration"|X-Amz-Signature|Signature=' -- . ':!docs/'
# biggest blobs ever committed
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $3>200000 {print $3, $4}' | sort -rn | head
```

---

## A16 — (PREVENTIVE) A whole task silently produces nothing: >10,000 jobs → `SUBMITREFUSED` (2026-07-27, sibling repo)

**Not yet observed in NtupleForge — recorded because the same code path exists
here and there is no guard yet.**

**Symptom (as seen in `TTHHGenCategoryTools`).** `crab submit` reports success,
the submitter prints `submitted : 7`, and one dataset then produces **zero**
output for a day. `--report` shows a row of **all zeros** for it, which looks
identical to "submitted, not started yet". `--resubmit` says
`Status information is unavailable`. Only the full `--status` dump reveals it:

```
Status on the CRAB server:	SUBMITREFUSED
Warning: The splitting on your task generated 10010 jobs.
         The maximum number of jobs in each task is 10000
```

**Cause.** With `splitting: FileBased`, `njobs = ceil(nfiles / units_per_job)`.
CRAB refuses any task above **10,000 jobs**, and the refusal is **server-side,
after** the client has already reported a successful submit. So:

- nothing in the submit log indicates a problem;
- `jobsPerStatus` stays empty → the compact `--report` row is all zeros;
- **`crab resubmit` cannot rescue it** — resubmit only requeues *failed* jobs of
  a task that reached the scheduler. The task must be **re-submitted**.

The sibling case: 2018 `TTbar_SemiLep` MiniAOD has 10,010 files and
`units_per_job` was 1 → 10,010 jobs → refused. The campaign total (20,953 jobs)
looked fine because **the limit is per TASK, not per campaign**.

**Why NtupleForge is currently safe — and exactly when it stops being safe.**
These configs run over **NanoAOD**, whose file counts are ~20x smaller than the
MiniAOD parents. Largest 2018UL dataset **by file count** =
`WJetsToLNu_HT200To400_ext1` with **780 files → 780 jobs** at `units_per_job: 1`
(then 669, 523). `TTbar_SemiLep` is largest by **events** (476 M) but only 4th by
files (391) — **job count follows files, not events**. The 7,466-job campaign is
spread over **85 tasks**.
It breaks the moment you either
(a) point a config at MiniAOD, or
(b) add a NanoAOD dataset with >10,000 files,
while leaving `units_per_job: 1`.

**Prevention.**
1. Warnings are in place at the code site every submission passes through —
   `crab/submit_crab.py` (`conf.Data.unitsPerJob`) — plus
   `crabConfig/config_ttHH2017UL.yaml` and `script/build_ul18_from_log.py`
   (which stamps the comment into both generated 2018 configs).
   The 8 `config_CPV*` files and `config_crabTest.yaml` are FileBased with
   `units_per_job: 1` but are **not** annotated locally; they rely on the
   submitter-side warning. Their inputs are NanoAOD (few hundred files max).
2. **GAP — `--preflight --check-das` here does NOT compute per-task job counts.**
   The extend submitter in `TTHHGenCategoryTools` does (it reads DAS `nfiles` and
   FAILs above the limit); porting that check is the obvious follow-up. Until
   then, check any suspect dataset by hand:
   ```bash
   dasgoclient -query "summary dataset=<DS>" -json | grep -o '"nfiles":[0-9]*'
   ```
3. Raising `units_per_job` is always safe *for this limit* (fewer jobs); the only
   upward constraint is the CRAB walltime. For a `noop` passthrough job the
   output is unaffected by packing.

**Full write-up and the standing rule:**
`TTHHGenCategoryTools/docs/08_troubleshooting.md` **T-19** (incident) and
`TTHHGenCategoryTools/docs/04_decisions.md` **D15** (rule + enforcement).

---

## A15 — CRAB job dies in 14 s: `[3011] No such file` on the LOCAL SE, no AAA fallback (2026-07-27)

**Symptom.** A job of the ttHH2018UL full production (`TTbar_SemiLep`, CRAB id
252) ran at `T2_KR_KISTI` and failed after 16 s:

```
== CMSSW: 27-Jul-2026 18:30:37 KST  Initiating request to open file
     root://cms-t2-se01.sdfarm.kr:1094//store/mc/RunIISummer20UL18NanoAODv9/...
== CMSSW: Error in <TNetXNGFile::Open>: [ERROR] Server responded with an error: [3011] No such file
== CMSSW: OSError: Failed to open file root://cms-t2-se01.sdfarm.kr:1094//store/mc/...
== CMSSW: [crab_script] : Execution failed with exit code 1
Application exit code: 5   ->  long exit code 50115 (BadFWJRXML), short 195
```

**Cause.** Two things compounding:

1. `script/run_postproc.py` handed the **bare LFN** (`/store/mc/...`) to
   `PostProcessor`, which does `ROOT.TFile.Open(fname)`. CMSSW's site-local
   trivial file catalogue translates that to the **local SE PFN only**
   (`root://cms-t2-se01.sdfarm.kr:1094/...`). The replica was not readable
   there, and a plain `TFile::Open` has **no redirector fallback** — unlike
   cmsRun's `PoolSource`, which is what every other CMS workflow relies on.
   We use `scriptExe`, so we get none of that for free.
   The job AD listed `T2_KR_KISTI` in `DESIRED_CMSDataLocations`, i.e. Rucio
   believed the block was there — so "the site has the data" is not a
   guarantee that the individual file opens.
2. The `50115 BadFWJRXML` in `crab status` is a **red herring**: our script
   aborted before `PostProcessor` could write `FrameworkJobReport.xml`, so
   WMCore then failed to parse an empty file and reported the XML error instead
   of the real cause. Always read `cmsRun-stdout.log` / the `job_out.<id>.txt`
   for the actual failure.

**Resolution — DO NOTHING; let CRAB retry. [DECIDED 2026-07-27]**

The post-job log settles it: CRAB classifies this itself and recovers.

```
RetryJob: Applying retry policy for exit code 50115
ERROR:RetryJob Job did not produce a FJR; will retry.
The retry handler indicated this was a recoverable error. DAGMan will retry.
status: COOLOFF        (retry 1 of max 3)
RECOVERABLE JOB FAIL. This jobs will be retried
```

Each retry is re-matched, so it can land at a site that *can* serve the file —
which is a **better** remedy than anything the job itself can do. Only if all 3
retries fail does this become a real problem.

**Why this was not a regression.** The `TFile.Open(LFN)`-without-fallback
structure predates every 2026-07 change; nothing regressed. The vulnerability
has always been there and fires only when the matched site cannot serve the
file — i.e. it depends on replica health and scheduling luck. It very likely
occurred during the 2017 campaign too and was silently absorbed by the same
automatic retries; it is visible now only because the first job log was read by
hand. 2018 is somewhat more exposed: `TTbar_SemiLep` is 1 TB / 391 files, so
there is more room for an incomplete block replica.

> **[SUPERSEDED 2026-09-30, D-2026-09-30-p7]** New submissions have `run_postproc.py --input-fallback` (A24): an LFN the site
> cannot open is copied through AAA with xrdcp and read from the copy; `submit_crab.py` turns it on by default. A24 ("A15 와의
> 관계") says how the reasons below were weighed. The paragraph below describes the code of 2026-07-27 to 2026-09-29.

**There is NO AAA fallback in the code.** One was written on 2026-07-27
(`resolve_input_files()` + `--xrd-fallback`), demoted to opt-in the same day, and
then **fully reverted at the user's request** — `run_postproc.py` contains zero
traces of it and `--xrd-fallback` is not a valid flag. Do not go looking for it;
if you decide to re-add it, these are the reasons it was dropped:

1. **Narrow scope.** If no site has a readable replica, the redirector cannot
   find one either. It only helps when the matched site fails but another
   succeeds — the case CRAB's retry already handles, better.
2. **It can be actively harmful.** A transient local failure is
   indistinguishable from a missing replica, so the job degrades to WAN
   streaming instead of failing fast and being re-matched. One `TTbar_SemiLep`
   file is ~1.22 M events; a 5–10× slower read can exceed the 600-min walltime.
   The probe also masks the local failure reason (`gErrorIgnoreLevel = kFatal`).
3. **Unproven on the grid** — and shipping unproven code in a 7,466-job sandbox
   is itself a risk (cf. A14).

If it is ever re-added, the only defensible use is **a targeted resubmission of
files that are demonstrably unreadable everywhere CRAB sends them** — never as a
default. The reverted version had been verified locally against a stubbed ROOT
for all three paths (local OK / AAA rescue / unreadable → exit 2) and was
**never exercised on the grid.**

**What to do instead, today:** let CRAB's automatic retries move the job
(they recover this in practice — see the 2026-07-27 UL18 job reports), and only
escalate if a specific file fails at every site across all retries.

**Ops note — a code fix does NOT reach already-submitted tasks.** CRAB ships the
sandbox at submit time, so `crab resubmit` reuses the OLD `run_postproc.py`
(same trap as A14). Anything patched must go out as **NEW tasks**.

**Diagnosis recipe for next time.** `crab status` will say
`50115 / BadFWJRXML`; ignore it. Read
`https://cmsweb.cern.ch/scheddmon/<schedd>/<user>/<reqname>/job_out.<id>.<retry>.txt`
(or `cmsRun-stdout.log` in the job sandbox) and look for the `TNetXNGFile::Open`
line — that names the site SE and the real error code.

---

## A14 — `OverflowError: math range error` in `_energy` (background samples, 2026-07-15)

**Symptom.** CRAB jobs on background samples (first seen: `QCD_HT*` 2017UL) die
immediately with

```
File ".../topCPVCategorizer.py", line 313, in push_genpar
    gp["energy"].append(_energy(pt[idx], eta[idx], mass[idx]))
File ".../topCPVCategorizer.py", line 111, in _energy
    ch = math.cosh(eta)
OverflowError: math range error
```

**Cause.** The 2026-07-10 background rebuild (audit §2b, D-2026-07-10-
background-hardprocess) correctly includes **status-21 incoming partons** in the
selected list (MiniAOD's TreePar did too). But beam-parallel legs have pt ≈ 0
and NanoAOD stores their eta as O(1e3..1e4); `math.cosh` overflows past ~710.
MiniAOD never computed this — it read `genPar->energy()` directly. The signal
path never hits it (the 12 slots are all physical particles), which is why
ttbar production and every pre-A14 test passed.

**Fix.** `_energy()` returns the −999 sentinel for `|eta| > 50` (physical gen
particles stay < ~20) and catches `OverflowError` defensively. The standalone
applies the identical rule via `SafeEnergy()` at all four energy sites — the
C++ would not have crashed but would have silently written `inf` to
`GenPar_energy`, which `validate_topcpvcat.py` would then flag as module (−999)
vs standalone (inf) mismatches. Regression: E3 in both test harnesses now uses
beam-parallel incoming legs (eta ±23000, pt 0) and asserts the sentinel.

**Ops note.** Tasks submitted with the pre-A14 sandbox cannot be fixed by
`crab resubmit` (the module is baked into the sandbox) — kill and submit a NEW
task with the fixed module. No ntuples were produced by the failed jobs, so
there is nothing stale to clean.


## A21 — 비교기가 `nan` vs `nan` 을 불일치로 보고한다 (2026-08-31)

**증상.** `script/compare_v9_v15.py` 가 enriched NanoAOD 와 중앙본을 비교하면서
`events with >=1 disagreement: 2000 (100.0000 %)` 를 냈다. per-branch 는 딱 5 개:
`HTXS_Higgs_y` 2000, `PuppiMET_{pt,phi}JER{Up,Down}` 각 5.

**원인.** 양쪽 값이 모두 `nan` 이었다. IEEE 754 에서 `nan != nan` 이므로 `x == y` 와
`abs(x-y) <= ftol*(...)` 가 **둘 다** False 를 낸다. 물리 불일치가 아니라 부동소수점
규격의 인공물이다.

- `HTXS_Higgs_y` — Higgs 가 없는 샘플에서 `HTXSRivetProducer` 가 rapidity 를 정의할 수
  없다. `cmsRun` 로그에 `LogicError HTXSRivetProducer:rivetProducerHTXS@beginRun` 경고가
  같이 나온다. **중앙본도 동일하게 `nan`**.
- `PuppiMET_*JER*` — 일부 event 에서 JER 변주가 정의되지 않는다. 같은 event 의 명목값
  `PuppiMET_pt`/`_phi` 와 `ptJESUp`·`ptUnclusteredUp`·`MET_pt`·`nJet`·`Jet_pt` 는 diff 0.

**교훈이 두 개다.**

1. `--ftol` 을 올려도 안 고쳐진다. NaN 은 tolerance 문제가 아니다. "float 이라 tolerance
   문제겠지" 로 넘기면 **실제 불일치 0 인데 100 % 실패로 읽고 마이그레이션을 세운다.**
   반대 방향의 위험도 같다 — 개수만 보고 "5 개 branch 만 다르네" 로 넘어갔다면 그 5 개가
   진짜 차이인지 인공물인지 모른 채 남는다. **개수가 아니라 값을 찍어봐야 한다.**
2. 도구의 float 판정이 이름 기반이다: `_pt`/`_eta`/`_phi`/`_mass`/`_energy` 로 끝나는
   것만 float 로 보고 tolerance 를 적용한다. `PuppiMET_ptJERUp` 은 여기 안 걸려서
   `--ftol` 과 무관하게 `==` 로 비교됐다. 즉 **대부분의 float 이 사실상 완전일치 비교**다.
   byte-identity 검증에는 좋지만, 어디에 tolerance 가 적용되는지 착각하면 안 된다.

**조치.** `equalish` 가 양쪽 NaN 을 agreement 로 처리하되 **branch 별 건수를 세어 끝에
출력**한다. 조용히 통과시키지 않는다 (TTHHGenCategoryTools D16 의 "안전장치는 입력이
없으면 통과가 아니라 실패해야 한다" 와 같은 원칙). NaN 대 숫자는 여전히 불일치다.

같은 커밋에서 `index_by_eventid` 도 고쳤다 — key 3 개 branch 만 켜고 인덱싱한 뒤
`finally` 로 복원. 640k entry × 1666 branch 를 전부 읽고 있어서 20m46s 중 거의 전부가
거기였다. `finally` 가 중요하다: SetBranchStatus 가 꺼진 채로 값 loop 에 들어가면
`GetEntry` 가 버퍼를 갱신하지 않아 **조용히 "일치" 로 보일 수 있다.**

---

## A22 · CRAB 제출이 myproxy 위임에서 실패했는데 `EXIT : 0`, 게다가 재실행이 조용히 헛도는 상태로 남았다 (2026-09-23)

**증상.** 2024 파일럿 MC(`ZZ`) 제출 transcript(`script/runlogs/nocommit/run_submit_pilot_2024_MC_20260923_075928.log`, 커밋 금지)의 요지:

```
Enter GRID pass phrase for this identity:
 error: Error: Couldn't read user key in /afs/cern.ch/user/j/junghyun/.globus/userkey.pem.
grid-proxy-init failed ...
[submit_crab] : Submit Failed: Problems delegating My-proxy.
EXIT        : 0
```

같은 블록에 이어 붙인 두 줄(Data 파일럿 제출, `exit`)은 명령으로 실행되지 않았다(Data 쪽 RUNLOG 머리글이 없고, 셸은 `Singularity>` 에 남았다).

**원인 셋.** CRABClient 동작은 lxplus 의 클라이언트와 같은 v3.260630 소스(태그, commit `970fabd`)에서 읽었다.

1. **pass phrase 프롬프트가 붙여 넣은 다음 줄을 먹었다.** myproxy 에 위임된 자격 증명이 만료돼 있었다(`Myproxy is valid: 0`).
   CRAB 은 남은 기간이 15 일 미만이면(`RENEW_MYPROXY_THRESHOLD = 15`, `Commands/SubCommand.py`) 30 일짜리를 새로 위임하고
   (`myproxyDesiredValidity = 30`, `CredentialInteractions.py`), 그때 `grid-proxy-init` 이 터미널에서 GRID pass phrase 를 묻는다.
   RUNBOOK 10 [4] 의 마지막 블록은 제출 두 줄과 `exit` 를 한 번에 붙여 넣게 되어 있었고, 프롬프트가 터미널 버퍼의 입력(뒤에 붙여 넣은
   줄)을 가져가 key 를 풀지 못했다. 입력을 기다리는 명령은 따로 두라는 RUNBOOK 0 의 규칙을 문서 스스로 어겼다(`AI_LIMITS_AND_PROTOCOL.md` 5 절
   실패 6 의 재발).
2. **wrapper 가 실패를 삼켰다.** `crab/submit_crab.py` 는 모든 CRAB 예외를 잡아 `logger.error` 만 하고 exit 0 으로 끝났다. runlog 의
   `EXIT : 0` 이 성공처럼 보였다.
3. **실패한 제출이 작업 디렉토리를 남겼다.** `SubCommand.__init__` 은 VOMS(365 행)·myproxy(383 행) 단계보다 먼저 작업 디렉토리를
   만들고(`createWorkArea`, 328 행), `.requestcache` 는 서버가 task 이름을 돌려준 뒤에만 쓴다(`Commands/submit.py` 146 행). 그래서
   `campaign_ttHH2024_v15_had_MC_v1_pilot/crab_ZZ` 가 `.requestcache` 없이 남았다. wrapper 의 기본 동작은 디렉토리가 있으면 resubmit
   이라서, 같은 명령을 다시 돌리면 `Cannot find .requestcache file` 로 또 실패하고 또 exit 0 이었을 것이다. 서버에는 아무 task 도 없다.

**같이 찾은 것.** `--kill` 분기가 기본(submit/resubmit) 분기 **뒤에** 있었다. 그래서 `--kill` 은 기존 task 를 전부 resubmit 하고,
project dir 이 없는 dataset 은 **제출한 다음** kill 했다.

**조치 (2026-09-23).**

- `crab/submit_crab.py`: dataset 마다 결과를 모아 끝에 `SUMMARY` 블록(OK / WARN / FAILED / SKIPPED)을 찍고, FAILED 나 SKIPPED 가
  있으면 exit 1. `commandStatus: SUCCESS` 와 `.requestcache` 가 둘 다 있어야 제출 성공이다. `.requestcache` 없는 디렉토리는 stale 로 보고
  CRAB 을 부르지 않으며 `rm -r` 안내를 낸다(`--resubmit`, `--report` 도 같음; `--kill` 은 WARN). proxy 계열 실패(`ProxyCreationException`
  또는 메시지에 proxy)는 나머지 dataset 을 시도하지 않고 멈춘다. 모두 같은 이유로 실패하고, myproxy 라면 dataset 마다 pass phrase 를
  다시 묻기 때문이다. `--kill` 분기는 기본 분기 앞으로 옮겨 제출하지 않는다. `--preflight` 는 stale 디렉토리를 FAIL 로, 살아 있는 task 를
  "plain submit 이 auto-RESUBMIT 한다" WARN 으로 나눈다(예전 문구 "would clash/skip" 은 틀렸다).
- 워크스페이스 RUNBOOK 10: myproxy 위임을 `crab createmyproxy --days 30` 한 줄로 떼어 먼저 돌리고(pass phrase 는 사람이 친다), 제출은
  한 줄씩, 제출 여부는 EXIT 대신 `.requestcache` 로 확인한다.

**검증.** v3.260630 의 순서(작업 디렉토리 → proxy → `.requestcache`)를 흉내 낸 mock CRABAPI 로 옛 코드와 새 코드를 같은 입력에 돌렸다.
재현: `python3 script/test_submit_crab_mock.py` (CRAB·proxy·네트워크 없이 임시 디렉토리에서만 돈다; 새 코드 17/17 PASS, 옛 코드는 13 개 FAIL).

| 경우 | 옛 코드 | 새 코드 |
|---|---|---|
| 첫 dataset 에서 myproxy 실패 (3 dataset) | 3 개 모두 시도, rc 0 | 1 FAILED + 2 SKIPPED, CRAB 호출 1 번, runlog `EXIT : 1` |
| stale 디렉토리를 둔 채 재실행 | 3 × `Resubmit Failed: Cannot find .requestcache`, rc 0 | stale 1 개 FAILED(CRAB 호출 없음), 나머지 제출, rc 1 |
| `rm -r` 뒤 재실행 | | 제출 1 + 기존 2 개 auto-resubmit(보낼 것 없음, WARN), rc 0 |
| `--kill`, 미제출 dataset 1 개 포함 | 기존 3 개 resubmit 후 kill, 미제출 dataset 을 **submit 후 kill**, rc 0 | kill 3, WARN 1, submit 0 |
| `--report` / `--status` / `--resubmit` 실패 경로 | rc 0 | 해당 행 FAILED, rc 1 |
| proxy 가 아닌 실패(HTTP 500) | 다음 dataset 계속, rc 0 | 다음 dataset 계속, rc 1 |

**재시도 결과 (같은 날, RUNBOOK 10 [4b]).** 예측대로였다. `crab_ZZ` 는 `.requestcache` 없이 남아 있었고(`STALE` 1 줄) `rm -r` 로 지웠다.
`crab createmyproxy --days 30` 한 줄에서만 pass phrase 를 물었고(`validity: 29 days, 23:59:00`), 이어진 두 제출은 묻지 않고
(`Myproxy is valid: 2591940`, `2591580`) 둘 다 `Success: Your task has been delivered to the prod CRAB3 server.` 로 끝났다:
`260923_081917:junghyun_crab_ZZ`, `260923_082524:junghyun_crab_JetMET0_Run2024H_MINIv6NANOv15_v2`. 두 project dir 모두 `.requestcache` 가 있다.
(이 제출은 lxplus 의 옛 wrapper 로 했다. 수정본은 전체 제출 전에 들어간다.)

**교훈.** (a) 규칙은 이미 있었다(RUNBOOK 0 이 `crab submit` 을 입력 대기 명령으로 명시). 규칙을 적는 것과 블록을 짤 때 적용하는 것은 다르다.
블록을 다 쓴 뒤 "이 중 입력을 기다릴 수 있는 줄이 블록 중간에 있는가" 를 한 번 더 본다. 평소에는 묻지 않는 명령도 조건에 따라 묻는다
(만료 시 재위임, 덮어쓰기 확인).
(b) wrapper 의 exit code 는 사람이 결과를 판정하는 첫 신호다. 실패를 로그로만 남기는 도구는 성공과 실패를 구별하지 못하게 만든다
(A16 의 `SUBMITREFUSED` 와 같은 축: 성공처럼 보이는 실패).

## A23 · (PREVENTIVE) `--audit` job 이 non-zero 로 끝났다: exit code 로 읽는 법 (2026-09-28)

2024 생산(`skim: 6j20`, `audit: true`)부터 job 은 복사 뒤 closure 를 보고 exit code 로 원인을 나눈다(`script/forge_audit.py` 머리글,
`12_fastpath_workflow_plan.md` §2.3). 값은 CRABServer `RetryJob.py` 의 `EXIT_RETRY_POLICY` 에 맞췄다: 목록에 없는 코드는 fatal(재시도 없음),
8020·8021 은 하위 8 bit 인 84·85 로도 다른 사이트에서 재시도.

> **[정정 2026-10-01, A28]** 아래 표의 "CRAB" 칸은 틀렸다. CRAB 은 scriptExe 의 exit code 를 그대로 받지 않는다: P7 까지의 job 은 FJR 이
> 있으면 **5**, 없으면 **50115** 로 기록됐고(우리 1 도 85 도 wrapper 에는 `Application exit code: 5`), 5 는 재시도되지 않았다(2024: Brunel 의
> 85). P7.1 부터는 `run_postproc.py` 가 FJR 맨 앞의 `FrameworkError` 로 넘긴다: 85→8021, 84→8020(CRAB 이 다른 사이트에서 재시도), 복사 뒤
> 출력 쓰기 실패 1→1(재시도), 5→80005, 7→80007(재시도 안 함).
> "사람이 할 일" 칸과 아래 재현 방법은 그대로 맞다. `crab status` 의 exit code 로 원인을 읽을 때는 이 정정을 따른다.

| exit | 뜻 | CRAB | 사람이 할 일 |
|---|---|---|---|
| 1 | NanoAODTools 예외, 또는 출력 쓰기 실패(`kWriteError`) | 재시도 | 예전과 같다. 반복되면 job 로그의 traceback |
| 2 | 인자 오류: 모르는 `--skim`, `--skim` 과 `--cut` 을 함께, `-o` 없는 `--audit`, sandbox 에 `forge_skims.py` 없음 | 재시도 안 함 | 모든 job 이 같이 실패한다. config 와 `submit_crab.py` 판을 본다(preflight 가 먼저 잡는다) |
| 84 | audit 이 입력 파일을 못 엶(ROOT 6.30 에서 `TFile.Open` 이 예외를 던져도, audit v2), 또는 입력에 `Events` tree 가 없음 | 다른 사이트에서 재시도 | 반복되면 그 LFN 의 replica(`dasgoclient -query "site file=<LFN>"`, A24) |
| 85 | 읽기 문제: C2(범위 끝까지 못 읽음), C2e(ROOT 오류 줄), RDataFrame 읽기 예외 | 다른 사이트에서 재시도 | 재시도 뒤에도 실패면 `--resubmit`. job 로그의 `FORGE\|CHECK\|C2e\|FAIL` 줄이 첫 오류 줄을 담는다 |
| 5 | 읽기 문제 없는 closure FAIL: C1(출력 event 수 ≠ RVec 통과 수), C2c(코드 histogram 합 ≠ entries), audit v2 부터 C2r(`Runs.genEventCount` ≠ 읽은 수)·C3(가중치 합 상대차 > 1e-5) | 재시도 안 함 | 아래 재현. 해석 전에는 그 dataset 을 쓰지 않는다 |
| 7 | audit 코드 자체의 예외(버그) | 재시도 안 함 | job 로그의 `forge audit failed` traceback 을 AI 세션에 |

**재현 (exit 5).** job 로그의 `FORGE|FILE|<lfn>|...` 줄에서 LFN 을 얻어, lxplus 컨테이너의 저장소 루트에서 입력을 `/tmp` 로 복사한 뒤 같은 명령을 돌리고
event 단위로 비교한다(`<lfn>`, `<list>` 를 채운다; 워크스페이스 RUNBOOK 13 의 4 와 같은 방식). 복사하는 이유: lxplus 에서 AAA 로 직접 읽으면
수십 배 느리고 file open 에서 멈추기도 한다(09-29 P5: 9.2 Hz 대 `/tmp` 복사본 3,364 Hz, `docs/08` 2 절 Step 2, `09` 25 절).

```bash
mkdir -p localcheck_v15 /tmp/$USER/repro && L=/tmp/$USER/repro/$(basename <lfn>)
/bin/bash script/runlog.sh repro_xrdcp -- env XRD_REQUESTTIMEOUT=120 timeout 1800 xrdcp -f --nopbar root://cms-xrd-global.cern.ch/<lfn> $L || /bin/bash script/runlog.sh repro_xrdcp_eu -- env XRD_REQUESTTIMEOUT=120 timeout 1800 xrdcp -f --nopbar root://xrootd-cms.infn.it/<lfn> $L
/bin/bash script/runlog.sh repro_audit -- /bin/bash -c "cd localcheck_v15 && python3 ../script/run_postproc.py ${L:?} -I modules.noop:MODULES -b ../branches/<list> --skim 6j20 --audit -o repro.root"
/bin/bash script/runlog.sh repro_audit_check -- python3 script/check_forge_output.py localcheck_v15/repro.root ${L:?}
```

로컬에서 PASS 면 그 job 의 읽기가 문제였을 가능성이 크고(C2e 가 못 본 조용한 읽기), FAIL 이면 X7 줄이 어긋난 event 키 하나를 찍는다.
어느 쪽이든 LFN 과 함께 원장에 적는다.

**출력의 `failed/`.** CRAB 은 실패한 job 의 출력도 `.../0000/failed/` 아래로 옮긴다(`cmscp.py`). audit FAIL 인 출력에는 `ForgeAudit` 이 없다
(closure 가 통과해야 쓴다). analyzer 의 file list 와 P8 집계는 `failed/` 를 건너뛰고, 같은 job 의 재시도 출력만 쓴다. `script/forge_campaign_audit.py`
는 그 파일을 세지 않고 D7 WARN 으로 job 번호를 알린다. **tempTTHH `make_filelists.py` 는 지금 건너뛰지 않는다**(`find_root_files()` 가 `os.walk`
로 모든 디렉터리를 모은다): D7 이 파일을 보이면 그 dataset 의 file list 에 실패 사본이 재시도 출력과 함께 들어간다. 고치는 것은 계획 12 A2.

**캠페인 단위 (KNU).** 한 dataset 의 job 이 모두 끝나면 저장소에서 `python3 script/forge_campaign_audit.py -c crabConfig/<config>.yaml --das script/drafts/review_das_<...>.tsv`
(cmsenv 뒤, 읽기 전용; 명령과 기대값은 워크스페이스 RUNBOOK 14): 출력 수와 job 번호, 입력마다 한 행, Σ`n_in` == DAS nevents, skim·git·branch md5 가
하나, `Runs` 합(D6, 파일마다의 최대 상대차), `ForgeTTbbKeys`(K), no-skim 캠페인과의 event 단위 비교(X7, `--reference-config`), log tarball 의 ROOT 오류
줄과 job 시간(`--scan-logs`, L1·T1). FAIL 이면 그 줄이 job 번호나 event 키를 준다.

**`FORGE|CHECK` 의 WARN 은 job 을 실패시키지 않는다**: C2w(그 파일에 없는 keep 패턴, 예: pythia 만 쓴 샘플의 `LHE*`), C2a(입력 autosave),
C3 의 상대차 1e-6~1e-5. **audit v2(2026-09-30, D-2026-09-30-p7)부터는 C2r(`Runs.genEventCount` != 읽은 event 수)과 C3 상대차 1e-5 초과가 FAIL
(exit 5)** 이다. 파일럿 265 파일에서 C2r 은 모두 정확히 같았고 C3 은 최대 4.68e-8 이었다(Float_t 반올림). exit 5 가 나오면 그 LFN 의 `Runs` 를
직접 본다: `python3 -c "import ROOT; f=ROOT.TFile.Open('root://cms-xrd-global.cern.ch/<lfn>'); r=f.Get('Runs'); e=f.Get('Events'); print(sum(x.genEventCount for x in r), e.GetEntries())"`.

## A24 · CRAB 이 입력 파일이 없는 사이트로 job 을 보냈고(overflow), 우리 job 은 AAA 로 돌아가지 않아 2 분 만에 50115 로 죽었다 (2026-09-29, 기록 2026-09-30)

**상태: 원인 확인, 대응 둘 중 하나는 적용 전**. 진행 중인 task 는 whitelist resubmit(대응 1), 새 제출은 `--input-fallback`(대응 2, P7 부터).
두 대응의 결과가 나오면 이 절 끝 "해결 기록" 에 적는다(사용자 지시, 2026-09-30).

**증상.** 2018UL 첫 `--report`(09-29): 실패 160 job 중 149 개가 50115(유효한 FrameworkJobReport 없음). plain resubmit 으로 대부분 풀렸지만
`ST_t_top` 16 개는 두 번째 시도에서도 같은 코드. `crab status --long` 에서 실패 job 은 모두 T2_US_Vanderbilt(11)·T2_US_UCSD(5)에서
2 분 남짓 돌았다(Runtime 0:02:1x, Retries 5). `crab getlog --short --jobids=31` 의 job stdout:
- 09-28 시도: `Error in <TNetXNGFile::Open>: [ERROR] Server responded with an error: [3011] Too many DFS read attempts; operation terminated`
- 09-29 시도: `Error in <TFile::TFile>: file /cms/store/mc/RunIISummer20UL18NanoAODv15/ST_t-channel_top_.../2a7bb4f0-....root does not exist`
- 그 뒤 `Traceback` 과 `ERROR: Exceptional exit ... 50115: BadFWJRXML`.

**원인.** 16 개 입력 모두 replica 가 Vanderbilt·UCSD 에 없다(`dasgoclient -query "site file=<lfn>"`: T2_DE_DESY, T2_FR_GRIF, T2_FR_IPHC,
T2_PT_NCG_Lisbon, T2_RU_JINR, T2_US_Florida, T2_US_Nebraska, T2_US_Purdue, T1_RU_JINR_Tape). 데이터가 있는 사이트가 바쁘면 CMS 는 job 을
근처(미국 안)의 다른 사이트로 보낸다(overflow). 그 job 은 입력을 AAA 로 읽는다는 전제이고, cmsRun job 은 사이트 설정의 fallback 으로 그렇게 한다.
우리 job 은 cmsRun 이 아니라 `crab_script.py` → `run_postproc.py` → NanoAODTools 이고, NanoAODTools 는 LFN 을 `edmFileUtil -d` 로 **그 사이트의
PFN** 으로 바꿔 ROOT 로 바로 연다(CMSSW 14_2_X `postprocessor.py`). fallback 이 없어서 파일이 없는 사이트에서는 열기에서 예외가 나고,
FJR 은 PostProcessor 가 끝에서 쓰므로 CRAB 은 FJR 없음 = 50115 로 적는다(payload 의 exit code 는 보이지 않는다). resubmit 은 다음 시도가
우연히 데이터 사이트로 갈 때만 통과한다. 같은 데이터 사이트(Nebraska)로 간 job 78 은 2 시간 40 분 돌고 성공했다.

**진단 순서** (lxplus 컨테이너, crab-setup 뒤; 셸 변수에 기대지 말고 경로를 직접 쓴다. 2026-09-30 에 전날 셸의 `$D` 가 비어 `-d` 뒤에 옵션이
들어가 CRAB 이 `is not a valid CRAB project directory`, EXIT 192 로 거절했다):
1. 실패 job 번호·사이트: `crab status -d <project dir> --long > <file> 2>&1` 한 줄, 그다음 `grep -E "Most Recent Site|50115" <file>`.
   `<project dir>` 는 `<jobID>/crab_<key>` 이고 key 의 `-` 는 `_` 로 바뀐다(`submit_crab.py`: `req_name = key.replace("-", "_")`; 09-30 에
   `-` 그대로 쓴 경로는 CRAB 오류 줄만 내고 grep 에 걸러져 빈 출력이었다).
2. 그 job 의 stdout: `crab getlog -d <project dir> --short --jobids=<N,...>`(job 번호. exit code 가 아니다), 그다음
   `grep -h -i -m8 -E "segmentation|traceback|exception|error in <|fatal|total time" <project dir>/results/job_out.<N>.*.txt`.
3. 입력 LFN 과 replica: `grep -h -o '/store/mc/[^ "]*\.root' <project dir>/results/job_out.<N>.*.txt | sort -u`, 그다음
   `dasgoclient -query "site file=<lfn>"`. job 이 돈 사이트가 목록에 없으면 이 절이다.

**대응 1: 이미 제출한 task.** sandbox 는 첫 제출 때 것이라 코드로는 못 고친다. 데이터가 있는 디스크 사이트로만 보낸다(한 줄):
`crab resubmit -d <project dir> --sitewhitelist=<replica 사이트들, tape 제외>`. `ST_t_top`(2018UL MC):
`--sitewhitelist=T2_US_Nebraska,T2_US_Purdue,T2_US_Florida,T2_DE_DESY,T2_FR_GRIF,T2_FR_IPHC,T2_PT_NCG_Lisbon,T2_RU_JINR`.

**대응 2: 새 제출 (2026-09-30 코드, D-2026-09-30-p7).** `run_postproc.py --input-fallback URL`: LFN 마다 먼저 사이트에서(NanoAODTools 와 같은
`edmFileUtil` PFN) 열어 본다. 안 열리면 `URL + LFN`(`root://cms-xrd-global.cern.ch//store/...`)을 `xrdcp -f -N` 으로 job 디렉터리의
`forge_aaa/store/...` 에 복사하고(3600 s 제한) NanoAODTools 와 audit 이 그 사본을 읽는다. 복사하는 이유: P5 에서 AAA 로 event 단위로 읽기는
9·59 event/s 였고(`docs/09` 25 절) xrdcp 는 269 MB 에 15 s 였다. 2024 의 가장 큰 입력(2 GB, 61 만 event)을 직접 읽으면 수 시간~하루, 복사는
수 분이다. 복사도 실패하면(`xrdcp` 이 없음, 어디서도 못 읽음, 시간 초과) `URL + LFN` 을 직접 읽는다. 실패한 시험 열기의 ROOT 오류 줄은
찍지 않는다(`gErrorIgnoreLevel` 을 그 열기 동안만 kFatal, 어느 경로로 나가든 되돌림): 로컬 사본이 없는 것은 이 job 의 읽기 오류가 아니고,
KNU 집계의 L1 은 job log 의 `Error in <` 줄을 모두 센다(job audit 의 C2e 는 그 뒤에 시작하는 capture 만 센다). 못 연 이유는 버리지 않고
한 줄에 남긴다: `FORGE|INPUT|<lfn>|local|<pfn>`, 또는 `FORGE|INPUT|<lfn>|fallback|<url>|<사이트에서 못 연 이유>|copy (<MB> MB in <s> s) <사본>`,
또는 `...|stream (<복사가 실패한 이유>)`. `ForgeAudit`·`ForgeProvenance` 에는 여는 이름이 아니라 받은 LFN 을 적는다. `submit_crab.py` 는 YAML
`aaa_fallback: false` 가 아니면 이 flag 를 `crab_args.txt` 에 넣는다(기본 on; `aaa_fallback: "root://<host>[:<port>]/"` 로 다른 redirector).
KNU 집계의 T1 이 fallback 으로 읽은 job 수, 그 xrdcp 시간(payload 시간 밖), 복사 없이 직접 읽은 job 을 적는다. overflow 자체는 끄지 않았다
(slot 이 많다; 사용자 결정).

**A15(2026-07-27)와의 관계.** 그때 쓴 fallback(`--xrd-fallback`)은 사용자 요청으로 되돌렸고 이유는 넷이었다: CRAB 재시도가 더 낫다, 일시적인
로컬 실패도 WAN streaming 으로 느려져 walltime 을 넘길 수 있다, 시험 열기가 로컬 실패 이유를 가린다, grid 에서 시험하지 않았다. 이번에는:
overflow 에서는 재시도가 다시 파일 없는 사이트로 갈 수 있다(`ST_t_top` 16 개가 두 번 연속); 복사가 먼저라 WAN streaming 은 복사까지
실패한 때뿐이다; 이유는 `FORGE|INPUT` 줄에 남는다; grid 의 첫 사용은 P7 이고 T1 과 아래 해결 기록으로 본다. 기본 on 은 사용자 결정이다
(D-2026-09-30-p7).

**남는 것.** 입력이 어디서도 안 열리면(복사도 직접 읽기도 실패) 여전히 NanoAODTools 예외 → FJR 없음 → 50115 이고 CRAB 이 재시도한다. 그때는
위 진단 3 으로 replica 를 본다. 사이트의 사본이 열리기는 하는데 읽다가 깨지는 경우는 audit 의 C2e/C2 가 exit 85 로 잡는다(정정 2026-10-01: CRAB 은 이 85 를
받지 못하고 5 로 적어 재시도하지 않았다, A28; P7.1 부터 FJR 의 8021 로 넘겨 재시도된다). 사본은 job 디렉터리에 남고 job 이 끝나면 batch 가 지운다(2024 입력은 파일당 최대 2 GB). 이미 제출한 task 에는
닿지 않는다(A15 Ops note: sandbox 는 제출 때 것).

**해결 기록.**
- `ST_t_top` (2018UL, 대응 1): 09-30 lxplus 확인 `finished 100.0% (169/169)`. 09-29 의 두 번째 plain resubmit 으로 남은 16 개가 모두 끝났다
  (파일을 열 수 있는 사이트로 갔다는 뜻이다; 어느 사이트였는지는 보지 않았다). whitelist resubmit 은 필요 없었다(09-30 07:06 의 시도는 빈 `$D` 로
  들어가지 않았다). 이미 제출한 task 에서는 이 절의 증상이 보이면 plain resubmit 을 한두 번 하고, 같은 job 이 또 파일 없는 사이트에서 죽을 때만
  whitelist 로 보낸다.
- P7 (대응 2), lxplus 시험(09-30, lxplus9109, `d626a55`): 사본이 CERN 에 없는 `ST_t_top` LFN 하나를 `--input-fallback` 으로. `edmFileUtil` 의 EOS
  경로는 `OSError: Failed to open file root://eoscms.cern.ch//eos/cms/store/...` 로 안 열렸고(ROOT 오류 줄은 찍히지 않음), AAA 에서 `xrdcp` 로
  2,600 MB 를 149 s(약 17 MB/s)에 복사해 읽었다. 2,000 event 에서 C1·C2·C2e·write PASS, exit 0. 같은 파일(1,133,000 event)을 AAA 로 직접 읽었다면
  P5 의 9.2 Hz 로 30 시간이 넘는다.
- P7 (대응 2), grid: (결과가 나오면 여기에: P7 에서 fallback 으로 읽은 job 수, xrdcp 시간, 그 job 들의 closure.)

## A25 · 출력 전송이 사이트에서 거절됐다: 60322 "User is not authorized to write to destination site" (2026-09-29)

**증상.** skim 파일럿 Data job 77(T2_US_Vanderbilt): payload 는 끝났고 audit 도 전부 PASS(`FORGE|JOB ... exit=0`, 240 s)였는데 job 이 60322 로
실패. `crab getlog --short --jobids=77` 의 stageout 부분: `Stageout policy: local, remote`, `Stage out to : T2_US_Vanderbilt using: gfal2`,
`Stage out requested with tokens, but environment variable is not defined. Forcing it to use X509 authentication method instead.`,
`ERROR:root:Exception During Stage Out` / `StageOutError`.

**원인.** 실행 사이트의 저장소가 X509 쓰기를 거절했다(토큰 인증 전환 중인 사이트로 보인다). 우리 코드와 무관. 같은 파일럿의 81 개는 다른
사이트에서 정상.

**대응.** 한 번은 plain resubmit(09-29 13:14 UTC, 들어감). 같은 사이트에서 되풀이되면 그 task 에 `crab resubmit -d <project dir>
--siteblacklist=<사이트>`, 새 제출은 YAML `site_blacklist: [<사이트>]`(2026-09-30 부터 `submit_crab.py` 가 `config.Site.blacklist` 로 넘기고
preflight 에 `site blacklist` 줄). 되풀이되지 않으면 blacklist 하지 않는다(그 사이트의 slot 을 잃는다).

## A26 · 제출이 모두 FAILED 였는데 요약 칸에는 curl 진행 표시뿐: CRAB 서버가 `502 Bad Gateway` (2026-09-30)

**증상.** 2024 MC 제출(09-30 13:19 UTC, lxplus9109, `d626a55`): `SUMMARY (submit): 60 dataset(s): 0 OK, 0 WARN, 60 FAILED, 0 SKIPPED`. FAILED 칸에는
오류 대신 curl 의 진행 표시(`% Total % Received % Xferd ... * Trying 188....`)만 있어 원인이 안 보인다. `ls -d <jobID>/crab_*/.requestcache` 는 0 개,
`<jobID>/crab_*` 디렉터리는 60 개(서버에 간 적 없는 stale 디렉터리). 7 분 뒤 같은 노드, 같은 코드의 Data 제출은 32 개 모두 OK.

**원인.** 제출 transcript 의 HTTP 줄: CRAB client 가 제출 전에 서버에 묻는 `GET /crabserver/prod/info?subresource=delegatedn` 에 cmsweb 이
`HTTP/1.1 502 Bad Gateway` 로 답했다(그 순간 CRAB REST 서버가 응답하지 않았다). 요청을 보내기 전에 멈췄으므로 서버에 task 는 없고, client 가
만든 project 디렉터리만 남았다. 우리 코드나 proxy 의 문제가 아니다. (AI 는 처음에 sandbox 의 S3 업로드로 짐작했는데 틀렸다: `188.` 은 cmsweb
의 CERN 주소였다.)

**진단** (transcript 는 `script/runlogs/nocommit/` 에 있고 서명이 들어 있으니 서명 줄을 거른다):
`grep -m8 -E "curl: \([0-9]+\)|Failed to connect|timed out|Could not resolve|Connection refused|SSL|HTTP/[12]" <transcript> | grep -viE "x-amz|signature|policy|awsaccesskeyid"`.
`< HTTP/1.1 5xx` 가 보이면 이 절이다.

**대응.** (1) 서버에 없는지 본다(crab 한 줄): `crab tasks --days=1 | grep -E "_crab_(<key>|<key>)([[:space:]]|$)" || echo "not on the server"`.
(2) `.requestcache` 가 하나도 없을 때만 지운다: `test $(ls -d <jobID>/crab_*/.requestcache 2>/dev/null | wc -l) -eq 0 && rm -r <jobID> && echo removed`.
(3) 같은 제출 줄을 다시. `submit_crab.py` 는 stale 디렉터리가 있으면 그 task 를 다시 내지 않는다(`FAILED ... stale` 과 `rm -r` 힌트). 또 5xx 면
서버 쪽 장애가 풀릴 때까지 기다렸다가 다시 낸다.

**나중 개선 (미적용).** 제출 실패의 요약 칸에 예외 문자열의 앞 200 자 대신 `HTTP/1.1 NNN ...` 줄이나 `curl: (N)` 줄을 보이게 하면 이 절의
진단이 필요 없다.

**해결 기록.** 09-30 저녁(lxplus966, 새 proxy): 서버에 없음을 확인(`not on the server`), stale 디렉터리 60 개를 지우고 같은 제출 줄을 다시 냈다:
`SUMMARY (submit): 60 dataset(s): 60 OK`(16:26~16:31 UTC), `.requestcache` 60. 서버 쪽 장애였고 우리 쪽에서 바꾼 것은 없다.

## A27 · 2024 의 T1_US_FNAL job: 시험 열기는 열렸는데 NanoAODTools 의 두 번째 열기가 `[3011] No servers are available to read the file` (2026-10-01)

**상태: 대응 중**(10-02): lxplus 에서는 재열기 거절이 재현되지 않았고 FNAL 에서 끝난 job 이 2,429 개라, 그 시각 FNAL 쪽의 간헐적인 읽기 문제로
본다. 이미 제출한 task 는 FNAL 등을 뺀 사이트 blacklist resubmit(워크스페이스 RUNBOOK §19), 새 제출은 P7.1(D-2026-10-01-p71, 커밋 `e4ee5a2`).
결과가 나오면 이 절 끝 "해결 기록" 에 적는다(사용자 지시, 2026-09-30).

**증상.** 2024 MC `WJetsToQQ_HT400to800` 의 50115 201 개가 모두 T1_US_FNAL(10-01 triage: 2024 fail 980 중 50115 892). job 151·159 의
stdout(`crab getlog --short`):
- `FORGE|INPUT|/store/mc/RunIII2024Summer24NanoAODv15/Wto2Q-3Jets_Bin-HT-400to800_.../...root|local|root://cmsxrootd-site.fnal.gov//store/mc/...`:
  P7 의 시험 열기(`--input-fallback`)는 사이트 PFN 을 열었다.
- 곧이어 `Error in <TNetXNGFile::Open>: [ERROR] Server responded with an error: [3011] No servers are available to read the file.`
- `NanoAODTools PostProcessor failed: OSError: Failed to open file root://cmsxrootd-site.fnal.gov//store/...`,
  `FORGE|JOB|files=1|n_in=-1|...|exit=1` → FJR 없음 → 50115. CRAB 의 자동 재시도 3 번도 FNAL 에서 같은 모양.
다른 큰 50115 task(JetMET0 2024G 105, ttHTobb_semilep 98, JetMET0 2024F 53, JetMET1 2024E 45)의 사이트는 §17 1 의 표로 본다.

**원인 (가설).** 같은 프로세스가 방금 열고 닫은 파일을 다시 열 때 FNAL site redirector 가 거절한다. P7 의 job 은 LFN 마다 사이트 PFN 을 열어
보고(probe) 닫은 뒤 NanoAODTools 가 같은 URL 을 다시 열고, audit 이 그 뒤 한 번 더 연다(P6 부터). 가설이 맞으면 P7 이전(P6 audit)에도 FNAL 에서
audit 의 재열기(84)가 걸렸을 것이다. 가리는 법: (1) lxplus 에서 실패한 job 의 LFN 을 한 프로세스에서 `root://cmsxrootd-site.fnal.gov/` 로 세 번,
AAA 로 세 번 연다(§17 3; FNAL 에서 끝난 job 의 LFN 으로 대조). (2) 같은 task 에서 FNAL 에서 끝난 job 이 있는지(§17 1). FNAL 에서 끝난 job
이 많으면 재열기 자체가 아니라 특정 파일이나 시간대의 문제다.
**10-02 판정**: (1) 세 번 열기는 FNAL·AAA 모두 ok(실패한 job 151 의 파일, FNAL 에서 끝난 job 의 파일), (2) FNAL 에서 끝난 job 2,429, 실패 762.
가설(재열기 거절)은 지지되지 않는다. job 의 사이트 PFN 도 같은 `root://cmsxrootd-site.fnal.gov//store/...` 였으니 다른 것은 시각과 FNAL 안의
경로다. `[3011] No servers are available to read the file` 은 redirector 가 그 순간 그 파일을 줄 서버를 찾지 못했다는 뜻이라 그 시각 FNAL
저장소 쪽 문제로 본다(우리 쪽에서 더 가릴 방법은 없다). 50115 892 개는 모두 retries=2(세 번 다 실패; 표에는 마지막 사이트만 나온다)라
resubmit 은 FNAL 밖으로 보낸다.

**대응 1: 이미 제출한 task** (sandbox 는 제출 때 것). replica 가 다른 디스크 사이트에도 있으면(§17 4) FNAL 에서 죽은 job 번호만
`crab resubmit -d <project dir> --jobids=<N,...> --siteblacklist=T1_US_FNAL`. FNAL 에만 있으면 P7.1 코드로 그 파일만 다시 처리한다
(recovery task; 방법은 결과를 보고 정한다). plain resubmit 은 다시 FNAL 로 가서 같은 식으로 죽을 공산이 크다.
**10-02 실행**: replica 가 모두 다른 사이트에도 있어(RUNBOOK §17 4) recovery task 는 필요 없다. 생성기(RUNBOOK §19 1)가 task 당 한 줄에
`--siteblacklist=<실패한 사이트>,T1_US_FNAL,T2_BE_IIHE,T2_UK_London_Brunel,T2_US_MIT` 를 붙이고, DAS 에서 그 dataset 의 가장 높은 block
completion 을 가진 디스크 T1/T2 가 blacklist 밖에 남는지 본다(없으면 blacklist 를 줄이고 표에 적는다). 확인한 CRAB 의 규칙(CRABClient
`Commands/resubmit.py`, CRABServer `DagmanResubmitter.py`·`DagmanCreator.py`·`PreJob.py`): (1) `--siteblacklist` 는 제출 때의 blacklist 를
덮어쓰고 그 resubmit 의 job 과 그 자동 재시도에만 쓰인다. (2) job 이 갈 수 있는 사이트는 제출 때(09-30)의 입력 block 위치에서 그날 CRAB 의
전역 blacklist 를 뺀 것(`site.ad.json`)이다: blacklist 가 그것을 모두 지우면 PreJob 이 `Can not submit since DESIRED_Sites list is empty` 로
끝나고 job 은 실행 없이 곧 다시 failed. DAS 는 지금의 위치라 다를 수 있어 RUNBOOK §19 2b 로 낸 job 의 상태를 본다. (3) 같은 task 에
다음 resubmit 을 내면 그 전 resubmit 의 job 은 blacklist 를 다음 재시도 한 번에만 쓴다(`redoSites` 가 읽은 목록을 저장하지 않음): 다음 round 는
그 task 의 job 이 모두 끝난 뒤에 낸다.

**대응 2: 새 제출 (P7.1, D-2026-10-01-p71).** `run_postproc.py --input-copy`: 사이트 PFN 이 `root://`(`roots://`, `xroot://`)면 먼저
`xrdcp -f -N` 으로 job 디렉터리의 `forge_in/store/...` 에 복사하고(3600 s 제한) NanoAODTools 와 audit 은 그 사본만 읽는다. 원격 파일은
xrdcp 가 한 번 연다. 복사가 실패하면 순서는 `--input-fallback` 의 AAA 복사(`forge_aaa/`), 사이트에서 열어 읽기(사본을 둘 디스크가 없을 때),
AAA 직접 읽기다(이유는 `FORGE|INPUT` 줄에 모두 남는다; 리뷰 10-01: 사이트 열기를 AAA 복사보다 뒤로). 로컬 경로 PFN(`/...`, `file:`)은 복사하지
않는다. 성공한 복사는 `FORGE|INPUT|<lfn>|copy|<pfn>|copy (<MB> MB in <s> s) <사본>`; KNU 집계의 T1 이 그 job 수와 xrdcp 시간을 적는다.
`submit_crab.py` 는 YAML `input_copy: false` 가 아니면 이 flag 를 넣는다(기본 on; preflight `input copy` 줄). 대가: 사이트 저장소에서 옮기는
양이 파일 전체로 늘 수 있다(지금은 브랜치 목록이 남기는 브랜치와 audit 의 몇 브랜치만 읽는다). 대신 원격 접근이 한 번이고 큰 블록 순차
읽기다. Brunel 의 job 1(A28)은 gateway 를 통해 146,381 event 를 6,072 s(24 Hz)에 읽었다; `/tmp` 사본은 P5 에서 3,364 Hz 였다. 읽기 제한이
사본 복사에서도 걸리는지는 모른다(그때는 위 순서로 넘어간다). 시험: mock 96(P7.1 20 새로), CRAB mock 52, 실제 ROOT 시험 6 개 추가(AI 세션 ROOT 6.40 에서
26/26; lxplus 는 RUNBOOK §18), 원장 V56.

**대응 3 (사용자 제안 10-02, 결정 전): 제출 때부터 blacklist.** 다음 제출부터는 지난 캠페인의 job 표에서 되풀이해 실패한 사이트를 YAML
`site_blacklist`(09-30 부터 `config.Site.blacklist`)에 넣어 처음부터 막고, `submit_crab.py --preflight` 가 dataset 마다 그 blacklist 밖에
가장 높은 block completion 의 디스크 T1/T2 가 남는지 DAS 로 본다. 제출 때 모든 위치가 막힌 block 은 CRAB 이 경고만 남기고 건너뛰므로
(`DagmanCreator.py`: `... will be skipped because those sites are in user black list`) 이 확인이 없으면 dataset 이 조용히 비게 된다. 이미
돌고 있는 task 의 blacklist 는 resubmit 으로만 바꿀 수 있다(대응 1). 사이트 문제는 시간에 따라 바뀌므로(FNAL 은 finished 2,429) 고정 blacklist
는 보조이고, 실행 중의 읽기 실패는 P7.1(대응 2: 사본 읽기, 85·84 → 8021·8020 이라 CRAB 이 다른 사이트에서 재시도)이 맡는다. 계획 12 의 P7.2.

**해결 기록.**
- P7.1 lxplus 시험(10-01, lxplus9103, `e4ee5a2`, RUNBOOK §18 3): FNAL 에서 죽은 job 151 의 파일을 `--input-copy` 로 읽었다. CERN 에 없어
  사이트(EOS) 복사는 `[3011] Unable to open file ... No such` 로 실패했고, AAA 복사가 703 MB 를 94 s(약 7.5 MB/s)에 가져와 2,000 event 에서
  closure PASS, exit 0. FNAL 에만 있는 파일도 AAA 로 한 번에 가져올 수 있다(recovery 의 전제).
- 10-02 04:33 job 표(RUNBOOK §17 1): 2024 의 26,947 job 중 failed 995. 50115 는 FNAL 758·T2_BE_IIHE 134(892 개 모두 retries=2). FNAL 은
  finished 2,429·failed 762(50115 758 + postprocessing 4)이고 실패는 38 task 에 고루 있다. IIHE 에도 50115 134, exit 5 36, 50664 14, 50660 7
  (finished 1,200): FNAL 만의 문제는 아니다.
- 10-02 세 번 열기(§17 3): job 151 의 파일 FNAL 3/3·AAA 3/3 ok, FNAL 에서 끝난 JetMET0 2024C job 58 의 파일도 6/6. 재열기 거절은 재현되지
  않는다.
- 10-02 resubmit: FNAL 밖의 안전한 실패 168(IIHE 의 50115 134 포함)은 blacklist 없이 §17 2 로 `ok 24 / 24`(IIHE 로 다시 가서 실패하면 다음
  round 에서 막는다). FNAL 의 50115 758 과 exit 5·50664 는 §19 의 사이트 blacklist resubmit: 10-02 09:56 CEST 에 48 줄 827 job,
  `ok 48 / 48`(남는 T1/T2 가 가장 적은 task 도 셋). 그 job 들이 도는지는 §19 2b, 끝나면 새 job 표로 본다.
- (남은 것: §19 의 결과, 그 job 들이 다른 사이트에서 끝나는지, P7.1 의 첫 grid 결과.)

## A28 · CRAB 은 scriptExe 의 exit code 를 그대로 받지 않는다: audit 의 85 가 exit code 5 로 기록되고 재시도되지 않았다 (2026-10-01)

**상태: 원인 확인, 2024 의 54 job 분류 끝**(10-02, 워크스페이스 RUNBOOK §17 4): 진짜 closure FAIL 은 없다. 이미 제출한 task 는 사이트 blacklist
resubmit(RUNBOOK §19), 새 제출은 P7.1(D-2026-10-01-p71, 커밋 `e4ee5a2`, lxplus 시험 통과).

**증상.** 2024 MC `WJetsToQQ_HT400to800` 의 "exit code 5" 14 개(T2_UK_London_Brunel 13, T3_UK_London_QMUL 1; 2024 전체 54). job 1·13 의
stdout(`crab getlog --short`, 원문):
- `Error in <TNetXNGFile::ReadBuffer>: [ERROR] Server responded with an error: [3005] I/O limit exceeded and wait time hit`(Brunel 의 xrootd
  gateway `xrootdgw.brunel.ac.uk`), `Total time 6071.7 sec. to process 146381 events. Rate = 24.1 Hz.`
- `FORGE|CHECK|C2e|FAIL|2 ROOT error line(s), ...`, C1·C2·C2r·C3 PASS, `FORGE|JOB|...|exit=85`, `[crab_script] : ... exit code 85`
- 그다음 CRAB wrapper: `Application exit code: 5`, `The application failed with exit code 5`, `==== Job Exit Code from FrameworkJobReport.xml
  and Application exit code: 5 ====`, `User Application failed (exit code =  5) No stageout will be done`, `Long exit code of the job is 5`.
같은 task 의 50115 job 151(우리 exit 1, FJR 없음)도 `Application exit code: 5` 를 찍은 뒤 `BadFWJRXML` → 50115 였다(A27).

**원인.** CRAB 의 job wrapper(CRABServer `scripts/job_wrapper/CMSRunAnalysis.py`, 2026-09-28 판)는 scriptExe 를 WMCore `Scram` 으로 돌리고 그
반환값을 `Application exit code` 로 찍는다. 그다음 `FrameworkJobReport.xml` 을 읽어 첫 `FrameworkError` 의 `ExitStatus` 를 job 의 exit code
로 쓰고, FJR 에 오류가 없을 때만 application exit code 를 쓴다(FJR 을 못 읽으면 50115). 우리 job 에서 application exit code 는 1 이든 85 든
**5** 였다(왜 5 인지는 Scram 쪽이라 확인하지 못했다). 그래서 NanoAODTools 가 끝까지 돌아 FJR 이 있으면 5, 없으면 50115. CRABServer
`RetryJob.py` 의 `EXIT_RETRY_POLICY`: 5 는 표에 없어 fatal(재시도 없음), 50115 는 재시도(메모리 1.3 배), 8020·8021 은 재시도에
`change_site`(다른 사이트로), 1 은 재시도("likely a worker node issue"). A23 의 "84·85 면 CRAB 이 다른 사이트에서 재시도" 는 RetryJob 표로는
맞지만 우리 85 가 RetryJob 에 닿지 않아 처음부터 동작하지 않았다. AI 의 설계 오류(2026-09-28): RetryJob 표만 보고 wrapper 가 exit code 를 어떻게
넘기는지는 보지 않았다. (CRAB3AdvancedTopic twiki 는 "non-zero 로 끝나면 wrapper 가 JSON report 전에 끝난다" 고 쓰지만 지금 wrapper 코드는 FJR
을 끝까지 읽는다: 코드를 따른다.)

**대응 1: 이미 제출한 task.** exit 5 job 을 로그로 나눈다(워크스페이스 RUNBOOK §17 4: `FORGE|JOB` 의 exit 가 85 냐 5 냐, FAIL 항목, 첫
`[3xxx]` 오류). 85(읽기 문제)는 resubmit 한다. 같은 사이트로 가면 또 걸릴 수 있으니 replica 를 보고 `--siteblacklist=T2_UK_London_Brunel` 을
붙일지 정한다. 진짜 closure FAIL(5)은 resubmit 하지 않고 A23 의 재현.

**대응 2: 새 제출 (P7.1, D-2026-10-01-p71).** `--audit` 이 0 이 아니고 NanoAODTools 가 FJR 을 썼으면 `run_postproc.py` 가
`<FrameworkError ExitStatus="N" Type="Forge...">이유 한 줄</FrameworkError>` 를 FJR 맨 앞에 넣고(`fjr_mark_error`, ElementTree; FJR 의 나머지는
그대로, 이유는 출력 가능한 ASCII 만) `FORGE|FJR|ExitStatus=N|exit=<code>|<이유>` 를 찍는다. 코드(`CRAB_ERROR`): 85 → 8021(FileReadError),
84 → 8020(FileOpenError): 다른 사이트에서 재시도. 복사 뒤 출력 쓰기·다시 읽기 실패(1, FJR 있음) → 1: 재시도. 5 → 80005, 7 → 80007: CRAB 이
모르는 코드라 재시도하지 않는다. NanoAODTools 가 예외로 끝나 FJR 이 없으면 아무것도 쓰지 않는다(50115, 재시도: 예전과 같다). FJR 을 파싱하지
못하면 손대지 않는다. exit code 는 그대로 non-zero 다: `crab_script.py` 는 FJR 의 코드를 로그에 한 줄 적고 run_postproc.py 의 exit code 를 그대로
넘긴다(처음 안은 0 으로 끝내는 것이었으나 리뷰 10-01 에서 바꿈: wrapper 가 FrameworkError 를 못 읽는 경우에도 job 이 실패로 남아야 한다; 실패한
job 은 어느 쪽이든 stage-out 하지 않는다). `crab status` 의 Error Summary 에 이 코드와 이유가 보이게 된다.

**해결 기록.**
- 10-02 분류(RUNBOOK §17 4, 21 task 54 job): `FORGE|JOB` 의 exit 가 85 로 끝난 51(85 만 36, 1 다음 85 14, 0 다음 85 1; FAIL 항목은 C2e 또는
  C2e·audit), 84 둘(`ttHToNonbb` 102·116, C2e·audit), `FORGE|JOB` 줄 없음 하나(`Muon1_Run2024H` job 24). 진짜 closure FAIL(5)은 없다. 사이트는 IIHE 36,
  Brunel 14, JINR 2, QMUL 1, Estonia 1. 가장 많은 오류는 `[3005] I/O limit exceeded and wait time hit` 14 job, `[3011] No servers are available
  to read the file` 7 job, `[3xxx]` 줄이 없는 job 32(84 둘과 job 24 포함), 요약에 안 나온 다른 `[3xxx]` 1. 수는 retries 표와도 맞는다: 85 만 36 과
  84·`FORGE|JOB` 없음 3 = retries 0 의 39, `1,85` 11 과 `0,85` 1 = retries 1 의 12, `1,1,85` 3 = retries 2 의 3. `1,85` 는 첫 시도가 FJR 없이 끝나(50115,
  재시도) 둘째가 85(CRAB 에는 5, 재시도 없음)로 끝난 모양이다.
- 대응 1 의 resubmit: 54 개 모두 실패한 사이트와 FNAL·IIHE·Brunel·MIT 를 뺀 resubmit(RUNBOOK §19, 10-02 `ok 48 / 48`).
- 10-02 §19 3: 84 둘은 T1_RU_JINR 에서 났다. probe 와 NanoAODTools 는 JINR 의 `root://xrootd01.jinr-t1.ru:1094//pnfs/...` 를 열어 끝까지
  돌았고(출력 97,605·94,296 event), 세 번째 열기인 audit 의 재열기만 `[FATAL] Connection error` → `AuditError: cannot open ...` → 84. 한 job 이
  같은 원격 파일을 여러 번 여는 위험(A27 의 가설)이 실제로 드러난 경우다(그 순간의 사이트 문제일 수도 있다): P7.1 의 `--input-copy` 는 원격을
  xrdcp 로 한 번만 열고 audit 은 사본을 읽으므로 이 경우를 없앤다. 두 파일은 DBS 에서 유효(121,040·116,960 event), lxplus 에서 AAA 로 열리고
  디스크 replica 가 열 곳 넘게 있다. job 24 는 T2_EE_Estonia 에서 로컬 파일(`file:/cms/store/...`)을 읽다 `TBranch::GetBasket ... at byte:0,
  branch:nJet, ..., basketnumber=77` 이 되풀이됐다(`FORGE|JOB` 줄 없음): Estonia 의 그 replica 나 저장소 문제로 보인다. 셋 다 실패한 사이트를
  막고 다시 냈다.
- (P7.1 이 grid 에서 처음 쓰이면 여기에: 8021 job 이 다른 사이트에서 자동 재시도되는지, 80005 가 재시도 없이 멈추는지, Error Summary 의 모양.)

## A29 · 2024 MC 출력 하나가 크기 0 으로 최종 위치에 남았다: `TTbar_Hadronic` job 443 (2026-10-02, 발견 2026-10-05)

**상태: 원인 미확인, 처리 방법 정함**(10-05). 분석은 그 파일을 빼고 진행하고, 생산은 P8 집계로 같은 경우를 모두 찾아 그 job 만 resubmit 한다.

**증상.** tempTTHH 의 KNU branch 스캔(`tools/stage0/branch_signature.py`, condor job `knu_d16_branchsig_mc`, 10-05)이 2024 MC 의 한 파일에서
(원문) `Error in <TFile::ReadBuffer>: error reading all requested bytes from file /pnfs/knu.ac.kr/data/cms/store/user/junghyun/ttHH2024_v15_had_MC_v1/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/TTbar_Hadronic/260930_162708/0000/forgedNtuple_443.root, got 0 of 300`
와 `Error in <TFile::Init>: ... failed to read the file type data.` 를 냈고 그 dataset 을 `files=770 unreadable=1` 로 셌다. 사용자의 `ls -l`(10-05):
`-rw-r--r-- 1 jhlee cms 0 Oct  2 18:48 .../forgedNtuple_443.root` — **크기 0**, `failed/` 가 아니라 출력 디렉터리 그대로, 10-02 18:48 KST(09:48 UTC).
같은 dataset 의 나머지 769 파일은 열리고 branch 집합이 하나다.

**알고 있는 것.** 10-02 는 2024 의 두 차례 resubmit 날이다(워크스페이스 RUNBOOK §17 2 의 168, §19 의 827). 크기 0 인 최종 파일은 읽을 수 없으니
분석에도 생산 완결성(P8 D0)에도 실패다. CRAB 이 job 443 을 지금 무엇으로 아는지(finished/failed/transferring), 그 job 의 시도·사이트·전송
기록은 아직 보지 않았다 — 그것이 원인을 가른다(전송이 빈 파일을 남기고 성공으로 기록됐는지, 실패 뒤 재시도가 아직인지).

**대응.** (1) 분석(tempTTHH): 2024 파일 목록은 크기 0·열리지 않는 파일을 빼고 그 이름을 기록에 남긴다; prescan(Σ genEventSumw)과 본 실행이 같은
목록을 쓰므로 정규화는 맞고 통계만 1/770 준다. (2) 생산: KNU 에서 P8 집계(`script/forge_campaign_audit.py`, D0 열리지 않는 출력·D1 빠진
job 번호·D4 event 합 = DAS)를 2024 MC·Data 에 돌려 같은 경우를 모두 찾는다(워크스페이스 RUNBOOK §21). (3) lxplus 에서 그 job 들의 `crab status
--long` 상태를 보고 resubmit 한다(finished 로 남아 있으면 finished job 의 resubmit 이 되는지 CRABClient 코드로 먼저 확인한다); 다시 P8.

**해결 기록.**
- (P8 집계와 crab status 를 본 뒤 여기에: 원인, 같은 경우의 수, 쓴 명령과 결과.)
