#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the four compressed hadronic branch lists (2017/2018 x MC/Data, v15).

    python3 script/gen_hadronic_branchlists.py branches/

Kept as a generator, not four hand-maintained files, for the same reason
samples_registry.txt exists: the four differ only in the gen block and two HLT
lines, and hand-editing four near-identical files is how they drift. Edit the
blocks here and regenerate.

The generated files are UNVERIFIED against a real v15 schema by construction --
that verification is script/check_branchlist.py --inventory, and every header
says so.
"""
import os
import sys

HEADER = """# =============================================================================
#  branch_hadronic_{era}_v15_{tier}.txt
#  ttHH -> 4b, fully-hadronic channel -- COMPRESSED output branch selection
#  Target: {era} x NanoAOD **v15**, {tierlong}
# =============================================================================
#  Created 2026-08-17.  STATUS: **UNVERIFIED against a real v15 file.**
#  Do not submit a campaign with this file until you have run:
#
#      python3 script/dump_branch_inventory.py <one real v15 {tierlong} file> \\
#              --label {era}_v15_{tier} -o script/inventory/inv_{era}_v15_{tier}.tsv
#      python3 script/check_branchlist.py branches/branch_hadronic_{era}_v15_{tier}.txt \\
#              --inventory script/inventory/inv_{era}_v15_{tier}.tsv --era {era}{mcflag}
#
#  and fixed every pattern it reports. A `keep` pattern that matches nothing
#  makes ROOT emit a SetBranchStatus error ONCE PER JOB -- it is not silently
#  ignored (docs/02_CHANGELOG.md 2026-07-27, which is why the prescan lists are
#  split per year in the first place).
#
# -----------------------------------------------------------------------------
#  SEMANTICS (NanoAODTools branch selection)
#    - A branch matching NO rule is KEPT. Hence the leading `drop *`.
#    - Later rules override earlier ones.
#    - This file selects the OUTPUT branches only. The PostProcessor is called
#      with branchsel=None on the input side (A4) -- filtering the input
#      produces a zombie file.
#    - `Runs` and `LuminosityBlocks` are copied wholesale and are NOT affected
#      by this file, so genEventSumw / genEventSumw2 / genEventCount survive
#      (verified on a real UL18 file, 2026-07-27). Prescan mode still works.
#
# -----------------------------------------------------------------------------
#  DESIGN
#  Two rules govern every line below.
#
#  1. WILDCARD FOR GENEROSITY, EXPLICIT NAME FOR VERIFICATION.
#     A collection-prefix wildcard (`Muon_*`) is both generous AND immune to
#     the v9->v15 renames, and it can never be "unmatched" as long as the
#     collection exists. The specific branch names the analyzer depends on are
#     asserted in script/check_branchlist.py instead, where a missing one is a
#     loud failure rather than a silent zero. So: wildcards here, assertions
#     there. Do not "tighten" a wildcard into a name list -- that just moves
#     the fragility back into this file.
#
#  2. WHAT IS DROPPED IS DROPPED ON PURPOSE. The bottom of this file lists
#     every collection that is deliberately absent, with the reason. If you
#     need one back, add it there and say why -- do not silently re-add.
#
# -----------------------------------------------------------------------------
#  SCOPE OF THIS FILE (user decision 2026-08-17)
#  Compression is applied to the **v15** production only. The v9 production
#  keeps `branches/branch_keep_all.txt` (`keep *`) so that the existing,
#  already-validated 2017UL/2018UL output stays the comparison baseline.
#  CONSEQUENCE, and it is not a small one: a v9 <-> v15 comparison can only
#  cover the branches this file keeps. Anything dropped here is outside the
#  scope of that comparison -- say so when reporting the result.
#
# -----------------------------------------------------------------------------
#  WHAT THE ANALYZER ACTUALLY READS
#  Traced 2026-08-17 through every `_ev->` dereference in
#  tempTTHH/ttHHanalyzer_unified.{{cc,h}}, src/*.cc, include/*.h:
#  **73 branches**, of which exactly ONE is MET-related (`MET_pt`, used for the
#  1-muon control region and copied into the output tree) and ZERO are
#  FatJet_*. Everything beyond those 73 in this file is there for the
#  validation headroom requested on 2026-08-17, not because the current code
#  needs it.
#
#  Five of the 73 are load-bearing in a non-obvious way: eventBuffer sizes a
#  whole collection from ONE branch, and dropping it yields an EMPTY collection
#  with no error --
#      Jet_area, Muon_charge, Electron_charge, GenJet_eta, GenPart_eta
#  All five are inside the wildcards below; check_branchlist.py re-checks them.
# =============================================================================

drop *

