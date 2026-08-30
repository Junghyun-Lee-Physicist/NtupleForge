# NanoAODv9 → v15 마이그레이션 — 캠페인 로그

**이 문서의 역할.** *무엇을 실행했고 무엇이 나왔는가*를 시간순으로, **원본 로그와
함께** 남깁니다. 결론과 재사용 가능한 절차는 여기 쓰지 않습니다 —
[`08_branch_schema_migration.md`](08_branch_schema_migration.md)에 있고 이 문서는
거기를 가리킵니다 (한 사실은 한 곳에만).

| 찾는 것 | 문서 |
|---|---|
| branch 목록 검증 **절차**, 복사용 명령어 | [08](08_branch_schema_migration.md) 2절 |
| v9→v15 **스키마 차이**와 workstream별 영향 | [08](08_branch_schema_migration.md) 3절 |
| v9↔v15 **동일성 결론**과 검증 사슬 | [08](08_branch_schema_migration.md) 6절 |
| **무엇을 언제 실행했고 로그가 어땠나** | **이 문서** |
| 무엇이 깨졌었나 | [05](05_troubleshooting.md) A18 |
| 지금 무엇이 남았나 | [01_STATUS](01_STATUS.md) |

**재현.** `source script/setup_v9v15_validation.sh` 한 줄이 아래 모든 실행의 환경을
복구합니다 (고정 LFN, 공유 lumi cut, `nf_*` 명령).

---

## 0. 왜 이 캠페인을 했나

요구는 다섯 개였습니다 — v9/v15 병렬 진행 후 v15로 마이그레이션, 2017·2018UL에
Run3 확장 가능한 구조, `Expanded_genTtbarId`를 ntuple forge 단계로, hadronic
branch 압축(+MET/muon), SSB gen validation.

**1번이 나머지 전부의 전제**입니다. v15가 v9와 다른 결과를 낸다면 압축이든 확장이든
의미가 없습니다. 그래서 이 캠페인은 "v15로 옮겨도 물리 결과가 바뀌지 않는다"를
증명하는 데 집중했습니다.

---

## 1. 2026-08-17 — v15 존재 확인과 데이터셋 인프라

Run2 UL NanoAODv15가 실재함을 확인했습니다:
`RunIISummer20UL{17,18}NanoAODv15-150X_mc{2017,2018}_realistic_v1-v{1,2}` (plain) 및
JMENano/BTVNano flavour. 글로벌 태그 `150X` ⇒ CMSSW_15_0_X ⇒ v12/v15 rename이
실제로 적용됩니다.

만든 것: `script/samples_registry.txt` (172행 단일 소스, 4중 중복 제거),
`script/das_scan.sh`, `script/build_from_scan_log.py`,
`script/dump_branch_inventory.py`, `script/check_branchlist.py`.

**TT4b는 v15가 없습니다 (전수조사 완료).** 전체 인벤토리 9개 NanoAOD 데이터셋,
최대 버전 v9. TT4b는 tt+nb patch 행 1,882,170개(61+62=1,585,810 / 71+72=296,360)의
공급원이므로, 마이그레이션 검증은 나머지 6/7로 하고 (모든 코드 경로가 밟힘) 동일
MiniAODv2에서 사설 NANO를 생산하는 방향입니다.

**Gate 6 (MiniAOD parent 동일성), 2017·2018 양쪽:** `6 SAME_PARENT / 0
DIFFERENT_PARENT / 1 VERSION_ABSENT`, `RECORDED|…|IN_CHILD_LIST` 14/14.
⇒ 6개에 대해 extend CRAB 재생산 불필요.

---

## 2. 2026-08-25 — Gate 4: 프로젝트 최초의 실제 ROOT 검증

`script/validate_topcpvcat.py`를 강화(비교 커버리지 53 → **61 / 64** GenCatTree
branch; run/lumi/event만 미비교)한 뒤 standalone C++ `TopCPVGenCategorizer` 출력과
NtupleForge 모듈 출력을 event 단위로 비교:

```
compared 61/64 branches, uncompared 0
matched 2000 events, unmatched 0 / 0
mismatches 0
exit = 0
```

