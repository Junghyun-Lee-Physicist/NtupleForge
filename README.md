# NtupleForge ⚒️

CMS **NanoAOD post-processing** 유틸리티 모음입니다. upstream
`PhysicsTools/NanoAODTools` 패키지를 수정하지 않고 skim / slim / 파생 branch
생성을 수행하며, **CRAB3** 제출 glue를 포함합니다. 현재 두 개의 분석
workstream이 이 파이프라인을 공유합니다:

- **TopCPV** (top CP-violation): MC 샘플에 gen-level top-decay categorization
  branch(`TopCPVCat_*`)를 추가하는 `modules/topCPVCategorizer.py` 모듈.
  문서: [`docs/TopCPV/`](docs/TopCPV/README.md)
- **ttHH → 4b**: full-NanoAOD passthrough 기반 ntuple 생산 (categorization은
  main analyzer로 이관됨). 문서: [`docs/ttHH/`](docs/ttHH/README.md)

📖 **심화 문서는 [`docs/`](docs/README.md)에 있습니다** — framework 내부 구조,
PyROOT branch-access 규칙, 변경/결정/트러블슈팅 로그. 이 README는 코드를
*실행*하는 데 필요한 내용만 담습니다.

- Upstream framework: <https://github.com/cms-sw/cmssw/tree/CMSSW_14_2_X/PhysicsTools/NanoAODTools>

---

## 🛠️ 환경 설정 (Setup)

> **환경:** **lxplus8** (`ssh <user>@lxplus8.cern.ch`) 또는 Singularity
> container(`cmssw-el8`)를 사용하십시오. `CMSSW_14_2_1`은
> **el8_amd64_gcc12**를 요구합니다.

```bash
cmsrel CMSSW_14_2_1
cd CMSSW_14_2_1/src
cmsenv

git cms-init
git cms-addpkg PhysicsTools/NanoAODTools          # 표준 NanoAODTools
git clone https://github.com/Junghyun-Lee-Physicist/NtupleForge.git

scram b -j 8                                       # 컴파일 + python path 설정
cd NtupleForge
```

## ⚠️ 실행 전 준비 (Prerequisites)

```bash
cmsenv                                             # CMSSW 환경
voms-proxy-init --voms cms --valid 168:00          # 원격(XRootD) 파일 접근
source /cvmfs/cms.cern.ch/crab3/crab.sh            # CRAB 제출용
```

---

## 🚀 로컬 실행 (Run locally)

Full NanoAOD passthrough (입력을 그대로 복사, 모든 branch 유지):

```bash
python3 script/run_postproc.py <input.root> \
  -I modules.noop \
  -b branches/branch_keep_all.txt \
  -N 1000
```

TopCPV gen categorizer 로컬 검증 (MC 파일에서 `-N` 소량 실행 권장):

```bash
python3 script/run_postproc.py <MC_nanoaod.root> \
  -I modules.topCPVCategorizer:MODULES \
  -b branches/branch_CPV_Run2_MC.txt \
  -N 10
```

`<input.root>`는 로컬 경로 또는 XRootD URL
(`root://cms-xrd-global.cern.ch//store/...`) 모두 가능합니다. 여러 파일을
나열하면 순차 처리되고, `-o merged.root`를 주면 출력들을 `hadd`로 병합합니다.

### Driver 인자 (arguments)

| Flag | 필수 | 설명 |
|---|---|---|
| `input_files` (positional) | ✓ | 하나 이상의 ROOT 파일 (XRootD 또는 로컬). |
| `-I`, `--imports` | ✓ | 모듈 지정, 예: `modules.noop` 또는 `modules.topCPVCategorizer:MODULES`. |
| `-b`, `--branch-selection` | ✓ | **출력** keep/drop 파일 (입력은 항상 전체 read — `docs/04_architecture.md` §7). Passthrough는 `branches/branch_keep_all.txt`. |
| `-o`, `--output-file` | | 지정 시 모든 출력을 이 파일 하나로 `hadd`. |
| `-N`, `--max-events` | | 처리 이벤트 수 제한 (기본: 전체). |
| `--first-entry` | | 앞쪽 N개 entry 건너뛰기 (기본: 0). |

skim을 적용하려면 cut 모듈을 끼우십시오 — 예제:
[`modules/jetsMETcut.py`](modules/jetsMETcut.py). 커스텀 branch 작성 방법은
[`docs/04_architecture.md`](docs/04_architecture.md) §4를 보십시오.

---

## 🦀 CRAB 실행 (Run on CRAB)

작업은 [`crabConfig/`](crabConfig/)의 YAML 파일로 정의합니다.
`analysis_module`과 `branch_file` 필드가 worker의 `run_postproc.py`
(`-I` / `-b`)로 전달됩니다.

