# Changelog

All notable changes to NtupleForge. Reconstructed from git history
(`dev260412_TTbarCategory` branch) and curated into logical milestones rather
than raw commits. Dates are approximate (derived from commit/backup
timestamps; `26MMDD` suffixes seen in the repo decode as `20YY-MM-DD`).

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased] — 2026-08-30: v9 ↔ v15 event-matched 동일성 확인 (불일치 0), A18, 검증 전용 branch 목록

### Result — CPV gen categorizer 의 v9→v15 마이그레이션은 물리 결과를 바꾸지 않습니다

`TTToSemiLeptonic` UL17. lumi 로 짝지은 v9/v15 파일 쌍에서 **143,000 개의 같은
event** 를 뽑아 `script/compare_v9_v15.py` 로 `(run, luminosityBlock, event)` join 비교:

| 범위 | 비교 횟수 | 불일치 |
|---|---|---|
| `--prefix TopCPVCat_` (46 branch) | 6,578,000 | **0** |
| `--prefix ""` (61 branch) | 8,723,000 | **0** |
| `--ftol 0` (허용오차 없음, 46 branch) | 6,578,000 | **0** |

`common=143000`, `v9-only=0`, `v15-only=0`. Gate 4 (standalone C++ ≡ 모듈, v9,
2026-08-25) 와 합쳐 **v15 위의 모듈이 기준 구현체에 대해 전이적으로 검증**됐습니다 —
표준 C++ 도구가 `GenPart_statusFlags` 를 `Int_t` 로 읽어 v15 를 직접 비교할 수 없는
제약을 우회한 것입니다. `Int_t→UShort_t` / `Int_t→Short_t` 타입 변경이 물리에 영향이
없다는 것이 추론이 아니라 872 만 회 비교로 실증됐습니다. 전문: 08 6절.

**음성 대조군.** `--prefix ""` 실행이 `only in v15: GenJet_nBHadrons,
GenJet_nCHadrons` 를 보고했습니다 — 3.4절 인벤토리 diff 가 예측한 바로 그 두 개.
비교기가 차이를 실제로 감지한다는 확인이자, 독립적인 두 측정의 교차 검증입니다.

**파일 페어링이 이 비교의 어려운 부분이었습니다.** parent MiniAODv2 가 같아 event
집합은 동일한데 NanoAOD job splitting 이 버전마다 달라 파일 경계가 전혀 대응하지
않습니다 (각 데이터셋 첫 파일끼리 event 겹침 0). v9 파일의 lumi 집합 대 v15 의 398 개
파일을 겹침 순으로 랭킹해 143 lumi 를 공유하는 파일을 찾았습니다. 페어링은 특정 v9
파일에 묶여 있으므로 `setup_v9v15_validation.sh` 가 LFN 을 고정합니다.

### Added

- **`script/compare_v9_v15.py`** — 두 모듈 출력의 event-matched 비교기. 겹침이 비면
  "불일치 0" 이 아니라 **exit 3 으로 실패**합니다 (이 비교에서 깨지기 쉬운 것은 물리가
  아니라 페어링입니다). exit 1 불일치 / 2 공통 branch 없음 / 4 파일 읽기 실패.
- **`script/setup_v9v15_validation.sh`** — `source` 전용 원스톱 세션 준비: cmsenv,
  git pull, proxy, 모든 환경변수, 고정 LFN 입력 2 개, 공유 lumi cut 재생성, 스크래치
  디렉토리 이동. `nf_status` / `nf_pull` / `nf_smoke` / `nf_v9` / `nf_v15` /
  `nf_compare` 명령을 정의합니다.
- **`branches/branch_CPV_validation.txt`** — 검증 전용 최소 출력 목록. 프로덕션 목록은
  2.01 kB/event (입력 NanoAOD 2.06 kB/event 와 사실상 동일 — 버리는 collection 들이
  작고 압축이 잘 되어 이득이 없음) 였고, 143k event 실행 하나가 AFS home 을 99 % 까지
  채웠습니다. 이 목록은 **0.315 kB/event (6.4 배 감소)**. v9 와 v15 에서 이름이 바이트
  단위로 같아 **양쪽에 같은 파일**을 쓰므로 목록이 비교의 교란 요인이 되지 않습니다.
- **`script/run_postproc.py --cut`** — `PostProcessor(cut=...)` 직행. default `None`
  이라 기존 동작 불변. 두 버전을 공유 lumi 집합으로 제한해 각 ~8 분에 끝내기 위한 것
  (전체 파일 두 개는 ~3 h). 출력 event 집합을 바꾸므로 **검증 전용**이며 켜지면
  `PRESELECTION CUT ACTIVE -- VALIDATION MODE` 배너가 찍힙니다.

### Fixed

- **`05_troubleshooting.md` A18 — 앞에 `drop *` 가 오는 branch 목록은 모듈 자신의
  branch 까지 조용히 버립니다.** 스모크 테스트에서 출력이 15 branch / `TopCPVCat_*`
  **0 개** 로 나왔는데 모듈은 `processed=2000 signal=2000` 을 보고했습니다 — 완벽히
  돌고 결과를 전부 버린 것입니다. 에러도 경고도 없습니다. `branch_CPV_validation.txt`
  초안에 "모듈 branch 는 outputbranchsel 을 피해간다" 고 써 두었던 주장이 반증됐고,
  `keep TopCPVCat_*` 를 추가했습니다. 프로덕션 목록들은 leading `drop *` 가 없어
  이 함정에 걸리지 않았습니다.
- **`setup_v9v15_validation.sh`** — untracked 파일이 `git pull` 을 막던 문제
  (`--untracked-files=no`), `$WORK` 에서 bare `git pull` 이 실패하는 문제 (`nf_pull`),
  `INV` 상대경로.

### Measured

- 실효 처리율 **313 Hz (v9) / 288 Hz (v15)**, 각 ~8 분 / 143k event.
  ⚠ 로그의 `Rate = 1868.7 Hz` 는 분모가 *입력* entry 수라 틀립니다.
- `run_postproc.py` 는 `OUTPUT_DIR="."` (CRAB 요구) 이므로 중간 `_Skim.root` 가 항상
  cwd 에 떨어집니다. repo 에서 돌리면 AFS home (10 GB) 이 찹니다 — 스크래치에서
  실행하고 `-o` 에 절대경로(EOS)를 주면 병합 결과만 EOS 로 갑니다.

---

## [Unreleased] — 2026-08-28: v9 NanoAOD가 parent 대비 2.61 % 결손임을 확인, event-matched v9/v15 비교 도구

### Measured — 이 데이터셋의 v9 NanoAOD는 불완전합니다

`TTToSemiLeptonic_TuneCP5_powheg`, UL17. `dasgoclient summary` 실측:

| | nevents | nlumis | parent 대비 |
|---|---|---|---|
| `RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1` (parent) | 355,332,000 | 355,332 | — |
| `RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2` | 355,332,000 | 355,332 | **100.00 %** |
| `RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1` | 346,052,000 | 346,052 | **97.39 %** |

양쪽 모두 정확히 1000 event/lumi 이므로 차이는 **9,280 lumi = 9,280,000 event**
입니다. v9 와 v15 는 **동일한 MiniAODv2 parent** 를 가지므로(`dasgoclient parent`
로 확인), v9 쪽 NanoAOD 생산이 parent 를 다 덮지 못한 것입니다. 잃어버린 lumi 는
실패한 생산 job 이라 물리적으로 무작위이므로 **편향이 아니라 통계 손실**이고,
`genEventSumw` 를 실제로 처리한 파일에서 합산하는 한 정규화는 자기일관적입니다.
v15 마이그레이션의 추가 근거이며 그룹 보고 사안입니다.

### Measured — v9/v15 파일 경계는 전혀 대응하지 않습니다

parent 가 같아 event 집합은 동일한데, 각 데이터셋의 "첫 번째 파일" 은 event 가
**하나도 겹치지 않았습니다** (v9 1,126,000 / v15 927,000, overlap 0). lumi 범위는
[14715,353516] 과 [2579,331876] 로 크게 겹치지만 lumi *집합* 이 거의 서로소입니다
— NanoAOD job splitting 이 버전마다 다르기 때문입니다. 따라서 event-matched 비교는
**lumi 목록으로 파일을 짝지어야** 합니다: v9 파일의 lumi 집합을
`LuminosityBlocks` 트리에서 읽고, `dasgoclient -query="file,lumi dataset=..."`
(v15 398 파일) 로 겹침을 랭킹하면 143 lumi (~143k event) 를 공유하는 파일이
나옵니다. 이 페어링은 **특정 v9 파일에 묶여 있습니다** — `head -1` 로 다른 파일을
집으면 겹침이 사라집니다.

### Added

- **`script/run_postproc.py --cut`** — `PostProcessor(cut=...)` 로 직행하는
  preselection. default `None` 이라 기존 동작 불변. 두 NanoAOD 버전을 공유 lumi
  집합으로 제한해 event 단위로 비교하기 위해 존재합니다 (전체 파일 두 개를 도는
  ~3 h 대신 각 ~15 min). **출력 event 집합을 바꾸므로 검증 전용**이며, 켜지면
  `PRESELECTION CUT ACTIVE -- VALIDATION MODE` 배너가 로그에 찍힙니다. 물리 컷은
  여전히 모듈의 `analyze()` 에 둡니다.