물리 sanity (TTToSemiLeptonic, 2000 event): e : μ : τ = **669 : 686 : 645**
(기대 666.7, σ=21.1 → +0.1σ / +0.9σ / −1.0σ), all-hadronic 0, dilepton 0,
unclassifiable 0.

그전까지 이 프로젝트의 검증은 코드 읽기뿐이었습니다.

---

## 3. 2026-08-26 — 성능: 제가 낸 경고가 틀렸습니다

원격(XRootD) 실행이 2.2 Hz로 나와 "1.126M event 파일 하나에 5.9일, CRAB wall-time
7배 초과 ⇒ 생산 불가"라고 경고했습니다. **틀렸습니다.**

| 입력 | 모듈 | event loop | Rate | user+sys |
|---|---|---|---|---|
| XRootD (WAN) | topCPVCategorizer | 929.8 s | 2.2 Hz | — |
| XRootD (WAN) | noop | 405.0 s | 4.9 Hz | 15.9 s (**CPU 3.8 %**) |
| /tmp 로컬 | noop | 8.7 s | 230.2 Hz | 12.556 s |
| /tmp 로컬 | topCPVCategorizer | 10.0 s | 199.5 Hz | 13.885 s |

CPU 사용률 3.8 %가 전부를 말해 줍니다 — 병목은 계산이 아니라 WAN I/O 대기였습니다.
모듈 자체 비용은 `13.885 − 12.556 = 1.33 s / 2000 event = **0.66 ms/event**`
(순수 복사 대비 CPU +11 %). 1.126M event ÷ 199.5 Hz ≈ 1.57 h ⇒ CRAB 여유.
**경고 철회.**

교훈: 느리다고 모듈을 탓하기 전에 `noop`으로 baseline을 재고, `time`의 `user+sys`만
비교합니다 (`real`은 page cache에 좌우됨 — 실제로 local-noop의 `real` 35.2 s가
local-module의 16.1 s보다 컸는데, 앞 실행이 방금 쓴 2.3 GB를 cold cache로 읽었기
때문입니다).

---

## 4. 2026-08-27 — 스키마 실측과 Gate 5

### 4.1 인벤토리

```
[dump] Events 1666 branches   (2017UL v9  MC)
[dump] Events 1903 branches   (2017UL v15 MC)
## Summary: 127 removed, 370 added, 86 retyped
```

전체 diff: `script/inventory/diff_v9_v15_2017UL_MC.txt`. 분석: [08](08_branch_schema_migration.md) 3절.

### 4.2 Gate 5 — CPV 모듈이 읽는 branch만 좁혀 보기

```
+  Events/GenJet_nBHadrons        UChar_t
+  Events/GenJet_nCHadrons        UChar_t
+  Events/GenPart_iso             Float_t
~  Events/GenJet_partonFlavour    Int_t -> Short_t
~  Events/GenPart_genPartIdxMother Int_t -> Short_t
~  Events/GenPart_statusFlags     Int_t -> UShort_t
~  Events/nGenJet                 UInt_t -> Int_t
~  Events/nGenPart                UInt_t -> Int_t
~  Events/nPSWeight               UInt_t -> Int_t
```

**rename 0건, 삭제 0건.** 타입만 변경. `statusFlags`의 bit 7/13은 16비트 안이므로
잘림 없음. `GenJet_hadronFlavour`는 UChar_t 그대로 ⇒ `to_int` 계속 필요.

### 4.3 check_branchlist — (C) 절 오탐 6건

v9·v15 양쪽에서 `TopCPVCat_isSignal` 등 6개가 "입력 파일에 없음"으로 나왔습니다.
당연합니다 — 모듈이 *만드는* branch를 입력 스키마에서 찾고 있었습니다. `produced`
플래그로 (C)에서 제외하도록 수정. 이후:

```
=== (C) analyzer requirements ABSENT FROM THE INPUT FILE ITSELF ===
  (6 module-produced branch(es) excluded -- see check (B))
  OK -- every required branch exists in the input schema.
```

