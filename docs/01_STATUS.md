# Status — NtupleForge

> **Purpose:** the single place to answer "where are we right now?" for any
> contributor (human or AI) joining cold. **Audience:** all. **Updated:**
> 2026-08-17. Keep this current; details/why live in `03_DECISIONS.md` and `02_CHANGELOG.md`.

## Read this first (repo-level facts)

- **The working branch is `devExtendedTtbarId`, NOT `main`.** `origin/main` is
  frozen at `c76d014` (2026-07-05) and is 13 commits behind; it does not even
  contain the 2026-07-15 TopCPV state. `main` IS fully contained in
  `devExtendedTtbarId`, so a fast-forward merge is available whenever wanted —
  deliberately not done yet (D-2026-08-17-branch-policy). Cloning the default
  branch gives you a stale tree.
- **This is a PUBLIC GitHub repo** (`Junghyun-Lee-Physicist/NtupleForge`).
  Never commit CRAB submission transcripts or other verbose run logs — they
  embed pre-signed crabcache S3 credentials. One slipped in on 2026-07-27
  (commit `33e3030`, 1.52 MB / 16,715 lines) and is still reachable in history;
  the credential in it expired 2026-07-27T10:23:37Z, so nothing needs rotating.
  Rules and remediation: `05_troubleshooting.md` **A17**, `03_DECISIONS.md`
  **D-2026-08-17-no-logs-in-git**, and `.gitignore`.
- **2026-08-17 merge:** this tree was reconciled against the
  `NtupleForge_TopCPV_v8_1_handoff` tar (a 2026-07-15 snapshot). The tar was a
  strict subset of the code here, but it still held three records that had been
  dropped from these docs — restored, see `02_CHANGELOG.md` 2026-08-17.

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
  **2026-08-17:** `config_CPV2017UL_MC.yaml` is back to its full **73 datasets**
  — on 2026-07-26 it had been overwritten in place with a 13-sample subset, with
  no doc entry, leaving the 73 only in a `.bk`. The subset now lives in its own
  file `crabConfig/config_CPV2017UL_MC_validation.yaml`, the name OPEN #0 always
  specified; its 13 keys and DAS paths are verified 1:1 against
  `TopCPVGenCategorizer/condor/datasets.txt` (13/13, zero mismatches).
  See D-2026-08-17-validation-config-split.
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
- **CRAB job-count ceiling — 10,000 jobs PER TASK (know this before touching
  `units_per_job`).** `FileBased` splitting gives `njobs = ceil(nfiles /
  units_per_job)`; above 10,000 CRAB parks the task at `SUBMITREFUSED`
  **server-side, after `crab submit` already reported success**, `--report` shows
  a row of all zeros, and `--resubmit` cannot fix it. A dataset can silently
  produce nothing for days (this is what happened in the sibling repo on
  2026-07-27). **Safe today only because these are NanoAOD inputs**: the largest
  2018UL dataset by file count is `WJetsToLNu_HT200To400_ext1` at 780 files ->
  780 jobs, and the 7,466-job campaign is spread over 85 **tasks**.
  Rule + enforcement: `03_DECISIONS.md` **D-2026-07-27-crab-job-limit**;
  preventive entry `05_troubleshooting.md` **A16**; cross-repo canonical
  `TTHHGenCategoryTools/docs/04_decisions.md` **D15**.
  **OPEN gap:** `--preflight --check-das` here does not compute per-task job
  counts yet (the extend submitter does).
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

0. **⚠️ 미완 작업 (2026-07-15 유실) — condor path + validation config.**
   Restored 2026-08-17 from the v8.1 handoff tar, where it was OPEN #0; it had
   been deleted from this file on 2026-07-26 **without the work being done**.
   Re-verified 2026-08-17: NtupleForge still has **no `condor/` directory**.
   - **Status of the deliverables:**
     - `crabConfig/config_CPV2017UL_MC_validation.yaml` — **DONE 2026-08-17**
       (see the Configs bullet above).
     - `condor/{config.sh, runJob.sh, submit_all.sh, README.md}` +
       `makeFilelists.py` / `makeCondorIndex.py` / `checkOutputs.sh` /
       `resubmit_failed.sh` / `datasets.txt`, copied from the standalone and
       name-swapped — **STILL MISSING.**
   - **Recovery pointer:** contents are reconstructable from the 2026-07-15
     conversation — past-chats search: `"NtupleForge condor runJob validation yaml"`.
     The standalone originals are readable right now at
     `../TopCPVGenCategorizer/condor/` — and as of 2026-08-17 that copy again
     carries the v1.10.1 preflight guard + `-s <TAG>` mode and the v1.10.2
     `MY.JobBatchName` line, so the template below is no longer hypothetical.
   - **Design decisions already made (keep):**
     1. condor = local (re)processing role; CRAB = grid production.
     2. The worker `cmsenv`s a nanoAOD-tools release and runs
        `script/run_postproc.py` with the SAME module + branch wiring as CRAB,
        so the two paths' outputs are directly comparable.
     3. Output chunk naming `<dataset>_chunkNNN.root`, shared with the
        standalone so its `checkOutputs.sh` works verbatim.
     4. `MY.JobBatchName = "$(short)"` in the rendered JDL.
     5. `config.sh` added to `transfer_input_files`.
     6. Preflight `condor_submit` guard + `-s TAG` submit-only mode, inherited
        from the standalone glue.
   - **Remaining:** recreate files → CHANGELOG/STATUS entries →
     `bash -n` / `py_compile` / link-check gates → package as **v9**.
   - **Companion task** (standalone side, CRAB-ification):
     `TopCPVGenCategorizer/docs/01_STATUS.md` OPEN #0 — also still open; its
     `crab/` directory does not exist either.

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