- **`script/setup_v9v15_validation.sh`** — `source` 용 세션 부트스트랩. 새 lxplus
  세션이 잃는 것(셸 변수, `/tmp` 의 NanoAOD 2개, 공유 lumi cut 문자열)을 전부
  복구합니다. LFN 은 위 페어링 때문에 **고정**되어 있습니다. `NF_CACHE` 를 EOS 로
  두면 5 GB 재다운로드를 피할 수 있습니다.

---

## [Unreleased] — 2026-08-27: 실제 파일 기반 v9/v15 스키마 측정, v15 CPV branch 목록, check_branchlist (C) 오탐 수정

### Added

- **`docs/08_branch_schema_migration.md`** (신규) — branch 목록을 실제 NanoAOD
  파일에서 유도·검증하는 6단계 절차(복사용 명령어 포함)와, 2017UL MC로 실측한
  v9 → v15 스키마 차이 **127 removed / 370 added / 86 retyped**, 그리고
  workstream별 영향. `docs/07_DeveloperGuideline.md` 에 이를 의무화하는
  **Rule 8** 과 Rule 4 라우팅 표 항목, 커밋 체크리스트 항목 추가.
- **`branches/branch_CPV_Run2_MC_v15.txt`** — v9 목록을 실제 v15 인벤토리
  (`script/inventory/inv_2017UL_v15_MC.tsv`, Events 1903 branches)에 대고 포팅.
  v9 rule chain을 v15가 추가한 364개 Events branch에 시뮬레이션해 281개가
  살아남는 것을 확인하고, 그중 per-candidate·미사용 서브시스템 **49개**만 drop
  추가 (`PFCand_*`, `FatJetPFCand_*`, `TrackGenJetAK4_*`, `GenProton_*`,
  `PVBS_*`, `DST_*`, `Scouting*`, `nTauProd`). 새 MET/Rho(`PFMET_*`,
  `RawPFMET_*`, `TrkMET_*`, `FiducialMET_*`, `Rho_*`), 새 태거(PNet/UParT/
  globalParT3), 새 gen 컬럼(`GenJet_n{B,C}Hadrons`, `GenPart_iso`)은 의도적으로
  유지. dead HLT 2개는 v9와 동일하게 남김 — 이 파일은 "v15 스키마" 한 축만 변경.
- `script/inventory/` — `inv_2017UL_v9_MC.tsv` (1666 branches),
  `inv_2017UL_v15_MC.tsv` (1903), `diff_v9_v15_2017UL_MC.txt`.

### Fixed

- **`script/check_branchlist.py` — (C) 절의 오탐 6건.** (C)는 *입력* 스키마에
  대한 검사인데, `cpv` profile의 required 목록에 있던 모듈 **산출** branch
  (`TopCPVCat_isSignal`, `..._Channel_Idx`, `..._Channel_Idx_Expanded`,
  `..._GenPar_Count`, `..._GenBJet_Count`, `..._GenBHad_Count`)를 입력
  인벤토리에서 찾고 있었습니다. 중앙 NanoAOD에 있을 리 없으므로 v9·v15 양쪽에서
  항상 실패했습니다. required 항목에 `produced` 플래그를 도입해 (C)에서 제외하고,
  제외 개수를 출력에 찍어 조용히 넘어가지 않게 했습니다. 이 6개에 대해서는
  (B)("rule chain이 출력까지 살려 보내는가")만이 유의미한 검사입니다.
  => 이제 `rc=4` 는 순수하게 dead 패턴 문제만을 의미합니다.

### Measured (근거, 전문은 08 2절·3절)

- **XRootD 직독이 병목이지 모듈이 아님.** 2000 events 기준 lxplus WAN 2.2 Hz
  vs /tmp 로컬 199.5 Hz. WAN `noop` 실행의 CPU 사용률은 3.8 %. 모듈 자체 비용은
  `user+sys` 차이로 **1.33 s / 2000 events = 0.66 ms/event** (순수 복사 대비
  CPU +11 %). 1.126 M event 파일 ~1.57 h => CRAB wall-time 안. 앞서 제기된
  "2.2 Hz면 생산 불가" 우려는 **철회**.
- **CPV 모듈의 read set은 v15에서 이름 변경 0건, 삭제 0건.** 타입만 변경:
  `GenPart_statusFlags` Int_t->UShort_t (bit 7/13 사용 => 잘림 없음),
  `GenPart_genPartIdxMother` Int_t->Short_t, count branch들 UInt_t->Int_t.
  `GenJet_hadronFlavour` 는 UChar_t 그대로 => `to_int` 계속 필요.
- **ttHH 위험 신호**: v15에서 `Jet_puId`·`Jet_jetId`·`Jet_btagDeepB`·`Jet_qgl`·
  `ChsMET_*` 등이 대체 없이 삭제. `Jet_btagDeepFlavB` 는 생존.
- **`HLT_IsoTkMu*` / `HLT_L2DoubleMu*` 는 2017UL v9·v15 모두 dead** (각각 job당
  ROOT 에러 1줄). 2016 경로명이고 파일이 Run2 4개 era 공유이므로 삭제 금지 —
  per-era 분리가 정답. `01_STATUS.md` OPEN 참조.

---

## [Unreleased] — 2026-08-17: reconciled with the v8.1 handoff tar — three lost records restored, one mis-targeted edit corrected, log hygiene

The `NtupleForge_TopCPV_v8_1_handoff` tar (a 2026-07-15 snapshot) was diffed
against this tree file by file. **Code-wise the tar is a strict subset** — every
`.py`/`.sh`/`.yaml` in it is either identical here or superseded — so nothing was
back-ported. But three *records* had been dropped from the docs between
2026-07-15 and 2026-07-27 while the work they tracked was still undone, and one
config edit had landed on the wrong file. No physics logic changed.

### Restored (tar → here)

1. **`01_STATUS.md` OPEN #0 — condor path + validation config.** Deleted on
   2026-07-26 *without the work being done*: re-verified 2026-08-17, NtupleForge
   still has **no `condor/` directory**. Restored with its recovery pointer
   (past-chats search string), the list of lost files, and all six design
   decisions (condor=local vs CRAB=grid; worker runs `run_postproc.py` with the
   same module+branch wiring; `<dataset>_chunkNNN.root` naming shared with the
   standalone; `MY.JobBatchName`; `config.sh` in `transfer_input_files`;
   preflight `condor_submit` guard + `-s TAG`). Sub-item 1 of 2 is now **DONE**
   (see below); the `condor/` glue is still open.
2. **Ops guidance from the deleted `2026-07-15 (2)` rename entry.** The
   `forgedNtuple.root` rename is re-recorded here as `2026-07-26 (6)` (D-F), but
   two operational notes were lost with the older entry and are reinstated:
   - Anything that matches outputs **by filename** — hadd globs, pullers,
     `checkOutputs`-style scripts — must accept **both** `forgedNtuple_*` and
     `slimmedNtuple_*` during the transition. Cleaner alternative: **pair a
     rename with the next campaign tag** so each campaign directory is
     single-named. Only `make_filelists.py` was ever fixed for this.
   - The name is baked into each task's sandbox/PSet at submit time, so it takes
     effect **from the next submission**. Already-produced files keep the old
     name — and so do the remaining jobs of **in-flight tasks**.
   - Dating note: `crab/PSet.py` and `crab/submit_crab.py` in the 2026-07-15 tar
     already contain `forgedNtuple.root`, so the rename predates the `2026-07-26`
     stamped in their comments. Left as-is (harmless), recorded here.
3. **`.gitignore` rules `*.bk*` and `._*`.** Dropped in the 2026-07-26 rewrite;
   `._*` for no stated reason, `*.bk*` immediately before a `.bk` file became the
   only copy of a production config (next item).

### Corrected

4. **`config_CPV2017UL_MC.yaml` restored to its full 73 datasets;
   `config_CPV2017UL_MC_validation.yaml` created.** On 2026-07-26 the production
   config was overwritten in place (73 → 13 datasets, jobID/output_base →
   `CPV2017UL_MC_Validation`) with **no CHANGELOG / DECISIONS / STATUS entry**,
   leaving the 73 only in `config_CPV2017UL_MC.yaml.bk`. The 13-sample cut was
   correct work aimed at the wrong file: OPEN #0 had already named the intended
   target `config_CPV2017UL_MC_validation.yaml`. Restored from the `.bk` (md5
   `2c6db20cf550db67e4447b08ac1c1dd9`, identical to the tar); the subset moved to
   its own file with an explicit label contract in the header. **Re-verified:**
   the 13 keys and their DAS paths match `TopCPVGenCategorizer/condor/datasets.txt`
   1:1 — 13/13 labels, 13/13 paths, zero mismatches. Both files YAML-parse and
   pass `--preflight` (Rule 6 PASS). Decision:
   **D-2026-08-17-validation-config-split**.
   *Follow-up for the analyst:* the now-redundant `.bk` is ignored again but is
   still tracked — `git rm --cached crabConfig/config_CPV2017UL_MC.yaml.bk`.