`rc=4`는 이제 순수하게 dead 패턴 문제만 의미합니다. 남은 dead 패턴 2개
(`HLT_IsoTkMu*`, `HLT_L2DoubleMu*`)는 2016 경로명이고 파일이 Run2 4개 era 공유라
**삭제 금지** — per-era 분리가 정답.

### 4.4 Gate 5b — v15에서 모듈 실행

```
[topCPVCategorizer] pre-registered 16 gen branch readers
processed=143000... (아래 6절) / 2000 event 시험: signal=2000, unclassifiable=0
Total time 11.5 sec. to process 2000 events. Rate = 174.4 Hz.
real 0m33.663s  user 0m13.509s  sys 0m2.224s
```

**코드 수정 없이 통과.** CMSSW_14_2_1의 NanoAODTools `arrayReader`가 v15의
`UShort_t`/`Short_t`를 처리합니다. `unclassifiable=0`이 `statusFlags` 비트마스크가
멀쩡하다는 증거입니다 (깨졌다면 hard-process 선택이 무너져 대량 −999).

---

## 5. 2026-08-28 — v9 NanoAOD가 불완전합니다

`dasgoclient summary`, `TTToSemiLeptonic` UL17:

| | nevents | nlumis | parent 대비 |
|---|---|---|---|
| MiniAODv2 (parent) | 355,332,000 | 355,332 | — |
| **NanoAODv15** | **355,332,000** | 355,332 | **100.00 %** |
| **NanoAODv9** | 346,052,000 | 346,052 | **97.39 %** |

양쪽 다 정확히 1000 event/lumi이므로 차이는 **9,280 lumi = 9,280,000 event**.
parent가 동일하므로(§6.1) v9 생산이 parent를 다 덮지 못한 것입니다. 잃어버린 lumi는
실패한 job이라 물리적으로 무작위 ⇒ **편향이 아니라 통계 손실**이고, `genEventSumw`를
실제 처리한 파일에서 합산하는 한 정규화는 자기일관적입니다.
**v15 마이그레이션의 추가 근거이며 그룹 보고 사안입니다.**

---

## 6. 2026-08-30 — event-matched 비교: 결론

### 6.1 파일 페어링이 어려운 부분이었습니다

```
parent dataset=<v9>  -> /TTToSemiLeptonic.../RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1/MINIAODSIM
parent dataset=<v15> -> /TTToSemiLeptonic.../RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1/MINIAODSIM
```

parent 동일 ⇒ 같은 event가 양쪽에 존재. 그런데 각 데이터셋 첫 파일끼리:

```
nano_v9_local.root    entries=1126000  unique=1126000  lumi=[14715,353516]
nano_v15_local.root   entries= 927000  unique= 927000  lumi=[ 2579,331876]
overlap = 0   (0.000 % of v9, 0.000 % of v15)
```

lumi *범위*는 크게 겹치는데 event 겹침이 0 — NanoAOD job splitting이 버전마다 달라
lumi *집합*이 거의 서로소입니다. v9 파일의 lumi 집합 대 v15의 398개 파일을 겹침 순
랭킹:

```
shared=143  lumis_in_file=927  /store/mc/.../2560000/12804c46-d060-4a27-b333-a6254f4dc02c.root
shared=84   lumis_in_file=927  /store/mc/.../2560000/029e819b-...root
shared=68   lumis_in_file=927  /store/mc/.../2560000/8b3ce137-...root
```

⇒ 143 lumi ≈ 143,000 event 공유. **이 페어링은 특정 v9 파일에 묶여 있습니다** —
`dasgoclient | head -1`로 다른 파일을 집으면 겹침이 사라집니다. 그래서
`setup_v9v15_validation.sh`가 LFN을 고정합니다.

### 6.2 A18 — 30초짜리 스모크 테스트가 15분 실행 두 번을 구했습니다

검증 전용 최소 branch 목록(`drop *` + 필요한 것만 keep)을 만들고 먼저 2000 event로
확인:

```
total branches = 15
TopCPVCat_*    = 0
VERDICT: FAIL -- 'drop *' also removed the module's own branches.
```

