# 10 검증 원장 (validation ledger)

> **목적**: 이 저장소에서 "확인했다" 고 말하는 모든 것을 한 표에 모은다. 날짜, 무엇을, 어느 규모로, 결과가 어땠고,
> **증거 파일이 어디 있는지**. 결과의 해석은 각 문서에 있고, 여기는 색인이다(한 사실은 한 곳에: 숫자는 증거 파일과
> 그 문서를 가리키고 다시 적지 않는 것이 원칙이지만, 표를 읽을 수 있을 만큼의 요약값은 적는다).
> **대상 독자**: "그거 검증됐나?" 를 묻는 사람. 답은 표의 한 행이어야 한다.
> **상태**: 2026-09-16 작성, 09-17 V21–V25 추가. 그 이전 행은 기존 문서에서 옮겨 적었고(출처 열), 이날부터는 `script/runlog.sh` 가 남기는
> `script/runlogs/LEDGER.tsv` 의 실행이 이 표의 원자료다. **새 검증을 하면 행을 추가한다.**
> **관련**: [`08_branch_schema_migration.md`](08_branch_schema_migration.md) (절차·결과), [`09_v15_migration_log.md`](09_v15_migration_log.md) (시간순 로그),
> `script/runlogs/README.md` (실행 기록 규약).

## 결론 먼저 (BLUF)

- 2026-09-17 현재 **닫힌 검증**: CPV 모듈의 v9 기준 동등성(Gate 4)과 v9↔v15 동등성(143,000 event, 불일치 0), Run 2 네 v15 캠페인과 Summer24 의
  샘플 가용성(inventory, `CASE_ONLY` 0), UL16 MiniAODv2 부모 136 키 전부 존재, 브랜치 스키마 48 인벤토리, v15 브랜치 목록 10 개의
  dead-pattern 0.
- **열린 검증**: CPV 나머지 샘플(`TTToHadronic`, `TTTo2L2Nu`) 코드 경로, CPV Data tier, 2018A 에서 `…_2p94`/`…_1p59` 가 메뉴에 들어온 run(bracket),
  실제 job 에서의 branch 목록 동작(Step 6, `-N 10`), Run 3 트리거·`Flag_METFilters` 의 analyzer 측 영향. ~~2016 Data 9 era 스윕~~, ~~2018A 첫 파일 run 범위~~ 는 09-17 에 닫혔다(V21–V25).
- 읽는 법: **결과 열이 "통과" 라도 규모 열을 같이 본다.** 한 파일·한 샘플 측정은 그렇게 적혀 있다.

## 1. 원장

