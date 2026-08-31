#!/usr/bin/env python3
r"""Event-matched comparison of the CPV gen categorizer across NanoAOD versions.

WHY THIS EXISTS
---------------
`validate_topcpvcat.py` answers "does the NtupleForge module agree with the
standalone C++ TopCPVGenCategorizer". It cannot answer the migration question,
because the standalone reads `GenPart_statusFlags` as `Int_t` and v15 stores it
as `UShort_t` -- on v15 it would return silent garbage, not an error.

So the v15 check is module-vs-module: run the SAME module over the SAME events
taken from a v9 file and a v15 file, and compare branch by branch.

GETTING THE SAME EVENTS IS THE HARD PART
----------------------------------------
v9 and v15 of this dataset share an identical MiniAODv2 parent, so the events
exist on both sides -- but the NanoAOD file boundaries do not correspond at all
(the first file of each has ZERO events in common). The two inputs must
therefore be paired by luminosity block and both runs restricted to the shared
lumi set (`run_postproc.py --cut`). See docs/08_branch_schema_migration.md.

This script does NOT assume the pairing worked: it joins on
(run, luminosityBlock, event) and FAILS if the overlap is empty, rather than
reporting "0 mismatches" on 0 compared events.

Usage
-----
    python3 script/compare_v9_v15.py --v9 matched_v9.root --v15 matched_v15.root
    [--prefix TopCPVCat_] [--ftol 1e-4] [--max-print 40] [--json out.json]

Exit codes
----------
    0  every common event agrees on every compared branch
    1  at least one branch disagrees
    2  the two files share no branches to compare
    3  the two files share no events (pairing failed) -- NOT a pass
    4  a file or its Events tree could not be read
"""
from __future__ import annotations

import argparse
import json
import sys


def _elem(x):
    """UChar_t elements can surface as 1-byte bytes/str under PyROOT."""
    if isinstance(x, (bytes, bytearray)):
        return x[0]
    if isinstance(x, str) and len(x) == 1:
        return ord(x)
    return x


def as_list(v):
    try:
        return [_elem(x) for x in v]
    except TypeError:
        return [_elem(v)]


def equalish(a, b, ftol, is_float):
    a, b = as_list(a), as_list(b)
    if len(a) != len(b):
        return False
    if is_float:
        return all(abs(x - y) <= ftol * (1.0 + abs(y)) for x, y in zip(a, b))
    return all(x == y for x, y in zip(a, b))


def branch_names(tree, prefix):
    return [b.GetName() for b in tree.GetListOfBranches()
            if b.GetName().startswith(prefix)]


