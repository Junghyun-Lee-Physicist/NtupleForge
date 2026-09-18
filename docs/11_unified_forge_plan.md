# 11 NtupleForge 통합 계획: 후처리 + MiniAOD 사전(dictionary) + MiniAOD → NanoAOD(+사용자 branch) 를 한 도구에서

> **목적**: 사용자가 2026-09-17 에 제안한 방향("NtupleForge 를 여러 역할을 하는 모듈 집합체로; 단 구조가 비직관적이 되면 분리 유지")
> 이 **가능한지, 무엇을 옮기고 무엇을 새로 써야 하는지, 어떤 순서로 가는지, 무엇으로 완료를 판정하는지**를 한 곳에 적는다.
> **대상 독자**: 이 통합을 실제로 할 사람/AI, 그리고 "왜 저장소가 이렇게 생겼나" 를 묻는 사람.
> **상태**: 2026-09-17 작성. 방향은 사용자 결정(`03_DECISIONS.md` D-2026-09-17-single-forge), 단계별 세부는 PROPOSED.
> **관련**: [`04_architecture.md`](04_architecture.md)(현재 NtupleForge 구조), TTHHGenCategoryTools `docs/05_architecture.md`(sidecar/enriched 데이터 흐름),
> `docs/11_enriched_nanoaod.md`(enriched 레시피·gate), `TopCPVGenCategorizer/README.md`, [`ttHH/03_run3_plan.md`](ttHH/03_run3_plan.md).

## 결론 먼저 (BLUF)

- **가능하다.** 원하는 세 기능은 이미 전부 존재한다. 다만 세 저장소, 두 런타임(python NanoAODTools / CMSSW cmsRun)에 흩어져 있고
  제출·장부(registry, DAS 스캔, preflight, runlog, 원장)는 NtupleForge 에만 있다.
- **통합의 실체는 "제출과 장부를 하나로" 이고, 코드 위치 이동은 그 다음이다.** 첫 단계(Phase 0)는 저장소를 합치지 않고도 된다:
  NtupleForge 제출기에 `job_type: cmsrun` 을 추가해 TTHHGenCategoryTools 의 cfg 를 그대로 태우면 enriched 생산·sidecar 생산이 지금의
  registry·das_scan·preflight·runlog 체계 안에서 돈다. 이것이 표 15 의 "글루" 결정이기도 하다: **(A) NtupleForge 확장** 으로 간다.
- 저장소 병합(Phase 1)은 Phase 0 을 한 번 돌려 본 뒤 결정한다. 병합해도 **경계 두 개**는 유지한다: ① python(후처리) 과 CMSSW(cmsRun, scram)
  런타임의 디렉토리 분리, ② 검증 기준 데이터·도구의 소유(D16). 이 둘이 지켜지면 비직관적이 되지 않는다.
- **완료 판정은 사용자가 정한 두 검증**이다(§4): (i) 한 dataset 에서 중앙 NanoAOD 와 우리가 MiniAOD 에서 만든 NanoAOD 가 kinematics 에서
  비 1(사실은 event 단위 동일), (ii) NanoAOD + MiniAOD 사전 경로와 MiniAOD 에서 producer 를 직접 돌린 NanoAOD 의 `genTtbarIdExpanded` 가 비 1.

## 1. 지금 있는 조각

