# Branch 스키마 검증 절차 + NanoAOD v9 → v15 실측 결과

이 문서는 두 가지를 담습니다.

1. **절차** — branch 목록을 만들거나 고칠 때 **반드시** 거쳐야 하는 검증 과정과,
   그대로 복사해 쓸 수 있는 동작 확인된 명령어. NanoAOD 버전이 바뀔 때마다
   (v9→v15, 나중에 Run3) 이 절차를 재사용합니다.
2. **v9 → v15 실측 결과** — 2026-08-27에 실제 파일로 측정한 스키마 차이와,
   그것이 각 workstream에 주는 영향.

관련: [`06_nanoaod_branch_access.md`](06_nanoaod_branch_access.md) (PyROOT read
헬퍼), [`07_DeveloperGuideline.md`](07_DeveloperGuideline.md) Rule 8 (의무 조항),
`script/dump_branch_inventory.py`, `script/check_branchlist.py`.

**언제 무엇을 실행했고 로그가 어땠는지**는 여기가 아니라
[`09_v15_migration_log.md`](09_v15_migration_log.md) 에 있습니다.

---

## 1. 왜 이 절차가 필요한가 — 실패가 양방향으로 조용하다

branch 목록은 틀려도 크래시가 나지 않습니다. 두 방향 모두 조용히 잘못된 결과를
냅니다.

| 실수 | 증상 | 결과 |
|---|---|---|
| `keep` 패턴이 아무것도 매치하지 않음 | ROOT `SetBranchStatus` 에러가 **job당 1줄** | 로그에 묻혀 안 보임 |
| 소비자가 읽는 branch를 목록이 drop | 없음 | `eventBuffer`가 0/empty로 기본값 처리 |
| 파일 자체에 branch가 없음 (버전 차이) | 요약 한 줄 | `Jet_puId` 누락 → 50 GeV 미만 jet 전부 컷<br>`genTtbarId` 누락 → 모든 ttbar가 tt+LF |

그래서 **branch 목록은 절대 기억이나 옛 인벤토리로 쓰지 않습니다.** 실제 파일의
스키마를 덤프한 뒤 그것에 대고 검사합니다.

## 2. 절차 (6단계)

### Step 0 — 셸 준비: `set +H` (⚠ 먼저 이것부터)

```bash
set +H
```

대화형 bash는 **큰따옴표 안에서도 history expansion을 수행합니다.** 따라서
`echo "!! something"` 의 `!!` 가 직전 명령 전체로 치환되어, 붙여넣은 명령이
조용히 다른 명령으로 바뀝니다. 함수 정의 안에서 터지면 뒤따르는 `}` 까지
연쇄로 깨져 `syntax error near unexpected token` 이 납니다.

2026-08-27에 이 문제로 두 번 시간을 잃었습니다. 규칙:

- 세션 시작 시 `set +H` (또는 `~/.bashrc` 에 넣기)
- 이 문서와 프롬프트의 예제에서는 경고 표시로 `!!` 대신 `ERROR:` / `>>` /
  `⚠` 를 씁니다
- 여러 줄 함수 정의를 터미널에 붙여넣지 말고, 재사용할 것은 `script/` 에
  파일로 두십시오

### Step 0b — proxy

```bash
voms-proxy-info -e || voms-proxy-init -voms cms -rfc -valid 192:00
```

`xrdcp`가 `cryptossl_X509CreateProxy: unable to load EEC private key` +
`[FATAL] Redirect limit has been reached` 로 죽으면 proxy가 없는 것입니다.
(`unable to load EEC private key`는 `userkey.pem` 문제처럼 보이지만 실제로는
프록시가 없어 새로 만들려다 실패한 것 — `voms-proxy-init`만 하면 됩니다.)

### Step 1 — DAS에서 데이터셋과 파일 하나 찾기

```bash
dasgoclient -query="dataset=/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-*/NANOAODSIM"
```

