#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_forge_audit_root.py -- the event skim and audit with REAL ROOT and the real
NanoAODTools (plan 12 P5, lxplus: inside cmssw-el8 after cmsenv; no grid, no AAA).

Writes small NanoAOD-like files into a temp dir (NanoAODv15 branch types: run
and luminosityBlock UInt_t, event ULong64_t, Jet_pt / Jet_eta Float_t[nJet],
genWeight Float_t, genTtbarId Int_t, a Runs tree with genEventCount /
genEventSumw / genEventSumw2, Events autosave 0 as NanoAODOutputModule writes
it), with events on the selection boundaries (pt exactly 20, the next float,
|eta| exactly 2.5, NaN and inf pt and eta, no jets) plus random ones, and runs
script/run_postproc.py on them the way a CRAB job does (-o, noop module,
--skim, --audit). Each output is then read back by script/check_forge_output.py,
which compares the TTreeFormula selection that NanoAODTools applied with the
RVec expression EVENT BY EVENT (X7), the ForgeAudit row (A) and the keys (K).
Also: a Data file, a Data file given the MC list (a keep pattern that matches
nothing is a WARN, not a failure), a file where nothing passes, an empty file,
an entry range (-N, --first-entry), two inputs, a haddnano.py merge of two
outputs (the audit trees must be concatenated), and the command line without
the new flags (unchanged behaviour).

    python3 script/test_forge_audit_root.py        # last line: RESULT: ALL PASS (N checks)

