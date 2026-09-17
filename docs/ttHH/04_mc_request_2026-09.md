# 04 — MC 생성 요청 (2026-09, Higgs MC contact 앞)

> **목적**: ttHH→4b fully hadronic 채널을 위해 중앙 MC 생성에 **무엇을 요청했는지**와 **왜 그것만 요청했는지**를
> 한 곳에 남긴다. 보낸 메일 본문을 그대로 보존하므로, 답장이 오거나 생산이 시작될 때 이 문서가 대조 기준이 된다.
> **대상 독자**: 요청 상태를 추적할 사람, 답장을 받아 후속 작업을 할 사람.
> **상태**: 살아있는 문서. 작성 **2026-09-14**, 갱신 **2026-09-16**(2016 열을 MiniAODv2 부모 수치로 교체), **09-17**(§4 데이터 PD: v15 JetHT 2016 dataset 9 개와 B ver1/ver2 run 범위). 메일 발송 여부와 답장은 아래 §5 에 기록한다.
> **관련**: 조사 근거 [`03_run3_plan.md`](03_run3_plan.md) §4.6·§4.7, [`../09_v15_migration_log.md`](../09_v15_migration_log.md)
> 10·15·16 절, 결정 [`../03_DECISIONS.md`](../03_DECISIONS.md) D-2026-09-11-ttz-hadronic-from-ttzqq ·
> D-2026-09-11-run2-scope-2016, 슬라이드 `~/claude/NtuplizerDev/ttHH_latex/GenRequest_Sep2026/`.

## 결론 먼저 (BLUF)

두 가지를 요청한다. **Run 2 는 5 종 28 dataset 의 NanoAODv15 생성**(네 era-half 전부, 약 162M event), **Run 3 는
Sherpa tt+jets 계열**(진행 중인 4 종의 완성 + Sherpa tt+bb / tt+4b 신규)이다. 그 밖에는 요청하지 않는다. 조사 결과
나머지는 이미 중앙에 있거나(이름만 다름), 대체 샘플로 해결했거나, 우리 영역에서 기여가 작다.

수신: Hbb MC contact. 근거 조사는 2026-09-03 / 09-07 / 09-11 / 09-16 의 DAS 조회이고 event 수는 그 시점 값이다.

## 1. Run 2 요청 (5 종, 28 dataset)

NanoAODv9 에는 있고 NanoAODv15 에는 없다. MiniAODv2 부모는 DAS 에 있으므로 NANO step 만 남았다.

| 샘플 | 16preVFP | 16postVFP | UL17 | UL18 |
|---|---:|---:|---:|---:|
| `TTHHTo4b_TuneCP5_13TeV-madgraph-pythia8` (신호) | 5.0M | 4.8M | 9.9M | 9.6M |
| `TT4b_TuneCP5_13TeV_madgraph_pythia8` | 4.8M | 4.8M | 9.5M | 9.8M |
| `TTZHTo4b_TuneCP5_13TeV-madgraph-pythia8` (+ext1) | 5.0M | 5.0M | 10.0M | 9.8M |
| `TTZZTo4b_TuneCP5_13TeV-madgraph-pythia8` (+ext1) | 5.0M | 5.0M | 9.8M | 9.9M |
| `THW_ctcvcp_5f_Hincl_TuneCP5_13TeV_madgraph_pythia8` | 7.5M | 7.5M | 15.0M | 15.0M |
| **era-half 당 7 dataset** | **27.2M** | **27.1M** | **54.2M** | **54.1M** |

