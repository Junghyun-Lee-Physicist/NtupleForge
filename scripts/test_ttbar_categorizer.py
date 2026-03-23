#!/usr/bin/env python3
"""
Standalone tt+jets Categorization Tester
=========================================
Reads a NanoAOD/skimmed ROOT file directly (no NanoAODTools dependency)
and runs the same categorization logic as ttbarCategorizer.py,
printing detailed debug output for each event.

Usage:
    python3 scripts/test_ttbar_categorizer.py <input.root> [--max-events N] [--tree Events]

Examples:
    # Test on a Tier3 ntuple (first 20 events)
    python3 scripts/test_ttbar_categorizer.py /pnfs/.../slimmedNtuple_10.root --max-events 20

    # Test with xrootd
    python3 scripts/test_ttbar_categorizer.py root://cms-xrd-global.cern.ch//store/.../file.root

Author: auto-generated for debugging ttCat mismatch
"""
from __future__ import annotations

import sys
import math
import argparse
from collections import Counter

# -------------------------------------------------------------------------
# Try to import ROOT
# -------------------------------------------------------------------------
try:
    import ROOT
    ROOT.gROOT.SetBatch(True)
except ImportError:
    print("ERROR: PyROOT not available. Run inside a CMSSW environment:")
    print("  cmsenv  # or source the ROOT setup")
    sys.exit(1)


# =========================================================================
# Physics helpers (same as ttbarCategorizer.py)
# =========================================================================
GEN_JET_PT_MIN = 20.0
GEN_JET_ETA_MAX = 2.4
DR_MATCH_MAX = 0.4