Needs PyROOT, NanoAODTools (PhysicsTools.NanoAODTools) and haddnano.py in PATH:
cmsenv gives all three. Writes only into a temp dir. ASCII only.
"""
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
from array import array

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "script")
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   -> %s" % (detail,)))


def f32(x):
    return float(array("f", [x])[0])


def edge_events():
    six = [(60.0, 0.1)] * 5
    nxt20, prv25 = f32(20.000002), f32(2.4999998)
    nan, inf = float("nan"), float("inf")
    return [
        six + [(20.0, 0.0)],               # 6th jet pt exactly 20: fails pt > 20
        six + [(nxt20, 0.0)],              # next float above 20: passes
        six + [(30.0, 2.5)],               # |eta| exactly 2.5: fails
        six + [(30.0, -prv25)],            # |eta| just below 2.5: passes
        six + [(nan, 0.0)],                # NaN pt
        six + [(30.0, nan)],               # NaN eta
        six + [(inf, 0.0)],                # inf pt
        six + [(30.0, -inf)],              # -inf eta
        six + [(-30.0, 0.0)],              # negative pt
        six + [(30.0, 0.0), (nan, 3.0)],   # NaN pt outside the acceptance
        [],                                # no jet
        six,                               # five jets
        [(21.0, 2.4)] * 6,                 # HT 126
        [(80.0, 0.3)] * 6,                 # HT 480
        [(80.0, 0.3)] * 5 + [(inf, 3.0)],  # inf pt outside eta: the formula's HT is NaN
    ]


def make(ROOT, path, n_random, is_mc, seed=1, run=1, pass_frac=None, edges=True):
    random.seed(seed)
    f = ROOT.TFile(path, "RECREATE")
    t = ROOT.TTree("Events", "Events")
    t.SetAutoSave(0)
    b = {"run": array("I", [0]), "lumi": array("I", [0]), "evt": array("Q", [0]), "nj": array("i", [0]),
         "pt": array("f", [0.0] * 64), "eta": array("f", [0.0] * 64), "w": array("f", [0.0]), "gt": array("i", [0]),
         "hlt": array("B", [0])}
    t.Branch("run", b["run"], "run/i")
    t.Branch("luminosityBlock", b["lumi"], "luminosityBlock/i")
    t.Branch("event", b["evt"], "event/l")
    t.Branch("nJet", b["nj"], "nJet/I")
    t.Branch("Jet_pt", b["pt"], "Jet_pt[nJet]/F")
    t.Branch("Jet_eta", b["eta"], "Jet_eta[nJet]/F")
    if is_mc:
        t.Branch("genWeight", b["w"], "genWeight/F")
        t.Branch("genTtbarId", b["gt"], "genTtbarId/I")
    t.Branch("HLT_PFJet500", b["hlt"], "HLT_PFJet500/O")
    codes = [0, 0, 0, 51, 52, 53, 54, 55, 1053, 2054, 10155, 41, 45, -1, 4, 5]
    evs = edge_events() if edges else []
    sumw = sumw2 = 0.0
    n = 0
    for i in range(len(evs) + n_random):
        if i < len(evs):
            jets = evs[i]
        else:
            nj = random.randint(0, 14)
            jets = [(random.expovariate(1 / 35.0) + 5.0, random.uniform(-4.7, 4.7)) for _ in range(nj)]
            if pass_frac is not None:
                if random.random() < pass_frac:
                    jets = [(random.uniform(21, 200), random.uniform(-2.4, 2.4)) for _ in range(6)] + jets
                else:
                    jets = [(random.uniform(5, 19.9), random.uniform(-2.4, 2.4)) for _ in range(nj)]
        b["run"][0] = run
        b["lumi"][0] = 1 + i // 50
        b["evt"][0] = 1 + i
        b["nj"][0] = len(jets)
        for j, (pt, eta) in enumerate(jets):
            b["pt"][j], b["eta"][j] = pt, eta
        w = random.choice([1.0, 1.0, 1.0, -1.0, 0.5, 2.5]) * 123.456
        b["w"][0] = w
        sumw += f32(w)
        sumw2 += f32(w) * f32(w)
        b["gt"][0] = random.choice(codes)
        b["hlt"][0] = 1 if i % 3 else 0
        t.Fill()
        n += 1
    t.Write()
    r = ROOT.TTree("Runs", "Runs")
    r.SetAutoSave(0)
    rr, rc, rs, rs2 = array("I", [run]), array("q", [n]), array("d", [sumw]), array("d", [sumw2])
    r.Branch("run", rr, "run/i")
    if is_mc:
        r.Branch("genEventCount", rc, "genEventCount/L")
        r.Branch("genEventSumw", rs, "genEventSumw/D")
        r.Branch("genEventSumw2", rs2, "genEventSumw2/D")
    r.Fill()
    r.Write()
    lb = ROOT.TTree("LuminosityBlocks", "LuminosityBlocks")
    lr, ll = array("I", [run]), array("I", [0])
    lb.Branch("run", lr, "run/i")
    lb.Branch("luminosityBlock", ll, "luminosityBlock/i")
    for k in range(1 + (n - 1) // 50 if n else 0):
        ll[0] = 1 + k
        lb.Fill()
    lb.Write()
    f.Close()
    return n


def main():
    try:
        import ROOT
    except ImportError:
        print("FATAL: PyROOT not importable; run inside cmssw-el8 after cmsenv")
        return 4
    ROOT.gROOT.SetBatch(True)
    try:
        import PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor  # noqa: F401
    except ImportError as e:
        print("FATAL: NanoAODTools not importable (%s); run after cmsenv" % e)
        return 4
    if not shutil.which("haddnano.py"):
        print("FATAL: haddnano.py not in PATH; run after cmsenv")
        return 4
    tmp = tempfile.mkdtemp(prefix="test_forge_audit_root_")
    try:
        data = os.path.join(tmp, "data")
        os.makedirs(data)
        paths = {}
        for name, n, mc, kw in (("mc1", 3000, True, {}), ("mc2", 1500, True, {"seed": 2, "edges": False}),
                                ("mc_zero", 500, True, {"seed": 3, "edges": False, "pass_frac": 0.0}),
                                ("mc_empty", 0, True, {"edges": False}),
                                ("data1", 3000, False, {"seed": 4, "run": 381000})):
            paths[name] = os.path.join(data, name + ".root")
            make(ROOT, paths[name], n, mc, **kw)
        br_mc = os.path.join(data, "br_mc.txt")
        br_data = os.path.join(data, "br_data.txt")
        with open(br_mc, "w") as f:
            # keep LHE_*: a wildcard that matches nothing in these files, as in a pythia-only sample
            # (ZZ) with the 2024 MC list; ROOT then prints 'No branch name is matching wildcard'
            f.write("drop *\nkeep run\nkeep luminosityBlock\nkeep event\nkeep nJet\nkeep Jet_*\nkeep genWeight\n"
                    "keep genTtbarId\nkeep HLT_PFJet*\nkeep LHE_*\n")
        with open(br_data, "w") as f:
            f.write("drop *\nkeep run\nkeep luminosityBlock\nkeep event\nkeep nJet\nkeep Jet_*\nkeep HLT_PFJet*\n")

        def run(name, inputs, br, *extra):
            job = os.path.join(tmp, "jobs", name)
            os.makedirs(job)
            cmd = [sys.executable, os.path.join(SCRIPT, "run_postproc.py")] + inputs + \
                  ["-I", "modules.noop:MODULES", "-b", br, "-o", "forgedNtuple.root"] + list(extra)
            p = subprocess.run(cmd, cwd=job, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            checks = dict()
            for l in p.stdout.splitlines():
                if l.startswith("FORGE|CHECK|"):
                    parts = l.split("|")
                    checks.setdefault(parts[2], []).append(parts[3])
            return p.returncode, checks, p.stdout, p.stderr, os.path.join(job, "forgedNtuple.root")

        def readback(out, inp, *extra):
            p = subprocess.run([sys.executable, os.path.join(SCRIPT, "check_forge_output.py"), out, inp] + list(extra),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            return p.returncode, p.stdout

        def core_pass(checks):
            return all(checks.get(k) == ["PASS"] for k in ("C1", "C2", "C2e", "write"))

        rc, ck, out, err, o = run("mc1_6j20", [paths["mc1"]], br_mc, "--skim", "6j20", "--audit", "--forge-git", "t0")
        check("MC 6j20: exit 0, C1 C2 C2e write PASS, C2r C3 PASS", rc == 0 and core_pass(ck)
              and ck.get("C2r") == ["PASS"] and ck.get("C3") == ["PASS"] and "C2a" not in ck, (rc, ck, err[-600:]))
        check("MC 6j20: the wildcard keep LHE_* that matches nothing is C2w WARN, not a C2e error",
              ck.get("C2w") == ["WARN"] and "LHE_*" in out and ck.get("C2e") == ["PASS"]
              and "No branch name is matching wildcard -> LHE_*" in err, (ck, err[-600:]))
        rc2, txt = readback(o, paths["mc1"])
        check("MC 6j20 read-back: X7 event by event, A, K", rc2 == 0, txt[-800:])
        rc, ck, out, err, o = run("mc1_ht", [paths["mc1"]], br_mc, "--skim", "6j20ht400", "--audit")
        rc2, txt = readback(o, paths["mc1"])
        check("MC 6j20ht400 (NaN / inf edge events): exit 0 and read-back PASS", rc == 0 and core_pass(ck) and rc2 == 0,
              (rc, ck, txt[-800:]))
        for sk in ("6jcount", "6j25", "6j30"):
            rc, ck, out, err, o = run("mc1_" + sk, [paths["mc1"]], br_mc, "--skim", sk, "--audit")
            rc2, txt = readback(o, paths["mc1"])
            check("MC %s: exit 0 and read-back PASS" % sk, rc == 0 and core_pass(ck) and rc2 == 0, (rc, ck, txt[-400:]))
        rc, ck, out, err, o = run("data1", [paths["data1"]], br_data, "--skim", "6j20", "--audit")
        rc2, txt = readback(o, paths["data1"])
        check("Data 6j20: exit 0, no Runs checks, read-back PASS", rc == 0 and core_pass(ck) and "C3" not in ck
              and rc2 == 0, (rc, ck, txt[-400:]))
        rc, ck, out, err, o = run("data1_mclist", [paths["data1"]], br_mc, "--skim", "6j20", "--audit")
        check("Data with the MC list: exit 0, C2w WARN (genWeight, genTtbarId, LHE_*), C2e PASS",
              rc == 0 and ck.get("C2w") == ["WARN"] and ck.get("C2e") == ["PASS"] and "genWeight" in out
              and "LHE_*" in out,
              (rc, ck, err[-400:]))
        rc, ck, out, err, o = run("mc_zero", [paths["mc_zero"]], br_mc, "--skim", "6j20", "--audit")
        rc2, txt = readback(o, paths["mc_zero"])
        check("nothing passes: exit 0, C1 PASS with 0 events, read-back PASS", rc == 0 and core_pass(ck) and rc2 == 0,
              (rc, ck, txt[-400:]))
        rc, ck, out, err, o = run("mc_empty", [paths["mc_empty"]], br_mc, "--skim", "6j20", "--audit")
        check("empty input: exit 0", rc == 0 and core_pass(ck), (rc, ck, err[-400:]))
        rc, ck, out, err, o = run("mc1_range", [paths["mc1"]], br_mc, "--skim", "6j20", "--audit", "-N", "100",
                                  "--first-entry", "7")
        rc2, txt = readback(o, paths["mc1"], "-N", "100", "--first-entry", "7")
        check("-N 100 --first-entry 7: exit 0, C2r INFO, read-back of the same range PASS",
              rc == 0 and core_pass(ck) and ck.get("C2r") == ["INFO"] and rc2 == 0, (rc, ck, txt[-400:]))
        rc, ck, out, err, o2 = run("two", [paths["mc_zero"], paths["mc2"]], br_mc, "--skim", "6j20", "--audit")
        check("two inputs: exit 0, one ForgeAudit row each", rc == 0 and core_pass(ck), (rc, ck, err[-400:]))
        f = ROOT.TFile.Open(o2)
        check("two inputs: ForgeAudit 2 rows", f and f.Get("ForgeAudit") and int(f.Get("ForgeAudit").GetEntries()) == 2)
        f.Close()
        # a later merge of two job outputs keeps the audit (all TTrees)
        o_a = os.path.join(tmp, "jobs", "mc1_6j20", "forgedNtuple.root")
        o_b = os.path.join(tmp, "jobs", "mc1_ht", "forgedNtuple.root")
        merged = os.path.join(tmp, "merged.root")
        p = subprocess.run(["haddnano.py", merged, o_a, o_b], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        f = ROOT.TFile.Open(merged)
        n = dict((k, int(f.Get(k).GetEntries()) if f and f.Get(k) else -1)
                 for k in ("ForgeAudit", "ForgeProvenance", "ForgeTTbbKeys", "Events"))
        fa, fb = ROOT.TFile.Open(o_a), ROOT.TFile.Open(o_b)
        want_keys = int(fa.Get("ForgeTTbbKeys").GetEntries()) + int(fb.Get("ForgeTTbbKeys").GetEntries())
        want_ev = int(fa.Get("Events").GetEntries()) + int(fb.Get("Events").GetEntries())
        check("haddnano.py merge: ForgeAudit 2, ForgeProvenance 2, keys and Events summed",
              p.returncode == 0 and n["ForgeAudit"] == 2 and n["ForgeProvenance"] == 2 and n["ForgeTTbbKeys"] == want_keys
              and n["Events"] == want_ev, (p.returncode, n, want_keys, want_ev, p.stdout[-300:]))
        if f and f.Get("ForgeProvenance"):
            t = f.Get("ForgeProvenance")
            t.GetEntry(0)
            check("merged ForgeProvenance row 0 is json with the skim", json.loads(str(t.json)).get("skim") == "6j20",
                  str(t.json)[:200])
        # the command line of the 2018UL production: no new flag, nothing new happens
        rc, ck, out, err, o = run("old", [paths["mc1"]], br_mc)
        f = ROOT.TFile.Open(o)
        check("no --skim / --audit: exit 0, all events, no ForgeAudit, no FORGE lines",
              rc == 0 and not ck and f and not f.Get("ForgeAudit") and int(f.Get("Events").GetEntries()) == 3015,
              (rc, ck, err[-300:]))
    except Exception:              # a broken case must still end in a RESULT line
        import traceback
        check("the test ran to the end", False, traceback.format_exc()[-800:])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_fail = RESULTS.count(False)
    print("RESULT: %s (%d checks)" % ("ALL PASS" if n_fail == 0 else "%d FAILED" % n_fail, len(RESULTS)))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