### Log hygiene (new)

5. **Never commit CRAB transcripts — `.gitignore` hardened, A17 + decision
   added.** `crab submit` echoes the pre-signed S3 POST policy and signature used
   to upload the task sandbox to `crabcache_prod`. A history audit found two such
   blobs in this **public** repo: `submit_UL18_full_20260727_1120.log` (1.52 MB,
   commit `33e3030`) and `ttbar_SemiLeptonic_v1/.../crab.log` (6.71 MB, commit
   `c72a711`). Both are out of HEAD but reachable in history; **every signature
   in both had already expired** (2026-07-27T10:20Z and 2025-12-11T09:24Z
   respectively) and each was scoped to a single bucket+key, so **nothing needs
   rotating** and no grid credential is exposed. `.gitignore` now blocks
   `submit_*.log`, `crab_status_*.log`, `localcheck_*/`, `local_test_*.log` with
   the reason inline, and keeps the deliberate carve-out for
   `script/das_ul18_scan_*.log` (DAS output, no secrets, and the documented input
   of `build_ul18_from_log.py`). History rewrite is **deliberately not done** —
   recipe and rationale in `05_troubleshooting.md` **A17** and
   `03_DECISIONS.md` **D-2026-08-17-no-logs-in-git**.

### Small code fixes (behaviour-preserving)

6. **`crab/submit_crab.py` — Rule 6 check now accepts both quote styles.** The
   preflight regex only matched `cms.untracked.string('...')`, while
   `07_DeveloperGuideline.md` Rule 6 documents the double-quoted form — a
   guideline-conformant `PSet.py` produced a spurious
   `could not parse` FAIL. Now `(['"])(.+?)\1` with optional inner whitespace;
   verified against single-quoted, double-quoted and padded forms. Re-ran
   `--preflight` on both CPV MC configs: **Rule 6 PASS**, totals unchanged.
7. **`script/das_ul18_scan.sh` — USAGE header teed the log into the CWD**, but
   `build_ul18_from_log.py` only globs `script/`, so following the header
   verbatim ended in `FATAL: no das_ul18_scan_*.log found under script/`. Header
   now shows the form `README.md` already used
   (`bash script/das_ul18_scan.sh … | tee script/das_ul18_scan_….log`).
   *(An earlier note that this file was not executable was wrong — it is `0700`
   on disk; only the container copy lost the bit.)*

### Branch policy recorded

8. `origin/main` is at `c76d014` (2026-07-05), **13 commits behind** and without
   even the 2026-07-15 TopCPV state, while being the repo's default branch.
   `main` is fully contained in `devExtendedTtbarId`, so a fast-forward is
   available at any time; deliberately **not** taken mid-campaign. Recorded at
   the top of `01_STATUS.md` and as **D-2026-08-17-branch-policy**.

### Also confirmed (no action)

- `script/das_ul18_scan_20260726_1657.log` **is** tracked (432 lines, 33 KB), so
  the UL18 configs' provenance is reproducible from this checkout. An earlier
  reading that it was missing came from a copy step that skipped it.
- The `2026-07-27 (4)` slot is genuinely absent from this log; (3) is followed by
  (5). Nothing in the repo references it — treat the gap as a numbering slip, not
  a lost entry.

---

## [Unreleased] — 2026-07-27 (7): CRAB 10,000-jobs-per-task limit documented at every decision point

No behaviour change. A sibling repo lost a day to this and the same code path
exists here with no guard, so the trap is now written down where someone about
to change the value will actually see it.

### The trap
`splitting: FileBased` -> `njobs = ceil(nfiles / units_per_job)`. CRAB refuses
any task above **10,000 jobs**, but **server-side, after the client reported a
successful submit**. So `crab submit` looks fine, the task then sits at
`SUBMITREFUSED`, `--report` shows a row of all zeros (indistinguishable from
"not started yet"), and `--resubmit` cannot fix it -- resubmit only requeues
*failed* jobs of a task that reached the scheduler. One dataset silently
produces nothing.

### Added (comments, at the points where the value is chosen)
- `crab/submit_crab.py` at the `conf.Data.unitsPerJob` assignment.
- `crabConfig/config_ttHH2017UL.yaml` next to `units_per_job: 1`.
- `script/build_ul18_from_log.py` -- stamped into **both** generated 2018
  configs, so it survives regeneration. Verified: regenerating leaves the 85/81
  dataset configs and `samples_2018UL.json` otherwise unchanged.

### Added (docs)
- `03_DECISIONS.md` **D-2026-07-27-crab-job-limit**.
- `05_troubleshooting.md` **A16** (marked PREVENTIVE -- not yet observed here).

### Why NtupleForge is safe today, and exactly when it stops being
These configs read NanoAOD (~20x fewer files than the MiniAOD parents): largest
2018UL dataset **by file count** is `WJetsToLNu_HT200To400_ext1` at **780 files
-> 780 jobs** (`TTbar_SemiLep` is largest by events but 4th by files, 391 --
job count follows FILES). The 7,466-job
campaign is spread over **85 tasks** and the limit is **per task** -- do not read
the campaign total as if it were near the ceiling. It breaks if a config is
pointed at MiniAOD, or a >10,000-file dataset is added, with `units_per_job: 1`.

### OPEN gap
`--preflight --check-das` here does **not** compute per-task job counts. The
extend submitter in `TTHHGenCategoryTools` does (DAS `nfiles` -> FAIL above the
limit, WARN above 90%, prints the required `units_per_job`). Porting it is the
follow-up; until then the check is manual:
`dasgoclient -query "summary dataset=<DS>" -json | grep -o '"nfiles":[0-9]*'`.

Canonical rule: `TTHHGenCategoryTools/docs/04_decisions.md` **D15**;
incident: that repo's `docs/08_troubleshooting.md` **T-19**.

---

## [Unreleased] — 2026-07-27 (6): 2018 luminosity settled — 59.83 → **59.56 fb⁻¹**

### Changed
- `script/build_ul18_from_log.py` `_meta` block: `lumi_fb_inv` **59.83 → 59.56**, plus a
  full lumi provenance block mirroring the 2017 schema (uncertainty 0.84 %,
  PreLegacy 59.47, Golden JSON filename, brilcalc command, citation, 2018-only
  combine nuisance `lumi_13TeV_15161718_l = 1.0084`, and
  `lumi_brilcalc_result_fb_inv: null`).
  **Regenerated and verified byte-identical** against the hand-edited
  `tempTTHH/data/samples_2018UL.json`, and both crab configs came out unchanged —
  so the value cannot silently revert on the next regeneration.
- `docs/01_STATUS.md` OPEN (b) → **SETTLED**.

### Why
The user supplied the LUM POG page itself. Its **"Recorded Golden Legacy"** row is
the one that matches our UltraLegacy samples: **2017 = 42.07 (0.82 %)**,
**2018 = 59.56 (0.84 %)**. **59.83 appears nowhere on that page** — it had been a
placeholder. PreLegacy (42.12 / 59.47) must not be used.
Sources now linked from the docs:
<https://twiki.cern.ch/twiki/bin/viewauth/CMS/TWikiLUM> (index) and
<https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2> (the table);
cite **CMS-PAS-LUM-20-001**.

### Still open (per the TWiki itself)
The page requires re-running `brilcalc` on the analysis' own certified JSON
(run/lumi + trigger selection); the quoted numbers are full-dataset values.
2017 was done (42.0688 → 42.07); **2018 has not been**. Full change list and the
9 places lumi lives: `tempTTHH/docs/reference/LUMI_SOURCES.md`.

---

## [Unreleased] — 2026-07-27 (5): reproducibility audit — broken commands fixed, phantom feature retracted, status corrected

No production code changed. This entry records the result of auditing every
documented command against the actual CLI of the scripts it invokes.

### Fixed — commands that would have failed as written
- `README.md` "Run locally" passthrough example used `-I modules.noop`.
  `-I` takes **one** `module.path:LIST_NAME` token; with `:LIST_NAME` omitted the
  driver looks for a list literally named `modules` (lowercase), while every
  module in this repo exports `MODULES` → `list 'modules' NOT found`, exit 1.
  Now `-I modules.noop:MODULES`, and the argument table states the rule.
  (The other example, and the UL18 section, were already correct — hence the
  README contradicted itself.)

### Changed — `--ttcat-*` flags labelled DEPRECATED (dead)
- `run_postproc.py` parses `--ttcat-debug-csv`, `--ttcat-debug-csv-path`,
  `--ttcat-quiet` and passes them to `modules/ttbarCategorizer.py` **through
  environment variables — but that module does not exist in this repo**
  (`modules/` holds `noop`, `topCPVCategorizer`, `jetsMETcut`,
  `nanoaod_branch_access`). The flags are accepted and do nothing. Documented as
  such in the README argument table rather than left as an invisible trap.