| 기능 | 어디 | 런타임 | 상태 (근거) |
|---|---|---|---|
| NanoAOD 후처리(ntuplizer): branch keep/drop, 모듈로 branch 추가·cut | `NtupleForge/modules/`(`topCPVCategorizer.py`, `jetsMETcut.py`, `noop.py`), `script/run_postproc.py`, `branches/` | python, NanoAODTools `PostProcessor` | 2017UL v9 config 91 dataset 안정, v15 passthrough 첫 ntuple(00_START_HERE §4 ②) |
| 제출·장부: registry → DAS 스캔 → config → preflight → CRAB submit/status; 실행 기록 | `script/samples_registry*.txt`, `das_scan.sh`, `build_from_scan_log.py`, `crab/submit_crab.py`·`crab_script.py`·`PSet.py`, `runlog.sh`, `docs/10_validation_ledger.md` | python/bash | 동작 중. job 종류는 NanoAODTools 후처리 하나 |
| MiniAOD → "사전"(event 키 → 확장 id) | TTHHGenCategoryTools `TtbarIdExtender/`(CMSSW 패키지: `matchGenBHadron → matchGenCHadron → categorizeGenTtbar → ExtendedTtbarIdProducer → TtbarIdExtendAnalyzer → ttbarIDExtend.root`), `Validation/`(matching, patch 추출) | CMSSW cmsRun(10_6_32_patch1, v9), standalone ROOT | 2017 7 샘플 전량 byte-identity 완료, 2018 O6 event 수 불일치 미해결(00_START_HERE §4 ②) |
| 사전을 ntuple 에 주입 | `modules/expandedTtbarIdInjector.py` (DEFERRED) | python | 미작성. 지금은 analyzer 가 실행 시 patch 파일에서 resolve(`ExpandedTtbarId::loadFromDir`) |
| MiniAOD → NanoAOD(중앙과 동일 NANO step) + 사용자 branch | TTHHGenCategoryTools enriched 레시피(`11_enriched_nanoaod.md` §2: 중앙 cmsDriver 원문 + `ExtendedTtbarIdProducer` customise) | CMSSW cmsRun(15_0_X) | D17 gate 1–5 닫힘(2017, TT4b 2000 event; 중앙 v9 와 3,332,000 값 `--ftol 0` 불일치 0). 글루·2018/2016 레시피 미작성 |
| CPV 분류(NanoAOD 입력) | `modules/topCPVCategorizer.py`(모듈), `TopCPVGenCategorizer/`(standalone C++ `GenCatTree`, condor) | python / standalone C++ | 모듈 ≡ standalone 불일치 0(Gate 4), v9↔v15 143,000 event 불일치 0 |
| CPV 분류(MiniAOD 입력) | 원 프레임워크 `SSBAnalyzer`(MiniAOD, C++ EDAnalyzer) | CMSSW | NanoAOD 경로와의 수치 비교 **기록 없음**(사용자 지적, 신규 작업) |

## 2. 목표 구조 (제안)

한 저장소, 네 종류의 job, 하나의 registry·제출기·장부. 디렉토리는 **런타임별로** 나눈다. NtupleForge 는 lxplus 에서 이미
`CMSSW_14_2_1/src/NtupleForge` 아래에 있으므로, scram 은 `NtupleForge/<Package>/BuildFile.xml` 이 있는 디렉토리만 패키지로 컴파일하고
나머지(python, 문서, standalone tools)는 무시한다(TTHHGenCategoryTools 의 `Validation/tools/` 가 BuildFile 없이 standalone `make` 로 빌드되는 것과 같은 원리).

```
NtupleForge/
  script/           registry, das_scan, das_inventory, build_from_scan_log, runlog, check_branchlist, 인벤토리 도구   (변화 없음)
  crab/             submit_crab.py: job_type = postproc | cmsrun                                                     (Phase 0 에서 확장)
  modules/          NanoAODTools 모듈 (topCPVCategorizer, injector, cuts)                                              (python 런타임)
  branches/         keep/drop 목록                                                                                    (변화 없음)
  TtbarIdExtender/  CMSSW 패키지 (plugins/ python/ bin/ BuildFile.xml): ExtendedTtbarIdProducer, sidecar analyzer,
                    enriched NANO customise, (Phase 2) CPV MiniAOD producer                                            (scram 런타임; Phase 1 에서 흡수)
  tools/            standalone C++ (GenCatTree, Validation 의 matching/patch 도구)                                     (make; Phase 1)
  validation/       검증 기준 데이터·비교기 (D16: 이 저장소가 소유; 런타임에 다른 저장소를 읽지 않음)
  docs/             공통 문서 + TopCPV/ + ttHH/ + ExpandedTtbarId/ (TTHHGenCategoryTools docs 를 하위 디렉토리로)
```

job 종류와 그것이 만드는 것:

| job_type | 입력 → 출력 | 실행 단위 | 지금 어디 |
|---|---|---|---|
| `postproc` | NanoAOD → ntuple (branch 선택 ± 모듈) | NanoAODTools, python | NtupleForge (현재 유일) |
| `cmsrun` (nano) | MiniAOD → NanoAOD, 중앙 cmsDriver + customise(`ExtendedTtbarIdProducer`, 나중에 CPV producer) | cmsRun 15_0_X | TTHHGenCategoryTools 레시피, 제출 글루 없음 |
| `cmsrun` (sidecar) | MiniAOD → 작은 TTree(event 키 + 확장 id) = 사전 | cmsRun 10_6_32 (v9) / 15_0_X | `TtbarIdExtender/crab/`, `condor/` |
| `standalone` | NanoAOD → GenCatTree, 사전 ↔ NanoAOD matching, patch 추출 | C++ make, condor | TopCPVGenCategorizer, TTHHGenCategoryTools Validation |

registry 한 줄이 어느 job 으로 가는지는 config YAML 의 `job_type` 이 정한다(현재 YAML 이 이미 dataset 목록·모듈·branch 파일을 담는다).
`runlog.sh` 와 원장은 job 종류와 무관하게 그대로 쓴다.

## 3. 비직관적이 되지 않게 하는 규칙

1. **런타임별 디렉토리**: `modules/`(python) 과 `TtbarIdExtender/`(scram) 를 섞지 않는다. scram 패키지는 하나의 하위 디렉토리에만 두고 BuildFile 은 거기에만.
2. **registry 는 하나**: 같은 dataset 이 postproc 에도 cmsrun 에도 쓰일 수 있으므로 "무엇을" 은 registry, "어떻게" 는 config YAML 의 `job_type`.
3. **검증 데이터는 저장소가 소유**(D16 유지): `validation/` 에 기준 파일과 비교기를 두고, 런타임에 다른 저장소를 읽지 않는다.
4. **문서는 한 세트**: TTHHGenCategoryTools 의 번호 문서는 `docs/ExpandedTtbarId/` 로 옮기고 루트 STATUS/CHANGELOG/DECISIONS 는 하나만 남긴다(`docs/README.md` 배치 원칙과 같다).
5. **CRAB 로그는 여전히 git 밖**(D-2026-08-17-no-logs-in-git; `runlog.sh` 의 nocommit 라우팅 그대로).

이 규칙 중 하나라도 지킬 수 없게 되면(예: 두 CMSSW 릴리스에서 같은 패키지가 컴파일되지 않아 소스를 갈라야 함) 그 시점에 분리 유지로 되돌린다.
사용자가 붙인 조건("구조가 비직관적이면 독립 저장소")을 판정하는 기준이 이 다섯 줄이다.

## 4. 완료 판정: 사용자가 정한 두 검증 (acceptance criteria)

**(i) 중앙 NanoAOD ≡ 우리가 MiniAOD 에서 만든 NanoAOD.** 중앙 v15 가 있는 dataset 하나(예: 2017 `TTbb_4f_TTToHadronic` 또는
`TTToHadronic`)의 MiniAODv2 에 우리 `cmsrun`(nano) 레시피를 돌리고, 같은 event 를 짝지어 **공통 branch 전부를 `--ftol 0` 으로 비교**한다.
D17 gate 2 가 v9 에서 이미 이 형태로 통과했으므로(2000 event × 1666 branch, 불일치 0) 기대값은 "비 1" 이 아니라 **동일**이다.
사람이 읽는 요약으로 analyzer 가 쓰는 kinematics(jet pt/eta/phi/mass, b-tag 판별값, MET, muon/electron pt)의 히스토그램 비를 함께 낸다.
규모는 dataset 전체가 목표이고, 최소 파일 단위로 시작한다. 결과는 원장에 한 행.

**(ii) 사전 경로 ≡ enriched 경로.** 같은 MiniAOD 에서 (a) sidecar → 사전(run, lumi, event → 확장 id) 을 중앙 NanoAOD 에 붙인 값과
(b) enriched NanoAOD 의 `genTtbarIdExpanded` 를 event 단위로 비교한다. 같은 producer 코드이므로 **100 % 동일**이 기대값이고,
불일치는 event 키 매칭 오류나 설정(genJet 컬렉션, flavour info) 차이를 뜻한다. 히스토그램 비 1 은 요약이다.
CPV 도 같은 틀이다: NanoAOD 모듈(`topCPVCategorizer`) 값 ↔ MiniAOD 에서 계산한 값(SSBAnalyzer 재구현 producer). 이것이 지금 기록이 없는 비교다.

