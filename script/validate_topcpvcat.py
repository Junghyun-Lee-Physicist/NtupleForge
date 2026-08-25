#!/usr/bin/env python3
r"""Validate topCPVCategorizer output against the standalone TopCPVCategorizer.

Run on lxplus (needs ROOT + a NanoAOD test file processed both ways). It matches
events by (run, luminosityBlock, event) and compares branch-by-branch:
integer/categorization branches must be **exactly** equal; float branches must
agree within a tolerance (TopCPV computes in float32, this port in float64 then
ROOT stores float32, so the last ULP can differ -- that is expected and benign).

=============================================================================
2026-08-25 HARDENING -- read this before trusting a green result
=============================================================================
The previous version returned **exit 0** in three situations where nothing had
actually been proven:

  1. Unmatched events. If the two files processed different event sets, the
     matched subset could be empty or tiny and the tool still printed the
     success line. Now: unmatched != 0 is a FAILURE (--allow-unmatched to
     override, e.g. when comparing a -N subset against a full run).
  2. A passthrough branch missing on either side. It printed a WARNING and
     kept going, so a typo'd or renamed branch silently dropped out of the
     comparison. Now: a missing branch is a FAILURE (--allow-missing).
  3. Branches nobody compared. The docstring claimed `PSWeight_*` was covered
     but it was not in any list, and Channel_Idx_Expanded / GenJet_Count /
     GenJet_energy were uncompared too -- 11 of GenCatTree's 64 branches were
     outside the comparison, silently.

All three are fixed. Coverage is now accounted for explicitly and printed, so
"uncompared" can never again be invisible. The four previously-impossible
comparisons are now possible because the standalone's conventions were read
out of its source (src/TopCPVGenCategorizer.cpp):

    GenJet_Count      == nGenJet                            (L928)
    GenJet_energy     == sqrt((pt*cosh(eta))^2 + mass^2)    (L922, recomputed here)
    PSWeight_n        == nPSWeight                          (L1010)
    PSWeight_ISR_Up   == PSWeight[0]   (default 1.0 if nPSWeight < 1)   (L1011)
    PSWeight_FSR_Up   == PSWeight[1]   (default 1.0 if nPSWeight < 2)   (L1012)
    PSWeight_ISR_Down == PSWeight[2]   (default 1.0 if nPSWeight < 3)   (L1013)
    PSWeight_FSR_Down == PSWeight[3]   (default 1.0 if nPSWeight < 4)   (L1014)

Only run / luminosityBlock / event remain uncompared -- they ARE the join key.

Usage
-----
    python3 validate_topcpvcat.py \
        --nano   forgedNtuple.root \             # NtupleForge output (Events tree, TopCPVCat_*)
        --gencat gencat.root \                   # TopCPVCategorizer output (GenCatTree)
        [--prefix TopCPVCat_] [--ftol 1e-4] [--max-print 40]
        [--allow-unmatched] [--allow-missing] [--json summary.json]

Branch map
----------
TopCPV GenCatTree branch  ->  NtupleForge Events branch
  Derived (the module emits these under the prefix):
      isSignal, SelectedIdx, GenPar_*, GenTop_*, GenAnTop_*, Channel_*,
      GenBJet_*, GenBHad_*                         ->  <prefix><same name>
  Passthrough (the module does NOT re-emit; compared to raw NanoAOD names):
      GenJet_*, GenMET_*                           ->  <same name, no prefix>
  Indexed / computed (see the hardening note above):
      PSWeight_*, GenJet_Count, GenJet_energy

EXIT CODES
----------
    0  every compared branch agrees on every matched event
    1  a value mismatch (ints must be exact; floats within --ftol)
    2  bad arguments / could not read a file or tree
    3  unmatched events (the two files did not process the same event set)
    4  a branch needed for a comparison is missing on one side
    (several can apply; the highest is returned)
"""
from __future__ import annotations

import argparse
import json
import math
import sys

# NB: ROOT is imported inside main(), not at module scope. At module scope even
# `--help` died with ModuleNotFoundError on a machine without PyROOT, which made
# the tool undiscoverable outside a CMSSW shell.

