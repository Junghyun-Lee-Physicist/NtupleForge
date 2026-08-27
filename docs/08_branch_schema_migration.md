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

### Step 0 — proxy

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

**ttHH → 4b — 미검증. 3.2의 삭제 목록이 직격입니다.**

`Jet_puId`와 `Jet_jetId`가 둘 다 사라졌고 added/retyped 어디에도 없습니다.
`dump_branch_inventory.py` docstring이 경고한 바로 그 시나리오
("missing `Jet_puId` cuts every jet below 50 GeV")입니다. ttHH analyzer의 jet
선택 자체를 v15용으로 재설계해야 할 수 있습니다.

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
