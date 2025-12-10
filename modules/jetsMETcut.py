from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection
import ROOT

class JetsMETCut(Module):
    """
    [Event Selector & Producer Module]
    1. Filters events based on MET and Jet criteria.
    2. Adds a new branch 'nGoodJet' (number of jets passing selection).
    """
    def __init__(self, njet_thr=4, met_thr=150.0, jet_pt_thr=30.0, jet_eta_thr=2.4):
        self.njet_thr = int(njet_thr)
        self.met_thr  = float(met_thr)
        self.jet_pt_thr = float(jet_pt_thr)
        self.jet_eta_thr = float(jet_eta_thr)
        self._warned = set()

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        """
        Called when a new file is opened. Declare new branches here.
        """
        self.out = wrappedOutputTree
        # 새로운 브랜치 'nGoodJet' 추가 (Integer 타입)
        self.out.branch("nGoodJet", "I")

    def _read_or(self, event, name, default):
        try:
            return getattr(event, name)
        except Exception:
            if name not in self._warned:
                print(f"[WARN] Branch '{name}' missing. Using default {default}.")
                self._warned.add(name)
            return default

    def analyze(self, event):
        """
        Process event: Apply cuts AND fill new branches.
        """
        # 1. MET Cut
        met_pt = self._read_or(event, "MET_pt", 0.0)
        if met_pt < self.met_thr:
            return False

        # 2. Jet Selection
        try:
            jets = Collection(event, "Jet")
        except Exception as e:
            if "Jet" not in self._warned:
                print(f"[WARN] Failed to load Jet collection: {e}")
                self._warned.add("Jet")
            return False

        good_jet_count = 0
        
        for jet in jets:
            # Kinematic Cuts
            if jet.pt < self.jet_pt_thr:
                continue
            if abs(jet.eta) > self.jet_eta_thr:
                continue
            
            # Jet ID Cut
            try:
                if jet.jetId < 6:
                    continue
            except AttributeError:
                 if "Jet_jetId" not in self._warned:
                    print("[WARN] Jet_jetId branch missing. Skipping ID cut.")
                    self._warned.add("Jet_jetId")

            good_jet_count += 1

        # 3. Fill New Branch (컷 적용 전에 저장하거나, 통과한 이벤트만 저장)
        # 컷을 통과한 이벤트에 대해서만 값이 저장됩니다.
        self.out.fillBranch("nGoodJet", good_jet_count)

        # 4. Final nJet Cut
        if good_jet_count < self.njet_thr:
            return False

        return True

# Configuration
MODULES = [JetsMETCut(njet_thr=4, met_thr=150.0, jet_pt_thr=30.0, jet_eta_thr=2.4)]
