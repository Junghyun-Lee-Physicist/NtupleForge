"""A13 regression test — runs the REAL CMSSW_14_2_X nanoAOD-tools framework
files over a mock ROOT (cppyy lifetime semantics) to (1) reproduce the
stale-reader crash of 2026-07-02 and (2) verify the pre-registration fix keeps
the event loop remake-free. See docs/05_troubleshooting.md A13.

Prerequisites (dev container):
  /tmp/natools/   <- treeReaderArrayTools.py, datamodel.py, eventloop.py from
                     https://raw.githubusercontent.com/cms-sw/cmssw/CMSSW_14_2_X/PhysicsTools/NanoAODTools/python/postprocessing/framework/
  /tmp/rootmock/ROOT.py <- the mock (weakref proxies); see A13 entry.
Not needed on lxplus (there you validate against real ROOT instead:
  python3 script/run_postproc.py <MC file> -I modules.topCPVCategorizer:MODULES -b branches/branch_CPV_Run2_MC.txt -N 10).
"""
import sys, os, types

# 1) mock ROOT first (framework files `import ROOT`)
sys.path.insert(0, "/tmp/rootmock")
import ROOT  # noqa

# 2) expose the REAL CMSSW_14_2_X framework files under their package names
pkg_chain = ["PhysicsTools", "PhysicsTools.NanoAODTools",
             "PhysicsTools.NanoAODTools.postprocessing",
             "PhysicsTools.NanoAODTools.postprocessing.framework"]
for nm in pkg_chain:
    m = types.ModuleType(nm); m.__path__ = []; sys.modules[nm] = m
import importlib.util
def load_as(path, fullname):
    spec = importlib.util.spec_from_file_location(fullname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = mod
    spec.loader.exec_module(mod)
    return mod
tra = load_as("/tmp/natools/treeReaderArrayTools.py",
              "PhysicsTools.NanoAODTools.postprocessing.framework.treeReaderArrayTools")
dm  = load_as("/tmp/natools/datamodel.py",
              "PhysicsTools.NanoAODTools.postprocessing.framework.datamodel")
el  = load_as("/tmp/natools/eventloop.py",
              "PhysicsTools.NanoAODTools.postprocessing.framework.eventloop")
from ROOT import FakeTree

# ---- synthetic 2-event MC sample (ttbar-like signal x2) --------------------
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modules"))
import topCPVCategorizer as M
LAST = M._IS_LAST_COPY
pdg  = [6,-6, 24,5, -24,-5, 2,-1, 1,-2]
mom  = [-1,-1, 0,0, 1,1, 2,2, 4,4]
flg  = [LAST]*10
sta  = [22,22,22,23,22,23,23,23,23,23]
pt   = [180.,175.,90.,60.,88.,58.,40.,35.,42.,33.]
eta  = [0.4,-0.3,0.2,0.5,-0.1,0.6,0.25,0.15,-0.2,-0.05]
phi  = [0.1,3.0,0.3,0.8,2.9,2.2,0.35,0.28,3.05,2.8]
mass = [172.5,172.5,80.4,4.7,80.4,4.7,0.,0.,0.,0.]
NEV = 2
arrays = {
    "GenPart_pdgId": [pdg]*NEV, "GenPart_statusFlags": [flg]*NEV,
    "GenPart_genPartIdxMother": [mom]*NEV, "GenPart_status": [sta]*NEV,
    "GenPart_pt": [pt]*NEV, "GenPart_eta": [eta]*NEV,
    "GenPart_phi": [phi]*NEV, "GenPart_mass": [mass]*NEV,
    "GenJet_pt": [[61.]]*NEV, "GenJet_eta": [[0.52]]*NEV,
    "GenJet_phi": [[0.81]]*NEV, "GenJet_mass": [[8.]]*NEV,
    "GenJet_hadronFlavour": [[b"\x05"]]*NEV,
}
scalars = {"nGenPart": [10]*NEV, "nGenJet": [1]*NEV, "nGenVisTau": [0]*NEV}

def fresh_tree():
    return tra.InputTree(FakeTree(arrays, scalars, NEV))

# ============ TEST 1: reproduce YESTERDAY'S pattern (lazy binds) ============
print("== TEST 1: reproduce the CRAB failure (lazy mid-loop binds) ==")
t = fresh_tree()
e = dm.Event(t, 0)                       # gotoEntry(0): reader now dirty
_n = e.nGenPart                          # first-access: remake + value reader
b_pdg = e.GenPart_pdgId                  # remake; bind local
b_flg = e.GenPart_statusFlags            # remake -> b_pdg now dangles
b_mom = e.GenPart_genPartIdxMother       # remake -> b_flg dangles
b_sta = e.GenPart_status                 # remake -> b_mom dangles
b_pt  = e.GenPart_pt                     # ...
try:
    _ = b_mom[0]
    print("  UNEXPECTED: stale read succeeded (mock GC timing?)"); sys.exit(1)
except ReferenceError as err:
    print("  REPRODUCED: ReferenceError on stale local ->", str(err).splitlines()[-1].strip())
print("  reader version after binds:", t._ttreereaderversion)

# ============ TEST 2: fixed module through the REAL eventLoop ============
print("== TEST 2: fixed module via real eventLoop/Event/InputTree ==")
class OutTree:
    def __init__(self): self.defined=[]; self.filled=[]; self._cur={}
    def branch(self, name, typ, n=None, lenVar=None): self.defined.append(name)
    def fillBranch(self, name, val): self._cur[name]=val
    def fill(self): self.filled.append(dict(self._cur)); self._cur={}

t2 = fresh_tree()
out = OutTree()
cat = M.TopCPVCategorizer()
v_before = t2._ttreereaderversion
(done, accepted, _) = el.eventLoop([cat], None, None, t2, out, progress=None)
v_after = t2._ttreereaderversion
last = out.filled[-1]
print(f"  events done={done} accepted={accepted}; branches defined={len(out.defined)}")
print(f"  reader version before/after loop: {v_before} -> {v_after} "
      f"({'REMAKE-FREE OK' if v_after==v_before else 'REMADE (BAD)'})")
print(f"  isSignal={last['TopCPVCat_isSignal']} GenPar_Count={last['TopCPVCat_GenPar_Count']} "
      f"GenBJet_Count={last['TopCPVCat_GenBJet_Count']} Channel_Idx={last['TopCPVCat_Channel_Idx']}")
assert done == NEV and accepted == NEV
assert v_after == v_before, "readers were remade during the loop"
assert last["TopCPVCat_isSignal"] is True
assert last["TopCPVCat_GenPar_Count"] == 12
assert last["TopCPVCat_GenBJet_Count"] == 1
cat.endJob()

# ============ TEST 3: data no-op through the same machinery ============
print("== TEST 3: data file (no GenPart) is a no-op ==")
t3 = tra.InputTree(FakeTree({}, {"run":[1]*NEV, "luminosityBlock":[1]*NEV, "event":[1,2]}, NEV))
out3 = OutTree()
cat3 = M.TopCPVCategorizer()
(done3, acc3, _) = el.eventLoop([cat3], None, None, t3, out3, progress=None)
assert done3 == NEV and acc3 == NEV and not out3.defined
print(f"  events passed={acc3}, branches defined={len(out3.defined)} (no-op OK)")
cat3.endJob()

print("\nALL FRAMEWORK-LEVEL TESTS PASSED")