### Retracted — the AAA fallback never existed in the committed code
- Entry **2026-07-27 (3)** announced `resolve_input_files()` + `--xrd-fallback`.
  That change was **fully reverted the same day** at the user's request and the
  revert was never written down, so two documents advertised a flag that raises
  `unrecognized arguments`. Both are now corrected in place:
  the changelog entry carries a **[REVERTED]** banner, and
  `05_troubleshooting.md` **A15** now opens with "There is NO AAA fallback in the
  code" plus what to do instead (let CRAB's retries move the job).
  The *reasoning* for dropping it is preserved — it is the useful part.

### Corrected — `01_STATUS.md` was describing a superseded plan
- Said the prescan CRAB submission "is the next action" and that real production
  would come "after the ttHH categorization work lands". Neither happened:
  the prescan smoke task was **killed and its project dir removed**, and the
  **full UL18 production was submitted 2026-07-27** (85 tasks / 7,466 jobs /
  6.74 TB, preflight 35 PASS / 0 FAIL) without waiting for the categorizer —
  the two campaigns are independent because the analyzer resolves
  `Expanded_genTtbarId` at runtime from patch files.
- Watch items recorded: `WJetsToLNu_HT200To400_ext1` (461/780 failed) and
  `HT70To100_ext1` (322/669) — A15-type KISTI `[3011]`, recovered by retries.
- Removed the stale OPEN "(c) jobID/splitting placeholders until first
  submission" (the submission happened). Clarified **61 MC primary datasets
  (queries) → 77 MC entries (with ext variants) → 85 total with Data**, which
  read as three inconsistent counts.

### Housekeeping
- `.gitignore`: no rule change needed, but the files deleted in the previous pass
  are still in the index — `git rm` them (see the report accompanying this
  change). Deleted a stale `script/__pycache__/run_postproc.cpython-310.pyc`
  that still contained the reverted `--no-xrd-fallback` and was the only on-disk
  evidence for the phantom feature.

---

## [Unreleased] — 2026-07-27 (3): A15 incident — documented; AAA fallback added but OPT-IN → **REVERTED, see 2026-07-27 (5)**

### Incident (A15)
- First failure of the UL18 full production: a `TTbar_SemiLep` job at
  `T2_KR_KISTI` died in 14 s with `[3011] No such file` — the bare LFN resolved
  to the local SE only, and `ROOT.TFile.Open` has no redirector fallback (cmsRun's
  `PoolSource` would have retried; our `scriptExe` path gets nothing for free).
  Rucio listed the site as holding the block, so "the site has the data" does not
  guarantee the file opens.
- **Resolution: do nothing.** The post-job log shows CRAB classifies it as
  `RECOVERABLE` → `COOLOFF` → DAGMan retries (max 3), and each retry is
  re-matched, so it can land at a site that can serve the file. That is a better
  remedy than anything the job can do for itself.
- **Not a regression:** the no-fallback structure predates all 2026-07 changes.
  It fires only when the matched site cannot serve the file, so it depends on
  replica health and scheduling luck — it was very likely absorbed silently by
  the same retries during the 2017 campaign.
- Full write-up incl. the `50115 BadFWJRXML` red herring and a diagnosis recipe:
  `05_troubleshooting.md` **A15**.

### Added (opt-in, default OFF) → **REVERTED the same day — DO NOT LOOK FOR THIS CODE**
> **[REVERTED 2026-07-27]** At the user's request the whole AAA-fallback change was
> **fully removed** from `script/run_postproc.py` (0 traces; `grep xrd` returns
> nothing). `--xrd-fallback` and `resolve_input_files()` **do not exist** — passing
> the flag gives `error: unrecognized arguments: --xrd-fallback`. Only the
> *diagnosis* half was kept (`05_troubleshooting.md` A15). The reasoning below is
> preserved as the record of why it was tried and why it was dropped.

- `script/run_postproc.py` `resolve_input_files()` + **`--xrd-fallback`**:
  probe-open inputs (local first) and re-route unreadable ones through
  `cms-xrd-global` → `xrootd-cms.infn.it` → `cmsxrootd.fnal.gov`; a file that
  opens nowhere exits **2** with an explicit list instead of a traceback from
  inside `PostProcessor.run()`.
- **Written and demoted to opt-in on the same day**, after re-assessing it at the
  user's prompting ("is this worth doing now, could it hurt?"). It is not a free
  win: (1) narrow scope — if no replica is readable anywhere, the redirector
  cannot help either, and the useful case is the one CRAB's retry already covers
  better by moving the job; (2) it can be **harmful** — a transient local failure
  is indistinguishable from a missing replica, so the job silently degrades to
  WAN streaming instead of failing fast and being re-matched, and one
  `TTbar_SemiLep` file (~1.22 M events) read 5–10× slower can exceed the 600-min
  walltime; (3) it is unproven on the grid, and shipping unproven code in a
  7,466-job sandbox is itself a risk (cf. A14).
  With the flag off, the default code path is unchanged (no probe, no extra open).
- Verified locally against a stubbed ROOT for all three paths (local OK / AAA
  rescue / unreadable → exit 2). **Never exercised on the grid.**

### Ops note
- A code fix does not reach already-submitted tasks: CRAB ships the sandbox at
  submit time, so `crab resubmit` reuses the OLD script (same trap as A14).
  Anything patched must go out as **NEW tasks**.

---

## [Unreleased] — 2026-07-27 (2): plan re-scope — injector DEFERRED, UL18 full production is the path

### Decided (user, 2026-07-27)
- **`modules/expandedTtbarIdInjector.py` is DEFERRED to a later update.** The
  project's end goal is unchanged — NtupleForge, not the analyzer, should own
  `Expanded_genTtbarId` as a baked-in branch — but writing it now would add
  new-module validation *plus a full ntuple re-production* to the critical path,
  and the immediate objective is the fastest route to UL18 control plots.
  The interim contract (analyzer-side runtime patch lookup, the 2017-proven
  path, zero new code), the cost of deferring, and the resume conditions are
  recorded in `01_STATUS.md` and in the workspace `00_CONTEXT…md` §1.
- **The slim prescan CRAB production is cancelled**, not just postponed: its
  purpose (do the UL18 samples produce? does the slim path work?) was met by
  the 2026-07-27 local run. `config_ttHH2018UL_prescan.yaml` and the two
  `branch_prescan_slim_*.txt` files are kept — they remain the cheapest way to
  re-test a new era or a new NanoAOD version.
- New runbook: workspace `RUNBOOK_UL18_to_controlplots.md`
  (`RUNBOOK_UL18_step1.md` marked SUPERSEDED).

### Added (runbook §2, Phase 1-0)
- **Pre-submission local multi-sample check** for the full production, added on
  the user's prompting after recalling the A14 incident: in the CPV campaign
  *signal passed and only the `QCD_HT*` background died* in CRAB
  (`05_troubleshooting.md` A14 — `math.cosh` overflow on status-21 beam-parallel
  partons), which a single-sample test could never have caught. The new check
  runs 4 datasets of different character (smallest MC / largest MC / `_ext1` /
  Data) at `-N 500` and asserts per sample: file opens, Events non-empty,
  ≥500 branches (i.e. `keep *` really applied), and for MC that
  `Runs.genEventSumw`, `genWeight`, `genTtbarId` are present; ROOT `Error in <`
  lines must be 0.
  **Risk assessment recorded honestly:** this campaign uses `noop.py` +
  `keep *`, so it does no per-event math and is schema-agnostic — the A14 class
  of failure *cannot* recur here, and neither can `SetBranchStatus` errors. The
  residual risks the check does cover are dataset-path typos, unreadable files
  and empty datasets; `--check-das` covers existence for all 85.

---

## [Unreleased] — 2026-07-27: first REAL lxplus run of the UL18 prescan path — 3 fixes

### Verified on lxplus (logs supplied by the user)
- **`--preflight` on `config_ttHH2018UL_prescan.yaml`: 35 PASS / 0 WARN / 0 FAIL
  → READY TO SUBMIT.** Environment (CRABClient, CMSSW_14_2_1 el8_amd64_gcc12,
  proxy 168 h), Rule 6 (`forgedNtuple.root` on both sides), all 81 datasets,
  and the outLFN/requestName preview all check out.
- **Local `-N 2000` run on a real UL18 file** (`TTbb_4f_TTTo2L2Nu…-v1`,
  xrootd): job finished successfully and the output satisfies every check the
  slim strategy depends on —
  `Runs` tree present with `genEventSumw`/`genEventSumw2`/`genEventCount`,
  `LuminosityBlocks` also passed through, Events kept exactly **15** branches
  including `run`/`luminosityBlock`/`event`/`genWeight`/`genTtbarId`.
  **The slim-branch strategy is now empirically validated, not just argued.**
- **Physics finding (feeds tempTTHH trigger work):** the 2018 NanoAOD contains
  `HLT_PFHT330PT30_QuadPFJet_75_60_45_40_TriplePFBTagDeepCSV_4p5`,
  `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94`,
  `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` (+ `HLT_PFHT1050`,
  `HLT_IsoMu24`, `HLT_IsoMu27`), and **none of the six 2017 CSV-era paths**.

