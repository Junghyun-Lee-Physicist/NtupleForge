#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_slim_branchlists.py -- write DRAFT slim versions of the four v15 hadronic
branch lists and prove they lose nothing the analyzer reads.

A slim draft is the production list, unchanged, followed by explicit `drop`
lines. The production design stays as it is (collection wildcards keep new and
renamed branches; branches/branch_hadronic_*_v15_*.txt header, DESIGN 1); the
drafts only remove named branches that this analysis has no use for.

    slimA  no plausible use here: HF-only jet shapes, links to collections the
           list does not store (SV, FsrPhoton, Photon), lepton/tau heads of the
           jet taggers, soft / low-pT / high-pT (TuneP, HEEP) lepton IDs,
           beam-spot and GSF-mode internals, HZZ MVA, PV fit details, OtherPV,
           pileup-truth extras, GenVisTau, GenPart_iso, LHEPart
    slimB  slimA + tagger class heads beyond B / CvB / CvL / QvG, the lepton-MVA
           inputs and ID/energy internals of Muon and Electron (the IDs,
           isolations, promptMVA and scale/smearing inputs stay), two jet
           muon-subtraction angles, HLT_AK8PFJet*
    slimC  slimB + LHEPdfWeight (MC only). Listed to show what the PDF weights
           cost; dropping them means the PDF uncertainty needs another source.

Kept in every draft: all 73 branches the analyzer reads (check_branchlist.py
REQUIRED + HLT_REQUIRED), jet-ID recomputation inputs (docs/08 3.4: energy
fractions, multiplicities, hfHEF, hfEmEF, puIdDisc), JEC/JER inputs (rawFactor,
area, Rho_*, genJetIdx, GenJet_*), all b-jet regressions, the B / CvB / CvL /
QvG tagger outputs, every MET branch and all Flag_* (a MET cut and a 1-lepton
region stay possible), lepton IDs, isolations and SF / scale inputs, GenPart
except iso, LHE_* scalars, LHEScaleWeight, PSWeight, LHEReweightingWeight.

Rules. A drop line is written for a list only if it matches at least one
branch KEPT by the production list in EVERY inventory that list serves
(otherwise ROOT prints a SetBranchStatus error per job, check_branchlist.py
(A)); lines that fail this are reported and left out. Every requirement the
production list satisfies must still be satisfied (check_branchlist.py (B)).
Output is byte-identical on regeneration (no timestamp).

    python3 script/make_slim_branchlists.py            # write drafts + report
    python3 script/make_slim_branchlists.py --check    # report only, write nothing

