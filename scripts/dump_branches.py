#!/usr/bin/env python3
import uproot
import argparse
import sys

def dump_branches(input_file, output_txt, sort=True):
    print(f"[INFO] Opening file: {input_file}")
    try:
        f = uproot.open(input_file)
        tree = f["Events"]
        branches = tree.keys()
        if sort: branches = sorted(branches)
        
        with open(output_txt, 'w') as out:
            for b in branches:
                out.write(b + '\n')
        print(f"[INFO] Saved {len(branches)} branches to: {output_txt}")

    except Exception as e:
        print(f"[ERROR] Failed to read file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", default="branches.txt")
    args = parser.parse_args()
    dump_branches(args.input_file, args.output)
