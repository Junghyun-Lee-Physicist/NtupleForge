#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_size_options_mock.py -- offline test of script/size_options.py.

Runs the real script against the real crabConfigs, review tables and branch
lists of this repository, with a fake dasgoclient and a mock ROOT module put
in front of PATH / PYTHONPATH (both written to a temp dir). Nothing in the
repository is written: the TSV and the scratch files live in the temp dir.
It checks control flow and bookkeeping (mapping, DAS file choice, TSV resume,
signatures, failure handling, projection sums, era scaling, the per-branch
table and the pricing of the slim drafts in script/drafts/), not ROOT itself;
the mock gives exactly known sizes, so a real ROOT sneaking in fails the
number checks.

    python3 script/test_size_options_mock.py        # last line: RESULT: ALL PASS

Needs python3 with PyYAML (cmsenv has it). Python 3.6 compatible, ASCII only.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "script", "size_options.py")

FAKE_DAS = r'''#!/bin/bash
q="$2"
ds=$(echo "$q" | sed -E 's/^file dataset=([^ ]+).*/\1/')
tier=data; [[ "$ds" == */NANOAODSIM ]] && tier=mc
run=run3; [[ "$ds" == *13TeV* || "$ds" == *UL2018* ]] && run=run2
tag=$(echo "$ds" | tr -c 'A-Za-z0-9\n' '_' | cut -c1-40)
p="/store/${tier}/${run}/${tag}"
if [[ "$q" == *"grep file.name"* ]]; then
  echo "${p}/b_file.root 50000"
  echo "${p}/a_small.root 300"
  echo "${p}/c_file.root 70000"
else
  echo "${p}/a_small.root"
fi
'''