네 열 모두 **MiniAODv2 부모의 event 수**다(2017/2018: DAS 2026-09-07, 2016: DAS 2026-09-16
`script/das_inventory_ul16pre_miniaodv2_20260916_0856.tsv` · `script/das_inventory_ul16post_miniaodv2_20260916_0857.tsv`,
실행 기록 `script/runlogs/run_ul16pre_miniaodv2_20260916_065618.log` · `run_ul16post_miniaodv2_20260916_065754.log`).
2016 부모는 모두 VALID 이고, 정확한 값은 preVFP `TTHHTo4b` 4,950,000 · `TT4b` 4,801,000 · `TTZHTo4b` 2,496,000 + ext1 2,500,000 ·
`TTZZTo4b` 2,500,000 + ext1 2,500,000 · `THW` 7,498,000 (합 27,245,000), postVFP `TTHHTo4b` 4,798,000 · `TT4b` 4,848,000 ·
`TTZHTo4b` 2,500,000 + ext1 2,500,000 · `TTZZTo4b` 2,468,000 + ext1 2,500,000 · `THW` 7,484,000 (합 27,098,000). 2016 v9 수치(09-11)와의
차이는 preVFP `THW` 7.4M → 7.5M 한 칸뿐이라 합계 약 162M(정확히 162.6M)은 그대로다. 캠페인 이름은
`RunIISummer20UL16MiniAODAPVv2-106X_mcRun2_asymptotic_preVFP_v11-v2`(ext1 은 `_v11_ext1-v2`) 와
`RunIISummer20UL16MiniAODv2-106X_mcRun2_asymptotic_v17-v2`(ext1 은 `_v17_ext1-v2`) 이다.
네 era-half 를 한 번에 요청하는 근거는 네 v15 캠페인의 `NOT_FOUND` 키 집합이 diff 0 으로 동일하다는 것이다
(D-2026-09-11-run2-scope-2016).

## 2. Run 3 요청 (Sherpa tt 계열)

| 요청 | 상태 (DAS 2026-09-11) |
|---|---|
| `TTto4Q-4Jets-1NLO3LO_TuneSherpaDef_13p6TeV_sherpaMEPS` | PRODUCTION 약 101M |
| `TTtoLminusNuQ-4Jets-1NLO3LO_TuneSherpaDef_…` | PRODUCTION 약 36M |
| `TTtoLplusNuQ-4Jets-1NLO3LO_TuneSherpaDef_…` | VALID 약 250M |
| `TTto2L2Nu-4Jets-1NLO3LO_TuneSherpaDef_…` | VALID 약 496M |
| Sherpa tt+bb (4FS), fully hadronic | **없음** (powheg `TTBBto4Q` 만 존재) |
| Sherpa tt+4b | **없음** (madgraph `TT4B` 만 존재) |

세 붕괴 채널을 **같은 variant 로** 요청하는 이유: 우리는 FH 뿐 아니라 SL·DL 도 배경으로 쓴다(lepton 을 놓치면
hadronic selection 을 통과한다). 그런데 **어느 variant 도 세 채널이 완성되어 있지 않다** — `TuneSherpaDef` 는 FH 와
ℓ⁻ 가 생산 중이고, `TuneAHADIC` 는 FH 가 INVALID 이며 ℓ⁺ 가 생산 중이다. 채널마다 다른 hadronisation 모델을 섞을 수
없으므로 한쪽으로 통일해 완성해 달라는 형태로 요청했다.

함께 물은 것: ① 권장 variant, ② 목표 통계(powheg `TTto4Q` 의 약 473M 을 기준으로 제시), ③ `TuneSherpaDef` 의 SL
이름이 `TTtoLminusNuQ`/`TTtoLplusNuQ` 인데 `TuneAHADIC` 는 `TTtoLminusNu2Q`/`TTtoLplusNu2Q` 인 것이 오타인지.

## 3. 요청하지 **않은** 것과 그 이유

| 항목 | 이유 |
|---|---|
| `TTZToBB` (v15 없음, 네 era-half 전부) | v15 에 있는 inclusive `TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8` 로 대체. Run 3 처리(`TTZ-ZtoQQ-1Jets`)와 같아지고, Z→cc·light 도 mistag 로 4b 선택에 들어오므로 hadronic 채널에는 더 완전하다. D-2026-09-11-ttz-hadronic-from-ttzqq |
| QCD-HT 7 구간 | 이름만 다르고 네 v15 캠페인에 모두 존재(`QCD_HT<bin>_TuneCP5_PSWeights_13TeV-madgraph-pythia8`). registry PRIMARY 를 그 이름으로 바꿨다 |
| `TTTW` | v15 에 전하 분할판 `TTTWminus/plus-DR1_TuneCP5_13TeV_amcatnlo-pythia8` 으로 존재 |
| Run 3 의 나머지 hadronic 목록 전부 | Summer24 v15 에 중앙 생산으로 있음(신호 `TTHH-HHto4B`, `TTBBto4Q`, `TT4B`, ttH(bb) top-decay-split 3 종 등) |
| Run 2 Sherpa tt+jets | semileptonic v9 만 존재. 재생성 요청은 부담이 크고 분석에 필수가 아니다(그룹 의견 2026-09-10) |
| Sherpa V+jets 의 hadronic V 붕괴 | Summer24 의 Sherpa V+jets 는 `WtoENu/WtoMuNu/WtoTauNu-5Jets`, `DYto2E/2Mu/2Tau-5Jets` 뿐이라 W→qq·Z→qq 판이 없다. 다만 b-tag 4 개 이상 영역에서 V+jets 기여는 QCD·tt 대비 작아 요청하지 않았다 |
| Sherpa QCD multijet | 중앙에는 tuning 용 flat-pT(`QCD_Bin-PT-10toInf_Par-PT-Flat_TuneSherpaLEP`)뿐이다. 분석용 생성은 CPU 가 과도하고 QCD 는 데이터 기반으로 추정한다 |
| single top / 하드로닉 VV / ttV / ttVV / four top 의 Sherpa 판 | CMS 중앙 생산 전례가 없고 우리 영역 기여가 작다 |
| 중앙 NanoAOD 에 `GenHFHadronMatcher` 출력 포함 | 초안에 있었으나 **뺐다**(사용자 판단 2026-09-14): 일부 샘플만 가져도 우리는 어차피 전 샘플에 대해 직접 만들어야 하므로 이점이 없다 |

