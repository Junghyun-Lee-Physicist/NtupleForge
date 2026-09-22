# 03 — Run 3 확장 계획: NanoAODv15 위의 2022–2025, event-level 필수 항목, 데이터셋

> **목적**: ttHH → 4b 파이프라인을 Run 3 로 넓히기 위한 단일 참조. ① 범위와 결정, ② Run 2 와 달리 Run 3 에서 **반드시** 지켜야 할 event-level 항목(veto map, MET filter, jet ID 재계산 …)의 체크리스트, ③ 데이터셋을 **추정하지 않고 DAS 로 확정**하는 절차와 도구, ④ hadronic / leptonic 용도 구분(`had`/`lep` 태그)과 hadronic 우선 생산.
> **대상 독자**: Run 3 registry 를 채우고 첫 ntuple 을 만들 사람; analyzer 에 Run 3 cleaning 을 넣을 사람.
> **상태**: 살아있는 문서. 작성 **2026-09-07**, 갱신 **2026-09-16** (§6 항목 1·2·5·6: Run 3 had 스캔 2024/2025 완료, `build_from_scan_log.py` Run 3 데이터 변형 처리, `genTtbarId` 존재 확인, 브랜치 인벤토리 스윕 완료), 그 전 **2026-09-10/11** (`TT4b` = 중앙 `TT4B` 확인 §4.6, BTV UParTAK4 WP 답변 §2 행 9, 캠페인 inventory 절차 §4.3 (4) 와 결과 §4.7; 09-11 ttH(bb) 분할 샘플 3 종 VALID 29.5M 씩 → `had`, 2025 MC 캠페인 없음 DAS 확인); 같은 날 **PdmVRun3Analysis twiki r223(2026-09-07)** 과 **PPD "Run3 2025 Summary Table"(2026-01-20)** 원문(PDF)으로 era 경계·golden JSON·루미·GT·데이터 명명 규칙을 대조해 해당 행을 "실측" 으로 올렸다. 남은 "기억" 표시(veto map 키, MET filter 세부, JEC 태그, PU 키, 트리거 경로)는 POG twiki 원문 확인 전까지 **코드에 넣지 않는다**. **2026-09-07 저녁: probe·discovery 완료** — 6 era 의 캠페인 문자열 전부 DAS 로 확정(§4.2), Summer24 에 신호 `TTHH-HHto4B` 를 포함한 hadronic 세트가 **중앙 생산으로 존재**, 2022/2023 v15 는 부분 재생산(§4.5). `script/samples_registry_run3.txt` 작성(MC 77 = had 58 + lep 19, DATA 11).
> **관련**: Run 2 v15 마이그레이션 [`../09_v15_migration_log.md`](../09_v15_migration_log.md), 스캐너 [`../../script/das_scan.sh`](../../script/das_scan.sh), Run 3 discovery [`../../script/das_discover_run3.sh`](../../script/das_discover_run3.sh), 2018 확장 시 정한 multi-year 원칙 (workspace `00_CONTEXT…` §2.3).

## 결론 먼저 (BLUF)

