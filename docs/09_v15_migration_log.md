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
> 그 문구는 최상위 `archive_2026/00_CONTEXT_ExpandedTtbarId_NtupleForge_Migration.md` 의 patch-파일 주입 계획(DEFERRED)을
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

## 15. 2026-09-11 — `TTZToBB` 는 요청하지 않는다: v15 의 `TTZToQQ` 로 (부재 6 → 요청 5)

`script/das_inventory.sh` 로 UL17/UL18 v15 캠페인을 전수 나열해(`status=*`, 각 108 EXACT) 10 절의 부재 6 종을 다시 봤다.
부재 자체는 그대로다(대소문자 미스 0 건). 새로 보인 것은 **형제**다: v15 에 `TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8` 가
UL17 13,982,000 / UL18 19,816,000 ev VALID 로 있다 — v9 분석의 ttHH 목록에는 없던 샘플이다.

**결정(사용자, 2026-09-11).** Run 2 v15 는 ttZ(hadronic Z) 를 이 inclusive `TTZToQQ`(Z→bb + cc + light) 에서 취한다.
Run 3 (`TTZ-ZtoQQ-1Jets`) 와 같은 처리라 registry KEY 도 `TTZToQQ` 로 같게 두었고(`ttHH,had`), `TTZToBB` 는 `ttHH,alt`
(v9 전용) 로 내렸다. 둘을 함께 쓰면 Z→bb 가 이중 계수된다. 근거·대안은 [`03_DECISIONS.md`](03_DECISIONS.md)
D-2026-09-11-ttz-hadronic-from-ttzqq; hadronic 채널에는 bb 전용보다 완전하다(cc/light 가 mistag 로 4b 선택에 들어온다).
Z→bb 몫 ≈ 22 % → 3.0M / 4.3M ev — 부차 background 에 충분.

**영향.** ① 컨비너에게 보내는 "MiniAODv2 → NanoAODv15" 요청은 **5 종 14 dataset ≈ 108M ev**(`TTHHto4b`, `TT4b`, `TTZHTo4b`,
`TTZZTo4b`, `tHW`). ② 12 절의 enriched 사설 목록도 5 종 — TTHHGenCategoryTools D17 정정(`docs/04_decisions.md`,
`11_enriched_nanoaod.md` §3.4: 3,192 파일 / 108,323,000 ev / ≈ 23,900 core-h). ③ v9 → v15 에서 ttZ 처리가 바뀐 유일한 곳이므로
v9 대조 때 `TTZToBB`(v9) ↔ `TTZToQQ`(v15) 는 1:1 비교 대상이 아니다.

같은 날 Summer24 쪽: ttH(bb) 는 top-decay-split 3 종(각 ~29.5M) 을 쓰고, 2025 MC 캠페인은 DAS 에 없음을 확인했다 —
`ttHH/03_run3_plan.md` §4.7.

## 16. 2026-09-11 (밤) — 2016 점검: 네 era-half 가 똑같다, 요청은 28 datasets

메일을 보내기 전에 2016 을 확인했다. `das_scan.sh` 는 쓸 수 없다 — ttHH 행의 ERAS 에 2016 이 없어서 전부 조용히 건너뛴다.
그래서 ERAS 를 보지 않는 `das_inventory.sh` 로 네 캠페인을 전수 조회했다(로그 커밋됨):

| tag | campaign | EXACT | NOT_FOUND |
|---|---|---:|---:|
| `ul16pre_v15` | `RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1*` | 109 | 27 |
| `ul16post_v15` | `RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1*` | 109 | 27 |
| `ul16pre_v9` | `RunIISummer20UL16NanoAODAPVv9-106X_mcRun2_asymptotic_preVFP_v11*` | 129 | 7 |
| `ul16post_v9` | `RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17*` | 129 | 7 |

**핵심 결과: 네 Run 2 v15 캠페인(16pre, 16post, UL17, UL18)의 `NOT_FOUND` 키 집합이 diff 0 으로 완전히 같다.** 27 개의 내역은
요청 대상 5 종(`TTHHto4b`, `TT4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`) + `TTZToBB`(→ `TTZToQQ` 로 대체, 15 절) + 이름만 다른 8 종
(QCD-HT 7, `TTTW`) + CPV 워크스트림 13 종이다. 2016 v9 의 `NOT_FOUND` 7 은 전부 QCD-HT 이름 문제이고, 5 종은 2016 v9 에 다 있다.
`CASE_ONLY` 는 네 곳 모두 0.