⚠ **plain 캠페인을 고르십시오.** `JMENano` / `BTVNano` / `PFNano` 접두가 붙은
flavour 변종은 branch 구성이 다릅니다. 위 쿼리는 3개를 돌려주는데 스키마 기준으로
쓸 것은 첫 번째뿐입니다:

```
/…/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2/NANOAODSIM        ← 이것
/…/RunIISummer20UL17NanoAODv15-20UL17JMENano_150X_mc2017_realistic_v1-v1/…   ← 아님
/…/RunIISummer20UL17NanoAODv15-BTVNanoV15_150X_mc2017_realistic_v1-v3/…      ← 아님
```

### Step 2 — /tmp로 xrdcp (⚠ 이 단계를 건너뛰지 마십시오)

```bash
DS='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2/NANOAODSIM'
LFN=$(dasgoclient -query="file dataset=$DS" | head -1)
[ -n "$LFN" ] || { echo "LFN EMPTY -- 중단"; }
xrdcp -f root://cms-xrd-global.cern.ch/$LFN /tmp/nano_v15_local.root
ls -lh /tmp/nano_v15_local.root
```

⚠ lxplus의 `/tmp`는 노드별이고 정리됩니다. 세션이 바뀌면 다시 받으십시오
(인벤토리 TSV는 AFS의 repo 안이라 남습니다).

**왜 로컬 복사인가 — 측정값 (2026-08-27, lxplus8, 2000 events):**

| 입력 | 모듈 | event loop | Rate | user+sys |
|---|---|---|---|---|
| XRootD (WAN) | `topCPVCategorizer` | 929.8 s | **2.2 Hz** | — |
| XRootD (WAN) | `noop` | 405.0 s | 4.9 Hz | 15.9 s (CPU 3.8 %) |
| /tmp 로컬 | `noop` | 8.7 s | **230.2 Hz** | 12.556 s |
| /tmp 로컬 | `topCPVCategorizer` | 10.0 s | **199.5 Hz** | 13.885 s |

lxplus에서 XRootD로 직접 읽으면 **90배 느립니다.** CPU 사용률 3.8 %가 말해주듯
전부 WAN I/O 대기입니다. 2.322 GB `xrdcp`는 46.6 MB/s로 ~50초면 끝나므로 복사가
항상 이득입니다.

동시에 이 표가 **모듈 자체의 비용**을 분리해 줍니다: 13.885 − 12.556 =
**1.33 s / 2000 events = 0.66 ms/event** (순수 복사 대비 CPU +11 %, rate −13 %).
1.126 M event 파일 하나가 ~1.57 h → CRAB wall-time(기본 21.9 h) 안입니다.

⚠ **"느리다"를 모듈 탓으로 돌리기 전에 `noop`으로 baseline을 재십시오.**
`time`의 `user+sys`는 파일이 어디 있든 무관하므로 이 값만이 비교 가능한 숫자입니다.
`real`은 page cache 상태에 좌우됩니다 (실제로 위 측정에서 local-noop의 `real`
35.2 s > local-module의 16.1 s 였는데, 앞 실행이 방금 쓴 2.3 GB를 cold cache로
읽었기 때문입니다).

### Step 3 — 인벤토리 덤프

```bash
mkdir -p script/inventory
python3 script/dump_branch_inventory.py /tmp/nano_v15_local.root \
    --label 2017UL_v15_MC -o script/inventory/inv_2017UL_v15_MC.tsv
```

### Step 4 — 두 버전 diff

```bash
python3 script/dump_branch_inventory.py --diff \
    script/inventory/inv_2017UL_v9_MC.tsv \
    script/inventory/inv_2017UL_v15_MC.tsv | tee script/inventory/diff_v9_v15_2017UL_MC.txt
```

그다음 **내 모듈이 실제로 읽는 이름만** 좁혀서 봅니다. 전체 diff는 수백 줄이라
그대로 보면 놓칩니다:

