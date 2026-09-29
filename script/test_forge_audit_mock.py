#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_forge_audit_mock.py -- offline test of the NtupleForge event skim and
audit: script/forge_skims.py, script/forge_audit.py, the --skim / --audit /
--forge-git options of script/run_postproc.py and the capture echo in
crab/crab_script.py.

Nothing real runs: the real run_postproc.py is started as a child process with
a mock ROOT module and a mock NanoAODTools PostProcessor in front of
PYTHONPATH. Both keep their "files" as JSON documents in a temp dir. The mock
RDataFrame knows exactly the expressions forge_audit.py uses (a new or changed
expression fails the test until the mock learns it, on purpose) and counts
event loops, so booking a result after the loop ran shows up. What this
checks: control flow, bookkeeping, closure logic, exit codes, FORGE lines,
the ROOT error-line rule (also for a child process such as haddnano.py), the
written objects, argument validation, and that a command line without --skim
/ --audit neither needs nor imports the new files. What it cannot check:
ROOT itself (RDataFrame, TTreeFormula, PyROOT branch types). That is P5 on
lxplus: real files, where C1 compares the TTreeFormula and RVec selections.

    python3 script/test_forge_audit_mock.py        # last line: RESULT: ALL PASS (N checks)

Needs python3 >= 3.6 only (no ROOT, no numpy, no PyYAML). ASCII only.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "script")
RUN_POSTPROC = os.path.join(SCRIPT, "run_postproc.py")
CRAB_SCRIPT = os.path.join(REPO, "crab", "crab_script.py")

# ---------------------------------------------------------------------------
# the Python meaning of every expression forge_audit.py / forge_skims.py use
# ---------------------------------------------------------------------------
EXPR_PY = r'''
def _nj(ev, ptmin):
    return sum(1 for p, e in zip(ev["Jet_pt"], ev["Jet_eta"]) if p > ptmin and abs(e) < 2.5)

def _ht(ev, ptmin):
    return sum(p for p, e in zip(ev["Jet_pt"], ev["Jet_eta"]) if p > ptmin and abs(e) < 2.5)

SKIM_PY = {
    "6jcount": lambda ev: sum(1 for e in ev["Jet_eta"] if abs(e) < 2.5) >= 6,
    "6j20": lambda ev: _nj(ev, 20) >= 6,
    "6j25": lambda ev: _nj(ev, 25) >= 6,
    "6j30": lambda ev: _nj(ev, 30) >= 6,
    "6j20ht400": lambda ev: _nj(ev, 20) >= 6 and _ht(ev, 20) > 400,
}

def code_index(i):
    return 0 if i < 0 else 1 + i % 100

def expressions(forge_skims):
    """{expression string: function(event dict) -> value} for the mock RDF and PostProcessor."""
    out = {
        "(int)Sum(Jet_pt>20 && abs(Jet_eta)<2.5)": lambda ev: _nj(ev, 20),
        "forge_ht(Jet_pt, Jet_eta, 20., 2.5)": lambda ev: _ht(ev, 20),
        "true": lambda ev: True,
        "forge_pass": lambda ev: bool(ev["forge_pass"]),
        "(double)genWeight": lambda ev: float(ev["genWeight"]),
        "forge_w*forge_w": lambda ev: ev["forge_w"] * ev["forge_w"],
        "genWeight < 0": lambda ev: ev["genWeight"] < 0,
        "forge_code_index(genTtbarId)": lambda ev: code_index(ev["genTtbarId"]),
        "genTtbarId >= 0 && genTtbarId % 100 >= 53 && genTtbarId % 100 <= 55":
            lambda ev: ev["genTtbarId"] >= 0 and 53 <= ev["genTtbarId"] % 100 <= 55,
    }
    for name, formula, rvec in forge_skims.SKIMS:
        out["(bool)(%s)" % rvec] = SKIM_PY[name]
        out[formula] = SKIM_PY[name]          # the PostProcessor cut
    return out
'''