**2016 의 5 종 (NanoAODv9 event 수).** preVFP: `TTHHTo4b` 4,950,000 / `TT4b` 4,801,000 / `TTZHTo4b`(+ext1) 2,468,000+2,500,000 /
`TTZZTo4b`(+ext1) 2,500,000+2,500,000 / `tHW` 7,430,000 = **27.1M, 7 datasets**. postVFP: 4,772,000 / 4,848,000 /
2,500,000+2,500,000 / 2,468,000+2,500,000 / 7,484,000 = **27.1M, 7 datasets**. MiniAODv2 부모 수는 아직 조회하지 않았다
(2017/2018 에서 v9 보다 1–4 % 많았다).

**사용자 결정(2026-09-11).** 요청을 full Run 2 로 넓힌다 — 5 종 × 4 era-half = **28 datasets, 약 162M event**.
`03_DECISIONS.md` D-2026-09-11-run2-scope-2016.

**registry 변경.** ttHH 62 행 전부 ERAS = `2016postVFPUL,2016preVFPUL,2017UL,2018UL`(era 당 `had` 45 행, 중복 KEY 0).
QCD-HT 는 PRIMARY 를 v9 이름(`..._TuneCP5_13TeV-madgraphMLM-pythia8`, v15 에는 어느 캠페인에도 없다)에서
`..._TuneCP5_PSWeights_13TeV-madgraph-pythia8`(네 v15 캠페인 모두 EXACT)로 바꿨다. KEY 는 그대로라 xsec·filelist·patch 이름은
영향 없다. 그 결과 **2017/2018 v15 스캔에서도 QCD-HT 가 이제 풀린다** — 09-11 오전의 "27 NOT_FOUND" 는 20 이 된다.

**남은 것.** ① ~~2016 MiniAODv2 부모 조회(요청 표의 정확한 수)~~ 17 절에서 끝남(09-16). ② `TTTW` 는 v15 에서 전하별 2 종(`TTTWminus/plus-DR1`)이라
KEY 두 개와 xsec 두 개가 필요하다(요청 대상 아님). ③ 데이터 PD(`JetHT`, `BTagCSV`)는 2016 을 넣지 않았다 — CPV 행이 쓰는
run-era 분할 패턴(`<PD>_Run2016B-ver1` …)과 DAS 스캔이 먼저다(v15 의 2016 JetHT era 문자열은 17 절에 있다). ④ 2016 의 era 별 JEC/JER·golden JSON·트리거는 analyzer 작업.

## 17. 2026-09-16: lxplus 실행 기록 도입, UL16 MiniAODv2 부모, Run 3 had 스캔, 35 인벤토리 스윕

이날부터 lxplus 의 모든 단계를 `script/runlog.sh` 로 감싼다(`script/runlogs/run_<step>_<UTC>.log` + `LEDGER.tsv`, 규약은
`script/runlogs/README.md`). 이 절의 숫자는 전부 그 로그와 산출물에서 읽었다. 실행은 사용자가 lxplus929 에서 했고 git HEAD 는
`e6eb9c3`, 결과 커밋은 `a781cb3`. 검증 원장 [`10_validation_ledger.md`](10_validation_ledger.md) 에도 같은 실행이 등재돼 있다.

| step (LEDGER) | EXIT | 소요 | 산출물 / 결과 |
|---|---:|---:|---|
| `selftest` ×2 | 0 | 0 s | 게이트 통과 (ROOT 6.40.04 호스트, dasgoclient v02.04.54, proxy 43,153 s) |
| `ul16pre_miniaodv2` | 0 | 93 s | `das_inventory_ul16pre_miniaodv2_20260916_0856.tsv` 30,897 dataset; registry 136 키 **전부 EXACT** |
| `ul16post_miniaodv2` | 0 | 109 s | `das_inventory_ul16post_miniaodv2_20260916_0857.tsv` 31,683 dataset; 136 키 전부 EXACT |
| `das_scan_2024_had` | 0 | 75 s | `das_ttHH_2024_v15_20260916_0859.log`: 65 선택(MC 61 + DATA 4), EXACT 64, NOT_FOUND 1 (`TTWJetsToLNu`) |
| `das_scan_2025_had` | 0 | 53 s | `das_ttHH_2025_v15_20260916_0900.log`: MC 부분은 2024 로그와 동일(Summer24), DATA 2025B–G |
| `discover_ul16_jetht_v15` ×2 | 0 | 0 s | JetHT UL16 v15 dataset 26 줄(BTV/JME 플레이버 포함), `_UL2016_NanoAODv15` 9 개 |
| `sweep_run3_2016` | 0 | 582 s | `inv_*.tsv` **35 개, dumped=35 skipped=0 failed=0** (cmssw-el8 안, ROOT 6.30.09) |
| `matrix_hlt` | 2 | 3 s | `--pattern '^HLT_' --partial-only`, 48 인벤토리 (2 = PARTIAL 있음, 정상) |
| `matrix_main_mc` | 2 | 1 s | `--profile main --mc`: 37 전부 존재 / 19 MC 전용 / **PARTIAL 6** (아래) |

