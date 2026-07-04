#!/usr/bin/env python3
r"""Validate topCPVCategorizer output against the standalone TopCPVCategorizer.

Run on lxplus (needs ROOT + a NanoAOD test file processed both ways). It matches
events by (run, luminosityBlock, event) and compares branch-by-branch:
integer/categorization branches must be **exactly** equal; float branches must
agree within a tolerance (TopCPV computes in float32, this port in float64 then
ROOT stores float32, so the last ULP can differ — that is expected and benign).

Usage
-----
    python validate_topcpvcat.py \
        --nano   forgedNtuple.root \           # NtupleForge output (Events tree, TopCPVCat_*)
        --gencat gencat.root \                   # TopCPVCategorizer output (GenCatTree)
        [--prefix TopCPVCat_] [--ftol 1e-4] [--max-print 40]

Branch map
----------
TopCPV GenCatTree branch  ->  NtupleForge Events branch
  Derived (the module emits these under the prefix):
      isSignal, SelectedIdx, GenPar_*, GenTop_*, GenAnTop_*, Channel_*,
      GenBJet_*, GenBHad_*                         ->  <prefix><same name>
  Passthrough (the module does NOT re-emit; compared to raw NanoAOD names):
      GenJet_*, GenMET_*, PSWeight_*               ->  <same name, no prefix>
"""
from __future__ import annotations

import argparse
import sys

import ROOT

# TopCPV branch -> ("derived"|"passthrough"). Derived get the prefix; passthrough
# are compared against the unprefixed NanoAOD names already in the Events tree.
DERIVED = [
    "isSignal", "SelectedIdx",
    "GenPar_Count", "GenPar_Idx", "GenPar_pdgId", "GenPar_Status",
    "GenPar_pt", "GenPar_eta", "GenPar_phi", "GenPar_mass", "GenPar_energy",
    "GenPar_Mom1_Idx", "GenPar_Mom2_Idx", "GenPar_Dau1_Idx", "GenPar_Dau2_Idx",
    "GenPar_Mom_Counter", "GenPar_Dau_Counter",
    "GenTop_pt", "GenTop_eta", "GenTop_phi", "GenTop_energy",
    "GenAnTop_pt", "GenAnTop_eta", "GenAnTop_phi", "GenAnTop_energy",
    "Channel_Idx", "Channel_Idx_Final", "Channel_Lepton_Count",
    "Channel_Lepton_Count_Final", "Channel_Jets", "Channel_Jets_Abs",
    "Channel_Tau_Lepton", "Channel_Visible_Tau",
    "GenBJet_Count", "GenBHad_Count",
    "GenBJet_pt", "GenBJet_eta", "GenBJet_phi", "GenBJet_energy",
    "GenBHad_pt", "GenBHad_eta", "GenBHad_phi", "GenBHad_energy",
    "GenBHad_FromTopWeakDecay", "GenBHad_Flavour",
]
PASSTHROUGH = [
    "GenJet_pt", "GenJet_eta", "GenJet_phi", "GenJet_mass", "GenJet_energy",
    "GenJet_PartonFlavour", "GenJet_HadronFlavour",
    "GenMET_pt", "GenMET_phi",
    "PSWeight_n",
]
FLOAT_BRANCHES = {
    b for b in DERIVED + PASSTHROUGH
    if any(b.endswith(s) for s in ("_pt", "_eta", "_phi", "_mass", "_energy"))
}


def as_list(v):
    try:
        return list(v)
    except TypeError:
        return [v]


def equalish(a, b, ftol, is_float):
    a, b = as_list(a), as_list(b)
    if len(a) != len(b):
        return False
    if is_float:
        return all(abs(x - y) <= ftol * (1.0 + abs(y)) for x, y in zip(a, b))
    return all(x == y for x, y in zip(a, b))


def index_by_eventid(tree):
    idx = {}
    n = tree.GetEntries()
    for i in range(n):
        tree.GetEntry(i)
        key = (int(tree.run), int(tree.luminosityBlock), int(tree.event))
        idx[key] = i
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nano", required=True, help="NtupleForge output (Events tree)")
    ap.add_argument("--gencat", required=True, help="TopCPVCategorizer output (GenCatTree)")
    ap.add_argument("--prefix", default="TopCPVCat_")
    ap.add_argument("--ftol", type=float, default=1e-4)
    ap.add_argument("--max-print", type=int, default=40)
    args = ap.parse_args()

    fn = ROOT.TFile.Open(args.nano)
    fg = ROOT.TFile.Open(args.gencat)
    ev = fn.Get("Events")
    gc = fg.Get("GenCatTree")
    if not ev or not gc:
        sys.exit("ERROR: could not read Events / GenCatTree")

    ev_idx = index_by_eventid(ev)
    n_common = n_mismatch = 0
    per_branch_fail = {}
    printed = 0

    for j in range(gc.GetEntries()):
        gc.GetEntry(j)
        key = (int(gc.run), int(gc.luminosityBlock), int(gc.event))
        if key not in ev_idx:
            continue
        ev.GetEntry(ev_idx[key])
        n_common += 1
        row_bad = False
        for sb in DERIVED:
            nb = args.prefix + sb
            if not equalish(getattr(gc, sb), getattr(ev, nb),
                            args.ftol, sb in FLOAT_BRANCHES):
                per_branch_fail[sb] = per_branch_fail.get(sb, 0) + 1
                row_bad = True
                if printed < args.max_print:
                    print(f"  MISMATCH {key} {sb}: gencat={as_list(getattr(gc, sb))} "
                          f"nano={as_list(getattr(ev, nb))}")
                    printed += 1
        for sb in PASSTHROUGH:
            if ev.GetBranch(sb) is None:
                continue
            if not equalish(getattr(gc, sb), getattr(ev, sb),
                            args.ftol, sb in FLOAT_BRANCHES):
                per_branch_fail[sb] = per_branch_fail.get(sb, 0) + 1
                row_bad = True
        if row_bad:
            n_mismatch += 1

    print("\n" + "=" * 64)
    print(f"matched events: {n_common}   rows with >=1 mismatch: {n_mismatch}")
    if per_branch_fail:
        print("per-branch mismatch counts:")
        for b, c in sorted(per_branch_fail.items(), key=lambda kv: -kv[1]):
            print(f"  {b}: {c}")
        print("\nNOTE: float-only mismatches are usually float32-vs-float64 ULP; "
              "raise --ftol. Integer-branch mismatches indicate a real difference.")
        sys.exit(1)
    print("ALL MATCHED EVENTS AGREE (ints exact, floats within tol). ✔")


if __name__ == "__main__":
    main()
