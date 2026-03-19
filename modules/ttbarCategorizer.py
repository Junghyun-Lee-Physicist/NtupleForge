"""
TTbar Jet Categorizer Module for NanoAODTools

Classifies ttbar events into categories based on additional heavy-flavor jets
beyond those from top decay. Uses genTtbarId from the GenTtbarCategorizer
and additional GenPart/GenJet matching for fine-grained b-jet counting.

Categories:
  tt+LF     : ttbar + light-flavor jets (catId == 0 with tt pair present)
  tt+cc     : ttbar + charm jets (catId 41-49)
  tt+b      : ttbar + 1 additional b-jet (catId 51)
  tt+2b     : ttbar + 2 additional b-jets from same gluon splitting (catId 52)
  tt+bb     : ttbar + 2 additional b-jets (catId 53-56, nAdditionalBJets == 2)
  tt+bbb    : ttbar + 3 additional b-jets (catId 53-56, nAdditionalBJets == 3)
  tt+4b     : ttbar + >=4 additional b-jets (catId 53-56, nAdditionalBJets >= 4)
  noTTJets  : no tt pair found or unrecognized category
"""

import math
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection


class TTbarJetCategorizer(Module):
    """Produces ttbar categorization branches from genTtbarId."""

    def __init__(self):
        super(TTbarJetCategorizer, self).__init__()

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        # Boolean category flags
        self.out.branch("ttCat_LF", "O")       # Bool_t
        self.out.branch("ttCat_cc", "O")
        self.out.branch("ttCat_b", "O")
        self.out.branch("ttCat_2b", "O")
        self.out.branch("ttCat_bb", "O")
        self.out.branch("ttCat_bbb", "O")
        self.out.branch("ttCat_4b", "O")
        self.out.branch("ttCat_noTTJets", "O")
        # Additional b-jet count
        self.out.branch("nAdditionalBJets", "I")  # Int_t

    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass

    @staticmethod
    def _is_b_hadron(pdgId):
        """Check if a particle is a B hadron (contains b quark content)."""
        aid = abs(pdgId)
        # B mesons: floor(aid/100) == 5, B baryons: floor(aid/1000) == 5
        return (aid // 100) % 10 == 5 or aid // 1000 == 5

    @staticmethod
    def _is_last_copy(statusFlags):
        """Check isLastCopy flag (bit 13) of GenPart_statusFlags."""
        return bool(statusFlags & (1 << 13))

    @staticmethod
    def _has_top_ancestor(idx, genpart_mother, genpart_pdgId):
        """Walk up the mother chain; return True if any ancestor is a top quark."""
        current = idx
        while True:
            mother = genpart_mother[current]
            if mother < 0:
                return False
            if abs(genpart_pdgId[mother]) == 6:
                return True
            current = mother

    @staticmethod
    def _delta_r(eta1, phi1, eta2, phi2):
        deta = eta1 - eta2
        dphi = phi1 - phi2
        # Wrap dphi to [-pi, pi]
        while dphi > math.pi:
            dphi -= 2.0 * math.pi
        while dphi < -math.pi:
            dphi += 2.0 * math.pi
        return math.sqrt(deta * deta + dphi * dphi)

    def _count_additional_bjets(self, event):
        """Count additional b-jets not from top ancestry.

        Algorithm:
        1. Find last-copy B hadrons NOT descending from a top quark.
        2. Find GenJets with hadronFlavour==5, pT>20, |eta|<2.4.
        3. Match B hadrons to GenJets with deltaR < 0.4.
        4. Count unique matched jets.
        """
        genparts = Collection(event, "GenPart")
        genjets = Collection(event, "GenJet")

        # Collect arrays for mother-chain traversal
        genpart_mother = [gp.genPartIdxMother for gp in genparts]
        genpart_pdgId = [gp.pdgId for gp in genparts]

        # Step 1: find last-copy B hadrons not from top
        b_hadrons = []
        for i, gp in enumerate(genparts):
            if not self._is_b_hadron(gp.pdgId):
                continue
            if not self._is_last_copy(gp.statusFlags):
                continue
            if self._has_top_ancestor(i, genpart_mother, genpart_pdgId):
                continue
            b_hadrons.append(gp)

        if not b_hadrons:
            return 0

        # Step 2: find b-flavored GenJets passing kinematic cuts
        b_genjets = []
        for j, gj in enumerate(genjets):
            if gj.hadronFlavour != 5:
                continue
            if gj.pt <= 20.0 or abs(gj.eta) >= 2.4:
                continue
            b_genjets.append((j, gj))

        if not b_genjets:
            return 0

        # Step 3: match B hadrons to GenJets
        matched_jet_indices = set()
        for bh in b_hadrons:
            for j_idx, gj in b_genjets:
                if j_idx in matched_jet_indices:
                    continue
                dr = self._delta_r(bh.eta, bh.phi, gj.eta, gj.phi)
                if dr < 0.4:
                    matched_jet_indices.add(j_idx)
                    break  # this B hadron matched; move to next

        return len(matched_jet_indices)

    @staticmethod
    def _has_tt_pair(event):
        """Check if both top (pdgId==6) and antitop (pdgId==-6) exist in GenPart."""
        genparts = Collection(event, "GenPart")
        has_top = False
        has_antitop = False
        for gp in genparts:
            if gp.pdgId == 6:
                has_top = True
            elif gp.pdgId == -6:
                has_antitop = True
            if has_top and has_antitop:
                return True
        return False

    def analyze(self, event):
        # Initialize all categories to False
        cats = {
            "ttCat_LF": False,
            "ttCat_cc": False,
            "ttCat_b": False,
            "ttCat_2b": False,
            "ttCat_bb": False,
            "ttCat_bbb": False,
            "ttCat_4b": False,
            "ttCat_noTTJets": False,
        }
        n_add_bjets = 0

        genTtbarId = int(getattr(event, "genTtbarId", 0))
        catId = genTtbarId % 100

        if 41 <= catId <= 49:
            cats["ttCat_cc"] = True
        elif catId == 51:
            cats["ttCat_b"] = True
        elif catId == 52:
            cats["ttCat_2b"] = True
        elif 53 <= catId <= 56:
            n_add_bjets = self._count_additional_bjets(event)
            if n_add_bjets >= 4:
                cats["ttCat_4b"] = True
            elif n_add_bjets == 3:
                cats["ttCat_bbb"] = True
            else:
                # Default to tt+bb for catId 53-56 (at least 2 additional b-jets implied)
                cats["ttCat_bb"] = True
                n_add_bjets = max(n_add_bjets, 2)
        elif catId == 0:
            if self._has_tt_pair(event):
                cats["ttCat_LF"] = True
            else:
                cats["ttCat_noTTJets"] = True
        else:
            cats["ttCat_noTTJets"] = True

        # Fill output branches
        for branch_name, value in cats.items():
            self.out.fillBranch(branch_name, value)
        self.out.fillBranch("nAdditionalBJets", n_add_bjets)

        return True


MODULES = [TTbarJetCategorizer()]