**2016 MiniAODv2 부모 (요청 표 확정).** preVFP `TTHHTo4b` 4,950,000 / `TT4b` 4,801,000 / `TTZHTo4b` 2,496,000 + ext1 2,500,000 /
`TTZZTo4b` 2,500,000 + ext1 2,500,000 / `THW` 7,498,000 = **27,245,000 (27.2M)**. postVFP 4,798,000 / 4,848,000 / 2,500,000 + 2,500,000 /
2,468,000 + 2,500,000 / 7,484,000 = **27,098,000 (27.1M)**. 전부 VALID. 16 절의 v9 수치보다 preVFP `TTZHTo4b` +28,000, `THW` +68,000,
postVFP `TTHHTo4b` +26,000 만큼 많고(2017/2018 과 같은 방향), 합계 162.6M 은 "약 162M" 그대로다. `ttHH/04_mc_request_2026-09.md` §1 과
덱 v1.9 에 반영했다. MiniAODv2 에는 현재 registry 136 키가 **모두** 있다. v15 에 없는 20 키(5 종 + `TTZToBB` + `TTTW` + CPV 13)도
포함되므로, 우리가 5 종만 요청한 것은 가용성이 아니라 필요성의 선택이다.

**Run 3 had 스캔.** MC 60 개 dataset 전부 정확히 1 개씩 매칭(ext·복수 버전 없음). DATA 는 PD 4 개 × 8 dataset:
2024 `JetMET0/1`, `Muon0/1` 의 `Run2024C..I-MINIv6NANOv15-v1|v2` + `Run2024I-MINIv6NANOv15_v2-v1|v2`; 2025 는 `Run2025B..G-PromptReco-v1`
+ `Run2025C/F-PromptReco-v2`. **DBS 버전 꼬리(-v1/-v2)가 PD 마다 다르다**(예: 2024F/G 는 JetMET0 `-v2`, Muon0 `-v1`; 2024I 는 JetMET0 `-v2`
JetMET1 `-v1`). 따라서 DATA 행은 PD×era 별 정확한 이름을 스캔 로그에서 가져와야 하며 패턴으로 적으면 안 된다. 2024 JetMET0 합계
1,210,265,110 ev(8 dataset), 2025 JetMET0 합계 1,190,559,370 ev. RUNBOOK 의 기대값 "MC 45" 는 틀렸다(Run 2 registry 의 had 수를 옮겨 적음);
Run 3 registry 는 had 61 이다(`ttHH/README.md`).

**UL16 v15 JetHT era 문자열 (discover 로그).** preVFP: `Run2016B-HIPM_UL2016_NanoAODv15-v1`, `Run2016B-HIPM_UL2016_NanoAODv15_v2-v1`,
`Run2016C/D/E/F-HIPM_UL2016_NanoAODv15-v1`; postVFP: `Run2016F/G/H-UL2016_NanoAODv15-v1`. v9 의 `Run2016B-ver1_HIPM`/`ver2_HIPM` 구분이
v15 에서는 `-v1` 과 `_v2-v1` 두 dataset 으로 나타나는데, 둘의 run 범위는 아직 확인하지 않았다(다음 lxplus 항목). BTV/JME 플레이버는 제외.

**스윕과 교차표.** `--profile main` 의 PARTIAL 6 은 새 발견이 아니라 이미 알던 것의 확인이다: `fixedGridRhoFastjetAll`, `MET_pt`,
`Jet_jetId`, `Jet_puId`, `Electron_mvaFall17V2Iso_WP90` 는 **v9 에만** 있고(08 문서 §3.1·§3.2 의 rename/삭제), `L1PreFiringWeight_Nom` 은
**Run 2 에만** 있다(Run 3 21 인벤토리 전부 부재). 즉 UL16·UL18 v15 는 UL17 v15 와 같은 스키마 변화를 보이고, Run 3 는 거기에
prefiring 부재가 더해진다. `Jet_*` 집합은 UL18 v15 MC 와 Summer24 v15 MC 가 **완전히 같다**(PNet/UParT 태거, `Jet_puIdDisc`,
`Jet_chMultiplicity`/`neMultiplicity` 포함). 자세한 브랜치 목록 결과와 HLT 표는 `08_branch_schema_migration.md` §7.

