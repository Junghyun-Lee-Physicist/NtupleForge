from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class JetsMETBasicCut(Module):
    def __init__(self, njet_thr=4, met_thr=200.0):
        self.njet_thr = int(njet_thr)
        self.met_thr  = float(met_thr)
        self._warned = set()

    def _read_or(self, event, name, default):
        try:
            return getattr(event, name)
        except Exception as e:
            if name not in self._warned:
                print(f"[WARN] missing/disabled branch '{name}' (status=0?). Using default {default}.")
                self._warned.add(name)
            return default  # 또는 return False를 위해 analyze에서 바로 드롭해도 됨

    def analyze(self, event):
        njet = self._read_or(event, "nJet", 0)
        met  = self._read_or(event, "MET_pt", 0.0)
        return (njet > self.njet_thr) and (met > self.met_thr)

MODULES = [JetsMETBasicCut(njet_thr=4, met_thr=200.0)]
