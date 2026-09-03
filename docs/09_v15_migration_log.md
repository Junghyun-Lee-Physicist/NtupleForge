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

## 8b. 2026-08-30 — ttHH 첫 v15 ntuple

`config_ttHH*.yaml` 이 `modules/noop.py` (순수 passthrough) 를 쓰므로 v15 ntuple 에
**모듈 코드 변경이 전혀 필요 없었습니다.** `branch_hadronic_2017_v15_MC.txt` 로
20,000 event:

```
Error in <TTree::SetBranchStatus>: No branch name is matching wildcard -> btagWeight_*
Total time 83.3 sec. to process 20000 events. Rate = 240.2 Hz.
branches=664  events=20000  1.948 kB/event
누락: 없음
```

입력 2.92 kB/event 대비 67 %. `check_branchlist --profile main` 으로 분석기가 읽는
62 개를 대조한 결과 **60 개 생존, 3 개는 이미 인코딩된 rename, 대응이 없는 것은
`Jet_jetId` / `Jet_puId` 둘뿐**입니다. `genTtbarId` 는 생존 — tt+HF 범주화 전체가
걸린 branch 입니다.

`btagWeight_*` 는 v15 에서 삭제됐으므로 dead 패턴입니다 (`gen_hadronic_branchlists.py`
에서 고쳐야 함).

크기 분해 (36.3 MB / 664 branch):

```
Jet 34.9 %   GenPart 20.4 %   Electron 9.1 %   Muon 7.8 %
LHEPdfWeight 5.6 %   LHEPart 5.3 %   GenJet 4.9 %   HLT 1.7 %
```

Jet 의 상당 부분이 v15 신규 태거(`btagUParTAK4*`, `btagPNet*`, `*RegPtRaw*`)이고
분석기는 DeepJet 만 씁니다 — 압축 여지는 "v15 에만 있고 분석기가 못 쓰는 것"입니다.

---

## 10. 2026-08-31 — v9 ↔ v15 데이터셋 가용성 전수 조사

`das_scan.sh --workstream ttHH` 를 두 버전으로 돌려 registry 64 개를 대조했습니다.

**중앙 v15 가 없는 것은 6 개뿐입니다:**

| 키 | v9 | v15 |
|---|---|---|
| **`TTHHto4b`** (신호) | 9,934,000 ev / 0.033 TB | **없음** |
| **`TT4b`** | 9,502,000 ev / 0.027 TB | **없음** |
| `TTZHTo4b` | 2 datasets | 없음 |
| `TTZZTo4b` | 2 datasets | 없음 |
| `tHW` | 14,325,000 ev | 없음 |
| `TTZToBB` | 7,074,000 ev | 없음 |

`TTHHTo4b*` 는 전 캠페인 조회에서도 UL16/17/18 모두 **v9 가 최신**이고 HEFT 변종
(c2-3, c2-6, c2-m1, kl-0p5, kl-2, kl-3, kt-2) 도 전부 같습니다 — 실제 부재입니다.

**나머지는 전부 v15 가 있습니다**, stitching 용 `TTbb_4f` 3 종 포함. Data 도
전부 있습니다 (A20 의 버그를 고친 뒤 확인): `JetHT`·`BTagCSV` Run2017B–F,
`SingleMuon` Run2017B–H, plain 캠페인은 `UL2017_NanoAODv15-v1`.

---

## 11. 2026-08-30~31 — 이 캠페인이 남긴 도구

| 도구 | 역할 |
|---|---|
| `script/setup_v9v15_validation.sh` | `source` 한 줄로 세션 복구 (cmsenv, pull, proxy, 변수, 입력, cut) + `nf_*` 명령 |
| `script/compare_v9_v15.py` | event-matched 비교. 겹침 0 이면 "불일치 0" 이 아니라 exit 3. `--alias` / `--v9v15-renames` 로 rename 쌍까지 비교 |
| `script/pair_v9_v15.py` | 샘플별 파일 페어링. DAS `file,lumi` 만 쓰므로 **파일을 열지 않음** |
| `script/sweep_inventories.sh` + `inventory_manifest_2017UL.txt` | (tier × run era × 버전) 인벤토리 일괄 덤프 |
| `script/branch_presence_matrix.py` | 인벤토리 교차표. MC-only / Data-only 는 자동 분류하고 **PARTIAL** 만 남김 |
| `script/run_postproc.py --cut` | 검증 전용 preselection (공유 lumi 제한) |
| `branches/branch_CPV_validation.txt` | 검증 전용 최소 목록, v9/v15 공용. 2.01 → 0.315 kB/event |
| `branches/branch_CPV_Run2_MC_v15.txt` | 실측 인벤토리에서 유도한 v15 CPV 목록 |

`branch_presence_matrix.py` 첫 실행이 PARTIAL 31 개를 보고했는데 19 개가 단순
MC-only 였습니다 — `genWeight` 존재로 tier 를 실측 판정해 `MC-ONLY (expected)` 로
분류하도록 고쳤습니다. 남는 12 개가 진짜 신호입니다 (v15 5 + HLT era 7).

---

## 12. 2026-08-31 — 방향 전환: enriched NanoAOD

10 절의 결과가 방침을 바꿉니다. 결정 기록은
`TTHHGenCategoryTools/docs/04_decisions.md` (D-DEP1 을 부분 번복) 에 있고, 요지만:

- `TT4b` 는 tt+nb patch 행 약 200 만 중 **1,882,170 개**를 공급합니다 — sidecar
  복잡도의 대부분이 여기서 나옵니다. 그리고 **v15 가 없어 어차피 사설 생산**해야
  합니다.
