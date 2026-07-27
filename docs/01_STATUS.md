# Status — NtupleForge

> **Purpose:** the single place to answer "where are we right now?" for any
> contributor (human or AI) joining cold. **Audience:** all. **Updated:**
> 2026-07-27. Keep this current; details/why live in `03_DECISIONS.md` and `02_CHANGELOG.md`.

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

### ttHH → 4b — EXISTING (2017UL) + 2018UL expansion STARTED (2026-07-26)
- `crabConfig/config_ttHH2017UL.yaml` (91 datasets, UL17 NanoAODv9). Stable.
- **2018UL campaign — DAS scan DONE, config generated (2026-07-26):**
  `script/das_ul18_scan.sh` was run on lxplus (log:
  `script/das_ul18_scan_20260726_1657.log`) — all **61 MC primary datasets**
  (= 61 queries; expanding `ext1`/`ext2`/`ext3` variants gives the **77 MC
  entries** below) found EXACT, no relaxed fallback needed.
  `script/build_ul18_from_log.py` generated
  `crabConfig/config_ttHH2018UL.yaml` (85 datasets = 77 MC + 8 Data) and
  `tempTTHH/data/samples_2018UL.json`. Regenerating from the real lxplus log
  reproduced both files byte-identical (idempotent; log is the sole input).
  **SETTLED 2026-07-26:** BTagCSV genuinely does not exist in 2018 (0 hits any
  tier / any status; 2018 PD consolidation) → **JetHT alone covers the 2018 FH
  hadronic trigger menu**; the analyzer's 2017 BTagCSV↔JetHT veto must collapse
  to a JetHT-only OR for 2018 (tempTTHH, FUTURE).
  **OPEN:** (a) Data non-GT36 chosen — confirm against the samples used by the
  ttHH AN (+ XPOG/PdmV twiki); GT36 twins kept as comments.
  **(b) SETTLED 2026-07-27 — 2018 lumi = 59.56 /fb (0.84 %)**, LUM POG "Recorded
  Golden Legacy" (`LumiRecommendationsRun2`; index `TWikiLUM`; cite
  CMS-PAS-LUM-20-001). The preliminary **59.83 was wrong** — it appears nowhere
  in the LUM POG page. Both `tempTTHH/data/samples_2018UL.json._meta` and the
  generator `script/build_ul18_from_log.py` were updated and regeneration is
  byte-identical. Still open per the TWiki: re-run `brilcalc` on this analysis'
  own certified JSON (2017 gave 42.0688 → 42.07). Full change list:
  `tempTTHH/docs/reference/LUMI_SOURCES.md`.
- **2018UL FULL production — SUBMITTED 2026-07-27.**
  `crabConfig/config_ttHH2018UL.yaml` + `branches/branch_keep_all.txt`:
  **85 tasks / 7,466 jobs / 6.74 TB expected**, `--preflight` 35 PASS / 0 FAIL
  before submit. Running; monitor with
  `python3 crab/submit_crab.py -c crabConfig/config_ttHH2018UL.yaml --status`.
  - **Watch items** (2026-07-27): `WJetsToLNu_HT200To400_ext1` (461/780 failed)
    and `WJetsToLNu_HT70To100_ext1` (322/669). KISTI `[3011] No such file`
    (`05_troubleshooting.md` A15) — CRAB retries recover these; not a
    regression. Re-check before declaring the campaign done.
  - This production did **not** wait for the ttHH categorization work: the
    analyzer resolves `Expanded_genTtbarId` at runtime from patch files, so the
    two campaigns are independent (workspace `RUNBOOK_UL18_to_controlplots.md`
    §0).
  - Post-production check (**not yet run**): prescan `genEventCount_runs` vs the
    DAS `nevents` already stored in `samples_2018UL.json`.
- **2018UL prescan slim config — LOCAL PATH VERIFIED, CRAB RUN CANCELLED.**
  `crabConfig/config_ttHH2018UL_prescan.yaml` (81 datasets: 77 MC + JetHT only,
  `units_per_job: 1`) + `branches/branch_prescan_slim_2018.txt`.
  A smoke task was submitted then **killed by the user and its project dir
  removed** (`02_CHANGELOG.md` 2026-07-27) — the plan changed to going straight
  to full production. The config is kept because the **analyzer** prescan mode
  still needs the same slim branch contract.
  - Local `-N 2000` run on a real UL18 file: `Runs` tree with
    `genEventSumw/Sumw2/Count` survives, `LuminosityBlocks` too, Events keeps
    exactly 15 branches incl. `genWeight`/`genTtbarId` → **the slim strategy is
    empirically validated**.
  - Branch lists are **per-era** (`_2017`/`_2018`) because unmatched `keep`
    patterns raise ROOT `SetBranchStatus` errors, one per job — see
    `02_CHANGELOG.md` 2026-07-27.
- **Output filename = `forgedNtuple.root` (D-F executed 2026-07-26).**
  Producers: `crab/PSet.py` + `crab/submit_crab.py` (Rule 6 pair). Downstream
  file discovery (`tempTTHH/make_filelists.py`,
  `TTHHGenCategoryTools/Validation/filelists/make_filelists.py`) matches
  **both** `forgedNtuple*` and `slimmedNtuple*`, because pre-2026-07-26
  productions (incl. `ttHH2017UL_fullNano_v20`) exist on Tier-3 under the old
  name. Drop the legacy prefix only after all campaigns are reproduced. Multi-year goals
  (incl. Run3) live in the workspace-level
  `00_CONTEXT_ExpandedTtbarId_NtupleForge_Migration.md` §2.3.
- **DEFERRED (2026-07-27, user decision) — `modules/expandedTtbarIdInjector.py`:**
  the long-term goal is that **NtupleForge**, not the analyzer, owns
  `Expanded_genTtbarId` — baked into `forgedNtuple.root` as a branch (patch
  lookup + genTtbarId self-check + FATAL-on-mismatch). Design is complete
  (5-stage plan, D-A…D-H in the workspace-level
  `00_CONTEXT_ExpandedTtbarId_NtupleForge_Migration.md` §4) but **no code has
  been written and none will be in this round.**
  - **Why deferred:** the immediate objective is the fastest path to UL18
    control plots. Writing the module means new-module validation *plus a full
    ntuple re-production*, which lengthens the critical path.
  - **Interim contract until then:** `Expanded_genTtbarId` is NOT an ntuple
    branch. The analyzer looks it up at run time from per-sample patch files
    (`TTHHGenCategoryTools` → `ttnb_<projectKey>.root`/tree `TtNb` →
    tempTTHH `path_expanded_ttbarid_dir` → `ExpandedTtbarId::resolve()`).
    NtupleForge contributes only the full passthrough (`branch_keep_all.txt`).
    This is the 2017-proven path, so it needs zero new code.
  - **Cost of deferring** (i.e. the reason to do it eventually): every analyzer
    job loads the patch map in memory (tt4b = 1.88 M rows); patch paths must be
    wired per sample and per year in the yml; the 3-key lookup lives inside the
    analyzer so downstream tools cannot reuse it; and the legacy
    `ttnb_*`/`TtNb` naming stays in force (OPEN O2 remains open).
  - **Resume after** the UL18 control plots exist. Note that resuming requires
    re-producing the ntuples (bake-in trade-off, §4.4 there).
  - The output-file rename `slimmedNtuple.root` → `forgedNtuple.root` was part
    of this plan (D-F) and **has already been executed** (see above) — it is not
    blocked by the deferral.

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