- **버전은 하나로 간다: NanoAODv15.** Run 2 UL 재생산도 v15 이고 Run 3 (2022, 2022EE, 2023, 2023BPix, 2024) 의 최신 재생산도 v15 라, analyzer 는 **하나의 스키마**만 알면 된다. **2025 (기본 대상)**: 데이터는 T0 prompt 로 MINIAODv6/NANOv15 (GT `150X_dataRun3_Prompt_v1`), **MC 캠페인은 아직 없다** → PPD 권고대로 **Summer24 MC** (`RunIII2024Summer24NanoAODv15`, GT `150X_mcRun3_2024_realistic_v2`) 를 2025 데이터에 쓴다 (§4.2).
- **Discovery 결과 (§4.5)**: Summer24 v15 에는 우리 hadronic 세트가 **다 있다** — 신호 `TTHH-HHto4B`, `TTZH-ZHto4B`, `TTZZ-ZZto4B`, `TTBB*`(ttbb), `TTH-Hto2B-TTto4Q/-TTtoLNu2Q/-TTto2L2Nu`(ttH(bb) top-decay-split, 29.5M 씩; inclusive `TTH-Hto2B` 2.4M 은 `alt`), `THQ/THW`, QCD-HT 11 구간, V→qq, 단일톱, ttVV, 그리고 **`TT4b` 도 있다** (`TT4B_TuneCP5_13p6TeV_madgraph-pythia8`, 9.9M ev — 09-07 조사는 `TT4b*` 패턴의 대소문자 때문에 놓쳤고 09-10 에 확인, §4.6). Run 2 의 부재 6 종 **전부**가 Run 3 에서는 중앙에 있다 → Run 3 에 enriched 생산은 필요 없고 expanded id 는 sidecar 경로. 반면 **2022/2023 의 v15 재생산은 부분적**(ttbar·ttV·tW·VV·QCD-PT·DY·W→ℓν 만) 이라 v15 단일 스키마로는 2024·2025 만 지금 가능하다.
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
| **D-R3-7 · 2022/2023 보류** (PROPOSED 2026-09-07) | 첫 라운드는 **2024 + 2025 (Summer24 MC)**. 2022/2022EE/2023/2023BPix 는 v15 재생산이 부분적(§4.5)이어서 v15 만으로는 hadronic 세트를 채울 수 없다 — v12 를 섞지 않고(D-R3-2), 전체 v15 재생산이 나오거나 요청이 받아들여질 때 넣는다 | discovery 실측 2026-09-07: 네 era 모두 동일한 **70 개** 표준 데이터셋(ttbar 9, ttV 5, 단일톱 10 = t/s/tW, VV 4, QCD-PT 28, DY 8, W→ℓν 6)만 v15 |
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
| 9 | **b-tagging** | 전부 | Run 2 의 DeepJet 대신 **ParticleNet** (`Jet_btagPNetB`, 2022–2023) 과 **UParT** (`Jet_btagUParTAK4B`, 2024–). WP 와 SF 는 BTV `btagging.json.gz` (era 별). 어느 tagger 로 갈지는 결정 항목 (D-R3-7 후보). **BTV 답변 (CMS-talk "UParTAK4 working points for 2022/2023 NanoAODv15", V. Rodriguez Lorenzo · A. De Moor, 2026-09-09)**: 재-NanoAODv15 캠페인(Run 2, 2022/2023)은 Summer24 MC 셋업 위에 있으므로 **2024 용 UParTv2/UParTAK4 WP 를 2022/2023 v15 의 `Jet_btagUParTAK4B` 에 그대로 쓴다**; `Jet_btagRobustParTAK4B` 의 WP/SF(v12 시절 권고)를 UParTAK4 에 재사용하면 안 된다; SF payload 는 UParTAK4/UParTv2 + v15 재처리에 맞는 것이어야 한다. → v15 단일 스키마에서는 **UParTAK4 하나로** 2022–2025 를 갈 수 있다는 뜻. Run 2 v15 의 UParT SF 제공 여부는 별도 확인. | analyzer | BTV twiki / `btv-public.docs.cern.ch` | 규칙 + 기억 |
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
| `TTZH/TTZZ/TTWW/TTWH/TTWZ_TuneCP5_13TeV-madgraph-pythia8`, `TTTT`, `TTTW`, `TT4b` | `TTZH*`, `TTZZ*`, `TTWW*`, `TTWH*`, `TTWZ*`, `TTTT*`, `TTTW*`, `TT4b*` **+ `TT4B*`** (DAS 패턴은 대소문자 구분; 실제 이름은 `TT4B_…`, 09-10) | 신호 `TTHHto4b` 포함, **Run 3 중앙 생산 존재 여부가 핵심 질문** — 없으면 Run 2 처럼 사설 생산 결정 |
| `ST_t-channel_*`, `ST_tW_*`, `ST_s-channel_*` | `TBbarQ_t-channel_4FS_*`, `TbarBQ_t-channel_4FS_*`, `TWminusto4Q/LNu2Q/2L2Nu_*`, `TbarWplusto*`, `TBbartoLplusNuBbar-s-channel-4FS_*`, `TbarBtoLminusNuB-s-channel-4FS_*` | 붕괴 모드별로 분리됨 |
| `WW/WZ/ZZ_TuneCP5_13TeV-pythia8` | `WW_*`, `WZ_*`, `ZZ_*` (+ 붕괴별); Summer24 **확인**: `ZZto2L2Q_TuneCP5_13p6TeV_powheg-pythia8`, `WZto2L2Q_…`, `ZZto2L2Q-1Jets_…amcatnloFXFX` | 붕괴별 분리가 기본 |
| `WJetsToQQ_HT-*`, `ZJetsToQQ_HT-*` | `Wto2Q-3Jets_HT-200to400, 400to600, 600to800, 800`, `Zto2Q-4Jets_HT-*` | |
| `WJetsToLNu_HT-*` (lep) | `WtoLNu-4Jets_*` (jet-binned `1J..4J` 또는 HT-binned) | |
| `DYJetsToLL_M-50_HT-*` (lep) | `DYto2L-4Jets_MLL-50_*` (jet-/HT-binned), `DYto2L-2Jets_MLL-50_*` (NLO); Summer24 **확인**: `DYto2E-2Jets_Bin-0J-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8` (jet-binned, 렙톤 종류별) | |
| PD `JetHT`, `BTagCSV`, `SingleMuon` | `JetMET` (2022C 부터 JetHT+MET 병합), **`JetMET0`/`JetMET1`** (2023–), `Muon` (2022C 부터 SingleMuon+DoubleMuon 병합)/`Muon0`/`Muon1`, `EGamma`/`EGamma0`/`EGamma1` (2024 **확인**: EGamma0/1 C–I), `BTagMu` | BTagCSV 는 없다. PD 가 `PDi` 로 나뉜 해는 **전부** 받아야 전체 데이터 (PdmV 규칙, 실측) |

### 4.2 캠페인 문자열과 GT

근거: `das_scan.sh --probe --nano v15` 6 era (2026-09-07, `script/das_probe_<era>_v15.log`) — 아래 표의 문자열은 전부 DAS 가 돌려준 것이다. 배경 문서: PdmVRun3Analysis twiki r223, PPD "Run3 2025 Summary Table"(2026-01-20; GT·릴리스), 참조 분석(Hγγ, 2024)의 목록.