- Approach 2 (MiniAOD → 중앙과 동일한 NanoAOD + 추가 branch) 는 **이미 실증**됐습니다:
  v7.2 (2026-05-28), 공통 1,665 branch 전부 sum-ratio 1.000.
  (`TTHHGenCategoryTools/docs/10_enriched_nanoaod_archive.md`)
- 당시 폐기 사유는 **storage 100 배**였습니다. *(2026-08-31 같은 날 정정)* 이 문장을 처음엔
  "TT4b 는 작아서 해당 없다" 고 썼는데 **틀렸습니다** — TT4b 도 enriched 약 27 GB 대 sidecar 약 0.3 GB 로
  상대 배율은 여전히 ~90 배입니다. 바뀐 것은 배율이 아니라 **비교 대상**입니다: D1 의 100 배는
  "중앙본을 복제" 하는 비용이었고, 이 6 샘플은 **복제할 중앙 v15 자체가 없습니다.** 중복이 아니라
  유일본의 비용입니다. TTHHGenCategoryTools D17 근거 2.

⇒ **혼합**: ttbar 3 종은 sidecar 유지, `TT4b`·`TTHHto4b`·`TTZHTo4b`·`TTZZTo4b`·
`tHW`·`TTZToBB` 는 enriched 사설 생산.

## 13. 지금 상태 (2026-09-02)

**닫힘 (NtupleForge 쪽):** CPV gen categorizer 의 v9→v15 동일성 (143,000 event × 61 branch, 비트 단위,
불일치 0) — [08](08_branch_schema_migration.md) 6 절. 데이터셋 가용성 전수 조사 — 10 절.

**닫힘 (TTHHGenCategoryTools 쪽, 이 캠페인이 촉발):** enriched NanoAOD 경로가 v9 에서 **값 단위로 증명**됐고
v15 에서 스키마까지 통과했다 — 14 절.

**남은 것:** [01_STATUS](01_STATUS.md) OPEN 절이 단일 출처다. 그룹 A(enriched 통합: `job_type: cmsrun`,
`units_per_job`, 적용 순서, 컬럼 이름 결정), B(ttHH v15 passthrough 잔여), C(CPV 잔여: 다른 ttbar 샘플·Data tier),
D(2018UL·Run3).

> 2026-08-31 판의 이 절에 있던 "`Expanded_genTtbarId` 의 ntuple forge 단계 통합" 은 **범위가 바뀌었다**.
> 그 문구는 최상위 `00_CONTEXT_ExpandedTtbarId_NtupleForge_Migration.md` 의 patch-파일 주입 계획(DEFERRED)을
> 가리켰는데, 중앙 v15 가 없는 6 샘플은 이제 NanoAOD 안에 컬럼이 **직접** 들어가므로 그 주입이 필요 없다.
> 주입 계획은 sidecar 로 남는 ttbar 3 종에만 해당한다.

## 14. 2026-08-31 ~ 09-02 — enriched NanoAOD: 12 절의 방향이 실측으로 확인됨

작업은 TTHHGenCategoryTools 저장소에서 했고 기록도 거기 있다 — **`TTHHGenCategoryTools/docs/11_enriched_nanoaod.md`**.
NtupleForge 관점의 요지만:

- **중앙 cmsDriver 원문을 DAS 에서 받았다.** `dasgoclient -query="config dataset=..."` → ReqMgr config cache.
  v9 = CMSSW_10_6_26 / `106X_mc2017_realistic_v9`, v15 = CMSSW_15_0_18 / `150X_mc2017_realistic_v1`.
  **`--era Run2_2017,run2_nanoAOD_106Xv2` 와 부모 MiniAODv2 가 완전히 같다.** 이 캠페인의 61-branch 비트 동일
  결과와 정합한다 — gen 은 릴리스·GT 와 무관하다.
- **customise 하나로 끝났다.** `--customise Configuration/DataProcessing/Utils.addMonitoring,TTHHGenCategoryTools/TtbarIdExtender/ttbarIdTable_cff.customise`.
  중앙도 그 슬롯을 쓰므로 정규 사용법이다. 새 C++ 없음.
- **v9 검증**: 2000 event × 1666 branch = 3,332,000 값, `--ftol 0`, **실질 불일치 0**. 우리에만 3 branch, 중앙에만 0.
  이 비교가 10_6_26(중앙) 대 10_6_32_patch1(우리)라 patch 차이의 영향이 0 임도 같이 증명됐다.
- **v15**: 15_0_18 에서 무수정 빌드, 1906 = 1903 + 3, 타입 동일. 값 비교 대기.
- **이 저장소의 도구가 쓰였고 고쳐졌다.** `compare_v9_v15.py` 가 NaN==NaN 을 100 % 불일치로 보고했다 — A21.
  같은 커밋(`c0eab1e`)에서 인덱싱을 key 3 branch 로 줄여 20m46s → 수 분. 짝 찾기는 `pair_v9_v15.py`(lumi) 가
  아니라 `dasgoclient -query="child file=<MiniAOD LFN>"`(부모 확정)이 정확했다 — 우리 산출물 대 중앙본에는 이쪽.
- **처리율**: v9 6.4 Hz(WAN 포함) / v15 2.4 Hz(200 ev, 로컬). v15 NANO 는 ParticleNetAK4 를 재계산한다.
  `units_per_job` 은 이 값 기준이며 2000 ev 로 재측정 후 확정.
- **사고 2 건**: proxy 만료 + MiniAOD WAN 직독 → 18m53s 소모 후 exit 84 (08 2 절 Step 2 의 "로컬 디스크" 규칙이
  MiniAOD 입력에도 그대로). stale 영역(v10 이름)에 파일을 먼저 만들었다가 정본으로 옮김. 둘 다 TTHH 08 T-28·T-32.
