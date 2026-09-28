# 12 통합 워크플로우와 2018·2024 최단 경로: 생산은 지금 검증된 경로로, MiniAOD 산출물의 교차 검증은 병행

> **목적**: 2018 과 2024 의 stack plot 을 trigger SF 와 b-tag norm reweight 를 적용한 상태로 가장 짧은 경로로 보기 위한 실행 계획.
> NtupleForge 가 "slimmed NanoAOD 생산 / MiniAOD 에서 tt+nb 사전 만들기 / MiniAOD 에서 NanoAOD 유도" 를 한 명령 체계로 하는 모양,
> 교차 검증 표, 그리고 실수를 일찍 잡기 위한 중간 로그 규약을 한 곳에 적는다.
> **대상 독자**: 이 계획을 실행하는 사용자(lxplus, KNU, 맥)와 코드를 쓰는 AI 세션.
> **상태**: 2026-09-27 작성, **PROPOSED**. 09-28 갱신: V1 **DONE**(ALL SAMPLES PASS, 원장 V45); P1 [7c] 의 v1 측정은 쓰지 않고 `size_options.py` v2 로 34 개를 다시 잰다(원장 V46, RUNBOOK §11). 방향 두 가지는 사용자 제안(09-27): (1) 검증이 생산을 막지 않는다, analyzer 는 기존 방식의
> ntuple(NanoAOD + categorizer 산출물)로 돌리고 MiniAOD 산출물은 병행해 교차 검증한다; (2) NtupleForge 한 도구가 세 역할을 직관적으로 한다.
> 세부와 순서는 AI 제안이고 §7 의 결정을 받으면 DECIDED 로 옮긴다.
> **관련**: [11](11_unified_forge_plan.md)(도구 통합 설계, Phase 0~2 와 완료 판정 (i)(ii)), 명령은 워크스페이스 `RUNBOOK_lxplus_2026-09-16.md` §11,
> SF 유도 절차의 원형은 tempTTHH `docs/RUNBOOK_2017_SF_rederive.md`, 2018 patch 수치는 TTHHGenCategoryTools `docs/06_validation_results.md`,
> 원장은 [10](10_validation_ledger.md).

## 결론 먼저

- **analyzer 는 2017 에서 쓴 경로로 먼저 돈다**: 중앙 NanoAODv15 를 NtupleForge 로 slim 한 ntuple 에, MiniAOD 에서 만든 tt+nb patch 를
  (run, lumi, event) 로 실행 시 붙인다. MiniAOD 산출물(sidecar patch, enriched NanoAOD)과 NanoAOD `genTtbarId`, CPV 분류 사이의 교차 검증은
  병행하고, 그 결과는 산출물을 **쓰는** 단계만 막는다(§4 표의 "막는 것" 열). 생산 자체를 막는 검증은 NtupleForge 의 로컬 점검과 job 안의
  closure 뿐이다.
- **가장 큰 단축은 2018UL 이다.** 두 config 가 3,743 job(MC 2,277 + Data 1,466 files)으로 2024 의 26,947 job(19,136 + 7,811)의 1/7 이고
  (`script/drafts/review_das_ttHH_2018UL_v15_20260923_0853.md`, `review_das_ttHH_2024_v15_20260923_0851.md`), 출력 추정은 3.2~4.8 TB 다
  (RUNBOOK §10 [7b], 원장 V44). [7c] 가 허락하면 2018UL 은 새 코드 없이 지금의 noop 경로(파일럿 V43 통과)로 먼저 낸다. 그러면 모든 event 가
  남으므로 analyzer 의 prescan 도 지금 코드 그대로 쓴다. skim 이 필요한 2024 용 코드(§2.3)는 2018 이 도는 동안 만든다.
