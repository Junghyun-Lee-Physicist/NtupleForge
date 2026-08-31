#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_branchlist.py -- validate a NanoAODTools branch-selection file against a
real NanoAOD schema, and against what the ttHH analyzer actually reads.

Read-only. Nothing is submitted, produced or modified.

WHY
---
Two silent failure modes bracket every compressed branch list:

  (A) a `keep` pattern that matches NO branch in the input.
      ROOT prints a SetBranchStatus error ONCE PER JOB -- it is not silently
      ignored. This is why the prescan lists had to be split per year
      (docs/02_CHANGELOG.md 2026-07-27).

  (B) a branch the analyzer READS but the list DROPS (or that the NanoAOD
      version renamed away).
      tempTTHH's eventBuffer defaults a missing scalar to 0 and leaves a
      missing vector empty, printing only a summary line. Consequences seen or
      predicted: a missing `L1PreFiringWeight_Nom` makes every MC weight 0;
      a missing `Jet_puId` cuts every jet below 50 GeV; a missing `genTtbarId`
      bins all ttbar MC as tt+LF; a missing `Jet_area` makes the Jet collection
      length ZERO because that is the branch eventBuffer sizes it from.
      None of these crash.

(A) needs a real inventory (script/dump_branch_inventory.py).
(B) is checked against the list below, which was derived by tracing every
`_ev->` dereference in tempTTHH/ttHHanalyzer_unified.{cc,h}, src/*.cc and
include/*.h on 2026-08-17.

USAGE
-----
    # full check: keep-list vs real schema vs analyzer needs
    python3 script/check_branchlist.py branches/branch_hadronic_2018_v15_MC.txt \
        --inventory script/inventory/inv_2018UL_v15_MC.tsv --mc

    # no inventory yet: analyzer-coverage check only (still catches (B))
    python3 script/check_branchlist.py branches/branch_hadronic_2018_v15_MC.txt --mc

    # what would survive? print the resulting branch list
    python3 script/check_branchlist.py <list> --inventory <tsv> --print-kept

EXIT CODES
    0  all checks pass
    2  bad arguments
    3  a required analyzer branch would be dropped, or is absent from the file
    4  a keep/drop pattern matches nothing in the inventory (per-job ROOT error)
    (3 and 4 can both apply; the higher one is returned)
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys

# ---------------------------------------------------------------------------
# What the ttHH fully-hadronic analyzer actually dereferences.
#
# Each entry is a tuple of ACCEPTABLE names -- any one of them satisfies the
# requirement. Multi-name entries exist where the NanoAOD version renamed the
# branch; listing both means this file does not have to assert which version is
# in play. Sources for the renames: v9->v12 and v12->v15 change tables.
#
# flags: 'mc'       -> only required for MC inputs
#        'critical' -> eventBuffer sizes a whole collection from this branch,
#                      so dropping it silently yields an EMPTY collection
# ---------------------------------------------------------------------------
REQUIRED = [
    # ---- event scalars ----
    (("run",), ""),
    (("luminosityBlock",), ""),
    (("event",), ""),
    (("genWeight",), "mc"),
    (("genTtbarId",), "mc"),
    (("Pileup_nTrueInt",), "mc"),
    # Applied to the MC event weight only; the era config disables it for 2018.
    (("L1PreFiringWeight_Nom",), "mc"),
    (("fixedGridRhoFastjetAll", "Rho_fixedGridRhoFastjetAll"), ""),
    (("PV_npvsGood",), ""),
    (("MET_pt", "PFMET_pt"), ""),
    # ---- MET filters (setFilter(), ttHHanalyzer_unified.cc L495-504) ----
    (("Flag_goodVertices",), ""),
    (("Flag_globalSuperTightHalo2016Filter",), ""),
    (("Flag_HBHENoiseFilter",), ""),
    (("Flag_HBHENoiseIsoFilter",), ""),
    (("Flag_EcalDeadCellTriggerPrimitiveFilter",), ""),
    (("Flag_BadPFMuonFilter",), ""),
    (("Flag_BadPFMuonDzFilter",), ""),
    (("Flag_eeBadScFilter",), ""),
    (("Flag_ecalBadCalibFilter",), ""),
    # ---- Jet ----
    (("nJet",), ""),
    (("Jet_pt",), ""),
    (("Jet_eta",), ""),
    (("Jet_phi",), ""),
    (("Jet_mass",), ""),
    (("Jet_jetId",), ""),
    (("Jet_puId",), ""),
    (("Jet_area",), "critical"),
    (("Jet_rawFactor",), ""),
    (("Jet_btagDeepFlavB",), ""),
    (("Jet_genJetIdx",), "mc"),
    (("Jet_hadronFlavour",), "mc"),
    (("Jet_partonFlavour",), "mc"),
    # ---- Muon ----
    (("nMuon",), ""),
    (("Muon_pt",), ""),
    (("Muon_eta",), ""),
    (("Muon_phi",), ""),
    (("Muon_charge",), "critical"),
    (("Muon_tightId",), ""),
    (("Muon_pfRelIso04_all",), ""),
    (("Muon_miniPFRelIso_all",), ""),
    # ---- Electron ----
    (("nElectron",), ""),
    (("Electron_pt",), ""),
    (("Electron_eta",), ""),
    (("Electron_phi",), ""),
    (("Electron_charge",), "critical"),
    (("Electron_deltaEtaSC", "Electron_superclusterEta"), ""),
    (("Electron_mvaFall17V2Iso_WP90", "Electron_mvaIso_WP90"), ""),
    (("Electron_pfRelIso03_all",), ""),
    (("Electron_miniPFRelIso_all",), ""),
    # ---- GenJet / GenPart (MC only) ----
    (("nGenJet",), "mc"),
    (("GenJet_pt",), "mc"),
    (("GenJet_eta",), "mc critical"),
    (("GenJet_phi",), "mc"),
    (("GenJet_hadronFlavour",), "mc"),
    (("nGenPart",), "mc"),
    (("GenPart_pt",), "mc"),
    (("GenPart_eta",), "mc critical"),
    (("GenPart_phi",), "mc"),
    (("GenPart_mass",), "mc"),
    (("GenPart_pdgId",), "mc"),
    (("GenPart_statusFlags",), "mc"),
    (("GenPart_genPartIdxMother",), "mc"),
]

# The prescan mode never calls process()/createObjects() -- it reads only
# genWeight, genTtbarId, run/luminosityBlock/event from Events, plus the Runs
# tree (genEventSumw/Sumw2/Count, which the post-processor copies wholesale and
# which output-branch selection does not touch). So a prescan branch list is
# SUPPOSED to fail the main-profile check; use --profile prescan for those.
PRESCAN_REQUIRED = [
    (("run",), ""), (("luminosityBlock",), ""), (("event",), ""),
    (("genWeight",), "mc"), (("genTtbarId",), "mc"), (("Pileup_nTrueInt",), "mc"),
    (("PV_npvsGood",), ""), (("Flag_METFilters",), ""), (("Flag_goodVertices",), ""),
]

# ---------------------------------------------------------------------------
# CPV (top-CPV / SSB gen categorization) workstream.
#
# ⚠ INPUT vs OUTPUT -- do not conflate them.
# This file validates an OUTPUT branch selection. It does NOT govern what the
# module can READ: the PostProcessor is called with branchsel=None on the input
# side (A4 -- filtering the input produces a zombie file), so
# modules/topCPVCategorizer.py sees the complete NanoAOD regardless of what is
# listed here. Likewise the standalone TopCPVGenCategorizer reads the ORIGINAL
# central NanoAOD, never our ntuple. So GenPart_* / GenVisTau_* being dropped
# from the output costs the categorizer nothing.
#
# What the output MUST carry is what a downstream consumer reads back, and for
# this workstream that consumer is script/validate_topcpvcat.py:
#   * the 3-key (run, luminosityBlock, event) -- the join key;
#   * the module's own TopCPVCat_* branches (the DERIVED comparisons);
#   * GenJet_* / nGenJet, GenMET_*, PSWeight / nPSWeight -- the PASSTHROUGH and
#     INDEXED comparisons read these out of the Events tree of the OUTPUT file.
#     Drop any of them and the validation silently loses that coverage; since
#     2026-08-25 the comparator FAILS instead of warning, so it will be caught.
# ---------------------------------------------------------------------------
CPV_REQUIRED = [
    (("run",), ""), (("luminosityBlock",), ""), (("event",), ""),
    # passthrough comparisons (validate_topcpvcat.py PASSTHROUGH / COMPUTED)
    (("nGenJet",), "mc"),
    (("GenJet_pt",), "mc"), (("GenJet_eta",), "mc"), (("GenJet_phi",), "mc"),
    (("GenJet_mass",), "mc"), (("GenJet_partonFlavour",), "mc"),
    (("GenJet_hadronFlavour",), "mc"),
    (("GenMET_pt",), "mc"), (("GenMET_phi",), "mc"),
    # indexed comparisons (PSWeight_ISR_Up etc. are read as PSWeight[0..3])
    (("nPSWeight",), "mc"), (("PSWeight",), "mc"),
    # The module's own output. Flag 'produced' = CREATED by the module, so it
    # is by construction ABSENT from the input NanoAOD schema; check (C) must
    # skip it (it checks the input inventory). Only check (B) -- "does the rule
    # chain let it survive into the output" -- is meaningful for these. A
    # leading 'drop *' without a matching keep would erase the whole campaign.
    (("TopCPVCat_isSignal",), "mc,produced"),
    (("TopCPVCat_Channel_Idx",), "mc,produced"),
    (("TopCPVCat_Channel_Idx_Expanded",), "mc,produced"),
    (("TopCPVCat_GenPar_Count",), "mc,produced"),
    (("TopCPVCat_GenBJet_Count",), "mc,produced"),
    (("TopCPVCat_GenBHad_Count",), "mc,produced"),
]

# HLT paths, per era.
#
# ⚠ "the analyzer reads it" != "it must exist in THIS file". The HLT branch set
# is the menu of the run range the dataset covers, so it differs between primary
# datasets, between run eras, and between Data and MC. Measured on 2017UL v9:
# MC has 569 HLT paths, Data 526, and 43 are MC-only. Judging a path "does not
# exist" from ONE file is wrong -- that mistake was made on 2026-08-30.
#
# HLT_REQUIRED    : must be present; absence is a real finding.
# HLT_ERA_CONDITIONAL : the analyzer reads them through eventBuffer's
#     input->present() guard, but they only exist in some run eras / primary
#     datasets. Absence is EXPECTED and is reported as information, not failure.
#
# The four 2017 entries below are the **2017 Run B** hadronic paths (calo-based
# b-tagging at HLT; replaced by the PF versions from Run C onward). Measured
# per era on 2026-08-31, /JetHT/Run2017?-UL2017_MiniAODv2_NanoAODv9:
#     Run B  1208 Events / 269 HLT   <- these four, and ONLY here
#     Run C  1523 / 479              <- PF CSV only
#     Run D  1570 / 526              <- PF CSV + PF DeepCSV
#     Run E  1612 / 526
#     Run F  1666 / 580
#     UL17 MC 1666 / 569
# So they exist and fire on the Run2017B primary datasets, and are correctly 0
# elsewhere. tempTTHH/include/eventBuffer.h is a deliberate 2017+2018 superset
# header (583 HLT) whose input->present() guard handles their absence.
HLT_ERA_CONDITIONAL = {
    "2017": ["HLT_HT300PT30_QuadJet_75_60_45_40",
             "HLT_HT300PT30_QuadJet_75_60_45_40_TripeCSV_p07",
             "HLT_PFHT430_SixJet40_BTagCSV_p080",
             "HLT_PFHT380_SixJet32_DoubleBTagCSV_p075"],
    "2018": [],
}

# The analyzer FATALs if the 2018 four are absent (requireTriggerBranches2018_(),
# ttHHanalyzer_unified.cc L337-342); the 2017 ones are read without a guard.
HLT_REQUIRED = {
    "2017": ["HLT_PFHT1050", "HLT_IsoMu27",
             "HLT_PFHT300PT30_QuadPFJet_75_60_45_40_TriplePFBTagCSV_3p0",
             "HLT_PFHT430_SixPFJet40_PFBTagCSV_1p5",
             "HLT_PFHT380_SixPFJet32_DoublePFBTagCSV_2p2"],
    "2018": ["HLT_PFHT1050", "HLT_IsoMu27",
             "HLT_PFHT330PT30_QuadPFJet_75_60_45_40_TriplePFBTagDeepCSV_4p5",
             "HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94",
             "HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59"],
}


# ---------------------------------------------------------------------------

def read_rules(path):
    """-> [(action, pattern, lineno)] in file order."""
    rules = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            f = line.split()
            if len(f) < 2 or f[0] not in ("keep", "drop"):
                print("[check] WARNING: line %d is not 'keep <pat>' / 'drop <pat>': %r"
                      % (i, line))
                continue
            rules.append((f[0], f[1], i))
    return rules


def read_inventory(path, tree="Events"):
    names = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) >= 2 and f[0] == tree:
                names.append(f[1])
    return names


def apply_rules(branches, rules):
    """NanoAODTools semantics: a branch matching no rule is KEPT; later rules
    override earlier ones. Returns (kept:set, matched_per_rule:dict)."""
    status = {b: True for b in branches}
    matched = {i: 0 for i, _ in enumerate(rules)}
    for i, (action, pat, _ln) in enumerate(rules):
        hit = fnmatch.filter(branches, pat)
        matched[i] = len(hit)
        for b in hit:
            status[b] = (action == "keep")
    return {b for b, v in status.items() if v}, matched


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("branchlist", help="NanoAODTools branch selection file")
    ap.add_argument("--inventory", help="TSV from dump_branch_inventory.py")
    ap.add_argument("--tree", default="Events")
    ap.add_argument("--mc", action="store_true", help="input is MC (checks gen branches too)")
    ap.add_argument("--era", choices=sorted(HLT_REQUIRED), help="also check the HLT paths for this era")
    ap.add_argument("--profile", choices=("main", "prescan", "cpv"), default="main",
                    help="which consumer the list is for. 'main' = ttHH hadronic "
                         "analyzer (default); 'prescan' = the small set prescan "
                         "mode reads; 'cpv' = the top-CPV gen categorizer plus "
                         "what validate_topcpvcat.py needs to see in the output")
    ap.add_argument("--print-kept", action="store_true", help="print the surviving branch names")
    args = ap.parse_args()

    if not os.path.isfile(args.branchlist):
        sys.exit("FATAL: cannot read '%s'" % args.branchlist)
    rules = read_rules(args.branchlist)
    required = {"prescan": PRESCAN_REQUIRED,
                "cpv": CPV_REQUIRED}.get(args.profile, REQUIRED)
    if not rules:
        sys.exit("FATAL: no keep/drop rules found in '%s'" % args.branchlist)
    print("[check] %s: %d rule(s)  |  profile=%s  |  %s"
          % (args.branchlist, len(rules), args.profile, "MC" if args.mc else "Data"))

    rc = 0

    # ---- (B) analyzer coverage. Works with or without an inventory. ----
    # Without an inventory we can only ask "does some keep rule match this
    # name", which is a lower bound but catches an outright omission.
    keep_pats = [p for a, p, _ in rules if a == "keep"]
    drop_pats = [(p, i) for i, (a, p, _) in enumerate(rules) if a == "drop"]

    def survives(name):
        """Simulate the rule chain for a single hypothetical branch name."""
        st = True
        for action, pat, _ln in rules:
            if fnmatch.fnmatch(name, pat):
                st = (action == "keep")
        return st

    missing, missing_crit = [], []
    for names, flags in required:
        if "mc" in flags and not args.mc:
            continue
        if not any(survives(n) for n in names):
            (missing_crit if "critical" in flags else missing).append("|".join(names))

    hlt_missing = []
    if args.era and args.profile == "cpv":
        print("[check] NOTE: --era ignored for --profile cpv (the CPV categorizer "
              "has no HLT dependency; its logic has zero year branching).")
    elif args.era:
        for h in HLT_REQUIRED[args.era]:
            if not survives(h):
                hlt_missing.append(h)

    print()
    print("=== (B) branches the analyzer reads but this list would DROP ===")
    if missing_crit:
        rc = max(rc, 3)
        print("  !! CRITICAL (eventBuffer sizes a whole collection from these --")
        print("  !! dropping one yields an EMPTY collection with no error):")
        for m in missing_crit:
            print("       %s" % m)
    if missing:
        rc = max(rc, 3)
        print("  !! MISSING (silently defaulted to 0 / empty by eventBuffer):")
        for m in missing:
            print("       %s" % m)
    if hlt_missing:
        rc = max(rc, 3)
        print("  !! HLT paths missing for era %s:" % args.era)
        for m in hlt_missing:
            print("       %s" % m)
    if not (missing or missing_crit or hlt_missing):
        n = sum(1 for names, fl in required if args.mc or "mc" not in fl)
        n += len(HLT_REQUIRED[args.era]) if args.era else 0
        print("  OK -- all %d required branch(es) survive the rule chain." % n)

    # ---- (A) patterns that match nothing in the real schema ----
    print()
    print("=== (A) keep/drop patterns vs the real schema ===")
    if not args.inventory:
        print("  SKIPPED -- no --inventory given.")
        print("  Run script/dump_branch_inventory.py on one real file of the target")
        print("  (era, NanoAOD version, MC/Data) and pass the TSV. Without it you")
        print("  cannot know whether a v15 name in this list actually exists, and")
        print("  every wrong name costs one ROOT error per job.")
    else:
        if not os.path.isfile(args.inventory):
            sys.exit("FATAL: cannot read inventory '%s'" % args.inventory)
        branches = read_inventory(args.inventory, args.tree)
        if not branches:
            sys.exit("FATAL: inventory has no rows for tree '%s'" % args.tree)
        kept, matched = apply_rules(branches, rules)
        dead = [(rules[i][0], rules[i][1], rules[i][2]) for i in matched if matched[i] == 0]
        print("  inventory: %d branch(es) in tree '%s'" % (len(branches), args.tree))
        print("  kept     : %d  (%.1f %% of the input)" % (len(kept), 100.0 * len(kept) / len(branches)))
        if dead:
            rc = max(rc, 4)
            print("  !! %d pattern(s) match NOTHING -> one ROOT SetBranchStatus error"
                  % len(dead))
            print("  !! per job each. Fix or remove them:")
            for action, pat, ln in dead:
                cand = [b for b in branches
                        if pat.strip("*").split("_")[-1] and
                        pat.strip("*").split("_")[-1].lower() in b.lower()][:4]
                extra = ("   candidates: " + ", ".join(cand)) if cand else ""
                print("       line %-4d %s %s%s" % (ln, action, pat, extra))
        else:
            print("  OK -- every pattern matches at least one branch.")

        # cross-check: required branches that are simply not in this file
        absent = []
        n_produced = 0
        for names, flags in required:
            if "mc" in flags and not args.mc:
                continue
            if "produced" in flags:
                # created by the analysis module -- never in the input schema.
                # (B) above already checked that the rule chain keeps it.
                n_produced += 1
                continue
            if not any(n in branches for n in names):
                absent.append("|".join(names))
        cond_absent = []
        if args.era:
            absent += [h for h in HLT_REQUIRED[args.era] if h not in branches]
            cond_absent = [h for h in HLT_ERA_CONDITIONAL.get(args.era, [])
                           if h not in branches]
        print()
        print("=== (C) analyzer requirements ABSENT FROM THE INPUT FILE ITSELF ===")
        if n_produced:
            print("  (%d module-produced branch(es) excluded -- see check (B))"
                  % n_produced)
        if absent:
            rc = max(rc, 3)
            print("  !! the keep-list cannot help here -- the branch does not exist in")
            print("  !! this NanoAOD version. Each one needs an analyzer-side decision")
            print("  !! (rename, replacement variable, or drop the cut):")
            for a in absent:
                print("       %s" % a)
        else:
            print("  OK -- every required branch exists in the input schema.")
        if cond_absent:
            print("  info: %d era-conditional HLT path(s) absent -- EXPECTED, not a"
                  % len(cond_absent))
            print("        failure. They exist only in some run eras / primary")
            print("        datasets and eventBuffer guards them with present():")
            for h in cond_absent:
                print("          %s" % h)

        if args.print_kept:
            print()
            print("=== kept branches (%d) ===" % len(kept))
            for b in sorted(kept):
                print("  " + b)

    print()
    print("[check] exit %d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