def index_by_eventid(tree):
    """(run, lumi, event) -> entry number. Duplicate keys are reported, not hidden."""
    idx, dup = {}, 0
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        k = (int(tree.run), int(tree.luminosityBlock), int(tree.event))
        if k in idx:
            dup += 1
        idx[k] = i
    return idx, dup


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v9", required=True, help="module output from the v9 input")
    ap.add_argument("--v15", required=True, help="module output from the v15 input")
    ap.add_argument("--prefix", default="TopCPVCat_")
    ap.add_argument("--alias", action="append", default=[], metavar="A=B",
                    help="compare branch A in the v9 file against branch B in the "
                         "v15 file (repeatable). For a passthrough ntuple the two "
                         "versions do not share every name.")
    ap.add_argument("--v9v15-renames", action="store_true",
                    help="preload the measured v9->v15 renames as aliases "
                         "(MET_*/Rho_*/Electron_mvaIso_*; docs/08 3.1)")
    ap.add_argument("--ftol", type=float, default=1e-4,
                    help="relative tolerance for float branches (default 1e-4)")
    ap.add_argument("--max-print", type=int, default=40)
    ap.add_argument("--json", help="write a machine-readable summary here")
    args = ap.parse_args()

    import ROOT
    ROOT.gROOT.SetBatch(True)

    f9 = ROOT.TFile.Open(args.v9)
    f15 = ROOT.TFile.Open(args.v15)
    t9 = f9.Get("Events") if f9 and not f9.IsZombie() else None
    t15 = f15.Get("Events") if f15 and not f15.IsZombie() else None
    if not t9 or not t15:
        sys.exit("ERROR(4): could not read the Events tree of %s / %s"
                 % (args.v9, args.v15))

    b9 = set(branch_names(t9, args.prefix))
    b15 = set(branch_names(t15, args.prefix))
    # --- aliases: a renamed branch is the SAME quantity under two names -------
    RENAMES = [
        ("MET_pt", "PFMET_pt"), ("MET_phi", "PFMET_phi"),
        ("MET_sumEt", "PFMET_sumEt"), ("MET_significance", "PFMET_significance"),
        ("MET_covXX", "PFMET_covXX"), ("MET_covXY", "PFMET_covXY"),
        ("MET_covYY", "PFMET_covYY"),
        ("MET_fiducialGenPt", "FiducialMET_pt"),
        ("MET_fiducialGenPhi", "FiducialMET_phi"),
        ("RawMET_pt", "RawPFMET_pt"), ("RawMET_phi", "RawPFMET_phi"),
        ("RawMET_sumEt", "RawPFMET_sumEt"),
        ("TkMET_pt", "TrkMET_pt"), ("TkMET_phi", "TrkMET_phi"),
        ("TkMET_sumEt", "TrkMET_sumEt"),
        ("fixedGridRhoFastjetAll", "Rho_fixedGridRhoFastjetAll"),
        ("fixedGridRhoFastjetCentral", "Rho_fixedGridRhoFastjetCentral"),
        ("fixedGridRhoFastjetCentralCalo", "Rho_fixedGridRhoFastjetCentralCalo"),
        ("fixedGridRhoFastjetCentralNeutral", "Rho_fixedGridRhoFastjetCentralNeutral"),
        ("fixedGridRhoFastjetCentralChargedPileUp",
         "Rho_fixedGridRhoFastjetCentralChargedPileUp"),
        ("Electron_mvaFall17V2Iso", "Electron_mvaIso"),
        ("Electron_mvaFall17V2Iso_WP80", "Electron_mvaIso_WP80"),
        ("Electron_mvaFall17V2Iso_WP90", "Electron_mvaIso_WP90"),
        ("Electron_mvaFall17V2Iso_WPL", "Electron_mvaIso_WPL"),
        ("Electron_mvaFall17V2noIso", "Electron_mvaNoIso"),
        ("Electron_mvaFall17V2noIso_WP80", "Electron_mvaNoIso_WP80"),
        ("Electron_mvaFall17V2noIso_WP90", "Electron_mvaNoIso_WP90"),
        ("Electron_mvaFall17V2noIso_WPL", "Electron_mvaNoIso_WPL"),
    ]
    pairs = [(b, b) for b in sorted(b9 & b15)]
    aliased = []
    alias_src = (RENAMES if args.v9v15_renames else []) + \
                [tuple(a.split("=", 1)) for a in args.alias if "=" in a]
    for a, b in alias_src:
        if a in b9 and b in b15 and a != b:
            pairs.append((a, b))
            aliased.append("%s -> %s" % (a, b))
    common_br = [p[0] for p in pairs]
    alias_of = dict(pairs)
    only9 = sorted(b9 - b15 - {a for a, _ in pairs})
    only15 = sorted(b15 - b9 - {b for _, b in pairs})

    print("=" * 66)
    print("v9  file : %s   (%d entries, %d '%s' branches)"
          % (args.v9, t9.GetEntries(), len(b9), args.prefix))
    print("v15 file : %s   (%d entries, %d '%s' branches)"
          % (args.v15, t15.GetEntries(), len(b15), args.prefix))
    print("compared : %d branches (%d via alias)" % (len(common_br), len(aliased)))
    for a in aliased:
        print("     alias %s" % a)
    if only9:
        print("  !! only in v9 output : %s" % ", ".join(only9))
    if only15:
        print("  !! only in v15 output: %s" % ", ".join(only15))
    if not common_br:
        sys.exit("ERROR(2): no '%s' branches in common -- nothing to compare"
                 % args.prefix)

    float_br = {b for b in common_br
                if any(b.endswith(s) for s in
                       ("_pt", "_eta", "_phi", "_mass", "_energy"))}

    idx9, dup9 = index_by_eventid(t9)
    idx15, dup15 = index_by_eventid(t15)
    if dup9 or dup15:
        print("  !! duplicate (run,lumi,event) keys: v9=%d v15=%d "
              "(last entry wins)" % (dup9, dup15))

    common_ev = sorted(set(idx9) & set(idx15))
    print("-" * 66)
    print("events   : v9=%d  v15=%d  common=%d  (v9-only=%d, v15-only=%d)"
          % (len(idx9), len(idx15), len(common_ev),
             len(idx9) - len(common_ev), len(idx15) - len(common_ev)))

    if not common_ev:
        print()
        print("ERROR(3): the two outputs share NO events, so nothing was compared.")
        print("          This is a FAILURE of the file pairing, not agreement.")
        print("          Rebuild the shared-lumi cut and rerun both sides")
        print("          (source script/setup_v9v15_validation.sh).")
        sys.exit(3)

    per_branch = {}
    rows_bad = 0
    printed = 0
    for k in common_ev:
        t9.GetEntry(idx9[k])
        t15.GetEntry(idx15[k])
        bad_here = False
        for b in common_br:
            if not equalish(getattr(t9, b), getattr(t15, alias_of[b]),
                            args.ftol, b in float_br):
                per_branch[b] = per_branch.get(b, 0) + 1
                bad_here = True
                if printed < args.max_print:
                    tag = b if alias_of[b] == b else "%s/%s" % (b, alias_of[b])
                    print("  MISMATCH %s %s:\n      v9 =%s\n      v15=%s"
                          % (k, tag, as_list(getattr(t9, b)),
                             as_list(getattr(t15, alias_of[b]))))
                    printed += 1
        if bad_here:
            rows_bad += 1

    print("=" * 66)
    print("compared %d events x %d branches" % (len(common_ev), len(common_br)))
    print("events with >=1 disagreement: %d  (%.4f %%)"
          % (rows_bad, 100.0 * rows_bad / len(common_ev)))

    summary = {
        "v9": args.v9, "v15": args.v15,
        "entries_v9": t9.GetEntries(), "entries_v15": t15.GetEntries(),
        "branches_compared": len(common_br),
        "branches_only_v9": only9, "branches_only_v15": only15,
        "events_common": len(common_ev),
        "events_mismatched": rows_bad,
        "per_branch_mismatch": per_branch,
        "ftol": args.ftol,
    }
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(summary, fh, indent=2)
        print("wrote %s" % args.json)

    if per_branch:
        print("per-branch disagreement counts:")
        for b, c in sorted(per_branch.items(), key=lambda kv: -kv[1]):
            print("  %-40s %d" % (b, c))
        print()
        print("NOTE: float-only differences at the last ULP are expected "
              "(float32 storage); raise --ftol to confirm. An INTEGER branch "
              "disagreeing is a real v9/v15 difference and must be explained "
              "before the migration proceeds.")
        sys.exit(1)

    print()
    print("v9 and v15 AGREE on every compared branch of every common event.")
    sys.exit(0)


if __name__ == "__main__":
    main()
