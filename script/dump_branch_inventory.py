#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dump_branch_inventory.py -- dump the branch schema of one real NanoAOD file.

WHY THIS EXISTS
---------------
Every branch-name decision in this project is currently made from memory or
from a 2026-era inventory of NanoAODv9 (docs/ttHH/legacy/code/branches/
branch_2017UL/branches_mc.txt, 1666 lines). For the v9 -> v15 migration that is
not good enough: v15 renames branches the analyzer depends on
(MET_pt -> PFMET_pt, fixedGridRhoFastjetAll -> Rho_fixedGridRhoFastjetAll,
Electron_mvaFall17V2Iso_* -> Electron_mvaIso_*) and changes types
(nJet UInt_t -> Int_t, Jet_genJetIdx Int_t -> Short_t,
Jet_hadronFlavour Int_t -> UChar_t).

And the failure mode is silent in BOTH directions:
  * a `keep` pattern that matches nothing makes ROOT print a SetBranchStatus
    error ONCE PER JOB (it is not silently ignored -- see docs/02_CHANGELOG.md
    2026-07-27, which is why the prescan branch lists are split per year);
  * a branch the analyzer reads but the file does not have is defaulted to 0 by
    eventBuffer with only a summary line, so e.g. a missing `Jet_puId` cuts
    every jet below 50 GeV and a missing `genTtbarId` bins all ttbar MC as
    tt+LF, with no crash.

So: dump the real schema, then check the keep-list against it
(script/check_branchlist.py). Never hand-write a v15 branch list.

USAGE (lxplus or Tier-3, anywhere PyROOT exists)
------------------------------------------------
    # local file
    python3 script/dump_branch_inventory.py forgedNtuple.root -o inv_v9.tsv

    # straight off DAS -- get the LFN from `das_scan.sh --sample-file`
    python3 script/dump_branch_inventory.py \
        root://cms-xrd-global.cern.ch//store/mc/.../file.root \
        --label 2018UL_v9_MC -o script/inventory/inv_2018UL_v9_MC.tsv

    # diff two inventories (v9 vs v15) -- no ROOT needed for this mode
    python3 script/dump_branch_inventory.py --diff inv_2018UL_v9_MC.tsv inv_2018UL_v15_MC.tsv

OUTPUT (TSV, one row per branch)
    tree <TAB> branch <TAB> type <TAB> lenVar
  where lenVar is the counter branch for array branches ('' for scalars).
  The header line starts with '#' and carries the label + source file.

EXIT CODES
    0 ok   2 bad args   3 file/tree unreadable   4 diff found differences
"""

from __future__ import annotations

import argparse
import os
import sys

TREES_DEFAULT = ("Events", "Runs", "LuminosityBlocks")


def dump(path, trees, label, out):
    try:
        import ROOT  # noqa: F401  (import here so --diff works without PyROOT)
    except ImportError:
        sys.exit("FATAL: PyROOT not available. Run on lxplus/Tier-3 inside a CMSSW\n"
                 "       environment (cmsenv), or use --diff which needs no ROOT.")
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kWarning

    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        sys.exit("FATAL: could not open '%s'" % path)

    rows = []
    for tname in trees:
        t = f.Get(tname)
        if not t:
            print("[dump] NOTE: tree '%s' not present -- skipped" % tname)
            continue
        for br in t.GetListOfBranches():
            bname = br.GetName()
            leaves = br.GetListOfLeaves()
            if not leaves or leaves.GetEntries() == 0:
                rows.append((tname, bname, "?", ""))
                continue
            lf = leaves.At(0)
            typ = lf.GetTypeName()
            counter = lf.GetLeafCount()
            lenvar = counter.GetName() if counter else ""
            rows.append((tname, bname, typ, lenvar))
        print("[dump] %-18s %5d branches" % (tname, sum(1 for r in rows if r[0] == tname)))
    f.Close()

    if not rows:
        sys.exit("FATAL: no branches found in %s (trees tried: %s)" % (path, ",".join(trees)))

    lines = ["# label=%s" % (label or "(none)"),
             "# source=%s" % path,
             "# columns: tree\tbranch\ttype\tlenVar"]
    lines += ["\t".join(r) for r in sorted(rows)]
    text = "\n".join(lines) + "\n"
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("[dump] wrote %s (%d rows)" % (out, len(rows)))
    else:
        sys.stdout.write(text)
    return 0


def read_inventory(path):
    """-> (label, {(tree,branch): (type,lenVar)})"""
    label, d = os.path.basename(path), {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("# label="):
                label = line.split("=", 1)[1] or label
                continue
            if line.startswith("#") or not line.strip():
                continue
            f = line.split("\t")
            if len(f) < 3:
                continue
            d[(f[0], f[1])] = (f[2], f[3] if len(f) > 3 else "")
    return label, d


def diff(a_path, b_path):
    la, a = read_inventory(a_path)
    lb, b = read_inventory(b_path)
    only_a = sorted(k for k in a if k not in b)
    only_b = sorted(k for k in b if k not in a)
    retyped = sorted(k for k in a if k in b and a[k][0] != b[k][0])

    print("# Branch inventory diff")
    print("#   A = %s   (%d branches)" % (la, len(a)))
    print("#   B = %s   (%d branches)" % (lb, len(b)))
    print()
    print("## Removed in B (%d)" % len(only_a))
    for t, n in only_a:
        print("  -  %s/%s\t%s" % (t, n, a[(t, n)][0]))
    print()
    print("## Added in B (%d)" % len(only_b))
    for t, n in only_b:
        print("  +  %s/%s\t%s" % (t, n, b[(t, n)][0]))
    print()
    print("## Type changed (%d)" % len(retyped))
    for t, n in retyped:
        print("  ~  %s/%s\t%s -> %s" % (t, n, a[(t, n)][0], b[(t, n)][0]))
    print()
    print("## Rename candidates (a removed branch whose name is a suffix/substring")
    print("## of an added one, or vice versa). HEURISTIC -- confirm each by hand.")
    hits = 0
    for t, n in only_a:
        for t2, n2 in only_b:
            if t != t2:
                continue
            if n in n2 or n2 in n or n.split("_")[-1] == n2.split("_")[-1]:
                print("  ?  %s  ->  %s" % (n, n2))
                hits += 1
                break
    if not hits:
        print("  (none found)")
    print()
    n = len(only_a) + len(only_b) + len(retyped)
    print("## Summary: %d removed, %d added, %d retyped" % (len(only_a), len(only_b), len(retyped)))
    return 4 if n else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="ROOT file (local path or xrootd URL)")
    ap.add_argument("-o", "--out", help="write TSV here (default: stdout)")
    ap.add_argument("--label", help="label written into the TSV header, e.g. 2018UL_v15_MC")
    ap.add_argument("--trees", default=",".join(TREES_DEFAULT),
                    help="comma-separated tree names (default: %(default)s)")
    ap.add_argument("--diff", nargs=2, metavar=("INV_A", "INV_B"),
                    help="diff two inventory TSVs (no ROOT needed) and exit")
    args = ap.parse_args()

    if args.diff:
        for p in args.diff:
            if not os.path.isfile(p):
                sys.exit("FATAL: cannot read '%s'" % p)
        return diff(*args.diff)

    if not args.path:
        ap.error("give a ROOT file, or use --diff INV_A INV_B")
    return dump(args.path, [t for t in args.trees.split(",") if t], args.label, args.out)


if __name__ == "__main__":
    sys.exit(main())
