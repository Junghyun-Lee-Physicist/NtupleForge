# `ttHH/` — ttHH → 4b workstream 문서

> **Purpose:** ttHH→4b workstream 문서의 지역 인덱스. **Audience:** ttHH ntuple
> 생산이나 은퇴한 categorization 파이프라인 기록을 보는 사람.
> **Status:** active (파이프라인은 full passthrough; categorization은 main
> analyzer로 이관; **Run 3 확장 계획 시작 2026-09-07**). **Updated:** 2026-09-07.
> 공통 문서(상태/변경/결정/트러블슈팅)는 [`../README.md`](../README.md) 참조.

현재 ttHH ntuple 생산은 **full-NanoAOD passthrough**입니다
(`crabConfig/config_ttHH2017UL.yaml` + `modules/noop.py` +
`branch_keep_all.txt`). tt+jets categorization은 ntuplizer에서 은퇴했고 main
analyzer에서 수행합니다 — 이 디렉토리는 그 물리 배경과 은퇴한 구현의 완전한
기록을 보존합니다.

## 읽기 순서 (지역 번호)

1. **[`01_physics.md`](01_physics.md)** — 물리 배경: ttHH→4b 분석 타깃, tt+jets를
   categorize하는 이유, 5FS/4FS stitching, 5개 카테고리, `genTtbarId` 인코딩.
2. **[`02_legacy_ttbar_pipeline.md`](02_legacy_ttbar_pipeline.md)** — 은퇴한
   categorization 파이프라인의 구현 기록 (custom `Module` + branches + slimming
   목록 + skim cut)과 재구축 체크리스트.
3. **[`03_run3_plan.md`](03_run3_plan.md)** — **Run 3 확장 계획** (2022–2025,
   NanoAODv15): 범위 결정(D-R3-1…6), Run 2 와 다른 event-level 필수 항목
   15 개(jet veto map·BPix, Run 3 MET filter, jet ID 재계산, PUPPI, JEC/JER,
   PU, b-tagger …; 항목마다 실측/기억/규칙 표시), 13.6 TeV 데이터셋 명명과
   **DAS 로 확정하는 절차**(`script/das_discover_run3.sh`), `had`/`lep` 용도
   태그와 hadronic 우선 생산.
4. **[`legacy/code/`](legacy/code/)** — verbatim 소스 아카이브 (비유지보수):
   categorizer 모듈, compat shim(원래 이름 `_nanoaod_compat.py`), branch 목록들,
   원본 CRAB config, 검증 tool.

## 핵심 사실 (한 줄씩)

- 라이브 파이프라인은 branch를 추가하지 않습니다; `ttCat_*`는 더 이상 ntuple에
  없습니다 (main analyzer가 생성).
- legacy 코드는 build/import path 밖의 순수 참고 자료입니다. 재구축 체크리스트는
  [`02_legacy_ttbar_pipeline.md`](02_legacy_ttbar_pipeline.md) §9.
- 이 workstream에서 발견된 PyROOT 함정들(`UChar_t`-as-bytes 등)은 공통 규칙
  [`../06_nanoaod_branch_access.md`](../06_nanoaod_branch_access.md)으로
  일반화되어 TopCPV 모듈에도 적용됩니다.
- registry(`script/samples_registry.txt`)의 ttHH 행은 용도 태그를 갖습니다:
  `had` 47 + `lep` 16 + `had,lep` 1(SingleMuon). **ntuple 생산은
  `--workstream had`(hadronic) 먼저**, lep 는 다음 라운드
  ([`03_run3_plan.md`](03_run3_plan.md) §5).
- Run 3 데이터셋 이름은 추정하지 않습니다 — `script/das_discover_run3.sh` 의
  `HIT|` 줄만 `samples_registry_run3.txt` 로 옮깁니다 (§4).