# ---------------------------------------------------------------------------
# mock ROOT: JSON files, TTree reading / writing, TObjString, RDataFrame
# ---------------------------------------------------------------------------
MOCK_ROOT = r'''
import json, os, sys
sys.path.insert(0, os.environ["MOCK_DIR"])
import mock_expr, forge_skims
EXPR = mock_expr.expressions(forge_skims)
LOG = os.environ.get("MOCK_LOG")

def _log(*a):
    if LOG:
        with open(LOG, "a") as f:
            f.write(" ".join(str(x) for x in a) + "\n")

class _Named(object):
    def __init__(self, n):
        self.n = n
    def GetName(self):
        return self.n

class _ReadTree(object):
    def __init__(self, doc, name):
        self.doc, self.name = doc, name
        self.rows = doc[name]["events"] if name == "Events" else doc[name]
    def GetEntries(self):
        return len(self.rows)
    def GetAutoSave(self):
        return int(os.environ.get("MOCK_AUTOSAVE", "0")) if self.name == "Events" else 0
    def GetListOfBranches(self):
        if self.name == "Events" and self.doc["Events"].get("branches"):
            return [_Named(b) for b in self.doc["Events"]["branches"]]
        return [_Named(k) for k in (self.rows[0] if self.rows else {})]
    def GetEntry(self, i):
        for k, v in self.rows[i].items():
            setattr(self, k, v)
        return 1

class _String(object):
    def __init__(self, s=""):
        self.s = s
    def assign(self, s):
        self.s = str(s)

class _Std(object):
    string = _String
std = _Std()

class TObjString(object):
    def __init__(self, s):
        self.s = s
    def GetString(self):
        return self.s

kPrint, kInfo, kWarning, kError = 0, 1000, 2000, 3000
gErrorIgnoreLevel = -1

class _GROOT(object):
    def SetBatch(self, b=True):
        pass
    def GetVersion(self):
        return "6.30/mock"
gROOT = _GROOT()

class TFile(object):
    kWriteError = 1 << 14
    CURRENT = [None]
    def __init__(self, path, mode):
        self.path, self.mode, self.closed = path, mode, False
        self.doc = {}
        if mode in ("", "READ", "UPDATE"):
            with open(path) as f:
                self.doc = json.load(f)
        TFile.CURRENT[0] = self
    @staticmethod
    def Open(path, mode=""):
        if mode in ("", "READ", "UPDATE") and not os.path.exists(path):
            print("Error in <TFile::TFile>: file %s does not exist" % path, file=sys.stderr)
            return None
        if os.environ.get("MOCK_OPENFAIL") and os.environ["MOCK_OPENFAIL"] in path and mode == "":
            return None
        return TFile(path, mode)
    def IsZombie(self):
        return False
    def cd(self):
        TFile.CURRENT[0] = self
    def Get(self, name):
        if name not in self.doc:
            return None
        if isinstance(self.doc[name], str):
            return TObjString(self.doc[name])
        return _ReadTree(self.doc, name)
    def WriteTObject(self, obj, name):
        self.doc[name] = obj.s
    def TestBit(self, bit):
        return bit == TFile.kWriteError and self.mode == "UPDATE" and bool(os.environ.get("MOCK_WRITEERR"))
    def Close(self):
        if self.closed:
            return
        self.closed = True
        if self.mode in ("UPDATE", "RECREATE"):
            with open(self.path, "w") as f:
                json.dump(self.doc, f)

class TTree(object):
    def __init__(self, name, title=""):
        self.name, self.file, self.bufs, self.rows = name, TFile.CURRENT[0], [], []
    def Branch(self, name, buf, leaf=None):
        self.bufs.append((name, buf, leaf))
    def SetAutoSave(self, n):
        self.autosave = n
    def Fill(self):
        row = {}
        for name, buf, leaf in self.bufs:
            if isinstance(buf, _String):
                row[name] = buf.s
            elif leaf and "[" in leaf:
                row[name] = list(buf)
            else:
                row[name] = buf[0]
        self.rows.append(row)
    def Write(self):
        self.file.doc[self.name] = self.rows

class _Interp(object):
    def Declare(self, code):
        _log("declare", len(code))
        return True
gInterpreter = _Interp()

class _Result(object):
    def __init__(self, root, fn):
        self.root, self.fn, self.done, self.value = root, fn, False, None
        root.booked.append(self)
    def GetValue(self):
        if not self.done:
            self.root.run()
        return self.value

class _Hist(object):
    def __init__(self, n, lo, hi):
        self.n, self.lo, self.hi, self.c = n, lo, hi, [0.0] * (n + 2)
    def fill(self, x, w=1.0):
        b = 0 if x < self.lo else (self.n + 1 if x >= self.hi else 1 + int((x - self.lo) * self.n / (self.hi - self.lo)))
        self.c[b] += w
    def GetBinContent(self, i):
        return self.c[i]

class _Root(object):
    def __init__(self, path, treename="Events"):
        with open(path) as f:
            doc = json.load(f)
        self.events = doc["Events"]["events"] if treename == "Events" else doc[treename]
        if os.environ.get("MOCK_RDF_SHORT"):
            self.events = self.events[:-1]          # a read that stops early
        self.booked, self.loops, self.path = [], 0, path
    def run(self):
        self.loops += 1
        _log("loop", os.path.basename(self.path), self.loops)
        if os.environ.get("MOCK_RDF_RAISE"):
            raise RuntimeError("mock: RDataFrame event loop failed")
        if os.environ.get("MOCK_RDF_ROOTERR"):
            os.write(2, b"Error in <TBranch::GetBasket>: File: mock.root at byte:0, branch:Jet_pt, entry:3\n")
        for r in self.booked:
            if not r.done:
                r.value, r.done = r.fn(), True

class _Node(object):
    def __init__(self, root, ops):
        self.root, self.ops = root, ops
    def _rows(self):
        rows = [dict(e) for e in self.root.events]
        for op in self.ops:
            kind = op[0]
            if kind == "range":
                b, e = op[1], op[2]
                rows = rows[b:(e if e else None)]
            elif kind == "define":
                f = EXPR[op[2]]
                for r in rows:
                    r[op[1]] = f(r)
            elif kind == "filter":
                f = EXPR[op[1]]
                rows = [r for r in rows if f(r)]
        return rows
    def Range(self, *a):
        b, e = (0, a[0]) if len(a) == 1 else (a[0], a[1])
        return _Node(self.root, self.ops + [("range", b, e)])
    def Define(self, name, expr):
        if expr not in EXPR:
            raise KeyError("mock RDF: unknown expression %r" % expr)
        return _Node(self.root, self.ops + [("define", name, expr)])
    def Filter(self, expr):
        if expr not in EXPR:
            raise KeyError("mock RDF: unknown filter %r" % expr)
        return _Node(self.root, self.ops + [("filter", expr)])
    def Count(self):
        return _Result(self.root, lambda: len(self._rows()))
    def Sum(self, col):
        return _Result(self.root, lambda: float(sum(r[col] for r in self._rows())))
    def Histo1D(self, model, col, wcol=None):
        def fill():
            h = _Hist(model[2], model[3], model[4])
            for r in self._rows():
                h.fill(r[col], r[wcol] if wcol else 1.0)
            return h
        return _Result(self.root, fill)
    def AsNumpy(self, cols, lazy=False):
        res = _Result(self.root, lambda: dict((c, [r[c] for r in self._rows()]) for c in cols))
        return res if lazy else res.GetValue()

ROOTS = []
def RDataFrame(treename, path):
    r = _Root(path, treename)
    ROOTS.append(r)
    import atexit
    return _Node(r, [])
'''