# TopCPV branch -> compared against <prefix><same name> in Events.
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
    # 2026-08-25: both sides emit this and neither compared it until now.
    "Channel_Idx_Expanded",
    "GenBJet_Count", "GenBHad_Count",
    "GenBJet_pt", "GenBJet_eta", "GenBJet_phi", "GenBJet_energy",
    "GenBHad_pt", "GenBHad_eta", "GenBHad_phi", "GenBHad_energy",
    "GenBHad_FromTopWeakDecay", "GenBHad_Flavour",
]

# Direct name pairs: (GenCatTree name, NanoAOD Events name). Names differ across
# the two trees (SSB capitalization vs NanoAOD lowercase).
PASSTHROUGH = [
    ("GenJet_pt", "GenJet_pt"), ("GenJet_eta", "GenJet_eta"),
    ("GenJet_phi", "GenJet_phi"), ("GenJet_mass", "GenJet_mass"),
    ("GenJet_HadronFlavour", "GenJet_hadronFlavour"),
    ("GenJet_PartonFlavour", "GenJet_partonFlavour"),
    ("GenMET_pt", "GenMET_pt"), ("GenMET_phi", "GenMET_phi"),
    # scalar counts
    ("GenJet_Count", "nGenJet"),
    ("PSWeight_n", "nPSWeight"),
]

# (GenCatTree scalar, NanoAOD array, index, default when the array is shorter).
# Convention read from the standalone source, not guessed.
INDEXED = [
    ("PSWeight_ISR_Up",   "PSWeight", 0, 1.0),
    ("PSWeight_FSR_Up",   "PSWeight", 1, 1.0),
    ("PSWeight_ISR_Down", "PSWeight", 2, 1.0),
    ("PSWeight_FSR_Down", "PSWeight", 3, 1.0),
]

# GenCatTree branches with no stored NanoAOD counterpart, recomputed here from
# NanoAOD inputs. This validates the standalone's own arithmetic rather than
# skipping it.
COMPUTED = ["GenJet_energy"]

# The join key -- deliberately not compared.
KEY_BRANCHES = {"run", "luminosityBlock", "event"}

FLOAT_BRANCHES = {
    b for b in (DERIVED + [g for g, _ in PASSTHROUGH]
                + [g for g, _, _, _ in INDEXED] + COMPUTED)
    if any(b.endswith(s) for s in ("_pt", "_eta", "_phi", "_mass", "_energy"))
    or b.startswith("PSWeight_") and b != "PSWeight_n"
}


def _elem(x):
    # UChar_t elements can surface as 1-byte bytes/str under PyROOT
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


def index_by_eventid(tree):
    idx = {}
    for i in range(tree.GetEntries()):
        tree.GetEntry(i)
        idx[(int(tree.run), int(tree.luminosityBlock), int(tree.event))] = i
    return idx


def branch_names(tree):
    return {b.GetName() for b in tree.GetListOfBranches()}


