python3 crab/submit_crab.py \
  --name "Campagin_v1" \
  --sample-list samples.txt \
  --site T3_KR_KNU \
  --cut "nJet > 3 && Jet_pt > 200" \
  --branch-sel branches/keep_and_drop.txt \
  --imports modules.jets_met:MODULES