## 18. 2026-09-17: lxplus 배치 2 (2016B 정체, 2018A run 범위, UL16 era 9 스윕, 2016 목록 재점검)

RUNBOOK §6 그대로, lxplus982, git `8690132` → 커밋 `15f377b`. 전부 EXIT 0 (LEDGER 6 행: selftest 포함).

| step | 결과 | 산출물 |
|---|---|---|
| `runs_ul16B_v15` (1 s) | `-v1`: run 272760–273017, 9,726,665 ev, 11 file. `_v2-v1`: run 273150–275376, 133,752,091 ev, 145 file. **v9 의 ver1/ver2 분할과 같고 run 이 겹치지 않는다** → Data 캠페인에 둘 다 필요 | `run_runs_ul16B_v15_20260917_060631.log` |
| `runs_2018A_firstfile` (1 s) | 첫 파일 run 316058–316719, dataset 315257–316995 → `…_2p94`/`…_1p59` 는 적어도 316719 까지 메뉴에 없음 | `run_runs_2018A_firstfile_20260917_060634.log` |
| `sweep_ul16_data_eras` (101 s) | dumped 9 / skipped 33 / failed 0. Events 1492(B ver1)…1593(F HIPM), HLT 498…560 | `inv_2016{B,Bv2,C,D,E,FHIPM,F,G,H}_v15_Data.tsv` |
| `check_2016_data_list` (5 s) | 9 era 전부 exit 3 (`Jet_jetId`/`Jet_puId` 만), dead 0 | `run_check_2016_data_list_20260917_060836.log` |
| `check_cpv_data_2016` (5 s) | 9 era 전부 exit 0 | `run_check_cpv_data_2016_20260917_060842.log` |

반영: manifest 머리(B 두 dataset 의 run·event 수), `ttHH/04_mc_request_2026-09.md` §4(v15 JetHT 2016 dataset 9 개), `branch_hadronic_2016_v15_Data.txt`·
`branch_CPV_Run2_Data_v15.txt` 머리, `08` §7.1·§7.3·§7.4·§7.5, `10_validation_ledger.md` V21–V25, `01_STATUS.md` 22l-2·22n·행동 표.
남은 lxplus 항목은 2018A 의 메뉴 전환 run bracket(RUNBOOK §7)이다.

## 19. 2026-09-18: lxplus 배치 3 (2018 메뉴 전환 run, TTTW·BTagCSV DAS, 2024 PINNED 스캔, v9 인벤토리 16 + diff 16)

RUNBOOK §7. lxplus988, HEAD `1b576b9`, 커밋 `3c71cab`(09-19 맥 pull). 세 번 돌았다: ① 06:03 UTC 컨테이너 밖 [2b] 3 건 전부 EXIT 0;
② 06:04 컨테이너 안 4 건이 **cmsenv 없이** 돌아 EXIT 1/1/1/0 (여러 줄 붙여넣기의 호스트 셸 버퍼링, `02_CHANGELOG.md` 09-18 (1));
③ 07:22 같은 4 건을 cmsenv 로 다시 돌려 전부 EXIT 0. 09-19 07:42 의 재실행(HEAD `6c0b5d4`)은 proxy 만료로 probe EXIT 3, sweep EXIT 2 였고 diff 만
다시 돌아 09-18 과 byte-identical 한 요약을 냈다. LEDGER 에는 세 번이 다 남아 있다(실패 행 삭제 없음).

