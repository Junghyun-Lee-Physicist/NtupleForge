#!/usr/bin/env python3
import ROOT

ROOT.gROOT.SetBatch(True)

mc_file  = "root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/A86FD660-3852-2049-94F6-71F92FE6BC99.root"
data_file = "root://xrootd-cms.infn.it///store/data/Run2017D/JetHT/NANOAOD/UL2017_MiniAODv2_NanoAODv9-v1/120000/F611A508-2426-4544-A824-98BA66C79966.root"
tree_name = "Events"

def get_branch_set(filename, treename="Events"):
    print(f"Opening: {filename}")
    f = ROOT.TFile.Open(filename)
    if not f or f.IsZombie():
        print(f"[ERROR] Cannot open file: {filename}")
        return set()

    tree = f.Get(treename)
    if not tree:
        print(f"[ERROR] Tree '{treename}' not found in {filename}")
        f.Close()
        return set()

    branches = set()
    blist = tree.GetListOfBranches()
    for i in range(blist.GetEntries()):
        br = blist.At(i)
        branches.add(br.GetName())

    f.Close()
    return branches

# --- 브랜치 집합 읽기 ---
branches_mc   = get_branch_set(mc_file, tree_name)
branches_data = get_branch_set(data_file, tree_name)

# --- 파일로 저장 ---
with open("branches_mc.txt", "w") as f:
    for b in sorted(branches_mc):
        f.write(b + "\n")

with open("branches_data.txt", "w") as f:
    for b in sorted(branches_data):
        f.write(b + "\n")

# --- 차이 계산 ---
only_in_mc   = sorted(branches_mc   - branches_data)
only_in_data = sorted(branches_data - branches_mc)
common       = sorted(branches_mc   & branches_data)

print("\n========== SUMMARY ==========")
print(f"MC   branches: {len(branches_mc)}")
print(f"DATA branches: {len(branches_data)}")
print(f"Common       : {len(common)}")
print(f"Only in MC   : {len(only_in_mc)}")
print(f"Only in DATA : {len(only_in_data)}")

print("\n--- Only in MC ---")
for b in only_in_mc:
    print(b)

print("\n--- Only in DATA ---")
for b in only_in_data:
    print(b)

# diff 결과도 파일로 저장
with open("branches_only_in_mc.txt", "w") as f:
    for b in only_in_mc:
        f.write(b + "\n")

with open("branches_only_in_data.txt", "w") as f:
    for b in only_in_data:
        f.write(b + "\n")
