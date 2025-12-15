#!/usr/bin/env python3
"""
Script: compare_branches.py
Description:
    Compares the list of branches between two ROOT files (typically MC vs Data).
    It identifies common branches, branches unique to MC, and branches unique to Data.
    Results are printed to stdout and saved to text files.

Usage:
    python3 compare_branches.py
    python3 compare_branches.py --mc <mc_file_path> --data <data_file_path>
"""

import ROOT
import sys
import argparse
import os

# ROOT Batch Mode (No GUI)
ROOT.gROOT.SetBatch(True)

# Default File Paths (Used if no arguments provided)
DEFAULT_MC_FILE = "root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/A86FD660-3852-2049-94F6-71F92FE6BC99.root"
DEFAULT_DATA_FILE = "root://xrootd-cms.infn.it///store/data/Run2017D/JetHT/NANOAOD/UL2017_MiniAODv2_NanoAODv9-v1/120000/F611A508-2426-4544-A824-98BA66C79966.root"

def get_branch_set(filename, treename="Events"):
    """Opens a ROOT file and returns a set of branch names."""
    print(f"[INFO] Opening file: {filename}")
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
    total_branches = blist.GetEntries()
    
    print(f"[INFO] Found {total_branches} branches in '{treename}'")
    
    for i in range(total_branches):
        br = blist.At(i)
        branches.add(br.GetName())

    f.Close()
    return branches

def save_to_file(filename, data_set):
    """Helper to save a set of strings to a file."""
    with open(filename, "w") as f:
        for item in sorted(data_set):
            f.write(item + "\n")
    print(f"[INFO] Saved list to: {filename}")

def main():
    parser = argparse.ArgumentParser(description="Compare branches between two ROOT files.")
    parser.add_argument("--mc", default=DEFAULT_MC_FILE, help="Path to MC ROOT file")
    parser.add_argument("--data", default=DEFAULT_DATA_FILE, help="Path to Data ROOT file")
    parser.add_argument("--tree", default="Events", help="Tree name to inspect")
    args = parser.parse_args()

    print("="*60)
    print("      BRANCH COMPARISON TOOL      ")
    print("="*60)

    # 1. Read Branches
    branches_mc = get_branch_set(args.mc, args.tree)
    branches_data = get_branch_set(args.data, args.tree)

    if not branches_mc or not branches_data:
        print("[ERROR] Failed to read branches from one or both files. Exiting.")
        sys.exit(1)

    # 2. Save Full Lists
    save_to_file("branches_mc.txt", branches_mc)
    save_to_file("branches_data.txt", branches_data)

    # 3. Calculate Differences
    only_in_mc = sorted(branches_mc - branches_data)
    only_in_data = sorted(branches_data - branches_mc)
    common = sorted(branches_mc & branches_data)

    # 4. Save Differences
    save_to_file("branches_only_in_mc.txt", set(only_in_mc))
    save_to_file("branches_only_in_data.txt", set(only_in_data))

    # 5. Print Summary
    print("\n" + "="*60)
    print("          COMPARISON SUMMARY          ")
    print("="*60)
    print(f"Total MC Branches   : {len(branches_mc)}")
    print(f"Total DATA Branches : {len(branches_data)}")
    print(f"Common Branches     : {len(common)}")
    print("-"*60)
    print(f"Unique to MC        : {len(only_in_mc)}")
    print(f"Unique to DATA      : {len(only_in_data)}")
    print("="*60)

    if only_in_mc:
        print(f"\n[Preview] Top 5 branches Only in MC:")
        for b in only_in_mc[:5]: print(f" - {b}")
        if len(only_in_mc) > 5: print(" ... (check branches_only_in_mc.txt for full list)")

    if only_in_data:
        print(f"\n[Preview] Top 5 branches Only in DATA:")
        for b in only_in_data[:5]: print(f" - {b}")
        if len(only_in_data) > 5: print(" ... (check branches_only_in_data.txt for full list)")

if __name__ == "__main__":
    main()
