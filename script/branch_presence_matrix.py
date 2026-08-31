#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
branch_presence_matrix.py -- cross-tabulate branch presence across MANY inventories.

WHY THIS EXISTS
---------------
On 2026-08-30 three 2017 hadronic trigger paths were declared "missing in v15"
on the evidence of ONE MC inventory, and the conclusion drawn was that the
trigger efficiency and scale factor would have to be re-derived. Every part of
that was wrong: they are 2017 **Run B** paths, they are present in
/JetHT/Run2017B-UL2017_MiniAODv2_NanoAODv9/NANOAOD, and v9 and v15 MC have
byte-identical HLT sets. (docs/05_troubleshooting.md A19.)

The measured spread that made the single-file judgement worthless:

    Run2017B  1208 Events / 269 HLT     <- calo b-tag paths, 'TripeCSV' typo
    Run2017C  1523 / 479                <- PF CSV only
    Run2017D  1570 / 526                <- PF CSV + PF DeepCSV
    Run2017E  1612 / 526
    Run2017F  1666 / 580
    UL17 MC   1666 / 569

A branch family whose presence is decided by the HLT menu of the run range
cannot be judged from one file. Neither can anything else that varies by
primary dataset, tier or era. So: dump many inventories
(script/sweep_inventories.sh) and cross-tabulate them here.

The output column that matters is **PARTIAL** -- branches present in some
inventories and absent in others. Those are the ones that produce silent
failures, because a keep-list or an analyzer requirement derived from one file
will be wrong for the others.

USAGE
-----
    # everything in script/inventory/ against an explicit branch list
    python3 script/branch_presence_matrix.py \\
        --inventory-dir script/inventory \\
        --branches HLT_PFHT1050 HLT_PFHT430_SixJet40_BTagCSV_p080 Jet_puId

    # against a check_branchlist.py profile (reuses its REQUIRED tables)
    python3 script/branch_presence_matrix.py \\
        --inventory-dir script/inventory --profile main --mc --era 2017

    # only the HLT family, all inventories
    python3 script/branch_presence_matrix.py \\
        --inventory-dir script/inventory --pattern '^HLT_' --partial-only

EXIT CODES
----------
    0  every requested branch is present in every inventory
    2  at least one branch is PARTIAL (present here, absent there)
    3  at least one branch is absent EVERYWHERE
    4  no inventories or no branches to compare
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys


def read_inventory(path, tree="Events"):
    """TSV from dump_branch_inventory.py -> (label, set(branch names))."""
    names, label = set(), None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("#"):
                m = re.search(r"label[:=]\s*(\S+)", line)
                if m and not label:
                    label = m.group(1)
                continue
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] == tree:
                names.add(parts[1])
    if not label:
        label = os.path.basename(path)
        label = re.sub(r"^inv_", "", label)
        label = re.sub(r"\.tsv$", "", label)
    return label, names


def load_profile(repo_root, profile, mc, era):
    """Reuse check_branchlist.py's tables so the two tools cannot drift apart."""
    sys.path.insert(0, os.path.join(repo_root, "script"))
    try:
        import check_branchlist as cb
    except ImportError as exc:
        sys.exit("ERROR: cannot import check_branchlist.py (%s)" % exc)
    table = {"prescan": getattr(cb, "PRESCAN_REQUIRED", []),
             "cpv": getattr(cb, "CPV_REQUIRED", [])}.get(profile, cb.REQUIRED)
    out = []
    for names, flags in table:
        if "mc" in flags and not mc:
            continue
        if "produced" in flags:      # created by a module; never in an input file
            continue
        out.append(names[0])
    if era:
        out += list(getattr(cb, "HLT_REQUIRED", {}).get(era, []))
        out += list(getattr(cb, "HLT_ERA_CONDITIONAL", {}).get(era, []))
    seen, uniq = set(), []
    for b in out:
        if b not in seen:
            seen.add(b); uniq.append(b)
    return uniq