Writes script/drafts/branch_hadronic_<era>_v15_<tier>_slim{A,B,C}.txt. A draft
becomes real only when copied over a production list by hand. Needs no ROOT
or CMSSW, only python3 >= 3.7 (it imports script/check_branchlist.py). Exit 0
ok, 1 a requirement would be lost or a draft differs under --check. ASCII only.
"""
import argparse
import fnmatch
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "script"))
import check_branchlist as cb   # REQUIRED, HLT_REQUIRED (the analyzer trace)

INV = "script/inventory/"
LISTS = [   # production list, era token, MC?, inventories it serves
    ("branches/branch_hadronic_2024_v15_MC.txt", "2024", True,
     ["inv_Summer24_v15_MC.tsv", "inv_Summer24_v15_MC_TTBB.tsv", "inv_Summer24_v15_MC_TTHH.tsv"]),
    ("branches/branch_hadronic_2024_v15_Data.txt", "2024", False,
     ["inv_2024%s_v15_Data.tsv" % e for e in ("C", "D", "E", "F", "G", "H", "I", "Iv2")]
     + ["inv_2024C_v15_Muon.tsv"]),
    ("branches/branch_hadronic_2018_v15_MC.txt", "2018", True, ["inv_2018UL_v15_MC.tsv"]),
    ("branches/branch_hadronic_2018_v15_Data.txt", "2018", False,
     ["inv_2018%s_v15_Data.tsv" % e for e in ("A", "B", "C", "D")]),
]

# (reason, [patterns]) per tier. Patterns are exact names or '*' wildcards.
SLIM_A = [
    ("HF-only jet shower shapes (non-zero only for |eta| > 3; the jet-ID inputs hfHEF / hfEmEF stay)",
     ["Jet_hfsigmaEtaEta", "Jet_hfsigmaPhiPhi", "Jet_hfcentralEtaStripSize", "Jet_hfadjacentEtaStripsSize"]),
    ("links into collections this list does not store (SV_*, FsrPhoton_*, Photon_*)",
     ["Jet_svIdx1", "Jet_svIdx2", "Jet_nSVs", "Muon_svIdx", "Muon_fsrPhotonIdx",
      "Electron_svIdx", "Electron_fsrPhotonIdx", "Electron_photonIdx"]),
    ("lepton-in-jet and tau-vs-jet heads of the jet taggers",
     ["Jet_btagUParTAK4Ele", "Jet_btagUParTAK4Mu", "Jet_btagUParTAK4TauVJet", "Jet_btagPNetTauVJet"]),
    ("muon beam-spot / impact-point vector internals (dxy, dz, ip3d, sip3d stay)",
     ["Muon_IPx", "Muon_IPy", "Muon_IPz", "Muon_VXBS_Cov00", "Muon_VXBS_Cov03", "Muon_VXBS_Cov33",
      "Muon_bsConstrainedChi2", "Muon_bsConstrainedPt", "Muon_bsConstrainedPtErr", "Muon_dxybs", "Muon_dxybsErr"]),
    ("soft / low-pT muon IDs (B-physics) and TuneP high-pT momentum",
     ["Muon_mvaLowPt", "Muon_softId", "Muon_softMva", "Muon_softMvaId", "Muon_softMvaRun3",
      "Muon_tuneP_charge", "Muon_tuneP_pterr", "Muon_tunepRelPt"]),
    ("electron impact-point vector, preshower, GSF-mode track, HEEP and HZZ-specific IDs",
     ["Electron_IPx", "Electron_IPy", "Electron_IPz", "Electron_PreshowerEnergy",
      "Electron_gsfTrketaMode", "Electron_gsfTrkpMode", "Electron_gsfTrkpModeErr", "Electron_gsfTrkphiMode",
      "Electron_cutBased_HEEP", "Electron_vidNestedWPBitmapHEEP", "Electron_dr03TkSumPtHEEP",
      "Electron_mvaHZZIso", "Electron_mvaIso_WPHZZ"]),
    ("primary-vertex fit details (npvs, npvsGood, z stay) and the other PVs",
     ["PV_chi2", "PV_ndof", "PV_score", "PV_sumpt2", "PV_sumpx", "PV_sumpy", "PV_x", "PV_y",
      "nOtherPV", "OtherPV_*"]),
    ("pileup-truth extras (nTrueInt, nPU stay)",
     ["Pileup_gpudensity", "Pileup_pudensity", "Pileup_sumEOOT", "Pileup_sumLOOT", "Pileup_pthatmax"]),
    ("gen visible taus, GenPart isolation, LHE-level particles (the analyzer uses GenPart / GenJet; LHE_* scalars stay)",
     ["nGenVisTau", "GenVisTau_*", "GenPart_iso", "nLHEPart", "LHEPart_*"]),
]
SLIM_B = [
    ("tagger class heads beyond B / CvB / CvL / QvG",
     ["Jet_btagUParTAK4probb", "Jet_btagUParTAK4probbb", "Jet_btagUParTAK4SvCB", "Jet_btagUParTAK4SvUDG",
      "Jet_btagUParTAK4UDG", "Jet_btagUParTAK4CvNotB", "Jet_btagPNetCvNotB"]),
    ("jet muon-subtraction angles (muonSubtrFactor stays for Type-1 MET)",
     ["Jet_muonSubtrDeltaEta", "Jet_muonSubtrDeltaPhi"]),
    ("muon lepton-MVA inputs (promptMVA stays), PNet lepton scores, rarely used ID bits and errors",
     ["Muon_jetDF", "Muon_jetNDauCharged", "Muon_jetPtRelv2", "Muon_jetRelIso",
      "Muon_pnScore_heavy", "Muon_pnScore_light", "Muon_pnScore_prompt", "Muon_pnScore_tau",
      "Muon_multiIsoId", "Muon_puppiIsoId", "Muon_inTimeMuon", "Muon_triggerIdLoose", "Muon_segmentComp",
      "Muon_isStandalone", "Muon_bestTrackType", "Muon_highPurity", "Muon_ipLengthSig", "Muon_dxyErr", "Muon_dzErr"]),
    ("electron ID / isolation components (cutBased, vidNestedWPBitmap, MVA WPs stay), energy internals, lepton-MVA inputs",
     ["Electron_dr03EcalRecHitSumEt", "Electron_dr03HcalDepth1TowerSumEt", "Electron_dr03TkSumPt",
      "Electron_eInvMinusPInv", "Electron_fbrem", "Electron_hoe", "Electron_sieie",
      "Electron_ecalEnergy", "Electron_ecalEnergyError", "Electron_energyErr", "Electron_rawEnergy",
      "Electron_isEcalDriven", "Electron_isPFcand", "Electron_jetDF", "Electron_jetNDauCharged",
      "Electron_jetPtRelv2", "Electron_jetRelIso", "Electron_ipLengthSig", "Electron_dxyErr", "Electron_dzErr",
      "Electron_seediEtaOriX", "Electron_seediPhiOriY"]),
    ("boosted-jet triggers (no FatJet collection is stored)", ["HLT_AK8PFJet*"]),
]
SLIM_C = [
    ("PDF weights: ~100 floats per event, not read by the analyzer; the PDF uncertainty then needs another source",
     ["LHEPdfWeight", "nLHEPdfWeight"]),
]
TIERS = [("slimA", SLIM_A), ("slimB", SLIM_A + SLIM_B), ("slimC", SLIM_A + SLIM_B + SLIM_C)]


def inventory(path):
    """{branch: lenVar} of the Events tree."""
    out = {}
    with open(os.path.join(REPO, INV, path)) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            t = line.rstrip("\n").split("\t")
            if t[0] == "Events":
                out[t[1]] = t[3] if len(t) > 3 else ""
    return out


def rules_of_text(text):
    rules = []
    for line in text.splitlines():
        line = re.sub(r"#.*", "", line).strip()
        if line:
            op, pat = line.split()
            rules.append((op, pat))
    return rules


def kept(inv, rules):
    """NanoAODTools semantics, plus ROOT activating the count branch of every
    active array branch (reproduces the 09-23 local-check counts 703/638/717)."""
    st = dict((n, True) for n in inv)
    for op, pat in rules:
        for n in fnmatch.filter(list(inv), pat):
            st[n] = (op == "keep")
    for n, cnt in inv.items():
        if st[n] and cnt and cnt in st:
            st[cnt] = True
    return set(n for n in inv if st[n])


def requirements_lost(prod, slim, mc, era):
    lost = []
    for names, flags in cb.REQUIRED:
        if "mc" in flags and not mc:
            continue
        if any(n in prod for n in names) and not any(n in slim for n in names):
            lost.append("|".join(names))
    for h in cb.HLT_REQUIRED.get(era, []):
        if h in prod and h not in slim:
            lost.append(h)
    return lost


def draft_text(prod_text, tier, groups, used):
    out = [prod_text.rstrip("\n"), "",
           "# " + "=" * 77,
           "#  %s DRAFT -- generated by script/make_slim_branchlists.py from the list above." % tier,
           "#  Everything above this block is the production list, unchanged. The lines",
           "#  below only DROP named branches; review them, then copy this file over the",
           "#  production list by hand if the decision is taken. Re-check after any edit:",
           "#      python3 script/make_slim_branchlists.py --check",
           "# " + "=" * 77]
    for reason, pats in groups:
        pats = [p for p in pats if p in used]
        if not pats:
            continue
        out.append("")
        out.append("# %s" % reason)
        for p in pats:
            out.append("drop %s" % p)
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report only; fail if a draft on disk differs")
    args = ap.parse_args()
    bad = 0
    for lpath, era, mc, invs in LISTS:
        prod_text = open(os.path.join(REPO, lpath)).read()
        prod_rules = rules_of_text(prod_text)
        inv_sets = [(i, inventory(i)) for i in invs]
        prod_kept = dict((i, kept(inv, prod_rules)) for i, inv in inv_sets)
        print("== %s (%s, %s; %d inventories)" % (lpath, era, "MC" if mc else "Data", len(invs)))
        for tier, groups in TIERS:
            if tier == "slimC" and not mc:
                continue
            used, skipped = [], []
            for _, pats in groups:
                for p in pats:
                    miss = [i for i, inv in inv_sets if not fnmatch.filter(sorted(prod_kept[i]), p)]
                    (skipped if miss else used).append((p, miss))
            used_p = set(p for p, _ in used)
            text = draft_text(prod_text, tier, groups, used_p)
            slim_rules = rules_of_text(text)
            counts, lost_all = [], []
            for i, inv in inv_sets:
                s = kept(inv, slim_rules)
                extra = s - prod_kept[i]
                if extra:
                    lost_all.append("%s keeps %d branches the production list drops" % (i, len(extra)))
                lost = requirements_lost(prod_kept[i], s, mc, era)
                if lost:
                    lost_all.append("%s loses %s" % (i, ", ".join(lost)))
                counts.append("%d->%d" % (len(prod_kept[i]), len(s)))
            out = os.path.join(REPO, "script", "drafts", os.path.basename(lpath).replace(".txt", "_%s.txt" % tier))
            state = ""
            if args.check:
                same = os.path.exists(out) and open(out).read() == text
                state = "on disk: same" if same else "on disk: DIFFERS"
                if not same:
                    bad += 1
            else:
                with open(out, "w") as f:
                    f.write(text)
                state = "written %s" % os.path.relpath(out, REPO)
            print("   %-5s drop lines %3d | kept per inventory %s | %s" % (
                tier, len(used_p), " ".join(sorted(set(counts))), state))
            na = [p for p, miss in skipped if len(miss) == len(invs)]
            partial = [(p, miss) for p, miss in skipped if len(miss) < len(invs)]
            if na and tier == "slimA":
                print("         not applicable to this list (no kept branch in any inventory): %s" % " ".join(na))
            for p, miss in partial:
                print("         LEFT OUT, matches in some inventories only (would be a ROOT error in %s): %s"
                      % (",".join(miss), p))
            for l in lost_all:
                print("         FAIL: " + l)
                bad += 1
    print("RESULT: %s" % ("OK" if bad == 0 else "%d problem(s)" % bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