def gen_jet_energy_from_nano(ev):
    """E = sqrt((pt*cosh(eta))^2 + m^2), element-wise -- the standalone builds a
    TLorentzVector from (pt, eta, phi, mass) and stores its E()."""
    pt = as_list(ev.GenJet_pt)
    eta = as_list(ev.GenJet_eta)
    m = as_list(ev.GenJet_mass)
    return [math.sqrt((p * math.cosh(e)) ** 2 + mm * mm)
            for p, e, mm in zip(pt, eta, m)]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nano", required=True, help="NtupleForge output (Events tree)")
    ap.add_argument("--gencat", required=True, help="TopCPVCategorizer output (GenCatTree)")
    ap.add_argument("--prefix", default="TopCPVCat_")
    ap.add_argument("--ftol", type=float, default=1e-4)
    ap.add_argument("--max-print", type=int, default=40)
    ap.add_argument("--allow-unmatched", action="store_true",
                    help="do not fail on unmatched events (use when comparing a "
                         "-N subset against a full run; the matched subset is "
                         "still compared)")
    ap.add_argument("--allow-missing", action="store_true",
                    help="do not fail when a branch needed for a comparison is "
                         "absent; it is reported as UNCOMPARED instead")
    ap.add_argument("--json", help="write a machine-readable summary here")
    args = ap.parse_args()

    try:
        import ROOT
    except ImportError:
        sys.exit("ERROR: PyROOT not available. Run inside a CMSSW environment "
                 "(cmsenv) on lxplus or Tier-3.")
    ROOT.gROOT.SetBatch(True)

    fn = ROOT.TFile.Open(args.nano)
    fg = ROOT.TFile.Open(args.gencat)
    if not fn or fn.IsZombie():
        sys.exit("ERROR: could not open --nano '%s'" % args.nano)
    if not fg or fg.IsZombie():
        sys.exit("ERROR: could not open --gencat '%s'" % args.gencat)
    ev = fn.Get("Events")
    gc = fg.Get("GenCatTree")
    if not ev or not gc:
        sys.exit("ERROR: could not read Events / GenCatTree")

    ev_br, gc_br = branch_names(ev), branch_names(gc)

    # ---- resolve what can actually be compared, BEFORE looping -------------
    missing = []          # (gencat branch, reason)
    use_derived, use_passthrough, use_indexed, use_computed = [], [], [], []

    for sb in DERIVED:
        nb = args.prefix + sb
        if sb not in gc_br:
            missing.append((sb, "absent from GenCatTree"))
        elif nb not in ev_br:
            missing.append((sb, "Events lacks %s" % nb))
        else:
            use_derived.append(sb)

    for gb, nb in PASSTHROUGH:
        if gb not in gc_br:
            missing.append((gb, "absent from GenCatTree"))
        elif nb not in ev_br:
            missing.append((gb, "Events lacks %s" % nb))
        else:
            use_passthrough.append((gb, nb))

    for gb, arr, i, dflt in INDEXED:
        if gb not in gc_br:
            missing.append((gb, "absent from GenCatTree"))
        elif arr not in ev_br:
            missing.append((gb, "Events lacks %s" % arr))
        else:
            use_indexed.append((gb, arr, i, dflt))

    need_for_energy = {"GenJet_pt", "GenJet_eta", "GenJet_mass"}
    for gb in COMPUTED:
        if gb not in gc_br:
            missing.append((gb, "absent from GenCatTree"))
        elif not need_for_energy <= ev_br:
            missing.append((gb, "Events lacks %s" %
                            ",".join(sorted(need_for_energy - ev_br))))
        else:
            use_computed.append(gb)

    compared = (set(use_derived) | {g for g, _ in use_passthrough}
                | {g for g, _, _, _ in use_indexed} | set(use_computed))
    uncompared = sorted(gc_br - compared - KEY_BRANCHES)

    # ---- event loop --------------------------------------------------------
    ev_idx = index_by_eventid(ev)
    n_common = n_mismatch = n_gc_unmatched = 0
    per_branch_fail = {}
    printed = 0

    for j in range(gc.GetEntries()):
        gc.GetEntry(j)
        key = (int(gc.run), int(gc.luminosityBlock), int(gc.event))
        if key not in ev_idx:
            n_gc_unmatched += 1
            continue
        ev.GetEntry(ev_idx[key])
        n_common += 1
        row_bad = False

        def fail(name, got, exp):
            nonlocal row_bad, printed
            per_branch_fail[name] = per_branch_fail.get(name, 0) + 1
            row_bad = True
            if printed < args.max_print:
                print("  MISMATCH %s %s: gencat=%s nano=%s" % (key, name, got, exp))
                printed += 1

        for sb in use_derived:
            g, n = getattr(gc, sb), getattr(ev, args.prefix + sb)
            if not equalish(g, n, args.ftol, sb in FLOAT_BRANCHES):
                fail(sb, as_list(g), as_list(n))

        for gb, nb in use_passthrough:
            g, n = getattr(gc, gb), getattr(ev, nb)
            if not equalish(g, n, args.ftol, gb in FLOAT_BRANCHES):
                fail(gb, as_list(g), as_list(n))

        for gb, arr, i, dflt in use_indexed:
            vals = as_list(getattr(ev, arr))
            expect = vals[i] if len(vals) > i else dflt
            got = _elem(getattr(gc, gb))
            if not equalish(got, expect, args.ftol, True):
                fail(gb, got, expect)

        for gb in use_computed:
            got = as_list(getattr(gc, gb))
            expect = gen_jet_energy_from_nano(ev)
            if not equalish(got, expect, args.ftol, True):
                fail(gb, got, expect)

        if row_bad:
            n_mismatch += 1

    n_ev_unmatched = len(ev_idx) - n_common

    # ---- report ------------------------------------------------------------
    print("\n" + "=" * 72)
    print("COVERAGE")
    print("  GenCatTree branches      : %d" % len(gc_br))
    print("  compared                 : %d  (derived %d, passthrough %d, "
          "indexed %d, computed %d)" % (len(compared), len(use_derived),
                                        len(use_passthrough), len(use_indexed),
                                        len(use_computed)))
    print("  join key (not compared)  : %d  %s" %
          (len(KEY_BRANCHES & gc_br), sorted(KEY_BRANCHES & gc_br)))
    if uncompared:
        print("  !! UNCOMPARED            : %d  %s" % (len(uncompared), uncompared))
        print("     (a branch exists in GenCatTree that no rule covers -- if the")
        print("      standalone gained a branch, add it to DERIVED/PASSTHROUGH here)")
    else:
        print("  uncompared               : 0")
    if missing:
        print("  !! MISSING (comparison impossible):")
        for b, why in missing:
            print("       %-24s %s" % (b, why))

    print("\nEVENTS")
    print("  matched                  : %d" % n_common)
    print("  rows with >=1 mismatch   : %d" % n_mismatch)
    print("  unmatched                : %d GenCatTree-only, %d Events-only"
          % (n_gc_unmatched, n_ev_unmatched))

    rc = 0
    if per_branch_fail:
        print("\nPER-BRANCH MISMATCH COUNTS")
        for b, c in sorted(per_branch_fail.items(), key=lambda kv: -kv[1]):
            print("  %-28s %d" % (b, c))
        print("\nNOTE: float-only mismatches are usually float32-vs-float64 ULP; "
              "raise --ftol.\n      INTEGER-branch mismatches indicate a real "
              "difference and must be understood.")
        rc = max(rc, 1)

    if (n_gc_unmatched or n_ev_unmatched) and not args.allow_unmatched:
        print("\nFAIL: the two files did not process the same event set.")
        print("      Re-run both sides on the SAME input file with the SAME -N,")
        print("      or pass --allow-unmatched if the subset is intentional.")
        rc = max(rc, 3)
    if missing and not args.allow_missing:
        print("\nFAIL: %d branch(es) could not be compared (see MISSING above)."
              % len(missing))
        rc = max(rc, 4)

    if rc == 0 and n_common == 0:
        print("\nFAIL: zero events matched -- nothing was actually compared.")
        rc = 3
    if rc == 0:
        print("\nALL %d MATCHED EVENTS AGREE across %d branches "
              "(ints exact, floats within %g)." % (n_common, len(compared), args.ftol))

    if args.json:
        with open(args.json, "w") as fh:
            json.dump({
                "nano": args.nano, "gencat": args.gencat, "ftol": args.ftol,
                "n_matched": n_common, "n_rows_mismatched": n_mismatch,
                "n_unmatched_gencat_only": n_gc_unmatched,
                "n_unmatched_events_only": n_ev_unmatched,
                "n_gencat_branches": len(gc_br), "n_compared": len(compared),
                "uncompared": uncompared,
                "missing": [{"branch": b, "reason": w} for b, w in missing],
                "per_branch_fail": per_branch_fail, "exit_code": rc,
            }, fh, indent=1)
        print("[validate] wrote %s" % args.json)

    print("=" * 72)
    return rc


if __name__ == "__main__":
    sys.exit(main())
