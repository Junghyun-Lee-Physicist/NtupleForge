from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class JetsMETBasicCut(Module):
    """
    Filters events based on Jet multiplicity and MET pt.
    """
    def __init__(self, njet_thr=4, met_thr=200.0):
        self.njet_thr = int(njet_thr)
        self.met_thr  = float(met_thr)
        self._warned = set()

    def _read_or(self, event, name, default):
        try:
            return getattr(event, name)
        except Exception:
            if name not in self._warned:
                print(f"[WARN] Branch '{name}' missing. Using default {default}.")
                self._warned.add(name)
            return default

    def analyze(self, event):
        njet = self._read_or(event, "nJet", 0)
        met  = self._read_or(event, "MET_pt", 0.0)
        
        # Keep event if it passes both cuts
        return (njet > self.njet_thr) and (met > self.met_thr)

# Define the list using uppercase MODULES convention
MODULES = [JetsMETBasicCut(njet_thr=4, met_thr=200.0)]