# -----------------------------------------------------------------------------
# 1. Event identity, vertices, pileup density
# -----------------------------------------------------------------------------
keep run
keep luminosityBlock
keep event
keep PV_*
keep nOtherPV
keep OtherPV_*
# v15/v12 name. In v9 this is the bare `fixedGridRhoFastjetAll` with no prefix
# (rename v9 -> v12). The analyzer reads it for JEC/JER.
keep Rho_*

# -----------------------------------------------------------------------------
# 2. AK4 jets -- the whole collection
#    Includes the b-tag discriminants under whatever names v15 uses
#    (Jet_btagDeepFlavB is what the analyzer reads today; v12+ also ship
#    ParticleNet / UParT taggers). Also picks up Jet_area, which eventBuffer
#    sizes the Jet collection from.
# -----------------------------------------------------------------------------
keep nJet
keep Jet_*

# -----------------------------------------------------------------------------
# 3. MET -- generous, for the MET+muon validation region
#    The analyzer today reads only `MET_pt`. Everything else here is headroom:
#    a 1-muon + MET control region, MET-based QCD sidebands, and the
#    unclustered/JES/JER MET systematics all need more than pt.
#    v15 renames: MET_* -> PFMET_*, RawMET_* -> RawPFMET_*, TkMET_* -> TrkMET_*.
# -----------------------------------------------------------------------------
keep PFMET_*
keep PuppiMET_*
keep RawPFMET_*
keep RawPuppiMET_*

# -----------------------------------------------------------------------------
# 4. Muons and electrons -- whole collections
#    nMuon/nElectron are small, so keeping the full collections costs little
#    and buys every ID/isolation working point a validation region might want.
#    Also picks up Muon_charge / Electron_charge, the collection-sizing
#    branches.
# -----------------------------------------------------------------------------
keep nMuon
keep Muon_*
keep nElectron
keep Electron_*
"""

MC_BLOCK = """
# -----------------------------------------------------------------------------
# 5. Gen-level (MC only)
#    GenJet_* and GenPart_* are required by the in-analyzer ttbar
#    categorization; GenJet_eta and GenPart_eta are the collection-sizing
#    branches. genTtbarId is the CMS GenTtbarCategorizer output -- if it is
#    absent, eventBuffer defaults it to 0 and EVERY ttbar MC event is binned as
#    tt+LF, with no error. Verify it exists in v15 before trusting any yield.
# -----------------------------------------------------------------------------
keep genWeight
keep genTtbarId
keep Generator_*
keep Pileup_*
keep nGenJet
keep GenJet_*
keep nGenPart
keep GenPart_*
keep GenMET_*
keep nGenVisTau
keep GenVisTau_*

# Theory weights. LHEScaleWeight (~9) and PSWeight (~4) are cheap.
# LHEPdfWeight is ~100 floats/event and is the single most expensive thing in
# this file -- the analyzer does not use it today. If output size becomes a
# problem, this is the first line to delete.
keep LHE_*
keep nLHEPart
keep LHEPart_*
keep LHEScaleWeight
keep nLHEScaleWeight
keep LHEPdfWeight
keep nLHEPdfWeight
keep LHEReweightingWeight
keep nLHEReweightingWeight
keep PSWeight
keep nPSWeight
keep LHEWeight_originalXWGTUP
keep btagWeight_*