MOCK_PP = r'''
import importlib.util, json, os, sys, subprocess
sys.path.insert(0, os.environ["MOCK_DIR"])
import mock_expr
# the skim table under another module name, from its real path, so that
# run_postproc.py itself still cannot import forge_skims where it is absent
_spec = importlib.util.spec_from_file_location("mock_pp_skim_table", os.environ["MOCK_SKIMS_FILE"])
_table = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_table)
EXPR = mock_expr.expressions(_table)

class PostProcessor(object):
    def __init__(self, outputDir, inputFiles, cut=None, branchsel=None, modules=[], compression="LZMA:9",
                 friend=False, postfix=None, noOut=False, justcount=False, maxEntries=None, firstEntry=0,
                 haddFileName=None, provenance=False, fwkJobReport=False, outputbranchsel=None, **kw):
        self.inputs, self.cut, self.out = inputFiles, cut, haddFileName
        self.maxEntries, self.firstEntry = maxEntries, firstEntry
        with open(os.environ["MOCK_PP_LOG"], "a") as f:
            f.write(json.dumps({"cut": cut, "out": haddFileName, "inputs": inputFiles,
                                "forge_modules": sorted(m for m in sys.modules if m.startswith("forge_"))}) + "\n")
    def run(self):
        if os.environ.get("MOCK_PP_RAISE"):
            raise RuntimeError("mock PostProcessor: cannot open input")
        if os.environ.get("MOCK_PP_ROOTERR"):
            os.write(2, b"Error in <TNetXNGFile::ReadBuffer>: [ERROR] Server responded with an error: [3005] I/O limit exceeded\n")
        if os.environ.get("MOCK_PP_BENIGN"):            # a keep pattern that matches nothing in this file
            os.write(2, b"Error in <TTree::SetBranchStatus>: unknown branch -> LHEPdfWeight\n")
            os.write(2, b"Error in <TTree::SetBranchStatus>: No branch name is matching wildcard -> LHE_*\n")
        if os.environ.get("MOCK_PP_CHILDERR"):          # like haddnano.py, a child process writing to fd 2
            os.system("echo 'Error in <TTree::Merge>: from a child process' 1>&2")
        events, runs = [], []
        for p in self.inputs:
            with open(p) as f:
                doc = json.load(f)
            ev = doc["Events"]["events"]
            b = self.firstEntry or 0
            ev = ev[b:(b + self.maxEntries) if self.maxEntries else None]
            if self.cut:
                ev = [e for e in ev if EXPR[self.cut](e)]
            events += ev
            runs += doc.get("Runs", [])
        if os.environ.get("MOCK_PP_DROP") and events:
            events = events[:-1]
        print("Selected %d entries (mock PostProcessor)" % len(events))
        if self.out:
            with open(self.out, "w") as f:
                json.dump({"Events": {"branches": [], "events": events}, "Runs": runs}, f)
'''

MOCK_CMS = r'''
class _V(list):
    pass
class _Obj(object):
    def __init__(self, *a, **kw):
        for k, v in kw.items():
            setattr(self, k, v)
class untracked(object):
    vstring = staticmethod(lambda *a: _V(a))
    int32 = staticmethod(lambda x: x)
    string = staticmethod(lambda x: x)
    PSet = _Obj
Process = lambda name: _Obj()
Source = lambda kind, **kw: _Obj(**kw)
OutputModule = lambda kind, **kw: _Obj(**kw)
EndPath = lambda *a: _Obj()
'''

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   -> %s" % (detail,)))


def write_json(path, doc):
    with open(path, "w") as f:
        json.dump(doc, f)


def jets(n, pt, eta=0.5):
    return {"nJet": n, "Jet_pt": [pt - 3 * i for i in range(n)], "Jet_eta": [eta] * n}


