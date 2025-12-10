#!/bin/bash

# 에러 발생 시 즉시 종료
set -euo pipefail

INPUT_FILES="root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root \
root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/AC357503-8E32-0445-89E6-D3BD6BB1B5DC.root"

echo "======================================================"
echo "Starting Local Skim Test"
echo "======================================================"

# 3. Python 실행
# --output-file: 결과물을 이 이름으로 병합(hadd)하여 저장합니다. (tree.root 아님)
# -I: modules.jetsMETcut:MODULES (jetsMETcut.py 안의 MODULES 리스트 사용)

python3 scripts/run_postproc.py \
  $INPUT_FILES \
  -b branches/branch_keep_and_drop.txt \
  -I modules.jetsMETcut:MODULES \
  -o testMergeROOT.root

echo "======================================================"
echo "Job Finished. Checking output..."
