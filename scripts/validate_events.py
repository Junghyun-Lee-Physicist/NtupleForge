#!/usr/bin/env python3
import uproot
import argparse
import glob
import os
import sys

def validate(file_pattern):
    """
    Reads Output ROOT files and checks 'Events' tree entries vs 'Runs' tree info.
    """
    # Expand wildcard pattern
    files = glob.glob(file_pattern)
    if not files:
        print(f"[Error] No files found matching pattern: {file_pattern}")
        return

    print(f"[Info] Found {len(files)} files. analyzing...")
    
    # Header
    print("="*100)
    print(f"{'File Name':<50} | {'Gen (Raw)':<12} | {'Skimmed':<10} | {'Eff (%)':<8}")
    print("-" * 100)

    total_gen = 0
    total_skim = 0
    valid_files = 0

    for fpath in sorted(files):
        fname = os.path.basename(fpath)
        try:
            with uproot.open(fpath) as f:
                # 1. Get Skimmed Count (Output Events)
                if "Events" in f:
                    skim_count = f["Events"].num_entries
                else:
                    skim_count = 0
                
                # 2. Get Generated Count (Original Events)
                # NanoAOD stores meta-info in 'Runs' tree
                gen_count = 0
                if "Runs" in f:
                    runs = f["Runs"]
                    # Usually 'genEventCount' exists for MC. 
                    # For Data, it might be missing or we assume raw input count.
                    keys = runs.keys()
                    if "genEventCount" in keys:
                        # genEventCount is stored per Run/Lumi, so we sum it up
                        gen_count = int(runs["genEventCount"].array().sum())
                    else:
                        # Fallback for Data or if branch missing
                        # If we can't find genCount, we can't calculate efficiency properly
                        # but we can show skim count.
                        gen_count = -1 
                
                # Output Row
                if gen_count > 0:
                    eff = (skim_count / gen_count) * 100
                    print(f"{fname:<50} | {gen_count:<12} | {skim_count:<10} | {eff:.2f}%")
                    total_gen += gen_count
                else:
                    print(f"{fname:<50} | {'Unknown':<12} | {skim_count:<10} | {'N/A':<8}")
                
                total_skim += skim_count
                valid_files += 1

        except Exception as e:
            print(f"{fname:<50} | {'ERROR':<12} | {str(e)}")

    print("=" * 100)
    
    # Final Summary
    print(f"Total Files Processed: {valid_files}")
    if total_gen > 0:
        total_eff = (total_skim / total_gen) * 100
        print(f"TOTAL GEN Events     : {total_gen}")
        print(f"TOTAL SKIM Events    : {total_skim}")
        print(f"Overall Efficiency   : {total_eff:.4f}%")
    else:
        print(f"TOTAL SKIM Events    : {total_skim}")
        print("Overall Efficiency   : N/A (Could not determine Gen count, maybe Data?)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Skim Efficiency")
    parser.add_argument("pattern", help="File pattern (e.g. 'output/*.root')")
    args = parser.parse_args()
    
    validate(args.pattern)
