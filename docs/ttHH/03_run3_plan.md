# 03 — Run 3 확장 계획: NanoAODv15 위의 2022–2025, event-level 필수 항목, 데이터셋

> **목적**: ttHH → 4b 파이프라인을 Run 3 로 넓히기 위한 단일 참조. ① 범위와 결정, ② Run 2 와 달리 Run 3 에서 **반드시** 지켜야 할 event-level 항목(veto map, MET filter, jet ID 재계산 …)의 체크리스트, ③ 데이터셋을 **추정하지 않고 DAS 로 확정**하는 절차와 도구, ④ hadronic / leptonic 용도 구분(`had`/`lep` 태그)과 hadronic 우선 생산.
> **대상 독자**: Run 3 registry 를 채우고 첫 ntuple 을 만들 사람; analyzer 에 Run 3 cleaning 을 넣을 사람.
> **상태**: 살아있는 문서. 작성 **2026-09-07**; 같은 날 **PdmVRun3Analysis twiki r223(2026-09-07)** 과 **PPD "Run3 2025 Summary Table"(2026-01-20)** 원문(PDF)으로 era 경계·golden JSON·루미·GT·데이터 명명 규칙을 대조해 해당 행을 "실측" 으로 올렸다. 남은 "기억" 표시(veto map 키, MET filter 세부, JEC 태그, PU 키, 트리거 경로)는 POG twiki 원문 확인 전까지 **코드에 넣지 않는다**. §4 의 데이터셋은 2024 두 줄(참조 분석 목록으로 확인)을 빼면 discovery 전까지 **패턴**이다.
> **관련**: Run 2 v15 마이그레이션 [`../09_v15_migration_log.md`](../09_v15_migration_log.md), 스캐너 [`../../script/das_scan.sh`](../../script/das_scan.sh), Run 3 discovery [`../../script/das_discover_run3.sh`](../../script/das_discover_run3.sh), 2018 확장 시 정한 multi-year 원칙 (workspace `00_CONTEXT…` §2.3).

## 결론 먼저 (BLUF)

- **버전은 하나로 간다: NanoAODv15.** Run 2 UL 재생산도 v15 이고 Run 3 (2022, 2022EE, 2023, 2023BPix, 2024) 의 최신 재생산도 v15 라, analyzer 는 **하나의 스키마**만 알면 된다. **2025 (기본 대상)**: 데이터는 T0 prompt 로 MINIAODv6/NANOv15 (GT `150X_dataRun3_Prompt_v1`), **MC 캠페인은 아직 없다** → PPD 권고대로 **Summer24 MC** (`RunIII2024Summer24NanoAODv15`, GT `150X_mcRun3_2024_realistic_v2`) 를 2025 데이터에 쓴다 (§4.2).
- **Run 3 는 "Run 2 + 몇 가지" 가 아니라 cleaning 규칙이 다르다.** 필수: era 별 golden JSON, **jet veto map(전 era, event veto)** — 2023BPix 는 BPix 구멍이 따로 있음 —, Run 3 MET filter 목록(`Flag_BadPFMuonDzFilter`·`Flag_hfNoisyHitsFilter` 추가, `ecalBadCalibFilter` 의 2022–23 보정), NanoAOD `Jet_jetId` 를 PF fraction 으로 **재계산**, PUPPI jet/MET 기본, era 별 JEC/JER·pileup JSON, b-tagger 교체(PNet → UParT). L1 prefiring 과 HEM veto 는 Run 3 에 없다. 표는 §2.
- **데이터셋 이름은 13.6 TeV 명명으로 전부 바뀐다** (`TTto4Q_TuneCP5_13p6TeV_powheg-pythia8`, `QCD-4Jets_HT-*`, `Wto2Q-3Jets_HT-*`, `DYto2L-4Jets_MLL-50*`, PD `JetMET0/1`, `Muon0/1`, `EGamma0/1`). 그래서 registry 는 **별도 파일**(`samples_registry_run3.txt`)로 두고, 이름은 `das_discover_run3.sh` 가 DAS 에서 가져온 것만 적는다 (§4).
- **용도 태그 `had` / `lep` 를 registry 에 넣었다** (Run 2 포함). hadronic 채널의 signal·background·JetHT/BTagCSV 가 `had`(47 key), DY·W→ℓν HT 샘플이 `lep`(16), SingleMuon 은 둘 다. **ntuple 생산은 `--workstream had` 로 hadronic 먼저**, lep 는 다음 라운드 (§5).
- 첫 실행 순서는 §6: `das_scan.sh --probe` (캠페인 문자열 확정) → `das_discover_run3.sh` (이름 확정) → registry 작성 → `das_scan.sh --workstream had` (event 수·파일 수) → config 생성.