```bash
grep -E '(GenPart_|GenJet_|GenMET_|PSWeight|nGenPart|nGenJet|nPSWeight|luminosityBlock)' \
    script/inventory/diff_v9_v15_2017UL_MC.txt
```

⚠ diff의 `## Rename candidates` 블록은 **휴리스틱이며 틀립니다.** 2026-08-27
실행에서 `MET_pt -> FiducialMET_pt`로 추측했지만 실제 대응은 `MET_pt -> PFMET_pt`
이고 `FiducialMET_pt`는 `MET_fiducialGenPt`의 새 이름입니다. 반드시 손으로
확인하십시오.

### Step 5 — 목록 × 스키마 × 소비자 교차 검사

```bash
python3 script/check_branchlist.py branches/branch_CPV_Run2_MC_v15.txt \
    --inventory script/inventory/inv_2017UL_v15_MC.tsv --mc --profile cpv; echo "rc=$?"
```

세 절이 나옵니다:

- **(A)** 아무것도 매치 못 하는 패턴 → job당 ROOT 에러
- **(B)** 소비자가 읽는데 목록이 drop하는 branch
- **(C)** 파일 자체에 없는 branch (버전 차이 — 목록으로는 못 고침)

exit code: `0` OK / `2` (B) 위반 / `3` (C) 위반 / `4` (A) 위반.

⚠ **(C)는 입력 스키마 검사입니다.** 모듈이 *만드는* branch(`TopCPVCat_*` 등)는
입력 NanoAOD에 있을 리 없으므로 `produced` 플래그로 (C)에서 제외됩니다 — 제외
개수가 출력에 찍힙니다. 새 profile을 추가할 때 이 구분을 지키십시오.
(2026-08-27 이전에는 이 구분이 없어 6개를 오탐했습니다.)

### Step 6 — 실제로 돌려보기

스키마 검사가 통과해도 **reader 타입 지원**은 별개입니다. v15는 `UShort_t` /
`Short_t`를 대거 도입하는데, NanoAODTools의 `arrayReader`가 그 템플릿을 갖고
있는지는 돌려봐야만 압니다.

```bash
python3 script/run_postproc.py /tmp/nano_v15_local.root \
    -I modules.topCPVCategorizer:MODULES \
    -b branches/branch_CPV_Run2_MC_v15.txt \
    -N 2000 -o local_v15_module.root 2>&1 | tail -40
```

---

## 3. v9 → v15 실측 결과 (2017UL MC, 2026-08-27)

**소스**

| | |
|---|---|
| v9 | `/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM` (2.322 GB, Events 1666 branches) |
| v15 | `…/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2/NANOAODSIM` (2.709 GB, Events 1903 branches) |
| 산출물 | `script/inventory/inv_2017UL_v{9,15}_MC.tsv`, `script/inventory/diff_v9_v15_2017UL_MC.txt` |

**총계: 127 removed / 370 added / 86 retyped** (Events 기준 added 364 + Runs 2 +
LuminosityBlocks 4).

### 3.1 확인된 rename (손으로 검증)

| v9 | v15 |
|---|---|
| `MET_*` | `PFMET_*` |
| `MET_fiducialGenPt` / `…Phi` | `FiducialMET_pt` / `FiducialMET_phi` |
| `RawMET_*` | `RawPFMET_*` |
| `TkMET_*` | `TrkMET_*` |
| `fixedGridRhoFastjet*` | `Rho_fixedGridRhoFastjet*` |
| `Electron_mvaFall17V2Iso_*` | `Electron_mvaIso_*` |
| `Electron_mvaFall17V2noIso_*` | `Electron_mvaNoIso_*` |
| `Tau_idDeepTau2017v2p1VS*` | `Tau_idDeepTau2018v2p5VS*` |

### 3.2 대체 없이 사라진 것 (⚠ 위험)

