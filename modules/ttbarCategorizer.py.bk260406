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
  nMatchedBHadrons    (Int, -1 for non-tt; B hadrons matched to GenJets)
  nAdditionalCJets    (Int, -1 for non-tt)

Author : Junghyun Lee (NtupleForge / CMS ttHH)
"""
from __future__ import annotations

import math
from collections import defaultdict
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

_PREFIX = "[ttbarCategorizer]"


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

    # genTtbarId % 100 -> category mapping for cross-validation
    _GENID_TO_CAT: dict[str, str] = {
        "0_tt": "ttCat_LF",      # genTtbarId%100==0 with tt pair
        "0_nott": "ttCat_noTTJets",
        "41": "ttCat_cc", "42": "ttCat_cc", "43": "ttCat_cc",
        "44": "ttCat_cc", "45": "ttCat_cc", "46": "ttCat_cc",
        "47": "ttCat_cc", "48": "ttCat_cc", "49": "ttCat_cc",
        "51": "ttCat_b",
        "52": "ttCat_2b",
        "53": "ttCat_bb", "54": "ttCat_bb", "55": "ttCat_bb", "56": "ttCat_bb",
    }

    # ------------------------------------------------------------------
    # constructor
    # ------------------------------------------------------------------
    def __init__(self, debug: bool = False, max_debug_events: int = 100) -> None:
        super().__init__()
        self._debug = debug
        self._max_debug_events = max_debug_events

    # ------------------------------------------------------------------
    # framework hooks
    # ------------------------------------------------------------------
    def beginJob(self) -> None:
        self._cat_counts: dict[str, int] = defaultdict(int)
        self._n_events = 0
        self._n_debug_printed = 0
        self._xval_agree = 0
        self._xval_disagree = 0
        self._xval_na = 0  # genTtbarId not available or ambiguous

    def endJob(self) -> None:
        if not self._debug:
            return
        print(f"\n{_PREFIX} ===== END-OF-JOB SUMMARY =====")
        print(f"{_PREFIX} Total events processed: {self._n_events}")
        print(f"{_PREFIX} Category counts:")
        for cat in self.CATEGORIES:
            print(f"{_PREFIX}   {cat:20s}: {self._cat_counts.get(cat, 0):7d}")
        total_xval = self._xval_agree + self._xval_disagree
        if total_xval > 0:
            pct = 100.0 * self._xval_agree / total_xval
            print(f"{_PREFIX} Cross-validation (GenPart vs genTtbarId):")
            print(f"{_PREFIX}   agree:    {self._xval_agree:7d} / {total_xval} ({pct:.1f}%)")
            print(f"{_PREFIX}   disagree: {self._xval_disagree:7d} / {total_xval} ({100-pct:.1f}%)")
            print(f"{_PREFIX}   skipped:  {self._xval_na:7d} (genTtbarId N/A or ambiguous)")
        print(f"{_PREFIX} ===============================\n")

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree) -> None:
        self.out = wrappedOutputTree
        for cat in self.CATEGORIES:
            self.out.branch(cat, "O")                  # Bool
        self.out.branch("nAdditionalBJets", "I")       # Int
        self.out.branch("nAdditionalBHadrons", "I")    # Int
        self.out.branch("nMatchedBHadrons", "I")       # Int
        self.out.branch("nAdditionalCJets", "I")       # Int

        # cache which gen-level branches are available
        names = {b.GetName() for b in inputTree.GetListOfBranches()}
        self._has_genTtbarId = "genTtbarId" in names
        self._has_genPart = "GenPart_pdgId" in names
        self._has_genJet = "GenJet_pt" in names

    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree) -> None:
        pass

    # ------------------------------------------------------------------
    # helper: robust array size (never trust nGenPart / nGenJet counters)
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_len(branch) -> int:
        """Return the length of a NanoAOD array branch.

        The scalar counter branches (nGenPart, nGenJet) can be corrupted
        (e.g. nGenPart=32760, nGenJet=0) in some tree-stream
        configurations.  Reading ``len(event.GenPart_pdgId)`` is reliable
        because the underlying ROOT TBranch stores the correct entry count
        independently of the scalar counter leaf.
        """
        try:
            return len(branch)
        except TypeError:
            return 0

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
    def _has_top_ancestor(self, event, idx: int, nGP: int, max_depth: int = 30) -> bool:
        cur = idx
        for _ in range(max_depth):
            mother = event.GenPart_genPartIdxMother[cur]
            if mother < 0 or mother >= nGP:
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
        nGP = self._safe_len(event.GenPart_pdgId)
        for i in range(nGP):
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
    #   Returns (jet_bh_map, n_bh_total)
    #     jet_bh_map: {GenJet_index: number_of_B_hadrons_matched_to_it}
    #     n_bh_total: total additional B hadrons (including unmatched)
    # ------------------------------------------------------------------
    def _count_additional_bjets(self, event) -> tuple[dict[int, int], int]:
        if not (self._has_genPart and self._has_genJet):
            return ({}, 0)

        nGP = self._safe_len(event.GenPart_pdgId)
        nGJ = self._safe_len(event.GenJet_pt)

        # Step 1: collect additional (non-top-ancestor) last-copy B hadrons
        add_bh: list[tuple[int, float, float]] = []  # (gp_idx, eta, phi)
        for i in range(nGP):
            if not self._is_b_hadron(event.GenPart_pdgId[i]):
                continue
            if not ((event.GenPart_statusFlags[i] >> 13) & 1):   # isLastCopy
                continue
            if self._has_top_ancestor(event, i, nGP):
                continue
            add_bh.append((i, event.GenPart_eta[i], event.GenPart_phi[i]))

        if not add_bh:
            return ({}, 0)

        # Step 2: gen b-jets in acceptance
        bjet_indices: list[int] = []
        for j in range(nGJ):
            if event.GenJet_hadronFlavour[j] != 5:
                continue
            if event.GenJet_pt[j] < self.GEN_JET_PT_MIN:
                continue
            if abs(event.GenJet_eta[j]) > self.GEN_JET_ETA_MAX:
                continue
            bjet_indices.append(j)

        if not bjet_indices:
            return ({}, len(add_bh))

        # Step 3 & 4: DR matching - each B hadron to closest GenJet
        # Build per-jet B hadron count map
        dr2_cut = self.DR_MATCH_MAX * self.DR_MATCH_MAX
        jet_bh_map: dict[int, int] = defaultdict(int)
        n_matched_bh = 0
        for gp_idx, bh_eta, bh_phi in add_bh:
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
                jet_bh_map[best_j] += 1
                n_matched_bh += 1

                if self._debug and self._n_debug_printed < self._max_debug_events:
                    print(f"{_PREFIX}     BH(GP[{gp_idx}]) -> GenJet[{best_j}] "
                          f"dR={math.sqrt(best_dr2):.3f}")
            else:
                if self._debug and self._n_debug_printed < self._max_debug_events:
                    print(f"{_PREFIX}     BH(GP[{gp_idx}]) -> NO MATCH")

        return (dict(jet_bh_map), len(add_bh))

    # ------------------------------------------------------------------
    # core: count additional c-jets (no overlap with b-jets)
    # ------------------------------------------------------------------
    def _count_additional_cjets(self, event) -> int:
        if not (self._has_genPart and self._has_genJet):
            return 0

        nGP = self._safe_len(event.GenPart_pdgId)
        nGJ = self._safe_len(event.GenJet_pt)

        add_ch: list[tuple[float, float]] = []
        for i in range(nGP):
            if not self._is_c_hadron(event.GenPart_pdgId[i]):
                continue
            if not ((event.GenPart_statusFlags[i] >> 13) & 1):
                continue
            if self._has_top_ancestor(event, i, nGP):
                continue
            add_ch.append((event.GenPart_eta[i], event.GenPart_phi[i]))

        if not add_ch:
            return 0

        cjet_indices: list[int] = []
        for j in range(nGJ):
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
    def _fill(self, category: str, n_add_b: int, n_add_bh: int,
              n_matched_bh: int, n_add_c: int) -> None:
        """Set exactly one category branch True; fill counting branches."""
        for cat in self.CATEGORIES:
            self.out.fillBranch(cat, (cat == category))
        self.out.fillBranch("nAdditionalBJets", n_add_b)
        self.out.fillBranch("nAdditionalBHadrons", n_add_bh)
        self.out.fillBranch("nMatchedBHadrons", n_matched_bh)
        self.out.fillBranch("nAdditionalCJets", n_add_c)

        # bookkeeping
        self._cat_counts[category] += 1
        self._n_events += 1

    # ------------------------------------------------------------------
    # cross-validation: compare GenPart result with genTtbarId
    # ------------------------------------------------------------------
    def _cross_validate(self, event, genpart_cat: str) -> None:
        if not self._has_genTtbarId:
            self._xval_na += 1
            return

        cat_id = event.genTtbarId % 100

        # Map genTtbarId to expected category
        if cat_id == 0:
            key = "0_tt" if self._event_has_tt_pair(event) else "0_nott"
        else:
            key = str(cat_id)

        expected = self._GENID_TO_CAT.get(key)
        if expected is None:
            self._xval_na += 1
            return

        # genTtbarId cannot distinguish bbb/4b from bb
        if expected == "ttCat_bb" and genpart_cat in ("ttCat_bbb", "ttCat_4b"):
            self._xval_agree += 1
        elif expected == genpart_cat:
            self._xval_agree += 1
        else:
            self._xval_disagree += 1
            if self._debug and self._n_debug_printed <= self._max_debug_events:
                print(f"{_PREFIX}   *** XVAL MISMATCH: GenPart={genpart_cat} "
                      f"vs genTtbarId={event.genTtbarId}(mod100={cat_id})->{expected}")

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
            self._fill("ttCat_cc", 0, 0, 0, -1)
            return
        if cat_id == 51:
            self._fill("ttCat_b", 1, 1, 1, 0)
            return
        if cat_id == 52:
            self._fill("ttCat_2b", 1, 2, 2, 0)
            return
        if 53 <= cat_id <= 56:
            # genTtbarId guarantees >=2 b-jets but cannot resolve 3b/4b
            self._fill("ttCat_bb", 2, -1, -1, 0)
            return
        if cat_id == 0:
            if self._event_has_tt_pair(event):
                self._fill("ttCat_LF", 0, 0, 0, 0)
            else:
                self._fill("ttCat_noTTJets", -1, -1, -1, -1)
            return

        # unexpected value
        self._fill("ttCat_noTTJets", -1, -1, -1, -1)

    # ------------------------------------------------------------------
    # main event loop
    #
    # Primary: full GenPart-based categorization (Section 21 decision tree)
    # Fallback: genTtbarId-based when GenPart is absent
    # ------------------------------------------------------------------
    def analyze(self, event) -> bool:
        do_debug = self._debug and self._n_debug_printed < self._max_debug_events

        # --- guard: data or MC without any generator info ---
        if not self._has_genTtbarId and not self._has_genPart:
            self._fill("ttCat_noTTJets", -1, -1, -1, -1)
            return True

        # --- Primary path: full GenPart-based categorization ---
        nGP = self._safe_len(event.GenPart_pdgId) if self._has_genPart else 0
        if self._has_genPart and self._has_genJet and nGP > 0:
            # Step 1: check for tt pair
            if not self._event_has_tt_pair(event):
                if do_debug:
                    print(f"{_PREFIX} Event {self._n_events}: no ttbar pair -> ttCat_noTTJets")
                self._fill("ttCat_noTTJets", -1, -1, -1, -1)
                if do_debug:
                    self._n_debug_printed += 1
                return True

            if do_debug:
                nGJ = self._safe_len(event.GenJet_pt)
                print(f"\n{_PREFIX} Event {self._n_events}: nGP={nGP}, nGJ={nGJ}")

            # Step 2-4: count additional b-jets with per-jet B hadron map
            jet_bh_map, n_bhadrons = self._count_additional_bjets(event)
            n_bjets = len(jet_bh_map)
            n_matched_bh = sum(jet_bh_map.values())

            if do_debug:
                print(f"{_PREFIX}   addBJets={n_bjets}, addBHadrons={n_bhadrons}, "
                      f"matchedBH={n_matched_bh}, jet_bh_map={jet_bh_map}")

            # Step 5: decision tree (Section 21.5)
            #   The tt+2b check now uses PER-JET B hadron count:
            #   a single jet with >=2 matched B hadrons (collinear g->bb)
            category: str | None = None
            if n_bjets >= 4:
                category = "ttCat_4b"
                n_cjets = 0
            elif n_bjets == 3:
                category = "ttCat_bbb"
                n_cjets = 0
            elif n_bjets == 1:
                # Check if the single matched jet has >=2 B hadrons (tt+2b)
                single_jet_bh = next(iter(jet_bh_map.values()))
                if single_jet_bh >= 2:
                    category = "ttCat_2b"
                else:
                    category = "ttCat_b"
                n_cjets = self._count_additional_cjets(event)
            elif n_bjets >= 2:
                category = "ttCat_bb"
                n_cjets = 0
            else:
                # No additional b-jets; check c-jets
                n_cjets = self._count_additional_cjets(event)
                category = "ttCat_cc" if n_cjets > 0 else "ttCat_LF"

            if do_debug:
                print(f"{_PREFIX}   -> {category} (nCJets={n_cjets})")

            self._fill(category, n_bjets, n_bhadrons, n_matched_bh, n_cjets)
            self._cross_validate(event, category)

            if do_debug:
                self._n_debug_printed += 1
            return True

        # --- Fallback: genTtbarId-based (GenPart absent) ---
        if self._has_genTtbarId:
            if do_debug:
                print(f"{_PREFIX} Event {self._n_events}: GenPart absent, "
                      f"fallback genTtbarId={event.genTtbarId}")
            self._categorize_from_genTtbarId(event)
            if do_debug:
                self._n_debug_printed += 1
            return True

        # No categorization possible
        self._fill("ttCat_noTTJets", -1, -1, -1, -1)
        return True


# ======================================================================
# PostProcessor module lists
# ======================================================================
MODULES = [TTbarJetCategorizer()]
MODULES_DEBUG = [TTbarJetCategorizer(debug=True)]