- **2018 plot 의 critical path 는 ntuple 이 아니라 analyzer 다.** v15 스키마(eventBuffer 재생성, `Jet_jetId`/`Jet_puId` 재계산), 2018 배관
  (tempTTHH STATUS OPEN 6 의 P0', 07-26 부터 미해결), 2018A 트리거 결정(D-2026-09-18-2018A-trigger), 그리고 07-29 의 P0 수정 7 건이
  **한 번도 빌드되지 않았다**(tempTTHH `docs/STATUS.md` "❌ make 미수행"). 그래서 오늘 KNU 에서 빌드부터 한다(§3 A0).
- **2024 의 critical path 는 결정이다**: 트리거 집합, b-tagger 와 SF 방식, era 보정. `ttHH/03_run3_plan.md` §2 의 "기억" 행은 twiki 원문
  확인 전에는 코드에 넣지 않는다는 규칙이 있다.
- **MiniAOD 쪽 교차 검증 하나(V1)는 09-28 에 끝났다**: 2018 patch 를 중앙 v15 NanoAOD 여섯 샘플 전량과 맞춰 `ALL SAMPLES PASS`.
  extend 와 v15 의 event 수가 같은 네 샘플은 patch 행 수와 정확히 같고, v15 가 적은 둘은 기대값대로다(TTHH `docs/06` 끝 절, 원장 V45).
  그래서 S1 의 tt+nb 분할은 이 patch 로 간다.
- **이번 조사에서 새로 확인한 것 (§6)**: 2018 v15 표준 NanoAOD 는 MiniAOD 보다 `TTbar_SemiLep` 이 18,849,000 event(3.9 %), `TTbb_Hadronic` 이
  103,000 event(1.3 %) 적다. 2017 에서 확인한 "v15 = MiniAOD 100 %" 는 2018 에 그대로 옮길 수 없고, patch coverage 판정의 모집단은 v15 여야 한다.

## 1. 용어와 데이터 흐름

이 문서에서 **TTHH categorizer** 는 ttbar + heavy-flavour 분류 전체를 뜻한다: 공식 `genTtbarId` 와 그 위의 tt+nb 확장.

| 무엇 | 계산 | 입력 → 산출물 | 지금 |
|---|---|---|---|
| `genTtbarId` (공식) | `100·nBJetsFromTop + 1000·nBJetsFromW + 10000·nCJetsFromW` + 추가 jet 코드(0, 41~45, 51~55) | MiniAOD 의 `GenTtbarCategorizer` → NanoAOD branch | 모든 v15 MC 에 있음. 인코딩은 CMSSW `TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc` 에서 확인 |
| 확장 id `genTtbarIdExpanded` | 추가 b-jet 3 개 → 61/62, 4 개 이상 → 71/72, 앞자리 보존 (TTHHGenCategoryTools `docs/02_physics.md`) | MiniAOD 의 `ExtendedTtbarIdProducer` → (a) sidecar `ttbarIDExtend.root` → patch `ttnb_<KEY>.root`(tree `TtNb`), (b) enriched NanoAOD 의 컬럼 | patch: 2017 7 편(사용 중), 2018 7 편(v9 기준 검증 6/7), 2024 없음. enriched: 2017 gate 1~5 CLOSED |
| analyzer 의 조회 | patch 행을 (run, lumi, event) 로 찾고, 찾으면 확장값, 못 찾으면 `genTtbarId` 그대로 | ntuple + patch → 실행 시 값 (`tempTTHH/include/ExpandedTtbarId.h`) | 2017 에서 쓰는 현행 계약. patch 주입 모듈(injector)은 DEFERRED |
| CPV 분류 `TopCPVCat_*` | 채널(`Channel_Idx`, lepton 수), W→qq 쿼크 코드(`Channel_Jets`), gen b-jet | NanoAOD `GenPart` → NanoAOD 모듈 branch (`modules/topCPVCategorizer.py`) | 별도 workstream. 여기서는 같은 gen 정보를 다른 알고리즘으로 보는 **독립 증인** |

```
central MiniAODv2 --(central NANO)--> central NanoAODv15 --[slim]--> forgedNtuple.root (T3_KR_KNU) --> analyzer (KNU)
      |                                                                                            ^
      +--[categorize: sidecar]--> ttbarIDExtend.root --[validate: match to NanoAOD]--> ttnb_<KEY>.root --+  key (run, lumi, event)
      |
      +--[derive: enriched]--> NanoAODv15 + genTtbarIdExpanded (5 samples with no central v15) --------> analyzer
```

## 2. NtupleForge: 명령 하나, 레시피 셋

### 2.1 레시피

사용자가 고르는 것은 **레시피 이름**이고 런타임(job_type)은 거기서 정해진다. [11](11_unified_forge_plan.md) §2 의 job_type 표를 사용자 쪽 이름으로
다시 쓴 것이다.

| recipe | job_type | 입력 → 출력 | YAML 에 쓰는 것 | 지금 | 새로 필요한 것 |
|---|---|---|---|---|---|
| `slim` | postproc | 중앙 NanoAOD → `forgedNtuple.root` (branch 목록, 선택적 event skim, audit) | `branch_file`, (새) `skim`, (새) `audit` | noop 경로 동작 (2024 파일럿 158/158, V43) | skim 과 audit (§2.3). 2024 용 |
| `categorize` | cmsrun (sidecar) | MiniAOD → `ttbarIDExtend.root` (event 키 + 확장 id) | `pset`, `cmssw_release`, 출력 파일 이름 | TTHHGenCategoryTools 자체 제출기로 2017·2018 완료 | 같은 YAML·preflight·runlog 로 (Phase 0). 2024 는 15_0_X |
| `derive` | cmsrun (nano) | MiniAOD → NanoAODv15 + 확장 id 3 컬럼 | `pset`(중앙 cmsDriver 원문 + customise), `cmssw_release` | 2017 gate 1~5 CLOSED (TTHH `docs/11_enriched_nanoaod.md`) | Phase 0 제출 글루 + 2018 레시피 |
| `validate` | standalone (CERN condor) | extend ↔ NanoAOD 매칭 → patch 추출 | 명령행 인자 | TTHHGenCategoryTools `Validation/` 동작 | 이번 변경: `2018v15` filelist, v15 기준값 |

### 2.2 사용자가 보는 것

```yaml
common:
  recipe: slim          # slim | categorize | derive   (absent = slim, so today's four configs keep working)
  skim: 6j25            # slim only: none | 6jcount | 6j20 | 6j25 | 6j30 | 6j20ht400 (the names size_options.py measured)
  audit: true           # slim only: default true
  branch_file: "branches/branch_hadronic_2024_v15_MC.txt"
```

명령은 레시피와 무관하게 지금과 같다: `python3 crab/submit_crab.py -c <yaml> --preflight`, 제출, `--report`, `--status`, `--resubmit`, `--kill`.
preflight 의 첫 줄에 `recipe: slim (postproc; skim 6j25 = <식>; audit on)` 처럼 **무엇을 할지**를 문장으로 찍고, `cmsrun` 레시피는
`cmssw_release` 와 지금 셸의 `$CMSSW_VERSION` 이 다르면 FAIL 한다(10_6_X cfg 를 14_2_X 셸에서 내는 사고 방지).

### 2.3 `slim` 의 event skim 과 audit (새 코드, 2024 용)

**왜 python 모듈로 skim 하지 않나.** NanoAODTools 는 모듈이 하나라도 있으면 모든 입력 event 에 python 루프를 돌고, 통과한 event 마다
`readAllBranches()` 로 입력 branch 전부를 읽어 `CloneTree(0)` 로 만든 tree 를 채운 뒤, 끝에 branch 목록으로 다시 복사한다
(CMSSW 14_2_X `PhysicsTools/NanoAODTools/python/postprocessing/framework/output.py` `FullOutput`, `postprocessor.py`). 모듈 없이 `cut` 을 주면
선택은 C++ `TTree::Draw` 의 entry list 로 끝나고 복사도 C++ 이다(같은 파일의 preSkim + fullClone 경로). 그래서 skim 은 `cut` 경로로 하고,
audit 은 C++(RDataFrame)로 따로 계산한다.

**제안 구현.**
- `run_postproc.py` 에 `--skim <이름>`. 이름 → 식의 표는 한 곳에만 둔다(`size_options.py` 의 다섯 식과 같은 문자열, 예:
  `6j25` = `Sum$(Jet_pt>25 && abs(Jet_eta)<2.5)>=6`). 지금의 `--cut` 은 계속 검증 전용이다(docstring 의 규칙 유지).
- **audit (입력 파일마다, 선택 전의 모든 event)**: RDataFrame 한 번에 `n_in`, Σ`genWeight`, Σ`genWeight`², 음수 weight 수,
  `genTtbarId % 100` 코드별 Σweight 와 개수(0~99 와 음수), 같은 skim 을 **RVec 식으로 다시 쓴** 통과 수, 그리고 stitching 7 샘플만
  코드 53~55 event 의 `(run, luminosityBlock, event, genTtbarId, genWeight)` 표. tt+nb 는 전부 53~55 에서 나오므로(TTHH `docs/02_physics.md`)
  이 표와 patch 를 맞추면 확장 bin(61/62/71/72)의 Σweight 를 **나중에** 정확히 계산할 수 있다. 생산이 patch 를 기다릴 필요가 없다.
- 결과는 haddnano 뒤 `forgedNtuple.root` 에 덧붙인다: TTree `ForgeAudit`(입력 파일당 1 행), TTree `ForgeTTbbKeys`, TObjString `ForgeProvenance`
  (git 커밋, 옵션, skim 식). haddnano 는 TTree, TH1, TObjString, THnSparse 만 합치고 나머지는 `Cannot handle` 을 찍고 버린다
  (CMSSW 14_2_X `PhysicsTools/NanoAOD/scripts/haddnano.py`) → 나중에 누가 ntuple 을 합쳐도 audit 이 남도록 이 셋만 쓴다.
- **job 안의 closure** (하나라도 어긋나면 non-zero exit. CRAB 은 그 job 을 failed 로 표시하고 재시도 대상에 넣는다; `crab_script.py` 는 이미 payload 의 exit code 를 그대로 돌려준다):
  C1 출력 `Events` entries == Σ 통과 수(RVec) (TTreeFormula 식과 RVec 식이 같은 event 를 고르는지);
  C2 Σ `n_in` == Σ 입력 `Events` entries (정수, 읽기 완결성: TTHH T-23 ⑧ 유형의 조용한 읽기 실패). MC 는 여기에 Σ `Runs.genEventCount` 도
  같아야 한다: dataset 합으로는 2017 에서 확인됐고(tempTTHH `docs/RUNBOOK_2017_SF_rederive.md` §2-1 의 표), 파일 단위는 P5 에서 확인한 뒤 FATAL 로;
  C3 MC: 파일마다 Σ`genWeight` 와 `Runs.genEventSumw` 의 상대차. `genWeight` 가 Float_t 라 비트 일치는 아니므로 P5 에서 실제 크기를 재고
  기준을 정한 뒤 FATAL 로 올린다(그 전에는 WARN 줄).
- 비용: audit 은 branch 몇 개(`genWeight`, `genTtbarId`, 키 셋, skim 에 쓰는 `nJet`·`Jet_pt`·`Jet_eta`)만 읽는다. skim 은 C++ 이다.
  파일럿(P6)에서 job 시간과 통과율을 잰다.
- prescan 과의 관계: skim 한 ntuple 에서는 analyzer 의 `--mode prescan`(모든 event 필요)을 쓸 수 없다. 그래서 tempTTHH 쪽에 `ForgeAudit` +
  `ForgeTTbbKeys` + patch 로 `prescan_summary.json` 과 같은 형식을 만드는 작은 스크립트가 필요하다(A5). skim 하지 않은 ntuple 에서는
  두 방법의 결과가 같아야 한다(X5).

### 2.4 `categorize` 와 `derive`

[11](11_unified_forge_plan.md) §5 Phase 0 그대로다. 순서만 이 계획에 맞춘다: 2018 `derive` 레시피(중앙 cmsDriver 원문 이식) → `TT4b` →
`TTHHto4b` → `TTZHTo4b`·`TTZZTo4b`·`tHW` (01_STATUS A.4). `TT4b` 가 먼저인 이유는 stitching(tt+nb 를 소유하는 dedicated sample)과
X12(patch 경로 ≡ enriched 경로)를 한 번에 풀기 때문이다. 2024 는 모든 샘플이 중앙에 있으므로 `derive` 는 필요 없고 `categorize`(15_0_X)만
필요하다(`ttHH/03_run3_plan.md` 결론 2).

## 3. 최단 경로: 네 트랙

상태: **READY** 지금 실행 가능 · **CODE** 코드가 먼저 · **DECIDE** 사용자 결정이 먼저 · **WAITS** 앞 단계 뒤.

### 트랙 P: NtupleForge 생산

| ID | 무엇 | 어디 | 상태 | 끝나면 |
|---|---|---|---|---|
| P1 | [7c] 용량 측정(34 샘플, skim 5 안 × branch 목록 4 안) | lxplus 컨테이너 | **다시** (09-28 v1 은 2018 의 7/11 에서 segfault, 한 행은 읽기 오류와 함께 기록; v2 로 34 개 전부, RUNBOOK §11) | P2 |
| P2 | config 마다 (branch 목록, event 선택) 선택. 합계는 한도 안에서 1 TB 이상 여유(enriched 는 Run 2 네 era-half 전체로 약 0.47 TB 추정, analyzer 산출물, 파일럿 48.6 GB) | 사용자 | DECIDE | P3, P4 |
| P3 | **2018UL 제출** (skim 없음이 가능할 때): 고른 목록을 `branches/` 로 → `check_branchlist.py` → 로컬 500 event 점검 2 → preflight 2 → [8] 두 config | lxplus | P2 뒤 READY | S1 |
| P4 | skim + audit 코드(§2.3), `submit_crab.py` 의 `recipe`/`skim`/`audit`, mock test | AI | CODE (P2 뒤 바로) | P5 |
| P5 | 로컬 점검: era·tier 4 개 × 파일 1 개 전부, closure C1~C3, X5·X7 | lxplus 컨테이너 | WAITS P4 | P6 |
| P6 | skim 파일럿(2024 ttbar 하나 + `JetMET0_Run2024H`), KNU 에서 audit 합산 | lxplus, KNU | WAITS P5 | P7 |
| P7 | 2024 전체 두 config (2018UL 을 skim 하기로 했으면 그것도) | lxplus | WAITS P6 | S5 |
| P8 | 캠페인 audit 집계: dataset 마다 Σ`n_in` == DAS nevents, 출력 파일마다 audit 행, dataset 별 크기 | KNU | WAITS P3/P7 | S1/S5 |

### 트랙 A: analyzer (tempTTHH)

| ID | 무엇 | 어디 | 상태 | 끝나면 |
|---|---|---|---|---|
| A0 | 빌드(`make`) + 단위 테스트 3 개 + 2017 `btagtrig` preflight(읽기 전용). 07-29 코드의 첫 빌드 | KNU | **READY** | A1 |
| A1 | v15 스키마: `eventBuffer.h` 를 v15 파일에서 재생성(2018·2024 MC/Data 의 합집합), 08 §3.1 rename, §3.4 jet ID 재계산과 PU ID(`Jet_puIdDisc` WP), 타입 변경 | AI 코드 + KNU 빌드 | CODE | A2 |
| A2 | 2018 배관: output 경로에 연도(`submit_job_FH_Tier3_unified.py` 가 지금 `AnalyzerOutput_<mode>` 만 씀), 기본 yml 을 연도로, 2018 yml 3 개, `make_filelists.py`(MC·Data 두 base, `Run2017` 고정 분기), `samples_2018UL.json` v15 판(das_path, nevents, 새 키 `TTZToQQ`/`TTTWminus`/`TTTWplus`), prescan_summary 연도 분리, 2018A 트리거, P1(IsoMu24, leadMuonPt 26, JEC-unc loader), btagtrig skim 의 `passTrigger_*` 를 era 무관 bit 로 | AI 코드 + 결정 | CODE + DECIDE | S1~S4 |
| A3 | downstream 연도 일반화: TriggerStudy(`IsoMu27` 고정, era B/CDEF bit, 샘플 목록), bTagSF(BTV JSON, WP), `compute_stitch_factors.py`(lumi 41480, 출력 `stitch_factors_2017.json` 고정), plotter(`stack_plotter.C:639` LUMI 41.48, "13 TeV") | AI 코드 | CODE | S2~S4 |
| A4 | 2024 era: `EraConfig` 2024(트리거, UParTAK4 WP, JEC/JER, PU, golden JSON, jet veto map, MET filter 목록, Run 3 jet ID, PUPPI MET, prefiring·HEM 끔) | AI 코드 + 결정 + twiki | DECIDE | S5 |
| A5 | skim 한 ntuple 용 prescan: `ForgeAudit` + `ForgeTTbbKeys` + patch → `prescan_summary.json` 형식 | AI 코드 | CODE (P4 와 함께) | S5 |

### 트랙 S: SF 와 plot (KNU, 절차는 tempTTHH `docs/RUNBOOK_2017_SF_rederive.md` 를 연도만 바꿔 그대로)

| ID | 무엇 | 상태 | 막고 있는 것 |
|---|---|---|---|
| S1 | 2018 prescan → `consolidate_prescan.py` → stitch factor (tt+nb 분할은 V1 을 통과한 patch 로) | WAITS | P3, A0~A2 (V1 은 끝) |
| S2 | `btagtrig` 2018 → merge → TriggerStudy → `trigger_sf` (기준 트리거 `HLT_IsoMu24`, D-2026-09-18 의 기록: AN2019_094 는 `IsoMu27` 기준) | WAITS | S1, A3, 기준 트리거 결정 |
| S3 | bTagSF RW 2018 (FH region) → `btagNormReweight` JSON | WAITS | S2 |
| S4 | `main` 2018 (SF on) → merge → plotter → **첫 2018 stack plot**. 신호와 `TT4b` 는 V5 뒤에 추가, 그 전 stitching 은 §7 결정 3 | WAITS | S3 |
| S5 | 2024 같은 순서. prescan 은 P8/A5 | WAITS | P7, A4, A5 |

### 트랙 V: 교차 검증 (병행)

| ID | 무엇 | 어디 | 상태 | 풀어 주는 것 |
|---|---|---|---|---|
| V1 | 2018 patch ↔ 중앙 v15 NanoAOD: `matchTtbarIdSorted` 캠페인 6 샘플 63 job(`tt4b` 는 중앙 v15 없음), 판정 X1~X3 | lxplus 호스트 (CERN condor) | **DONE 09-28** (ALL PASS, 원장 V45) | S1 의 tt+nb 분할, S3 의 tt+nb group |
| V2 | 생산 중 closure C1~C3 | CRAB job | P4 에 포함 | P7 의 신뢰 |
| V3 | analyzer 실행 시 조회 점검(X4) + `tools/check_ttnb_coverage.py`(v15 기대값: V1 결과, TTHH `docs/06` 끝 절의 `nAddBJets≥3`) | KNU | S1 과 함께 | S1~S4 |
| V4 | CPV 증인: 2018 v15 ttbar 샘플 몇 파일에 `topCPVCategorizer` + `genTtbarId` 교차표(X8~X10) | lxplus 컨테이너 | CODE (비교 스크립트) | 해석 (plot 을 막지 않음) |
| V5 | Phase 0 enriched 2018: `TT4b` → `TTHHto4b` → 나머지 셋. X11·X12 | lxplus (CRAB cmsrun) | CODE + 승인 | S4 의 신호와 `TT4b` |
| V6 | 2024 sidecar(15_0_X, TTHH O5) → patch → 중앙 2024 v15 와 매칭 | lxplus | CODE | S5 의 tt+nb 분할 |

**오늘 병렬로 시작할 수 있는 것**: 맥 커밋 → (lxplus) P1, (lxplus 호스트) V1, (KNU) A0. AI 는 그동안 A1·A2 코드를 쓰고, P1 결과가 오면 P2 정리와 P4.
**09-28 기준**: V1 끝. (lxplus) P1 을 v2 로 다시, (맥) 2018 patch 를 tempTTHH 로 복사, (KNU) A0.

## 4. 교차 검증 표

종류: **identity** (같아야 함, 불일치 0) · **implication** (논리적 함의, 위반 0 기대, 예외는 event 키와 함께 출력) · **correlation** (표만, 사람이 봄).

| ID | 비교 | 종류 | 합격 기준 | 도구·로그 | 막는 것 |
|---|---|---|---|---|---|
| X1 | sidecar `genTtbarId`(MiniAOD, 10_6_32) ↔ 중앙 v15 `genTtbarId`(15_0_X) | identity | 모든 matched 키에서 disagree 0 | `matchTtbarIdSorted --json` → `aggregate_validation.py` | 2018 patch 사용 |
| X2 | v15 event 가 모두 extend 에 있다 | identity | nano 쪽 unmatched 0, nano total == v15 DAS nevents(`data/das_nevents_2018v15.json`); extend 에만 있는 수 = `TTToSemiLeptonic` 18,849,000, `ttbb_Hadronic` 103,000, 나머지 0. 단 v15 의 부모 MiniAOD 가 sidecar 입력(`TTToSemiLeptonic` 은 MiniAODv2 `-v2`, TTHH `crab/datasets.yaml`)과 다른 판이면 unmatched 가 0 이 아닐 수 있다: 그것을 드러내는 것이 이 검사다(그때는 `dasgoclient -query "parent dataset=<v15 dataset>"` 로 부모 판을 확인한다) | 같은 도구 | 2018 patch 사용 |
| X3 | 확장 불변식 | identity | 61·71 ← 53, 62·72 ← 54·55 (multi 구분과 같다), 재분류는 전부 53~55 에서, 앞자리 보존, sub ∈ {61,62,71,72} ⟺ `nAddBJets >= 3` (TTHH `docs/02_physics.md` §3, `Validation/scripts/check_extend_invariants.C`); extend 와 v15 가 같은 네 샘플은 matched 위의 `nAddBJets>=3` == patch 행 수(TTToHadronic 36,835, TTTo2L2Nu 11,790, ttbb_SemiLeptonic 37,420, ttbb_2L2Nu 15,766), 두 샘플은 patch 행 수 이하(`TTToSemiLeptonic` 44,851, `ttbb_Hadronic` 33,072) | 같은 도구 + TTHH `docs/06` 의 patch 표 | 2018 patch 사용 |
| X4 | analyzer 조회 | identity | `ExpandedTtbarId::active()` 참, `size()` == patch 행 수, genId self-check 불일치 0 (지금도 FATAL), Σ hits(전 job) == v15 의 tt+nb 수(X3) | job 로그 끝의 요약, `tools/check_ttnb_coverage.py` | S1~S4 |
| X5 | forge prescan(`ForgeAudit`+patch) ↔ analyzer prescan, 같은 event 위 | identity | 개수는 정수 일치, Σweight 는 상대차 1e-9 이하(같은 float 를 다른 순서로 더한 차이만) | A5 스크립트 vs `--mode prescan`, 한 파일 | 2024 prescan 을 forge 쪽으로 |
| X6 | Σweight closure | identity | dataset 마다 Σ `n_in` == DAS nevents(정확히), Σ `Runs.genEventCount` == Σ `n_in` | P8 집계 | S1/S5 의 정규화 |
| X7 | skim 식의 두 구현 | identity | TTreeFormula(`cut`) 통과 수 == RVec 통과 수, 파일마다 | job closure C1 | P7 |
| X8 | CPV 채널 ↔ 샘플의 붕괴 모드 | identity | `TTToHadronic`: 경입자 W 0 개, `TTToSemiLeptonic`: 1 개, `TTTo2L2Nu`: 2 개 (τ 포함 여부는 `Channel_Lepton_Count` 정의를 따름), 예외는 키와 함께 전부 출력 | V4 스크립트 | 해석 |
| X9 | `genTtbarId` 앞자리 ↔ CPV 의 W 붕괴 쿼크 | implication | 10000 자리(c-jet from W) > 0 ⇒ `Channel_Jets` 에 W→c 쌍; 1000 자리(b-jet from W) > 0 ⇒ W→qb 쌍. 반대 방향은 acceptance(pT>20, abs(eta)<2.4) 때문에 성립하지 않아도 된다 | V4 스크립트 | 해석 |
| X10 | `genTtbarId % 100` ↔ CPV `GenBJet_Count` 와 top 에서 온 b 수 | correlation | 교차표만 (acceptance 정의가 달라 identity 가 아니다) | V4 스크립트 | 없음 |
| X11 | 우리 `derive` 2018 ↔ 중앙 v15 (중앙이 있는 dataset 하나) | identity | 공통 branch 전부 `--ftol 0` 불일치 0 (D17 gate 2·5 방법) | `script/compare_v9_v15.py` 계열 | V5 결과 사용 |
| X12 | enriched `genTtbarIdExpanded` ↔ sidecar patch, `TT4b` 2018 | identity | 모든 event 에서 같음 (patch 1,950,601 행 + 나머지는 `genTtbarId` 와 같음) | 새 비교 한 줄(키 조인) | S4 의 `TT4b` |
| X13 | trigger 효율과 SF 모양 | 감시 | nb bin 마다 유한, 2017 대비 큰 변화는 원인 기록 | TriggerStudy 출력 | 없음 |
| X14 | 루미 | identity | brilcalc(우리 JSON) 2018 == 59.56 (소수 둘째 자리) | brilcalc | 최종 결과 전 |

## 5. 로그와 audit 규약

### 5.1 원칙 (이 프로젝트의 실제 실패에서)

- **모든 개수에는 독립된 두 번째 개수가 있다** (closure). 2018 `TTToSemiLeptonic` 은 `matched` 가 DAS 와 정확히 같았는데 1.87 % 의 읽기가 실패해 있었다(TTHH T-23 ⑧). 두 번째 개수(루프 뒤 `GetEntries()`)가 그것을 잡았다.
- **기준이 없으면 PASS 가 아니라 FAIL** (TTHH T-23 ⑦: 기준 파일을 못 찾자 SKIP 된 채 PASS).
- **wrapper 의 exit code 를 믿을 수 있어야 한다** (A22: 제출 실패에도 exit 0).
- **이상한 것은 처음 N 개를 event 키와 함께 찍는다** (나중에 같은 event 를 다른 도구로 볼 수 있게).
- **CRAB transcript 는 git 밖** (D-2026-08-17-no-logs-in-git; `runlog.sh` 가 crab 명령을 `nocommit/` 으로 보낸다).

### 5.2 줄 형식

grep 으로 모을 수 있게 고정 접두어, `|` 구분, 한 줄 한 사실:

```
FORGE|EVT|<run>:<lumi>:<event>|nj20=<n>|ht20=<x>|pass=<0/1>|gtid=<id>          (first 20 events of a job)
FORGE|FILE|<lfn>|n_in=<n>|n_pass=<n>|sumw=<x>|runs_sumw=<x>|runs_count=<n>|t_s=<x>
FORGE|CHECK|<name>|PASS|<detail>          (or WARN / FAIL; names C1, C2, C3 ...)
FORGE|JOB|files=<n>|n_in=<n>|n_pass=<n>|exit=<code>
```

### 5.3 수준별로 남는 것

| 수준 | 어디 | 무엇 |
|---|---|---|
| L0 event | job stdout | `FORGE|EVT` 20 줄 |
| L1 파일 | job stdout + `ForgeAudit` 1 행 | `FORGE|FILE`, 코드별 Σweight |
| L2 job | job stdout, exit code | `FORGE|CHECK` 전부, `FORGE|JOB`; FAIL 이면 non-zero |
| L3 dataset | KNU 집계(P8) | Σ `n_in` vs DAS, 파일 수 vs job 수, Σweight, 크기 |
| L4 캠페인 | `script/runlogs/forge_audit_<campaign>_<UTC>.tsv`, 원장 행 | dataset 당 한 줄 |

analyzer 와 TTHH 도구는 이미 같은 수준의 요약을 낸다: `ExpandedTtbarId::printSummary()`(hit/miss/self-check), `--preflight`(PASS/WARN/FAIL),
`aggregate_validation.py`(샘플별 PASS/FAIL), `exe_MakeJSON` 의 group 구성과 central ratio. 트랙 S 의 각 단계에서 **붙여 줄 줄**은 RUNBOOK §11 에 적는다.

### 5.4 실패 정책

- job 안의 closure FAIL → non-zero exit → CRAB 재시도. 같은 파일에서 반복되면 그 LFN 을 원장에 적고 사람이 본다.
- 집계에서 dataset 이 DAS 와 다르면 그 dataset 은 S 트랙에 쓰지 않는다(부분 생산으로 plot 을 그리지 않는다; 필요하면 명시적으로 `PARTIAL` 표시).
- 기준 파일(DAS 수치, patch)이 없으면 FAIL.

## 6. 이번 조사에서 확인한 사실 (근거)

1. **2018 v15 의 event 수는 MiniAOD 와 두 샘플에서 다르다.** 스캔 로그 `script/das/das_ttHH_2018UL_v15_20260923_0853.log` 의 `DS|` 줄과
   TTHH `docs/06_validation_results.md` 의 extend rows:

   | 샘플 | 중앙 v15 (표준) | extend (MiniAOD) | v9 (DAS) |
   |---|---:|---:|---:|
   | TTbar_SemiLep | 460,133,000 | 478,982,000 | 476,408,000 |
   | TTbar_Hadronic | 343,248,000 | 343,248,000 | 334,206,000 |
   | TTbar_DiLep | 146,010,000 | 146,010,000 | 145,020,000 |
   | TTbb_SemiLep | 10,378,681 | 10,378,681 | 10,378,681 |
   | TTbb_Hadronic | 7,946,064 | 8,049,064 | 8,049,064 |
   | TTbb_DiLep | 4,858,850 | 4,858,850 | 4,792,850 |
   | TT4b | 없음 | 9,844,000 | 9,844,000 |

   같은 로그의 JMENano 판 v15 `TTToSemiLeptonic` 은 478,982,000 이다. 09-03 스캔도 같은 값이라 생산 중인 dataset 이 아니다.
   영향: patch coverage 기대값과 X2·X3, 그리고 정규화는 ntuple 의 `Runs` tree 를 쓰므로 자동으로 맞다.
2. **haddnano 가 합치는 객체**: TTree, TH1, TObjString, THnSparse. 그 밖은 `Cannot handle` 후 버림. Events tree 의 0-entry 파일은 건너뛴다
   (CMSSW 14_2_X `PhysicsTools/NanoAOD/scripts/haddnano.py`). audit 형식(§2.3)의 근거.
3. **NanoAODTools 의 두 경로**: 모듈이 있으면 `CloneTree(0)` + 통과 event 마다 `readAllBranches()`, 없으면 `CopyTree` (+ `cut` 의 entry list).
   `Runs`·`LuminosityBlocks` 는 두 경로 모두 통째로 복사, module 의 `endFile` 은 `outTree.write()` 전에 불린다
   (`output.py`, `eventloop.py`, `postprocessor.py`).
4. **2024 트리거 후보가 inventory 에 있다**: `script/inventory/inv_2024C_v15_Data.tsv`, `inv_2024I_v15_Data.tsv`, `inv_Summer24_v15_MC.tsv`
   셋 모두에 `HLT_PFHT400_SixPFJet32_PNet2BTagMean0p50`, `HLT_PFHT450_SixPFJet36_PNetBTag0p35`, `HLT_PFHT280_QuadPFJet30_PNet2BTagMean0p55`,
   `HLT_PFHT340_QuadPFJet70_50_40_40_PNet2BTagMean0p70`, `HLT_PFHT1050`, `HLT_IsoMu24`, `HLT_IsoMu27` 이 있다. branch 가 있다는 것은 prescale 이
   없다는 뜻이 아니다(결정 4 에서 확인).
5. **`tempTTHH/data/samples_2018UL.json`** (85 키, v9 기준): 2018UL v15 MC config 의 42 키 중 `TTZToQQ`, `TTTWminus`, `TTTWplus` 가 없고,
   있는 키도 `das_path` 는 v9 dataset 이다(A2).
6. **tempTTHH 의 2017 고정 지점**(A2·A3 의 목록): 제출기의 기본 yml `Tier3_2017_FH_unified_<mode>.yml` 과 output 경로 `AnalyzerOutput_<mode>`;
   `make_filelists.py` 의 `Run2017` 분기와 2018 기본 경로 `ttHH2018UL_prescanSlim_v1`; TriggerStudy `EventLooper.cpp` 의 `IsoMu27` 과
   era B/CDEF bit; `compute_stitch_factors.py` 의 `LUMI_PB_INV = 41480.0` 과 `stitch_factors_2017.json`; `stack_plotter.C:639` 의 41.48 과 "13 TeV".
7. **TTHH 검증 도구는 인자만으로 v15 에 쓸 수 있다**: `submit_validation_condor.py` 의 `--nano-filelist-dir`, `--out-base`, `--work-base`,
   `aggregate_validation.py` 의 `--xsec-db`. 없던 것은 filelist era 와 기준값 파일뿐이었고 이번에 넣었다(TTHH 03_changelog 2026-09-27).

## 7. 결정이 필요한 것 (사용자)

1. **P2**: [7c] 결과를 보고 config 마다 branch 목록(current / slimA / slimB / slimC)과 event 선택(none / 6jcount / 6j20 / 6j25 / 6j30 / 6j20ht400).
   AI 권고 규칙: 2018UL 이 slim 만으로 들어가면 skim 없이 먼저 낸다; 합계는 한도에서 1 TB 이상 남긴다.
2. **2018A 트리거** (D-2026-09-18-2018A-trigger): 기록된 권고는 (b)+(c), 즉 2018 한 목록의 합집합 OR + 선언된 부재 목록.
   그리고 trigger SF 의 기준 트리거(`IsoMu24` 로 가는 P1 항목 vs AN2019_094 의 `IsoMu27`).
3. **`TT4b` 없이 첫 2018 plot 을 낼지**: (i) enriched `TT4b` 를 기다린다, (ii) 임시로 tt+nb 를 ttbb 와 inclusive 가 갖는 stitching 으로 먼저
   그리고 `TT4b` 가 오면 교체한다(`compute_stitch_factors.py` 에 그 option 이 아직 없다). 신호 `TTHHto4b` 도 같은 경로로 온다.
4. **2024 트리거와 b-tag**: §6 4 의 후보 중 무엇을, 기준 트리거는 무엇으로; b-tagger 는 UParTAK4(BTV 09-09 답변, `ttHH/03_run3_plan.md` §2 9 행),
   SF 는 shape SF 가 있는지 BTV payload 로 확인한 뒤 norm reweight 방식을 그대로 쓸지.
5. **Phase 0 착수** ([11](11_unified_forge_plan.md) §7 1): 2018 `derive` 부터.
6. **xsec**: `TTZToQQ`(861 fb vs 841 fb 정의), `TTTWminus`/`TTTWplus`, 13.6 TeV 표(01_STATUS 표 7). 첫 plot 은 `verify_xsec: true` 임시값으로 갈 수 있다.
7. **2024 tt+nb**: V6 착수 시점. 그 전의 2024 plot 은 tt+nb 를 나누지 않는다(tt+B 안에 있다).

## 8. 위험과 대응

- **무증상 오답**: tempTTHH P0 7 건이 전부 "크래시 없이 틀린 숫자" 였다(tempTTHH STATUS OPEN 6). 대응은 closure(§4, §5)와 FATAL.
- **AAA 불안정**: TTHH T-24(파일 open timeout, 한 dataset 에 job 이 몰릴 때). V1 은 재시도가 읽기 경로에 있는 `matchTtbarIdSorted` 를 쓴다.
  09-28 [7c]: 사이트 throttle(`[3005] I/O limit exceeded`)에서 ROOT 는 `CopyTree` 를 멈추지 않고, TBranch 는 한 process 에서 오류를 10 번까지만
  알린다. 그래서 측정 도구는 샘플마다 child process 를 쓰고 ROOT 오류 줄 하나로 그 샘플을 FAILED 로 한다(원장 V46). 생산 job 쪽의 같은 위험은
  closure C1~C3(§4, §5) 가 잡는다.
- **lxplus9 의 tmux**: 그냥 `tmux new` 로 만든 세션은 logout 때 죽는다(CERN KB0008111 의 `tmux.service` 는 그 노드에서만 다시 붙는다).
  09-28 v2 측정도 ssh 가 끊기며 멈췄다. 그래서 한 시간 넘게 도는 것은 condor job 으로 낸다(`script/condor/size_options.sub`, RUNBOOK §11).
- **CRAB task 당 10,000 job**: 2024 최대 dataset 2,532 files(원장 V38), 2018UL 589 files(V39). units_per_job 1 에서 안전.
- **용량**: P8 이 dataset 별 크기를 기록하고 합계를 한도와 비교한다.
- **AI 가 외부 도구 동작을 짐작하는 것**(AI_LIMITS 실패 7): 이 문서의 NanoAODTools·haddnano·GenTtbarCategorizer 서술은 CMSSW 14_2_X 소스를,
  TTHH 도구 인자는 `submit_validation_condor.py`·`aggregate_validation.py` 를, tempTTHH 의 고정 지점은 해당 파일을 읽고 썼다.
