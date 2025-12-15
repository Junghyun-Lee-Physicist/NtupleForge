from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module
# We do not import Collection anymore as we don't loop over jets
import ROOT

class JetsMETCut(Module):
    """
    [Event Selector Module]
    
    This module performs simple event skimming based on:
    1. MET_pt threshold
    2. nJet threshold (Raw count directly from NanoAOD)

    [Design Principle: Why not filter Jet collection here?]
    ------------------------------------------------------------------
    We deliberately DO NOT filter or modify the 'Jet' collection in this 
    skimming step (PostProcessor).
    
    Reasons:
    1. **Analysis Flexibility**: The definition of a "Good Jet" often 
       changes depending on the analysis phase (e.g., varying pT cuts, 
       changing ID requirements, or shifting between Loose/Tight working points). 
       Hardcoding a specific object selection here would require re-producing 
       the entire Ntuple dataset whenever definitions change.
       
    2. **Performance**: Looping over every object (Jets) in Python during the 
       production phase can be slower. It is often more efficient to perform 
       object-level filtering in the final Analyzer step using compiled C++ 
       or vectorized frameworks (like RDataFrame).
       
    3. **Data Integrity**: Keeping the full Jet collection allows for 
       sideband studies (e.g., estimating backgrounds using rejected jets) 
       and fake rate calculation later on.
       
    Therefore, this module acts purely as a "Gatekeeper", dropping events 
    that are obviously not interesting (e.g. very low MET or zero Jets), 
    while preserving the full content of the surviving events.
    ------------------------------------------------------------------
    """
    def __init__(self, njet_thr=4, met_thr=150.0):
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
        Process event:
        Apply Simple Event Cuts (MET & nJet)
        """
        # 1. MET Cut
        met_pt = self._read_or(event, "MET_pt", 0.0)
        if met_pt < self.met_thr:
            return False

        # 2. nJet Cut (Raw count)
        # We rely on the pre-calculated nJet branch in NanoAOD
        njet = self._read_or(event, "nJet", 0)
        if njet < self.njet_thr:
            return False

        return True

# Configuration
# Default: nJet >= 4, MET > 150
MODULES = [JetsMETCut(njet_thr=6, met_thr=300.0)]