### Fixed
- **`--check-das` reported all 81 datasets as unresolvable (false FAIL).** The
  plain-text output of `dasgoclient -query "summary dataset=…"` is a column
  layout, not `nevents=N`, so the regex never matched. Now queries with
  `-json` and reads `summary[0].nevents` — the same code path
  `script/das_ul18_scan.sh` already proved on lxplus — with a plain-text
  regex fallback. Verified against a stub dasgoclient (81/81 resolved).
- **Branch selection is now ERA-SPECIFIC:** `branch_prescan_slim.txt` →
  **`branch_prescan_slim_2018.txt`** (+ new `branch_prescan_slim_2017.txt`).
  Reason: a `keep` pattern that matches nothing is **not** silently ignored —
  ROOT prints `Error in <TTree::SetBranchStatus>: unknown branch -> …` once per
  job for each. The six 2017 CSV HLT names produced exactly that on the UL18
  file. Beyond log noise (6 lines × thousands of jobs), a real typo would be
  indistinguishable from these expected misses; with per-era lists any such
  error now means a genuine problem. The earlier claim in the old file's header
  that unmatched keeps are "harmless" was wrong and is corrected.
  The 2017 file's HLT list is taken from the analyzer's production 2017 logic
  and is marked **unverified** until a `-N` run on a UL17 file confirms it.
- **`config_ttHH2018UL_prescan.yaml`: `units_per_job` 5 → 1.** The "slim output
  ⇒ bigger jobs" reasoning was wrong: the INPUT is read in full regardless
  (A4, `branchsel=None`; the driver even logs "input is read in full"), so job
  runtime scales with input files. 1 file/job is the value the 2017 campaign
  proved; at 5 the largest 2018 samples (TTbar_SemiLep 476 M events over 391
  files ⇒ ~6.1 M events/job) would risk the CRAB walltime.
- `script/build_ul18_from_log.py` updated for both of the above so the configs
  stay reproducible; regenerated.

---

## [Unreleased] — 2026-07-26 (7): `--preflight` pre-submission checker + audit fixes

### Added
- **`crab/submit_crab.py --preflight`** — read-only, submits nothing, creates
  nothing but a log (`preflight_<config>_<timestamp>.log`), exits non-zero on
  any FAIL. Checks: config schema (`common.*` keys, splitting value), analysis
  module file + that the declared list variable is actually assigned, sibling
  `.py` files that will be shipped, branch-selection file (rule count, syntax,
  SLIM vs PASSTHROUGH, and — for SLIM — that `run`/`luminosityBlock`/`event`
  are kept and `genWeight`/`genTtbarId` are not silently dropped), **Rule 6**
  (parses the output filename out of both `PSet.py` and `submit_crab.py` and
  compares), worker files, CRABClient/CMSSW/VOMS environment, cwd writability,
  dataset path syntax + duplicates + tier mix, an outLFN/requestName preview,
  and existing CRAB project dirs that would make a submit skip. `--check-das`
  additionally resolves every dataset on DAS; `--preview N` controls listing.
- **Guarded CRAB imports:** `CRABClient`/`CRABAPI` import failures no longer
  crash the script at import time — they are reported as a preflight FAIL, and
  any real action fails fast through `_require_crab()`. This is what lets
  `--preflight` run in a shell where `crab-setup.sh` was not sourced.

### Fixed (2026-07-26 audit)
- `build_ul18_from_log.py` and the artefacts it stamps (`config_ttHH2018UL*.yaml`
  header, `samples_2018UL.json._meta.source_log`) referenced a **nonexistent**
  `script/logs/das_ul18_scan_2026-07-26.log`; corrected to the real
  `script/das_ul18_scan_20260726_1657.log` and regenerated (contents otherwise
  byte-identical).
- `docs/07_DeveloperGuideline.md`, `docs/05_troubleshooting.md` and `README.md`
  still stated that both Rule-6 sites use `slimmedNtuple.root`; updated to
  `forgedNtuple.root` (the rename is what the preflight now enforces).
- `.gitignore`: ignore `preflight_*.log`.

---

## [Unreleased] — 2026-07-26 (6): D-F executed — output ntuple renamed to forgedNtuple.root

### Changed (BEHAVIOUR — new productions write a different filename)
- **Producers (authoritative, Rule 6 pair kept identical):**
  `crab/PSet.py` `process.output.fileName` and `crab/submit_crab.py` `out_name`
  → **`forgedNtuple.root`** (was `slimmedNtuple.root`).
- **Consumers / file discovery — accept BOTH names**, because every ntuple
  produced before today is physically on Tier-3 as `slimmedNtuple_*.root`
  (campaign `ttHH2017UL_fullNano_v20` included). A forged-only pattern would
  make the existing 2017 filelists unregenerable:
  - `tempTTHH/make_filelists.py`: new `NTUPLE_PREFIXES = ("forgedNtuple",
    "slimmedNtuple")`, used by `find_root_files()`.
  - `TTHHGenCategoryTools/Validation/filelists/make_filelists.py`: same constant
    and same dual matching.
  Remove the legacy prefix only after every campaign has been reproduced.
- Docs/comment-only: `script/validate_topcpvcat.py` usage example,
  `TTHHGenCategoryTools/Validation/scripts/submit_hist_condor.py`,
  `Validation/tools/{makeTtbarHist,matchTtbarId}.cc` header comments.
- Rule 7 grep performed workspace-wide (not only `crab/`+`script/`+
  `crabConfig/`): the only functional hits were the two producers and the two
  filelist makers. `TtbarIdHistCompare/` (legacy, D-G),
  `tempTTHH/docs/backup_20260629/`, `docs/legacy/` and committed filelist data
  files were intentionally left untouched. Analyzer-side `TFile::Open` calls
  take their paths from the filelists, so no other code hardcodes the name.
- Verified locally: producer strings identical (Rule 6), all touched Python
  parses, `str.startswith(tuple)` matching confirmed on both prefixes.
  **unverified:** no CRAB run yet with the new name.

---

## [Unreleased] — 2026-07-26 (5): UL18 prescan smoke-test campaign (slim branches)

### Added
- **`branches/branch_prescan_slim.txt`** — minimal Events-tree selection
  (`drop *` + explicit keeps) for a cheap UL18 smoke-test production whose only
  consumer is tempTTHH `prescan`. Header documents *why it is safe*: Σgenw is
  read from `Runs.genEventSumw/genEventSumw2/genEventCount`, and output branch
  selection filters only the Events tree while the post-processor copies `Runs`
  and `LuminosityBlocks` through (04_architecture, 05_troubleshooting).
  Verified prescan Events usage in `ttHHanalyzer_unified.cc`: `genWeight`
  (L1902), `genTtbarId` (L1913/1927), `run`/`luminosityBlock`/`event`
  (L1917-18, the Expanded_genTtbarId 3-key). **Hazard the keeps guard against:**
  a missing `genTtbarId` is NOT detected — eventBuffer defaults it to 0, so
  every MC event would be silently binned as tt+LF (`sumGenW_id_0`); same for
  `genWeight` → `sumGenW_total = 0`. Also keeps the hadronic HLT bits so the
  2018 path availability (DeepCSV variants) can be checked on the slim ntuple.
- **`crabConfig/config_ttHH2018UL_prescan.yaml`** — 81 datasets: all 77 MC +
  **JetHT only** for Data (user decision: 2018 has no BTagCSV, and SingleMuon
  is only needed for the later trigger-SF study; it stays in the full config).
  `jobID/output_base = campaign_ttHH2018UL_prescanSlim_v1`, `units_per_job: 5`
  (slim output ⇒ fewer, larger jobs). Generated by
  `script/build_ul18_from_log.py` alongside the full config, so both stay in
  sync with the DAS log. YAML-schema checked against every key
  `crab/submit_crab.py` consumes. **unverified — no CRAB submission yet.**

### Verified
- UL18 sample completeness: all 85 entries carry `nevents`+`nfiles`
  (MC total 2,428,778,733; Data/JetHT+SingleMuon 1,662,166,075), and every MC
  entry has non-null xsec/BR — so the post-production prescan can be compared
  against DAS `nevents` sample by sample.
- Sample-list cross-check vs the ttH AN (AN-2019/094, non-UL, reference only):
  44/61 MC primaries appear there; 5 more (TTHHto4b, TT4b, TTZToBB, TTZHTo4b,
  TTZZTo4b) appear in the ttHH AN (AN-2022/122). Remaining 12 = the hadronic
  V→qq / high-HT V+jets bins (XSDB-sourced by design, documented in the xsec
  DB refs) plus the 5 rare-top samples in the OPEN item below.

### OPEN (found during the cross-check — values NOT changed)
- `TTTT/TTWW/TTWH/TTWZ/TTTW` carry `xsec_ref: "ttHH AN Tab.9"` in
  `samples_2017UL.json` (copied verbatim into `samples_2018UL.json`), but AN
  Table 9 lists only ttHH/ttH/tt+jets/tt+bb/tt+4b/ttZ/ttZZ/ttZH, and the AN text
  contains no ttWW/tttt/multi-top entry at all → **reference is wrong or the
  values come from elsewhere (likely XSDB); needs a source fix.**
- `TTZToBB` = 861 fb (ref: AN Tab.16) vs **AN Tab.9 ttZ = 841 fb** — confirm
  which definition/table is intended before unblinding.