| step | 결과 | 산출물 |
|---|---|---|
| `probe_2018A_sixjet` (99 s) | DAS run 127 개(315257–316995), 316700 부터 2 개마다 12 run → 파일 9 개(합쳐 315257–316995 덮음). **9 파일 전부** `_2p2`·`_1p5` 있음, `_2p94`·`_1p59` 없음 | `run_probe_2018A_sixjet_20260918_072158.log` |
| `probe_2018B_sixjet` (111 s) | DAS run 61 개(317080–319310), 8 개마다 9 run → 파일 6 개. **6 파일 전부** 네 경로 있음 | `run_probe_2018B_sixjet_20260918_072338.log` |
| `sweep_v9_2016_2018` (71 s) | dumped 16 / skipped 0 / failed 0. MC: UL16 두 half Events 1504 / HLT 601, UL18 1628 / 651. Data 2016: Events 1286(B ver1)–1363(G), HLT 498–554; 2018: A 1749/664, B 1567/685, C 1542/642, D 1561/657 | `inv_2016{preVFP,postVFP}_v9_MC.tsv`, `inv_2018UL_v9_MC.tsv`, `inv_2016{B1,B2,C,D,E,FHIPM,F,G,H}_v9_Data.tsv`, `inv_2018{A,B,C,D}_v9_Data.tsv`, `run_sweep_v9_2016_2018_20260918_072530.log` |
| `diff_v9_v15_2016_2018` (3 s) | 16 쌍 전부 exit 4(차이 있음). MC 2016 두 half 127/370/86 = 2017 과 동일, 2018 129/396/86; Data 12 era 121–129 / 328–360 / 58, 2018A 378/333/58 | `diff_v9_v15_{2016preVFP,2016postVFP,2018UL}_MC.txt`, `diff_v9_v15_{2016B,2016Bv2,...,2018D}_Data.txt`, `run_diff_v9_v15_2016_2018_20260918_072642.log` |
| `probe_tttw_v15` (2 s) | TTTWminus/plus v15 8 dataset(`..._v1-v1`) 의 summary: 1.63M–3.60M ev(표는 registry 주석) | `run_probe_tttw_v15_20260918_060303.log` |
| `discover_ul16_btagcsv_v15` (1 s) | BTagCSV UL16 v15 9 dataset, JetHT 와 같은 era 구조 | `run_discover_ul16_btagcsv_v15_20260918_060305.log` |
| `das_scan_2024_had_pinned` (30 s) | MC 61 + DATA 4 → RESULT 65 = EXACT 64 + **PINNED 1**(`TTWJetsToLNu`), NOT_FOUND 0 | `script/das/das_ttHH_2024_v15_20260918_0803.log`, `run_das_scan_2024_had_pinned_20260918_060306.log` |

**해석은 `08_branch_schema_migration.md` §3.5(era 별 diff)·§7.4(2018 메뉴 전환: 2018A 전체에 새 쌍 없음, 진입 run 317509 는 AN2019_094 대조로)** 에, 검증 행은 `10_validation_ledger.md` V27–V33 에 있다.
2024 스캔 로그로 처음 낸 Run 3 config 초안 2 개(MC·Data 분리, `build_from_scan_log.py --data-branch-file`, 09-19)는 `script/drafts/config_das_ttHH_2024_v15_20260918_0803_{MC,Data}.yaml.draft`
와 review 표 `script/drafts/review_das_ttHH_2024_v15_20260918_0803.{md,tsv}`; 제출 전 사용자 검토(`ttHH/03_run3_plan.md` §6 4).
남은 lxplus 항목은 TTTW± 8 dataset 의 DBS status 한 줄(RUNBOOK §8).

## 20. 2026-09-22: lxplus 배치 4 (TTTW± DBS status, 2025 had 재스캔 with PINNED)

RUNBOOK §8. lxplus956, HEAD `d81f2ad` → 커밋 `1a9f20d`. 컨테이너 없음, 두 단계 전부 EXIT 0.

| step | 결과 | 산출물 |
|---|---|---|
| `probe_tttw_v15_status` (3 s, `das_status.sh` 첫 실제 사용) | 6 dataset 전부 **VALID**, nevents 09-18 과 동일(TTTWminus UL16 1,700,000 / UL17 3,291,000 / UL18 3,485,000; TTTWplus 1,700,000 / 3,389,000 / 3,597,000). **UL16APV 2 개는 안 나왔다**: RUNBOOK §8 의 패턴 `RunIISummer20UL1*NanoAODv15-150X*` 가 `NanoAODAPVv15` 를 못 잡는다(09-18 의 `NanoAOD*v15` 에서 `*` 하나를 빠뜨림; AI 실수). **같은 날 §9 로 보정**: `run_probe_tttw_v15_status_apv_20260922_061821.log`, 둘 다 VALID(1,630,000 / 4, 1,700,000 / 5) → 8/8 VALID, 커밋 `6e276c1` | `run_probe_tttw_v15_status_20260922_055553.log` |
| `das_scan_2025_had_pinned` (84 s) | MC 61 + DATA 4 → RESULT 65 = EXACT 64 + PINNED 1, NOT_FOUND 0 | `das_ttHH_2025_v15_20260922_0755.log`, `run_das_scan_2025_had_pinned_20260922_055557.log` |

그 로그로 2025 config 초안 2 개를 냈다(`build_from_scan_log.py --data-branch-file`, 09-22): `config_das_ttHH_2025_v15_20260922_0755_{MC,Data}.yaml.draft`,
review `review_das_ttHH_2025_v15_20260922_0755.{md,tsv}`. **MC 초안의 61 dataset 은 2024 MC 초안과 byte 단위로 같다**(머리·jobID 만 다름): 2025 MC 캠페인이
없어 Summer24 를 같이 쓰기 때문이며, 따라서 MC ntuple 은 한 번만 만들고 2025 는 Data 초안만 제출 대상이다(`ttHH/03` §6 1, STATUS 표 18). Data 32 행 =
JetMET0/1 + Muon0/1 × PromptReco B~G(C·F 는 `-v1`+`-v2`), 6,607,369,332 ev, 18,494 files, 최대 1,166 files(guard OK). 원장 V35–V36.

