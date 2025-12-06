#!/bin/bash

set -euo pipefail

python3 scripts/run_postproc.py \
  --input "root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root" \
  --input "root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/AC357503-8E32-0445-89E6-D3BD6BB1B5DC.root" \
  --input "root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/A86FD660-3852-2049-94F6-71F92FE6BC99.root" \
  --branchsel "$(readlink -f configs/branch_selection.txt)" \
  --cut "nJet>4 && MET_pt>200" \
  --modules "$(readlink -f configs/modules_noop.py)" \
  --firstEntry 0 --maxEntries 50000 \
  --output skimmed_ttbarSemi_3files.root