---

## 1. 범위와 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| **D-R3-1 · 대상 era** | **2025 (C–G, 110.6 fb⁻¹ 예비; MC = Summer24)** 를 기본으로, 2024 (C–I, 110.0 fb⁻¹), 2023 (C) / 2023BPix (D), 2022 (C–D) / 2022EE (E–G). 2026 (A–D 진행 중, MC TBD) 은 제외. B era 들(2022 0.10, 2024 0.13, 2025 0.25 fb⁻¹)은 golden JSON 이 포함하면 같이 쓴다 | era 분할은 검출기 상태(EE 누수, BPix 모듈 손실)를 따르는 MC 캠페인 분할과 일치해야 보정 JSON 을 그대로 쓸 수 있다. 사용자 지정 2026-09-07: "기본은 25년도 NanoAOD" |
| **D-R3-2 · NanoAOD 버전** | v15 만 | Run 2 v15 마이그레이션과 같은 스키마·같은 도구(`compare_v9_v15.py`, 브랜치 인벤토리) 재사용 |
| **D-R3-3 · registry 분리** | `script/samples_registry_run3.txt` (KEY 는 Run 2 와 같게, PRIMARY 만 13.6 TeV 이름) | 기존 registry 의 전제 "PRIMARY 는 era 무관" 이 Run 3 에서 깨진다. KEY 를 공유해야 xsec DB·filelist·patch 파일 이름이 연도 사이에서 이어진다 |
| **D-R3-4 · 이름 추정 금지** | primary 이름은 `das_discover_run3.sh` 의 `HIT|` 줄에서만 옮겨 적는다 | `das_scan.sh` 의 원칙 그대로. Run 3 명명은 세대(Summer22 → Summer24)마다도 조금씩 달라 기억이 특히 믿을 수 없다 |
| **D-R3-5 · had/lep 태그 + hadronic 우선** | WORKSTREAM 컬럼에 `had`/`lep` 추가, 첫 생산은 `--workstream had` | 사용자 결정 2026-09-07. lep 샘플(DY, W→ℓν)은 data/MC 정합 테스트용이라 signal region 결과에 필요하지 않다 |
| **D-R3-6 · xsec** | 13.6 TeV 단면적은 **새로 받는다** (XSDB / GenXSecAnalyzer); Run 2 `samples_2017UL.json` 값을 재사용하지 않는다 | 13 → 13.6 TeV 는 모든 σ 가 다르다 (tt̄ 약 +10 %) |

---

## 2. Run 3 에서 지켜야 할 event-level 항목

기호: **실측** = 이 세션에서 DAS/로그로 직접 봄 · **기억** = 2026-09 기준 기억이며 twiki 원문과 대조 필요 · **규칙** = 정책이라 값 확인 불필요. "단계" 는 우리 파이프라인에서 어디서 적용하는지 — NtupleForge 는 passthrough 라 대부분 **analyzer(tempTTHH)** 다.