def make_mc(path, gtids, nj, weights, runs_sumw=None, runs_count=None):
    events = []
    for i, (g, n, w) in enumerate(zip(gtids, nj, weights)):
        e = {"run": 1, "luminosityBlock": 7 + i // 3, "event": 1000 + i, "genWeight": w, "genTtbarId": g}
        e.update(jets(n, 60.0))
        events.append(e)
    sw = sum(weights) if runs_sumw is None else runs_sumw
    doc = {"Events": {"branches": ["run", "luminosityBlock", "event", "nJet", "Jet_pt", "Jet_eta", "genWeight",
                                   "genTtbarId"], "events": events},
           "Runs": [{"genEventCount": len(events) if runs_count is None else runs_count, "genEventSumw": sw,
                     "genEventSumw2": sum(x * x for x in weights)}]}
    write_json(path, doc)
    return events


def make_data(path, nj):
    events = []
    for i, n in enumerate(nj):
        e = {"run": 315300, "luminosityBlock": 40 + i, "event": 5000 + i}
        e.update(jets(n, 70.0))
        events.append(e)
    write_json(path, {"Events": {"branches": ["run", "luminosityBlock", "event", "nJet", "Jet_pt", "Jet_eta"],
                                 "events": events}, "Runs": [{"run": 315300}]})
    return events


def main():
    tmp = tempfile.mkdtemp(prefix="test_forge_audit_")
    try:
        mock = os.path.join(tmp, "mock")
        os.makedirs(os.path.join(mock, "PhysicsTools", "NanoAODTools", "postprocessing", "framework"))
        for d in ("PhysicsTools", "PhysicsTools/NanoAODTools", "PhysicsTools/NanoAODTools/postprocessing",
                  "PhysicsTools/NanoAODTools/postprocessing/framework"):
            open(os.path.join(mock, d, "__init__.py"), "w").close()
        with open(os.path.join(mock, "PhysicsTools/NanoAODTools/postprocessing/framework/postprocessor.py"), "w") as f:
            f.write(MOCK_PP)
        with open(os.path.join(mock, "ROOT.py"), "w") as f:
            f.write(MOCK_ROOT)
        with open(os.path.join(mock, "mock_expr.py"), "w") as f:
            f.write(EXPR_PY)
        os.makedirs(os.path.join(mock, "FWCore", "ParameterSet"))
        open(os.path.join(mock, "FWCore", "__init__.py"), "w").close()
        open(os.path.join(mock, "FWCore", "ParameterSet", "__init__.py"), "w").close()
        with open(os.path.join(mock, "FWCore", "ParameterSet", "Config.py"), "w") as f:
            f.write(MOCK_CMS)
        work = os.path.join(tmp, "work")
        os.makedirs(work)
        modules = os.path.join(work, "modules")
        os.makedirs(modules)
        open(os.path.join(modules, "__init__.py"), "w").close()
        with open(os.path.join(modules, "noop.py"), "w") as f:
            f.write("MODULES = []\n")
        branch = os.path.join(work, "branch_test.txt")
        with open(branch, "w") as f:
            f.write("drop *\nkeep run\nkeep luminosityBlock\nkeep event\nkeep Jet_*\n")
        log = os.path.join(tmp, "mock_log.txt")
        pp_log = os.path.join(tmp, "pp_log.txt")

        sys.path.insert(0, SCRIPT)
        import forge_skims
        # 1. one table: the formulas are those size_options.py measured (its row signatures depend on them)
        spec = importlib.util.spec_from_file_location("size_options_mod", os.path.join(SCRIPT, "size_options.py"))
        so = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(so)
        check("forge_skims formulas == size_options.py SKIMS (names and strings)",
              [(n, f) for n, f, _ in forge_skims.SKIMS] == list(so.SKIMS), (forge_skims.SKIMS, so.SKIMS))
        check("forge_skims names: none + the five", forge_skims.NAMES == ["none", "6jcount", "6j20", "6j25", "6j30",
                                                                          "6j20ht400"], forge_skims.NAMES)
        try:
            forge_skims.get("6j21")
            ok = False
        except KeyError:
            ok = True
        check("forge_skims.get: unknown name raises KeyError", ok)
        for path in (os.path.join(SCRIPT, "forge_skims.py"), os.path.join(SCRIPT, "forge_audit.py"), __file__):
            with open(path, "rb") as f:
                check("ASCII only: %s" % os.path.basename(path), all(b < 128 for b in bytearray(f.read())))

        def env(**kw):
            e = dict(os.environ)
            e["PYTHONPATH"] = mock + os.pathsep + SCRIPT + (os.pathsep + e["PYTHONPATH"] if e.get("PYTHONPATH") else "")
            e["MOCK_DIR"] = mock
            e["MOCK_LOG"] = log
            e["MOCK_PP_LOG"] = pp_log
            e["MOCK_SKIMS_FILE"] = os.path.join(SCRIPT, "forge_skims.py")
            for k in list(e):
                if k.startswith("MOCK_") and k not in ("MOCK_DIR", "MOCK_LOG", "MOCK_PP_LOG", "MOCK_SKIMS_FILE"):
                    del e[k]
            e.update(kw)
            return e

        def run(inputs, *extra, **kw):
            for p in (log, pp_log, os.path.join(work, "out.root")):
                if os.path.exists(p):
                    os.remove(p)
            cmd = [sys.executable, kw.pop("script", RUN_POSTPROC)] + inputs + \
                  ["-I", "modules.noop:MODULES", "-b", branch] + list(extra)
            p = subprocess.run(cmd, cwd=work, env=env(**kw), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
            return p.returncode, p.stdout, p.stderr

        def out_doc():
            with open(os.path.join(work, "out.root")) as f:
                return json.load(f)

        def prov_of(d):
            rows = d.get("ForgeProvenance") or [{}]
            return json.loads(rows[0].get("json", "{}"))

        def forge(out, kind):
            return [l for l in out.splitlines() if l.startswith("FORGE|%s|" % kind)]

        def loops():
            if not os.path.exists(log):
                return {}
            n = {}
            for l in open(log).read().splitlines():
                if l.startswith("loop "):
                    _, f, k = l.split()
                    n[f] = max(n.get(f, 0), int(k))
            return n

        # MC inputs: 12 + 9 events; genTtbarId codes incl. 53..55 and one negative id
        a = os.path.join(work, "mc_a.root")
        b = os.path.join(work, "mc_b.root")
        ga = [0, 53, 10154, 55, 5, 54, 0, -1, 1053, 53, 51, 0]
        na = [6, 7, 5, 8, 6, 3, 9, 6, 6, 2, 7, 6]
        wa = [1.0, 1.0, -1.0, 2.0, 1.0, 1.0, 1.0, 0.5, 1.0, 1.0, -0.5, 1.0]
        ea = make_mc(a, ga, na, wa)
        gb = [55, 0, 0, 54, 53, 0, 10000, 0, 45]
        nb = [6, 6, 4, 6, 9, 1, 6, 6, 6]
        wb = [1.0] * 9
        eb = make_mc(b, gb, nb, wb)
        sk = forge_skims.get("6j20")[0]
        pass_py = lambda ev: sum(1 for p, e in zip(ev["Jet_pt"], ev["Jet_eta"]) if p > 20 and abs(e) < 2.5) >= 6
        want_pass = sum(1 for e in ea + eb if pass_py(e))

        # 2. the production command line: two MC files
        rc, out, err = run([a, b], "-o", "out.root", "--skim", "6j20", "--audit", "--forge-git", "abc123def456")
        check("MC skim + audit: exit 0", rc == 0, (rc, out[-800:], err[-800:]))
        d = out_doc() if rc == 0 else {}
        pp = [json.loads(l) for l in open(pp_log).read().splitlines()] if os.path.exists(pp_log) else []
        check("the PostProcessor got the 6j20 formula as cut", len(pp) == 1 and pp[0]["cut"] == sk, pp)
        check("output Events = events passing 6j20 (%d)" % want_pass,
              len(d.get("Events", {}).get("events", [])) == want_pass, len(d.get("Events", {}).get("events", [])))
        rows = d.get("ForgeAudit", [])
        check("ForgeAudit: one row per input file", len(rows) == 2, rows)
        if len(rows) == 2:
            r0, r1 = rows
            check("ForgeAudit n_in / n_tree / n_pass", (r0["n_in"], r0["n_tree"], r1["n_in"]) == (12, 12, 9)
                  and r0["n_pass"] + r1["n_pass"] == want_pass, (r0, r1))
            check("ForgeAudit sums of genWeight, of its square, negative count",
                  abs(r0["sumw"] - sum(wa)) < 1e-12 and abs(r0["sumw2"] - sum(w * w for w in wa)) < 1e-12
                  and r0["n_neg"] == 2, (r0["sumw"], r0["sumw2"], r0["n_neg"]))
            check("ForgeAudit sumw over passing events",
                  abs(r0["sumw_pass"] - sum(e["genWeight"] for e in ea if pass_py(e))) < 1e-12, r0["sumw_pass"])
            cn, cw = r0["code_n"], r0["code_sumw"]
            check("ForgeAudit code arrays: 101 entries, index 0 = negative id, 1+c = code c",
                  len(cn) == 101 and cn[0] == 1 and cn[1 + 53] == 3 and cn[1 + 54] == 2 and cn[1 + 55] == 1
                  and cn[1 + 0] == 3 and sum(cn) == 12 and abs(cw[1 + 54] - (-1.0 + 1.0)) < 1e-12
                  and abs(cw[0] - 0.5) < 1e-12, (cn, cw))
            check("ForgeAudit Runs sums and file name", r0["runs_count"] == 12 and abs(r0["runs_sumw"] - sum(wa)) < 1e-12
                  and r0["file"] == a, (r0["runs_count"], r0["runs_sumw"], r0["file"]))
            check("ForgeAudit is_mc, entry range", r0["is_mc"] == 1 and r0["first_entry"] == 0 and r0["max_entries"] == 0,
                  r0)
        keys = d.get("ForgeTTbbKeys", [])
        want_keys = [e for e in ea + eb if e["genTtbarId"] >= 0 and 53 <= e["genTtbarId"] % 100 <= 55]
        check("ForgeTTbbKeys: every event with code 53..55 (incl. 1053, 10154), with its pass flag",
              [(k["event"], k["genTtbarId"], k["pass"]) for k in keys] ==
              [(e["event"], e["genTtbarId"], 1 if pass_py(e) else 0) for e in want_keys], keys)
        prov = prov_of(d)
        check("ForgeProvenance tree: one row; skim, git columns",
              len(d.get("ForgeProvenance", [])) == 1 and d["ForgeProvenance"][0].get("skim") == "6j20"
              and d["ForgeProvenance"][0].get("git") == "abc123def456", d.get("ForgeProvenance"))
        check("ForgeProvenance json: skim, formula, rvec, git, branch file md5, inputs",
              prov.get("skim") == "6j20" and prov.get("formula") == sk and prov.get("rvec") == forge_skims.get("6j20")[1]
              and prov.get("git") == "abc123def456" and len(prov.get("branch_md5", "")) == 32
              and prov.get("inputs") == [a, b], prov)
        check("FORGE lines: EVT for the first file only (12 <= 20), FILE x2, JOB exit=0",
              len(forge(out, "EVT")) == 12 and len(forge(out, "FILE")) == 2 and forge(out, "JOB")
              and forge(out, "JOB")[-1].endswith("exit=0"), (forge(out, "EVT")[:2], forge(out, "JOB")))
        evt0 = forge(out, "EVT")[0] if forge(out, "EVT") else ""
        check("FORGE EVT line: key, nj20, ht20, pass, gtid",
              evt0 == "FORGE|EVT|1:7:1000|nj20=6|ht20=%.2f|pass=1|gtid=0" % sum(60.0 - 3 * i for i in range(6)), evt0)
        chk = dict((l.split("|")[2], l.split("|")[3]) for l in forge(out, "CHECK"))
        check("closure C1 C2 C2e PASS, C2r C3 PASS for both files, write PASS",
              chk.get("C1") == "PASS" and chk.get("C2") == "PASS" and chk.get("C2e") == "PASS"
              and chk.get("C3") == "PASS" and chk.get("C2r") == "PASS" and chk.get("write") == "PASS",
              forge(out, "CHECK"))
        check("one event loop per input file (every result booked before the loop runs)",
              loops() == {"mc_a.root": 1, "mc_b.root": 1}, loops())
        check("the capture file is gone after a clean run", not os.path.exists(os.path.join(work, "forge_stderr.txt")))

        # 3. Data: no gen branches
        c = os.path.join(work, "data_c.root")
        ec = make_data(c, [6, 7, 2, 6, 5, 6])
        rc, out, err = run([c], "-o", "out.root", "--skim", "6j20", "--audit")
        d = out_doc() if rc == 0 else {}
        rows = d.get("ForgeAudit", [])
        check("Data: exit 0, is_mc 0, zero sums, no ForgeTTbbKeys, no Runs checks",
              rc == 0 and len(rows) == 1 and rows[0]["is_mc"] == 0 and rows[0]["sumw"] == 0.0
              and "ForgeTTbbKeys" not in d and not [l for l in forge(out, "CHECK") if "|C3|" in l or "|C2r|" in l],
              (rc, rows, forge(out, "CHECK"), err[-500:]))
        check("Data: n_pass = events passing 6j20", rows and rows[0]["n_pass"] == sum(1 for e in ec if pass_py(e)),
              rows)
        check("Data: the write line says no ForgeTTbbKeys", "no ForgeTTbbKeys (no genTtbarId)" in out,
              [l for l in forge(out, "CHECK") if "|write|" in l])

        # 4. C1: the output misses an event the RVec expression passes
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_PP_DROP="1")
        d = out_doc() if os.path.exists(os.path.join(work, "out.root")) else {}
        check("C1 FAIL: exit 5, no audit objects written",
              rc == 5 and "FORGE|CHECK|C1|FAIL" in out and "ForgeAudit" not in d, (rc, forge(out, "CHECK")))

        # 5. a ROOT error line while NanoAODTools copies
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_PP_ROOTERR="1")
        check("ROOT error line during the copy: exit 85 (CRAB retries), C2e FAIL, the line reaches stderr live",
              rc == 85 and "FORGE|CHECK|C2e|FAIL" in out and "[3005] I/O limit exceeded" in err, (rc, out[-400:], err[-400:]))

        # 5b. keep patterns matching nothing (SetBranchStatus: a plain name and a wildcard): WARN, not a read error
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_PP_BENIGN="1")
        check("SetBranchStatus 'unknown branch' and 'No branch name is matching wildcard' lines: exit 0, C2e PASS, "
              "C2w WARN naming both patterns",
              rc == 0 and "FORGE|CHECK|C2e|PASS" in out and "FORGE|CHECK|C2w|WARN" in out and "LHEPdfWeight" in out
              and "LHE_*" in out, (rc, forge(out, "CHECK")))
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_PP_BENIGN="1", MOCK_PP_ROOTERR="1")
        check("... together with a real read error line: exit 85", rc == 85 and "FORGE|CHECK|C2e|FAIL" in out,
              (rc, forge(out, "CHECK")))

        # 5c. an input whose Events tree autosaves (central NanoAOD writes 0): a WARN that explains a C1 FAIL
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_AUTOSAVE="-200000")
        check("input Events autosave != 0: C2a WARN, exit 0 while C1 holds", rc == 0 and "FORGE|CHECK|C2a|WARN" in out,
              (rc, forge(out, "CHECK")))

        # 6. ... written by a child process (haddnano.py runs as one)
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_PP_CHILDERR="1")
        check("ROOT error line from a child process: exit 85", rc == 85 and "from a child process" in err,
              (rc, err[-300:]))

        # 7. ... during the audit read
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_RDF_ROOTERR="1")
        check("ROOT error line during the audit read: exit 85", rc == 85 and "FORGE|CHECK|C2e|FAIL" in out,
              (rc, out[-300:]))

        # 8. NanoAODTools raises: exit 1 as before --audit existed
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_PP_RAISE="1")
        check("PostProcessor raises: exit 1, JOB exit=1", rc == 1 and forge(out, "JOB") and
              forge(out, "JOB")[-1].endswith("exit=1"), (rc, out[-300:], err[-300:]))

        # 9. the audit itself fails
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_RDF_RAISE="1")
        check("audit exception: exit 7, CHECK audit FAIL, capture file removed",
              rc == 7 and "FORGE|CHECK|audit|FAIL" in out and not os.path.exists(os.path.join(work, "forge_stderr.txt")),
              (rc, out[-300:]))
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_OPENFAIL="mc_a")
        check("input not openable by the audit: exit 84 (CRAB retries)", rc == 84 and "cannot open" in out,
              (rc, out[-300:]))

        # 10. a read that stops early
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_RDF_SHORT="1")
        check("audit read short of the range: exit 85, C2 FAIL", rc == 85 and "FORGE|CHECK|C2|FAIL" in out,
              (rc, forge(out, "CHECK")))

        # 11. -N: part of the file; Runs sums are not compared
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", "-N", "5")
        d = out_doc() if rc == 0 else {}
        rows = d.get("ForgeAudit", [])
        check("-N 5: exit 0, n_in 5, max_entries 5, C2r INFO, no C3",
              rc == 0 and rows and rows[0]["n_in"] == 5 and rows[0]["max_entries"] == 5
              and "FORGE|CHECK|C2r|INFO" in out and "|C3|" not in out, (rc, rows, forge(out, "CHECK")))
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", "-N", "5", "--first-entry", "4")
        d = out_doc() if rc == 0 else {}
        check("--first-entry 4 -N 5: the same range in the copy and the audit (C1 PASS)",
              rc == 0 and "FORGE|CHECK|C1|PASS" in out and d.get("ForgeAudit", [{}])[0].get("first_entry") == 4,
              (rc, forge(out, "CHECK")))

        # 12. Runs sums that disagree: WARN only (limits are set in P5)
        m = os.path.join(work, "mc_m.root")
        make_mc(m, ga, na, wa, runs_sumw=sum(wa) * 1.001, runs_count=13)
        rc, out, err = run([m], "-o", "out.root", "--skim", "6j20", "--audit")
        check("Runs sums differ: C3 WARN and C2r WARN, exit 0",
              rc == 0 and "FORGE|CHECK|C3|WARN" in out and "FORGE|CHECK|C2r|WARN" in out, (rc, forge(out, "CHECK")))

        # 13. audit without a skim: C1 compares with the entries read
        rc, out, err = run([a], "-o", "out.root", "--audit")
        d = out_doc() if rc == 0 else {}
        check("--audit without --skim: exit 0, cut None, every event kept, C1 PASS",
              rc == 0 and len(d.get("Events", {}).get("events", [])) == 12 and "FORGE|CHECK|C1|PASS" in out
              and prov_of(d).get("skim") == "none", (rc, forge(out, "CHECK")))
        rc, out, err = run([a], "-o", "out.root", "--skim", "none", "--audit")
        check("--skim none behaves as no skim", rc == 0 and "FORGE|CHECK|C1|PASS" in out, rc)

        # 14. every skim of the table runs (the mock knows each formula and rvec expression)
        for name in forge_skims.NAMES[1:]:
            rc, out, err = run([a, b], "-o", "out.root", "--skim", name, "--audit")
            check("skim %s: exit 0, C1 PASS" % name, rc == 0 and "FORGE|CHECK|C1|PASS" in out, (rc, out[-300:], err[-300:]))

        # 15. write error on the output (disk full)
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit", MOCK_WRITEERR="1")
        check("write error on the output: exit 1 (worker node; CRAB retries), CHECK write FAIL",
              rc == 1 and "FORGE|CHECK|write|FAIL" in out,
              (rc, out[-300:]))

        # 16. argument rules
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--cut", "nJet>3")
        check("--skim with --cut: exit 2", rc == 2 and "exclude each other" in err, (rc, err[-300:]))
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j21")
        check("--skim unknown: exit 2", rc == 2 and "unknown skim" in err, (rc, err[-300:]))
        rc, out, err = run([a], "--audit")
        check("--audit without --output-file: exit 2", rc == 2 and "needs --output-file" in err, (rc, err[-300:]))
        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20")
        check("--skim without --audit: exit 0, formula used, no FORGE lines, no audit objects",
              rc == 0 and not forge(out, "JOB") and "ForgeAudit" not in out_doc()
              and json.loads(open(pp_log).read().splitlines()[0])["cut"] == sk, (rc, out[-300:]))

        # 17. an old command line in a sandbox without the new files: runs, and imports neither
        if os.path.exists(pp_log):
            os.remove(pp_log)
        old = os.path.join(tmp, "old_repo", "script")      # run_postproc.py finds modules/ in its parent dir
        os.makedirs(old)
        shutil.copytree(modules, os.path.join(tmp, "old_repo", "modules"))
        shutil.copy(RUN_POSTPROC, os.path.join(old, "run_postproc.py"))
        e2 = env()
        e2["PYTHONPATH"] = mock + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
        p = subprocess.run([sys.executable, os.path.join(old, "run_postproc.py"), a, "-I", "modules.noop:MODULES",
                            "-b", branch, "-o", "out.root"], cwd=work, env=e2, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, universal_newlines=True)
        ppl = [json.loads(l) for l in open(pp_log).read().splitlines()] if os.path.exists(pp_log) else []
        check("no --skim / --audit, no forge files next to run_postproc.py: exit 0, no forge module imported",
              p.returncode == 0 and ppl and ppl[-1]["forge_modules"] == [] and "FORGE|" not in p.stdout,
              (p.returncode, ppl, p.stderr[-300:]))
        p = subprocess.run([sys.executable, os.path.join(old, "run_postproc.py"), a, "-I", "modules.noop:MODULES",
                            "-b", branch, "-o", "out.root", "--skim", "6j20"], cwd=work, env=e2,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        check("--skim without forge_skims.py next to run_postproc.py: exit 2 with the reason",
              p.returncode == 2 and "forge_skims.py is not importable" in p.stderr, (p.returncode, p.stderr[-300:]))

        # 18. the P5 read-back tool on outputs of one input file
        chk_tool = os.path.join(SCRIPT, "check_forge_output.py")

        def check_out(inp, *extra):
            p = subprocess.run([sys.executable, chk_tool, "out.root", inp] + list(extra), cwd=work, env=env(),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            return p.returncode, p.stdout

        def edit_out(fn):
            doc = out_doc()
            fn(doc)
            write_json(os.path.join(work, "out.root"), doc)

        rc, out, err = run([a], "-o", "out.root", "--skim", "6j20", "--audit")
        rc2, out2 = check_out(a)
        check("check_forge_output: MC 6j20 output -> X7, A, K PASS, exit 0",
              rc == 0 and rc2 == 0 and "X7   PASS" in out2 and "A    PASS" in out2 and "K    PASS" in out2, out2[-800:])
        edit_out(lambda d: d["Events"]["events"].pop(0))
        rc2, out2 = check_out(a)
        check("check_forge_output: an event (code 0) missing from the output -> X7 FAIL, K PASS, exit 1",
              rc2 == 1 and "X7   FAIL" in out2 and "K    PASS" in out2, out2[-600:])
        run([a], "-o", "out.root", "--skim", "6j20", "--audit")

        def drop_key_event(d):
            evs = d["Events"]["events"]
            i = [j for j, e in enumerate(evs) if e["genTtbarId"] >= 0 and 53 <= e["genTtbarId"] % 100 <= 55][0]
            evs.pop(i)
        edit_out(drop_key_event)
        rc2, out2 = check_out(a)
        check("check_forge_output: a passing code-53..55 event missing from the output -> X7 FAIL, K FAIL",
              rc2 == 1 and "X7   FAIL" in out2 and "K    FAIL" in out2, out2[-600:])
        run([a], "-o", "out.root", "--skim", "6j20", "--audit")
        edit_out(lambda d: d["ForgeTTbbKeys"][0].update({"pass": 1 - d["ForgeTTbbKeys"][0]["pass"]}))
        rc2, out2 = check_out(a)
        check("check_forge_output: a flipped pass flag in ForgeTTbbKeys -> K FAIL", rc2 == 1 and "K    FAIL" in out2,
              out2[-600:])
        run([a], "-o", "out.root", "--skim", "6j20", "--audit", "-N", "5", "--first-entry", "4")
        rc2, out2 = check_out(a, "-N", "5", "--first-entry", "4")
        check("check_forge_output: the same entry range (-N 5 --first-entry 4) -> ALL PASS", rc2 == 0, out2[-600:])
        run([c], "-o", "out.root", "--skim", "6j20", "--audit")
        rc2, out2 = check_out(c)
        check("check_forge_output: Data -> X7 A PASS, no keys expected", rc2 == 0 and "K    PASS" in out2, out2[-600:])
        run([a], "-o", "out.root", "--skim", "6j20")
        rc2, out2 = check_out(a)
        check("check_forge_output: an output without --audit -> exit 2", rc2 == 2, (rc2, out2[-300:]))

        # 19. crab_script.py prints the capture file when run_postproc.py dies inside the capture
        cs = os.path.join(tmp, "crab_job")
        os.makedirs(cs)
        shutil.copy(CRAB_SCRIPT, os.path.join(cs, "crab_script.py"))
        with open(os.path.join(cs, "PSet.py"), "w") as f:
            f.write("import FWCore.ParameterSet.Config as cms\nprocess = cms.Process('NANO')\n"
                    "process.source = cms.Source('PoolSource', fileNames=cms.untracked.vstring('/store/x.root'))\n")
        with open(os.path.join(cs, "run_postproc.py"), "w") as f:
            f.write("import sys\nopen('forge_stderr.txt', 'w').write('Error in <TTree::SetBranchStatus>: No branch name is "
                    "matching wildcard -> LHE_*\\nError in <TBranch::GetBasket>: the last words\\n')\n"
                    "sys.exit(9)\n")
        p = subprocess.run([sys.executable, "crab_script.py", "1"], cwd=cs, env=env(), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True)
        check("crab_script.py: exit code passed on, the capture file printed, a SetBranchStatus line not counted",
              p.returncode == 9 and "the last words" in p.stdout and "forge_stderr.txt" in p.stdout
              and "ROOT error lines (1 shown)" in p.stdout, (p.returncode, p.stdout[-600:]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_fail = RESULTS.count(False)
    print("RESULT: %s (%d checks)" % ("ALL PASS" if n_fail == 0 else "%d FAILED" % n_fail, len(RESULTS)))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
