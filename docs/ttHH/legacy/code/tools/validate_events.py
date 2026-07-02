#!/usr/bin/env python3
"""
Script: validate_events.py
Description:
    Validates skim efficiency by aggregating 'Events' vs 'Runs' tree information across multiple ROOT files.
    
    [Methodology]
    1. Output Events (Skimmed): Counted from 'Events' tree (num_entries).
    2. Input Events (Gen/Raw):  Aggregated from 'Runs' tree ('genEventCount' branch).
    
    Why aggregate?
    - CRAB jobs split processing across multiple files.
    - Each output file's 'Runs' tree contains the meta-info (gen weights, counts) ONLY for the lumi-blocks processed in that file.
    - Therefore, to get the correct total efficiency, we must SUM the gen counts from all files.

Usage:
    python3 validate_events.py "output_dir/*.root"
"""

import uproot
import argparse
import glob
import os
import sys
import numpy as np

def validate(file_pattern):
    # Expand wildcard pattern
    files = sorted(glob.glob(file_pattern))
    if not files:
        print(f"[ERROR] No files found matching pattern: {file_pattern}")
        return

    print("="*100)
    print(f" VALIDATION REPORT")
    print(f" Target Pattern: {file_pattern}")
    print(f" Found Files   : {len(files)}")
    print("="*100)
    print(f"{'File Name':<50} | {'Gen (Partial)':<15} | {'Skimmed':<10} | {'Step Eff':<8}")
    print("-" * 100)

    # Accumulators for Global Stats
    global_gen_sum = 0
    global_skim_sum = 0
    valid_files_count = 0
    is_data = False

    for fpath in files:
        fname = os.path.basename(fpath)
        try:
            with uproot.open(fpath) as f:
                # -------------------------------------------------------
                # 1. Get Skimmed Count (The Output)
                # -------------------------------------------------------
                if "Events" in f:
                    skim_count = f["Events"].num_entries
                else:
                    print(f"[WARNING] 'Events' tree missing in {fname}")
                    skim_count = 0
                
                # -------------------------------------------------------
                # 2. Get Generated/Processed Count (The Input)
                # -------------------------------------------------------
                # We iterate 'Runs' tree to sum up genEventCount.
                # In NanoAOD, 'Runs' tree stores sums per run/lumi block.
                local_gen_count = 0
                
                if "Runs" in f:
                    runs_tree = f["Runs"]
                    keys = runs_tree.keys()
                    
                    if "genEventCount" in keys:
                        # MC Case: Sum up gen events processed in this specific file/job
                        # .array() loads data, np.sum calculates the total
                        local_gen_count = int(np.sum(runs_tree["genEventCount"].array()))
                    else:
                        # Data Case: 'genEventCount' usually doesn't exist.
                        # For Data, efficiency is usually 100% relative to input trigger path, 
                        # but strictly speaking, we compare skim vs input.
                        # Here we assume it's data and might treat Gen as 'Unknown' or 0
                        is_data = True
                        local_gen_count = 0 
                else:
                    print(f"[WARNING] 'Runs' tree missing in {fname}")

                # -------------------------------------------------------
                # 3. Print Per-File Statistics
                # -------------------------------------------------------
                if local_gen_count > 0:
                    step_eff = (skim_count / local_gen_count) * 100
                    print(f"{fname:<50} | {local_gen_count:<15} | {skim_count:<10} | {step_eff:.2f}%")
                    global_gen_sum += local_gen_count
                else:
                    # If Data or missing info
                    print(f"{fname:<50} | {'N/A (Data?)':<15} | {skim_count:<10} | {'-'}")

                global_skim_sum += skim_count
                valid_files_count += 1

        except Exception as e:
            print(f"{fname:<50} | {'[READ ERROR]':<15} | {str(e)}")

    # -------------------------------------------------------
    # 4. Final Aggregated Summary
    # -------------------------------------------------------
    print("=" * 100)
    print("                      AGGREGATED SUMMARY                      ")
    print("=" * 100)
    print(f" Total Files Successfully Read : {valid_files_count}")
    print(f" Total SKIMMED Events (Output) : {global_skim_sum:,}")
    
    if not is_data and global_gen_sum > 0:
        total_eff = (global_skim_sum / global_gen_sum) * 100
        print(f" Total GEN Events     (Input)  : {global_gen_sum:,}")
        print("-" * 60)
        print(f" >> GLOBAL EFFICIENCY          : {total_eff:.6f} %")
    elif is_data:
        print(f" Total GEN Events     (Input)  : N/A (Appears to be DATA)")
        print("-" * 60)
        print(f" >> GLOBAL EFFICIENCY          : N/A")
    else:
        print(f" [WARNING] Could not determine Input Event counts. Check 'Runs' tree.")

    print("=" * 100)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Skim Efficiency by chaining Runs and Events info.")
    parser.add_argument("pattern", help="File pattern to match (e.g. 'output_dir/*.root')")
    args = parser.parse_args()
    
    validate(args.pattern)
