# Status — NtupleForge

> **Purpose:** the single place to answer "where are we right now?" for any
> contributor (human or AI) joining cold. **Audience:** all. **Updated:**
> 2026-07-02. Keep this current; details/why live in `03_DECISIONS.md` and `02_CHANGELOG.md`.

## Active workstreams

### CPV (top CP-violation) gen categorization — IN PROGRESS
- **Reference = MiniAOD `SSBAnalyzer`** (not the standalone TopCPV). The audit's
  restorations (`TopCPV/02_faithfulness_vs_miniaod.md` §9) are applied to **both**
  the module and the standalone TopCPV C++ — see `03_DECISIONS.md`
  → D-2026-06-28-miniaod-reference.
- **Module:** `modules/topCPVCategorizer.py` (renamed 2026-07-01 from
  `ssbGenCategorizer.py`; branch prefix now `TopCPVCat_` —
  `03_DECISIONS.md` → D-2026-07-01-rename-topcpv) — MiniAOD-faithful (full-list
  channel, τ→ℓ gen-tree walk + GenPar append, `Channel_Idx_Expanded`).
  **2026-07-01/02: three CRAB crash root-causes fixed in sequence**
  (A11 data guard → `GetListOfBranches` no-op; A12 `safe_len` probe →
  count-branch lengths; **A13 stale readers from mid-loop lazy creation →
  beginFile pre-registration of all readers** — `05_troubleshooting.md`).
  A13 fix validated in-container against the real CMSSW_14_2_X framework
  sources (exact error reproduced; fixed module remake-free through the real
  eventLoop). **BLOCKED on lxplus re-validation:** `-N 10` local run on a
  TTZToQQ/DYJets file + `validate_topcpvcat.py` byte-identity, then resubmit.
- **TopCPV C++ (companion):** the standalone `TopCPVGenCategorizer` (package
  renamed from `SSBGenCategorizer`, v1.9, 2026-07-11) was updated in
  lockstep (same restorations). Since 2026-07-10 the C++ IS compile- and
  run-tested in the dev container via the stub-ROOT cross-check harness
  (`TopCPVGenCategorizer/validation/crosscheck/`, g++ `-Wall -Wextra` clean,
  values identical to the Python module on 3 synthetic events). Real-ROOT
  build + `validate_topcpvcat.py` on lxplus still required before use.
- **Configs:** per-tier since 2026-07-02 —
  `crabConfig/config_CPV{2016preVFPUL,2016postVFPUL,2017UL,2018UL}_{Data,MC}.yaml`
  (Data = noop + Data branch list; MC = gen module + MC branch list; see
  D-2026-07-02-per-tier-configs). Datasets transcribed from the user lists
  (NanoAODv9) and DAS-verified 2026-07-01. **Datasets + per-tier wiring final;
  jobID/output_base/splitting are placeholders.**
- **Branch lists:** `branches/branch_CPV_Run2_{Data,MC}.txt` added.
- **Validation tool:** `script/validate_topcpvcat.py`.

### ttHH → 4b — EXISTING
- `crabConfig/config_ttHH2017UL.yaml` (91 datasets, UL17 NanoAODv9). Stable.

## OPEN / next steps (CPV)

1. **lxplus build + validation.** Compile the updated TopCPV C++ on lxplus
   (no ROOT in the dev container), then run `validate_topcpvcat.py` on a real
   NanoAODv9 file (module output vs standalone TopCPV `GenCatTree`). Ints must
   match exactly; floats within tol.
2. **Config `common:` fields.** Set jobID / output_base / splitting for real.
3. **Background-channel fidelity — code DONE 2026-07-10, lxplus pending.**
   The MiniAOD-faithful rebuild (isHardProcess base + direct-boson-mother
   finals; D-2026-07-10-background-hardprocess) is applied to BOTH the module
   and the standalone (v1.8), with synthetic-event cross-validation green in
   both languages. Remaining on lxplus: rebuild the standalone with real ROOT,
   rerun `validate_topcpvcat.py`, and do the one-time §2b `TTree::Draw` sanity
   on the DY production. NOTE: MC ntuples produced before 2026-07-10 carry the
   OLD background channel — regenerate background samples (signal unaffected).
   2026-07-15: first background production attempt crashed with A14
   (beam-parallel energy overflow) — fixed in both codebases; background tasks
   must be submitted as NEW tasks with the A14 module (`crab resubmit` reuses
   the broken sandbox).

4. **Per-tier `branch_file` + module split — DONE 2026-07-02.** Configs split
   into `config_CPV<era>_Data.yaml` (noop + Data branch list) and
   `config_CPV<era>_MC.yaml` (gen module + MC branch list); combined files
   removed (`03_DECISIONS.md` → D-2026-07-02-per-tier-configs). Remaining:
   **verify with one real data CRAB task** (YAML-parse tested only).
5. **Dataset-path anomalies to verify on DAS** (normalized/flagged by the loader,
   cannot be checked offline):
   - 2016postVFP MC `QCD_Pt_170to300_TuneCP5_13TeV_pythia8`: campaign has `104X`
     (others `106X`) — likely a typo.
   - 2016preVFP / 2016postVFP MC: `QCD_Pt_3200toInf...` appears twice (normal +
     `-pilot_106X`); the pilot one is emitted as a commented `# [DUP]` line.
   - 2 paths had a missing leading `/` (2016postVFP QCD_Pt-600To800_Mu,
     QCD_Pt-170to300_EM) — prepended.
   - 2017 MC `DYJetsToLL_M-50_TuneCP5_madgraphMLM`: had an extra stray field and a
     missing `/` — normalized.
6. **NanoAODv15 migration.** Campaign strings change; re-derive dataset paths.
7. **Restorations (#2/#5/#1).** Applied to both module and TopCPV as of
   2026-06-28 (`03_DECISIONS.md` D-2026-06-28-miniaod-reference). Unrecoverable items
   (GenBHad hadron kinematics, official FromTopWeakDecay, GenJet HCal/ECal energy,
   B-frag weights) remain best-effort / friend-tree only.

## Documentation
- **2026-07-01:** docs restructured into per-workstream subdirs
  (`TopCPV/` — renamed from `ssb_gencat/` — and new `ttHH/` holding
  `01_physics.md`, `02_legacy_ttbar_pipeline.md`, `legacy/`); root docs
  renumbered contiguously; single root `00_PROMPT.md` kept for both
  workstreams; top-level and docs READMEs rewritten in Korean. See
  `03_DECISIONS.md` → D-2026-07-01-docs-topcpv-tthh-split and
  `02_CHANGELOG.md`.
- **2026-06-27:** added `03_DECISIONS.md` (decision log) and `01_STATUS.md` (both were
  missing vs. the documentation guideline) and `TopCPV/README.md` (subdir index).
- **2026-06-28 (guideline v2):** docs numbered in reading order (`NN_name.md`); added
  `00_PROMPT.md` (AI/contributor working agreement); renamed the PyROOT helper to
  `modules/nanoaod_branch_access.py` and the CPV branch lists to
  `branch_CPV_Run2_{Data,MC}.txt`; added `TOPCPVCAT_DEBUG` guarded logging. See
  `03_DECISIONS.md` → D-2026-06-28-docs-v2.
