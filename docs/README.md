# NtupleForge 문서 (Documentation)

NtupleForge의 기술 문서 인덱스입니다. 최상위 [`../README.md`](../README.md)는
setup과 실행 커맨드만 다루고, 그보다 깊은 내용은 전부 여기에 있습니다.

문서는 **읽기 순서대로 번호가 붙어 있습니다** (`NN_name.md`) — 프로젝트와
최신 변경사항을 이해하려면 순서대로 읽으십시오. 문서화 계약
`DOCUMENTATION_GUIDELINE`(§3.1 번호 규칙, §7 병합/분리 기준, §8 prompt 문서)을
따릅니다.

> **코드를 수정하려면?** **[`00_PROMPT.md`](00_PROMPT.md)** (AI/기여자 작업
> 계약)와 **[`07_DeveloperGuideline.md`](07_DeveloperGuideline.md)** 를 먼저
> 읽고, 나머지를 순서대로 읽은 뒤 변경하십시오.

## 읽기 순서 (Reading order)

**공통 (repo 전체):**

- **[00_PROMPT.md](00_PROMPT.md)** — AI/기여자 작업 계약: persona, 진실의
  레퍼런스, 이 환경이 못 하는 것(ROOT/컴파일 없음), 검증·변경고지 의무.
  **TopCPV와 ttHH 두 workstream을 모두 관할하는 단일 계약**입니다. 맨 먼저 읽기.
- **[01_STATUS.md](01_STATUS.md)** — "지금 어디인가?": 활성 workstream(TopCPV,
  ttHH)과 OPEN next-steps 목록.
- **[02_CHANGELOG.md](02_CHANGELOG.md)** — 변경 이력 (append-only).
- **[03_DECISIONS.md](03_DECISIONS.md)** — 결정 로그: 비자명한 선택의 *이유*,
  대안, DECIDED/PROPOSED/OPEN/DEPRECATED 상태. Append-only.
- **[04_architecture.md](04_architecture.md)** — 프레임워크 구조: CMS
  `PostProcessor`, per-event `Module` loop, `modules/` 구성, **branch 추가/cut
  적용 모듈 작성 how-to**, input-vs-output branch-selection 규칙.
- **[05_troubleshooting.md](05_troubleshooting.md)** — 통합 인시던트 로그
  (모든 버그: 증상, 시그니처, 원인, 해결, 검증) + 검증 체계.
- **[06_nanoaod_branch_access.md](06_nanoaod_branch_access.md)** — 필수 PyROOT
  read 헬퍼(`modules/nanoaod_branch_access.py`: `to_int`, `count`)와 그것이
  막는 함정들 (`UChar_t`-as-bytes; **out-of-bounds probe segfault**). Python에서
  NanoAOD vector branch를 읽는 모든 모듈이 따라야 하는 규칙.
- **[07_DeveloperGuideline.md](07_DeveloperGuideline.md)** — 기여 규칙: 문서
  먼저 읽기, 모든 변경/문제 기록, 어떤 기록이 어느 문서로 가는지.

**모듈별 (subdirectory, 각자 지역 번호와 지역 README 보유):**

- **[TopCPV/](TopCPV/README.md)** — top CP-violation gen-level categorizer
  (`modules/topCPVCategorizer.py`) 문서: 모듈 레퍼런스와 branch 목록
  ([01_module.md](TopCPV/01_module.md)), MiniAOD 충실도 audit
  ([02_faithfulness_vs_miniaod.md](TopCPV/02_faithfulness_vs_miniaod.md)),
  verbatim MiniAOD 원본 ([03_miniaod_origin.md](TopCPV/03_miniaod_origin.md)).
  검증: `script/validate_topcpvcat.py`.
- **[ttHH/](ttHH/README.md)** — ttHH→4b workstream 문서: 물리 배경
  ([01_physics.md](ttHH/01_physics.md)), 은퇴한 tt+jets categorization
  파이프라인의 전체 기록
  ([02_legacy_ttbar_pipeline.md](ttHH/02_legacy_ttbar_pipeline.md)),
  verbatim 소스 아카이브 ([legacy/code/](ttHH/legacy/code/)).

## 배치 원칙 (why this layout)

- **status / changelog / decisions / troubleshooting은 공통(루트)** — 두
  workstream이 같은 파이프라인·같은 인프라를 공유하므로 "지금 어디", "무엇이
  바뀜", "왜 그 선택", "무엇이 깨졌었나"는 한 곳에 있어야 어긋나지 않습니다
  (one fact, one place).
- **물리/모듈 레퍼런스는 workstream별 하위 디렉토리** — 독자와 변경 축이
  다르기 때문입니다 (가이드라인 §7): TopCPV 물리가 바뀌어도 ttHH 문서는
  건드리지 않습니다.
- **prompt 문서는 루트에 하나만** (`00_PROMPT.md`) — 작업 계약(환경 한계,
  검증 의무, 스타일)이 두 workstream에서 동일하므로 디렉토리별 사본은 중복과
  drift만 만듭니다. 모듈별 세부 규칙(레퍼런스, branch prefix 등)은 그 계약
  안에 workstream별 항목으로 명시되어 있습니다.

## `ttHH/legacy/` 아카이브

[`ttHH/legacy/code/`](ttHH/legacy/code/)는 옛 categorization 파이프라인을
돌리던 코드의 verbatim, **비유지보수** 사본입니다 — categorizer 모듈, compat
shim(원래 이름 `_nanoaod_compat.py`로 보존), slimming branch 목록, branch
인벤토리, 원본 CRAB config. build/import path에 연결되어 있지 않은 순수 참고
자료입니다. 유사한 파이프라인을 재구축하려면 관련 파일을 라이브 트리로 복사해
오십시오 (체크리스트: [ttHH/02_legacy_ttbar_pipeline.md](ttHH/02_legacy_ttbar_pipeline.md) §9).