---

## [Unreleased] — 2026-07-26 (4): BTagCSV-2018 absence CONFIRMED (forensic scan run)

### Verified (lxplus run, log `script/das_ul18_scan_20260726_1657.log`)
- **BTagCSV does not exist in 2018 — settled, not a naming issue.** The v2
  forensic queries returned **0 hits** for `/BTagCSV/Run2018*/*` under **any
  tier** and **any dataset status** (`status=*`, i.e. INVALID/DEPRECATED
  included). `/BTag*/Run2018*/NANOAOD` returns only **BTagMu** (54 datasets) —
  the BTV muon-tagged calibration PD, not the FH b-tag jet stream.
- **PD inventory diff** (Run2018A vs Run2017C, UL NanoAODv9) — the 2018 primary
  dataset consolidation: **removed** BTagCSV, DoubleEG, FSQJet1, FSQJet2,
  HTMHT, HighPtLowerPhotons, HighPtPhoton30AndZ, SingleElectron, SinglePhoton;
  **added** EGamma. 2018 = BTagMu, Charmonium, DisplacedJet, DoubleMuon,
  DoubleMuonLowMass, EGamma, JetHT, MET, MuonEG, MuOnia, SingleMuon, Tau.
- **Consequence: JetHT alone covers the 2018 FH hadronic menu** (the 4J3T
  b-tag quad-jet paths sit in JetHT for 2018). Recorded in the generated
  config's comments. **Analyzer impact (tempTTHH, FUTURE):** the 2017
  BTagCSV↔JetHT orthogonality split + veto (`ttHHanalyzer_unified.cc`
  ~L295–360) must collapse to a JetHT-only OR for 2018, and 2018 path names
  differ (`…TriplePFBTagDeepCSV_4p5`); the existing TODO at L297 covers this.
- **Reproducibility:** rerunning `script/build_ul18_from_log.py` against the
  real lxplus log reproduced `config_ttHH2018UL.yaml` and
  `samples_2018UL.json` **byte-identical** to the earlier transcription-based
  run (diff empty) — the log is the sole input and the step is idempotent.

### Changed
- `script/build_ul18_from_log.py`: log auto-discovery now globs
  `script/**/das_ul18_scan_*.log` (the log lives directly in `script/`);
  BTagCSV comment block upgraded from inference to confirmed verdict.

---

## [Unreleased] — 2026-07-26 (3): das_ul18_scan.sh v2 — broad data forensics

### Added
- **`script/das_ul18_scan.sh` §[2b]** (user request): for NOT_FOUND primaries
  (BTagCSV), widen the search — BTagCSV under any tier and `status=*`
  (catches INVALID/DEPRECATED), `BTag*`/`*BTag*` name wildcards, and a full
  primary-dataset **inventory dump for Run2018A vs Run2017C** (UL NanoAODv9,
  `PD2018|`/`PD2017|` lines) so merged/renamed PDs are identifiable from the
  log. **unverified — rerun on lxplus.** GT36 data choice stays OPEN; decision
  policy per user: follow the samples used by the ttHH AN.

---

## [Unreleased] — 2026-07-26 (2): 2018UL campaign config generated from the DAS scan

### Added
- **`crabConfig/config_ttHH2018UL.yaml`** — 85 datasets (77 MC + 8 Data), generated
  by the new **`script/build_ul18_from_log.py`** from
  **`script/das_ul18_scan_20260726_1657.log`** (lxplus run, transcribed DS/RESULT
  lines). Selection rules recorded in the script header: standard campaign only
  (JMENano/PUFor*/FSUL18/BPH excluded); ext1/ext2 = separate keys (new vs UL17:
  `TTWW_ext1`); Data = non-GT36 with GT36 twins as comments (**OPEN**: confirm
  XPOG recommendation); **BTagCSV absent in 2018** (DAS NOT_FOUND — PD
  discontinued in the 2018 PD restructuring; FH b-tag HLT paths live in JetHT).
  `jobID: campaign_ttHH2018UL_fullNano_v1` (placeholder until first submission).
- `tempTTHH/data/samples_2018UL.json` written by the same script (see tempTTHH
  CHANGELOG). yaml↔json cross-checked programmatically (0 mismatches).
- Campaign-string sanity: `106X_upgrade2018_realistic_v16_L1v1` verified against
  the UL18 sample list in ttHH AN-2022/122 (identical GT string) — the `L1v1`
  suffix is the 2018 L1-menu tag inside the standard UL18 MC global tag.

---

## [Unreleased] — 2026-07-26: ttHH 2018UL expansion kickoff — DAS scan script

### Added
- **`script/das_ul18_scan.sh`** — for every sample in
  `crabConfig/config_ttHH2017UL.yaml`, queries DAS for the UL18 NanoAODv9
  equivalent (exact primary, then relaxed `_TuneCP5`-prefix fallback) and
  dumps `nevents`/`nfiles`/size per hit; `--ul17-nevents` re-dumps UL17
  summaries to cross-check `tempTTHH/data/samples_2017UL.json`. Output is
  machine-readable (`DS|`/`RESULT|` lines) and is the input for the future
  `config_ttHH2018UL_{Data,MC}.yaml`. The embedded 61-primary list was
  verified 1:1 against the YAML at generation time. **unverified — requires
  lxplus (dasgoclient + VOMS proxy); bash-syntax-checked only.**
- `01_STATUS.md`: 2018UL workstream + planned `expandedTtbarIdInjector.py`
  entry registered (plan canonical in the workspace-level 00_CONTEXT doc).

---

## [Unreleased] — 2026-07-15: A14 — beam-parallel energy overflow (background CRAB crash)

### Fixed
- **`_energy()` OverflowError on status-21 incoming partons** (first CRAB
  production attempt of the §2b background rebuild; QCD_HT 2017UL): beam-
  parallel legs carry pt≈0 and NanoAOD eta ~ O(1e4) → `math.cosh` overflow.
  Now returns the −999 sentinel for |eta| > 50 (+ defensive OverflowError
  catch). Standalone v1.9.1 applies the identical `SafeEnergy()` at all four
  energy sites — the C++ would have silently written `inf` instead of
  crashing, which the validator would have flagged as module/standalone
  mismatches. Both test harnesses gained the regression (E3 incoming legs at
  eta ±23000). See troubleshooting A14; MiniAOD comparison note added to the
  audit §8 (MiniAOD stored real `genPar->energy()` for these rows —
  unrecoverable from NanoAOD).

---

## [Unreleased] — 2026-07-11: standalone package renamed → TopCPVGenCategorizer

- The standalone reference implementation `SSBGenCategorizer` is renamed
  **`TopCPVGenCategorizer` (v1.9)**: class, files, directory, include guards,
  `TopCPVGenStatusBit` namespace, condor scripts, and all package docs.
  External MiniAOD names quoted as reference (`SSBAnalyzer`, `SSBTree`,
  `SSBCorrections`, `SSBCPVCalc`) are real upstream identifiers and stay
  verbatim (D-2026-07-01-rename-topcpv scope). Output format unchanged
  (`GenCatTree`, branch names, event-id keys) → `validate_topcpvcat.py` and
  existing GenCatTree outputs remain compatible. Living NtupleForge doc
  references updated; historical CHANGELOG entries left as written.

---

## [Unreleased] — 2026-07-10: background selection = MiniAOD §1.6; standalone v1.8 sync

### Changed (audit §2b resolution — module `topCPVCategorizer.py`)
- **`FillBackgroundSelection` rebuilt MiniAOD-faithful**: picked = every
  `statusFlags.isHardProcess` particle (the NanoAOD equivalent of MiniAOD's
  status-21–23 `TreePar`; hadronizer-independent, so the HERWIG branch collapses
  too) **+** status-1/2 leptons (|pdg| 11–16) whose **direct** mother is a
  top/Z/W/H — both scanned in ascending index, matching MiniAOD's ordering.
  Removed: the last-copy-boson base set, the recursive off-flavour descent, and
  the hard-process-τ rescue loop. Fixes both §2b risks: explicit-Z Z→ττ now
  −30 (was −60, τ double count) and boson-less ME ℓℓ now ±22/26 (was 0).
  `_FROM_HARD_PROCESS` constant removed (no longer used); `_IS_HARD_PROCESS`
  (bit 7) added.

### Standalone `SSBGenCategorizer` updated to v1.8 (synchronized)
- v1.7 (pre-2026-06-28-restoration) was uploaded and three-way compared
  (standalone ↔ module ↔ MiniAOD origin). Divergences found & fixed in the
  standalone, adopting the module's MiniAOD-faithful behaviour: ① direct
  channel over the **full** selected list (was: slots 8–11 only + background
  forced to 0); ② `Channel_Idx_Final` via the GenPart daughter-map walk with
  GenPar append and <14/>14 sign rules (was: `GenDressedLepton` count —
  branches no longer read); ③ background selection rebuilt as above (was:
  one-level boson daughters + τ rescue); ④ `Channel_Idx_Expanded` (+ Loop
  summary counter) added.