| era | MC 캠페인 (DAS, `--probe` 실측) | Data (DAS, 실측) | 비고 |
|---|---|---|---|
| **2025** | **없음 → `RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-vN`** (Summer24; PPD 권고) | `/PD/Run2025{B,C,D,E,F,G}-PromptReco-v1/NANOAOD` + **C·F 는 `-v2` 도** (disjoint run) | data GT `150X_dataRun3_Prompt_v1`; PD = JetMET0/1, Muon0/1, EGamma0/1, BTagMu |
| **2024** | `RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-vN` (`_ext1`, `_ext2` 도) | `/PD/Run2024{C..I}-MINIv6NANOv15-vN/NANOAOD` + `Run2024I-MINIv6NANOv15_v2-vN` (I 의 2 번째 prompt 처리분) | (PD, era) 당 `-vN` 은 하나(PD 마다 N 이 다름: JetMET0 F–I 는 v2, Muon0 은 v1); `_pilot` 은 제외 |
| 2023 / 2023BPix | `Run3Summer23NanoAODv15-150X_mcRun3_2023_realistic_v1-vN` / `Run3Summer23BPixNanoAODv15-150X_mcRun3_2023_realistic_postBPix_v1-vN` — **부분 재생산** | `/PD/Run2023B-NanoAODv15-v1`, `Run2023C-NanoAODv15{,_v2,_v3,_v4}-v1`(prompt v1–v4 = disjoint run), `Run2023D-NanoAODv15{,_v2}-v1` | PD = JetMET0/1, Muon0/1, EGamma0/1, BTagMu |
| 2022 / 2022EE | `Run3Summer22NanoAODv15-150X_mcRun3_2022_realistic_v1-vN` / `Run3Summer22EENanoAODv15-150X_mcRun3_2022_realistic_postEE_v1-vN` — **부분 재생산** | `/PD/Run2022{C..G}-NanoAODv15-v1` (JetMET, Muon, EGamma, BTagMu); `JetHT`·`SingleMuon` 은 A–C 만 | 2022 A–E 의 ReReco 계열 여부는 `CAMP|` 에 `ReRecoNanoAODv11`/`PromptNanoAODv10` 이 따로 있는 것으로 보아 v15 는 별도 재처리 — 입력 확인 필요(§2 #16) |

같은 접두어를 공유하는 **플레이버 재생산**이 많다(`RunIII2024Summer24NanoAODv15-JMENanoV15_…`, `-BTVNanoV15_`, `-FS_`(FastSim), `-NoPU_`, `-FlatPU0to120_`, `-EpsilonPU_`, `-EGMNanoV15_`, `-MUOPOGNano_`, `-mg35x_`). 그래서 `das_scan.sh` 는 Run 3 + v15 에서 MC 질의를 **GT 로 고정**한다(`/<primary>/<campaign>-<GT>*/NANOAODSIM`, `_ext` 와 `-vN` 만 허용) — 2026-09-07 추가.

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
# (2) HIT| 줄에서 samples_registry_run3.txt 작성 -- 2026-09-07 완료 (MC 77, DATA 11)
# (3) event/file 수: hadronic 먼저, 2025 (= Summer24 MC + Run2025 data) 부터. Run 3 era 는 registry 를 자동 선택한다.
bash script/das_scan.sh --era 2025 --nano v15 --workstream had --out script/das_ttHH_2025_v15_$(date +%Y%m%d_%H%M).log
bash script/das_scan.sh --era 2024 --nano v15 --workstream had --out script/das_ttHH_2024_v15_$(date +%Y%m%d_%H%M).log
```

(0)·(1) 은 2026-09-07 에 돌렸고 로그는 커밋되어 있다(`script/das_probe_*_v15.log`, `script/das_discover_*_v15_20260907_*.log`).

`das_discover_run3.sh` 는 family 당 wildcard 몇 개를 던져 `HIT|MC|<family>|<had|lep>|<dataset>` 를 찍는다 — 플레이버 재생산(JMENano/BTVNano)도 같이 나오므로 registry 에 옮길 때 뺀다. DATA 는 PD 별로 모든 캠페인(`CAMP|`)을 먼저 찍어 proc 문자열을 눈으로 확인하게 했다.

**(4) 캠페인 전수 inventory — 대소문자에 안전한 확인 (2026-09-11, `script/das_inventory.sh`).** 접두어 wildcard 는 DAS 가 대소문자를 구분해 놓친다(`TT4b*` ≠ `TT4B`). 그래서 캠페인의 dataset 을 **한 번에 전부** 받아(`dataset status=* dataset=/*/<campaign>*/NANOAODSIM`; DAS 가 `/*/` 를 거부하면 첫 글자 52 개로 나눠 질의) TSV 로 두고, registry 의 PRIMARY 와 자유 토큰을 **로컬에서 소문자 비교**한다. 같은 pass 에서 dataset 마다 `status`(VALID/PRODUCTION/INVALID)·nevents·nfiles·size·생성일을 기록한다 — 지금까지 손으로 조회하던 값들이다.

```bash
# lxplus, 컨테이너 밖, proxy 후.  bash 가 vim 으로 잡히는 셸에서는 /bin/bash
/bin/bash script/das_inventory.sh --campaign 'RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2*' --tag summer24_v15 \
    --registry script/samples_registry_run3.txt --grep tt4b,tthh,ttzh,ttzz,ttz,thw,thq,ttbb,sherpa,2jets,3jets
/bin/bash script/das_inventory.sh --campaign 'RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1*' --tag ul17_v15 \
    --registry script/samples_registry.txt --grep tt4b,tthh,ttzh,ttzz,ttztobb,thw,sherpa
/bin/bash script/das_inventory.sh --campaign 'RunIISummer20UL18NanoAODv15-150X_mc2018_realistic_v1*' --tag ul18_v15 \
    --registry script/samples_registry.txt --grep tt4b,tthh,ttzh,ttzz,ttztobb,thw,sherpa
```
출력: `script/das_inventory_<tag>_<stamp>.tsv`(전 dataset; 상세는 기본적으로 registry/grep 에 걸린 것만, `--details all` 로 전부), `.names.txt`, `.match.txt`(`EXACT|` / **`CASE_ONLY|`**(대소문자만 다른 이름이 있다) / `NOT_FOUND|…|hint:` / `GREP|`). `CASE_ONLY` 가 한 줄이라도 나오면 registry 의 PRIMARY 를 그 이름으로 고친다. 로그 3 개를 커밋한다(비밀 없음).

### 4.4 Run 3 에서 특히 확인할 것

1. **답이 나왔다 (§4.5)**: Summer24 v15 에 `TTHH-HHto4B`, `TTZH-ZHto4B`, `TTZZ-ZZto4B`, `THW-5FS-ctcvcp`, `TTZ-ZtoQQ-1Jets`(TTZToBB 의 대체) 가 **중앙 생산**으로 있다; `TT4b` 도 `TT4B_TuneCP5_13p6TeV_madgraph-pythia8` 이름으로 있다(09-10 확인, §4.6). Run 3 에는 enriched 생산(D17)이 필요 없고, expanded ttbar id 는 MiniAODv6 부모 위의 sidecar 경로(D-DEP1)로 간다 — 참고로 twiki 의 Run 3 NANO 레시피는 cmsDriver 에 `--nThreads 4` 가 들어 있어, 만약 Run 3 에서 NANO 를 다시 만들 일이 생기면 중앙 cfg 자체가 4 스레드다.
2. **QCD 의 HT 구간 변경** → xsec 표·stitching 경계 새로.
3. **DY/W 의 binning 선택** (jet-binned vs HT-binned) — lep 용도라 두 번째 라운드.
4. **PD 분할** (`JetMET0`+`JetMET1`) — registry 에 별도 row(KEY = PD 이름)로 두고 config 에서 합친다. **처리 버전**: prompt 2025 의 `-v1`/`-v2`(C, F), 2023C 의 `_v2/_v3/_v4`, 2024I 의 `_v2` 는 **disjoint run 범위**라 전부 config 에 넣어야 한다 — `build_from_scan_log.py` 의 `_split_data_variants` 는 (PD, era) 당 하나만 canonical 로 고르고 나머지를 주석 처리하므로 **Run 3 에서는 고쳐야 한다**(§6).
5. **2025**: golden JSON 은 있다(`Cert_Collisions2025_391658_398903_Golden.json`, 110.6 fb⁻¹ 예비), MC 캠페인은 없어 Summer24 를 쓴다(PPD). 데이터 PD 집합(JetMET0/1·Muon0/1·EGamma0/1 …)과 `PromptReco-vN` 의 N 분포는 `CAMP|` 줄로 확정한다.

### 4.5 Discovery 결과 (2026-09-07, `das_discover_run3.sh`, 표준 플레이버만)

| family | Summer24 v15 (2024·2025) | Summer22/22EE/23/23BPix v15 | registry KEY (Run 3) |
|---|---|---|---|
| 신호 | **`TTHH-HHto4B`** (+ `TTHH-TTto2L2Nu/TTtoLNu2Q-HHto2B2Tau/2B2W/2B2Z`) | 없음 | `TTHHto4b` |
| ttbar | `TTto4Q`, `TTtoLNu2Q`, `TTto2L2Nu` (+ Hdamp/MT/CR/Tune 변형, `-2Jets` FXFX, `-3Jets` MLM, BBDPS) | 같은 3 종 (+ 변형) | `TTbar_{Hadronic,SemiLep,DiLep}` |
| ttbb | `TTBBto4Q`, `TTBBtoLNu2Q`, `TTBBto2L2Nu` (powheg) | 없음 | `TTbb_{Hadronic,SemiLep,DiLep}` |
| QCD HT | `QCD-4Jets_Bin-HT-{40to70,…,2000}` 11 구간 | 없음 (QCD-PT 만) | `QCD_HT200to400 … QCD_HT2000toInf` (8) |
| ttH / tH | `TTH-Hto2B_Par-M-125`, `TTH-HtoNon2B_Par-M-125`, `THQ-4FS-ctcvcp_Par-M-125`, `THW-5FS-ctcvcp_Par-M-125` | 없음 | `ttHTobb`, `ttHToNonbb`, `tHq`, `tHW` |
| ttV | `TTZ-ZtoQQ-1Jets`(FXFXold), `TTW-WtoQQ-1Jets`, `TTLL_Bin-MLL-50`, `TTLL_Bin-MLL-4to50`, `TTNuNu`; **`TTLNu-1Jets` 는 `mg35x_` 플레이버에만** | `TTZ-ZtoQQ-1Jets`(FXFX), `TTW-WtoQQ-1Jets`, `TTLL_MLL-*`, `TTNuNu` | `TTZToQQ`(신설), `TTWJetsToQQ`, `TTWJetsToLNu`(NOT_FOUND 예정), `TTLL_MLL50`, `TTLL_MLL4to50`, `TTNuNu` |
| ttVV / 4top | `TTZH-ZHto4B`, `TTZZ-ZZto4B`(+`TTZZ`), `TTWW`, `TTWH`, `TTWZ`, `TTTT`, `TTTWminus/plus-DR1`(+DRW); **`TT4B`** (9,898,300 ev, VALID — 09-07 표에는 '없음'으로 적혔다: `TT4b*` 대소문자 미스, 09-10 수정) | 없음 | `TTZHTo4b`, `TTZZTo4b`, `TTWW`, `TTWH`, `TTWZ`, `TTTT`, `TTTWminus`, `TTTWplus` |
| 단일톱 | t-ch `TBbarQto2Q/toLNu-t-channel-4FS`, `TbarBQto2Q/toLNu…`; tW `TWminusto4Q/LNu2Q/2L2Nu`, `TbarWplusto…`; s-ch `TBbarto2Q/toLNu-s-channel`, `TbarBto…` | 10 종 (tW 6 + t-ch `TBbarQ_t-channel_4FS` 2 + s-ch `TBbartoLplusNuBbar-s-channel-4FS` 2; 이름이 Summer24 와 다름) | `ST_t_{top,antitop}_{had,lep}`, `ST_tW_{top,antitop}_{had,semilep,dilep}`, `ST_s_{top,antitop}_{had,lep}` |
| VV | `WW_`, `WZ_`, `ZZ_` pythia8 (+ 붕괴별 powheg/FXFX) | 같은 3 종 (+ `WZtoL3Nu-1Jets-4FS`) | `WW`, `WZ`, `ZZ` |
| V→qq | `Wto2Q-3Jets_Bin-HT-{100to400,400to800,800to1500,1500to2500,2500}`, `Zto2Q-4Jets_Bin-HT-…` (+ `Bin-PTQQ-*` NLO) | 없음 | `WJetsToQQ_HT400to800 … 2500toInf`, `ZJetsToQQ_…` |
| W→ℓν (lep) | `WtoLNu-4Jets_Bin-HT-*-MLNu-{0to120,120}` 12, `Bin-{1J..4J}` 4, NLO `WtoLNu-2Jets_Bin-PTLNu-*` | `WtoLNu-4Jets(_1J..4J)`, `WtoLNu-2Jets` | `WJetsToLNu_HT<bin>_MLNu<range>` (12) |
| DY (lep) | `DYto2L-4Jets_Bin-HT-*-MLL-{4to50,50to120,120}` 21, per-flavour NLO/MLM, powheg MLL 구간 | 8 종(혼합) | `DYJetsToLL_M50to120_HT<bin>` (7) |
| DATA | 2024: `JetMET0/1`, `Muon0/1`, `EGamma0/1`, `BTagMu` × C–I `MINIv6NANOv15`; 2025: 같은 PD × B–G `PromptReco-v1`(+C·F `-v2`) | 2023: 같은 PD × B, C(`_v2..v4`), D(`_v2`); 2022: `JetMET`/`Muon`/`EGamma`/`BTagMu` C–G, `JetHT`/`SingleMuon` A–C | KEY = PD |

**결론 세 가지.** ① Run 2 에서 사설 생산이 필요했던 6 종 **전부**(`TTHHto4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`, `TTZToBB`→`TTZToQQ`, 그리고 `TT4b`→`TT4B`)가 Summer24 에 있다 — Run 3 의 D17 확장은 없다. (09-07 판은 `TT4b` 를 '없음'으로 적었다. `das_discover_run3.sh` 가 `TT4b*`/`TTbbbb*` 만 찍었고 DAS 와일드카드는 대소문자를 구분해 `TT4B_…` 를 놓쳤다. 09-10 에 SL 채널 팀의 목록으로 발견, §4.6. 교훈: Run 3 이름은 b 를 `4B`/`BB` 로 쓴다 — family 접두어에 두 표기를 다 넣는다(스크립트 반영).) ② 2022/2023 v15 는 네 era 가 똑같은 70 개(표준 플레이버; 단일톱은 t/s/tW 10 종 포함)만 재생산됐다 — D-R3-7. ③ Summer24 표기: `Par-`/`Bin-`/`Fil-` 와 붕괴별 분리(`TTBBto4Q`, `TBbarQto2Q-t-channel-4FS`, `TWminusto4Q`) — KEY 를 그에 맞게 신설했다(registry 머리말).

---

### 4.6 2026-09-10 추가 확인 — SL 채널 팀의 목록과 DAS 원문

Aurore 가 전달한 Gabriel 의 1 년 전 발표(2024 Run 3 tt(SL)HH4b 시작 시점)의 dataset 목록과, 그 dataset 들의 DAS 원문(`dbs3rucio show`)에서 확인한 사실:

| dataset (Summer24 NanoAODv15, `150X_mcRun3_2024_realistic_v2`) | event | 비고 |
|---|---:|---|
| `TT4B_TuneCP5_13p6TeV_madgraph-pythia8` (`-v3`) | 9,898,300 | **우리 09-07 discovery 가 놓친 tt4b** — VALID, 34 files, 2025-03-27 |
| `TTHH-HHto4B_TuneCP5_13p6TeV_madgraph-pythia8` (`-v3`) | 9,999,300 | 신호 |
| `TTZH-ZHto4B_TuneCP5_13p6TeV_madgraph-pythia8` (`-v2`) | 9,984,820 | |
| `TTZZ-ZZto4B_TuneCP5_13p6TeV_madgraph-pythia8` (`-v3`) | 9,911,305 | |
| `TTtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8` (`-v2`) | 484,475,057 | powheg SL — FH `TTto4Q` 의 규모 참고(`das_scan` 전) |
| `TTBBtoLNu2Q_TuneCP5_13p6TeV_powheg-pythia8` (`-v2`) | 22,473,402 | ttbb SL |
| `TTH-Hto2B_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8` (`-v2`) | 2,443,910 | **작다** (Run 2 UL17 `ttHTobb` 는 수백만 대) — ttH(bb) 통계 추가 요청 후보 |

- Gabriel 의 표에 "ttZ still not produced??" 라고 적힌 것은 1 년 전 상태다. 지금은 `TTZ-ZtoQQ-1Jets_…amcatnloFXFXold`(§4.5) 가 있다.
- **교훈.** `das_discover_run3.sh` 의 family 접두어는 대소문자를 구분하는 DAS 패턴이다. Run 3 이름 규칙은 b 를 대문자로 쓴다(`TTBBto4Q`, `TTHH-HHto4B`, `TT4B`). 09-10 에 `TT4B*`, `TTBBBB*` 를 추가했다. 다른 family 에도 같은 함정이 있을 수 있으니, "없음" 결론은 `*4B*`·`*BB*` 같은 느슨한 패턴으로 한 번 더 확인한 뒤에 적는다.
- 이 표의 수치는 `das_scan.sh --era 2024 --nano v15 --workstream had` 가 돌면 `DS|…|nevents=` 로 다시 확인된다(§6 항목 1).
- **다른 접두어 구멍(09-11 점검).** family 접두어를 하나씩 대소문자 관점에서 다시 봤다. `TTtoLNu2Q*` 는 전하별 Sherpa 이름 `TTtoLminusNu2Q`/`TTtoLplusNu2Q`/`TTtoLminusNuQ` 를 못 잡는다 → `TTtoL*` 추가. 나머지(`TTHH*`, `TTto4Q*`, `TTto2L2Nu*`, `TTbb*`/`TTBB*`, `QCD-4Jets*`, `TTH*`, `THQ*`/`THW*`, `TTZ*`/`TTW*`, `TTZH*`/`TTZZ*`, single top, `WW*`/`WZ*`/`ZZ*`, `Wto2Q*`/`Zto2Q*`)는 09-07 로그에 실제 HIT 가 있으므로 표기가 맞다. 확정은 §4.3 (4) 의 inventory(`CASE_ONLY` 0 건)로 한다.
- **tt+jets 의 다른 multileg 샘플(09-07 로그에 이미 있음).** `TTto4Q-2Jets_TuneCP5_13p6TeV_amcatnloFXFX-pythia8`(+ext1; `TTto2L2Nu-2Jets_…` 도) — **MG5_aMC@NLO FxFx, tt+0,1,2 jets NLO** — 와 `TTto4Q-3Jets_TuneCP5_13p6TeV_madgraphMLM-pythia8`(LO MLM). 동료가 말한 "2jet" 은 이 FxFx 샘플일 가능성이 크다. Sherpa 는 `-4Jets-1NLO3LO`(0,1 NLO + 2,3,4 LO) 로, 우리 표기가 맞다(09-07 discovery 로그의 `TTto2L2Nu-4Jets-1NLO3LO_Tune{AHADIC,SherpaDef}_13p6TeV_sherpaMEPS` HIT, 09-07 `status=*` 조회의 FH/SL 이름, GEN 발표 slide 5). FxFx 2Jets 는 **이미 VALID 인 NLO multileg 대안**이라 Sherpa FH 가 끝나기 전의 비교 생성기로 쓸 수 있다.
- **powheg `TTto4Q` 의 계통 변형 샘플(Summer24 v15, 09-07 로그).** `Par-Hdamp-158/418`, `Par-MT-166p5…178p5`(6 점), `TuneCP5CR1/CR2`, `TuneCP5Up/Down`, `Par-ERD-On`, `BBDPS`. Run 2 와 같은 계통오차 세트가 있다 — registry 에는 넣지 않고 systematics 단계에서 쓴다.

### 4.7 Inventory 결과 (2026-09-11, `das_inventory.sh`, 세 캠페인 전수)

`script/das_inventory_{summer24_v15_20260911_0427,ul17_v15_20260911_0433,ul18_v15_20260911_0435}.tsv` (+`.names.txt`, `.match.txt`; 커밋됨).

**대소문자 점검 — 끝.** 세 캠페인 모두 `CASE_ONLY` **0 건**. 09-07 의 결론은 그대로이고, 대소문자로 놓친 것은 `TT4B` 하나였다(지금은 `EXACT`).
- Summer24 v15 (pattern `…realistic_v2*`, dataset 16,655 개): registry 78 행 중 **77 EXACT**, `NOT_FOUND` 1 = `TTWJetsToLNu`(`TTLNu-1Jets`, `mg35x_` 플레이버만 — 알던 것).
- UL17 / UL18 v15: **108 EXACT** 씩. `NOT_FOUND` 27 = 부재 6 종 + QCD-HT madgraphMLM 7 + `TTTW`(형제 `TTTWminus/plus-DR1` 있음) + **CPV 워크스트림 13**(`QCD_Pt-*_EMEnriched` 8, `QCD_Pt-*_MuEnriched*` 2, `ST_tW_antitop_5f_NoFullyHadronicDecays_…PDFWeights`, `TTJets_TuneCP5_13TeV-madgraphMLM`(v15 는 `…amcatnloFXFX` 만), `TTZToQQ_TuneCP5_13TeV_amcatnlo`(밑줄 판; v15 는 `-amcatnlo` 판만)). 6 + 7 + 1 + 13 = 27. CPV 쪽 v15 이행 때 쓸 목록이다.

**Run 2 v15 의 형제(hint 로 드러난 것).**
| 없는 것 | v15 에 있는 이웃 이름 | UL17 / UL18 event | 판단 |
|---|---|---:|---|
| `TTHHTo4b` | `TTHH_TuneCP5_13TeV-madgraph-pythia8` (HH 붕괴 포괄) | 360k / 500k, 파일 1–2 개 (2025-10) | 시험 생산 수준 — 대체 불가 |
| `TTZHTo4b`, `TTZZTo4b` | `TTZH_…`, `TTZZ_…` (붕괴 포괄) | 350k / 500k, 327k / 498k | 같음 — 대체 불가 |
| `TTZToBB` | **`TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8`** | **13.98M / 19.82M**, VALID | **결정 09-11 (D-2026-09-11-ttz-hadronic-from-ttzqq): `TTZToQQ` 를 쓴다** — Run 3 와 같은 처리(Z→qq 포괄: bb + cc + light; 4b 선택에는 bb 가 직접, cc/light 가 mistag 로 들어오므로 v9 의 bb 전용보다 완전하다). Z→bb ≈ 22 % → 3.0M / 4.3M vs 전용 7.1M / 10.0M — 부차 background 에 충분. registry: `TTZToQQ`(`ttHH,had`, Run 3 와 같은 KEY), `TTZToBB` → `ttHH,alt`(v9 전용). **요청 목록 6 → 5 종**(14 datasets, ≈108M) |
| `tHW`, `TT4b` | 없음 (hint 공백) | — | 요청 유지 |

**Summer24 v15 수치 (DAS 2026-09-11, status / nevents).**
| 샘플 | status | nevents | 비고 |
|---|---|---:|---|
| `TTto4Q_TuneCP5_13p6TeV_powheg-pythia8` (-v2) | VALID | 472,535,695 | **Sherpa 통계 요청의 기준** |
| `TTtoLNu2Q_…powheg` (-v2) / `TTto2L2Nu_…powheg` (-v3; -v2 는 INVALID 0) | VALID | 484,475,057 / 470,123,263 | |
| `TTto4Q-4Jets-1NLO3LO_TuneSherpaDef_…sherpaMEPS` | **PRODUCTION** | **100,807,210** (09-07: 80.5M) | 4 일에 +20M — 활발히 생산 중 |
| `TTto4Q-4Jets-1NLO3LO_TuneAHADIC_…` | INVALID | 0 | |
| SL Sherpa: `TTtoLminusNu2Q-…AHADIC` / `TTtoLplusNuQ-…SherpaDef` | VALID | 245.9M / 249.8M | `TTtoLplusNu2Q-…AHADIC` PROD 46.7M, `TTtoLminusNuQ-…SherpaDef` PROD 35.5M |
| DL Sherpa AHADIC / SherpaDef | VALID | 499.1M / 496.1M | |
| **`TTto4Q-2Jets_…amcatnloFXFX`** (-v2 + `_ext1-v2`) | VALID | 196.4M + 198.9M = **395M** | NLO multileg 대안, **지금 사용 가능** → registry `TTbar_Hadronic_FxFx2J` (alt) |
| `TTto4Q-3Jets_…madgraphMLM` | VALID | 202.2M | LO multileg → `TTbar_Hadronic_MLM3J` (alt) |
| `TTBBto4Q` / `TTBBtoLNu2Q` / `TTBBto2L2Nu` | VALID | 15.0M / 22.5M / 12.5M | `TuneCP5Up/Down`, `CR2` 변형은 PRODUCTION (2026-08/09) |
| `TT4B` / `TTHH-HHto4B` / `TTZH-ZHto4B` / `TTZZ-ZZto4B` | VALID | 9.90M / 10.00M / 9.98M / 9.91M | |
| `THQ-4FS-ctcvcp` / `THW-5FS-ctcvcp` | VALID | 20.0M / 15.0M | 2026-02 생산 |
| **`TTH-Hto2B-TTto4Q` / `-TTtoLNu2Q` / `-TTto2L2Nu`** (`_Par-M-125_…powheg`, -v2) | VALID | **29.62M / 29.22M / 29.57M** | top-decay-split ttH(bb) (2026-03-23/25 생산; 09-11 08:57 `--grep tth-hto2b-tt` 조회). 셋이 함께 inclusive 를 대체 → registry `ttHTobb_had / _semilep / _dilep` (`had`) |
| `TTH-Hto2B_Par-M-125` (inclusive) | VALID | 2.44M | 분할 세트의 1/36 → `ttHH,alt` 로 내림(키는 유지). 분할 세트와 **함께 쓰지 않는다**(이중 계수) |
| `TTH-HtoNon2B_Par-M-125_…powheg` | VALID | 54.0M | (`-1Jets_…amcatnloFXFX-madspin` 판도 있음) |
| `TTZ-ZtoQQ-1Jets_…amcatnloFXFXold` | VALID | 4.08M | 작다. `TTZ-ZtoQQ-1J_…madgraphMLM` 9.45M VALID → `TTZToQQ_MLM` (alt); `TTZ-ZtoQQ-TTtoLNu2Q-1Jets` PROD 3.9M (SL 전용) |
| `TTW-WtoQQ-1Jets_…amcatnloFXFXold` | VALID | 6.21M | |

Summer24 상세 316 행 중 VALID 269 / PRODUCTION 21 / INVALID 26 — INVALID 는 대부분 `-v2` 가 `-v3` 로 대체된 옛 판(예: `TTto2L2Nu` -v2)이라 "최고 -vN" 규칙으로 걸러진다.

**2025 MC 캠페인 (09-11 확인).** `dasgoclient -query "dataset status=* dataset=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/RunIII2025*/NANOAODSIM"` → **빈 결과**(status=* 포함). PPD 의 "2025 는 Summer24 MC 로" 가 DAS 에서도 확인됐다. `--era 2025` 는 계속 Summer24 를 스캔한다.

**ttH(bb) 분할 샘플 (09-11 08:57 CEST, `das_inventory_tth_split_20260911_0857.tsv`, lxplus 에 생성 — 커밋 필요).** 세 개 모두 VALID, 각 ~29.5M(파일 318–321, 0.13 TB), 2026-03-23/25 생산. 합 88.4M 으로 inclusive `TTH-Hto2B`(2.44M) 의 36 배. ttbar 와 같은 방식(`TTto4Q / TTtoLNu2Q / TTto2L2Nu`)으로 세 채널을 모두 `had` 에 넣는다 — SL·DL top 도 hadronic 선택을 통과할 수 있으므로 `TTto4Q` 하나만 쓰면 안 된다. inclusive 는 `alt` 로 내리고 키만 유지(D-R3-9). 결과: **Run 3 의 ttH(bb) 문의는 사라진다** — 요청도 문의도 없음.

**결론.** ① 이름·대소문자 문제는 닫혔다. ② Run 3 는 요청할 것이 없고 문의는 Sherpa FH 하나만 남는다(완료·통계·판); ttH(bb) 는 분할 샘플 3 종으로 해결. ③ Run 2 요청은 **5 종**(`TTHHto4b`, `TT4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`) — `TTZToBB` 는 v15 의 `TTZToQQ` 로 대체(09-11 결정). 같은 날 밤 2016 을 점검해 **네 era-half 의 부재 목록이 동일**함을 확인했고 요청 범위를 full Run 2 로 넓혔다: **28 datasets ≈162M**([`../09_v15_migration_log.md`](../09_v15_migration_log.md) 16 절). ④ Sherpa FH 가 끝나기 전의 생성기 비교는 FxFx `TTto4Q-2Jets`(395M) 로 지금 시작할 수 있다. ⑤ 2025 MC 캠페인은 없다(DAS 확인).

## 5. `had` / `lep` — 용도 태그

2026-09-07 에 `samples_registry.txt` 의 ttHH 행 64 개에 태그를 붙였다 (WORKSTREAM 컬럼, 기존 `--workstream` 필터로 바로 쓸 수 있고 다른 reader 는 컬럼 1·2·4 만 읽어 영향 없음):

| 태그 | 수 | 무엇 |
|---|---:|---|
| `had` | 47 | 신호 `TTHHto4b`, ttbar 3, ttbb 3, QCD 7, ttH 2, tH 2, ttV 4, ttVV 8, single top 6, diboson 3, W/Z→qq 6, DATA `JetHT`·`BTagCSV` |
| `lep` | 16 | `WJetsToLNu_HT*` 8, `DYJetsToLL_M50_HT*` 8 — leptonic selection 의 data/MC 정합 테스트용 |
| `had,lep` | 1 | `SingleMuon` — hadronic 트리거 효율의 기준 데이터셋이자 lepton CR 데이터 |

`ttV_lep` 그룹(`TTWJetsToLNu`, `TTZToLLNuNu`)과 `ST_s_lep` 은 hadronic 채널의 background 이기도 하므로 `had` 다 — 그룹 이름의 "lep" 은 붕괴 모드지 용도가 아니다. **Run 3 registry** (`samples_registry_run3.txt`, 2026-09-07; `TT4b` 행 09-10 추가; 09-11 `alt` 4 행 + ttH(bb) 분할 3 행, inclusive `ttHTobb` → `alt`): MC 85 = `had` 61 + `lep` 19 + `alt` 5, DATA 11 (`JetMET0/1` had, `Muon0/1` had,lep, `EGamma0/1` lep; 2022 는 `JetMET`/`Muon`/`EGamma`/`JetHT`/`SingleMuon`). `--era 2025 --workstream had` 는 MC 61 + DATA 4 를 고른다(09-11 이후; 그 전 58/59).

**생산 순서**: `--workstream had` 로 Run 2 v15(2017UL, 2018UL) → Run 3 순. `lep` 은 hadronic 이 돌기 시작한 뒤 같은 config 에 블록으로 붙인다.

---

## 6. 다음 행동

1. ~~**event/file 수 스캔**~~ **끝남 (2026-09-16, lxplus, `runlog.sh` 기록).** `das_scan.sh --era 2024|2025 --nano v15 --workstream had` →
   `script/das_ttHH_2024_v15_20260916_0859.log`, `script/das_ttHH_2025_v15_20260916_0900.log`(실행 기록 `script/runlogs/run_das_scan_2024_had_*.log`,
   `run_das_scan_2025_had_*.log`, EXIT 0). 선택 65 = MC 61 + DATA 4, RESULT EXACT 64, NOT_FOUND 1 = `TTWJetsToLNu`(예상대로, `mg35x_` 플레이버만).
   MC 60 dataset 은 키당 정확히 1 개(ext·복수 버전 없음). DATA 는 PD 4 개 × 8 dataset: 2024 `Run2024C..I-MINIv6NANOv15-v1|v2` + `Run2024I-MINIv6NANOv15_v2-v1|v2`,
   2025 `Run2025B..G-PromptReco-v1` + `Run2025C/F-PromptReco-v2`. **DBS `-vN` 꼬리는 PD 마다 다르다**(2024F/G: JetMET0 `-v2`, Muon0 `-v1`; 2024I: JetMET0
   `-v2`, JetMET1 `-v1`) → DATA 행 이름은 반드시 스캔 로그에서 가져온다. 2024 JetMET0 합계 1,210,265,110 ev, 2025 JetMET0 합계 1,190,559,370 ev.
   ~~**남은 결정**: `TTWJetsToLNu` 를 (a) `mg35x_` 플레이버 dataset 을 PRIMARY 로 받아들이거나 (b) ERAS 에서 2024/2025 를 빼거나.~~ **09-17 AI 제안 (a) 를 PINNED
   전체 경로로 구현, 09-18 실제 스캔으로 확인**(`script/das_ttHH_2024_v15_20260918_0803.log`: EXACT 64 + PINNED 1, NOT_FOUND 0; D-2026-09-17-ttwlnu-pinned 는
   사용자 veto 전까지 PROPOSED). 그 로그로 **첫 2024 config 초안 2 개**를 냈다(09-19, `build_from_scan_log.py --data-branch-file` 로 MC/Data 분리):
   `script/config_das_ttHH_2024_v15_20260918_0803_MC.yaml.draft`(MC 61 dataset, 19,322 files, 13.95 TB, jobID `ttHH2024_v15_had_MC_v1`,
   `branch_hadronic_2024_v15_MC.txt`), `..._Data.yaml.draft`(Data 32 = JetMET0/1 + Muon0/1 × 8, 7,811 files, `ttHH2024_v15_had_Data_v1`,
   `branch_hadronic_2024_v15_Data.txt`), review 표 `script/review_das_ttHH_2024_v15_20260918_0803.{md,tsv}`(CRAB 10,000-job guard OK, 최대 2,532 files).
   **검토 뒤 사용자가 `crabConfig/` 로 복사**(도구는 덮어쓰지 않는다): Muon0/1 을 had 생산에 넣을지(registry 태그 `had,lep`), `units_per_job`, 출력 사이트, `TTWJetsToLNu`.
   2025 는 같은 명령을 `script/das_ttHH_2025_v15_20260916_0900.log` 에 돌리면 되지만 그 로그에는 NOT_FOUND 1(`TTWJetsToLNu`, PINNED 도입 전)이 있어 재스캔이 먼저다.
2. **`build_from_scan_log.py` 의 Run 3 대응** — (a)·(b) **끝남 (2026-09-16)**: `--data-variants {auto,canonical,all}` 추가, `auto` 는 Run 3 era
   (`RUN3_ERAS`)에서 `all` = (PD, era) 당 하나만 남기는 규칙을 끄고 모든 DBS 변형을 `<PD>_<processed string>` 키의 독립 행으로 둔다(2024I 의 `-v2` + `_v2-v1`,
   2025C/F 의 `-v1` + `-v2` 전부 유지; 고치기 전에는 `Run2025C-PromptReco-v1` 155M ev 가 alternate 로 밀렸다). Data 플레이버 `BTVNano`/`JMENano` 는
   제외하고 review 표에 나열(고치기 전에는 Run 2 v15 `JetHT_Run2018A` 의 canonical 이 알파벳순 첫 항목 `UL2018_BTVNanoAODv15-v1` 이었다);
   canonical 매칭은 META 의 `_MiniAODv2_` 를 뺀 v15 문자열도 받는다. `DEFAULT_EXCLUDE` 에 Run 3 플레이버 토큰 추가. 검증: 2024/2025 로그로 review 표
   32 DATA 행, 2018UL 09-03 로그로 JetHT 4 era 가 `UL2018_NanoAODv15-v2` 로 잡힘, NOT_FOUND 를 뺀 2024 로그 사본으로 `--emit-config` dry-run(YAML 파싱 OK).
   (c) `_meta` 의 lumi·골든 JSON 은 **미착수**.
3. **xsec (D-R3-6)** — 13.6 TeV 단면적 표 `samples_2025.json`(= Summer24) 신설: XSDB + GenXSecAnalyzer; QCD-HT·V→qq·DY 구간이 Run 2 와 다르므로 전부 새로. 새 키 `ttHTobb_had / _semilep / _dilep` 는 σ(ttH)×BR(H→bb)×BR(tt→4Q / ℓν2Q / 2ℓ2ν) (D-R3-9); `alt` 행(FxFx/MLM/Sherpa tt+jets, `TTZToQQ_MLM`, inclusive `ttHTobb`)도 비교용으로 값이 필요하다.
   **참고값(사용자 제공, 2026-09-17, 어떤 문서의 Table 5 인지는 미확인 → 출처 확정 전에는 표에 넣지 않는다)**: `TTto2L2Nu` 98.58 pb, `TTtoLNu2Q` 406.3 pb, `TTto4Q` 418.6 pb (NNLO 표기, 셋의 합 923.5 pb), `TbarWplusto2L2Nu` 4.691 pb (NLO+NNLL 표기). 같은 표가 Run 3 중앙 ttbar 를 붕괴 분할 3 종으로 쓰는 것을 보여 주므로 D-R3-9(ttH 도 분할 3 종) 를 사용자가 확정했다.
4. ~~**`TT4b` 결정**~~ — **해소 (2026-09-10)**: 중앙 `TT4B_TuneCP5_13p6TeV_madgraph-pythia8`(Summer24 v15, 9.9M) 를 쓴다; registry 에 `TT4b` 행 추가(§4.6). 대체·사설 생산 논의는 필요 없다.
5. **expanded ttbar id (Run 3)** — 전 샘플이 중앙에 있으므로 sidecar 경로: Summer24 **MiniAODv6** 부모에 `TtbarIdExtender` → `matchTtbarId`. `genTtbarId` 는 Run 3 v15 에 **있다**(Int_t; `script/inventory/inv_Summer24_v15_MC.tsv`, 2026-09-16 스윕).
6. ~~**Run 3 브랜치 인벤토리 스윕**~~ **끝남 (2026-09-16)**: Summer24 MC 3(TTto4Q, TTBB, TTHH) + 2024 Data 9 era-row + 2025 Data 9 era-row, 전부 OK(`script/inventory/inv_2024*_v15_*.tsv`, `inv_2025*`, `inv_Summer24_v15_MC*.tsv`; `script/runlogs/run_sweep_run3_2016_20260916_071717.log`). 브랜치 목록 초안 `branches/branch_hadronic_2024_v15_{MC,Data}.txt`, `branch_hadronic_2025_v15_Data.txt` 와 HLT 표는 `../08_branch_schema_migration.md` §7.
7. **§2 의 남은 "기억" 항목** — jet veto map 키·MET filter 의 ecalBadCalib 보정 수치·JEC/JER 태그 버전·PU 키·트리거 경로를 POG twiki 원문으로 확정. (golden JSON·era 경계·루미·EGM ID·GT·캠페인 문자열은 2026-09-07 에 확정했다.)
8. analyzer(tempTTHH) 에 Run 3 cleaning 5 + off 2 를 넣는 작업 항목 발행 — NtupleForge 밖이라 여기서는 목록만 (§2).
