# `TopCPV/` — top CP-violation gen-level categorization 문서

> **Purpose:** TopCPV gen-level categorizer 문서의 지역 인덱스. **Audience:**
> `modules/topCPVCategorizer.py` 또는 `config_CPV*` ntuple을 다루는 사람.
> **Status:** active (NanoAODv9). **Updated:** 2026-07-01.
> 공통 문서(상태/변경/결정/트러블슈팅)는 [`../README.md`](../README.md) 참조.

이 폴더는 **MiniAOD `SSBAnalyzer`** 의 gen-level top-decay categorization을
NanoAOD에서 재현하는 모듈을 문서화합니다. **레퍼런스(진실의 원천)는 MiniAOD
`SSBAnalyzer` 코드**이며, standalone C++ `TopCPVCategorizer`는 같은 MiniAOD
동작을 따라가야 하는 동반 재현물이지 레퍼런스가 아닙니다.

> **네이밍 노트 (2026-07-01):** 이 모듈군은 `ssbGenCategorizer` /
> `SSBGenCat_`에서 **`topCPVCategorizer` / `TopCPVCat_`** 로 개명되었습니다.
> 외부 레퍼런스인 MiniAOD 클래스명 `SSBAnalyzer`는 남의 코드이므로 그대로
> 유지합니다 (`../03_DECISIONS.md` → D-2026-07-01-rename-topcpv).

## 읽기 순서 (지역 번호)

1. **[`01_module.md`](01_module.md)** — 모듈 실행 방법과 emit하는 branch의 정확한
   목록 (production wiring은 여기서 시작).
2. **[`02_faithfulness_vs_miniaod.md`](02_faithfulness_vs_miniaod.md)** — audit:
   port가 MiniAOD 원본과 일치/불일치하는 지점, 무엇이 복원되었고 무엇이 복구
   불가능한지.
3. **[`03_miniaod_origin.md`](03_miniaod_origin.md)** — port가 측정되는 기준인
   verbatim MiniAOD `SSBAnalyzer` 소스.
4. **`GenPart_channel_definition.md`** *(standalone TopCPV 패키지)* — channel-code
   규약 (lepton 합, τ 부호, jet digit code).

## 핵심 사실 (한 줄씩, 상세는 위 파일들)

- **레퍼런스 = MiniAOD `SSBAnalyzer`** (`03_miniaod_origin.md`); audit의 복원은
  모듈과 standalone TopCPV C++ **양쪽**에 적용됨
  (`../03_DECISIONS.md` → D-2026-06-28-miniaod-reference).
- `Channel_Idx`는 **전체** selected list 합 (background channel 복원);
  `Channel_Idx_Final`은 GenPart daughter map을 걸어 τ→ℓ을 해석하고 **τ daughter를
  GenPar에 append** (`01_module.md`).
- 파생 branch만, prefix `TopCPVCat_`; raw gen collection은 full-NanoAOD
  passthrough에서 옴. 추가 진단 `Channel_Idx_Expanded`.
- 유지(audit §3/§4/§6): last-copy top, 명시적 W⁻ daughters, `GenJet_hadronFlavour`
  기반 `GenBJet`. NanoAOD에서 복구 불가: `GenBHad` hadron kinematics, 공식
  `FromTopWeakDecay`, GenJet HCal/ECal energy, B-frag weights.
- **MC 전용.** GenPart 없는 입력(data)은 crash 대신 로그 한 줄 남기고 **no-op**
  (2026-07-01 수정; `../05_troubleshooting.md` A11). 그래도 data config에는 넣지
  말 것.
- Collection 길이는 **count branch**(`event.nGenPart` 등)에서만 읽음 —
  out-of-bounds array probe는 segfault (`../05_troubleshooting.md` A12,
  `../06_nanoaod_branch_access.md`).
- Byte-identity 검증은 lxplus에서 `script/validate_topcpvcat.py`로 수행
  (dev container에는 ROOT / 테스트 파일 / 네트워크 없음).