MOCK_ROOT = r'''
import fnmatch, os
kFatal = 6000
gErrorIgnoreLevel = 0
CUR = [None]
COMP, HDR_PER_BRANCH, FILE_HDR, NFILE = 0.3, 60, 2000, 60000
PASS = [("Jet_pt*(", 0.25), ("Jet_pt>20", 0.60), ("Jet_pt>25", 0.50), ("Jet_pt>30", 0.40),
        ("abs(Jet_eta)<2.5)>=6", 0.70)]
MOCK = True
def EnableImplicitMT(n):
    pass
class _R(object):
    def SetBatch(self, b):
        pass
gROOT = _R()
COUNTS = {"Jet_pt": "nJet", "Jet_eta": "nJet", "GenPart_pt": "nGenPart", "Photon_pt": "nPhoton",
          "OtherPV_z": "nOtherPV", "Muon_IPx": "nMuon", "Muon_jetDF": "nMuon", "Muon_pt": "nMuon",
          "LHEPart_pt": "nLHEPart", "LHEPdfWeight": "nLHEPdfWeight"}
def universe(url):
    run2 = "/run2/" in url
    b = {"run": 4, "luminosityBlock": 4, "event": 8, "nJet": 4, "Jet_pt": 60 if run2 else 40,
         "Jet_eta": 40, "PV_npvs": 4, "HLT_PFHT1050": 1, "HLT_IsoMu24": 1, "Photon_pt": 12,
         "nPhoton": 4, "nOtherPV": 4, "OtherPV_z": 8, "nMuon": 4, "Muon_IPx": 8, "Muon_jetDF": 8,
         "Muon_pt": 8}
    if "/mc/" in url:
        b.update({"genWeight": 4, "genTtbarId": 4, "nGenPart": 4, "GenPart_pt": 400,
                  "nLHEPart": 4, "LHEPart_pt": 100, "nLHEPdfWeight": 4, "LHEPdfWeight": 412})
    return b
class _Named(object):
    def __init__(self, n):
        self.n = n
    def GetName(self):
        return self.n
class _Leaf(object):
    def __init__(self, count):
        self.count = count
    def GetLeafCount(self):
        return _Named(self.count) if self.count else None
class _Leaves(list):
    def GetEntries(self):
        return len(self)
    def At(self, i):
        return self[i]
class Branch(object):
    def __init__(self, t, n):
        self.t, self.n = t, n
    def GetName(self):
        return self.n
    def GetListOfLeaves(self):
        return _Leaves([_Leaf(COUNTS.get(self.n, ""))])
    def GetZipBytes(self, o=""):
        return int(self.t.bpe[self.n] * self.t.entries * COMP)
class Tree(object):
    def __init__(self, bpe, entries):
        self.bpe, self.entries = dict(bpe), entries
        self.status = dict((k, 1) for k in bpe)
        self.written = False
    def GetEntries(self):
        return self.entries
    def SetBranchStatus(self, pat, st, found=None):
        for k in self.bpe:
            if fnmatch.fnmatchcase(k, pat):
                self.status[k] = 1 if st else 0
    def GetMinimum(self, col):
        return 15.0 if col in self.bpe and self.entries else 0.0
    def GetBranchStatus(self, name):
        return bool(self.status.get(name, 0))
    def GetListOfBranches(self):
        return [Branch(self, k) for k in self.bpe]
    def _active(self):
        return dict((k, v) for k, v in self.bpe.items() if self.status[k])
    def CopyTree(self, sel, opt="", n=None, first=0):
        if sel and os.environ.get("MOCK_BADSKIM"):
            return None
        ne = self.entries if n is None else min(n, self.entries)
        if sel:
            for s, f in PASS:
                if s in sel:
                    ne = int(round(ne * f))
                    break
        t = Tree(self._active(), ne)
        CUR[0].trees.append(t)
        return t
    def CloneTree(self, n=-1, opt=""):
        t = Tree(self._active(), 0 if n == 0 else self.entries)
        CUR[0].trees.append(t)
        return t
    def Write(self, *a):
        self.written = True
class TFile(object):
    OPEN = {}
    def __init__(self, path, mode="", title="", comp=101):
        self.path, self.mode, self.comp, self.trees, self.src, self.closed = path, mode, comp, [], None, False
        CUR[0] = self
    @staticmethod
    def Open(url, mode=""):
        bad = os.environ.get("MOCK_NOOPEN")
        if bad and bad in url:
            return None
        f = TFile(url, "READ", "", 209)
        f.src = Tree(universe(url), NFILE) if url.startswith("root://") else TFile.OPEN[url]
        return f
    def IsZombie(self):
        return False
    def cd(self):
        CUR[0] = self
    def Get(self, name):
        return self.src if name == "Events" else None
    def GetCompressionSettings(self):
        return self.comp
    def Close(self):
        if self.closed:
            return
        self.closed = True
        if self.mode != "RECREATE":
            return
        w = [t for t in self.trees if t.written]
        size = FILE_HDR + sum(HDR_PER_BRANCH * len(t.bpe) + int(sum(t.bpe.values()) * t.entries * COMP) for t in w)
        with open(self.path, "wb") as fh:
            fh.write(b"\0" * size)
        if w:
            TFile.OPEN[self.path] = Tree(w[0].bpe, w[0].entries)
'''

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   -> %s" % (detail,)))