| # | 항목 | era | 무엇을 | 단계 | 어디서 확인 | 상태 |
|---|---|---|---|---|---|---|
| 1 | **Golden JSON** | 전부 | `/eos/user/c/cmsdqm/www/CAF/certification/` 아래: 2022 `Collisions22/Cert_Collisions2022_355100_362760_Golden.json`, 2023 `Collisions23/Cert_Collisions2023_366442_370790_Golden.json`, 2024 `Collisions24/Cert_Collisions2024_378981_386951_Golden.json`, **2025 `Collisions25/Cert_Collisions2025_391658_398903_Golden.json`** (Muon JSON 은 같은 이름의 `_Muon.json`; 2025 low-PU run 은 별도 `2025_lowPU.json` — 쓰지 않음) | CRAB lumimask (NtupleForge) | PdmVRun3Analysis twiki r223 | **실측** (twiki 2026-09-07) |
| 2 | **era 분할과 run 경계** | 전부 | 2022: C 355794–357486, D 357487–359021 → `Summer22`; E 359022–360331, F 360332–362180, G 362350–362760 → `Summer22EE` (E 부터 EE+ 누수). 2023: C 367080–369802 → `Summer23`; D 369803–372415 → `Summer23BPix` (BPix 모듈 손실). 2024: C 379412–380252, D 380253–380947, E 380948–381943, F 381944–383779, G 383780–385813, H 385814–386408, I 386409–387121 → `Summer24` 하나. 2025: C 392159–393609, D 394286–395967, E 395968–396597, F 396598–397853, G 397854–398903 (사이의 pO/OO/NeNe 393610–394285 는 이온) → MC 는 Summer24 로 대용. 데이터와 MC 의 era 를 **교차 매칭하지 않는다** | config 분리 | PdmVRun3Analysis "Era definition" 표 | **실측** (run 경계·캠페인 매핑) |
| 3 | **Jet veto map** (JME) — **Run 3 전 era 필수** | 전부 | jet 이 "hot/cold" 검출기 영역에 있으면 **event 를 버린다**. jet 선택: pT > 15 GeV, tight jet ID, (chEmEF + neEmEF) < 0.9, PF muon 과 ΔR > 0.2. 지도 키(`jetvetomaps.json.gz`): `Summer22_23Sep2023_RunCD_V1`, `Summer22EE_23Sep2023_RunEFG_V1`, `Summer23Prompt23_RunC_V1`, `Summer23BPixPrompt23_RunD_V1`, `Winter24Prompt24_2024BCDEFGHI_V1`; type 은 분석용 `jetvetomap`. **2023BPix 는 `jetvetomap_bpix`(BPix 구멍, η≈[−1.5, 0]·φ≈[−1.2, −0.8]) 가 따로 있고, 2023 (C) 는 `jetvetomap_fpix` 가 있다** — 기본 `jetvetomap` 이 구멍을 포함하는지, 전자/광자에도 같은 영역 veto 를 걸지는 JME/EGM 권고 확인 | analyzer | `cms-jerc.web.cern.ch/Recommendations/#jet-veto-maps`, `jsonpog-integration/POG/JME/<era>/jetvetomaps.json.gz` | **정책은 실측** (PdmV twiki: "JME-POG recommends ALL analyses use jet-veto-maps … use `jetvetomap` to reject events"; 2022 EE+ 누수 영역은 본 지도에 포함, 별도 `jetvetomap_eep` 는 폐기) · **키 이름·선택 기준은 기억** — **Run 2 의 HEM veto 자리를 이것이 대신한다** |
| 4 | **MET filter** (Run 3 목록) | 전부 | `Flag_goodVertices`, `Flag_globalSuperTightHalo2016Filter`, `Flag_EcalDeadCellTriggerPrimitiveFilter`, `Flag_BadPFMuonFilter`, **`Flag_BadPFMuonDzFilter`**, **`Flag_hfNoisyHitsFilter`**, `Flag_eeBadScFilter`, `Flag_ecalBadCalibFilter`. `ecalBadCalibFilter` 는 2022–2023 에서 NanoAOD 플래그만으로 부족해 JME 가 특정 run 범위(≈362433–367144)에 대해 jet(η,φ 영역)+MET 조건의 event veto 를 추가 권고 | analyzer | JME `MissingETOptionalFiltersRun2` twiki 의 Run 3 절 | 기억 — 목록은 확신, ecalBadCalib 보정의 수치는 원문에서 옮길 것 |
| 5 | **Jet ID 재계산** | 전부 | Run 3 NanoAOD 의 `Jet_jetId` 는 그대로 쓰지 않는다 — PF 에너지 분율·다중도(`Jet_neHEF`, `Jet_neEmEF`, `Jet_chHEF`, `Jet_chEmEF`, `Jet_muEF`, `Jet_chMultiplicity`, `Jet_neMultiplicity`)로 tight / tightLepVeto 를 재계산. PUPPI 와 CHS 의 정의가 다르고 η 구간별 조건이 Run 2 와 다르다 | analyzer (NtupleForge 는 재료 branch 를 `keep`) | JME `JetID13p6TeV` twiki | 기억 — **Run 2 v15 B8 과 같은 작업**이므로 한 구현으로 |
| 6 | **PUPPI 가 기본** | 전부 | `Jet` = AK4 PUPPI (L1 pileup 보정 없음), MET = `PuppiMET_*` (Type-1). CHS 는 `JetCHS`? 로 따로 있음 | analyzer, branch list | JME Recommendations | 규칙 |
| 7 | **JEC / JER** | era 별 | correctionlib `jet_jerc.json.gz`; 태그는 era 별 (`Summer22_22Sep2023_V2`, `Summer22EE_22Sep2023_V2`, `Summer23Prompt23_V1`/`V2`, `Summer23BPixPrompt23_V1`/`V3`, 2024 `Winter24Prompt24`/`Summer24`) — 버전 숫자는 최신을 확인 | analyzer | JME Recommendations | 기억 (버전) |
| 8 | **Pileup reweighting** | era 별 | LUM `puWeights.json.gz` 키: `Collisions2022_355100_357900_eraBCD_GoldenJson`, `Collisions2022_359022_362760_eraEFG_GoldenJson`, `Collisions2023_366403_369802_eraBC_GoldenJson`, `Collisions2023_369803_370790_eraD_GoldenJson`, 2024 `Collisions24_...` | analyzer | LUM POG twiki | 기억 (키 이름) |
| 9 | **b-tagging** | 전부 | Run 2 의 DeepJet 대신 **ParticleNet** (`Jet_btagPNetB`, 2022–2023) 과 **UParT** (`Jet_btagUParTAK4B`, 2024–). WP 와 SF 는 BTV `btagging.json.gz` (era 별). 어느 tagger 로 갈지는 결정 항목 (D-R3-7 후보) | analyzer | BTV twiki / `btv-public.docs.cern.ch` | 규칙 + 기억 |
| 10 | **전자 / 광자** | 전부 | Run 3 ID 는 `mvaEleID-RunIIIWinter22-iso/noIso` (wp80/wp90), `cutBasedElectronID-RunIIIWinter22-V1`; 광자 `mvaPhoID-RunIIIWinter22-v1`, `cutBasedPhotonID-RunIIIWinter22-122X-V1` (CMSSW_126X / NanoV11 부터; NanoAOD 브랜치는 `Electron_mvaIso_WP80` 등). scale & smearing `electronSS.json.gz`(era 별). **2022 EE+ 누수**: era 분할 + 2022EE MC 가 기본이고, EGM 은 선택 사항으로 EE+ (η > 1.556) 의 `seediPhiOriY > 72 && seediEtaOriX < 45` 물체 veto 를 권고; 2022G fill 8456 의 EB 잡음 채널은 700 < pT < 900 GeV, `seediEtaOriX == -21`, `seediPhiOriY == 260` (run 362430–362439 만). 2023BPix 전자/광자의 BPix 영역 veto 여부는 EGM 확인 | analyzer (lep 채널) | PdmVRun3Analysis "From E/Gamma", "Notes on addressing EE+ issue" | **ID 이름·EE+ 권고 실측**, SF JSON 이름 기억 |
| 11 | **뮤온** | 전부 | ID 는 Run 2 와 같음(`Muon_tightId`), SF JSON 은 era 별 `muon_Z.json.gz` | analyzer | MUO twiki | 규칙 |
| 12 | **트리거 (FH)** | era 별 | 6-jet HT 트리거의 Run 3 판: 2022 `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepJet_2p94`, `HLT_PFHT450_SixPFJet36_PFBTagDeepJet_1p59`; 2023– PNet 판 `HLT_PFHT400_SixPFJet32_PNet2BTagMean0p50`, `HLT_PFHT450_SixPFJet36_PNetBTag0p35`, 4-jet `HLT_PFHT280_QuadPFJet30_PNet2BTagMean0p55`; `HLT_PFHT1050` 는 계속. **경로가 era 마다 바뀌므로 per-era 목록 + SF 재측정**. lep CR: `HLT_IsoMu24`, `HLT_Ele30_WPTight_Gsf` | analyzer + NtupleForge branch list (`HLT_*` keep) | HLT menu / 트리거 그룹 twiki, NanoAOD `HLT_*` 브랜치 인벤토리 | 기억 (경로 이름) |
| 13 | **없어진 것** | — | L1 prefiring 보정(2016–17 전용), HEM15/16 veto(2018 전용) 는 Run 3 에 **적용하지 않는다** | analyzer config | — | 규칙 |
| 14 | **루미** (golden JSON, fb⁻¹) | era 별 | 2022 **34.76** (B 0.10, C 5.02, D 2.97 · E 5.81, F 17.78, G 3.09; normtag) · 2023 **28.28** (B 0.64, C 17.96 · D 9.68; normtag) · 2024 **109.95** (B 0.13, C 7.26, D 7.98, E 11.42, F 28.04, G 38.07, H 5.49, I 11.56) · 2025 **110.63 예비** (B 0.25, C 21.56, D 25.82, E 14.05, F 26.69, G 22.25; normtag 없이 online luminosity — LUM 이 normtag 를 정하면 갱신). 우리 값은 `brilcalc` 로 재계산해 확정 (2017: 42.07 의 절차) | samples json `_meta` | PdmVRun3Analysis DATA 표, PPD 2025 표 | **실측** (예비치) |
| 15 | **MC 의 era 매칭·`genWeight`** | 전부 | MC 는 era 별 캠페인만 쓴다(2022 MC 를 2023 data 에 쓰지 않음; **예외는 2025 ← Summer24**, PPD 권고). Run 3 MC 의 `genWeight` 부호·`LHEPdfWeight` 크기 변화(PDF set) 는 sum-of-weights 정규화(`genEventSumw`) 그대로 처리 | prescan / json | PdmV, PPD 2025 표 | 규칙 |
| 16 | **2022 prompt 데이터의 HCAL barrel 문제** | 2022 | prompt 2022 데이터의 barrel 전자/광자(뮤온도)에서 PF neutral-hadron isolation·H/E 가 data/MC 불일치 → 2022 A–E 는 **ReReco(22Sep2023)** 기반 데이터셋을 쓴다. v15 재생산이 어느 입력에서 왔는지(`CAMP|` 문자열)로 확인 | 데이터셋 선택 | PdmVRun3Analysis "HCAL barrel issues" | **실측** |

