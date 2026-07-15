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

Extended 2026-07-10 (background rebuild, audit §2b): the MC sample is now FOUR
events — 2x ttbar signal (also asserts Channel_Jets 2112/1212 and
Channel_Idx_Expanded), explicit-Z Z->tautau (must give Channel_Idx=-30, NOT the
old double-counted -60), and boson-less ME mumu (must give 26, NOT the old 0).
The same three physics events are asserted, with identical expected values, by
the standalone C++ harness (SSBGenCategorizer/validation/crosscheck/).
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

# ---- synthetic 4-event MC sample -------------------------------------------
#  ev0/ev1: ttbar-like signal (unchanged; ev0 also drives TEST 1)
#  ev2:     explicit-Z Z->tautau background — regression for audit §2b risk (a)
#           (the pre-2026-07-10 recursion+tau-rescue double-counted: -60)
#  ev3:     boson-less ME mumu background — regression for §2b risk (b)
#           (the old algorithm found no boson and returned 0)
sys.path.insert(0, "/tmp/build/NtupleForge/modules")
import topCPVCategorizer as M
LAST = M._IS_LAST_COPY
IHP  = M._IS_HARD_PROCESS
FHP  = 1 << 8   # fromHardProcess (history bit; module no longer needs a constant)
pdg  = [6,-6, 24,5, -24,-5, 2,-1, 1,-2]
mom  = [-1,-1, 0,0, 1,1, 2,2, 4,4]
flg  = [LAST]*10
sta  = [22,22,22,23,22,23,23,23,23,23]
pt   = [180.,175.,90.,60.,88.,58.,40.,35.,42.,33.]
eta  = [0.4,-0.3,0.2,0.5,-0.1,0.6,0.25,0.15,-0.2,-0.05]
phi  = [0.1,3.0,0.3,0.8,2.9,2.2,0.35,0.28,3.05,2.8]
mass = [172.5,172.5,80.4,4.7,80.4,4.7,0.,0.,0.,0.]
# ev2: Z(iHP) -> tau23(iHP) x2 -> tau_last(LAST|FHP) x2 -> [mu,nu,nu] / [pi,nu]
pdg2 = [23, 15, -15, 15, -15, 13, -14, 16, 211, -16]
mom2 = [-1,  0,   0,  1,   2,  3,   3,  3,   4,   4]
flg2 = [IHP, IHP, IHP, LAST | FHP, LAST | FHP, 0, 0, 0, 0, 0]
sta2 = [22, 23, 23, 2, 2, 1, 1, 1, 1, 1]
kin2 = [50., 45., 44., 44.5, 43.5, 20., 12., 11., 15., 9.]
# ev3: qqbar(iHP) -> mu23(iHP) x2 (NO boson row) -> mu_last x2
pdg3 = [2, -2, 13, -13, 13, -13]
mom3 = [-1, -1, 0, 0, 2, 3]
flg3 = [IHP, IHP, IHP, IHP, LAST, LAST]
sta3 = [21, 21, 23, 23, 1, 1]
kin3 = [70., 68., 35., 33., 34.8, 32.9]
NEV = 4
arrays = {
    "GenPart_pdgId": [pdg, pdg, pdg2, pdg3],
    "GenPart_statusFlags": [flg, flg, flg2, flg3],
    "GenPart_genPartIdxMother": [mom, mom, mom2, mom3],
    "GenPart_status": [sta, sta, sta2, sta3],
    "GenPart_pt":   [pt, pt, kin2, kin3],
    "GenPart_eta":  [eta, eta, [0.1]*10, [0.2]*6],
    "GenPart_phi":  [phi, phi, [0.5]*10, [1.0]*6],
    "GenPart_mass": [mass, mass, [0.]*10, [0.]*6],
    "GenJet_pt": [[61.], [61.], [], []], "GenJet_eta": [[0.52], [0.52], [], []],
    "GenJet_phi": [[0.81], [0.81], [], []], "GenJet_mass": [[8.], [8.], [], []],
    "GenJet_hadronFlavour": [[b"\x05"], [b"\x05"], [], []],
}
scalars = {"nGenPart": [10, 10, 10, 6], "nGenJet": [1, 1, 0, 0],
           "nGenVisTau": [0, 0, 2, 0]}

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
r0, r1, r2, r3 = out.filled

# ev0/ev1 — ttbar signal, all-hadronic
for r in (r0, r1):
    assert r["TopCPVCat_isSignal"] is True
    assert r["TopCPVCat_GenPar_Count"] == 12
    assert r["TopCPVCat_GenBJet_Count"] == 1
    assert r["TopCPVCat_Channel_Idx"] == 0
    assert r["TopCPVCat_Channel_Idx_Final"] == 0
    assert r["TopCPVCat_Channel_Lepton_Count"] == 0
    assert r["TopCPVCat_Channel_Jets"] == 2112       # W+(u,dbar)=21, W-(d,ubar)=12
    assert r["TopCPVCat_Channel_Jets_Abs"] == 1212   # digit-normalized
    assert r["TopCPVCat_Channel_Idx_Expanded"] == 0

# ev2 — explicit-Z Z->tautau (tau+ -> mu, tau- -> hadrons)
assert r2["TopCPVCat_isSignal"] is False
assert r2["TopCPVCat_GenPar_Count"] == 4             # Z, tau, taubar (+ appended mu)
assert r2["TopCPVCat_Channel_Idx"] == -30            # NOT -60: no tau double count
assert r2["TopCPVCat_Channel_Lepton_Count"] == 2
assert r2["TopCPVCat_Channel_Idx_Final"] == 13       # -30 +15(tau->mu) +13 +15(tau_h removed)
assert r2["TopCPVCat_Channel_Lepton_Count_Final"] == 1
assert r2["TopCPVCat_Channel_Tau_Lepton"] == 1
assert r2["TopCPVCat_Channel_Visible_Tau"] == 2
assert r2["TopCPVCat_Channel_Idx_Expanded"] == -30
assert r2["TopCPVCat_GenPar_pdgId"] == [23, 15, -15, 13]
assert r2["TopCPVCat_GenPar_Mom1_Idx"][3] == 1       # appended mu: mother = selected tau

# ev3 — boson-less ME mumu
assert r3["TopCPVCat_isSignal"] is False
assert r3["TopCPVCat_GenPar_Count"] == 4             # u, ubar, mu23, mubar23
assert r3["TopCPVCat_Channel_Idx"] == 26             # NOT 0: e/mu recovered w/o boson row
assert r3["TopCPVCat_Channel_Lepton_Count"] == 2
assert r3["TopCPVCat_Channel_Idx_Final"] == 26
assert r3["TopCPVCat_Channel_Lepton_Count_Final"] == 2
assert r3["TopCPVCat_Channel_Tau_Lepton"] == 0
assert r3["TopCPVCat_Channel_Idx_Expanded"] == 26
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