`ChsMET_*` · `Jet_puId` · `Jet_jetId` · `FatJet_jetId` · `Jet_btagDeepB` ·
`Jet_btagCSVV2` · `Jet_btagDeepCvB/CvL` · `Jet_qgl` · `Jet_bRegCorr/Res` ·
`Jet_cRegCorr/Res` · `Jet_chFPV0EF` · `*_cleanmask` · `Electron_eCorr` ·
`Electron_mvaTTH` · `Muon_mvaTTH` · `Photon_mass` · `Photon_charge` ·
`Photon_pdgId` · `btagWeight_*` · FatJet `deepTag*` / `particleNetMD_*` 전부

`Jet_btagDeepFlavB`는 **생존** (ttHH b-tagger 무사).

### 3.3 타입 변경의 지배적 패턴

- 모든 count branch: `UInt_t → Int_t` (`nJet`, `nGenPart`, `nGenJet`, `nPSWeight`, …)
- 인덱스 branch: `Int_t → Short_t` (`*_genPartIdx*`, `Jet_genJetIdx`, `*_jetIdx`, …)
- 작은 정수/플래그: `Int_t → UChar_t` (`Jet_hadronFlavour`, `Electron_cutBased`,
  `PV_npvs`, `Muon_nStations`, …)
- `GenPart_statusFlags`: `Int_t → UShort_t`
- `TrigObj_filterBits`: `Int_t → ULong64_t`, `TrigObj_id`: `Int_t → UShort_t`

⚠ `Int_t → UChar_t` 전환은 [`06_nanoaod_branch_access.md`](06_nanoaod_branch_access.md)
Pitfall 1의 함정을 **새로운 branch들로 확대**합니다. v9에서 `to_int` 없이 읽어도
됐던 것들이 v15에서는 bytes로 옵니다.

### 3.4 workstream별 영향

**CPV (`modules/topCPVCategorizer.py`) — 이름 변경 0건, 삭제 0건. 안전.**

읽는 집합 전체가 v15에 그대로 존재합니다. 타입만 바뀝니다:

| branch | v9 → v15 | 판정 |
|---|---|---|
| `GenPart_statusFlags` | Int_t → UShort_t | bit 7(`isHardProcess`)/13(`isLastCopy`) 사용 → 16비트 안, **잘림 없음** |
| `GenPart_genPartIdxMother` | Int_t → Short_t | −1 sentinel 유효, `nGenPart` ≪ 32767 |
| `nGenPart`/`nGenJet`/`nGenVisTau`/`nPSWeight` | UInt_t → Int_t | 무해 |
| `GenJet_partonFlavour` (validator용) | Int_t → Short_t | 무해 |
| `GenJet_hadronFlavour` | **불변 (UChar_t)** | ⇒ `to_int` **계속 필요** |
| `GenPart_pdgId`/`status`/`pt`/`eta`/`phi`/`mass`, `GenJet_pt/eta/phi/mass`, `GenMET_*`, `PSWeight` | 불변 | — |

새로 생긴 gen 컬럼: `GenJet_nBHadrons` / `GenJet_nCHadrons` (UChar_t),
`GenPart_iso`, `GenJetAK8_n{B,C}Hadrons`, `TrackGenJetAK4_*`, `GenProton_*`.
`Runs`에 `PSSumw`/`nPSSumw`, `LuminosityBlocks`에 `GenFilter_*` 추가.

⚠ **standalone C++ `TopCPVGenCategorizer`는 v15를 그대로 읽을 수 없습니다.**
`GenPart_statusFlags`를 `Int_t`로 `SetBranchAddress` 하므로 v15의 `UShort_t`에서
크래시 없이 **조용한 쓰레기 값**이 나옵니다. 즉 v9에서 통과한 Gate 4
(`script/validate_topcpvcat.py`, forged `Events` vs standalone `GenCatTree`)를
v15에서 그대로 반복할 수 없습니다. v15 검증은 `module(v9)` vs `module(v15)`
이벤트 매칭 비교로 해야 합니다.

**ttHH → 4b — jet ID / PU ID를 재계산해야 하지만 재료는 전부 있습니다.**

2026-08-27 v15 인벤토리 확인 결과 (`awk` 로 `Jet_*` 직접 조회):

