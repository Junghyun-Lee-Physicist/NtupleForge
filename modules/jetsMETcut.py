from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class JetsMETBasicCut(Module):
    """
    [Event Selector Module]
    Hardcoding cuts here is safer than passing strings via CRAB arguments.
    """
    def __init__(self, njet_thr=3, met_thr=0.0): # Default cut values
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
        """
        Returns True (Keep Event) or False (Drop Event)
        """
        njet = self._read_or(event, "nJet", 0)
        met  = self._read_or(event, "MET_pt", 0.0)
        
        # --- CUT LOGIC ---
        # Modify your cuts logic here directly
        if njet < self.njet_thr:
            return False
        if met < self.met_thr:
            return False
            
        return True

# Define configuration
# You can change default values here
MODULES = [JetsMETBasicCut(njet_thr=8, met_thr=200.0)]
