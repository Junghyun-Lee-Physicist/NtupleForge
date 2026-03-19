"""
NtupleForge: tt+jets Event Categorizer Module
=============================================
Categorizes tt+jets events into sub-categories based on the flavour of
additional jets NOT originating from top-quark decays, following the
methodology of:
  - CMS AN-2022/122 (ttHH -> 4b, Sections 3.1 & 3.2)
  - CMS AN-19-094   (ttH  -> bb, Section 6.1)
Both analyses use the CMS GenHFHadronMatcher tool with generator-level
jets satisfying pT > 20 GeV and |eta| < 2.4.

Standard 5 categories (shared with ttH):
  tt+LF  : no additional heavy-flavour jets
  tt+cc  : additional charm jet(s), no additional b-jets
  tt+b   : 1 additional b-jet from a single B hadron
  tt+2b  : 1 additional b-jet from >= 2 overlapping B hadrons
  tt+bb  : exactly 2 additional b-jets
Extended categories (ttHH-specific, AN-2022/122 Section 3.2):
  tt+bbb : exactly 3 additional b-jets
  tt+4b  : >= 4 additional b-jets

Algorithm:
  1) Standard categories are derived from the NanoAOD `genTtbarId` branch
     (encoded by GenTtbarCategorizer in CMSSW).
  2) For events with genTtbarId % 100 in [53..56] (i.e. >= 2 additional
     b-jets), the exact count is refined by tracing B-hadron ancestry in
     GenPart and matching to GenJets.
  3) Non-tt events (signal, data, other bkg) are flagged via
     `ttCat_noTTJets`.

Output branches (all Bool except nAdditionalBJets):
  ttCat_LF, ttCat_cc, ttCat_b, ttCat_2b, ttCat_bb,
  ttCat_bbb, ttCat_4b, ttCat_noTTJets,
  nAdditionalBJets (Int, -1 for non-tt events)

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
            self.out.branch(cat, "O")               # Bool
        self.out.branch("nAdditionalBJets", "I")    # Int

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
    #   Must match C++ isBHadron() in ttHHanalyzer_unified.h exactly.
    # ------------------------------------------------------------------
    @staticmethod
    def _is_b_hadron(pdgId: int) -> bool:
        """Return True if *pdgId* encodes a hadron containing a b quark.

        PDG convention:
          - B mesons : hundreds digit == 5  (e.g. 511=B0, 521=B+, 531=Bs)
          - B baryons: thousands digit == 5 (e.g. 5122=Lambda_b)
          - Excited / special states   : base = aid % 10000, check base
        """
        aid = abs(pdgId)
        if aid < 100:
            return False
        if aid < 1000:                       # mesons
            return (aid // 100) == 5
        if aid < 10000:                      # baryons
            return (aid // 1000) == 5
        # excited states encoded as n * 10000 + base
        base = aid % 10000
        if 100 <= base < 1000:
            return (base // 100) == 5
        if 1000 <= base < 10000:
            return (base // 1000) == 5
        return False

    # ------------------------------------------------------------------
    # helper: check whether a GenPart has a top-quark ancestor
    #   Depth limit of 30 matches C++ hasTopAncestor().
    # ------------------------------------------------------------------
    def _has_top_ancestor(self, event, idx: int, max_depth: int = 30) -> bool:
        """Walk up the mother chain; return True if a top (|pdgId|==6)
        is found within *max_depth* steps."""
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
    #   NOTE: Do NOT require isLastCopy here. Some generators
    #   (e.g. Powheg+Pythia8) do not reliably set isLastCopy for top
    #   quarks, causing tt+LF events to be misclassified as noTTJets.
    #   Matches C++ eventHasTTPair() in ttHHanalyzer_unified.h.
    # ------------------------------------------------------------------
    def _event_has_tt_pair(self, event) -> bool:
        """Return True if event contains both t and t-bar in GenPart."""
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
    #   Algorithm mirrors GenHFHadronMatcher and C++ countAdditionalBJets():
    #     1) Collect last-copy B hadrons whose ancestry does NOT include
    #        a top quark  -> 'additional' B hadrons.
    #     2) Collect GenJets with hadronFlavour == 5 in acceptance.
    #     3) For each B hadron, find the CLOSEST GenJet (best deltaR match).
    #     4) Return the number of unique matched GenJets.
    # ------------------------------------------------------------------
    def _count_additional_bjets(self, event) -> int:
        if not (self._has_genPart and self._has_genJet):
            return 0

        # --- step 1: additional B hadrons ---
        add_bh: list[tuple[float, float]] = []          # (eta, phi)
        for i in range(event.nGenPart):
            if not self._is_b_hadron(event.GenPart_pdgId[i]):
                continue
            if not ((event.GenPart_statusFlags[i] >> 13) & 1):   # isLastCopy
                continue
            if self._has_top_ancestor(event, i):
                continue
            add_bh.append((event.GenPart_eta[i], event.GenPart_phi[i]))

        if not add_bh:
            return 0

        # --- step 2: gen b-jets in acceptance ---
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
            return 0

        # --- step 3 & 4: best-DR matching, collect unique jets ---
        #   Each B hadron matches to its closest GenJet (minimum deltaR).
        #   Multiple B hadrons may map to the same jet; set ensures
        #   unique counting.  This matches C++ countAdditionalBJets().
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

        return len(matched)

    # ------------------------------------------------------------------
    # output helper
    # ------------------------------------------------------------------
    def _fill(self, category: str, n_add_b: int) -> None:
        """Set exactly one category branch True; fill nAdditionalBJets."""
        for cat in self.CATEGORIES:
            self.out.fillBranch(cat, (cat == category))
        self.out.fillBranch("nAdditionalBJets", n_add_b)

    # ------------------------------------------------------------------
    # main event loop
    # ------------------------------------------------------------------
    def analyze(self, event) -> bool:
        # --- guard: data or MC without generator info ---
        if not (self._has_genTtbarId and self._has_genPart):
            self._fill("ttCat_noTTJets", -1)
            return True

        cat_id = event.genTtbarId % 100

        # ---- genTtbarId > 0 implies a tt system was found ----
        if 41 <= cat_id <= 49:
            # tt + cc (charm)
            self._fill("ttCat_cc", 0)
            return True

        if cat_id == 51:
            # tt + b  (1 extra b-jet, 1 B hadron)
            self._fill("ttCat_b", 1)
            return True

        if cat_id == 52:
            # tt + 2b (1 extra b-jet, >= 2 merged B hadrons)
            self._fill("ttCat_2b", 1)
            return True

        if 53 <= cat_id <= 56:
            # >= 2 additional b-jets - refine exact count
            n = self._count_additional_bjets(event)
            n = max(n, 2)              # genTtbarId guarantees >= 2
            if n >= 4:
                self._fill("ttCat_4b", n)
            elif n == 3:
                self._fill("ttCat_bbb", n)
            else:
                self._fill("ttCat_bb", n)
            return True

        if cat_id == 0:
            # ambiguous: tt+LF *or* non-tt sample (both give 0)
            if self._event_has_tt_pair(event):
                self._fill("ttCat_LF", 0)
            else:
                self._fill("ttCat_noTTJets", -1)
            return True

        # unexpected value - treat as non-tt
        self._fill("ttCat_noTTJets", -1)
        return True


# ======================================================================
# PostProcessor module list
# ======================================================================
MODULES = [TTbarJetCategorizer()]
