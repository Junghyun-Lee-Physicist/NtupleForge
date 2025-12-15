#!/usr/bin/env python3
"""
Script: dump_branches.py
Description:
    Reads a ROOT file using uproot and dumps all branch names from the 'Events' tree
    into a text file. Useful for quickly inspecting file content.

Usage:
    python3 dump_branches.py <input_file.root> [-o output.txt]
"""

import uproot
import argparse
import sys
import os

def dump_branches(input_file, output_txt, sort=True):
    print("="*60)
    print(f"[INFO] Target File : {input_file}")
    print(f"[INFO] Output File : {output_txt}")
    print("="*60)

    try:
        # Check if file exists
        if not os.path.exists(input_file) and not input_file.startswith("root://"):
            raise FileNotFoundError(f"File not found: {input_file}")

        # Open file
        with uproot.open(input_file) as f:
            if "Events" not in f:
                print(f"[ERROR] 'Events' tree not found in {input_file}")
                return

            tree = f["Events"]
            branches = tree.keys()
            
            # Additional Info
            num_entries = tree.num_entries
            print(f"[INFO] 'Events' Tree Entries: {num_entries}")
            
            if sort: 
                branches = sorted(branches)
            
            # Write to file
            with open(output_txt, 'w') as out:
                for b in branches:
                    out.write(b + '\n')
            
            print(f"[INFO] Successfully wrote {len(branches)} branch names to {output_txt}")
            print("="*60)

    except Exception as e:
        print(f"[ERROR] Failed to process file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dump branch names from a ROOT file.")
    parser.add_argument("input_file", help="Path to input ROOT file")
    parser.add_argument("-o", "--output", default="branches.txt", help="Output text file path (default: branches.txt)")
    args = parser.parse_args()
    
    dump_branches(args.input_file, args.output)
