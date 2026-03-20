"""
NtupleForge: tt+jets Event Categorizer Module
=============================================
Categorizes tt+jets events into sub-categories based on the flavour of
additional jets NOT originating from top-quark decays, following the
methodology of:
  - CMS AN-2022/122 (ttHH -> 4b, Sections 3.1-3.4)
  - CMS AN-19-094   (ttH  -> bb, Section 6.1)
Both analyses use the CMS GenHFHadronMatcher tool with generator-level
jets satisfying pT > 20 GeV and |eta| < 2.4.

Standard 5 categories (shared with ttH):
  tt+LF  : no additional heavy-flavour jets
  tt+cc  : additional charm jet(s), no additional b-jets
  tt+b   : 1 additional b-jet from a single B hadron
  tt+2b  : 1 additional b-jet from >= 2 overlapping B hadrons (collinear g->bb)
  tt+bb  : exactly 2 additional b-jets
Extended categories (ttHH-specific, AN-2022/122 Section 3.2):
  tt+bbb : exactly 3 additional b-jets
  tt+4b  : >= 4 additional b-jets

Algorithm (Section 21.5 of the categorization document):
  The classification is fundamentally a generator-level process label,
  NOT a reco-level b-tag count.

  Primary path (GenPart available):
    1) Identify top decay products via GenPart mother chain
    2) Collect additional (non-top-ancestor) last-copy B hadrons
    3) Match them to GenJets (hadronFlavour==5, pT>20, |eta|<2.4)
    4) Apply decision tree:
       extra_b_jets >= 4                                     -> tt+4b
       extra_b_jets == 3                                     -> tt+bbb
       extra_b_jets == 1 AND jet has >=2 B hadrons           -> tt+2b
       extra_b_jets >= 2                                     -> tt+bb
       extra_b_jets == 1 (single B hadron)                   -> tt+b
       extra_c_jets >= 1 (no extra b)                        -> tt+cc
       else                                                  -> tt+LF

  Fallback path (GenPart absent):
    Uses genTtbarId from NanoAOD (CMS GenTtbarCategorizer output).
    Can only resolve up to tt+bb; cannot distinguish tt+bbb/tt+4b.

Output branches:
  ttCat_LF, ttCat_cc, ttCat_b, ttCat_2b, ttCat_bb,
  ttCat_bbb, ttCat_4b, ttCat_noTTJets       (all Bool)
  nAdditionalBJets    (Int, -1 for non-tt)
  nAdditionalBHadrons (Int, -1 for non-tt)
  nAdditionalCJets    (Int, -1 for non-tt)

Author : Junghyun Lee (NtupleForge / CMS ttHH)
"""
from __future__ import annotations

import math
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module


