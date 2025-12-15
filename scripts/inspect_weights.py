#!/usr/bin/env python3
"""
Script: inspect_weights.py
Description:
    Inspects the 'Generator_weight' branch in the 'Events' tree and compares it
    with 'genEventSumw' in the 'Runs' tree to verify MC weight behavior.
"""

import uproot
import argparse
import sys
import numpy as np

def inspect_weights(filename):
    print("="*80)
    print(f" ⚖️  WEIGHT INSPECTION REPORT")
    print(f" Target: {filename}")
    print("="*80)

    try:
        with uproot.open(filename) as f:
            # -----------------------------------------------------------
            # 1. Runs Tree Inspection (Global Meta Info)
            # -----------------------------------------------------------
            if "Runs" not in f:
                print("[ERROR] 'Runs' tree not found.")
                return

            runs = f["Runs"]
            if "genEventCount" not in runs or "genEventSumw" not in runs:
                print("[WARNING] 'genEventCount' or 'genEventSumw' missing in Runs tree.")
                print("          -> Likely Real Data.")
                return

            # Load values (sum over all run blocks in file)
            n_gen = np.sum(runs["genEventCount"].array())
            sum_w = np.sum(runs["genEventSumw"].array())

            print(f" [1] Runs Tree Info (Aggregated)")
            print(f"     - genEventCount (N)    : {n_gen:,.0f}")
            print(f"     - genEventSumw  (SumW) : {sum_w:,.2f}")
            
            if n_gen == sum_w:
                print("     -> [NOTE] SumW == N. Events appear to be UNWEIGHTED (Weight = 1.0).")
            else:
                print(f"     -> [NOTE] SumW != N. Average Weight = {sum_w/n_gen:.4f}")

            print("-" * 80)

            # -----------------------------------------------------------
            # 2. Events Tree Inspection (Per-Event Weights)
            # -----------------------------------------------------------
            if "Events" not in f:
                print("[ERROR] 'Events' tree not found.")
                return
            
            events = f["Events"]
            if "Generator_weight" not in events:
                print("[WARNING] 'Generator_weight' branch not found in Events tree.")
                return

            # Read Weights (Partial read if file is huge)
            weights = events["Generator_weight"].array(entry_stop=100000)
            
            w_min = np.min(weights)
            w_max = np.max(weights)
            w_mean = np.mean(weights)
            w_std = np.std(weights)
            unique_weights = np.unique(weights)

            print(f" [2] Events Tree: 'Generator_weight' Statistics (Sample of first 100k)")
            print(f"     - Mean : {w_mean:.6f}")
            print(f"     - Std  : {w_std:.6f}")
            print(f"     - Min  : {w_min:.6f}")
            print(f"     - Max  : {w_max:.6f}")
            print(f"     - Unique Values Found: {len(unique_weights)}")

            print("-" * 80)
            print(" [3] First 10 Weights Preview:")
            print(f"     {weights[:10]}")
            
            print("-" * 80)
            print(" [4] Conclusion")
            if len(unique_weights) == 1 and unique_weights[0] == 1.0:
                 print("     ✅ CONFIRMED: All weights are exactly 1.0.")
                 print("        This is a standard 'Unweighted' MC sample.")
                 print("        To get physical yield, multiply by (CrossSection * Lumi / genEventSumw).")
            elif w_std < 1e-6:
                 print(f"     ⚠️  CONSTANT WEIGHT: All weights are approx {w_mean:.4f}.")
            else:
                 print("     ℹ️  WEIGHTED EVENTS: Weights vary (likely NLO +1/-1 or weighted generation).")
                 print("        Use 'genEventSumw' for normalization, NOT 'genEventCount'.")

    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to ROOT file")
    args = parser.parse_args()
    inspect_weights(args.file)