def classify(present, mc_set, data_set):
    """A branch present in exactly the MC inventories (or exactly the Data ones)
    is not a finding -- Data carries no gen information and MC carries no
    data-only branches. Calling those PARTIAL buries the real signal: on
    2026-08-30 the first run of this tool reported 31 PARTIAL branches of which
    19 were simply MC-only. Only the leftovers deserve attention."""
    if mc_set and present == mc_set:
        return "MC-ONLY"
    if data_set and present == data_set:
        return "DATA-ONLY"
    return "PARTIAL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory-dir", default="script/inventory",
                    help="directory of *.tsv from dump_branch_inventory.py")
    ap.add_argument("--inventories", nargs="*",
                    help="explicit TSV paths (overrides --inventory-dir)")
    ap.add_argument("--tree", default="Events")
    ap.add_argument("--branches", nargs="*", default=[],
                    help="explicit branch names to tabulate")
    ap.add_argument("--pattern",
                    help="regex; tabulate every branch in ANY inventory that matches")
    ap.add_argument("--profile", choices=("main", "prescan", "cpv"),
                    help="pull the branch list from check_branchlist.py")
    ap.add_argument("--mc", action="store_true")
    ap.add_argument("--era", help="also include that era's HLT tables")
    ap.add_argument("--partial-only", action="store_true",
                    help="print only genuinely partial branches (MC-only and Data-only "
                         "splits are expected and are suppressed)")
    ap.add_argument("--show-expected", action="store_true",
                    help="also list the MC-only / Data-only branches")
    ap.add_argument("--repo-root", default=".", help="NtupleForge root (for --profile)")
    args = ap.parse_args()

    paths = args.inventories or sorted(glob.glob(os.path.join(args.inventory_dir, "*.tsv")))
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        sys.exit("ERROR(4): no inventories found. Run script/sweep_inventories.sh first.")

    invs = [read_inventory(p, args.tree) for p in paths]
    labels = [lab for lab, _ in invs]

    wanted = list(args.branches)
    if args.profile:
        wanted += load_profile(args.repo_root, args.profile, args.mc, args.era)
    if args.pattern:
        rx = re.compile(args.pattern)
        union = set()
        for _, names in invs:
            union |= {n for n in names if rx.search(n)}
        wanted += sorted(union)
    seen, uniq = set(), []
    for b in wanted:
        if b not in seen:
            seen.add(b); uniq.append(b)
    wanted = uniq
    if not wanted:
        sys.exit("ERROR(4): nothing to compare. Give --branches / --pattern / --profile.")

    print("=" * 78)
    print("inventories (%d), tree '%s':" % (len(invs), args.tree))
    for (lab, names), p in zip(invs, paths):
        print("  %-24s %5d branches   %s" % (lab, len(names), p))
    print("=" * 78)

    # An inventory is MC iff it carries genWeight -- measured, not guessed from
    # the label.
    mc_set = {i for i, (_, names) in enumerate(invs) if "genWeight" in names}
    data_set = set(range(len(invs))) - mc_set
    print("tier split (by genWeight): MC = %s" % ", ".join(labels[i] for i in sorted(mc_set)))
    print("                           Data = %s" % ", ".join(labels[i] for i in sorted(data_set)))
    print("=" * 78)

    everywhere, nowhere, partial, mconly, dataonly = [], [], [], [], []
    for b in wanted:
        hits = [b in names for _, names in invs]
        present = {i for i, h in enumerate(hits) if h}
        if all(hits):
            everywhere.append(b)
        elif not any(hits):
            nowhere.append(b)
        else:
            kind = classify(present, mc_set, data_set)
            if kind == "MC-ONLY":
                mconly.append((b, hits))
            elif kind == "DATA-ONLY":
                dataonly.append((b, hits))
            else:
                partial.append((b, hits))

    w = max([len(b) for b in wanted] + [10])
    hdr = " " * (w + 2) + " ".join("%-14s" % lab[:14] for lab in labels)
    if args.partial_only:
        rows = partial + (mconly + dataonly if args.show_expected else [])
    else:
        rows = [(b, [b in n for _, n in invs]) for b in wanted]
    if rows:
        print(hdr)
        print("-" * len(hdr))
        for b, hits in rows:
            cells = " ".join("%-14s" % ("o" if h else ".") for h in hits)
            mark = "  <-- PARTIAL" if (any(hits) and not all(hits)) else ""
            print("%-*s  %s%s" % (w, b, cells, mark))
    print()
    print("present in ALL inventories   : %d" % len(everywhere))
    print("absent  in ALL inventories   : %d" % len(nowhere))
    print("MC-only   (expected, gen info): %d" % len(mconly))
    print("Data-only (expected)          : %d" % len(dataonly))
    print("PARTIAL   (the dangerous set) : %d" % len(partial))
    if nowhere:
        print("\nabsent everywhere -- either a wrong name, or nothing here covers it:")
        for b in nowhere:
            print("   %s" % b)
    if partial:
        print("\nPARTIAL -- presence depends on era / primary dataset / tier.")
        print("A keep-list or requirement derived from ONE file will be wrong for the")
        print("others. Mark these era-conditional rather than 'missing' (A19).")
        for b, hits in partial:
            here = [labels[i] for i, h in enumerate(hits) if h]
            gone = [labels[i] for i, h in enumerate(hits) if not h]
            print("   %s" % b)
            print("      present: %s" % ", ".join(here))
            print("      absent : %s" % ", ".join(gone))

    if nowhere:
        sys.exit(3)
    if partial:
        sys.exit(2)
    print("\nevery requested branch is present in every inventory.")
    sys.exit(0)


if __name__ == "__main__":
    main()