def main():
    tmp = tempfile.mkdtemp(prefix="test_size_options_")
    try:
        os.makedirs(os.path.join(tmp, "bin"))
        os.makedirs(os.path.join(tmp, "mock"))
        das = os.path.join(tmp, "bin", "dasgoclient")
        with open(das, "w") as f:
            f.write(FAKE_DAS)
        os.chmod(das, 0o755)
        with open(os.path.join(tmp, "mock", "ROOT.py"), "w") as f:
            f.write(MOCK_ROOT)
        tsv = os.path.join(tmp, "meas.tsv")
        brtsv = os.path.join(tmp, "branches.tsv")
        work = os.path.join(tmp, "work")
        os.makedirs(work)
        env = dict(os.environ)
        env["PATH"] = os.path.join(tmp, "bin") + os.pathsep + env.get("PATH", "")
        env["PYTHONPATH"] = os.path.join(tmp, "mock") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        def run(*extra, **kw):
            e = dict(env)
            e.update(kw.get("env", {}))
            p = subprocess.run([sys.executable, SCRIPT, "--tsv", tsv, "--br-tsv", brtsv, "--workdir", work] + list(extra),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=e)
            return p.returncode, p.stdout

        def nrows():
            if not os.path.exists(tsv):
                return 0
            with open(tsv) as f:
                return len([l for l in f if l.strip()]) - 1

        def total(out):
            m = re.search(r"^TOTAL TB .*$", out, re.M)
            return m.group(0) if m else None

        with open(SCRIPT, "rb") as f:
            src = f.read()
        check("script is ASCII only", all(b < 128 for b in bytearray(src)))

        rc, out = run("--dry-run")
        lines = [l for l in out.splitlines() if re.search(r"\s/store/(mc|data)/run[23]/", l)]
        check("dry-run exits 0", rc == 0, (rc, out[-400:]))
        check("dry-run lists 34 samples", len(lines) == 34, len(lines))
        check("dry-run: no group without a planned measurement", " NONE" not in out and "NO DAS EVENTS" not in out)
        check("dry-run picks the first sorted file with >= n events (b_file, not a_small)",
              len(lines) == 34 and all(l.endswith("/b_file.root") for l in lines), lines[:2])
        check("dry-run writes no TSV", not os.path.exists(tsv))

        rc, out = run()
        t1 = total(out)
        check("full run exits 0", rc == 0, (rc, out[-600:]))
        check("full run: 34 TSV rows", nrows() == 34, nrows())
        check("full run: no FAILED / PARTIAL", "FAILED" not in out and "PARTIAL" not in out, out[-400:])
        check("full run prints TOTAL", t1 is not None)
        check("full run leaves no scratch file", os.listdir(work) == [], os.listdir(work))
        m = re.search(r"^2024\s+MC\s+TTbar_Hadronic\s+tt_had\s+10000\s+(.*)$", out, re.M)
        v = [float(x) for x in m.group(1).split()[:12]] if m else []
        # kept 2024 MC branches in the mock universe: run lumi event nJet Jet_pt Jet_eta PV_npvs
        # HLT_PFHT1050 HLT_IsoMu24 genWeight genTtbarId nGenPart GenPart_pt (518 B) + nOtherPV OtherPV_z
        # nMuon Muon_IPx Muon_jetDF Muon_pt (40 B) + nLHEPart LHEPart_pt nLHEPdfWeight LHEPdfWeight (520 B)
        # = 1078 B, x0.3 = 0.3234 kB; skims 6jcount 6j20 6j25 6j30 6j20ht400 pass 0.70 0.60 0.50 0.40 0.25
        want = [0.3234, 0.3234, 0.70, 0.2264, 0.60, 0.1940, 0.50, 0.1617, 0.40, 0.1294, 0.25, 0.0809]
        ok = len(v) == 12 and all(abs(a - b) < 0.0015 for a, b in zip(v, want))
        check("2024 MC TTbar_Hadronic numbers = mock truth (base, meta, five skims)", ok, (v, want))
        check("smallest stored Jet_pt is reported (mock 15.0 GeV) for all 34 samples",
              out.count("smallest stored Jet_pt 15.0 GeV") == 34, out.count("smallest stored Jet_pt"))
        check("calibration lines printed for ZZ and JetMET0 2024H", out.count("calibration: CRAB pilot") == 2)
        check("family breakdown printed for 4 samples", out.count("kept bytes by family") == 4)
        m = re.search(r"^\s+multitop\s+2024:multitop x([\d.]+)", out, re.M)
        # 2018UL / 2024 tt_semilep base: (1078 + 20) / 1078 with Jet_pt 60 B in Run 2
        check("2018UL borrows multitop from 2024 with the era scale", bool(m) and abs(float(m.group(1)) - 1098.0 / 1078.0) < 0.006,
              m.group(0) if m else "no scaled multitop line")
        with open(tsv) as f:
            nk = sum(int(l.split("\t")[11]) for l in list(f)[1:])
        with open(brtsv) as f:
            nb = len(f.readlines()) - 1
        check("per-branch table: one row per kept branch of every sample (%d)" % nk, nb == nk and nk > 0, (nb, nk))
        m = re.search(r"slim drafts on the whole input file: slimA -([\d.]+)% \((\d+) br\), slimB -([\d.]+)% \((\d+) br\), "
                      r"slimC -([\d.]+)% \((\d+) br\)", out)
        # slimA drops nOtherPV OtherPV_z Muon_IPx nLHEPart LHEPart_pt (124 B), slimB also Muon_jetDF (8 B),
        # slimC also nLHEPdfWeight LHEPdfWeight (416 B): 11.5 / 12.2 / 50.8 % of 1078 B; 23 -> 18 / 17 / 15 branches
        got = [float(x) for x in m.groups()] if m else []
        check("slim drafts price as the mock says (2024 MC: -11.5% / -12.2% / -50.8%, 18 / 17 / 15 branches)",
              got == [11.5, 18, 12.2, 17, 50.8, 15], got)
        check("slim line printed for all 34 samples", out.count("slim drafts on the whole input file:") == 34,
              out.count("slim drafts on the whole input file:"))
        check("Data lists have no slimC and use slimB for it", out.count("slimC (= previous tier)") == 2)
        rowsT = dict((l.split()[0], [float(x) for x in l.split()[1:8]])
                     for l in out.splitlines() if re.match(r"^  (current|slimA|slimB|slimC) ", l))
        ok = sorted(rowsT) == ["current", "slimA", "slimB", "slimC"] and \
            rowsT["current"][0] > rowsT["slimA"][0] > rowsT["slimB"][0] > rowsT["slimC"][0] > 0
        check("decision table: current > slimA > slimB > slimC (base column)", ok, rowsT)
        m = re.search(r"^== 2024 Data: 32 datasets, (\d+) events", out, re.M)
        check("2024 Data projects all 32 datasets with 5958480379 DAS events", bool(m) and m.group(1) == "5958480379",
              m.group(0) if m else "")

        rc, out = run()
        check("rerun exits 0 and measures nothing new", rc == 0 and nrows() == 34, (rc, nrows()))
        check("rerun gives the same TOTAL", total(out) == t1, (total(out), t1))

        rc, out = run("--project-only")
        check("--project-only exits 0 with the same TOTAL", rc == 0 and total(out) == t1, (rc, total(out)))
        drafts = os.path.join(tmp, "drafts")
        shutil.copytree(os.path.join(REPO, "script", "drafts"), drafts)
        with open(os.path.join(drafts, "branch_hadronic_2024_v15_MC_slimA.txt"), "a") as f:
            f.write("drop Muon_pt\n")
        rc2, out2 = run("--project-only", "--drafts", drafts)
        a1 = [l for l in out.splitlines() if l.startswith("  slimA ")]
        a2 = [l for l in out2.splitlines() if l.startswith("  slimA ")]
        check("an edited draft is re-priced by --project-only (slimA drops more, current unchanged)",
              rc2 == 0 and a1 and a2 and float(a2[0].split()[1]) < float(a1[0].split()[1]) and total(out2) == t1,
              (a1, a2))

        rc, out = run("--fresh", "--only", "2024:MC:ZZ", env={"MOCK_NOOPEN": "_ZZ_Tune"})
        check("a file that cannot be opened: FAILED line, exit 1, no new row",
              rc == 1 and "FAILED: cannot open" in out and nrows() == 34, (rc, nrows(), out[-300:]))

        rc, out = run("--fresh", "--only", "2024:MC:WW", env={"MOCK_BADSKIM": "1"})
        check("a rejected skim expression: FAILED line, exit 1, no new row, no scratch file left",
              rc == 1 and "TTreeFormula rejected" in out and nrows() == 34 and os.listdir(work) == [],
              (rc, nrows(), os.listdir(work), out[-300:]))

        rc, out = run("--fresh", "--only", "2024:MC:WW")
        check("--fresh re-measures and appends one row", rc == 0 and nrows() == 35, (rc, nrows()))
        check("... and the projection is unchanged (same mock numbers)", total(out) == t1, (total(out), t1))

        rc, out = run("-n", "5000", "--only", "2024:MC:WW")
        check("-n 5000 is a new signature: measured again, projection PARTIAL", rc == 1 and nrows() == 36
              and "PARTIAL" in out, (rc, nrows()))

        with open(tsv, "a") as f:
            f.write("2026-09-24T00:00:00Z\t2024\tMC\ttruncated-row\n")
        rc, out = run("--project-only")
        check("a truncated TSV row is ignored", rc == 0 and total(out) == t1, (rc, total(out)))

        rc, out = run("--only", "2024:MC:NoSuchKey")
        check("--only with an unknown key exits 2", rc == 2, rc)
        rc, out = run("-n", "0")
        check("-n 0 exits 2", rc == 2, rc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_fail = RESULTS.count(False)
    print("RESULT: %s (%d checks)" % ("ALL PASS" if n_fail == 0 else "%d FAILED" % n_fail, len(RESULTS)))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