| # | 날짜 | 무엇을 검증 | 규모 | 결과 | 증거 파일 | 기록 문서 |
|---|---|---|---|---|---|---|
| V01 | 2026-08-25 | CPV: NanoAODTools 모듈 `topCPVCategorizer` ≡ standalone C++ `GenCatTree` (Gate 4, v9) | 2,000 event × 61/64 branch | 불일치 0 | `script/validate_topcpvcat.py` 출력 (당시 lxplus) | [08](08_branch_schema_migration.md) §6.5, [09](09_v15_migration_log.md) 2 절 |
| V02 | 2026-08-27 | v9 → v15 스키마 diff, 2017UL MC (`TTToSemiLeptonic`) | 1666 → 1903 branch | 127 삭제 / 370 추가 / 86 타입 변경 | `script/inventory/diff_v9_v15_2017UL_MC.txt`, `inv_2017UL_v9_MC.tsv`, `inv_2017UL_v15_MC.tsv` | 08 §3 |
| V03 | 2026-08-27 | CPV 모듈이 읽는 branch 의 v15 존재 (Gate 5) | 12 branch | rename 0, 삭제 0 | 위 diff | 08 §6.5, 09 4 절 |
| V04 | 2026-08-27 | CPV 모듈을 v15 파일에서 실행 (Gate 5b) | 2,000 event | 코드 수정 없이 통과 | (lxplus 출력, 09 에 인용) | 08 §5, 09 4 절 |
| V05 | 2026-08-30 | CPV 모듈(v9) ≡ 모듈(v15), event-matched | 143,000 event × 61 branch, `--ftol 0` 재실행 포함 | 불일치 0 (비트 동일) | `script/pair_v9_v15.py`·`compare_v9_v15.py` 출력 (09 에 인용) | 08 §6.3–6.6, 09 6 절 |
| V06 | 2026-08-30 | 음성 대조군: 비교기가 실제 차이를 잡는가 | 1 샘플 | 잡음 | 09 6.4 절 | 08 §6.4 |
| V07 | 2026-08-30/31 | HLT 집합은 run 범위가 결정 (2017 v9 Data era 별 HLT 수) | JetHT B..F + UL17 MC | B 269 / C 479 / D,E 526 / F 580 / MC 569 | `script/inventory/inv_2017?_v9_Data.tsv` | 08 §3.2b, `script/check_branchlist.py` 주석 |
| V08 | 2026-09-03 | Run 2 UL17/UL18 v9·v15 DAS 스캔 (registry 매칭) | ttHH registry | v15 NOT_FOUND 6 (당시) | `script/das_ttHH_2017UL_v15_20260903_0919.log`, `das_ttHH_2018UL_v15_20260903_1016.log` (+ v9) | 09 10 절, `ttHH/03_run3_plan.md` |
| V09 | 2026-09-07 | Run 3 캠페인 문자열 probe·discovery (6 era) | DAS | 캠페인 6 개 확정, Summer24 에 hadronic 세트 존재 | `script/das_probe_*_v15.log`, `script/das_discover_*_v15_20260907_*.log` | `ttHH/03_run3_plan.md` §4.2·§4.5 |
| V10 | 2026-09-11 | 캠페인 전수 inventory: Summer24, UL17, UL18 v15; UL16 pre/post v15 와 v9 | 캠페인당 수천~1.6 만 dataset | `CASE_ONLY` 0 전부; Run 2 v15 네 캠페인 `NOT_FOUND` 집합 동일(27, 이후 20) | `script/das_inventory_*_20260911_*.tsv` + `.match.txt` | 09 15·16 절, `03_DECISIONS.md` D-2026-09-11-run2-scope-2016 |
| V11 | 2026-09-16 | `runlog.sh` 자가 점검 (게이트) | 2 회 | EXIT 0; git `e6eb9c3`, ROOT 6.40.04, dasgoclient v02.04.54, proxy 43,153 s | `script/runlogs/run_selftest_20260916_064231.log`, `_064304.log` | 09 17 절 |
| V12 | 2026-09-16 | UL16 MiniAODv2 부모 inventory (preVFP / postVFP) | 30,897 / 31,683 dataset | registry 136 키 **전부 EXACT**; 요청 5 종 VALID, 27.2M / 27.1M | `script/das_inventory_ul16pre_miniaodv2_20260916_0856.tsv(.match.txt)`, `..._ul16post_..._0857.tsv`; `script/runlogs/run_ul16pre_miniaodv2_20260916_065618.log`, `run_ul16post_miniaodv2_20260916_065754.log` | 09 17 절, `ttHH/04_mc_request_2026-09.md` §1 |
| V13 | 2026-09-16 | Run 3 had 스캔 2024 / 2025 (`das_scan.sh`) | 65 키 (MC 61 + DATA 4) × 2 | EXACT 64, NOT_FOUND 1 (`TTWJetsToLNu`); DATA 8 dataset/PD | `script/das_ttHH_2024_v15_20260916_0859.log`, `das_ttHH_2025_v15_20260916_0900.log`; `script/runlogs/run_das_scan_2024_had_20260916_065943.log`, `run_das_scan_2025_had_20260916_070058.log` | 09 17 절, `ttHH/03_run3_plan.md` §6 1 |
| V14 | 2026-09-16 | UL16 v15 JetHT era 문자열 discovery | 26 dataset (BTV/JME 포함) | `_UL2016_NanoAODv15` 9 개 (B, B `_v2`, C, D, E, F HIPM; F, G, H) | `script/runlogs/run_discover_ul16_jetht_v15_20260916_071703.log` | 09 17 절, `script/inventory_manifest_run3_2016.txt` |
| V15 | 2026-09-16 | 브랜치 인벤토리 스윕 (Run 3 MC 3, 2024 Data 9, 2025 Data 9, UL16 MC 2, UL16 Data 2, UL17 Data 5, UL18 Data 4, UL18 MC 1) | 35 파일, 582 s, cmssw-el8 ROOT 6.30.09 | dumped 35 / failed 0 | `script/inventory/inv_*.tsv` (35), `script/runlogs/run_sweep_run3_2016_20260916_071717.log` | 08 §7.1 |
| V16 | 2026-09-16 | `--profile main` 교차표 (48 인벤토리) | 62 요구 branch | 전부 존재 37 / MC 전용 19 / **PARTIAL 6**(모두 기지) | `script/runlogs/run_matrix_main_mc_20260916_072719.log` | 08 §7.2 |
| V17 | 2026-09-16 | HLT 교차표 (`^HLT_`, partial-only, 48 인벤토리) | 전체 HLT | exit 2 (PARTIAL 다수; era 별 메뉴) | `script/runlogs/run_matrix_hlt_20260916_072714.log` (2.8 MB) | 08 §7.4 |
| V18 | 2026-09-16 | v15 브랜치 목록 4 개 × 실제 스키마 (`check_branchlist.py`) | 2017 MC 1, 2017 Data 5 era, 2018 MC 1, 2018 Data 4 era | dead 2 종 발견·제거(`btagWeight_*`, 2017 Data `HLT_QuadPFJet*`); 고친 뒤 dead 0, exit 3 = `Jet_jetId`/`Jet_puId` 만 | 목록 머리의 명령으로 재현 (컨테이너 실행, 결과는 08 §7.3 표) | 08 §7.3 |
| V19 | 2026-09-16 | 신규 목록 6 개 × 실제 스키마 | 2024 MC 3, 2024 Data 9, 2025 Data 9, 2016 MC 2, 2016 Data 2, CPV Data 11 | dead 0 (hadronic 5 개); CPV Data 는 의도된 공유 dead 2(2017B 6) | 같음 | 08 §7.3 |
| V20 | 2026-09-16 | `build_from_scan_log.py` Run 3 데이터 변형 처리 | 2024·2025 로그 + 2018UL 09-03 로그 + NOT_FOUND 제거 사본 `--emit-config` | DATA 32 행 전부 유지; 2018 JetHT canonical `UL2018_NanoAODv15-v2`; YAML 파싱 OK | 컨테이너 dry-run (산출물 미커밋), 코드 docstring 에 기록 | `ttHH/03_run3_plan.md` §6 2 |
| V21 | 2026-09-17 | UL16 JetHT v15 `Run2016B-HIPM…-v1` vs `…_v2-v1` 의 정체 (`summary` + `run`) | dataset 2 | `-v1` = ver1: run 272760–273017, 9,726,665 ev, 11 file; `_v2-v1` = ver2: run 273150–275376, 133,752,091 ev, 145 file; 겹침 없음 | `script/runlogs/run_runs_ul16B_v15_20260917_060631.log` | `ttHH/04` §4, manifest 머리 |
| V22 | 2026-09-17 | 2018A 첫 파일(`inv_2018A_v15_Data.tsv` source)의 run 범위 | 파일 1 + dataset | 파일 316058–316719, dataset 315257–316995 → `…_2p94`/`…_1p59` 는 적어도 316719 까지 메뉴에 없음 | `script/runlogs/run_runs_2018A_firstfile_20260917_060634.log` | 01_STATUS 22n, 08 §7.4 |
| V23 | 2026-09-17 | UL16 JetHT v15 브랜치 인벤토리, 9 era 파일 (B, B ver2, C, D, E, F HIPM, F, G, H) | 9 파일, 101 s | dumped 9 / skipped 33 / failed 0; Events 1492–1593, HLT 498–560 | `script/inventory/inv_2016{B,Bv2,C,D,E,FHIPM,F,G,H}_v15_Data.tsv`, `script/runlogs/run_sweep_ul16_data_eras_20260917_060650.log` | 08 §7.1·§7.4 |
| V24 | 2026-09-17 | `branch_hadronic_2016_v15_Data.txt` × 9 era 인벤토리 (`--era 2016`) | 9 | dead 0 전부; exit 3 = `Jet_jetId`/`Jet_puId` 만 | `script/runlogs/run_check_2016_data_list_20260917_060836.log` | 08 §7.3 |
| V25 | 2026-09-17 | `branch_CPV_Run2_Data_v15.txt` × 9 era 인벤토리 (`--profile cpv`) | 9 | exit 0 전부 (2016 에서는 공유 HLT 경로명이 살아 있음) | `script/runlogs/run_check_cpv_data_2016_20260917_060842.log` | 08 §7.3 |

TTHHGenCategoryTools(expanded ttbar id, D17 enriched NanoAOD) 의 Gate 1–5 는 그 저장소의 `docs/06_validation_results.md` 가 원장이다. 여기에는 옮기지 않는다.

## 2. 등재 규칙

1. lxplus 에서 무언가를 "확인" 하는 명령은 `script/runlog.sh <step> -- <명령>` 으로 돈다. 로그와 `LEDGER.tsv` 행이 증거다.
2. 결과를 해석한 문서(08, 09, ttHH/03 등)를 쓴 뒤, **이 표에 한 행**을 추가한다: 증거 파일 열은 반드시 저장소 안의 경로.
3. 컨테이너(AI 세션)에서 돌린 검증은 산출물을 커밋하지 않으므로, 재현 명령과 결과 표를 문서에 남기고 그 문서를 증거 열에 적는다(V18–V20 방식).
4. 한 파일·한 샘플로 본 것은 규모 열에 그렇게 적는다. 규모를 늘린 재검증은 새 행으로 등재하고 이전 행을 지우지 않는다.