모듈은 `processed=2000 signal(ttbar)=2000`을 보고했습니다. **완벽히 돌고 결과를
전부 버린 것**입니다. 에러도 경고도 없습니다. 제가 그 파일 주석에 "모듈 branch는
outputbranchsel을 피해간다"고 써 놓았던 주장이 반증됐습니다.
`keep TopCPVCat_*` 추가 후:

```
total branches = 61
TopCPVCat_*    = 46
events=2000  size=3.0 MB  -> 1.521 kB/event
VERDICT: OK
```

46은 정확한 수입니다 (`validate_topcpvcat.py`의 DERIVED 45개 + `Channel_Idx_Expanded`).
기록: [05](05_troubleshooting.md) A18.

### 6.3 본 실행

```
--- nf_v9 ---
Pre-select 143000 entries out of 1126000 (12.70%)
accepted 143000/143000 (100.00%)
processed=143000 signal(ttbar)=143000 unclassifiable=0 (0.000%)
Total time 457.0 sec.   real 7m46.561s  user 7m35.312s  sys 0m4.283s
-> /eos/user/j/junghyun/nfout/matched_v9.root   45M

--- nf_v15 ---
Pre-select 143000 entries out of 927000 (15.43%)
accepted 143000/143000 (100.00%)
processed=143000 signal(ttbar)=143000 unclassifiable=0 (0.000%)
Total time 496.1 sec.   real 8m27.093s  user 8m14.426s  sys 0m3.695s
-> /eos/user/j/junghyun/nfout/matched_v15.root  45M
```

실효 처리율 313 Hz / 288 Hz. ⚠ 로그의 `Rate = 2463.9 / 1868.7 Hz`는 NanoAODTools가
분모에 *입력* entry 수를 쓴 것이라 **틀립니다**; 진행 로그의 `avg speed 0.345 /
0.314 kHz`가 맞는 값입니다.

출력 45 MB / 143,000 = **0.315 kB/event** (프로덕션 목록의 2.01 kB/event 대비 6.4배
감소). 양쪽 모두 `branches/branch_CPV_validation.txt` **하나**를 썼습니다 — 이름이
v9/v15에서 바이트 단위로 같아 목록이 교란 요인이 될 수 없습니다.

### 6.4 비교 — 세 번

```
--- nf_compare (--prefix TopCPVCat_, --ftol 1e-4) ---
v9  : 143000 entries, 46 'TopCPVCat_' branches
v15 : 143000 entries, 46 'TopCPVCat_' branches
events : v9=143000  v15=143000  common=143000  (v9-only=0, v15-only=0)
compared 143000 events x 46 branches
events with >=1 disagreement: 0  (0.0000 %)
v9 and v15 AGREE on every compared branch of every common event.

--- nf_compare --prefix ""  (음성 대조군 겸 범위 확대) ---
v9  : 61 branches      v15 : 63 branches
compared : 61 branches
  !! only in v15 output: GenJet_nBHadrons, GenJet_nCHadrons
compared 143000 events x 61 branches
events with >=1 disagreement: 0  (0.0000 %)

--- nf_compare --ftol 0  (비트 단위) ---
compared 143000 events x 46 branches
events with >=1 disagreement: 0  (0.0000 %)
```

**음성 대조군이 핵심입니다.** "불일치 0"은 비교기가 고장나도 나옵니다.
`--prefix ""` 실행이 `only in v15: GenJet_nBHadrons, GenJet_nCHadrons`를 잡아냈고,
이는 §4.1 인벤토리 diff가 예측한 바로 그 두 개입니다 — 비교기가 차이를 실제로
감지하며, 독립적인 두 측정이 서로를 확인합니다.

`--ftol 0`도 통과했으므로 float까지 비트 단위 동일이고, 결과가 허용오차에 기댄 것이
아닙니다.

**검증 사슬**과 그 해석: [08](08_branch_schema_migration.md) 6.5절.

---

## 7. 2026-08-30 — ttHH 쪽 실측

분석기가 읽는 62개 branch를 v15 실측 목록에 대조:

- **60개 그대로 생존**
- 3개는 대체 이름이 `check_branchlist.py`의 `REQUIRED`에 **이미 인코딩돼 있음**:
  `fixedGridRhoFastjetAll → Rho_fixedGridRhoFastjetAll`, `MET_pt → PFMET_pt`,
  `Electron_mvaFall17V2Iso_WP90 → Electron_mvaIso_WP90`
- **대응이 전혀 없는 것은 정확히 2개**: `Jet_jetId`, `Jet_puId`

`genTtbarId`는 살아 있습니다 — tt+HF 범주화 전체가 걸린 branch입니다.

```
Events	Jet_puIdDisc	Float_t        <- 살아 있음 (WP 직접 적용 가능)
(Jet_jetId 없음, passJetIdTight 없음)
```

jetId 재계산 재료는 전부 존재합니다: `Jet_nConstituents`, `Jet_chMultiplicity`,
`Jet_neMultiplicity` (셋 다 UChar_t ⇒ `to_int` 필수), `Jet_neHEF`, `Jet_neEmEF`,
`Jet_chHEF`, `Jet_chEmEF`, `Jet_muEF`, `Jet_hfHEF`, `Jet_hfEmEF`.

**역할 분담이 여기서 갈립니다:**

| | 할 일 |
|---|---|
| NtupleForge | branch 목록이 바뀐 이름과 jetId/puId **재료**를 실어 보내면 끝. ttHH config는 `modules/noop.py`라 **모듈 코드 변경 0** |
| tempTTHH analyzer | PF fraction + multiplicity로 jetId 재계산, `Jet_puIdDisc`에 WP 적용, 바뀐 이름 반영, UChar_t는 `to_int` |

`branches/branch_hadronic_2017_v15_MC.txt` 초안은 `keep Jet_*`이라 재료가 자동으로
따라옵니다. 다만 인벤토리에 대보기 전 초안이라 최소 하나는 깨져 있습니다:
`keep btagWeight_*` — `btagWeight_CSVV2`/`btagWeight_DeepCSVB` 둘 다 v15에서
삭제됐으므로 dead 패턴입니다.

---

## 8. 부수적으로 잡은 것

| | 내용 |
|---|---|
| `resolve_nano_children.sh` | forward glob이 **글로벌 태그 속 `_v15`** 를 매치해 TT4b에 대해 허위 `DIFFERENT_PARENT`. era prefix + 정확한 버전 토큰 매치로 수정 |
| AFS quota | `run_postproc.py`는 `OUTPUT_DIR="."` (CRAB 요구)이라 중간 `_Skim.root`가 항상 cwd에. repo에서 돌려 AFS home(10 GB)이 99 %까지 참. **스크래치에서 실행하고 `-o`에 EOS 절대경로** |
| bash `!!` | 대화형 bash는 **큰따옴표 안에서도** history expansion을 합니다. 붙여넣은 명령이 조용히 다른 명령으로 바뀜 (두 번 당함). `set +H` — [08](08_branch_schema_migration.md) 2절 Step 0 |
| 상대경로 | `source` 후 cwd가 `$WORK`라 repo 상대경로가 실패 (`git pull`, `python3 script/...`). `nf_pull` / `nf_check` 래퍼로 구조적 차단 |

---

## 9. 지금 상태

**닫힘:** CPV gen categorizer의 v9→v15 동일성 (143,000 event × 61 branch, 비트 단위,
불일치 0). 상세와 검증 사슬은 [08](08_branch_schema_migration.md) 6절.

**남은 것:** [01_STATUS](01_STATUS.md)의 OPEN 절이 단일 출처입니다. 요약하면 —
다른 ttbar 샘플(`TTToHadronic`, `TTTo2L2Nu`)의 코드 경로 미검증, Data tier 미검증,
ttHH branch 목록의 dead 패턴 정리와 첫 v15 ntuple 생산, analyzer 쪽 jetId/puId
재계산, `Expanded_genTtbarId`의 ntuple forge 단계 통합, 2018UL·Run3 확장,
TT4b v15 부재에 따른 사설 생산.
