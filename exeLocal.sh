#!/bin/bash

# 에러 발생 시 즉시 종료
set -euo pipefail

# 1. 출력 디렉토리 설정 (없으면 생성)
OUTDIR="output_test"
mkdir -p $OUTDIR

# 2. 입력 파일들 (여러 개를 공백으로 구분하여 나열)
INPUT_FILES="root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root \
root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/AC357503-8E32-0445-89E6-D3BD6BB1B5DC.root"

# 3. 실행
# 문법: python3 run_postproc.py [Output_Dir] [Input_Files...] [Options]
python3 scripts/run_postproc.py \
  $OUTDIR \
  $INPUT_FILES \
  --branch-selection configs/branch_selection.txt \
  --cut "nJet>4 && MET_pt>200" \
  --imports configs.modules_noop \
  --first-entry 0 --max-events 1000 \
  --postfix "_MySkim" 

# 4. (선택사항) 결과를 하나로 합치고 싶다면 hadd 사용
# echo "Merging files..."
# hadd -f skimmed_ttbarSemi_merged.root $OUTDIR/*_MySkim.root
