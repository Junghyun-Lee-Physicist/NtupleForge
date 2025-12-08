#!/bin/bash

# 에러 발생 시 즉시 종료 (Safety First)
set -euo pipefail

# 1. 출력 디렉토리 설정 (기존 것 삭제 후 재생성)
OUTDIR="output_local_test"
if [ -d "$OUTDIR" ]; then
    echo "Cleaning up previous output directory..."
    rm -rf $OUTDIR
fi
mkdir -p $OUTDIR

# 2. 입력 파일 설정 (XRootD 스트리밍)
# 줄바꿈(\)을 사용하여 가독성을 높였습니다.
INPUT_FILES="root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root \
root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/AC357503-8E32-0445-89E6-D3BD6BB1B5DC.root"

echo "======================================================"
echo "Starting Local Skim Test (No Modules)"
echo "Output Directory: $OUTDIR"
echo "======================================================"

# 3. Python 스크립트 실행
# 주의: 줄바꿈(\) 뒤에는 절대로 공백(스페이스)이 있으면 안 됩니다!
python3 scripts/run_postproc.py \
  $OUTDIR \
  $INPUT_FILES \
  --cut "nJet>4 && MET_pt>200" \
  --branch-selection branches/keep_and_drop.txt \
  --max-events 1000 \
  --postfix "_TestSkim" \
  --compression "LZ4:4"

# 위 python3 명령어는 여기서 끝납니다.

echo "======================================================"
echo "Job Finished. Checking output..."
ls -lh $OUTDIR

