# Changelog

All notable changes to NtupleForge. Reconstructed from git history
(`dev260412_TTbarCategory` branch) and curated into logical milestones rather
than raw commits. Dates are approximate (derived from commit/backup
timestamps; `26MMDD` suffixes seen in the repo decode as `20YY-MM-DD`).

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased] — Full-NanoAOD passthrough + docs restructure

The active direction changed: **NtupleForge no longer produces `ttCat_*`
branches.** tt+jets categorization moves to the main analyzer, and the
post-processor now ships full NanoAOD unchanged. The repository was
reorganized so the live tree is the minimal working pipeline and all
knowledge lives in `docs/`.

### Changed
- **Default pipeline is now full passthrough.** New
  `branches/branch_keep_all.txt` (`keep *`); live
  `crabConfig/config_ttHH2017UL.yaml` switched to `modules/noop.py` +
  `branch_keep_all.txt` (dataset list preserved, campaign id → `fullNano_v19`).
- **`crabConfig/config_ttHH2017UL.yaml` dataset list extended** (2026-06-22)
  to cover ttH-style and ttHH SL/DL (leptonic) selections, not just ttHH→4b
  fully-hadronic. Added (UL17 NanoAODv9, names resolved via dasgoclient):
  tH signals `tHq`/`tHW` and `ttHToNonbb` (AN-19-094 Tab.7-8); `ttZH`/`ttZZ`
  ext1 productions (combine with base for stats); leptonic ttV
  `TTWJetsToLNu`/`TTZToLLNuNu` (nominal
  TuneCP5 only); full leptonic `WJetsToLNu` HT-binned set (base+ext, 21 tasks)
  and `DYJetsToLL_M-50` HT-binned set (8 tasks). Single top was already
  complete (6 channels); inclusive `ttHTobb` already covers all tt decays, so
  no tt-decay-split ttH samples were added (those are SL/DL DNN-training-only,
  AN-19-094 Tab.7, and would double-count against the inclusive in baseline).
  **Open items:** low-mass `DYJetsToLL_M-10to50` and leptonic data
  (SingleElectron/DoubleMuon/DoubleEG/MuonEG) not yet added.
- **`scripts/` renamed to `script/`**, containing the essential driver
  `run_postproc.py` and the CRAB status summarizer `parse_crab_status.py`
  (moved in from the top level). Path updated in `crab/submit_crab.py`,
  `crab/crab_script.py`, and `script/run_postproc.py`.
- **`parse_crab_status.py` enriched**: a `--show-lines` flag now prints the
  raw status lines (running / transferring / failed / finished), absorbing
  the old `checkCrabstatusCommand.txt` grep recipes; `checkCrabstatusCommand.txt`
  was deleted.
- **README slimmed** (837 → ~120 lines) to setup + run commands + a pointer to
  the developer guide. All deep material moved into `docs/`.

### Added
- **`crab/submit_crab.py` gained `--report` and `--resubmit`** (2026-06-22).
  `--report` queries CRAB and prints a compact per-sample job-state table
  (done/run/idle/transf/fail/other + totals) — easier to read than full
  `crab status`; unrecognised CRAB states fall into `other` and raise a warning
  naming them (extend `REPORT_COLUMNS`/`KNOWN_OTHER_STATES`). `--resubmit`
  explicitly resubmits failed jobs in existing tasks (the default submit path
  still auto-resubmits existing tasks). Every submit/resubmit run now prints a
  reminder that memory/walltime failures need a manual
  `crab resubmit --maxmemory/--maxjobruntime` (see troubleshooting A10).
- `docs/` reorganized into the documentation categories:
  - `DeveloperGuideline.md` — contributor rules (read all docs first; log every change
    and every problem; which doc each record goes in).
  - `architecture.md` — framework internals **plus a copy-followable how-to
    for writing a module that adds branches / applies cuts** (§6).
  - `physics.md` — physics basis (analysis target, stitching, five categories,
    `genTtbarId` encoding, why five not seven), split out of the legacy doc.
  - `troubleshooting.md` — consolidated incident log (every bug: symptom,
    error signature, root cause, fix, validation) + how validation works.
  - `legacy_ttbar_pipeline.md` — implementation record of the retired
    categorizer (physics delegated to `physics.md`).
  - `nanoaod_compat.md` — why the PyROOT compat shim existed.
  - `CHANGELOG.md` — this file.
- `docs/legacy/code/` — verbatim archive of the categorization pipeline
  (categorizer module, compat shim, slimming branch list, branch inventories,
  original CRAB config).

### Removed (from the live tree)
- `modules/ttbarCategorizer.py` (the module that used to write the twelve
  `ttCat_*` / `ttCatXval_*` categorization branches) and its
  `modules/_nanoaod_compat.py` helper → moved to `docs/legacy/code/`. The
  categorization itself now happens in the main analyzer; the full
  implementation record is kept in `legacy_ttbar_pipeline.md`.
- `branches/branch_ttHHto4b_hadronic_2017UL.txt`, `branches/branch_2017UL/`
  → archived under `docs/legacy/code/`.
- `scripts/inspect_weights.py`, `scripts/compare_branches.py`,
  `scripts/dump_branches.py`, `scripts/test_ttbar_categorizer.py` (stale,
  8-category) → **deleted**.
- `scripts/validate_events.py` → archived to `docs/legacy/code/tools/`
  (skim-efficiency QA; the current passthrough has no skim to measure). Its
  documentation moved to `legacy_ttbar_pipeline.md` §8.