## 21. 2026-09-23: lxplus 배치 6 (2018UL v15 + 2024 hadronic 첫 생산: 스캔 → config 4 → 로컬 점검 4 → preflight 6 → 파일럿 2 task 제출)

RUNBOOK §10. lxplus963. 컨테이너 밖 [2] 는 HEAD `8ab47c0` 에서 돌아 커밋 `3cb789b`, 컨테이너 안 [4] 는 `3cb789b` 에서 돌아 커밋 `72bd16f`.
맥 쪽 wrapper 수정은 커밋 `c7cbe95`(아래). LEDGER 9 행(스캔 2, build 2, 로컬 점검 4, 요약 1)은 전부 EXIT 0. preflight 와 제출은 crab 명령이라
runlog 가 `script/runlogs/nocommit/` 로 가고 LEDGER 행이 없다. preflight 는 `pf_*.txt` 복사본이 증거다.

| step | 결과 | 산출물 |
|---|---|---|
| `das_scan_2024_had_final` (81 s) | RESULT 64 = EXACT 64 (MC 60 + DATA 4), NOT_FOUND 0. 09-18 스캔의 review 표와 비교하면 `TTWJetsToLNu` 한 행만 빠졌고(registry 행 주석, 09-22 결정) 나머지 92 행은 dataset·nevents·nfiles 가 같다 | `script/das/das_ttHH_2024_v15_20260923_0851.log`, `run_das_scan_2024_had_final_20260923_065146.log` |
| `das_scan_2018UL_had_v15` (75 s) | RESULT 48 = EXACT 41 + RELAXED 2 (JetHT, SingleMuon) + NOT_FOUND 5 (`TTHHto4b`, `tHW`, `TTZHTo4b`, `TTZZTo4b`, `TT4b`; 예상한 5 종 그대로) | `script/das/das_ttHH_2018UL_v15_20260923_0853.log`, `run_das_scan_2018UL_had_v15_20260923_065307.log` |
| `build_2024_had` | MC 60 키 4,089,997,458 ev / 19,136 files / 입력 13.86 TB, Data 32 키 5,958,480,379 ev / 7,811 files; 최대 2,532 files (job-count guard OK) | `script/drafts/review_das_ttHH_2024_v15_20260923_0851.{md,tsv}`, `script/drafts/config_das_ttHH_2024_v15_20260923_0851_{MC,Data}.yaml.draft`, `run_build_2024_had_20260923_072131.log` |
| `build_2018UL_had` (`--allow-notfound` 첫 실제 사용) | MC 42 키 1,777,107,873 ev / 2,277 files / 입력 5.35 TB, Data 8 키 1,660,950,742 ev / 1,466 files; 최대 589 files (guard OK); 부재 5 종은 MC config 의 주석 블록 | `script/drafts/review_das_ttHH_2018UL_v15_20260923_0853.{md,tsv}`, `script/drafts/config_das_ttHH_2018UL_v15_20260923_0853_{MC,Data}.yaml.draft`, `run_build_2018UL_had_20260923_072132.log` |
| crabConfig 4 | 초안을 그대로 복사(네 쌍 `cmp` 동일) | `crabConfig/config_ttHH{2024,2018UL}_v15_had_{MC,Data}.yaml` (`3cb789b`) |
| `localcheck_{2018,2024}_{MC,Data}` (28 / 39 / 55 / 63 s; cmssw-el8 + cmsenv, ROOT 6.30.09) | 각 dataset 첫 파일에서 500 event, `modules.noop` + 해당 v15 목록(2018 MC `TTToHadronic`, 2018 Data `JetHT` 2018A, 2024 MC `TTto4Q`, 2024 Data `JetMET0` 2024C). 4 개 EXIT 0, `Error in <` 0 줄 | `run_localcheck_{2018_MC_20260923_073458,2018_Data_20260923_073528,2024_MC_20260923_073608,2024_Data_20260923_073704}.log` |
| `localcheck_summary` | branches / HLT_: 2018 MC 717 / 325, 2018 Data 627 / 302, 2024 MC 703 / 323, 2024 Data 638 / 315. run/lumi/event 는 넷 다 y. MC 두 개는 genWeight·genTtbarId·Runs.genEventSumw 가 y, Data 두 개는 셋 다 n | `run_localcheck_summary_20260923_073808.log` |
| preflight 4 | 2018UL MC 42: 33 PASS / 1 WARN; 2018UL Data 8: 31 / 3; 2024 MC 60: 33 / 1; 2024 Data 32: 31 / 3. FAIL 0 전부. WARN 은 proxy 11.4 h 와 Data 의 `genWeight`·`genTtbarId` absent(Data 에는 원래 없다). existing CRAB projects 는 전부 none | `script/runlogs/pf_config_ttHH{2018UL,2024}_v15_had_{MC,Data}_20260923_*.log.txt` |
| 파일럿 config 2 + preflight 2 | 전체 config 에서 한 행씩 떼어 jobID·output_base 에 `_pilot`: `ZZ` (4,800,000 ev, 76 files), `JetMET0_Run2024H-MINIv6NANOv15-v2` (55,794,457 ev, 82 files; 둘 다 09-23 2024 review 의 행). preflight 33 / 1, 31 / 3, FAIL 0 | `crabConfig/config_ttHH2024_v15_had_pilot{MC,Data}.yaml`, `script/runlogs/pf_config_ttHH2024_v15_had_pilot{MC,Data}_20260923_*.log.txt` (`72bd16f`) |
| 파일럿 제출 | 1 차(07:59 UTC)는 myproxy 재위임의 pass phrase 프롬프트가 붙여 넣은 다음 줄을 가져가 실패했고 wrapper 는 exit 0 이었다. 재시도(08:18~08:25 UTC): `.requestcache` 없는 `crab_ZZ` 정리 → `crab createmyproxy --days 30`(여기서만 pass phrase) → 두 task 제출: `260923_081917:junghyun_crab_ZZ`, `260923_082524:junghyun_crab_JetMET0_Run2024H_MINIv6NANOv15_v2` | transcript 는 `script/runlogs/nocommit/` 에만 있다(커밋 금지). 경위와 CRABClient 근거: `05_troubleshooting.md` A22 |