### Added (cross-validation without ROOT)
- `script/test_reader_lifecycle.py` extended to 4 synthetic events (2× ttbar
  signal incl. `Channel_Jets` 2112/1212 asserts, explicit-Z Z→ττ, boson-less
  ME μμ). The standalone ships `validation/crosscheck/` (stub-ROOT headers +
  harness): both implementations produce **identical** derived values on the
  same events (compiled with g++ 13, `-Wall -Wextra` clean, all asserts pass).

### Pending on lxplus
- Rebuild the standalone v1.8 with real ROOT; rerun `validate_topcpvcat.py`
  (event-matched, both codebases now MiniAOD-faithful **and** mutually
  identical); one-time `TTree::Draw` sanity on the DY production (§2b).

---

## [Unreleased] — 2026-07-02 (3): re-audit vs MiniAOD + validator hardening

### Fixed
- **`script/validate_topcpvcat.py` latent crash + dead comparisons** (found in
  the 2026-07-02 re-audit, before first lxplus use): the branch-presence guard
  used `GetBranch(x) is None`, but PyROOT returns a **null TBranch object,
  never Python `None`**, so the guard could not fire and the first missing
  passthrough name would have crashed `getattr`; several passthrough names did
  not exist on the NanoAOD side at all (`GenJet_energy`,
  `GenJet_{Parton,Hadron}Flavour` capitalization, `PSWeight_n`), making those
  comparisons silent no-ops. Now: passthrough is a `(GenCatTree name, Events
  name)` pair list with real NanoAOD names, presence is checked on **both**
  trees with truthiness and a one-time WARNING per skipped pair, `UChar_t`
  elements are coerced (`bytes/str → int`) before comparison, and unmatched
  event counts are reported in both directions.

### Documented (audit addendum, `TopCPV/02_faithfulness_vs_miniaod.md`)
- **§2b (new): background selection construction diverges from MiniAOD** —
  module/standalone pick last-copy bosons + recursive descendants + a τ-only
  rescue, vs MiniAOD's whole-hard-process base set; two concrete risks
  (explicit-Z→ττ double count → −60 vs −30; boson-less ME ℓℓ → 0 instead of
  ±22/26) with `TTree::Draw` discriminators to run on the fresh DY output.
  Module ≡ standalone, so the validator cannot see this — it is vs MiniAOD only.
- **§8 amended:** slots 0/1 and t/t̄ mother fields necessarily differ (NanoAOD
  prunes beam protons; −1/placeholder vs MiniAOD's real proton rows and
  `Mom=(0,1), nMo=2`). Channel-neutral, unrecoverable.
- **§5 strengthened:** τ→ℓ walk verified statement-by-statement against origin
  §2.2 (map order, descendant order, push-before-check, ν-triggered removal,
  sign rules) — order-exact.
- **§3 note:** background `GenTop` = −999 scalars vs MiniAOD's empty vectors
  (cosmetic).

---

## [Unreleased] — 2026-07-02 (2): fix A13 — pre-register branch readers (2nd CRAB crash)

### Fixed
- **Second MC CRAB production crash** (`config_CPV2017UL_MC`, 2026-07-02): every
  MC job died on the first event with `ReferenceError: attempt to access a
  null-pointer` on an in-bounds `mom[i]` (DYJets) or a segfault in
  `TObjectArrayReader::At` (QCD). Root cause proved from
  `treeReaderArrayTools.py` @ CMSSW_14_2_X: lazily creating a reader mid-loop
  triggers `_remakeAllReaders` (new TTreeReader, all readers recreated),
  silently invalidating every reader object bound earlier — our back-to-back
  local binds in `analyze()` produced 7 remakes before the first element read.
  **Fix:** `beginFile` now pre-registers every reader
  (`GEN_ARRAY_BRANCHES`/`GEN_COUNTER_BRANCHES` via
  `inputTree.arrayReader/valueReader`) while the TTreeReader is clean → the
  loop is remake-free and bound locals stay valid; plus fail-fast on partial
  gen inputs and a self-healing `_read_arrays` batch binder (re-binds once +
  warns if a future unregistered read sneaks in). Incident:
  `05_troubleshooting.md` **A13**; rule: `06_nanoaod_branch_access.md`
  Pitfall 4; decision: D-2026-07-02-prewarm-readers.
- **Validation:** reproduced and fixed against the *actual* CMSSW_14_2_X
  framework sources (`treeReaderArrayTools`/`datamodel`/`eventloop`) over a
  cppyy-lifetime mock ROOT in the dev container: old pattern reproduces the
  exact CRAB error; fixed module runs the real `eventLoop` with zero reader
  rebuilds (46 branches, correct signal quantities; data no-op intact).
  **Still unverified against real ROOT — lxplus `-N 10` + `validate_topcpvcat.py`
  before resubmission.**

---

## [Unreleased] — 2026-07-02: CPV configs split per tier (_Data / _MC)

### Changed
- **`crabConfig/config_CPV<era>UL.yaml` (combined) → `config_CPV<era>_Data.yaml`
  + `config_CPV<era>_MC.yaml`** for all four eras; combined files removed.
  Data configs: `modules/noop.py` + `branches/branch_CPV_Run2_Data.txt`;
  MC configs: `modules/topCPVCategorizer.py` + `branches/branch_CPV_Run2_MC.txt`.
  Split by DAS tier suffix; dataset counts preserved (30+73 / 15+75 / 29+73 /
  12+74). Closes the per-tier OPEN item and the config half of incident A11
  (`03_DECISIONS.md` → D-2026-07-02-per-tier-configs). YAML-parse verified
  in-container; **unverified on CRAB** — submit one small data task first.

---

## [Unreleased] — 2026-07-01: TopCPV rename, CRAB crash fixes, docs restructure

### Changed (rename — no logic change by itself)
- **Module renamed** `modules/ssbGenCategorizer.py` → **`modules/topCPVCategorizer.py`**;
  class `SSBGenCategorizer` → **`TopCPVCategorizer`**; **branch prefix**
  `SSBGenCat_` → **`TopCPVCat_`**; debug env `SSBGENCAT_DEBUG` → **`TOPCPVCAT_DEBUG`**;
  validator `script/validate_ssbgencat.py` → **`script/validate_topcpvcat.py`**;
  the standalone C++ shorthand "SSBGen" → "TopCPV" in prose. The **external
  MiniAOD class name `SSBAnalyzer` is intentionally preserved** everywhere (it
  is the reference of truth, not our code). `config_CPV*` `analysis_module`
  entries updated. Rename safety per `00_PROMPT.md` §7: `crab/submit_crab.py`
  ships every sibling `.py` name-agnostically and derives `-I` from the config
  basename, and a repo-wide grep confirms zero stale `SSBGen*`/`ssb_gencat`
  tokens — **a real CRAB job must still confirm** (no CRAB in the dev container).
  See `03_DECISIONS.md` → D-2026-07-01-rename-topcpv.
  ⚠️ **Old and new ntuples differ in branch names** (`SSBGenCat_*` vs
  `TopCPVCat_*`) — downstream readers must switch prefixes.
- **Docs restructured into per-workstream subdirectories**: `docs/ssb_gencat/` →
  **`docs/TopCPV/`**; `02_physics.md` → **`ttHH/01_physics.md`**;
  `09_legacy_ttbar_pipeline.md` → **`ttHH/02_legacy_ttbar_pipeline.md`**;
  `docs/legacy/` → **`docs/ttHH/legacy/`**; new local index `ttHH/README.md`.
  Root docs renumbered contiguously (§3.1): `03_CHANGELOG`→`02_CHANGELOG`,
  `04_DECISIONS`→`03_DECISIONS`, `05_architecture`→`04_architecture`,
  `06_troubleshooting`→`05_troubleshooting`,
  `07_nanoaod_branch_access`→`06_nanoaod_branch_access`,
  `08_DeveloperGuideline`→`07_DeveloperGuideline`. All cross-links rewritten;
  link check passed. `00_PROMPT.md` stays the **single** prompt doc covering
  both workstreams. Top-level `README.md` and `docs/README.md` rewritten in
  Korean. See D-2026-07-01-docs-topcpv-tthh-split.

### Fixed (first CPV CRAB production crashes, 2026-07-01)
- **MC segfault** (`TTZToQQ`, every job): `safe_len`'s out-of-bounds indexing
  probe on a raw `TTreeReaderArray` (`GenPart_pdgId`) hit ROOT undefined
  behaviour (`TObjectArrayReader::At` → `TBranchProxy::Setup` → SIGSEGV).
  **Lengths now come from the count branch** via new helpers
  `count(event, "X")` / `opt_count(event, "X")` in
  `modules/nanoaod_branch_access.py`; `safe_len` was de-fanged (no probe;
  fails fast) and deprecated for collections. The old "nGenPart is unreliable"
  doctrine was a mis-attribution of the A4 zombie-branch bug and is corrected
  in `06_nanoaod_branch_access.md`. Incident: `05_troubleshooting.md` **A12**;
  decision: D-2026-07-01-count-branch-length.
