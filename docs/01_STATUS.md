# Status — NtupleForge

> **Purpose:** the single place to answer "where are we right now?" for any
> contributor (human or AI) joining cold. **Audience:** all. **Updated:**
> 2026-09-17 (batch 2 folded in; decision batch 22p: tttW split, 2016 PDs, v9 parked, column name, D-R3-9). Keep this current; details/why live in `03_DECISIONS.md` and `02_CHANGELOG.md`.

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
  eventLoop). ~~**BLOCKED on lxplus re-validation:** `-N 10` local run on a
  TTZToQQ/DYJets file + `validate_topcpvcat.py` byte-identity, then resubmit.~~
  **RESOLVED 2026-08-25 / 08-30 (this line was left stale until 2026-09-16):**
  the module ran on lxplus on real NanoAOD and passed Gate 4 against the
  standalone `GenCatTree` (TTToSemiLeptonic, 2000 events, 61/64 branches,
  0 mismatches, exit 0) and the v9↔v15 event-matched comparison (143,000
  events × 61 branches, 0 mismatches) — `09_v15_migration_log.md` §2, §6.
  What is still open on lxplus is the *campaign-scale* step: the 13-sample
  `GenCatTree` production (standalone `condor/submit_all.sh`) and the
  per-sample `validate_topcpvcat.py` campaign on top of it, plus the
  background-sample resubmission with the A14 module (OPEN CPV #2, #3).
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

## OPEN / next steps — v15 마이그레이션 (2026-08-31 정리)

측정 근거: [`08_branch_schema_migration.md`](08_branch_schema_migration.md) (절차·스키마),
[`09_v15_migration_log.md`](09_v15_migration_log.md) (진행 기록·원본 로그).

> **CLOSED — CPV gen categorizer 의 v9→v15 동일성.**
> 143,000 개의 *같은* event 에 61 개 branch 를 비교해 **불일치 0**, `--ftol 0` 에서도
> 0 (비트 단위 동일). `--prefix ""` 실행이 음성 대조군을 겸해
> `only in v15: GenJet_nBHadrons, GenJet_nCHadrons` 를 정확히 검출했습니다.
> Gate 4 (standalone C++ ≡ 모듈, v9) 와 합쳐 **v15 위의 모듈은 기준 구현체에
> 대해 전이적으로 검증**되었습니다. 08 6 절.
> 재현: `source script/setup_v9v15_validation.sh` → `nf_v9` / `nf_v15` / `nf_compare`.

> **CLOSED — 데이터셋 가용성.** registry 64 개 중 중앙 v15 가 없는 것은 6 개뿐:
> `TTHHto4b`(신호), `TT4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`, `TTZToBB`.
> Data 는 전부 존재합니다 (`UL2017_NanoAODv15-v1`). 09 10 절.

### A. 방향 전환 — enriched NanoAOD (최우선) · 2026-09-02 갱신

`TTHHGenCategoryTools/docs/04_decisions.md` **D17** (PROPOSED, D-DEP1 부분 번복). 이론·레시피·증거는
**`TTHHGenCategoryTools/docs/11_enriched_nanoaod.md`** 가 단일 출처다. 여기에는 NtupleForge 가 해야 할 것만 남긴다.

> **CLOSED — gate 1·2 (v9).** `ttbarIdTable_cff.py`(python 71 줄, **새 C++ 0**) customise 로 3 컬럼이
> top-level 로 나오고, 중앙 v9 와 **3,332,000 값 `--ftol 0` 실질 불일치 0**(branch 1669 = 1666 + 3, 타입 동일).
> 2026-08-31 의 A1 "FlatTable producer 작성" 은 **비용 추정이 틀렸던 항목** — 릴리스 관용구로 끝났다.
> A2 "byte-identity 재검증" 도 닫혔다. A3 "확장값 검증" 은 61/62 까지(71/72 는 `TT4b` 필요).
> **gate 5 (v15, CMSSW_15_0_18)**: 무수정 빌드, 스키마 1906 = 1903 + 3, 타입 동일, **값 비교 대기**.

1. **`job_type: cmsrun | postproc`** — NtupleForge config YAML 에 job type 을 넣어 registry · `das_scan` ·
   preflight · submit/status/report 를 재사용한다. 별도 repo 는 만들지 않는다. `cmsrun` 타입은 cfg 파일 +
   `--customise` 인자 + 릴리스(10_6_32_patch1 / 15_0_18)를 지정해야 한다.
2. **CRAB `units_per_job` 산정 (D17 gate 4)** — MiniAOD 는 파일 수가 많고(2018 `TTbar_SemiLep` 10,010 파일)
   v15 NANO 는 v9 보다 CPU 가 훨씬 비싸다(200 ev 2.4 Hz — ParticleNetAK4 재계산; 2000 ev 로 재측정 필요).
   `--preflight --check-das` 가 `ceil(nfiles/upj)` 로 10,000 상한(05 A16, TTHH D15)을 검사한다.
3. **입력 로컬화** — `cmsrun` job 은 MiniAOD 를 WAN 직독하면 안 된다(TTHH T-28: proxy 만료 + 직독 = 18 분
   소모 후 exit 84). CRAB 에서는 사이트 로컬 읽기라 해당 없음; **로컬/condor 테스트에서만** `xrdcp` 선행.
4. **적용 순서** — `TT4b`(71/72 확인 겸) → `TTHHto4b`(신호) → `TTZHTo4b`·`TTZZTo4b`·`tHW`·`TTZToBB`.
5. **컬럼 이름 결정 대기** — NanoAOD 컬럼은 `expandedGenTtbarId`(camelCase), sidecar/analyzer 계약은
   `Expanded_genTtbarId`. 혼합 생산이므로 tempTTHH 가 둘 다 읽어야 한다. 결정은 TTHH D17 에 기록.
6. **비교기 `script/compare_v9_v15.py`** — NaN==NaN 을 agreement 로(건수 출력), 인덱싱은 key 3 branch 만
   (`c0eab1e`). float 판정이 **이름 기반**(`_pt/_eta/_phi/_mass/_energy`)이라 그 외 float 은 `--ftol` 무관하게
   완전일치 비교임을 알고 쓴다 (05 A21).

### B. ttHH v15 passthrough (진행 중)

7. **`btagWeight_*` dead 패턴 제거** — v15 에서 삭제된 branch. 4 개 목록이
   `gen_hadronic_branchlists.py` 로 생성되므로 생성기에서 고칩니다.
8. **`Jet_jetId` / `Jet_puId`** — v15 가 만든 **유일한** 요구사항 공백(62 개 중 2 개).
   `Jet_puIdDisc` 는 생존하므로 WP 직접 적용, `Jet_jetId` 는 PF fraction +
   multiplicity 로 재계산. **analyzer(tempTTHH) 쪽 작업**이고 NtupleForge 는 재료를
   실어 보내기만 하면 됩니다 (`keep Jet_*` 로 이미 포함). 08 3.4 절.
9. **v9 대응 hadronic 목록 없음** — v9 config 는 `branch_keep_all.txt` 를 씁니다.
   공정한 v9↔v15 비교를 하려면 `branch_hadronic_2017_v9_MC.txt` 가 필요합니다.
10. **6 샘플 event-matched 비교** — `TTbar_{SemiLep,Hadronic,DiLep}`,
    `TTbb_{SemiLep,Hadronic,DiLep}`. `pair_v9_v15.py` 로 페어링 후
    `compare_v9_v15.py --prefix "" --v9v15-renames --ftol 0`.
11. **출력 크기** — 1.948 kB/event (입력의 67 %). v15 신규 태거(`btagUParTAK4*`,
    `btagPNet*`, `*RegPtRaw*`)가 Jet 34.9 % 의 대부분입니다. "v15 에만 있고 분석기가
    못 쓰는 것"만 자르는 것이 원칙적 절단선.

### C. CPV 잔여

12. **다른 ttbar 샘플의 코드 경로 미검증** — `TTToHadronic`(all-hadronic 분기),
    `TTTo2L2Nu`(lepton ≥ 2 분기). `pair_v9_v15.py` 로 이제 샘플별 페어링이 됩니다.
13. **Data tier 미검증** — 위 검증은 전부 MC 입니다.
14. **`branch_CPV_Run2_Data_v15.txt` 없음** — 데이터셋은 존재합니다(위 CLOSED).
    08 2 절 Step 3b 의 sweep 으로 인벤토리를 뜬 뒤 작성.
15. **`HLT_IsoTkMu*` / `HLT_L2DoubleMu*` per-era 분리** — 2017UL 에서 v9·v15 모두
    dead 지만 파일이 Run2 4 개 era 공유라 삭제 불가. UL16 인벤토리 확인 후 분리.
16. **8 개 CPV config 의 placeholder `jobID`** (`TEMP_..._v0`).

### D. 그 밖

17. **standalone C++ `TopCPVGenCategorizer` 는 v9 전용** — `GenPart_statusFlags` 가
    v15 에서 `UShort_t` 라 `Int_t` `SetBranchAddress` 는 조용한 쓰레기 값을 냅니다.
18. **`tempTTHH/include/eventBuffer.h`** — v15 ntuple 이 나온 뒤 `mkanalyzer` 로
    재생성. 현재 헤더는 2017+2018 superset(HLT 583) 입니다.
19. **TTHHGenCategoryTools 2018 `TTToSemiLeptonic` 검증 실패** 미해결
    (467,498,000 vs 476,408,000). `ttnb_TTbar_SemiLep.root`(2018) 보류 중.
20. **2018UL 확장** — 2018UL v9/v15 스캔 완료 (2026-09-03, 63 key: 47 EXACT / 10 RELAXED / 6 NOT_FOUND —
    2017UL 과 같은 6 개 부재, 같은 8 개 sibling). Run 3 는 아래 E.

### E. Run 3 확장 (2022–2025, v15) · 2026-09-07 시작 — 계획 [`ttHH/03_run3_plan.md`](ttHH/03_run3_plan.md)

> 결정 D-R3-1…6 (**2025 기본** — data T0 prompt NANOv15 + MC 는 Summer24(PPD 권고, 2025 MC 없음) —, 2024, 2023/BPix, 2022/EE;
> v15 만, `samples_registry_run3.txt` 분리, 이름 추정 금지, `had`/`lep` 태그 + hadronic 우선, 13.6 TeV xsec 새로).
> 도구: `das_scan.sh` era 표에 Run 3 6 행 — 2024 두 문자열은 참조 목록으로 확인(`RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2`,
> `Run2024X-MINIv6NANOv15-vN`), 나머지는 `--probe` 전까지 UNVERIFIED —, 새 `script/das_discover_run3.sh`(family 별 접두어 wildcard →
> `HIT|` 줄), registry ttHH 64 행에 `had` 47 / `lep` 16 / `had,lep` 1 태그. golden JSON·era 경계·루미·GT 는 PdmV twiki r223 / PPD 2025 표 원문으로 확정(03_run3_plan §2, §4.2).

**다음 행동 (2026-09-16 저녁 기준).** 근거와 이력은 22a~22n 에 있다. 여기에는 *무엇을 할 차례인가*만 적는다.
같은 날 오전의 표에서 끝난 것: ~~4 (2016 MiniAODv2 부모)~~ → 22k, ~~5 (Run 3 had 스캔)~~ → 22a·22b, ~~3 (tth_split 커밋)~~ (lxplus 커밋 `a781cb3` 에 포함됐는지는 사용자 확인).

| # | 할 일 | 누가 / 어디서 | 근거 |
|---|---|---|---|
| 1 | **MC 요청 메일 발송**, 답장 오면 기록 | 사용자 | [`ttHH/04_mc_request_2026-09.md`](ttHH/04_mc_request_2026-09.md) §5 |
| 2 | **변경분 커밋**(09-16 저녁 배치): 브랜치 목록 10 개(신규 6 + 수정 4), `check_branchlist.py`, `build_from_scan_log.py`, manifest, 문서 8 개 + 신규 `10_validation_ledger.md`; TTHHGenCategoryTools 4 파일(오전분); 워크스페이스 문서(git 밖) | 사용자 (맥) | 22l |
| 3 | ~~lxplus 배치 2 (RUNBOOK §6)~~ **DONE 09-17** (`15f377b`). **lxplus 배치 3** (RUNBOOK §7): 2018A 의 `…_2p94`/`…_1p59` 경로가 메뉴에 들어온 run 을 파일 몇 개로 bracket(첫 파일은 316058–316719 에 없음), 2018B 파일의 run 범위 | lxplus | 22n |
| 4 | **`TTWJetsToLNu` (Run 3)**: 표준 캠페인에는 어떤 이름으로도 없음(사용자 DAS 확인 09-17). **AI 제안: mg35x dataset 을 PINNED 전체 경로로 수용**(registry 반영, `das_scan`·builder·inventory 에 PINNED 모드 구현·fake-DAS 검증). 사용자가 반대하면 ERAS 에서 2024/2025 제거로 되돌림 | 사용자 veto 가능 | D-2026-09-17-ttwlnu-pinned |
| 5 | ~~`TTTW` 분할~~ **DECIDED 09-17 (사용자)**: registry 에 `TTTWminus`/`TTTWplus` 두 키(`had`), 옛 `TTTW` 는 `ttVV_v9`/`alt`. 남은 것: xsec 2 개, v15 dataset 의 DAS status 확인(09-11 inventory 에 '-') | xsec: 미결 | 22p, D-2026-09-17-tttw-split |
| 6 | ~~데이터 PD 2016 행~~ **DECIDED 09-17 (사용자, 17/18 과 동일)**: `JetHT`·`BTagCSV` ERAS 에 2016 두 half 추가. `BTagCSV` UL16 v15 는 DAS 미확인(RUNBOOK §7). `build_from_scan_log.py` 가 2016B ver1/ver2 를 두 행으로 유지(09-17 수정) | lxplus (BTagCSV discovery) | 22p, D-2026-09-17-data-pd-2016 |
| 7 | **xsec 표**: 13.6 TeV(D-R3-6) + 새 키 `ttHTobb_had/_semilep/_dilep`(D-R3-9) + `alt` 키; Run 2 는 `TTZToQQ` 항목을 새로 쓰면서 **861 fb vs 841 fb 정의 확정**(`00_START_HERE.md` §4 의 기존 열린 항목) | 미결 | 22g(a), D-2026-09-11-ttz |
| 8 | **2016 확장의 analyzer 비용 산정**: `samples_2016*.json` 2 개, 2016 루미, golden JSON, 트리거, b-tag SF, JEC/JER | 미착수 | 22j |
| 9 | ~~D-R3-9 확인~~ **DECIDED 09-17 (사용자)**: ttH(bb) = top-decay-split 3 종. 사용자 제공 표(Table 5, 출처 미확인)의 13.6 TeV ttbar 분할 xsec 참고값은 `ttHH/03` §6 3 | 끝 | 22g(b) |
| 10 | **FxFx `TTto4Q-2Jets` 생성기 비교**: 지금 결정 불필요. `alt` 행은 `had` 생산에서 자동 제외되며, tt+jets 모델링 불확도 연구를 시작할 때 `alt` 를 workstream 에 넣어 ntuple 을 만든다 | 보류 | 22g(c) |
| 11 | **트리거 결정 (2016, Run 3)**: 사용자 09-17 "Run 3 는 아직 정한 바 없음". 생산에는 영향 없음(wildcard 가 HLT 계열 전부 보존, 용량 문제 아님). analyzer 확장 때 `HLT_REQUIRED` 채움 | 보류 | 22m |
| 12 | **analyzer 측 4 건**: `Jet_jetId`/`Jet_puId` 재계산(08 §3.4, 변화 없음), `Flag_METFilters` 부재(Summer24 MC·2025 Data), `L1PreFiringWeight` Run 3 미적용, 2018A 초기 메뉴 vs `requireTriggerBranches2018_()` | tempTTHH | 22m, 22n |
| 13 | **CPV 목록 per-era 분리**: 2016 경로명 2 개(2017/2018 dead), 2017B 추가 4 개, `Scouting*`(UL16 MC 에 없음) | 미착수 | 22m |
| 14 | Sherpa variant·목표 통계는 **컨비너 답장 대기** | 대기 | 04 문서 §2 |
| 16 | **2018UL v9 full 생산은 보류(완료 처리 안 함), v15 로 이동 (DECIDED 09-17)**. v9 목록·config 는 기록으로 유지. v9↔v15 차이 기록 보강: 2016·2018 v9 인벤토리(MC 1 + Data era 별 1)를 스윕해 `diff_v9_v15_*` 를 2017 외에도 만든다 | lxplus | 22p, D-2026-09-17-ul18-v9-parked |
| 17 | **통합 계획 검토** (`11_unified_forge_plan.md`): Phase 0 착수 승인, Phase 1(저장소 병합) 은 Phase 0 뒤, CPV MiniAOD producer 범위, 출력 사이트 | 사용자 | 22q, D-2026-09-17-single-forge |
| 15 | **enriched 생산 착수 = Phase 0 (`11_unified_forge_plan.md` §5)**: `crab/submit_crab.py` 에 `job_type: cmsrun` → TTHHGenCategoryTools 의 2017 enriched cfg 제출 → §4 (i) 검증 → 2018·2016 레시피. 글루는 **(A)** 로 확정(사용자 방향 D-2026-09-17-single-forge). 컬럼 이름 `genTtbarIdExpanded` | 사용자 착수 승인 | 22o, 22q |

실행 규약(09-16): lxplus 의 모든 단계는 `script/runlog.sh <step> -- <명령>` 으로 돌려 `script/runlogs/` 에 로그와 `LEDGER.tsv` 를 남기고,
검증으로 볼 것은 [`10_validation_ledger.md`](10_validation_ledger.md) 에 한 행을 더한다. 절차는 워크스페이스 `RUNBOOK_lxplus_2026-09-16.md`.

21. ~~probe + discover 실행~~ **DONE 2026-09-07** — 6 era 캠페인 문자열 확정(로그 커밋됨). 결과 03_run3_plan §4.2/§4.5:
    Summer24 v15 에 신호 `TTHH-HHto4B`·`TTZH-ZHto4B`·`TTZZ-ZZto4B`·`THW`·`TTZ-ZtoQQ` 가 **중앙에 있다**(→ Run 3 에 D17 확장 없음); `TT4b` 도 있다(`TT4B_…`, **09-10 수정** — 09-07 은 대소문자 패턴 미스로 '없음'이라 적었다, 03_run3_plan §4.6);
    **2022/2023 v15 는 부분 재생산**(70 개; 신호·ttbb·QCD-HT·ttH·tH·ttVV 없음) → D-R3-7: 첫 라운드는 2024+2025.
22. ~~registry 작성~~ **DONE** — `script/samples_registry_run3.txt` MC 78(had 59 / lep 19) + DATA 11 *(09-11 현재 MC 85 = had 61 + lep 19 + alt 5 — 22h 참조)* (09-10: `TT4b` ← `TT4B_TuneCP5_13p6TeV_madgraph-pythia8` 추가; `das_discover_run3.sh` 에 `TT4B*`/`TTBBBB*` 접두어 추가).
    `das_scan.sh` 는 Run 3 era 에서 이 registry 를 자동 선택하고 v15 MC 질의를 GT 로 고정한다(플레이버 재생산 제외).
22a. ~~**event/file 수 스캔**~~ **DONE 2026-09-16**: `das_scan.sh --era 2024|2025 --nano v15 --workstream had`, lxplus `runlog.sh` 기록(`script/runlogs/run_das_scan_202?_had_*.log`), 로그 `script/das_ttHH_2024_v15_20260916_0859.log`·`das_ttHH_2025_v15_20260916_0900.log` 커밋(`a781cb3`). 65 키(MC 61 + DATA 4), EXACT 64, NOT_FOUND 1 = `TTWJetsToLNu`; DATA PD 4 × 8 dataset, DBS `-vN` 꼬리가 PD 마다 다름. 상세 `09_v15_migration_log.md` 17 절, `ttHH/03_run3_plan.md` §6 1.
22b. ~~**`build_from_scan_log.py` Run 3 대응**~~ **DONE 2026-09-16 (a·b)**: `--data-variants {auto,canonical,all}`(Run 3 = all: 2024I `-v2`+`_v2-v1`, 2025C/F `-v1`+`-v2` 전부 독립 행; 고치기 전에는 `Run2025C-PromptReco-v1` 155M ev 가 alternate 로 밀렸다), Data 플레이버 `BTVNano`/`JMENano` 제외 + 표에 나열(고치기 전 Run 2 v15 `JetHT_Run2018A` canonical 이 `UL2018_BTVNanoAODv15-v1` 이었다), `_MiniAODv2_` 없는 v15 문자열 허용, `DEFAULT_EXCLUDE` 확장. 컨테이너 dry-run 만(산출물 미커밋; 원장 V20). **남은 것**: (c) `_meta` lumi·골든 JSON; Run 3 config 발행은 `TTWJetsToLNu` NOT_FOUND 가 풀려야 가능(표 4).
22c. **결정**: ~~`TT4b` 대체 vs 사설 생산~~ (해소 09-10: 중앙 `TT4B`); `TTWJetsToLNu`(v15 는 `mg35x_` 플레이버만) 수용 여부; 13.6 TeV xsec 표(D-R3-6).
22d. **MC 요청 (2026-09-08~10, 덱 `ttHH_latex/GenRequest_Sep2026`)** — Run 2: 부재 6 종의 MiniAODv2→NanoAODv15 중앙 생산(16 dataset, ≈125M) 요청 예정; Run 3: Sherpa FH `TTto4Q-4Jets-1NLO3LO` 상태(PRODUCTION 80.5M / AHADIC INVALID)·통계·권고 판 문의, Sherpa 4FS ttbb·Sherpa tt4b 는 비교용 저순위, `GenHFHadronMatcher` 출력의 중앙 NanoAOD 탑재 문의. 그룹 피드백(Aurore 09-10): Run 2 세트 동의, Run 2 Sherpa tt+jets(FH·inclusive) 는 저순위로 요청, 24+25 우선 동의.
22e. **BTV 참고 (09-10)** — 재-NanoAODv15(Run 2, 2022/2023)는 Summer24 셋업이라 `Jet_btagUParTAK4B` 에 2024 UParTv2 WP 를 그대로 쓴다(CMS-talk 09-09) → 03_run3_plan §2 행 9.
22f. ~~inventory 실행~~ **DONE 2026-09-11** — 세 캠페인 `CASE_ONLY` 0 건(09-07 결론 확정; `TT4B` 가 유일한 대소문자 미스). Summer24 77 EXACT / 1 NOT_FOUND(`TTLNu` mg35x); UL17/18 108 EXACT, NOT_FOUND 27 = 부재 6 + QCD-HT 7 + TTTW + **CPV 13**. 수치: powheg `TTto4Q` 472.5M, Sherpa FH PRODUCTION 100.8M(↑), FxFx `TTto4Q-2Jets` 395M VALID, `TT4B` 9.9M … (03_run3_plan §4.7). 로그 3 세트 커밋됨.
22g. **결정 (09-11 신규)** — (a) ~~Run 2 `TTZToBB` 유지 vs 대체~~ **DECIDED 09-11 (사용자)**: v15 의 `TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8`(13.98M / 19.82M) 사용 — Run 3 와 같은 처리, hadronic 채널에 더 완전(bb + cc + light). registry `TTZToQQ`(`had`, Run 3 와 같은 KEY), `TTZToBB` → `alt`. **Run 2 요청 6 → 5 종**(14 datasets ≈108M); enriched 사설 목록(D17)도 5 종. `03_DECISIONS.md` D-2026-09-11-ttz-hadronic-from-ttzqq. (b) ~~`TTH-Hto2B-TTto4Q_…` 조회~~ **DONE 09-11 08:57** — 분할 3 종 모두 VALID 29.62M / 29.22M / 29.57M → registry `ttHTobb_had / _semilep / _dilep`(`had`), inclusive `ttHTobb` → `alt` (D-R3-9, 확인 요청). Run 3 ttH(bb) 문의는 삭제. `das_inventory_tth_split_20260911_0857.tsv*` 는 lxplus 에 있음 — 커밋 필요. (c) 생성기 비교: FxFx `TTto4Q-2Jets`(alt, 395M) 로 Sherpa 완료 전에 시작 — **미결**.
22h. **2025 MC 캠페인 없음 — DAS 확인 (09-11)**: `dataset status=* dataset=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/RunIII2025*/NANOAODSIM` 빈 결과. `--era 2025` 는 Summer24 유지(03_run3_plan §4.7). registry 수: MC 85 = had 61 + lep 19 + alt 5, DATA 11.
22i. **MC 요청 기록 (09-14)** — 보낸 메일 본문과 "요청하지 않은 것과 그 이유" 를 `docs/ttHH/04_mc_request_2026-09.md` 에 남겼다. 답장·발송 기록은 그 문서 §5 에 append 한다. 초안에 있던 `GenHFHadronMatcher` 요청은 사용자 판단으로 뺐다(일부 샘플만 가져도 전 샘플을 직접 만들어야 하므로 이점 없음).
22j. **2016 확장의 analyzer 쪽 비용 (09-14, 미착수)** — MC 요청은 네 era-half 로 넓혔지만 `tempTTHH` 에는 `data/samples_2017UL.json`·`samples_2018UL.json` 만 있다. 2016 을 실제로 쓰려면 xsec 표 2 개, 2016 루미(`LUMI_SOURCES.md` 는 2017–2018 만), golden JSON, 트리거, b-tag SF, JEC/JER 이 필요하다. 범위 산정 안 됨.
22k. **Run 2 범위 = full Run 2 (09-11 밤, 사용자 결정)** — 2016 preVFP/postVFP 를 `das_inventory.sh` 로 점검(v15 2 + v9 2, 로그 커밋). 네 Run 2 v15 캠페인의 `NOT_FOUND` 집합이 **동일**(diff 0) — 같은 5 종이 빠져 있고 나머지는 다 있다. 요청 = 5 종 × 4 era-half = **28 datasets ≈162M**(2016 은 09-16 MiniAODv2 부모 기준 27.2M/27.1M; 09-11 의 v9 수치 27.1M/27.1M 을 대체). registry: ttHH 62 행 ERAS 4 era-half 로 확장(era 당 had 45), QCD-HT PRIMARY 를 PSWeights 이름으로 교체(네 캠페인 EXACT) → 2017/18 v15 의 QCD-HT NOT_FOUND 도 해소(27 → 20). 남은 것: ~~2016 MiniAODv2 부모 수~~(09-16 DONE: 두 캠페인 136 키 전부 EXACT, `script/das_inventory_ul16{pre,post}_miniaodv2_20260916_*.tsv`, 원장 V12), `TTTW` 전하 분할 KEY 2 개 + xsec, 데이터 PD 2016 행(v15 JetHT era 문자열 9 개는 `run_discover_ul16_jetht_v15_*.log` 로 확정, `inventory_manifest_run3_2016.txt` 에 반영). `03_DECISIONS.md` D-2026-09-11-run2-scope-2016, `09_v15_migration_log.md` 16·17 절.
22l. **lxplus 실행 기록 배치 1 (09-16)**: 블록 [1]–[7]: `runlog.sh` 게이트 → UL16 MiniAODv2 inventory 2 → Run 3 had 스캔 2 → UL16 JetHT discovery → 35 인벤토리 스윕(failed 0) → 교차표 2, 커밋 `a781cb3`, 맥 pull. 결과 반영: `ttHH/04_mc_request_2026-09.md` §1(2016 열), 덱 v1.9, `09` 17 절, `08` §7, `10_validation_ledger.md` V11–V20, manifest 2016 Data 9 era 행, 브랜치 목록 10 개(신규 `branch_hadronic_2016_v15_{MC,Data}`, `_2024_v15_{MC,Data}`, `_2025_v15_Data`, `branch_CPV_Run2_Data_v15`; 수정 4: `btagWeight_*` 제거(MC 2), 2017 Data `HLT_QuadPFJet*` 제거, 머리 STATUS → checked), `check_branchlist.py`(`--era 2016|2024|2025`, Run 3 prefiring 요구 제외), `build_from_scan_log.py`(22b). **다음 lxplus 배치**: 2016 Data 9 era 스윕(두 패턴 라벨 인벤토리는 문서가 인용하므로 유지), `Run2016B-HIPM…-v1` vs `…_v2-v1` run 범위, 2018A 첫 파일 run 범위(22n). 명령은 RUNBOOK §6.
22l-2. **배치 2 (09-17, lxplus982, git `8690132`, 커밋 `15f377b`)**: selftest → `runs_ul16B_v15`(2016B `-v1` = ver1 run 272760–273017 / 9,726,665 ev / 11 file; `_v2-v1` = ver2 run 273150–275376 / 133,752,091 ev / 145 file) → `runs_2018A_firstfile`(파일 run 316058–316719, dataset 315257–316995) → `sweep_ul16_data_eras`(9 새 인벤토리, dumped 9 / skipped 33 / failed 0, 101 s) → `check_2016_data_list`(9 era 전부 exit 3 = `Jet_jetId`/`Jet_puId` 만, dead 0) → `check_cpv_data_2016`(9 era 전부 exit 0). 전부 EXIT 0. 반영: manifest 머리(B 두 dataset 의 run·event), `ttHH/04` §4, 2016 목록·CPV Data 목록 머리, 원장 V21–V25, `08` §7.4·§7.5, `09` 18 절. 2016 의 six-jet CSV 경로 4 개는 9 era 파일 전부에 있고, `HLT_AK8PFJet450/500` 만 B ver1 에 없다.
22m. **브랜치 목록 점검 결과 (09-16, `08` §7.3)**: 08-17 의 v15 목록 4 개는 dead pattern 2 종(`btagWeight_*`: v15 에 없음; 2017 Data `HLT_QuadPFJet*`: 2017B–E 에 0 개, v9 도 같음)이 있었고 제거. 신규 6 개는 실제 스키마에서 dead 0. 남은 exit 3 은 전부 `Jet_jetId`/`Jet_puId`(analyzer 재계산, `08` §3.4). 열린 것: (a) **트리거 결정** 2016·Run 3 → `HLT_REQUIRED` 채우기(지금 빈 목록 = 검사 안 함); (b) **CPV 목록 per-era 분리**: 2016 경로명 `HLT_IsoTkMu*`/`HLT_L2DoubleMu*`(2017/2018 dead), 2017B 추가 `HLT_TkMu*`/`HLT_TrkMu*`/`HLT_DoubleIsoMu*`/`HLT_MET*`, MC v15 목록의 `Scouting*`(UL16 MC 에 없음); (c) `Flag_METFilters` 가 Summer24 MC·2025 PromptReco 에 없음(개별 `Flag_*` 는 있음) → prescan 프로필·analyzer 확인; (d) `branch_prescan_slim_2017.txt` 는 UL17 MC(v9·v15)에서 Run B calo 경로 3 개가 dead, 07-27 부터 그랬고 prescan 캠페인은 끝났으므로 기록만.
22n. **2018A 초기 HLT 메뉴 (09-16 발견, 한 파일 측정)**: `/JetHT/Run2018A-UL2018_NanoAODv15-v2` 첫 파일(`inv_2018A_v15_Data.tsv` 의 `# source=`)에 analyzer 2018 필수 경로 `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94`·`HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` 가 **없고** 2017 임계값의 DeepCSV 판(`…380_SixPFJet32_DoublePFBTagDeepCSV_2p2`, `…430_SixPFJet40_PFBTagDeepCSV_1p5`)만 있다. B 는 둘 다, C·D 는 새 것만. `requireTriggerBranches2018_()` 이 FATAL 하는 조건이라 확인 필요: 그 파일의 run 범위(`dasgoclient -query "run file=<LFN>"`), v9 2018A 생산에서 어떻게 지나갔는지, analyzer 가 2018A 초기 run 에서 어느 경로를 써야 하는지(AN 의 2018 트리거 정의). `check_branchlist.py` `HLT_ERA_CONDITIONAL["2018"]` 에 두 경로를 넣어 정보로 출력한다. **09-17 측정**: 그 파일의 run 범위는 316058–316719, dataset 은 315257–316995(`run_runs_2018A_firstfile_20260917_060634.log`). 즉 두 경로는 적어도 run 316719 까지 메뉴에 없었다. 어느 run 부터 있는지(2018A 후반 또는 2018B)는 파일 몇 개를 run 별로 골라 스키마를 보면 bracket 된다(RUNBOOK §7). 그 뒤 analyzer 의 `requireTriggerBranches2018_()` 처리와 AN 의 2018 트리거 정의를 맞춘다.
22o. **Run 2 v15 두 갈래 (09-17, 사용자 결정)**: 부재 5 종은 중앙 요청 답장을 기다리는 동안 enriched 사설 생산(TTHHGenCategoryTools D17)을 **병행**한다. 이전 문서들의 "거절 시 대체" 문구는 전부 병행으로 고쳤다(START_HERE §4 ②, `ttHH/04` §4, TTHHGenCategoryTools D17·11·01·03). 착수에 필요한 결정 두 개(글루, 컬럼 이름)는 표 15. 2016 MiniAODv2 입력은 873 + 864 파일, 54.3M ev, 4.2 TB(09-16 inventory). `03_DECISIONS.md` D-2026-09-17-run2-v15-two-tracks.
22p. **결정 묶음 (09-17, 사용자)**: ① tttW 두 키(D-2026-09-17-tttw-split, registry 수정: MC 138 행, era 당 had 46); ② 2016 데이터 PD = 17/18 과 동일(D-2026-09-17-data-pd-2016; `build_from_scan_log.py` 가 `_vN` 변형을 별도 행으로, 합성 로그로 검증); ③ 2018UL v9 보류(D-2026-09-17-ul18-v9-parked); ④ 컬럼 이름 `genTtbarIdExpanded`(D-2026-09-17-expanded-id-column-name); ⑤ D-R3-9 DECIDED; ⑥ FxFx 비교는 보류(결정 불필요), 트리거는 미정(생산 무관). `TTWJetsToLNu` 는 사용자가 DAS 를 더 찾아본 뒤. **enriched 글루 설명(표 15)**: enriched 생산 = MiniAODv2 파일마다 cmsRun(중앙 NANO 설정 + 우리 producer)을 CRAB 으로 4,929 파일에 돌리는 일. 제출 도구가 둘 있다. (A) NtupleForge 의 CRAB 제출기(YAML config + registry + das_scan + preflight + submit/status)는 지금 NanoAODTools 후처리 job 만 알므로 `job_type: cmsrun` 을 새로 가르쳐야 한다(코드 작업, 검증 필요; 대신 Run 3 sidecar 등 앞으로의 cmsRun 생산도 같은 관리 체계). (B) `TTHHGenCategoryTools/TtbarIdExtender/crab/` 은 이미 MiniAOD 위에서 cmsRun 을 CRAB 으로 돌려 본 스크립트라 pset 만 바꾸면 바로 돌지만 registry·preflight·runlog 와 따로 놀아 장부가 둘로 갈린다. 권고: 2017 첫 제출은 (B)로 빨리 시작하고, (A)는 2018·2016·Run 3 sidecar 전에 만든다.
22q. **통합 방향 (09-17, 사용자)**: NtupleForge 를 후처리 + MiniAOD 사전 + MiniAOD→NanoAOD(+사용자 branch) 를 다 하는 모듈 집합체로; 구조가 비직관적이면 분리 유지. 계획 문서 `11_unified_forge_plan.md`(조각 표, 목표 구조, 규칙 5 개, 완료 판정 2 검증, Phase 0–2). 글루는 (A). `TTWJetsToLNu` 는 PINNED 경로 제안(표 4). `das_scan.sh`/`das_inventory.sh`/`build_from_scan_log.py` 에 PINNED 모드 추가(fake DAS 로 검증; 실제 lxplus 스캔에서 재확인 필요, RUNBOOK §7 [2b]).

23. **event-level 항목의 "기억" 확정** — 03_run3_plan §2 의 jet veto map 키·MET filter 목록(ecalBadCalib
    보정 수치)·JEC/JER 태그·golden JSON 이름·PU 키를 twiki 원문으로 대조하고 상태 열 갱신. **값을 코드에
    넣기 전에 반드시.**
24. ~~**Run 3 브랜치 인벤토리 스윕**~~ **DONE 2026-09-16** (08 Step 3b, 35 인벤토리, 원장 V15) → `branch_hadronic_2024_v15_{MC,Data}.txt`, `branch_hadronic_2025_v15_Data.txt` 초안(dead 0; HLT 블록은 2024/2025 주석만 다르고 규칙은 같다, `08` §7.4). 22l·22m.
25. **analyzer(tempTTHH) 작업 항목 발행** — Run 3 cleaning 5 (veto map, MET filter, jet ID 재계산,
    PUPPI, b-tagger) + off 2 (prefiring, HEM). NtupleForge 밖.

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