**2018UL 대조.** config 의 50 dataset 중 49 개는 09-03 스캔(`script/das/das_ttHH_2018UL_v15_20260903_1016.log`)의 DS 행과 dataset·nevents·nfiles 가
같다. 나머지 1 개 `TTZToQQ`(19,816,000 ev, 34 files)는 09-03 뒤에 registry 에 들어온 키라 그 스캔에 없다(D-2026-09-11-ttz). 09-23 로그의 DS 행이
88 개로 09-03 의 132 개보다 적은 것은 `--workstream had`(DY·W+jets 44 행은 `lep`) 때문이고, 그 밖에 `QCD_HT2000toInf` 의 JMENano 판 1 행이 빠지고
`TTZToQQ` 1 행이 늘었다(JMENano·BTVNano 판은 builder 가 원래 빼므로 config 와 무관). TTTW 는 두 키(`TTTWminus`/`TTTWplus`)로 같은 두 dataset 이다.

**총량과 용량.** 네 config 합계 13,486,536,452 ev, 30,690 files = job 30,690 개(units_per_job 1; 네 review 표의 total 합). 출력 추정 20~26 TB 는
파일럿 출력의 kB/event 로 다시 잰다(RUNBOOK §10 [7b]). 500 event 로컬 점검 파일은 6.6~9.5 kB/event(09-23 사용자가 붙인 `ls -l localcheck_v15/out_*.root`)라
고정 오버헤드가 커서 추정에 쓰지 않는다.

**wrapper.** 1 차 제출 실패로 `crab/submit_crab.py` 의 결함 셋(실패해도 exit 0, `.requestcache` 없는 작업 디렉토리를 기존 task 로 보고 resubmit,
`--kill` 이 kill 전에 submit/resubmit)이 드러났고 맥 커밋 `c7cbe95` 에서 고쳤다(오프라인 mock 테스트 `script/test_submit_crab_mock.py`, 원장 V42).
파일럿 두 task 는 옛 wrapper 로 제출됐다. lxplus 는 전체 제출 [8] 전에 이 커밋을 pull 한다.

**파일럿 결과 (09-23~24, RUNBOOK §10 [7]).** job 상태는 lxplus `--report` 세 번(수정한 wrapper 의 첫 실사용: 매번 exit 0 과
`SUMMARY ... RESULT: OK`, 자격 증명 grep 0):

| 확인 (UTC) | `ZZ` (76 job) | `JetMET0_Run2024H` (82 job) |
|---|---|---|
| 09-23 08:50 | transferring 76 | running 72, transferring 10 |
| 09-23 09:35 | done 72, transferring 4 | done 11, running 44, transferring 27 |
| 09-24 13:46 | done 76 | done 82 |