- **Data crash** (`SingleElectron_Run2017B`, every job): the MC-only guard
  `inputTree.GetBranch("GenPart_pt") is None` did not fire through the
  nanoAOD-tools wrapper, so data reached `analyze` and died on
  `Unknown branch GenPart_pdgId`. `beginFile` now detects presence via
  `GetListOfBranches()` (the A5 pattern) and a GenPart-less file makes the
  module a logged **no-op** instead of crashing. Data/MC config split remains
  OPEN (`01_STATUS.md`). Incident: `05_troubleshooting.md` **A11**.
- Both fixes are **logic-tested in-container only** (stub harness: data no-op;
  synthetic ttbar event writes 46 branches, `GenPar_Count=12`,
  `GenBJet_Count=1`). **Unverified on real NanoAOD** — validate on lxplus
  (`-N 10` local run, then `validate_topcpvcat.py`) before resubmitting.

### Added
- `count()` / `opt_count()` in `modules/nanoaod_branch_access.py` (count-branch
  collection lengths); Pitfall 3 (branch-presence detection) documented in
  `06_nanoaod_branch_access.md`.
- `docs/ttHH/README.md` — local index for the ttHH workstream docs.

---

## [Unreleased] — CPV gen-level categorizer (MiniAOD-faithful)

Added the NanoAOD module + CRAB configs to produce the top-CP-violation (CPV)
gen-categorization ntuples. **Reference of truth = the MiniAOD `SSBAnalyzer`**
(not the intermediate standalone TopCPV); the audit's restorations are applied to
**both** the module and the standalone TopCPV C++ (see `03_DECISIONS.md` →
D-2026-06-28-miniaod-reference).

### Added
- **`modules/topCPVCategorizer.py`** — reproduces the MiniAOD `SSBAnalyzer`
  gen-level categorization from the NanoAOD `GenPart` collection. Emits **derived
  branches only**, prefix `TopCPVCat_` (12-slot family tree, `Channel_*` codes,
  top/antitop kinematics, ghost-B GenBJet/GenBHad); raw gen collections come from
  the full-NanoAOD passthrough. **MiniAOD-faithful channel:** `Channel_Idx` summed
  over the full selected list (§2.1, recovers background channels); `Channel_Idx_Final`
  resolves τ→ℓ by walking the GenPart daughter map (§2.2) and **appends the τ
  daughter to GenPar** (so `GenPar_Count` grows for leptonic-τ events). Additive
  `Channel_Idx_Expanded` diagnostic + end-of-job unclassifiable counter. NanoAOD
  bonuses kept (`Channel_Visible_Tau`, `Channel_Tau_Lepton`); last-copy top, explicit
  W⁻ daughters, `GenBJet` via `GenJet_hadronFlavour` kept (audit §3/§4/§6). MC only.
  Uses `to_int`/`safe_len` from the re-instated `modules/nanoaod_branch_access.py`
  (mandatory; see `06_nanoaod_branch_access.md`). Logic-tested in-container (all-hadronic /
  semileptonic-τ / background); byte-identity vs. TopCPV to confirm on lxplus.
- **`crabConfig/config_CPV{2016preVFPUL,2016postVFPUL,2017UL,2018UL}.yaml`** —
  per-era CRAB configs (named to stay distinct from the ttHH `config_ttHH*`
  lists), datasets transcribed from the user-provided UL lists (NanoAODv9:
  103/90/102/86 datasets). **Only `datasets:` is final; all `common:` fields are
  placeholders.** The loader normalized/flagged several transcription artifacts
  (2 missing leading `/`, a `104X` campaign typo, two `QCD_Pt_3200toInf` pilot
  duplicates emitted as commented `# [DUP]` lines, one extra-field/`/`-missing DY
  line) — all to verify on DAS (`01_STATUS.md`).
- **`branches/branch_CPV_Run2_{Data,MC}.txt`** — the CPV output branch lists
  (drop IsoTrack/LowPtElectron/SoftActivityJet/SubJet/Tau/boostedTau/HLT then
  re-keep specific HLT; MC also drops GenIsolatedPhoton/GenVisTau/HTXS/
  SubGenJetAK8). Note: the MC list drops `GenVisTau*` from the *output*, which the
  module reads from the *input* — keep `branch_file` as an output selection.
- **`script/validate_topcpvcat.py`** — lxplus equivalence checker (matches events
  by run/lumi/event; ints exact, floats within `--ftol`).
- **`docs/03_DECISIONS.md`** (decision log) and **`docs/01_STATUS.md`** (status) — both
  were missing vs. the documentation guideline; created here. **`docs/TopCPV/`**
  gained a `README.md` index and a `01_module.md` module reference.
- **`docs/00_PROMPT.md`** — AI/contributor working agreement (instance of the
  documentation contract §8): persona, reference of truth (MiniAOD), environment
  limits (no ROOT/compile here), and the validation + change-notification duties.

### Changed (documentation guideline v2 adoption)
- **Docs numbered in reading order** (`NN_name.md`), per the contract §3.1:
  `01_STATUS` → `ttHH/01_physics` → `02_CHANGELOG` → `03_DECISIONS` → `04_architecture`
  → `05_troubleshooting` → `06_nanoaod_branch_access` → `07_DeveloperGuideline` →
  `ttHH/02_legacy_ttbar_pipeline`; `TopCPV/` given local numbering
  (`01_module` / `02_faithfulness_vs_miniaod` / `03_miniaod_origin`). `README.md`
  stays unnumbered and lists the order. All cross-links rewritten.
- **Branch lists renamed** `branchlist_Run2_{Data,MC}.txt` →
  **`branch_CPV_Run2_{Data,MC}.txt`** (CPV-scoped names); `config_CPV*` `branch_file`
  references updated.
- **PyROOT helper renamed** `modules/_nanoaod_compat.py` →
  **`modules/nanoaod_branch_access.py`** (clearer role); the `topCPVCategorizer`
  import and the doc (now `06_nanoaod_branch_access.md`) updated. The archived copy
  under `docs/ttHH/legacy/code/` keeps its original name for historical accuracy.
- **`topCPVCategorizer` guarded validation logging**: env `TOPCPVCAT_DEBUG=N` prints
  per-event derived quantities for the first N events, then stays silent (never logs
  unboundedly in the event loop). Off by default.

### Fixed
- **CRAB import failure of the renamed helper** (first `config_CPV2017UL` submission
  failed fast with *"attempted relative import with no known parent package"*). Two
  coupled causes: (1) `crab/submit_crab.py` auto-included helpers only via
  `glob("modules/_*.py")`, so dropping the leading underscore in the rename removed
  `nanoaod_branch_access.py` from the sandbox; (2) the module's relative-import
  fallback cannot work in CRAB's flat (top-level) import context. Fix: `submit_crab.py`
  now ships **every** sibling `.py` (except the analysis module and dunders), and
  `topCPVCategorizer.py` puts its own dir on `sys.path` via `__file__` before importing.
  See `05_troubleshooting.md` A0. Follow-up: generalized this class of bug into
  **Rule 7 (rename/move safety)** in `07_DeveloperGuideline.md`, `00_PROMPT.md` §7, and
  the documentation contract §8.3 (flag hidden glob/hardcoded-path file couplings).

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
  - `07_DeveloperGuideline.md` — contributor rules (read all docs first; log every change
    and every problem; which doc each record goes in).
  - `04_architecture.md` — framework internals **plus a copy-followable how-to
    for writing a module that adds branches / applies cuts** (§6).
  - `ttHH/01_physics.md` — physics basis (analysis target, stitching, five categories,
    `genTtbarId` encoding, why five not seven), split out of the legacy doc.
  - `05_troubleshooting.md` — consolidated incident log (every bug: symptom,
    error signature, root cause, fix, validation) + how validation works.
  - `ttHH/02_legacy_ttbar_pipeline.md` — implementation record of the retired
    categorizer (physics delegated to `ttHH/01_physics.md`).
  - `06_nanoaod_branch_access.md` — why the PyROOT compat shim existed.
  - `02_CHANGELOG.md` — this file.
- `docs/ttHH/legacy/code/` — verbatim archive of the categorization pipeline
  (categorizer module, compat shim, slimming branch list, branch inventories,
  original CRAB config).

### Removed (from the live tree)
- `modules/ttbarCategorizer.py` (the module that used to write the twelve
  `ttCat_*` / `ttCatXval_*` categorization branches) and its
  `modules/_nanoaod_compat.py` helper → moved to `docs/ttHH/legacy/code/`. The
  categorization itself now happens in the main analyzer; the full
  implementation record is kept in `ttHH/02_legacy_ttbar_pipeline.md`.
- `branches/branch_ttHHto4b_hadronic_2017UL.txt`, `branches/branch_2017UL/`
  → archived under `docs/ttHH/legacy/code/`.
- `scripts/inspect_weights.py`, `scripts/compare_branches.py`,
  `scripts/dump_branches.py`, `scripts/test_ttbar_categorizer.py` (stale,
  8-category) → **deleted**.
- `scripts/validate_events.py` → archived to `docs/ttHH/legacy/code/tools/`
  (skim-efficiency QA; the current passthrough has no skim to measure). Its
  documentation moved to `ttHH/02_legacy_ttbar_pipeline.md` §8.
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