```bash
# 제출. 이미 존재하는 task는 실패 job을 AUTO-RESUBMIT합니다
# (task별 CRAB project dir 존재 여부로 submit/resubmit이 결정됨).
python3 crab/submit_crab.py --config crabConfig/config_CPV2017UL_MC.yaml

# 실패 job만 명시적으로 재제출
python3 crab/submit_crab.py --config crabConfig/config_CPV2017UL_MC.yaml --resubmit

# task별 full 'crab status'
python3 crab/submit_crab.py --config crabConfig/config_CPV2017UL_MC.yaml --status

# sample별 압축 요약 리포트 (--status보다 읽기 쉬움)
python3 crab/submit_crab.py --config crabConfig/config_CPV2017UL_MC.yaml --report

# config에 정의된 모든 job kill
python3 crab/submit_crab.py --config crabConfig/config_CPV2017UL_MC.yaml --kill
```

ttHH passthrough 캠페인은 `--config crabConfig/config_ttHH2017UL.yaml`로 동일하게
관리합니다.

> **⚠️ Data / MC 분리 (TopCPV):** config가 **tier별로 분리**되어 있습니다
> (2026-07-02): data는 `config_CPV<era>_Data.yaml`(noop +
> `branch_CPV_Run2_Data.txt`), MC는 `config_CPV<era>_MC.yaml`(gen 모듈 +
> `branch_CPV_Run2_MC.txt`)로 제출하십시오. `topCPVCategorizer`는 **MC
> 전용**이며, data가 들어와도 crash 대신 no-op이지만(2026-07-01 수정,
> `docs/05_troubleshooting.md` A11) 그것은 안전망이지 정상 경로가 아닙니다.

`--report`는 CRAB에 질의해 sample당 한 줄로 `done`(finished) / `run` / `idle` /
`transf`(transferring) / `fail` / `other` 개수와 총계를 출력합니다. 인식하지
못한 CRAB state는 `other`로 집계하고 경고로 이름을 알려줍니다
(`crab/submit_crab.py`의 `REPORT_COLUMNS` / `KNOWN_OTHER_STATES`에 추가).

> **⚠️ Memory / walltime 실패:** 일반 (re)submit은 **기본** 리소스를 쓰므로
> memory/walltime으로 실패한 job은 다시 실패합니다. project dir에서 한도를
> 올려 수동 재제출하십시오. 예:
> `crab resubmit -d <workArea>/crab_<reqName> --maxmemory=4000 --maxjobruntime=2700`.
> submit/resubmit 실행 끝에 이 리마인더가 출력됩니다.
> [`docs/05_troubleshooting.md`](docs/05_troubleshooting.md) A10 참조.

`script/parse_crab_status.py`는 오프라인 카운터파트입니다: 저장해 둔
`crab status` 로그를 요약하며(라이브 질의 없음), `--show-lines`로 raw status
라인을 함께 출력합니다:

```bash
python3 script/parse_crab_status.py crab_status.log
python3 script/parse_crab_status.py crab_status.log --show-lines
```

> **⚠️ 출력 파일명:** **두 곳**에 하드코딩되어 있고 반드시 일치해야 합니다 —
> `crab/PSet.py`(`PoolOutputModule` fileName)와 `crab/submit_crab.py`
> (`out_name`), 둘 다 `forgedNtuple.root`. 한쪽만 바꾸면 CRAB stageout이
> 깨집니다 (exit 60302). [`docs/07_DeveloperGuideline.md`](docs/07_DeveloperGuideline.md)
> Rule 6 참조.

---

## 🧑‍💻 개발 (Developing)

코드를 수정하려면 **[`docs/00_PROMPT.md`](docs/00_PROMPT.md)** (작업 계약)와
**[`docs/07_DeveloperGuideline.md`](docs/07_DeveloperGuideline.md)** 를 먼저
읽으십시오. 요약: 변경 전에 [`docs/`](docs/README.md)를 읽기 순서대로 전부 읽고,
모든 변경(CHANGELOG)과 모든 문제+해결(troubleshooting)을 그때그때 기록합니다.

## 📂 구조 (Layout)

```
NtupleForge/
├── script/
│   ├── run_postproc.py          # driver (CRAB에 배송되는 유일한 script)
│   ├── validate_topcpvcat.py    # TopCPV 동등성 검증기 (lxplus에서 실행)
│   └── parse_crab_status.py     # CRAB status-log 요약기 (--show-lines)
├── modules/
│   ├── noop.py                  # 빈 모듈 — passthrough / slim 전용
│   ├── jetsMETcut.py            # skim-cut (gatekeeper) 예제 모듈
│   ├── topCPVCategorizer.py     # TopCPV gen categorizer (MC 전용)
│   └── nanoaod_branch_access.py # 필수 PyROOT read 헬퍼 (to_int / count)
├── branches/
│   ├── branch_keep_all.txt      # keep * — full passthrough (기본)
│   ├── branch_keep_and_drop.txt # 최소 slimming 예제
│   └── branch_CPV_Run2_{Data,MC}.txt  # TopCPV 출력 branch 목록
├── crab/                        # CRAB3 제출 glue (submit/worker/PSet)
├── crabConfig/*.yaml            # CRAB 캠페인 config (dataset 목록)
└── docs/                        # ← 모든 기술 문서 + legacy 아카이브
    ├── TopCPV/                  #    TopCPV categorizer 문서
    └── ttHH/                    #    ttHH 물리 + legacy 파이프라인 문서
```

그 외 모든 것은 [`docs/`](docs/README.md)를 보십시오.