def is_b_hadron(pdgId: int) -> bool:
    aid = abs(pdgId)
    if aid < 100:
        return False
    if aid < 1000:
        return (aid // 100) == 5
    if aid < 10000:
        return (aid // 1000) == 5
    base = aid % 10000
    if 100 <= base < 1000:
        return (base // 100) == 5
    if 1000 <= base < 10000:
        return (base // 1000) == 5
    return False


def is_c_hadron(pdgId: int) -> bool:
    if is_b_hadron(pdgId):
        return False
    aid = abs(pdgId)
    if aid < 100:
        return False
    if aid < 1000:
        return (aid // 100) == 4
    if aid < 10000:
        return (aid // 1000) == 4
    base = aid % 10000
    if 100 <= base < 1000:
        return (base // 100) == 4
    if 1000 <= base < 10000:
        return (base // 1000) == 4
    return False


def delta_r2(eta1, phi1, eta2, phi2):
    deta = eta1 - eta2
    dphi = phi1 - phi2
    if dphi > math.pi:
        dphi -= 2.0 * math.pi
    elif dphi < -math.pi:
        dphi += 2.0 * math.pi
    return deta * deta + dphi * dphi


def has_top_ancestor(tree, idx, nGP, max_depth=30):
    cur = idx
    for _ in range(max_depth):
        mother = tree.GenPart_genPartIdxMother[cur]
        if mother < 0 or mother >= nGP:
            return False
        if abs(tree.GenPart_pdgId[mother]) == 6:
            return True
        cur = mother
    return False


# =========================================================================
# Safe array length: use the actual branch array, NOT the counter variable
# =========================================================================
def safe_array_len(tree, array_branch_name, counter_branch_name):
    """Return (actual_len, counter_val) for diagnostics.

    Reads the array branch via GetLeaf to find the true entry count,
    and also reads the scalar counter for comparison.
    """
    # Method 1: Try reading the array branch directly
    actual_len = 0
    try:
        arr = getattr(tree, array_branch_name, None)
        if arr is not None:
            # For TTreeFormula-wrapped or direct access
            actual_len = len(arr) if hasattr(arr, '__len__') else 0
    except Exception:
        pass

    # If that didn't work, try via TBranch
    if actual_len == 0:
        br = tree.GetBranch(array_branch_name)
        if br:
            leaf = br.GetLeaf(array_branch_name)
            if leaf:
                actual_len = leaf.GetLen()

    # Read the scalar counter
    counter_val = -1
    try:
        counter_val = int(getattr(tree, counter_branch_name, -1))
    except Exception:
        pass

    return actual_len, counter_val


# =========================================================================
# Main categorization (with verbose debug)
# =========================================================================
def categorize_event(tree, ievt, verbose=True):
    """Run categorization on a single event. Returns category string."""

    # --- Get array sizes (robust) ---
    nGP_actual, nGP_counter = safe_array_len(tree, "GenPart_pdgId", "nGenPart")
    nGJ_actual, nGJ_counter = safe_array_len(tree, "GenJet_pt", "nGenJet")

    # Use actual length (fall back to counter if needed)
    nGP = nGP_actual if nGP_actual > 0 else max(nGP_counter, 0)
    nGJ = nGJ_actual if nGJ_actual > 0 else max(nGJ_counter, 0)

    # Read genTtbarId if available
    genTtbarId = -1
    try:
        genTtbarId = int(tree.genTtbarId)
    except Exception:
        pass

    if verbose:
        mismatch_flag = ""
        if nGP_actual != nGP_counter:
            mismatch_flag += f" *** nGenPart MISMATCH: array={nGP_actual} vs counter={nGP_counter} ***"
        if nGJ_actual != nGJ_counter:
            mismatch_flag += f" *** nGenJet MISMATCH: array={nGJ_actual} vs counter={nGJ_counter} ***"

        print(f"\n{'='*70}")
        print(f"Event {ievt}: nGenPart(array)={nGP_actual}, nGenPart(counter)={nGP_counter}, "
              f"nGenJet(array)={nGJ_actual}, nGenJet(counter)={nGJ_counter}, "
              f"genTtbarId={genTtbarId} (mod100={genTtbarId % 100 if genTtbarId >= 0 else -1})")
        if mismatch_flag:
            print(f"  {mismatch_flag}")

    if nGP == 0:
        if verbose:
            print(f"  -> No GenPart. Category: ttCat_noTTJets")
        return "ttCat_noTTJets", 0, 0, 0

    # Check for tt pair
    found_t = found_tbar = False
    for i in range(nGP):
        pid = tree.GenPart_pdgId[i]
        if pid == 6:
            found_t = True
        elif pid == -6:
            found_tbar = True

    if not (found_t and found_tbar):
        if verbose:
            print(f"  -> No ttbar pair (found_t={found_t}, found_tbar={found_tbar}). Category: ttCat_noTTJets")
        return "ttCat_noTTJets", -1, -1, -1

    # Collect additional B hadrons (non-top-ancestor, last-copy)
    add_bh = []
    all_bh_count = 0
    top_bh_count = 0
    for i in range(nGP):
        pdgId = tree.GenPart_pdgId[i]
        if not is_b_hadron(pdgId):
            continue
        status_flags = tree.GenPart_statusFlags[i]
        if not ((status_flags >> 13) & 1):  # isLastCopy
            continue
        all_bh_count += 1
        if has_top_ancestor(tree, i, nGP):
            top_bh_count += 1
            continue
        add_bh.append((i, tree.GenPart_eta[i], tree.GenPart_phi[i], pdgId))

    if verbose:
        print(f"  B hadrons: total_lastCopy={all_bh_count}, from_top={top_bh_count}, additional={len(add_bh)}")
        for idx, (gp_idx, eta, phi, pdg) in enumerate(add_bh):
            print(f"    BH[{idx}]: GenPart[{gp_idx}] pdgId={pdg} eta={eta:.3f} phi={phi:.3f}")

    # GenJets: b-flavored in acceptance
    bjet_indices = []
    all_genjets = 0
    for j in range(nGJ):
        all_genjets += 1
        if tree.GenJet_hadronFlavour[j] != 5:
            continue
        if tree.GenJet_pt[j] < GEN_JET_PT_MIN:
            continue
        if abs(tree.GenJet_eta[j]) > GEN_JET_ETA_MAX:
            continue
        bjet_indices.append(j)

    if verbose:
        print(f"  GenJets: total={all_genjets}, b-flavored in acceptance={len(bjet_indices)}")
        for j in bjet_indices:
            print(f"    GenJet[{j}]: pT={tree.GenJet_pt[j]:.1f} eta={tree.GenJet_eta[j]:.3f} "
                  f"phi={tree.GenJet_phi[j]:.3f} hadFlav={tree.GenJet_hadronFlavour[j]}")

    # DR matching
    dr2_cut = DR_MATCH_MAX * DR_MATCH_MAX
    matched_jets = set()
    for bh_idx, bh_eta, bh_phi, bh_pdg in add_bh:
        best_dr2 = dr2_cut
        best_j = -1
        for j in bjet_indices:
            dr2 = delta_r2(bh_eta, bh_phi, tree.GenJet_eta[j], tree.GenJet_phi[j])
            if dr2 < best_dr2:
                best_dr2 = dr2
                best_j = j
        if best_j >= 0:
            matched_jets.add(best_j)
            if verbose:
                print(f"    BH(pdg={bh_pdg}) -> GenJet[{best_j}] dR={math.sqrt(best_dr2):.3f}")
        else:
            if verbose:
                print(f"    BH(pdg={bh_pdg}) -> NO MATCH (closest dR > {DR_MATCH_MAX})")

    n_bjets = len(matched_jets)
    n_bhadrons = len(add_bh)

    # Count additional c-jets
    add_ch = []
    for i in range(nGP):
        if not is_c_hadron(tree.GenPart_pdgId[i]):
            continue
        if not ((tree.GenPart_statusFlags[i] >> 13) & 1):
            continue
        if has_top_ancestor(tree, i, nGP):
            continue
        add_ch.append((tree.GenPart_eta[i], tree.GenPart_phi[i]))

    cjet_indices = []
    for j in range(nGJ):
        if tree.GenJet_hadronFlavour[j] != 4:
            continue
        if tree.GenJet_pt[j] < GEN_JET_PT_MIN:
            continue
        if abs(tree.GenJet_eta[j]) > GEN_JET_ETA_MAX:
            continue
        cjet_indices.append(j)

    c_matched = set()
    for ch_eta, ch_phi in add_ch:
        best_dr2 = dr2_cut
        best_j = -1
        for j in cjet_indices:
            dr2 = delta_r2(ch_eta, ch_phi, tree.GenJet_eta[j], tree.GenJet_phi[j])
            if dr2 < best_dr2:
                best_dr2 = dr2
                best_j = j
        if best_j >= 0:
            c_matched.add(best_j)
    n_cjets = len(c_matched)

    # Decision tree
    if n_bjets >= 4:
        cat = "ttCat_4b"
    elif n_bjets == 3:
        cat = "ttCat_bbb"
    elif n_bjets == 1 and n_bhadrons >= 2:
        cat = "ttCat_2b"
    elif n_bjets >= 2:
        cat = "ttCat_bb"
    elif n_bjets == 1:
        cat = "ttCat_b"
    elif n_cjets > 0:
        cat = "ttCat_cc"
    else:
        cat = "ttCat_LF"

    if verbose:
        print(f"  -> n_add_bjets={n_bjets}, n_add_bhadrons={n_bhadrons}, n_add_cjets={n_cjets}")
        print(f"  -> CATEGORY: {cat}")

        # Compare with ntuple ttCat_* branches if they exist
        try:
            ntuple_cat = "???"
            for c in ["ttCat_LF", "ttCat_cc", "ttCat_b", "ttCat_2b",
                       "ttCat_bb", "ttCat_bbb", "ttCat_4b", "ttCat_noTTJets"]:
                val = getattr(tree, c, None)
                if val is not None and bool(val):
                    ntuple_cat = c
            ntuple_nb = getattr(tree, "nAdditionalBJets", None)
            match_str = "MATCH" if ntuple_cat == cat else "*** MISMATCH ***"
            print(f"  -> Ntuple branch: {ntuple_cat} (nAdditionalBJets={ntuple_nb}) {match_str}")
        except Exception:
            pass

        # Compare with genTtbarId-based fallback
        if genTtbarId > 0:
            cat_id = genTtbarId % 100
            if 41 <= cat_id <= 49:
                fb = "tt+cc"
            elif cat_id == 51:
                fb = "tt+b"
            elif cat_id == 52:
                fb = "tt+2b"
            elif 53 <= cat_id <= 56:
                fb = "tt+bb"
            elif cat_id == 0:
                fb = "tt+LF"
            else:
                fb = f"unknown({cat_id})"
            print(f"  -> genTtbarId fallback: {fb} (genTtbarId={genTtbarId}, mod100={cat_id})")

    return cat, n_bjets, n_bhadrons, n_cjets


# =========================================================================
# Main
# =========================================================================
def main():
    parser = argparse.ArgumentParser(description="Standalone tt+jets categorization tester")
    parser.add_argument("input_file", help="ROOT file path (local, xrootd, or pnfs)")
    parser.add_argument("--max-events", "-N", type=int, default=20,
                        help="Max events to process (default: 20)")
    parser.add_argument("--tree", type=str, default="Events",
                        help="TTree name (default: Events)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Only print summary, not per-event details")
    args = parser.parse_args()

    print(f"Opening: {args.input_file}")
    f = ROOT.TFile.Open(args.input_file)
    if not f or f.IsZombie():
        print("ERROR: Cannot open file")
        sys.exit(1)

    tree = f.Get(args.tree)
    if not tree:
        print(f"ERROR: TTree '{args.tree}' not found. Available keys:")
        for key in f.GetListOfKeys():
            print(f"  {key.GetName()} ({key.GetClassName()})")
        sys.exit(1)

    n_entries = tree.GetEntries()
    n_process = min(n_entries, args.max_events) if args.max_events else n_entries
    print(f"TTree '{args.tree}': {n_entries} entries, processing {n_process}")

    # Check available branches
    branch_names = {b.GetName() for b in tree.GetListOfBranches()}
    has_genpart = "GenPart_pdgId" in branch_names
    has_genjet = "GenJet_pt" in branch_names
    has_ttcat = "ttCat_LF" in branch_names
    has_genttbarid = "genTtbarId" in branch_names

    print(f"\nBranch availability:")
    print(f"  GenPart_pdgId: {'YES' if has_genpart else 'NO'}")
    print(f"  GenJet_pt:     {'YES' if has_genjet else 'NO'}")
    print(f"  nGenPart:      {'YES' if 'nGenPart' in branch_names else 'NO'}")
    print(f"  nGenJet:       {'YES' if 'nGenJet' in branch_names else 'NO'}")
    print(f"  genTtbarId:    {'YES' if has_genttbarid else 'NO'}")
    print(f"  ttCat_LF:      {'YES' if has_ttcat else 'NO'} (categorizer output)")

    if not has_genpart:
        print("\nERROR: No GenPart branches - cannot categorize.")
        sys.exit(1)

    # Activate only needed branches for speed
    tree.SetBranchStatus("*", 0)
    for pat in ["GenPart_*", "nGenPart", "GenJet_*", "nGenJet",
                "genTtbarId", "ttCat_*", "nAdditional*"]:
        tree.SetBranchStatus(pat, 1)

    # Process events
    cat_counter = Counter()
    ntuple_counter = Counter()
    mismatch_count = 0
    counter_mismatch_gp = 0
    counter_mismatch_gj = 0

    verbose = not args.quiet

    for ievt in range(n_process):
        tree.GetEntry(ievt)
        cat, nb, nbh, nc = categorize_event(tree, ievt, verbose=verbose)
        cat_counter[cat] += 1

        # Check counter mismatch
        nGP_actual, nGP_counter = safe_array_len(tree, "GenPart_pdgId", "nGenPart")
        nGJ_actual, nGJ_counter = safe_array_len(tree, "GenJet_pt", "nGenJet")
        if nGP_actual != nGP_counter:
            counter_mismatch_gp += 1
        if nGJ_actual != nGJ_counter:
            counter_mismatch_gj += 1

        # Check ntuple mismatch
        if has_ttcat:
            ntuple_cat = "???"
            try:
                for c in ["ttCat_LF", "ttCat_cc", "ttCat_b", "ttCat_2b",
                           "ttCat_bb", "ttCat_bbb", "ttCat_4b", "ttCat_noTTJets"]:
                    if bool(getattr(tree, c, 0)):
                        ntuple_cat = c
            except Exception:
                pass
            ntuple_counter[ntuple_cat] += 1
            if ntuple_cat != cat:
                mismatch_count += 1

    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY ({n_process} events)")
    print(f"{'='*70}")

    print(f"\nRecalculated categorization:")
    for cat in ["ttCat_LF", "ttCat_cc", "ttCat_b", "ttCat_2b",
                "ttCat_bb", "ttCat_bbb", "ttCat_4b", "ttCat_noTTJets"]:
        print(f"  {cat:20s}: {cat_counter.get(cat, 0):5d}")

    if has_ttcat:
        print(f"\nNtuple ttCat_* branches (stored in file):")
        for cat in ["ttCat_LF", "ttCat_cc", "ttCat_b", "ttCat_2b",
                    "ttCat_bb", "ttCat_bbb", "ttCat_4b", "ttCat_noTTJets"]:
            print(f"  {cat:20s}: {ntuple_counter.get(cat, 0):5d}")

        print(f"\nMismatch: {mismatch_count}/{n_process} events differ between recalc and ntuple")

    print(f"\nCounter branch diagnostics:")
    print(f"  nGenPart counter != array size: {counter_mismatch_gp}/{n_process} events")
    print(f"  nGenJet  counter != array size: {counter_mismatch_gj}/{n_process} events")

    if counter_mismatch_gj > 0:
        print(f"\n  *** nGenJet counter is BROKEN in {counter_mismatch_gj} events! ***")
        print(f"  *** This is the root cause: categorizer loops used range(nGenJet)=range(0) ***")
        print(f"  *** so NO GenJets were found -> everything classified as tt+LF ***")

    if counter_mismatch_gp > 0:
        print(f"\n  *** nGenPart counter is BROKEN in {counter_mismatch_gp} events! ***")
        print(f"  *** range(nGenPart) iterates over garbage/wrong range ***")

    f.Close()
    print("\nDone.")


if __name__ == "__main__":
    main()