## 4. 우리 쪽에 남는 일 (승인 여부와 무관)

**2026-09-17 사용자 결정**: 같은 5 종을 MiniAODv2 부모에서 직접 만드는 enriched 생산(TTHHGenCategoryTools D17)을 중앙 요청과 **병행**한다.
답장을 기다리지 않고, 중앙본이 오면 같은 부모에서 나온 두 산출물을 교차 검증한다(`../03_DECISIONS.md` D-2026-09-17-run2-v15-two-tracks).

- ~~**2016 MiniAODv2 부모 조회.**~~ **끝남 (2026-09-16).** `das_inventory.sh --tier MINIAODSIM` 으로 두 캠페인을 조회해 §1 표를
  MiniAODv2 수치로 바꿨다. 두 캠페인 모두 registry 136 키 전부 EXACT(`NOT_FOUND` 0) 였다. 즉 v15 에 없는 5 종뿐 아니라
  `TTZToBB`·CPV 13 종 등 registry 의 모든 샘플이 UL16 MiniAODv2 에는 있다.
- **2016 을 분석에 넣는 비용은 샘플 요청만이 아니다.** analyzer(`tempTTHH`)에는 `data/samples_2017UL.json` 과
  `samples_2018UL.json` 만 있다. 2016 을 쓰려면 xsec 표 2 개(preVFP/postVFP), 2016 루미(현재 `LUMI_SOURCES.md` 는
  2017–2018 만 인용원을 정리했다), golden JSON, 트리거 경로·효율, b-tag SF, JEC/JER 을 전부 2016 용으로 추가해야 한다.
  **요청은 지금 해 두고 분석 확장은 별도 작업으로 계획한다.**
- **데이터 PD.** registry 의 `JetHT`/`BTagCSV` 행에는 2016 을 넣지 않았다. CPV 행이 쓰는 run-era 분할 패턴
  (`<PD>_Run2016B-ver1` …)과 DAS 스캔이 먼저다. **v15 의 JetHT 2016 dataset 9 개는 확정됐다**(2026-09-16/17,
  `script/runlogs/run_discover_ul16_jetht_v15_*.log`, `run_runs_ul16B_v15_*.log`): preVFP(HIPM) `Run2016B-HIPM_UL2016_NanoAODv15-v1`
  (= v9 의 ver1: run 272760–273017, 9,726,665 ev, 11 file), `Run2016B-HIPM_UL2016_NanoAODv15_v2-v1`(= ver2: run 273150–275376,
  133,752,091 ev, 145 file), `Run2016C/D/E/F-HIPM_UL2016_NanoAODv15-v1`; postVFP `Run2016F/G/H-UL2016_NanoAODv15-v1`. B 의 두 dataset 은
  run 이 겹치지 않으므로 둘 다 넣는다. registry 행 작성만 남았다(`BTagCSV` 는 별도 discovery 필요).
- **`TTZToQQ` 로 바꾼 데 따른 xsec.** `TTZToBB` 의 861 fb 항목이 AN Tab.9 의 ttZ 841 fb 와 어긋난다는 **기존 열린
  항목**(`tempTTHH/docs/CHANGELOG.md`, `00_START_HERE.md` §4)이 그대로 이어진다. 새 항목은 σ(ttZ)×BR(Z→qq) 이므로
  정의를 이때 확정한다.