**한 줄 요약.** Run 2 config 에서 Run 3 로 넘어올 때 analyzer 가 새로 배워야 할 건 다섯 가지다 — jet veto map(era 키), Run 3 MET filter 목록, jet ID 재계산, PUPPI jet/MET, b-tagger 교체 — 그리고 두 가지를 **꺼야** 한다 (prefiring, HEM). NtupleForge 쪽은 golden JSON·campaign 문자열·branch list 의 이름 변화만이다.

---

## 3. 스키마 — Run 2 v15 와 Run 3 v15 의 차이

같은 v15 지만 Run 3 브랜치 인벤토리는 다르다. NtupleForge 의 **인벤토리 스윕**([`../08_branch_schema_migration.md`](../08_branch_schema_migration.md) Step 3b) 을 Run 3 파일 하나에 돌리는 것이 첫 일이다. 예상되는 차이(기억):

- `Jet` 이 PUPPI: `Jet_puId`·`Jet_puIdDisc` **없음** (PUPPI 에 pileup ID 없음); `Jet_neMultiplicity`/`Jet_chMultiplicity` 있음.
- 태거: `Jet_btagPNetB`, `Jet_btagPNetCvB`, `Jet_btagPNetQvG`, `Jet_btagUParTAK4B`(2024), `Jet_PNetRegPtRawCorr*` — Run 2 v15 에도 재계산되어 있지만 Run 3 는 이것이 기본.
- MET: `PuppiMET_*` 가 기본, `PFMET_*` 는 raw 성격; `MET_*` 이름은 없다 (Run 2 v15 도 `PFMET_pt` 로 바뀐 것과 정합).
- 전자: `Electron_mvaIso_WP80`, `Electron_mvaNoIso_WP80` (v9 의 `mvaFall17V2Iso_WP80` 이 아님).
- 트리거: `HLT_*` 집합이 완전히 다름 → `branch_hadronic_<era>_v15_*.txt` 는 era 별로 새로 뽑는다 (`gen_hadronic_branchlists.py` 의 HLT 블록).
- `genTtbarId` 는 있다 (nano_cff 의 `ttbarCategorization` 은 Run 3 에서도 MC 에 붙음) → expanded ttbar id 파이프라인은 그대로.
- PdmV 경고(실측): NanoV12 부터 여러 브랜치가 `Int_t` → `Short_t`/`Char_t` 로 바뀌어 `MakeClass` 기반 코드가 조용히 깨진다 — Run 2 v9→v15 의 86 retyped 와 같은 부류이고, `eventBuffer.h` 재생성으로 처리한다.

