# Troubleshooting Log & Validation

This is the consolidated record of **every problem hit during development**,
with its symptom, the actual error/log signature, the root cause, the fix,
and how the fix was validated — followed by how the pipeline's **validation**
mechanisms work. When you hit a new problem, add an entry here (see
[`DeveloperGuideline.md`](DeveloperGuideline.md)).

Many of these surfaced together during the 2026-04-06/07 ttbarCategorizer
debugging session ("five infrastructure bugs in sequence"); two of them are
also captured in code as the [`_nanoaod_compat.py`](legacy/code/modules/_nanoaod_compat.py)
shim (deep dive: [`nanoaod_compat.md`](nanoaod_compat.md)).

---

## Part A — Incident log

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
- **Fix.** Use `safe_len(branch, branch_name=...)` — a 3-tier fallback
  (`len()` → `GetSize()` → indexing probe) instead of raw `len()`.
- **Validated by.** Loops iterate over the true element count; self-test in
  `_nanoaod_compat.py` (`python -m _nanoaod_compat`).

### A3. Scalar counters (`nGenPart`, `nGenJet`) are not a reliable length

- **Symptom.** Everything classified `tt+LF`; the categorizer found zero
  gen-jets in events that clearly had them.
- **Signature.** `range(nGenJet)` evaluated to `range(0)`, so the gen-jet
  loop body never ran. The standalone diagnostic printed:
  `*** nGenJet counter is BROKEN in N events! *** range(nGenJet)=range(0) so
  NO GenJets were found -> everything classified as tt+LF`.
- **Root cause.** On the raw-proxy access path the scalar `n<Coll>` counter
  branch cannot be trusted as the array length.
- **Fix** (commit `1fb657b`). Use the **array length** via `safe_len()` on
  the vector branch (`safe_len(event.GenJet_pt)`), never the `n<Coll>`
  counter, for loop bounds.
- **Validated by.** A diagnostic that compared `counter` vs `array size`
  per event went to 0 mismatches after the fix.

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
  [`architecture.md`](architecture.md) §7.
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
[`legacy_ttbar_pipeline.md`](legacy_ttbar_pipeline.md) §8 →
[`legacy/code/tools/validate_events.py`](legacy/code/tools/validate_events.py).
The current full-passthrough pipeline has no skim to measure; copy the tool
back into `script/` if you reintroduce one.