- **`TTTW`.** v15 에서 전하 분할이라 KEY 두 개와 xsec 두 개가 필요하다(요청 대상 아님, registry 주석에 기록).

## 5. 발송·답장 기록

| 날짜 | 사건 | 비고 |
|---|---|---|
| 2026-09-14 | 메일 본문 확정 (§6) | 발송 여부는 확인 후 여기 기록 |

## 6. 보낸 메일 본문 (영문, 확정본)

> **Subject: Sample request for the ttHH(bbbb) fully hadronic analysis**
>
> Dear all,
>
> My name is [ name ] and I am working on the ttHH(4b) fully hadronic analysis. I am writing to you because I found
> your address listed as the Hbb MC contact. I apologise if this request should be directed elsewhere, and in that
> case I would be very grateful if you could point me to the right place.
>
> The other channels of our analysis have already gone through their approval talk, and I share the CADI line for
> reference (HIG-24-016).
>
> For the hadronic channel we plan to use NanoAODv15 for both Run 2 and Run 3. Our signal region will require at
> least 8 jets and at least 4 b-tagged jets, so we use samples covering that region.
>
> For this analysis I would like to request the central production of the following samples.
>
> **1) Run 2**
>
> The five samples below exist in NanoAODv9 but not in NanoAODv15. Their MiniAODv2 parents are all on DAS, so only
> the NANO step is missing.
>
> * `TTHHTo4b_TuneCP5_13TeV-madgraph-pythia8` (signal)
> * `TT4b_TuneCP5_13TeV_madgraph_pythia8`
> * `TTZHTo4b_TuneCP5_13TeV-madgraph-pythia8` (+ext1)
> * `TTZZTo4b_TuneCP5_13TeV-madgraph-pythia8` (+ext1)
> * `THW_ctcvcp_5f_Hincl_TuneCP5_13TeV_madgraph_pythia8`
>
> This is for all four era-halves (UL16 preVFP, UL16 postVFP, UL17, UL18). We scanned the four campaigns completely
> and the list of missing samples is exactly the same in each, so we request them together.
>
> For reference, `TTZToBB` has no v15 either, but we plan to use the inclusive
> `TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8`, which is available in v15, instead, so we have left it out of the
> request. QCD-HT and tttW are present in all four campaigns under different names, and we will use those as they
> are.
>
> **2) Run 3**
>
> For Run 3 we would like to try the Sherpa tt+jets samples. We use all three decay channels as backgrounds, so we
> need the following samples within the same variant.
>
> * `TTto4Q-4Jets-1NLO3LO_TuneSherpaDef_13p6TeV_sherpaMEPS` (about 101M, in production)
> * `TTtoLminusNuQ-4Jets-1NLO3LO_TuneSherpaDef_13p6TeV_sherpaMEPS` (about 36M, in production)
> * `TTtoLplusNuQ-4Jets-1NLO3LO_TuneSherpaDef_13p6TeV_sherpaMEPS` (about 250M, done)
> * `TTto2L2Nu-4Jets-1NLO3LO_TuneSherpaDef_13p6TeV_sherpaMEPS` (about 496M, done)
> * Sherpa tt+bb (4FS), fully hadronic (counterpart of the central powheg `TTBBto4Q`, no Sherpa version exists)
> * Sherpa tt+4b (counterpart of the central madgraph `TT4B`, no Sherpa version exists)
>
> For the `TuneAHADIC` version, the fully hadronic sample is INVALID and the l+ semileptonic one is in production.
> If you could let us know which variant you recommend, we will follow that choice. On statistics, the level of the
> powheg `TTto4Q` sample (about 473M) would be ideal for us, but if you could tell us what level you are aiming for
> we will take it into account in our plans.
>
> One small thing to confirm: the `TuneSherpaDef` semileptonic samples are named `TTtoLminusNuQ` and
> `TTtoLplusNuQ`, while the `TuneAHADIC` ones are named `TTtoLminusNu2Q` and `TTtoLplusNu2Q`. Given the final state
> the latter looks correct to me, so could you confirm whether there is a typo in the names?
>
> Thank you very much for reading this long message. I would be grateful if you could let me know how best to
> proceed.
>
> Best regards,
> [ name ]

작성 경위: 초안은 한국어로 쓰고 사용자가 직접 검토·수정한 뒤 영역했다. 사용자 수정으로 빠진 것은 event 수 나열
(첨부 슬라이드로 이관), Run 3 의 현황 설명 문단, `GenHFHadronMatcher` 요청이다.