이 목록은 스윕 결과로 **대체**한다 — 여기 적어 두는 이유는 스윕에서 무엇을 봐야 하는지 알기 위해서다.

---

## 4. 데이터셋 — 이름을 추정하지 않고 찾는 절차

### 4.1 무엇이 바뀌었나

| Run 2 (13 TeV) | Run 3 (13.6 TeV) 패턴 | 비고 |
|---|---|---|
| `TTToHadronic/TTToSemiLeptonic/TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8` | `TTto4Q_*`, `TTtoLNu2Q_*`, `TTto2L2Nu_*` `_TuneCP5_13p6TeV_powheg-pythia8` | 이름 규약 자체가 바뀜 |
| `TTbb_4f_TTTo*_TuneCP5-Powheg-Openloops-Pythia8` | `TTbb*` | Run 3 존재 여부 확인 대상 |
| `QCD_HT200to300…2000toInf_TuneCP5_13TeV-madgraphMLM-pythia8` | `QCD-4Jets_HT-200to400, 400to600, 600to800, 800to1000, 1000to1500, 1500to2000, 2000` | **HT 구간이 다르다** (200–400, 400–600) → xsec 표 새로 |
| `ttHTobb/ttHToNonbb_M125` | Summer22/23 `TTHto2B_M-125_*`, `TTHtoNon2B_M-125_*`; Summer24 는 `TTH-Hto2B_Par-M-125_*` 꼴일 것 (참조 목록의 `TTH-Hto2G_Par-M-125_…` 로 유추) | 세대마다 표기가 다르다 → 접두어 `TTH*` |
| `THQ/THW_ctcvcp_*` | `THQ*`, `THW*`, `TQH*`, `TWH*` (패턴) | Run 3 존재 여부 확인 대상 |
| `TTZToBB`, `TTZToLLNuNu_M-10`, `TTWJetsToQQ/LNu` | `TTZ-ZtoQQ-1Jets_*`, `TTLL_MLL-*`, `TTLNu-1Jets_*`, `TTNuNu*` | 분해 방식이 다름 |
| `TTZH/TTZZ/TTWW/TTWH/TTWZ_TuneCP5_13TeV-madgraph-pythia8`, `TTTT`, `TTTW`, `TT4b` | `TTZH*`, `TTZZ*`, `TTWW*`, `TTWH*`, `TTWZ*`, `TTTT*`, `TTTW*`, `TT4b*` | 신호 `TTHHto4b` 포함, **Run 3 중앙 생산 존재 여부가 핵심 질문** — 없으면 Run 2 처럼 사설 생산 결정 |
| `ST_t-channel_*`, `ST_tW_*`, `ST_s-channel_*` | `TBbarQ_t-channel_4FS_*`, `TbarBQ_t-channel_4FS_*`, `TWminusto4Q/LNu2Q/2L2Nu_*`, `TbarWplusto*`, `TBbartoLplusNuBbar-s-channel-4FS_*`, `TbarBtoLminusNuB-s-channel-4FS_*` | 붕괴 모드별로 분리됨 |
| `WW/WZ/ZZ_TuneCP5_13TeV-pythia8` | `WW_*`, `WZ_*`, `ZZ_*` (+ 붕괴별); Summer24 **확인**: `ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8`, `WZto2L2Q_…`, `ZZto2L2Q-1Jets_…amcatnloFXFX` | 붕괴별 분리가 기본 |
| `WJetsToQQ_HT-*`, `ZJetsToQQ_HT-*` | `Wto2Q-3Jets_HT-200to400, 400to600, 600to800, 800`, `Zto2Q-4Jets_HT-*` | |
| `WJetsToLNu_HT-*` (lep) | `WtoLNu-4Jets_*` (jet-binned `1J..4J` 또는 HT-binned) | |
| `DYJetsToLL_M-50_HT-*` (lep) | `DYto2L-4Jets_MLL-50_*` (jet-/HT-binned), `DYto2L-2Jets_MLL-50_*` (NLO); Summer24 **확인**: `DYto2E-2Jets_Bin-0J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8` (jet-binned, 렙톤 종류별) | |
| PD `JetHT`, `BTagCSV`, `SingleMuon` | `JetMET` (2022C 부터 JetHT+MET 병합), **`JetMET0`/`JetMET1`** (2023–), `Muon` (2022C 부터 SingleMuon+DoubleMuon 병합)/`Muon0`/`Muon1`, `EGamma`/`EGamma0`/`EGamma1` (2024 **확인**: EGamma0/1 C–I), `BTagMu` | BTagCSV 는 없다. PD 가 `PDi` 로 나뉜 해는 **전부** 받아야 전체 데이터 (PdmV 규칙, 실측) |