class TTbarJetCategorizer(Module):
    """Classify tt+jets events by additional-jet heavy-flavour content."""

    # ---------- physics constants (matching GenHFHadronMatcher) ----------
    GEN_JET_PT_MIN: float = 20.0
    GEN_JET_ETA_MAX: float = 2.4
    DR_MATCH_MAX: float = 0.4

    # ordered list - exactly one will be True per event
    CATEGORIES: tuple[str, ...] = (
        "ttCat_LF",
        "ttCat_cc",
        "ttCat_b",
        "ttCat_2b",
        "ttCat_bb",
        "ttCat_bbb",
        "ttCat_4b",
        "ttCat_noTTJets",
    )

    # ------------------------------------------------------------------
    # framework hooks
    # ------------------------------------------------------------------
    def beginJob(self) -> None:
        pass

    def endJob(self) -> None:
        pass

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree) -> None:
        self.out = wrappedOutputTree
        for cat in self.CATEGORIES:
            self.out.branch(cat, "O")                  # Bool
        self.out.branch("nAdditionalBJets", "I")       # Int
        self.out.branch("nAdditionalBHadrons", "I")    # Int
        self.out.branch("nAdditionalCJets", "I")       # Int

        # cache which gen-level branches are available
        names = {b.GetName() for b in inputTree.GetListOfBranches()}
        self._has_genTtbarId = "genTtbarId" in names
        self._has_genPart = "nGenPart" in names
        self._has_genJet = "nGenJet" in names

    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree) -> None:
        pass

    # ------------------------------------------------------------------
    # helper: deltaR^2 (skip the sqrt - only needed for threshold)
    # ------------------------------------------------------------------
    @staticmethod
    def _delta_r2(eta1: float, phi1: float, eta2: float, phi2: float) -> float:
        deta = eta1 - eta2
        dphi = phi1 - phi2
        if dphi > math.pi:
            dphi -= 2.0 * math.pi
        elif dphi < -math.pi:
            dphi += 2.0 * math.pi
        return deta * deta + dphi * dphi

    # ------------------------------------------------------------------
    # helper: B-hadron identification from PDG ID
    # ------------------------------------------------------------------
    @staticmethod
    def _is_b_hadron(pdgId: int) -> bool:
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

    # ------------------------------------------------------------------
    # helper: C-hadron identification from PDG ID
    # ------------------------------------------------------------------
    @staticmethod
    def _is_c_hadron(pdgId: int) -> bool:
        aid = abs(pdgId)
        # B hadrons with charm content do not count as C hadrons
        if TTbarJetCategorizer._is_b_hadron(pdgId):
            return False
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

    # ------------------------------------------------------------------
    # helper: check whether a GenPart has a top-quark ancestor
    # ------------------------------------------------------------------
    def _has_top_ancestor(self, event, idx: int, max_depth: int = 30) -> bool:
        cur = idx
        for _ in range(max_depth):
            mother = event.GenPart_genPartIdxMother[cur]
            if mother < 0 or mother >= event.nGenPart:
                return False
            if abs(event.GenPart_pdgId[mother]) == 6:
                return True
            cur = mother
        return False

    # ------------------------------------------------------------------
    # helper: does this event contain a tt-bar pair?
    # ------------------------------------------------------------------
    def _event_has_tt_pair(self, event) -> bool:
        if not self._has_genPart:
            return False
        found_t = found_tbar = False
        for i in range(event.nGenPart):
            pid = event.GenPart_pdgId[i]
            if pid == 6:
                found_t = True
            elif pid == -6:
                found_tbar = True
            if found_t and found_tbar:
                return True
        return False

    # ------------------------------------------------------------------
    # core: count additional b-jets via B-hadron ancestry tracing
    #   Returns (nUniqueJets, nBHadrons) for b/2b distinction
    # ------------------------------------------------------------------
    def _count_additional_bjets_detailed(self, event) -> tuple[int, int]:
        if not (self._has_genPart and self._has_genJet):
            return (0, 0)

        # Step 1: collect additional (non-top-ancestor) last-copy B hadrons
        add_bh: list[tuple[float, float]] = []
        for i in range(event.nGenPart):
            if not self._is_b_hadron(event.GenPart_pdgId[i]):
                continue
            if not ((event.GenPart_statusFlags[i] >> 13) & 1):   # isLastCopy
                continue
            if self._has_top_ancestor(event, i):
                continue
            add_bh.append((event.GenPart_eta[i], event.GenPart_phi[i]))

        if not add_bh:
            return (0, 0)

        # Step 2: gen b-jets in acceptance
        bjet_indices: list[int] = []
        for j in range(event.nGenJet):
            if event.GenJet_hadronFlavour[j] != 5:
                continue
            if event.GenJet_pt[j] < self.GEN_JET_PT_MIN:
                continue
            if abs(event.GenJet_eta[j]) > self.GEN_JET_ETA_MAX:
                continue
            bjet_indices.append(j)

        if not bjet_indices:
            return (0, len(add_bh))

        # Step 3 & 4: DR matching - each B hadron to closest GenJet
        dr2_cut = self.DR_MATCH_MAX * self.DR_MATCH_MAX
        matched: set[int] = set()
        for bh_eta, bh_phi in add_bh:
            best_dr2 = dr2_cut
            best_j = -1
            for j in bjet_indices:
                dr2 = self._delta_r2(
                    bh_eta, bh_phi,
                    event.GenJet_eta[j], event.GenJet_phi[j],
                )
                if dr2 < best_dr2:
                    best_dr2 = dr2
                    best_j = j
            if best_j >= 0:
                matched.add(best_j)

        return (len(matched), len(add_bh))

    # ------------------------------------------------------------------
    # core: count additional c-jets (no overlap with b-jets)
    # ------------------------------------------------------------------
    def _count_additional_cjets(self, event) -> int:
        if not (self._has_genPart and self._has_genJet):
            return 0

        add_ch: list[tuple[float, float]] = []
        for i in range(event.nGenPart):
            if not self._is_c_hadron(event.GenPart_pdgId[i]):
                continue
            if not ((event.GenPart_statusFlags[i] >> 13) & 1):
                continue
            if self._has_top_ancestor(event, i):
                continue
            add_ch.append((event.GenPart_eta[i], event.GenPart_phi[i]))

        if not add_ch:
            return 0

        cjet_indices: list[int] = []
        for j in range(event.nGenJet):
            if event.GenJet_hadronFlavour[j] != 4:
                continue
            if event.GenJet_pt[j] < self.GEN_JET_PT_MIN:
                continue
            if abs(event.GenJet_eta[j]) > self.GEN_JET_ETA_MAX:
                continue
            cjet_indices.append(j)

        if not cjet_indices:
            return 0

        dr2_cut = self.DR_MATCH_MAX * self.DR_MATCH_MAX
        matched: set[int] = set()
        for ch_eta, ch_phi in add_ch:
            best_dr2 = dr2_cut
            best_j = -1
            for j in cjet_indices:
                dr2 = self._delta_r2(
                    ch_eta, ch_phi,
                    event.GenJet_eta[j], event.GenJet_phi[j],
                )
                if dr2 < best_dr2:
                    best_dr2 = dr2
                    best_j = j
            if best_j >= 0:
                matched.add(best_j)

        return len(matched)

    # ------------------------------------------------------------------
    # output helper
    # ------------------------------------------------------------------
    def _fill(self, category: str, n_add_b: int, n_add_bh: int, n_add_c: int) -> None:
        """Set exactly one category branch True; fill counting branches."""
        for cat in self.CATEGORIES:
            self.out.fillBranch(cat, (cat == category))
        self.out.fillBranch("nAdditionalBJets", n_add_b)
        self.out.fillBranch("nAdditionalBHadrons", n_add_bh)
        self.out.fillBranch("nAdditionalCJets", n_add_c)

    # ------------------------------------------------------------------
    # genTtbarId-based fallback (when GenPart is absent)
    #   genTtbarId % 100 encoding (CMS GenTtbarCategorizer):
    #     0       : no additional HF (tt+LF) or non-tt
    #     41-49   : additional c-jets (tt+cc)
    #     51      : 1 additional b-jet, 1 B hadron (tt+b)
    #     52      : 1 additional b-jet, >=2 B hadrons merged (tt+2b)
    #     53-56   : >=2 additional b-jets (tt+bb; cannot refine further)
    # ------------------------------------------------------------------
    def _categorize_from_genTtbarId(self, event) -> None:
        cat_id = event.genTtbarId % 100

        if 41 <= cat_id <= 49:
            self._fill("ttCat_cc", 0, 0, -1)
            return
        if cat_id == 51:
            self._fill("ttCat_b", 1, 1, 0)
            return
        if cat_id == 52:
            self._fill("ttCat_2b", 1, 2, 0)
            return
        if 53 <= cat_id <= 56:
            # genTtbarId guarantees >=2 b-jets but cannot resolve 3b/4b
            self._fill("ttCat_bb", 2, -1, 0)
            return
        if cat_id == 0:
            if self._event_has_tt_pair(event):
                self._fill("ttCat_LF", 0, 0, 0)
            else:
                self._fill("ttCat_noTTJets", -1, -1, -1)
            return

        # unexpected value
        self._fill("ttCat_noTTJets", -1, -1, -1)

    # ------------------------------------------------------------------
    # main event loop
    #
    # Primary: full GenPart-based categorization (Section 21 decision tree)
    # Fallback: genTtbarId-based when GenPart is absent
    # ------------------------------------------------------------------
    def analyze(self, event) -> bool:
        # --- guard: data or MC without any generator info ---
        if not self._has_genTtbarId and not self._has_genPart:
            self._fill("ttCat_noTTJets", -1, -1, -1)
            return True

        # --- Primary path: full GenPart-based categorization ---
        if self._has_genPart and self._has_genJet and event.nGenPart > 0:
            # Step 1: check for tt pair
            if not self._event_has_tt_pair(event):
                self._fill("ttCat_noTTJets", -1, -1, -1)
                return True

            # Step 2-4: count additional b-jets and B hadrons
            n_bjets, n_bhadrons = self._count_additional_bjets_detailed(event)

            # Step 5: decision tree (Section 21.5)
            #   extra_b_jets >= 4                                -> tt+4b
            #   extra_b_jets == 3                                -> tt+bbb
            #   extra_b_jets == 1 AND >=2 B hadrons              -> tt+2b
            #   extra_b_jets >= 2                                -> tt+bb
            #   extra_b_jets == 1                                -> tt+b
            #   extra_c_jets >= 1                                -> tt+cc
            #   else                                             -> tt+LF
            if n_bjets >= 4:
                self._fill("ttCat_4b", n_bjets, n_bhadrons, 0)
                return True
            if n_bjets == 3:
                self._fill("ttCat_bbb", n_bjets, n_bhadrons, 0)
                return True
            if n_bjets == 1 and n_bhadrons >= 2:
                n_cjets = self._count_additional_cjets(event)
                self._fill("ttCat_2b", n_bjets, n_bhadrons, n_cjets)
                return True
            if n_bjets >= 2:
                self._fill("ttCat_bb", n_bjets, n_bhadrons, 0)
                return True
            if n_bjets == 1:
                n_cjets = self._count_additional_cjets(event)
                self._fill("ttCat_b", n_bjets, n_bhadrons, n_cjets)
                return True

            # No additional b-jets; check c-jets
            n_cjets = self._count_additional_cjets(event)
            if n_cjets > 0:
                self._fill("ttCat_cc", 0, 0, n_cjets)
                return True

            self._fill("ttCat_LF", 0, 0, 0)
            return True

        # --- Fallback: genTtbarId-based (GenPart absent) ---
        if self._has_genTtbarId:
            self._categorize_from_genTtbarId(event)
            return True

        # No categorization possible
        self._fill("ttCat_noTTJets", -1, -1, -1)
        return True


# ======================================================================
# PostProcessor module list
# ======================================================================
MODULES = [TTbarJetCategorizer()]