fail 은 세 번 모두 0. report 는 확인 시점의 스냅샷이라 Data 가 실제로 끝난 시각은 두 번째와 세 번째 사이 어딘가다.
증거: `script/runlogs/crab_report_pilot{MC,Data}_20260923_{1050,1051,1135}.txt`, `..._20260924_1546.txt` (파일 이름의 시각은 lxplus 현지 CEST).

출력 점검을 처음에는 lxplus 에서 `crab getoutput --jobids=1` 로 하려 했으나 `results/` 가 비었다. CRABClient v3.260630 의 getoutput 은 모든 파일을
`gfal-copy` 로 `root://cms-xrd-global.cern.ch/<LFN>` 에서 받는다(`Commands/getcommand.py` 의 `insertXrootPfns`, `Commands/remote_copy.py`); RUNBOOK 에
"AAA 와 무관" 이라고 적은 것은 틀렸다(워크스페이스 `AI_LIMITS_AND_PROTOCOL.md` §5 실패 7). 그래서 KNU(cms01, CMSSW_14_2_1 cmsenv, ROOT 6.30/09)에서
`/pnfs` 의 파일럿 출력 158 개를 전부 직접 열었다(명령은 RUNBOOK §10 [7]). 출력 전문:

```
ttHH2024_v15_had_MC_v1_pilot | files 76 | events 4800000 (DAS 4800000) | bytes 5068009312 | 1.056 kB/event | unreadable none
   forgedNtuple_1.root | branches 674 | HLT_ 323 | non-HLT 351 | LHE* 0 | run/lumi/event y | genWeight y | genTtbarId y | Runs.genEventSumw y
ttHH2024_v15_had_Data_v1_pilot | files 82 | events 55794457 (DAS 55794457) | bytes 43503667199 | 0.780 kB/event | unreadable none
   forgedNtuple_1.root | branches 646 | HLT_ 323 | non-HLT 323 | LHE* 0 | run/lumi/event y | genWeight n | genTtbarId n | Runs.genEventSumw n
```

**판정: 두 파일럿 모두 통과.** event 합계가 DAS 와 같다(noop 통과이므로 event 손실 0), 열리지 않는 파일 0. MC 는 HLT_ 323 이 09-23 로컬 점검(`TTto4Q`)과
같고, branches 가 703 → 674 로 29 개 적은데 줄어든 29 개가 전부 non-HLT(380 → 351)이며 `ZZ` 에는 LHE 계열이 0 개다(pythia 단독 표본이라 LHE 정보가
없다). 이 29 개가 로컬 파일의 LHE 계열과 이름까지 같은지는 따로 확인하지 않았다. Data 는 non-HLT 323 이 로컬(638 − 315)과 같고, HLT_ 는 2024C 315 →
2024H 323 으로 8 개 많다(HLT 집합은 파일의 run 범위가 정한다, `08` §3.2b). gen 세 열은 MC y, Data n 으로 기대대로다.

**크기와 전체 추정.** MC `ZZ` 1.056 kB/event(파일당 66.7 MB), Data `JetMET0` 2024H 0.780 kB/event(파일당 530.5 MB). 09-23 review 의 event 수로:

| config | events | 추정 |
|---|---:|---:|
| 2018UL MC | 1,777,107,873 | 1.88~3.46 TB |
| 2018UL Data | 1,660,950,742 | 1.30 TB |
| 2024 MC | 4,089,997,458 | 4.32~7.97 TB |
| 2024 Data | 5,958,480,379 | 4.65 TB |
| **합계** | **13,486,536,452** | **12.1~17.4 TB** |

MC 의 하한은 `ZZ` 값(LHE 없음), 상한은 8b 절의 1.948 kB/event(2017 hadronic 목록, ttbar 20,000 event)다. 양이 많은 ttbar·QCD 는 LHE 가 있고
jet 이 많아 상한 쪽이 현실적이다. Data 는 2024H JetMET0 한 era 의 값을 모든 Data PD 에 썼다(Muon PD 는 jet 이 적어 이보다 작을 것으로 본다).
09-22 의 20~26 TB 추정은 모든 event 에 1.5~1.95 kB/event 를 쓴 값이라 Data 실측으로 대체된다. 파일럿 출력 48.6 GB 는 전체 생산이 같은 두
dataset 을 다른 jobID·output_base 로 다시 만들므로, 전체 생산을 확인한 뒤 지워도 된다.

검증 행은 `10_validation_ledger.md` V38–V44. 남은 것: T3_KR_KNU `/store/user/junghyun` 여유 확인(RUNBOOK §10 [7b]) → [8] 전체 4 config 제출.