### 4.2 캠페인 문자열과 GT

근거: PdmVRun3Analysis twiki r223 (2026-09-07), PPD "Run3 2025 Summary Table" (2026-01-20), 참조 분석(Hγγ, 2024)의 데이터셋 목록, 2018 probe 의 부수 관측(JetHT `Run2022A/B/C-NanoAODv15-v1`). **실측** 은 원문에서 옮긴 것, **확인** 은 실제 DAS 이름을 봤다는 뜻, 나머지는 `--probe` 전까지 패턴이다.

| era | MC 캠페인 (DAS) | MC GT | Data (DAS) | Data GT | 근거 |
|---|---|---|---|---|---|
| **2025** | **없음 → `RunIII2024Summer24NanoAODv15`** (Summer24 를 쓴다) | `150X_mcRun3_2024_realistic_v2` | `/PD/Run2025<C..G>-PromptReco-v<N>/NANOAOD` (T0 prompt MINIAODv6 + NANOv15; **모든 -vN 을 다 쓴다**) | `150X_dataRun3_Prompt_v1` (CMSSW_15_0_0_pre1 부터, snapshot 열림) | PPD 표 **실측**; data 이름 규칙은 2023 era-D 이후 규칙에서 유추 → probe |
| **2024** | `RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v<N>` | `150X_mcRun3_2024_realistic_v2` (CMSSW_15_0_0, 2025-03-12 snapshot) | `/PD/Run2024<C..I>-MINIv6NANOv15-v1|v2/NANOAOD` (Run2024I 에는 `-v2-v1` 도 있음) | 2024 re-mini/re-nano GT — PPD 2024 표 확인 | 참조 목록으로 **확인** (EGamma0/1 C–I, MC 24 개) |
| 2023 / 2023BPix | `Run3Summer23NanoAODv15*` / `Run3Summer23BPixNanoAODv15*` | (v12 원생산: `130X_mcRun3_2023_realistic_v14` / `_postBPix_v2`; v15 재생산 GT 는 probe) | `/PD/Run2023<C|D>-*NanoAODv15*/NANOAOD` (prompt v12 시절 규칙: C 는 `PromptNanoAODv12_v<M>-v<N>`, D 부터 `PromptReco-v<N>`) | probe | MC prefix 는 기억, 데이터 규칙 **실측** |
| 2022 / 2022EE | `Run3Summer22NanoAODv15*` / `Run3Summer22EENanoAODv15*` | (v12 원생산: `130X_mcRun3_2022_realistic_v5` / `_postEE_v6`) | `/PD/Run2022<C..G>-*NanoAODv15*/NANOAOD` — A–E 는 ReReco(22Sep2023) 계열이어야 함(§2 #16) | 2022 ReReco `124X_dataRun3_v15`, prompt FG `124X_dataRun3_PromptAnalysis_v2` (v12 시절) | JetHT `Run2022C-NanoAODv15-v1` **확인**; 나머지 probe |

참조 분석 목록에서 확인된 Summer24 **명명 규칙**: `TTH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8`, `GJet_Bin-MGG-40to80-PT-20_…`, `QCD_Bin-MGG-80-PT-30to40_Fil-DoubleEMEnriched_…`, `DYto2E-2Jets_Bin-0J-MLL-50_…`, `ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8`, `WZto2L2Q_…`, `TTGG_TuneCP5_13p6TeV_madgraph-madspin-pythia8` — 즉 Summer24 는 파라미터를 `Par-`, 구간을 `Bin-`, 필터를 `Fil-` 로 쓴다(Summer22/23 의 `QCD-4Jets_HT-200to400`, `TTHto2B_M-125` 와 다름). `das_discover_run3.sh` 의 wildcard 를 접두어형(`QCD-4Jets*`, `TTH*`, `DYto2L*`)으로 넓힌 이유다. 같은 논리로 우리 신호는 `TTHH*` 접두어로 잡고, ttH→bb 는 `TTH-Hto2B_Par-M-125_*` 일 가능성이 크다.

**2025 데이터 취급 (PPD 표의 주석, 실측)**: prompt 데이터는 한 era 에 v1 과 v2 가 있으면 **둘 다** 넣는다(재처리 데이터는 최신 -vN 하나만). DAS 의 run 목록에는 DBS 버그로 겹치는 run 이 잘못 보고될 수 있으니 루미는 golden JSON 으로 계산한다. MINI/NANO v15 생산 릴리스는 CMSSW ≥ 15_0_10.

### 4.3 절차 (lxplus)

```bash
cd ~/CMSSW_14_2_1/src/NtupleForge && voms-proxy-init --voms cms --valid 72:00
# (0) 캠페인 문자열: 2025·2024 먼저 (기본 대상), 그 다음 2022/2023. MC 두 줄에 HIT|, DATA 는 CAMP| 에서 proc 문자열을 읽어 era 표를 고친다
for E in 2025 2024 2023 2023BPix 2022 2022EE; do bash script/das_scan.sh --era $E --nano v15 --probe | tee script/das_probe_${E}_v15.log; done
# (1) family 별 wildcard 로 존재하는 primary 를 전부 나열 (이름 확정의 유일한 출처). 2025 의 MC 는 Summer24 라 2024 와 같다 -> --data-only
bash script/das_discover_run3.sh --era 2024 --nano v15 --out script/das_discover_2024_v15_$(date +%Y%m%d_%H%M).log
bash script/das_discover_run3.sh --era 2025 --nano v15 --data-only --out script/das_discover_2025_v15_$(date +%Y%m%d_%H%M).log
for E in 2023 2023BPix 2022 2022EE; do bash script/das_discover_run3.sh --era $E --nano v15 --out script/das_discover_${E}_v15_$(date +%Y%m%d_%H%M).log; done
# (2) HIT| 줄에서 samples_registry_run3.txt 작성 (KEY 는 Run 2 와 동일, WORKSTREAM 에 had/lep)
# (3) event/file 수: hadronic 먼저, 2025 (= Summer24 MC + Run2025 data) 부터
bash script/das_scan.sh --era 2025 --nano v15 --registry script/samples_registry_run3.txt --workstream had --out script/das_ttHH_2025_v15_$(date +%Y%m%d_%H%M).log
```

`das_discover_run3.sh` 는 family 당 wildcard 몇 개를 던져 `HIT|MC|<family>|<had|lep>|<dataset>` 를 찍는다 — 플레이버 재생산(JMENano/BTVNano)도 같이 나오므로 registry 에 옮길 때 뺀다. DATA 는 PD 별로 모든 캠페인(`CAMP|`)을 먼저 찍어 proc 문자열을 눈으로 확인하게 했다.

### 4.4 Run 3 에서 특히 확인할 것

1. **신호 `TTHH*` 와 ttVV 5 종(`TT4b`, `TTZH`, `TTZZ`, `tHW`, `TTZToBB`)의 Summer24 중앙 생산 존재 여부.** Run 2 v15 에서 없던 여섯이 Summer24 에도 없다면 사설 생산(D17 레시피)이 Run 3 까지 늘어난다 — 그 경우 Summer24 **MiniAODv6** 부모 존재 여부부터, GT 는 `150X_mcRun3_2024_realistic_v2`. 참고: twiki 의 Run 3 NANO 레시피(Summer22/23 NanoAODv12)는 cmsDriver 에 **`--nThreads 4`** 가 들어 있다 — Run 3 중앙 cfg 를 그대로 쓰면 그 자체가 4 스레드다(Run 2 UL17 v15 원문에는 없었다).
2. **QCD 의 HT 구간 변경** → xsec 표·stitching 경계 새로.
3. **DY/W 의 binning 선택** (jet-binned vs HT-binned) — lep 용도라 두 번째 라운드.
4. **PD 분할** (`JetMET0`+`JetMET1`) — 둘을 같은 KEY 로 합치되 registry 에는 별도 row 로 두고 config 에서 합친다 (das_scan 의 KEY 는 PD 이름이므로 `JetMET0`, `JetMET1` 두 row).
5. **2025**: golden JSON 은 있다(`Cert_Collisions2025_391658_398903_Golden.json`, 110.6 fb⁻¹ 예비), MC 캠페인은 없어 Summer24 를 쓴다(PPD). 데이터 PD 집합(JetMET0/1·Muon0/1·EGamma0/1 …)과 `PromptReco-vN` 의 N 분포는 `CAMP|` 줄로 확정한다.

---

## 5. `had` / `lep` — 용도 태그

2026-09-07 에 `samples_registry.txt` 의 ttHH 행 64 개에 태그를 붙였다 (WORKSTREAM 컬럼, 기존 `--workstream` 필터로 바로 쓸 수 있고 다른 reader 는 컬럼 1·2·4 만 읽어 영향 없음):

| 태그 | 수 | 무엇 |
|---|---:|---|
| `had` | 47 | 신호 `TTHHto4b`, ttbar 3, ttbb 3, QCD 7, ttH 2, tH 2, ttV 4, ttVV 8, single top 6, diboson 3, W/Z→qq 6, DATA `JetHT`·`BTagCSV` |
| `lep` | 16 | `WJetsToLNu_HT*` 8, `DYJetsToLL_M50_HT*` 8 — leptonic selection 의 data/MC 정합 테스트용 |
| `had,lep` | 1 | `SingleMuon` — hadronic 트리거 효율의 기준 데이터셋이자 lepton CR 데이터 |

`ttV_lep` 그룹(`TTWJetsToLNu`, `TTZToLLNuNu`)과 `ST_s_lep` 은 hadronic 채널의 background 이기도 하므로 `had` 다 — 그룹 이름의 "lep" 은 붕괴 모드지 용도가 아니다. Run 3 registry 도 같은 규칙(`das_discover_run3.sh` 가 family 별 제안값을 찍는다).

**생산 순서**: `--workstream had` 로 Run 2 v15(2017UL, 2018UL) → Run 3 순. `lep` 은 hadronic 이 돌기 시작한 뒤 같은 config 에 블록으로 붙인다.

---

## 6. 다음 행동

1. lxplus 에서 §4.3 의 (0)·(1) 을 돌리고 로그(probe 6, discover 6)를 커밋 (`script/das_*.log` 는 추적 대상). 2025·2024 가 먼저다.
2. 로그로 `samples_registry_run3.txt` 작성 → §4.4 의 1 번(신호·ttVV 의 Summer24 존재) 답이 나온다.
3. §2 의 남은 "기억" 항목을 POG twiki 원문으로 확정 — jet veto map 키·MET filter 의 ecalBadCalib 보정 수치·JEC/JER 태그 버전·PU 키·트리거 경로. (golden JSON·era 경계·루미·EGM ID·GT 는 2026-09-07 에 PdmV/PPD 원문으로 확정했다.)
4. Run 3 파일 하나로 브랜치 인벤토리 스윕 → `branch_hadronic_<era>_v15_MC/Data.txt`.
5. analyzer(tempTTHH) 에 Run 3 cleaning 다섯 가지 + 두 가지 off 를 넣는 작업 항목 발행 — NtupleForge 밖이라 여기서는 목록만 (§2).