# L1 prefiring. Applies to 2016/2017 only. 2018 NanoAODv9 has NO such branch,
# and the analyzer's era config disables it for 2018 -- an ungated multiply
# would zero every 2018 MC weight. VERIFY whether v15 ships it for this era;
# if not, DELETE this line (an unmatched keep = one ROOT error per job).
keep L1PreFiringWeight_*
"""

FILTER_BLOCK = """
# -----------------------------------------------------------------------------
# 6. MET filters -- all of them
#    The analyzer reads 9 by name. Keeping the whole family costs 28 booleans
#    and removes any per-era spelling risk (Data additionally carries a
#    parallel Flag_*_pRECO namespace).
# -----------------------------------------------------------------------------
keep Flag_*
"""

HLT_HEAD = """
# -----------------------------------------------------------------------------
# 7. Triggers -- {era}
#    Wildcards, not names: the analyzer's required paths are asserted in
#    script/check_branchlist.py --era {era}, where a missing one FAILS instead
#    of silently evaluating false.
#
#    !! HARD GATE FOR v15 !! The v12 -> v15 change set REMOVES deprecated HLT
#    and L1 branches. If the b-tag quad/six-jet paths this analysis triggers on
#    are among them, the analysis cannot run on v15 for this era at all -- no
#    branch list fixes that. Confirm their presence with
#    check_branchlist.py --era {era} section (C) BEFORE anything else.
# -----------------------------------------------------------------------------
"""

HLT_COMMON = """keep HLT_PFHT*
keep HLT_PFJet*
keep HLT_AK8PFJet*
keep HLT_QuadPFJet*
keep HLT_IsoMu*
keep HLT_Mu*
keep HLT_Ele*
keep HLT_PFMET*
"""

HLT_2017 = """# 2017 Era-B only: the calo-jet spellings (note the upstream CMS typo
# "TripeCSV"). These live under the HLT_HT* prefix, not HLT_PFHT*.
#   HLT_HT300PT30_QuadJet_75_60_45_40_TripeCSV_p07
# VERIFY: prime suspect for removal in v15's deprecated-trigger cleanup.
keep HLT_HT*
"""

HLT_2018 = """# 2018 has no HLT_HT* calo-jet b-tag paths (the CSV-era menu is 2017-only),
# so no HLT_HT* line here -- adding one would be an unmatched pattern.
"""

FOOTER = """
# =============================================================================
#  DELIBERATELY NOT KEPT -- each line is a decision, not an oversight
# =============================================================================
#  L1_*                      442 branches. Never read by the analyzer. The
#                            single largest branch-count saving in this file.
#  HLT_* (everything else)   569 HLT branches exist; the 8 wildcards above cover
#                            the ~11 the analyzer names plus the muon/MET
#                            reference menu. The rest are other analyses'.
#  FatJet_*, SubJet_*        ZERO reads in the current analyzer -- the only
#                            trace is a dead `objectBoostedJet*` declaration.
#                            The legacy 2017 list kept ~25 FatJet_* branches
#                            plus two wildcards; all of it was dead weight.
#                            RE-ADD if and when a boosted-Higgs category is
#                            actually implemented.
#  GenJetAK8_*, SubGenJetAK8_*   ditto (boosted gen).
#  Photon_*, Tau_*, boostedTau_*, LowPtElectron_*, FsrPhoton_*   zero reads.
#  IsoTrack_*, SoftActivityJet_*, SV_*, TrigObj_*   zero reads.
#  CorrT1METJet_*            only needed to re-derive Type-1 MET from scratch.
#                            Add back if MET is ever recomputed downstream.
#  CaloMET_*, ChsMET_*, TrkMET_*, DeepMET*   zero reads. PF and PUPPI MET (kept
#                            above) cover the validation region; add a specific
#                            one back if a study needs it.
#  PPSLocalTrack_*, Proton_*, HTXS_*, GenDressedLepton_*, GenIsolatedPhoton_*
#                            zero reads.
#  ttCat_* / ttCatXval_*     removed from the pipeline at STEP17 -- the
#                            full-Nano ntuple has no such branches and the
#                            analyzer no longer reads them. Categorization now
#                            runs in-analyzer from genTtbarId + GenPart_*.
#
#  Expanded_genTtbarId       NOT in this list on purpose. Today it is not an
#                            ntuple branch at all -- the analyzer resolves it at
#                            run time from the per-sample patch files. WHEN the
#                            deferred modules/expandedTtbarIdInjector.py lands,
#                            add:   keep Expanded_genTtbarId
#                                   keep Expanded_isPatched
#                            to this file in the SAME change, or the injected
#                            branch is written and then dropped -- silently.
# =============================================================================
"""


def build(era, tier):
    mc = (tier == "MC")
    txt = HEADER.format(era=era, tier=tier,
                        tierlong=("MC (NANOAODSIM)" if mc else "Data (NANOAOD)"),
                        mcflag=(" --mc" if mc else ""))
    if mc:
        txt += MC_BLOCK
    else:
        txt += ("\n# -----------------------------------------------------------------------------\n"
                "# 5. Gen-level -- NOT APPLICABLE (Data)\n"
                "#    genWeight / genTtbarId / GenJet_* / GenPart_* / LHE* / PSWeight /\n"
                "#    Pileup_* / L1PreFiringWeight_* do not exist in Data. Keeping any of\n"
                "#    them here would be an unmatched pattern = one ROOT error per job.\n"
                "#    This is the only difference between this file and the MC one.\n"
                "# -----------------------------------------------------------------------------\n")
    txt += FILTER_BLOCK
    txt += HLT_HEAD.format(era=era)
    txt += HLT_COMMON
    txt += (HLT_2017 if era == "2017" else HLT_2018)
    txt += FOOTER
    return txt


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(outdir, exist_ok=True)
    for era in ("2017", "2018"):
        for tier in ("MC", "Data"):
            p = os.path.join(outdir, "branch_hadronic_%s_v15_%s.txt" % (era, tier))
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(build(era, tier))
            print("wrote", p)


if __name__ == "__main__":
    main()
