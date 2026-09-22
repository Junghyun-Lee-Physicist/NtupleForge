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

### Step 1b — 확정된 Run 2 UL v15 캠페인 문자열 (2026-08-25 실측)

`resolve_nano_children.sh {2017,2018} --want v15` 로 두 연도 모두 확인했습니다.
양쪽 다 **6 SAME_PARENT / 0 DIFFERENT_PARENT / 1 VERSION_ABSENT** (부재는 TT4b).

```
2017UL  RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v1        plain
        RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2        plain, 최고 -vN  ★대표
        RunIISummer20UL17NanoAODv15-20UL17JMENano_150X_..._v1-v1       JME flavour
        RunIISummer20UL17NanoAODv15-BTVNanoV15_150X_..._v1-v1 / -v3    BTV flavour

2018UL  RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v1        plain
        RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1-v2        plain, 최고 -vN  ★대표
        RunIISummer20UL18NanoAODv15-20UL18JMENano_150X_..._v1-v1       JME flavour
        RunIISummer20UL18NanoAODv15-BTVNanoV15_150X_..._v1-v1 / -v3    BTV flavour
```

`das_scan.sh` era table 의 추정(`RunIISummer20UL{17,18}NanoAOD@V@`)이 두 연도 모두
맞았습니다. ⚠ GT 와 `-vN` 은 "규칙"이 아니라 이 7 개 샘플에서의 관측일 뿐입니다 —
새 샘플에는 그대로 적용하지 말고 조회하십시오.

**Data 는 형태가 다릅니다** (2026-08-31): v9 `UL2017_MiniAODv2_NanoAODv9`,
v15 `UL2017_NanoAODv15` — `MiniAODv2_` 가 빠집니다.
[05](05_troubleshooting.md) A20.

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

### Step 3b — ⚠ 한 파일로 끝내지 마십시오: 전수 sweep

branch 존재 여부는 NanoAOD **버전만의 속성이 아닙니다.** primary dataset, tier
(Data/MC), 그리고 HLT 의 경우 **run era** 에 따라 갈립니다 — HLT branch 집합은 그
dataset 이 덮는 run 범위의 트리거 메뉴이기 때문입니다. 2026-08-30 실측:

| | Events | HLT |
|---|---|---|
| Run2017B | **1208** | **269** |
| Run2017C | 1523 | 479 |
| Run2017D | 1570 | 526 |
| Run2017E | 1612 | 526 |
| Run2017F | 1666 | 580 |
| UL17 MC | 1666 | 569 |

Run B 는 Run F 의 절반도 안 되는 HLT 를 갖고 있고, 분석이 그 기간에 OR 하는
calo 기반 hadronic b-tag 경로(`HLT_HT300PT30_QuadJet_..._TripeCSV_p07` 등)를 가진
**유일한** era 입니다. 이걸 모르고 MC 파일 하나로 "v15 가 트리거를 잃었다" 는
잘못된 결론을 낸 적이 있습니다: [05](05_troubleshooting.md) A19.

그래서 **여러 인벤토리를 떠서 교차 대조합니다.** 스키마만 읽으므로 XRootD 직독으로
충분하고 (Step 2 의 "/tmp 로 복사" 규칙은 **event loop** 에만 적용됩니다) 데이터셋당
수 초입니다.

```bash
bash script/sweep_inventories.sh          # script/inventory_manifest_2017UL.txt
```

manifest 는 (tier x run era x NanoAOD 버전) 조합을 한 줄씩 담습니다 — MC primary 를
더 넣는 것보다 **run era 를 더 넣는 것**이 훨씬 값어치가 큽니다. 기존 인벤토리는
건너뛰므로 재실행이 쌉니다.

그다음 교차표:

```bash
python3 script/branch_presence_matrix.py --inventory-dir script/inventory \
    --profile main --mc --era 2017 --partial-only
```

봐야 할 것은 **PARTIAL** 열입니다 — 어떤 인벤토리에는 있고 어떤 데는 없는 branch.
한 파일에서 유도한 keep-list 나 요구사항이 나머지에서 틀리는, 조용한 실패의 근원이
바로 이 집합입니다. exit 0 전부 존재 / 2 PARTIAL 있음 / 3 어디에도 없음.

HLT 계열만 훑어보려면:

```bash
python3 script/branch_presence_matrix.py --inventory-dir script/inventory \
    --pattern '^HLT_' --partial-only
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

### 3.2b HLT 는 버전이 아니라 **run 범위**가 결정합니다

HLT branch 집합은 그 dataset 이 덮는 run 범위의 HLT 메뉴입니다. 버전 diff 로
"사라졌다" 를 판단할 수 없는 유일한 branch 군입니다. 2026-08-30 실측:

| 인벤토리 | Events | HLT | hadronic b-tag 경로 |
|---|---|---|---|
| 2017UL v9 MC | 1666 | 569 | PF CSV + PF DeepCSV |
| 2017UL v15 MC | 1903 | **569** | 〃 (v9 과 차집합 0) |
| Data `Run2017B` | **1208** | **269** | **calo 4 개, `TripeCSV` 오타 포함** |
| Data `Run2017C` | 1523 | 479 | PF CSV 만 |
| Data `Run2017D` | 1570 | 526 | PF CSV + PF DeepCSV |
| Data `Run2017E` | 1612 | 526 | 〃 |
| Data `Run2017F` | 1666 | 580 | 〃 |

hadronic 트리거는 **B / C / D–F 세 그룹**입니다: Run B 는 calo 기반,
Run C 는 PF CSV 만, Run D 부터 `HLT_PFHT380_SixPFJet32_DoublePFBTagDeepCSV_2p2`
가 추가됩니다. `Tripe` 오타는 **B 에만** 있고 C–F 는 전부 `TriplePFBTagCSV` 입니다.
(legacy `branches_data.txt` 의 1570 은 Run2017D 였습니다.)

**v9 MC 와 v15 MC 의 HLT 집합은 완전히 동일합니다 (차집합 0)** — v15 의 트리거
영향은 0. 한편 같은 v9 안에서도 MC 569 / Data 526 (MC-only 43) 이고 Data 끼리도
1570 vs 1208 입니다. 한 파일로 부재를 단정한 사고: [05](05_troubleshooting.md) A19.

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

~~`branches/branch_hadronic_{2017,2018}_v15_{MC,Data}.txt` 4개는 이 인벤토리가
나오기 **전에** 작성된 초안이라 UNVERIFIED 상태입니다.~~ **2026-09-16 에 실제 스키마로 점검 완료**
(7.3 절): dead pattern 2 종(`btagWeight_*`, 2017 Data 의 `HLT_QuadPFJet*`)을 제거했고, 남은 exit 3 은 위의
`Jet_jetId`/`Jet_puId` 재계산 항목 그대로다.

### 3.5 era 별 v9 → v15 diff: 2016 두 half · 2018 MC, Data 13 era (2026-09-18)

D-2026-09-17-ul18-v9-parked 가 요구한 기록. 위의 2017UL MC diff 하나만 있던 것을 `inventory_manifest_v9_2016_2018.txt` 의 v9 인벤토리 16 개
(`run_sweep_v9_2016_2018_20260918_072530.log`, dumped 16 / failed 0)와 기존 v15 인벤토리로 16 쌍 diff 했다(`run_diff_v9_v15_2016_2018_20260918_072642.log`,
산출물 `script/inventory/diff_v9_v15_*.txt`). 아래 분류는 diff 파일의 branch 이름 접두어로 나눈 것(obj = `HLT_`/`L1_`/`DST_`/`Flag_`/`Scouting` 이 아닌 전부).

| 쌍 (v9 → v15, 파일 1 + 1) | removed | added | retyped |
|---|---|---|---|
| 2016preVFP MC, 2016postVFP MC | 127 = **126 obj** + 1 L1 | 370 = **348 obj** + 18 DST + 4 L1 | **86 obj** |
| 2017UL MC (3 절) | 127 = **126 obj** + 1 L1 | 370 = **348 obj** + 16 DST + 2 Scouting + 4 L1 | **86 obj** |
| 2018UL MC | 129 = **126 obj** + 3 L1 | 396 = **348 obj** + 18 DST + 2 Scouting + 28 L1 | **86 obj** |
| Data 2016 B ver1, B ver2, C, D, E, F HIPM, F, G, H; 2018 B, C, D (12 era) | 121–129 = **120 obj** + 1–9 HLT/L1 | 328–360 = **309 obj** + 15–21 DST + 4–7 L1 + 0–26 HLT (+2 `Flag_*_pRECO` 2018) | **58 obj** |
| Data 2018A | 378 = **120 obj** + 54 HLT + 204 L1 | 333 = **309 obj** + 18 DST + 2 Flag + 4 L1 | **58 obj** |

읽는 법. ① **물리 객체 branch 의 v9→v15 변화는 era 와 무관하게 하나다**: MC 는 세 해 모두 126/348/86 으로 집합까지 같고(2016 두 half 와 2017 의
obj 집합 diff 0; 2018 도 obj 는 0, L1·DST 만 다름), Data 는 13 era 전부 120/309/58 로 집합까지 같다. 즉 2017UL 로 확인한 rename·삭제·타입 변화(3.1–3.4 절)가
2016·2018 에 그대로 적용된다. ② era 마다 다른 것은 전부 트리거 계열(`HLT_`, `L1_`, `DST_` scouting, 2018 의 `Flag_BadPFMuonDzFilter_pRECO`·
`Flag_hfNoisyHitsFilter_pRECO`)이고, 이는 3.2b 절대로 **run 범위(메뉴)의 문제**다. ③ 2018A Data 의 removed 378 은 스키마가 아니라 표본 파일의 run 덮개 차이다:
v9 표본(HLT 664)과 v15 표본(HLT 610)이 다른 run 집합을 덮어 v9 쪽 파일에만 있던 HLT 54 + L1 204 가 "removed" 로 잡혔다(7.4 절의 2018A 메뉴 사실과 같은 원인).
④ MC 와 Data 의 obj 변화 차이(MC 126/348/86 vs Data 120/309/58)는 gen 계열이다: MC 에만 removed 6(`FatJet_nBHadrons/nCHadrons`, `MET_fiducialGenPhi/Pt`,
`btagWeight_CSVV2/DeepCSVB`), MC 에만 added 40(`Gen*`, `HTXS_*`, `TauSpinner_weight_*`, `GenProton_*`, `LHEPart_*MotherIdx`, `LuminosityBlocks/GenFilter_*`, `Runs/PSSumw` 등) + Data 에만 added 1(`LuminosityBlocks/fill`), MC 에만 retyped 33(`*_genPartIdx`, `*Flavour`, `nGen*`, `nLHE*`,
`nPSWeight`, `Runs/nLHE*Sumw`), Data 에만 retyped 5(`Proton_*`, `nPPSLocalTrack`). 전부 diff 파일에서 셀 수 있는 수치이며 여기서는 요약만 둔다.

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

### 6.0 ⚠ 무엇이 같아야 하고 무엇이 달라도 되는가 — 비교를 해석하기 전에

v15 의 GT 는 `150X_mc<YEAR>_realistic_v1` 로 v9 (`106X_mc2017_realistic_v9`,
`106X_upgrade2018_realistic_v16_L1v1`) 와 **다릅니다.** MiniAOD 부모가 같아도 NANO
step 을 새 release·새 conditions 로 다시 돌린 **진짜 reprocessing** 입니다. 따라서
층에 따라 기대가 갈립니다:

| 층 | 기대 | 근거 | 다르면 |
|---|---|---|---|
| **gen-level** (`genTtbarId`, `GenPart_*`, `GenJet_*`, `GenMET_*`, `PSWeight`) | **동일해야 한다** | MiniAOD gen record 에서 그대로 옵니다 | **진짜 red flag.** 조사 대상 |
| **reco-level** (`Jet_*`, MET, b-tag score, jet ID, `Electron_*`, `Muon_*`) | **달라도 정상** | NANO step 이 새 conditions 로 재계산 | 차이 자체가 **결과**입니다. 버그 아님 |

이 구분을 못 박아 두지 않으면 나중에 나오는 reco 차이를 놓고 "마이그레이션이 깨졌다"
와 "예상된 재처리 효과"를 구별할 수 없게 됩니다.

**6 절의 결과는 전부 gen-level 입니다.** CPV categorizer 가 읽고 쓰는 것
(`GenPart_*`, `GenJet_*`, `GenMET_*`, `PSWeight`, `TopCPVCat_*`) 이 모두 gen-level
이므로 비트 단위 일치가 나온 것이고, 그것이 **reco branch 도 일치하리라는 증거는
아닙니다.**

⚠ 따라서 ttHH passthrough ntuple 을 `compare_v9_v15.py --prefix ""` 로 비교할 때는
**reco branch 의 불일치를 실패로 읽으면 안 됩니다.** 판정 기준은:

- gen-level branch 가 하나라도 어긋나면 → **조사**
- reco-level branch 가 어긋나면 → **측정 결과로 기록**. 얼마나 어긋나는지가 곧
  "v9→v15 재처리가 물리량을 얼마나 바꾸는가" 이고, 그게 마이그레이션이 답해야 할
  질문입니다

TTHHGenCategoryTools 의 match 는 **gen-level 검증**이고, analyzer 비교는
**reco-level 차이 측정**입니다 — 목적이 다릅니다.

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

---

## 7. 2026-09-16 전수 스윕 결과: UL16 · UL17/18 v15 Data · Run 3 (35 인벤토리) 와 브랜치 목록 점검

이 절은 **결과와 결정**만 담는다. 무엇을 언제 실행했는지는 [`09_v15_migration_log.md`](09_v15_migration_log.md) 17 절,
실행 원장은 [`10_validation_ledger.md`](10_validation_ledger.md). 숫자의 출처는 전부 `script/inventory/inv_*.tsv`(스윕 기록
`script/runlogs/run_sweep_run3_2016_20260916_071717.log`) 와 `script/check_branchlist.py` 의 출력이다.

### 7.1 인벤토리가 이제 덮는 범위

`script/inventory/` 57 개 (2017 v9 13 + 2017UL v15 MC 1 + 09-16 의 35 + 09-17 의 UL16 era 9). 스키마만 읽으므로 한 파일당 수 초, 35 개 582 초, 9 개 101 초.

| 그룹 | 인벤토리 | Events 브랜치 | HLT |
|---|---|---:|---:|
| Summer24 v15 MC | `TTto4Q`, `TTBBto4Q`, `TTHH-HHto4B` | 2007 (셋 다 동일) | 716 |
| 2024 v15 Data (JetMET0, C..I, I `_v2`) + Muon0 C | 9 | 2236–2300 | 702–720 |
| 2025 v15 Data (JetMET0 PromptReco B..G, C-v2, F-v2) + Muon0 C | 9 | 1932–1984 | 733–744 |
| UL16 v15 MC (preVFP / postVFP, `TTToHadronic`) | 2 | 1741 / 1741 | 601 / 601 |
| UL16 v15 Data (JetHT B-HIPM / F, 09-16 패턴 라벨) | 2 | 1492 / 1564 | 498 / 534 |
| UL16 v15 Data, era 별 9 (B ver1, B ver2, C, D, E, F HIPM, F, G, H; 09-17) | 9 | 1492 / 1554 / 1548 / 1547 / 1571 / 1593 / 1564 / 1566 / 1556 | 498 / 538 / 537 / 536 / 549 / 560 / 534 / 549 / 519 |
| UL17 v15 Data (JetHT B..F) | 5 | 1399 / 1716 / 1777 / 1819 / 1873 | 269 / 481 / 526 / 526 / 580 |
| UL18 v15 Data (JetHT A..D), UL18 v15 MC | 4 + 1 | 1703 / 1778 / 1753 / 1772, 1889 | 610 / 685 / 642 / 657, 651 |

UL17 v15 Data 의 HLT 수는 v9 와 era 별로 같다(B 269, D/E 526, F 580; C 만 481 vs 479). **HLT 집합은 버전이 아니라 run 범위가
결정한다**는 3.2b 절이 v15 에서도 그대로다.

### 7.2 `--profile main` 교차표 (48 인벤토리): 새 위험 없음

`branch_presence_matrix.py --profile main --mc --partial-only`(`run_matrix_main_mc_20260916_072719.log`): 전부 존재 37, MC 전용 19,
어디에도 없음 0, **PARTIAL 6**. 여섯 개는 모두 이미 알던 것이다.

| PARTIAL | 있는 곳 | 없는 곳 | 뜻 |
|---|---|---|---|
| `fixedGridRhoFastjetAll`, `MET_pt`, `Jet_jetId`, `Jet_puId`, `Electron_mvaFall17V2Iso_WP90` | v9 12 개 전부 | v15 36 개 전부 (UL16·UL17·UL18·Run 3) | 3.1 절 rename 과 3.2 절 삭제. **UL16 과 UL18 v15 는 UL17 v15 와 같은 변화** |
| `L1PreFiringWeight_Nom` | Run 2 27 개 전부 (v9·v15, Data 포함, 11 브랜치) | Run 3 21 개 전부 | Run 2 전용 보정. Run 3 목록에서는 keep 을 빼야 한다 |

`Jet_*` 집합은 **UL18 v15 MC 와 Summer24 v15 MC 가 완전히 같다**(`comm` diff 0): `Jet_puIdDisc`, `Jet_btagDeepFlavB`, PNet(`Jet_btagPNetB` 등 6),
UParT(`Jet_btagUParTAK4B` 등 14), `Jet_chMultiplicity`/`neMultiplicity`/`nConstituents`(UChar_t), `Jet_neHEF` 류 7 개 전부 양쪽에 있다.
Summer24 MC 와 UL18 v15 MC 의 non-HLT/L1/Flag 차이는 작다: Summer24 에만 `DST_PFScouting_*` 17, `Dataset_Scouting*` 2, `MC_PFScouting`,
`Electron_mvaIso_WPHZZ`, `Photon_hoe_PUcorr`, `Photon_pfRelIso03_*_quadratic`, `Pileup_pthatmax`; UL18 에만 `Electron_mvaIso_WPL`,
`Electron_mvaNoIso_WPL`, `LowPtElectron_embeddedID`, `Photon_pfRelIso03_all/chg`, `Scouting*Output` 2.

**`Flag_METFilters`(합성 플래그)는 Summer24 MC 와 2025 PromptReco Data 에 없다.** Run 2 v9·v15 전부와 2024 MINIv6NANOv15 Data 에는 있다.
개별 `Flag_*` 는 어디에나 있으므로 `keep Flag_*` 로 충분하지만, prescan 프로필(`PRESCAN_REQUIRED`)과 analyzer 가 합성 플래그를 읽는다면
Run 3 에서 조용히 0 이 된다(eventBuffer 기본값). analyzer 측 항목.

### 7.3 브랜치 목록 점검 결과 (`check_branchlist.py`, 2026-09-16)

08-17 에 만든 v15 목록 4 개는 인벤토리가 없어 UNVERIFIED 였다. 이번에 실제 스키마로 돌렸다. **exit 3 은 `Jet_jetId`·`Jet_puId` 부재(3.4 절,
analyzer 측 재계산) 때문이고 목록 문제가 아니다.** 목록 문제는 exit 4(무엇에도 안 맞는 패턴 = job 마다 ROOT 오류 1 회)다.

| 목록 | 인벤토리 | 고치기 전 | 고친 것 | 고친 뒤 |
|---|---|---|---|---|
| `branch_hadronic_2017_v15_MC` | UL17 v15 MC | exit 4: `btagWeight_*` dead | 줄 삭제(3.2 절: v15 에서 사라짐) | exit 3, dead 0, (B) 67/67 |
| `branch_hadronic_2018_v15_MC` | UL18 v15 MC | exit 4: `btagWeight_*` dead | 같음 | exit 3, dead 0 |
| `branch_hadronic_2017_v15_Data` | UL17 v15 Data B..F | exit 4 (B,C,D,E): **`HLT_QuadPFJet*` dead** (F 만 12 개 존재; v9 도 같음) | 줄 삭제(analyzer 의 quad-jet 경로는 `HLT_PFHT*` 아래) | exit 3, dead 0 (5 era 전부) |
| `branch_hadronic_2018_v15_Data` | UL18 v15 Data A..D | exit 3 | (수정 없음) | exit 3, dead 0 |
| **신규** `branch_hadronic_2024_v15_MC` | Summer24 MC 3 종 | 2018 MC 목록 그대로 쓰면 `btagWeight_*`, `L1PreFiringWeight_*` dead | 2018 목록에서 치환 생성: prefiring keep 제거, Run 3 HLT 주석, 카운트 | exit 3, dead 0, (B) 61/61 |
| **신규** `branch_hadronic_2024_v15_Data` | 2024 Data 9 | (2018 Data 목록 dead 0) | 치환 생성 | exit 3, dead 0 (9 개 전부) |
| **신규** `branch_hadronic_2025_v15_Data` | 2025 Data 9 | 같음 | 치환 생성 (`Flag_METFilters` 부재 주석) | exit 3, dead 0 |
| **신규** `branch_hadronic_2016_v15_MC` | UL16 MC 2 | (2018 MC 목록: `btagWeight_*` dead 만) | 치환 생성, prefiring keep 유지(11 브랜치 존재) | exit 3, dead 0 |
| **신규** `branch_hadronic_2016_v15_Data` | UL16 Data 2, 그 뒤 09-17 에 era 9 전부 | (dead 0) | 치환 생성 | exit 3, dead 0 (11 파일 전부); B ver1 에만 `HLT_AK8PFJet450` 없음(info) |
| **신규** `branch_CPV_Run2_Data_v15` | Run 2 v15 Data 11 | v9 Data 목록 + v15 추가분 | `PFCand_*`, `nPFCand`, `FatJetPFCand_*`, `nFatJetPFCand`, `PVBS_*`, `nPVBS`, `nTauProd` drop 추가; `DST_*` 는 2017B 에 0 개라 넣지 않음 | exit 0 (2016: 09-16 의 2 개 + 09-17 의 era 9 개 전부), exit 4 (2017/2018: 공유 2016 경로명 2 개, 2017B 는 6 개) |
| (기존) `branch_CPV_Run2_MC_v15` | UL16 v15 MC 2 | | | exit 4: **`Scouting*` 가 UL16 MC 에 없다** (UL17/18 에는 있음) → per-era 분리 근거 추가 |
| (기존) `branch_prescan_slim_2017` | UL17 MC v9·v15 | | | exit 4: Run B calo 경로 3 개(`HLT_HT300PT30_..._TripeCSV_p07`, `..._BTagCSV_p080`, `..._p075`)가 MC 에 없다. 07-27 부터 그랬고(v9 도 같음) prescan 캠페인은 끝났으므로 기록만 |

CPV Data 목록의 exit 4 는 MC v15 목록과 같은 **의도된** 상태다(`HLT_IsoTkMu*`, `HLT_L2DoubleMu*` 는 2016 경로명; 목록이 네 era 를 공유하므로
지우면 2016 출력에서 조용히 빠진다). 이번 2016 인벤토리로 처음 정량화됐다: 2016 B-HIPM 5/3 개, F 6/3 개, 2017·2018 0. 2017B 는 추가로
`HLT_TkMu*`, `HLT_TrkMu*`, `HLT_DoubleIsoMu*`, `HLT_MET*` 가 0 이라 6 개. 해법은 per-era 분리(01_STATUS 항목).

`check_branchlist.py` 변경: `--era 2016|2024|2025` 추가. `HLT_REQUIRED` 는 **비어 있다**(트리거 결정이 없으므로; 빈 목록은 "검사 안 함"이지
"안전" 이 아니다). 후보 경로는 `HLT_ERA_CONDITIONAL` 로 정보 출력. Run 3 era 에서는 `L1PreFiringWeight_Nom` 요구를 자동으로 뺀다.
2018 의 `HLT_ERA_CONDITIONAL` 에 `..._DoublePFBTagDeepCSV_2p2`, `..._PFBTagDeepCSV_1p5` 를 넣었다(7.4 절).

### 7.4 HLT: era 별 hadronic b-tag 경로 (인벤토리 실측)

**2018 의 메뉴 전환: 2018A 전체에 새 쌍 없음 (09-18, run 별 파일 15 개), 진입 run 317509 는 AN2019_094 로 (09-19).** 처음 한 파일(09-16)에서 본 것: `/JetHT/Run2018A-UL2018_NanoAODv15-v2`
에는 `HLT_PFHT380_SixPFJet32_DoublePFBTagDeepCSV_2p2`, `HLT_PFHT430_SixPFJet40_PFBTagDeepCSV_1p5`(2017 임계값의 DeepCSV 판)만 있고 analyzer 가
요구하는 `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94`, `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` 가 없다. 09-17 에 그 파일의 run 범위
316058–316719 를 재고 "적어도 316719 까지" 라고 적었는데, 09-18 의 `probe_hlt_path_by_run.py` 측정이 이를 **2018A 전체**로 넓혔다
(`run_probe_2018A_sixjet_20260918_072158.log`, `run_probe_2018B_sixjet_20260918_072338.log`):

| dataset (v15) | DAS run 범위 | 표본 | 결과 |
|---|---|---|---|
| `/JetHT/Run2018A-UL2018_NanoAODv15-v2` | 127 run, 315257–316995 | run 316700 부터 2 개마다 12 run → 파일 9 개, 합쳐 315257–316995 를 덮음 | 9 파일 전부 `_2p2`=1 `_1p5`=1, `_2p94`=0 `_1p59`=0 |
| `/JetHT/Run2018B-UL2018_NanoAODv15-v2` | 61 run, 317080–319310 | 8 개마다 9 run → 파일 6 개, 317080–319310 | 6 파일 전부 네 경로 =1 |

UL2018 v15 파일은 run 순이 아니라 파일 하나가 era 거의 전체를 덮으므로(예: 315257–316995), 이 방법의 해상도는 여기서 era 크기다: 스키마만으로는 새 두 경로가
**2018A 마지막 run 316995 와 2018B 첫 파일(317080–317696) 사이**에 들어왔다는 것까지 안다. v9 인벤토리도 같다(`inv_2018A_v9_Data.tsv` 옛 2/새 0,
`inv_2018B_v9_Data.tsv` 2/2, C·D 0/2) → v15 가공 산물이 아니라 HLT 메뉴 사실. 옛 두 경로는 2018B 파일에도 branch 로 남고 C·D 에서 사라진다.
**2018A 파일은 전부** analyzer 의 `requireTriggerBranches2018_()` 이 요구하는 두 경로가 없다. 어느 경로가 실제로 fire 했는지(event-level)는 스키마 probe 의 범위 밖이다.

**AN2019_094 (ttH(bb) full Run 2, fully-hadronic, §3.1; `Materials/TTHH/TTH_AN/AN2019_094_v20_ttHAnalysis.pdf`, 09-19 대조)** 가 정확한 run 을 준다.
2018 데이터는 세 기간의 OR 이고 시뮬레이션은 Period C 구성 하나다(§3.1.4, Tables 28–29; AN 은 밑줄 없이 표기하지만 여기서는 NanoAOD branch 이름으로 적는다):

| 기간 | run | 6J1T | 6J2T | 4J3T | HT |
|---|---|---|---|---|---|
| A | 315252–315974 | `HLT_PFHT430_SixPFJet40_PFBTagCSV_1p5` | `HLT_PFHT380_SixPFJet32_DoublePFBTagDeepCSV_2p2` | `HLT_PFHT330PT30_QuadPFJet_75_60_45_40_TriplePFBTagDeepCSV_4p5` | `HLT_PFHT1050` |
| B | 315974–317509 | `HLT_PFHT430_SixPFJet40_PFBTagDeepCSV_1p5` | 같음 | 같음 | 같음 |
| C (= MC) | 317509–end | `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` | `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94` | 같음 | 같음 |

효율은 `HLT_IsoMu27`(2016 은 `HLT_IsoMu24`) 로 뽑은 단일 muon 사건에서 재고, SF 는 HT·medium b-tag 수·6 번째 jet pT 의 함수로 연도별, 기간이 갈리는 해(2017·2018)는
run 평균으로 낸다(§3.1.1). 제어 경로(Table 30): `HLT_PFHT430_SixPFJet40`(315974–317509), `HLT_PFHT380_SixPFJet32`(315252–317509),
`HLT_PFHT450_SixPFJet36`·`HLT_PFHT400_SixPFJet32`(317509–end), `HLT_PFHT330PT30_QuadPFJet_75_60_45_40`(전체).

우리 인벤토리(한 파일씩)와 대조하면 전부 AN 의 기간 구조대로 있다(v9 도 같은 결과; 원장 V34):

| 경로 | 2018A | 2018B | 2018C | 2018D | UL18 MC |
|---|:-:|:-:|:-:|:-:|:-:|
| `..._SixPFJet40_PFBTagCSV_1p5` (기간 A 6J1T) | v9 표본 o / v15 표본 x (그 파일은 316058–316719 만 덮음) | x | x | x | x |
| `..._SixPFJet40_PFBTagDeepCSV_1p5` (B), `..._2p2` (A·B) | o | o | x | x | x |
| `..._1p59`, `..._2p94` (C) | x | o | o | o | o |
| `..._4p5`, `HLT_PFHT1050`, `HLT_IsoMu27`, `HLT_IsoMu24` | o | o | o | o | o |
| 제어 `HLT_PFHT430_SixPFJet40`, `HLT_PFHT380_SixPFJet32` | o | o | x | x | x |
| 제어 `HLT_PFHT450_SixPFJet36`, `HLT_PFHT400_SixPFJet32` | x | o | o | o | o |
| 제어 `HLT_PFHT330PT30_QuadPFJet_75_60_45_40` | o | o | o | o | o |

AN 의 run 경계와 09-18 probe 는 모순이 없다: 317509 는 2018B(317080–319310) 안이라 2018B 파일은 기간 B·C 사건을 다 담아 두 쌍이 다 있고, 2018A(≤316995) 파일에는
C 쌍이 없다. 즉 새 쌍의 진입은 A/B 경계가 아니라 **2018B 안의 run 317509** 다(09-18 에 "경계" 라 적은 것은 해상도 한계였고 이 문장으로 대체한다). 기간 A 의 CSV 판 6J1T 는
2018A 파일 중 run < 315974 를 덮는 파일에만 branch 로 있다(probe 의 9 파일은 315257 부터 덮으므로 있을 것이나 그 경로는 probe 인자에 없었다; 확인은 인벤토리 두 파일).
결론: analyzer 의 `HLT_REQUIRED["2018"]`(= `requireTriggerBranches2018_()`: C 쌍 + `_4p5` + `HLT_PFHT1050` + `HLT_IsoMu27`)는 **MC 구성 = 기간 C 만**이다.
AN 방식(기간별 OR)으로 2018A·B 데이터를 살리려면 기간 A/B 경로를 읽어야 하고, 파일에 없는 branch(2018A 의 C 쌍, C·D 의 A/B 경로, 일부 2018A 파일의 CSV 판)를 false 로 다루는
처리가 필요하다. 선택은 `03_DECISIONS.md` D-2026-09-18-2018A-trigger(사용자).

**Run 3 (2024 Data 9 era 전부 = Summer24 MC = 22 경로, 2025 Data 9 era 전부 = 21 경로).** `HLT_PFHT*` 아래 PNet 기반:

| 2018 analyzer 경로 | 2024/2025 대응 후보 | 2024 | 2025 | Summer24 MC |
|---|---|:-:|:-:|:-:|
| `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94` | `HLT_PFHT400_SixPFJet32_PNet2BTagMean0p50` | o | o | o |
| `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` | `HLT_PFHT450_SixPFJet36_PNetBTag0p35` | o | o | o |
| `HLT_PFHT330PT30_QuadPFJet_75_60_45_40_TriplePFBTagDeepCSV_4p5` | `..._PNet3BTag_2p0`, `..._PNet3BTag_4p3` | o | o | o |
| (같은 항목) | `..._TriplePFBTagDeepJet_4p5` | o | **x** | o |
| (신규) | `HLT_PFHT400_FivePFJet_120_120_60_30_30_PNet2BTag_4p3` / `_5p6` | o | o | o |
| (신규) | `HLT_PFHT250/280_QuadPFJet25/30/35_PNet2BTagMean0p55/0p60`, `HLT_PFHT340_QuadPFJet70_50_40_40_PNet2BTagMean0p70` | o | o | o |
| `HLT_PFHT1050`, `HLT_IsoMu27` | 같은 이름 (+ `HLT_IsoMu24`) | o | o | o |

2024 는 C 부터 I(`_v2` 포함)까지 22 경로가 완전히 같고, 2025 는 B 부터 G 까지 21 경로가 같다. 즉 Run 3 목록의 HLT 블록은 2024/2025 별로
나눌 필요가 없었다(파일은 관례대로 둘로 두되 규칙은 동일). **어느 경로로 트리거할지는 분석 결정**(`ttHH/03_run3_plan.md` §2), 아직 없다.

**2016 v15 (09-17: era 9 파일 전부 + MC 두 half).** CSV six-jet 4 개(`HLT_PFHT450_SixJet40_BTagCSV_p056`, `HLT_PFHT400_SixJet30_DoubleBTagCSV_p056`
와 un-tagged 두 개)는 **9 era 파일 전부**에 있다. AN2019_094 Table 24 의 2016 선택은 그 CSV 두 개 + `HLT_PFJet450` 의 OR(효율 기준 `HLT_IsoMu24`; Run H 의 L1 HT
포화 문제를 `HLT_PFJet450` 으로 보완)이고, 네 경로 모두 9 era 파일과 MC 두 half 에 있다(09-19 대조, 원장 V34) → 2016 트리거 결정(`01_STATUS.md` 표 11)의 후보.
2017 은 AN Tables 25–26 이 `check_branchlist.py` 의 `HLT_REQUIRED["2017"]`(C–F, PF CSV 판)·`HLT_ERA_CONDITIONAL["2017"]`(Run B calo 판)와 같다; Run B 의
`TripeCSV_p07` 오타는 AN 표기(`TripleCSV p07`)와 다르고 실제 branch 이름은 오타 쪽이다(3.2b 절). `HLT_PFHT900`(1050 없음), `HLT_PFJet450/500`, `HLT_IsoMu24`, `HLT_IsoTkMu24`, `HLT_IsoMu27`,
`HLT_Ele27_WPTight_Gsf`, `HLT_PFMET120_PFMHT120_IDTight` 도 전부. `HLT_AK8PFJet450/500` 은 **B ver1(run 272760–273017) 에만 없고** B ver2 부터 있다;
`HLT_PFHT800` 은 H 에만 없다. `HLT_Ele32_WPTight_Gsf` 는 2016 Data 에 없다(MC 에는 있음). 2016B 의 두 dataset 은 v9 의 ver1/ver2 와 같은 분할이다
(`-v1` 9.7M ev, `_v2-v1` 133.8M ev, run 이 겹치지 않음; 원장 V21).

### 7.5 이 스윕이 정한 것과 남긴 것

정한 것: ① v15 목록 4 개의 dead pattern 2 종 제거, ② 신규 목록 6 개(2016 MC/Data, 2024 MC/Data, 2025 Data, CPV Data v15) 가 실제 스키마에서
dead 0, ③ Run 3 목록은 prefiring keep 없음, ④ `check_branchlist.py` 가 2016/2024/2025 를 받음.

남긴 것 (01_STATUS 에 항목으로): ⓐ ~~2016 Data 9 era 행 스윕~~ 09-17 끝남(dead 0, 원장 V23–V25; 두 패턴 라벨 인벤토리는 이 절이 인용하므로 유지);
ⓑ CPV 목록 per-era 분리(2016 경로명 2 개, 2017B 4 개, `Scouting*` 2016 MC); ⓒ ~~2018A 에서 `…_2p94`/`…_1p59` 가 메뉴에 들어온 run 의 bracket~~ 09-18 끝남, 09-19 AN2019_094 로 run 317509 확정(7.4 절); 남은 것은 analyzer 의 2018A 트리거 처리(`01_STATUS.md` 22n);
ⓓ `Flag_METFilters` 부재(Summer24 MC, 2025 Data)의 analyzer/prescan 영향; ⓔ 2016·Run 3 트리거 결정 → `HLT_REQUIRED` 채우기;
ⓕ `Jet_jetId`/`Jet_puId` 재계산(3.4 절, 변화 없음); ⓖ Run 3 의 `Jet_puIdDisc` 는 존재하지만 PUPPI jet 에 PU ID 를 쓸지는 JME 권고 확인.