| 없어진 것 | 대체 경로 | 상태 |
|---|---|---|
| `Jet_puId` (WP 비트맵, Int_t) | **`Jet_puIdDisc` (Float_t) 는 v9·v15 양쪽에 존재** | WP 임계값을 직접 적용 |
| `Jet_jetId` (Int_t) | v15에 `passJetIdTight` 류도 **없음**. PF energy fraction + multiplicity 로 재계산 | 재료 15/15 확인 |

재계산 재료 (v15 실측, 전부 존재):

```
Jet_nConstituents   UChar_t   <- to_int 필요
Jet_chMultiplicity  UChar_t   <- to_int 필요 (v15 신규)
Jet_neMultiplicity  UChar_t   <- to_int 필요 (v15 신규)
Jet_neHEF  Jet_neEmEF  Jet_chHEF  Jet_chEmEF  Jet_muEF   Float_t
Jet_hfHEF  Jet_hfEmEF                                     Float_t
Jet_puIdDisc  Jet_area  Jet_pt  Jet_eta  Jet_btagDeepFlavB  Float_t
```

즉 중앙 NanoAOD가 **미리 계산된 플래그를 빼고 재료를 준** 형태입니다 —
`Jet_chMultiplicity` / `Jet_neMultiplicity` 가 v15에서 새로 추가된 것이 그
방향을 뒷받침합니다 (v9에서는 jetId 계산에 필요한 multiplicity가 노출되지
않았습니다).

