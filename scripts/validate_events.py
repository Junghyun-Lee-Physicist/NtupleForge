#!/usr/bin/env python3
import uproot
import argparse
import glob
import os

def validate(file_pattern):
    """
    Reads Output ROOT files and checks 'Events' tree entries vs 'Runs' tree info.
    """
    files = glob.glob(file_pattern)
    if not files:
        print(f"No files found matching: {file_pattern}")
        return

    total_gen_events = 0
    total_skim_events = 0
    
    print(f"{'File':<60} | {'Gen (Raw)':<12} | {'Skimmed':<10} | {'Eff (%)':<8}")
    print("-" * 100)

    for fpath in files:
        try:
            with uproot.open(fpath) as f:
                # 1. Count Skimmed Events
                if "Events" in f:
                    skim_count = f["Events"].num_entries
                else:
                    skim_count = 0
                
                # 2. Count Gen Events (from Runs tree genEventCount or similar)
                # NanoAOD usually stores 'genEventCount' in 'Runs' tree.
                gen_count = 0
                if "Runs" in f:
                    runs = f["Runs"]
                    if "genEventCount" in runs.keys():
                        # genEventCount is stored per run, need to sum
                        gen_count = int(runs["genEventCount"].array().sum())
                    else:
                        # Fallback if genEventCount is missing (e.g. Data)
                        gen_count = skim_count # Assume 100% if unknown, or handle differently
                
                # Print Row
                eff = (skim_count / gen_count * 100) if gen_count > 0 else 0.0
                print(f"{os.path.basename(fpath):<60} | {gen_count:<12} | {skim_count:<10} | {eff:.2f}%")
                
                total_gen_events += gen_count
                total_skim_events += skim_count

        except Exception as e:
            print(f"{os.path.basename(fpath):<60} | {'ERROR':<12} | {str(e)}")

    print("-" * 100)
    total_eff = (total_skim_events / total_gen_events * 100) if total_gen_events > 0 else 0.0
    print(f"{'TOTAL':<60} | {total_gen_events:<12} | {total_skim_events:<10} | {total_eff:.2f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Skim Output")
    parser.add_argument("pattern", help="File pattern (e.g. 'output/*.root')")
    args = parser.parse_args()
    
    validate(args.pattern)