- `checkCrabstatusCommand.txt` → deleted (functionality absorbed into
  `script/parse_crab_status.py --show-lines`).
- All stale `*.bk*` editor backups deleted; `.gitignore` updated to ignore
  `*.bk*`.

## tt+jets categorization — final 5-category design (~2026-04)

The major redesign of the categorizer into its final, shipped form.

### Changed
- **Primary path switched from GenPart-based to direct `genTtbarId`
  decoding.** After confirming via `GenTtbarCategorizer.cc` that the AN-cited
  tool does not store a bbb-vs-4b distinction, `genTtbarId % 100` became the
  primary source of truth (`f701f5a` reversed once more into final form).
- **Class renamed** `TTbarJetCategorizer` → `TtbarCategorizer`; categories
  collapsed from 8 (`ttCat_LF/cc/b/2b/bb/bbb/4b/noTTJets`) to 5
  (`ttCat_LightFlavour/AddCjet/Add1Bjet_1Had/Add1Bjet_2Had/Add2Bjet`) with
  explicit jet/hadron suffixes.
- **Dropped** the `nAdditional{B,C}Jets` / `nAdditionalBHadrons` /
  `nMatchedBHadrons` count branches.

### Added
- **Dual parallel branch sets.** The GenPart algorithm was demoted to a
  cross-check, written unconditionally to `ttCatXval_*` alongside the primary
  `ttCat_*`, so the analyzer can compare both per event without re-running
  (`619b5eb`).
- **endJob report** with source distribution, per-category counts, and a 5×5
  primary-vs-xval confusion matrix.
- **Optional per-event debug CSV** (`--ttcat-debug-csv`), off by default and
  never staged out by CRAB (`a9449a4`).
- **CLI flags via env-var + factory** (`--ttcat-debug-csv[-path]`,
  `--ttcat-quiet`) decoupled from the module class.

### Fixed
- **`tt+2b` (code 52) classification bug** (`619b5eb`).
- **Broken scalar counters.** Loops were switched from `range(nGenPart)` /
  `range(nGenJet)` (which returned `range(0)` under the raw-proxy access
  mode, classifying everything as `tt+LF`) to true array lengths via
  `safe_len()` (`1fb657b`).
- **Silent UChar_t comparison failure.** `GenJet_hadronFlavour == 5` always
  returned `False` (`b'\x05' == 5`), putting 1000/1000 signal events into
  `tt+LF`; fixed with `to_int()`. Captured in the new `_nanoaod_compat.py`.
- **Input-branch zombie state.** The driver stopped applying the keep/drop
  file to the input tree (`branchsel=None`); applying it had left
  `genTtbarId`/`GenPart_*` in a `hasattr=True / len()=0` state, sending every
  event to `NO_GENTTBARID`.
- **`hasattr` crash on data NanoAOD.** Branch-presence detection moved from
  `hasattr(event, name)` (the wrapper raises `RuntimeError`, which `hasattr`
  does not catch) to reading `inputTree.GetListOfBranches()` directly.

---

## tt+jets categorization — initial introduction (~2026-03–04)

### Added
- First ttbar categorization module (`TTbarJetCategorizer`) and the
  `GenJet_hadronFlavour` branch needed to feed it (`9be688f`).
- Enabled the categorizer in the CRAB pipeline and kept its output branches
  (`dab7120`).

### Fixed
- Aligned `_is_b_hadron` and the ΔR-matching algorithm with the C++ analyzer
  (`3bf1cdc`).

---

## Core framework and CRAB submission (earlier)

### Added
- `scripts/run_postproc.py` — driver wrapping the NanoAODTools
  `PostProcessor` (split/merge modes, dynamic `module:LIST` loading).
- `crab/{submit_crab.py,crab_script.py,PSet.py}` — YAML-driven CRAB3
  submission manager (submit / status / resubmit / kill), worker wrapper that
  reconstructs the command from `PSet.py` + `crab_args.txt`.
- `modules/{noop.py,jetsMETcut.py}` — empty passthrough module and a
  gatekeeper skim-cut example.
- Temporary CRAB status checkers (`parse_crab_status.py`, the
  `checkCrabstatusCommand.txt` grep cheatsheet) (`11251c8`, `e8a63c7`).

### Fixed / Changed
- Output-filename handling in CRAB (`9d806c0`, `edca229`) — the recurring
  PSet-vs-YAML stageout mismatch (see Known Issues below). Currently both
  sides use `slimmedNtuple.root`, but the value is still hardcoded in two
  places (`crab/PSet.py` and `crab/submit_crab.py`); a submit-time
  auto-sync remains a TODO.

---

## Known issues carried forward

- **Output filename hardcoded in two places.** `crab/PSet.py`
  (`PoolOutputModule` fileName) and `crab/submit_crab.py` (`out_name`) must
  agree or CRAB stageout fails with exit 60302. They currently agree
  (`slimmedNtuple.root`); auto-synchronizing them at submit time is the
  permanent fix.
- **`jetsMETcut.py` doc/default mismatch.** Docstring and `__init__` defaults
  say `njet≥4, MET>150`, but the shipped `MODULES` uses `njet_thr=6,
  met_thr=300`. Harmless, but confusing.
- **CRAB provenance staging disabled.** `crab_args.txt` and the YAML config
  are commented out of `submit_crab.py`'s `outputFiles`; only the main output
  is staged back.