두 검증의 도구는 있는 것을 확장한다: event 짝짓기 `script/pair_v9_v15.py`, 비교 `script/compare_v9_v15.py`(v9↔v15 143,000 event 에 쓴 것),
TTHHGenCategoryTools `Validation/`(대용량 external-sort matching). 새로 쓰는 것은 "두 NanoAOD 의 공통 branch 전부 비교" 모드 정도다.

## 5. 단계

**Phase 0 (지금, 저장소 병합 없음)**
1. `crab/submit_crab.py` 에 `job_type: cmsrun`: YAML 이 pset 경로·CMSSW 릴리스·출력 모듈을 지정하고, 제출기는 registry 의 dataset 을 CRAB config 로 만든다.
   preflight(DAS 존재, job 수 상한)와 `runlog.sh` 기록은 postproc 과 동일.
2. TTHHGenCategoryTools 의 enriched cfg(2017 검증본) 를 그 pset 으로 지정해 **2017 5 종 enriched 생산 제출**(D-2026-09-17-run2-v15-two-tracks).
3. §4 (i) 을 2017 의 중앙 v15 보유 dataset 하나로 수행 → 원장.
4. 2018·2016 enriched 레시피(중앙 cmsDriver 원문 이식) → 같은 job_type 으로 제출.

**Phase 1 (Phase 0 이 한 번 돈 뒤 결정)**
5. `git subtree add` 로 TTHHGenCategoryTools 를 `NtupleForge/TtbarIdExtender/`(+ `tools/`, `docs/ExpandedTtbarId/`)로 흡수(이력 보존).
   include 경로·python cfg 모듈 이름(`TTHHGenCategoryTools.TtbarIdExtender.*` → `NtupleForge.TtbarIdExtender.*`)을 바꾸고 10_6_32 와 15_0_X 에서 각각 `scram b`.
6. TopCPVGenCategorizer 도 같은 방식으로 `tools/`(standalone) 에.
7. 컬럼 이름 `genTtbarIdExpanded` 를 producer·sidecar·loader 에 적용(D-2026-09-17-expanded-id-column-name).

**Phase 2**
8. `modules/expandedTtbarIdInjector.py`: 사전을 postproc 에서 branch 로 주입(중앙 v15 가 있는 샘플용) → §4 (ii) 의 (a) 경로가 ntuple 안으로 들어온다.
9. CPV MiniAOD producer(EDProducer, `nanoaod::FlatTable` 출력) 를 `TtbarIdExtender/`(또는 이름을 바꾼 패키지) 에 추가 → §4 (ii) CPV 판.

## 6. 위험과 대응

- **릴리스 행렬**: v9 sidecar 는 10_6_32_patch1, v15 enriched 와 Run 3 는 15_0_X. 같은 패키지가 두 릴리스에서 컴파일되어야 한다(지금까지는 됐다: D17 gate ⑤). 안 되면 `#if CMSSW_VERSION` 대신 소스를 가르지 말고 분리 유지로 되돌린다(§3).
- **scram 과 python 혼재**: BuildFile 이 있는 하위 디렉토리만 컴파일된다. `modules/`·`script/` 에 BuildFile 을 두지 않는다.
- **문서 번호 충돌**: 두 저장소 모두 `01_status`… 를 가지므로 병합 시 TTHH 쪽은 `docs/ExpandedTtbarId/NN_*.md` 로 재번호 없이 이동, 루트 문서는 NtupleForge 것만 남기고 상태·변경·결정 항목을 옮겨 적는다(append-only 유지).
- **CPV MiniAOD producer 범위**: SSBAnalyzer 의 어느 값까지 옮기는지(gen 분류 6 branch 만인지, 운동학까지인지) 는 결정 필요.
- **출력 목적지·용량**: enriched 28 task ≈ 0.47 TB(추정), 사전은 작다. 사이트(T3_KR_KNU 기본)와 EOS quota 확인은 제출 전 preflight 항목으로.

## 7. 결정이 필요한 것 (사용자)

1. Phase 0 착수 승인(= 글루 (A)). 2. Phase 1 병합 여부는 Phase 0 뒤에. 3. CPV MiniAOD producer 의 범위. 4. 출력 사이트.