⚠ 새 multiplicity 3개가 모두 `UChar_t` 입니다.
[`06_nanoaod_branch_access.md`](06_nanoaod_branch_access.md) Pitfall 1에 따라
반드시 `to_int` 를 거쳐야 합니다 — 안 하면 jet ID 컷이 조용히 전부 실패합니다.
`dump_branch_inventory.py` docstring 의 경고("missing `Jet_puId` cuts every jet
below 50 GeV")는 목록에서 빠질 때의 이야기이고, 여기서는 **재계산을 하지 않을
때** 같은 결과가 납니다.

`branches/branch_hadronic_{2017,2018}_v15_{MC,Data}.txt` 4개는 이 인벤토리가
나오기 **전에** 작성된 초안이라 UNVERIFIED 상태입니다. §2 절차를 ttHH 소비자
목록(`--profile main`)으로 다시 돌려야 합니다.
[`01_STATUS.md`](01_STATUS.md) OPEN 항목 참조.

---

## 4. 이 절차로 잡은 것 (2026-08-27)

- `HLT_IsoTkMu*`, `HLT_L2DoubleMu*` — 2017UL에서 **v9·v15 both dead**.
  2016 경로 이름이며 `branch_CPV_Run2_MC.txt`는 Run2 4개 era가 공유하므로
  **지우면 안 됩니다** (UL16 출력에서 조용히 빠짐). 정답은 per-era 분리.
  `branch_CPV_Run2_Data.txt` L22/L24에도 동일하게 있습니다.
- `check_branchlist.py` (C) 절의 오탐 6건 (모듈 산출 branch를 입력 스키마에서
  찾고 있었음) — `produced` 플래그로 수정.
- 대화형 bash의 history expansion: 큰따옴표 안의 `!!` 가 직전 명령으로 치환되어
  붙여넣은 명령이 조용히 다른 명령이 됩니다. 2절 Step 0 (`set +H`) 참조.

## 5. Gate 5b 결과 — v15에서 CPV 모듈 실행 성공 (2026-08-27)

```
[topCPVCategorizer] pre-registered 16 gen branch readers
processed=2000 signal(ttbar)=2000 unclassifiable(Channel_Idx_Expanded==-999)=0
Total time 11.5 sec. Rate = 174.4 Hz.  user 13.509s sys 2.224s
```

- CMSSW_14_2_1 의 NanoAODTools `arrayReader` 는 v15 의 `UShort_t` / `Short_t` 를
  문제없이 처리합니다. **코드 수정 없이 통과.**
- `GenPart_statusFlags` 의 bit 7/13 비트마스크도 정상 — statusFlags 가 깨졌다면
  hard-process 선택이 무너져 대량 `-999` 가 나왔을 것이고, 실제로는 0건입니다.
- 174.4 Hz (v9 199.5 Hz 대비 −13 %, Events branch 1666→1903 증가분). CRAB 여유.
- 예상대로 dead HLT 패턴 2개가 각각 job당 ROOT 에러 1줄로 찍혔습니다.

물리 동일성 자체는 6절에서 event-matched 로 확인했습니다. 그 과정에서
**앞 2000 entry 끼리의 채널 분포 비교는 증거가 되지 않는다**는 점이 드러났습니다:
τ 645:645, e 669:679, μ 686:676 로 그럴듯해 보였지만
`(run, luminosityBlock, event)` 겹침이 **0** 이었습니다 — 서로 다른 event 를 비교한
것이므로 τ 일치는 우연이고, e/μ 의 ±10 은 총합과 τ 가 고정된 상태에서 따라오는
반대칭(0.3 σ)일 뿐입니다.

---

## 6. 최종 결과 — v9 ↔ v15 event-matched 비교 (2026-08-30)

**결론: 동일합니다.** 143,000 개의 *같은* event 에 대해 61 개 branch 를 비교해
불일치 0 건.

### 6.1 왜 파일을 짝지어야 했나

v9 와 v15 는 **동일한 MiniAODv2 parent** 를 가집니다 (`dasgoclient parent` 로 확인,
3절). 그러니 같은 event 가 양쪽에 존재합니다. 그런데 각 데이터셋의 첫 번째 파일은
event 가 **하나도 겹치지 않았습니다** — NanoAOD job splitting 이 버전마다 달라
파일 경계가 전혀 대응하지 않기 때문입니다. lumi *범위* 는 [14715,353516] 과
[2579,331876] 로 크게 겹치는데 lumi *집합* 이 거의 서로소입니다.

해법: v9 파일의 lumi 집합을 로컬 파일의 `LuminosityBlocks` 트리에서 읽고,
`dasgoclient -query="file,lumi dataset=<v15>"` 로 v15 의 398 개 파일을 겹침 순으로
랭킹합니다. 1 위가 **143 lumi (~143k event)** 를 공유했습니다.

⚠ 이 페어링은 **특정 v9 파일에 묶여 있습니다.** `dasgoclient ... | head -1` 로 다른
파일을 집으면 겹침이 사라집니다. `script/setup_v9v15_validation.sh` 가 LFN 을
고정해 두는 이유입니다.

양쪽 실행을 공유 lumi 집합으로 제한하는 데에 `run_postproc.py --cut` 을 썼습니다
(전체 파일 두 개를 도는 ~3 h 대신 각 ~8 min).

### 6.2 실행

| | v9 | v15 (paired) |
|---|---|---|
| 입력 | `.../280000/549451D9-...root` | `.../2560000/12804c46-...root` |
| 입력 event | 1,126,000 | 927,000 |
| preselect | 143,000 (12.70 %) | 143,000 (15.43 %) |
| accepted | 143,000 / 143,000 (100 %) | 143,000 / 143,000 (100 %) |
| unclassifiable | 0 | 0 |
| event loop | 457.0 s | 496.1 s |
| 실효 처리율 | 313 Hz | 288 Hz |
| 출력 | 45 MB | 45 MB |

branch 목록은 양쪽 모두 **`branches/branch_CPV_validation.txt` 하나**를 썼습니다.
거기 실린 이름이 v9 와 v15 에서 바이트 단위로 같기 때문에(3.4절), 목록이 비교의
교란 요인이 될 수 없습니다.

⚠ 로그의 `Total time ... Rate = 1868.7 Hz` 는 **믿지 마십시오.** NanoAODTools 가
분모에 *입력* entry 수를 씁니다. 실효 처리율은 143,000 / 496.1 s = 288 Hz 이고,
진행 로그의 `avg speed 0.314 kHz` 가 맞는 값입니다.

### 6.3 비교 결과

`script/compare_v9_v15.py`, `(run, luminosityBlock, event)` 로 join:

```
events : v9=143000  v15=143000  common=143000  (v9-only=0, v15-only=0)
--prefix TopCPVCat_ : 46 branches x 143,000 = 6,578,000 회 비교 -> 불일치 0
--prefix ""         : 61 branches x 143,000 = 8,723,000 회 비교 -> 불일치 0
--ftol 0            : 46 branches, 허용오차 없이 정확 일치 요구      -> 불일치 0
```

`--ftol 0` 은 float 를 비트 단위로 비교합니다. 통과했으므로 "허용오차 덕에 통과한
것 아니냐" 는 반론이 성립하지 않습니다.

`common=143000` 에 양쪽 only 가 0 이므로 페어링이 정확히 맞았습니다. 비교기는
겹침이 비면 "불일치 0" 이 아니라 exit 3 으로 실패하도록 만들어 두었습니다.

### 6.4 음성 대조군 — 비교기가 차이를 실제로 잡는가

"불일치 0" 은 비교기가 고장나도 나옵니다. `--prefix ""` 실행이 그 확인을 겸했습니다:

```
v9 : 61 branches      v15 : 63 branches
!! only in v15 output: GenJet_nBHadrons, GenJet_nCHadrons
```

정확히 3.4절의 인벤토리 diff 가 예측한 두 branch 입니다. 비교기의 branch-set 감지가
작동하며, 동시에 **독립적인 두 측정(인벤토리 diff, 출력 파일 비교)이 서로를
확인**합니다.

### 6.5 검증 사슬이 닫혔다

표준 C++ `TopCPVGenCategorizer` 는 `GenPart_statusFlags` 를 `Int_t` 로 읽으므로
v15 에서 조용한 쓰레기 값을 냅니다 (3.4절). 즉 v15 를 기준 구현체와 **직접** 비교할
수 없습니다. 전이적으로 닫았습니다:

| 단계 | 비교 | 규모 | 결과 |
|---|---|---|---|
| Gate 4 (2026-08-25) | standalone C++ ≡ 모듈, v9 | 2,000 ev × 61 br | 불일치 0 |
| Gate 5 (2026-08-27) | 모듈이 읽는 branch 의 v15 존재 | 12 br | rename 0, 삭제 0 |
| Gate 5b (2026-08-27) | v15 에서 모듈 실행 | 2,000 ev | 코드 수정 없이 통과 |
| **최종 (2026-08-30)** | **모듈(v9) ≡ 모듈(v15)** | **143,000 ev × 61 br** | **불일치 0** |

⇒ **v15 위의 모듈은 기준 구현체에 대해 전이적으로 검증되었습니다.**
`GenPart_statusFlags` 의 `Int_t → UShort_t` 와 `GenPart_genPartIdxMother` 의
`Int_t → Short_t` 가 물리 결과를 바꾸지 않는다는 것이 추론이 아니라 872 만 회
비교로 실증되었습니다.

### 6.6 남은 범위 한계 (정직하게)

- **샘플이 하나입니다.** `TTToSemiLeptonic` 만 검증했습니다. `TTToHadronic`
  (all-hadronic 분기) 과 `TTTo2L2Nu` (lepton ≥ 2 분기) 의 코드 경로는 안 밟혔습니다.
  같은 페어링 + 비교를 샘플마다 한 번씩 더 돌려야 완전합니다.
- ~~float 의 비트 동일성~~ **확인 완료 (2026-08-30).** `--ftol 0` 재실행에서도
  불일치 0 — v9 와 v15 는 gen 정보를 **비트 단위로 동일하게** 저장합니다. 따라서 위
  결과는 허용오차에 기댄 것이 아닙니다.
- **Data tier 미검증.** 위는 전부 MC 입니다.
