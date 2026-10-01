#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forge_audit.py -- per-input-file audit and job closure of the NtupleForge
`slim` recipe (docs/12_fastpath_workflow_plan.md sections 2.3 and 5).

`run_postproc.py --audit` imports this module; submit_crab.py ships it to the
CRAB worker next to run_postproc.py and forge_skims.py. After NanoAODTools has
written the merged output (-o forgedNtuple.root), every INPUT file is read once
more with RDataFrame over the same entry range. Only nJet, Jet_pt, Jet_eta,
genWeight, genTtbarId, run, luminosityBlock and event are read (a few percent
of a NanoAOD file). The results go into the output file, all as TTrees because
haddnano.py merges TTrees by concatenation (a TObjString it writes under its
own text as key name, CMSSW 14_2_X PhysicsTools/NanoAOD/scripts/haddnano.py):

  ForgeAudit       one row per input file: entries in the tree and read,
                   events passing the skim (RVec expression), sum of genWeight,
                   of its square and over passing events, negative-weight
                   count, the Runs-tree sums, and per genTtbarId code the count
                   and sum of genWeight (code_n[i], code_sumw[i]: i = 0 for a
                   negative id, i = 1 + genTtbarId % 100 otherwise)
  ForgeTTbbKeys    MC with genTtbarId: every input event with genTtbarId % 100
                   in 53..55, the codes every tt+nb extension comes from (TTHH
                   docs/02_physics.md): run, luminosityBlock, event, genTtbarId,
                   genWeight, pass (the skim). Joined later with the tt+nb
                   patch this gives the sums of weights of the extended bins
                   although a skim keeps few events. Written for every MC
                   sample (the job does not know which are stitched); for
                   ttH(bb) or the signal most events are in it, about 25 bytes
                   each before compression.
  ForgeProvenance  one row per job: json (audit version, skim, formula, rvec,
                   branch file and md5, git commit from submit_crab.py, CMSSW,
                   inputs), plus skim and git as their own columns

Closure, printed as FORGE|CHECK lines (docs/12 section 5.2):
  C1  FAIL  output Events entries != sum of events passing the RVec expression
            (without a skim: != sum of entries read). Assumes the module drops
            no event (modules/noop.py; submit_crab.py warns otherwise).
  C2  FAIL  an input file was not read to the end of its range
  C2e FAIL  a ROOT error line (Error in < / SysError in < / Fatal in <) while
            NanoAODTools copied or the audit read: ROOT goes on after a basket
            read error with stale buffers (2026-09-28 [7c], size_options.py v2)
  C2w WARN  'Error in <TTree::SetBranchStatus>: unknown branch -> X' (a plain
            name) or '... No branch name is matching wildcard -> X' (a wildcard):
            a keep pattern of the branch list matches nothing in this file (e.g.
            LHE_* in a pythia-only sample). The output just lacks X; not a read
            error.
  C2r FAIL  MC, whole file read: Runs genEventCount != entries (audit v2,
            2026-09-30, D-2026-09-30-p7: exact in all 265 files of the P6 pilot)
  C3  FAIL  MC, whole file read: sum genWeight vs Runs genEventSumw, relative
            difference above C3_FAIL (1e-5); WARN above C3_TOL (1e-6). genWeight
            is Float_t: the P6 pilot gave 4.68e-8 in every TTbb file (powheg,
            nearly constant |w|), the float rounding bound is 2^-24 x sum|w| /
            |sum w|; a lost event is C2r's job

Exit codes of run_postproc.py --audit. CRAB does not get them as they are: its
wrapper uses the first FrameworkError of the job report and only without one
the scriptExe's exit code, which in the 2024 production arrived as 5 for an 85
(not retried; docs/05_troubleshooting.md A28). Since P7.1 run_postproc.py
writes the code CRAB fails the job with into the report (fjr_mark_error,
CRAB_ERROR; in brackets; retries per CRABServer RetryJob.py EXIT_RETRY_POLICY):
  0  ok
  1  NanoAODTools raised (no report: CRAB records 50115 and retries), or the
     output could not be written or read back after the copy [1, retried as
     a worker-node error]
  84 the audit could not open an input file, or it has no Events tree
     [8020 FileOpenError, retried at another site]
  85 read trouble: a ROOT error line (C2e), a short read (C2), an RDataFrame
     read exception [8021 FileReadError, retried at another site]
  5  a closure FAIL without read trouble (C1, C2c, C2r, C3) [80005: not
     retried, a human looks]
  7  the audit itself failed otherwise (a bug) [80007: not retried]
LAST_FAIL[0] holds the one-line reason that goes with the code.
CRAB copies the outputs of a failed job under .../failed/: file lists for the
analysis must skip that directory (plan 12 P8).

ASCII only, python 3.6 compatible. Needs PyROOT and numpy (both in CMSSW).
Offline test with a mock ROOT: script/test_forge_audit_mock.py.
"""
import collections
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import traceback
from array import array

import forge_skims

AUDIT_VERSION = 2            # 2 (2026-09-30): C2r and C3 can FAIL, TFile.Open raising -> 84; same trees
N_EVT_LINES = 20
NCODE = 101                  # 0: genTtbarId < 0; 1 + c: genTtbarId % 100 == c
KEY_CODES = (53, 54, 55)
C3_TOL = 1e-6                # C3 WARN above
C3_FAIL = 1e-5               # C3 FAIL above (D-2026-09-30-p7)
ROOT_ERROR_PREFIXES = ("Error in <", "SysError in <", "Fatal in <")
# TTree::SetBranchStatus (ROOT 6.30 tree/tree/src/TTree.cxx): a keep pattern that matches no branch prints
# "unknown branch -> X" for a plain name and "No branch name is matching wildcard -> X" for a wildcard
BENIGN_RE = re.compile(r"^Error in <TTree::SetBranchStatus>: (?:unknown branch|No branch name is matching wildcard) -> (\S+)")
CAPTURE_SHOWN = 40
CAPTURE_FILE = "forge_stderr.txt"   # crab_script.py prints its summary if run_postproc.py dies
EXIT_NODE, EXIT_CLOSURE, EXIT_AUDIT, EXIT_OPEN, EXIT_READ = 1, 5, 7, 84, 85
KEEP = []                    # ROOT objects stay referenced until os._exit (no PyROOT dealloc)
LAST_FAIL = [""]             # run_job: why the last job failed, one line (run_postproc.py puts it in the FJR, A28)

CPP = r"""
#ifndef FORGE_AUDIT_CPP
#define FORGE_AUDIT_CPP
#include <cmath>
#include <cstddef>
#include "ROOT/RVec.hxx"
// sum in double of pt * (pt > ptmin && |eta| < etamax) over the jets: the same
// arithmetic as TTreeFormula Sum$(Jet_pt*(Jet_pt>ptmin && abs(Jet_eta)<etamax)),
// including a NaN or inf pt making the sum NaN (inf * 0 = NaN)
double forge_ht(const ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, double ptmin, double etamax)
{
   double s = 0.;
   for (std::size_t i = 0; i < pt.size() && i < eta.size(); ++i)
      s += double(pt[i]) * ((pt[i] > ptmin && std::abs(eta[i]) < etamax) ? 1. : 0.);
   return s;
}
int forge_code_index(int id) { return id < 0 ? 0 : 1 + id % 100; }
#endif
"""

KEY_FILTER = "genTtbarId >= 0 && genTtbarId %% 100 >= %d && genTtbarId %% 100 <= %d" % (KEY_CODES[0], KEY_CODES[-1])


class AuditError(RuntimeError):
    def __init__(self, msg, code=EXIT_AUDIT):
        RuntimeError.__init__(self, msg)
        self.code = code


# ---------------------------------------------------------------------------
# C-level stderr capture
# ---------------------------------------------------------------------------
def scan_capture(fh):
    """(n lines, n ROOT error lines, first error line, head, tail, benign names), bounded memory.
    SetBranchStatus lines for a keep pattern matching nothing are benign (C2w) and not counted as errors."""
    n = n_err = 0
    first = ""
    head, tail = [], collections.deque(maxlen=CAPTURE_SHOWN)
    benign = []
    for raw in fh:
        line = raw.decode("utf-8", "replace").rstrip("\n")
        n += 1
        for part in line.split("\r"):
            if part.startswith(ROOT_ERROR_PREFIXES):
                m = BENIGN_RE.match(part)
                if m:
                    if m.group(1) not in benign and len(benign) < 50:
                        benign.append(m.group(1))
                    continue
                n_err += 1
                if not first:
                    first = part
        if len(head) < CAPTURE_SHOWN:
            head.append(line)
        else:
            tail.append(line)
    return n, n_err, first, head, list(tail), benign


def echo_capture(scan):
    n, head, tail = scan[0], scan[3], scan[4]
    if not n:
        return
    lines = head + ([] if n <= len(head) + len(tail) else
                    ["... (%d captured lines not shown) ..." % (n - len(head) - len(tail))]) + tail
    sys.stderr.write("\n".join(lines) + "\n")
    sys.stderr.flush()


def c_flush():
    try:
        import ctypes
        ctypes.CDLL(None).fflush(None)
    except Exception:
        pass


class CapturedStderr(object):
    """fd 2 of this process (and of children such as haddnano.py) goes through
    `tee` for the duration of the block: every line reaches the real stderr at
    once (so nothing is lost if the job is killed) and a copy lands in a named
    file, scanned for ROOT error lines when the block ends. tee is a separate
    process, so a flood of ROOT output cannot block on this process's GIL.
    Without tee the lines go to the file only and are echoed (first and last
    CAPTURE_SHOWN) when the block ends; if the process dies inside the block the
    file stays and crab/crab_script.py prints a summary of it."""

    def __init__(self, path=CAPTURE_FILE):
        self.path = path
        self.n_lines, self.n_errors, self.first_error, self.benign = 0, 0, "", []
        self.live = False

    def __enter__(self):
        sys.stdout.flush()
        sys.stderr.flush()
        c_flush()
        self.saved = os.dup(2)
        self.tee = None
        try:
            self.tee = subprocess.Popen(["tee", self.path], stdin=subprocess.PIPE, stdout=self.saved,
                                        stderr=self.saved)
            os.dup2(self.tee.stdin.fileno(), 2)
            self.live = True
        except OSError:
            self.tee = None
            self.tmp = open(self.path, "w+b")
            os.dup2(self.tmp.fileno(), 2)
        return self

    def __exit__(self, *exc):
        try:
            sys.stderr.flush()
        except Exception:
            pass
        c_flush()
        os.dup2(self.saved, 2)
        if self.tee is not None:
            self.tee.stdin.close()
            try:
                self.tee.wait(timeout=60)
            except subprocess.TimeoutExpired:
                self.tee.kill()
                self.tee.wait()
        else:
            self.tmp.close()
        os.close(self.saved)
        with open(self.path, "rb") as fh:
            scan = scan_capture(fh)
        os.remove(self.path)
        self.n_lines, self.n_errors, self.first_error, self.benign = scan[0], scan[1], scan[2], scan[5]
        if not self.live:
            echo_capture(scan)
        return False


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def to_pfn(fname):
    """As NanoAODTools PostProcessor.run(): an LFN goes through edmFileUtil."""
    fname = fname.strip()
    if fname.startswith("/store/"):
        fname = subprocess.check_output(["edmFileUtil", "-d", "-f " + fname]).decode("utf-8").strip()
    return fname


INPUT_LFN = {}   # name the job opened -> the LFN it was given (run_postproc.py --input-fallback, args.input_lfn)


def lfn_of(fname):
    """The LFN recorded for an input: the one run_postproc.py was given when it
    opened another name (a site PFN, a fallback copy or URL), else the part from
    /store/ on without a ?query (as NanoAODTools' job report takes it)."""
    if fname in INPUT_LFN:
        return INPUT_LFN[fname]
    i = fname.find("/store/")
    return fname[i:].split("?", 1)[0] if i >= 0 else fname


def md5_of(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except (IOError, OSError):
        return ""


def fmt(x):
    return "%.9g" % x


def forge_line(*fields):
    print("FORGE|" + "|".join(str(f) for f in fields))
    sys.stdout.flush()


def declare(ROOT):
    ROOT.gInterpreter.Declare(CPP)


def pin_error_level(ROOT, logger):
    """ROOT must print its Error lines for C2e to see them: a .rootrc or rootlogon
    that raised the ignore level above kError would switch C2e off silently."""
    try:
        if int(ROOT.gErrorIgnoreLevel) > int(ROOT.kError):
            logger.warning("gErrorIgnoreLevel was %d (above kError); set to kWarning for the audit"
                           % int(ROOT.gErrorIgnoreLevel))
            ROOT.gErrorIgnoreLevel = ROOT.kWarning
    except Exception:
        pass


def is_read_exception(e):
    s = str(e)
    return ("processing the data" in s or "TTreeReader" in s or "error reading" in s.lower()
            or "readbuffer" in s.lower())


# ---------------------------------------------------------------------------
# one input file
# ---------------------------------------------------------------------------
def audit_file(ROOT, fname, rvec, first_entry=0, max_entries=None):
    """Read one input file; returns (row, keys, evts). row: dict of the ForgeAudit
    columns; keys: dict of numpy arrays (MC with genTtbarId) or None; evts: first
    N_EVT_LINES events."""
    t0 = time.time()
    pfn = to_pfn(fname)
    try:
        f = ROOT.TFile.Open(pfn)
    except OSError as e:                 # ROOT >= 6.30 raises instead of returning a null pointer
        raise AuditError("cannot open %s: %s" % (pfn, e), EXIT_OPEN)
    if not f or f.IsZombie():
        raise AuditError("cannot open %s" % pfn, EXIT_OPEN)
    KEEP.append(f)
    tree = f.Get("Events")
    if not tree:
        raise AuditError("no Events tree in %s" % pfn, EXIT_OPEN)
    KEEP.append(tree)
    n_tree = int(tree.GetEntries())
    in_autosave = int(tree.GetAutoSave())
    names = set(str(b.GetName()) for b in tree.GetListOfBranches())
    is_mc = "genWeight" in names
    has_gtid = "genTtbarId" in names
    runs_count, runs_sumw, runs_sumw2 = 0, 0.0, 0.0
    runs = f.Get("Runs")
    if is_mc and runs:
        KEEP.append(runs)
        for i in range(int(runs.GetEntries())):
            runs.GetEntry(i)
            runs_count += int(runs.genEventCount)
            runs_sumw += float(runs.genEventSumw)
            runs_sumw2 += float(runs.genEventSumw2)
    if max_entries:
        n_expect = max(0, min(n_tree - first_entry, max_entries))
    else:
        n_expect = max(0, n_tree - first_entry)

    df = ROOT.RDataFrame("Events", pfn)
    KEEP.append(df)
    if first_entry or max_entries:
        df = df.Range(first_entry, first_entry + max_entries if max_entries else 0)
        KEEP.append(df)
    df = (df.Define("forge_nj20", "(int)Sum(Jet_pt>20 && abs(Jet_eta)<%s)" % forge_skims.JET_ETA_MAX)
            .Define("forge_ht20", "forge_ht(Jet_pt, Jet_eta, 20., %s)" % forge_skims.JET_ETA_MAX)
            .Define("forge_pass", "(bool)(%s)" % rvec if rvec else "true"))
    KEEP.append(df)
    res = {"n": df.Count(), "pass": df.Filter("forge_pass").Count()}
    evt_cols = ["run", "luminosityBlock", "event", "forge_nj20", "forge_ht20", "forge_pass"]
    keys = None
    if is_mc:
        df = df.Define("forge_w", "(double)genWeight").Define("forge_w2", "forge_w*forge_w")
        KEEP.append(df)
        res["sumw"] = df.Sum("forge_w")
        res["sumw2"] = df.Sum("forge_w2")
        res["neg"] = df.Filter("genWeight < 0").Count()
        res["sumw_pass"] = df.Filter("forge_pass").Sum("forge_w")
    if is_mc and has_gtid:
        df = df.Define("forge_ci", "forge_code_index(genTtbarId)")
        KEEP.append(df)
        res["hn"] = df.Histo1D(("forge_hn", "", NCODE, -0.5, NCODE - 0.5), "forge_ci")
        res["hw"] = df.Histo1D(("forge_hw", "", NCODE, -0.5, NCODE - 0.5), "forge_ci", "forge_w")
        keys = df.Filter(KEY_FILTER).AsNumpy(["run", "luminosityBlock", "event", "genTtbarId", "genWeight",
                                              "forge_pass"], lazy=True)
        evt_cols.append("genTtbarId")
    evts = df.Range(N_EVT_LINES).AsNumpy(evt_cols, lazy=True)
    KEEP.extend(res.values())
    KEEP.extend([keys, evts])

    n_in = int(res["n"].GetValue())            # runs the event loop for every booked result
    row = {"file": lfn_of(fname), "n_tree": n_tree, "n_expect": n_expect, "n_in": n_in,
           "n_pass": int(res["pass"].GetValue()), "is_mc": bool(is_mc), "has_gtid": bool(has_gtid),
           "sumw": 0.0, "sumw2": 0.0, "n_neg": 0, "sumw_pass": 0.0,
           "runs_count": runs_count, "runs_sumw": runs_sumw, "runs_sumw2": runs_sumw2,
           "code_n": [0] * NCODE, "code_sumw": [0.0] * NCODE,
           "first_entry": int(first_entry), "max_entries": int(max_entries or 0), "in_autosave": in_autosave}
    if is_mc:
        row["sumw"] = float(res["sumw"].GetValue())
        row["sumw2"] = float(res["sumw2"].GetValue())
        row["n_neg"] = int(res["neg"].GetValue())
        row["sumw_pass"] = float(res["sumw_pass"].GetValue())
    if "hn" in res:
        hn, hw = res["hn"].GetValue(), res["hw"].GetValue()
        row["code_n"] = [int(round(hn.GetBinContent(i + 1))) for i in range(NCODE)]
        row["code_sumw"] = [float(hw.GetBinContent(i + 1)) for i in range(NCODE)]
        row["code_outside"] = int(round(hn.GetBinContent(0) + hn.GetBinContent(NCODE + 1)))
    keys = keys.GetValue() if keys is not None else None
    evts = evts.GetValue()
    row["t_s"] = time.time() - t0
    f.Close()
    return row, keys, evts


# ---------------------------------------------------------------------------
# closure
# ---------------------------------------------------------------------------
def closure(rows, n_out, n_root_errors, first_root_error, skim, benign=()):
    """[(name, level, detail)] for the job."""
    out = []
    n_pass = sum(r["n_pass"] for r in rows)
    n_in = sum(r["n_in"] for r in rows)
    want = n_pass if skim else n_in
    out.append(("C1", "PASS" if n_out == want else "FAIL",
                "output Events %d, %s %d" % (n_out, "RVec pass" if skim else "entries read", want)))
    short = [r for r in rows if r["n_in"] != r["n_expect"]]
    out.append(("C2", "FAIL" if short else "PASS",
                "every file read to the end of its range (%d files)" % len(rows) if not short else
                "%s read %d of %d entries" % (short[0]["file"], short[0]["n_in"], short[0]["n_expect"])))
    out.append(("C2e", "FAIL" if n_root_errors else "PASS",
                "%d ROOT error line(s)%s" % (n_root_errors, (", first: " + first_root_error.strip()[:200])
                                             if n_root_errors else "")))
    auto = [r for r in rows if r.get("in_autosave")]
    if auto:
        out.append(("C2a", "WARN", "%s: input Events autosave %d (central NanoAOD writes 0): NanoAODTools' clone "
                                   "inherits it, and haddnano.py merges every key cycle, so a backup cycle can "
                                   "replace the output tree; C1 guards against it"
                    % (auto[0]["file"], auto[0]["in_autosave"])))
    if benign:
        out.append(("C2w", "WARN", "keep pattern(s) matching nothing in this file (ROOT SetBranchStatus 'unknown "
                                   "branch' / 'No branch name is matching wildcard'): %s" % ", ".join(benign)))
    for r in rows:
        if "code_outside" in r and (r["code_outside"] or sum(r["code_n"]) != r["n_in"]):
            out.append(("C2c", "FAIL", "%s: genTtbarId codes count %d of %d entries (%d outside)"
                        % (r["file"], sum(r["code_n"]), r["n_in"], r["code_outside"])))
        if not r["is_mc"]:
            continue
        whole = r["first_entry"] == 0 and r["max_entries"] == 0
        if not whole:
            out.append(("C2r", "INFO", "%s: part of the file read, Runs sums not compared" % r["file"]))
            continue
        out.append(("C2r", "PASS" if r["runs_count"] == r["n_in"] else "FAIL",
                    "%s: Runs genEventCount %d, entries %d" % (r["file"], r["runs_count"], r["n_in"])))
        if r["runs_sumw"] == 0 and r["sumw"] == 0:     # as forge_campaign_audit.py rel_diff: 0 vs 0 agrees
            out.append(("C3", "PASS", "%s: %s, both sums 0" % (r["file"], "empty file" if r["n_in"] == 0
                                                                else "%d entries" % r["n_in"])))
            continue
        d = abs(r["sumw"] - r["runs_sumw"]) / abs(r["runs_sumw"]) if r["runs_sumw"] else float("inf")
        out.append(("C3", "PASS" if d <= C3_TOL else "WARN" if d <= C3_FAIL else "FAIL",
                    "%s: sum genWeight %s, Runs genEventSumw %s, relative difference %.3g (WARN above %g, FAIL above %g)"
                    % (r["file"], fmt(r["sumw"]), fmt(r["runs_sumw"]), d, C3_TOL, C3_FAIL)))
    return out


def exit_code_of(checks):
    fails = set(c[0] for c in checks if c[1] == "FAIL")
    if fails & {"C2", "C2e"}:
        return EXIT_READ
    if fails:
        return EXIT_CLOSURE
    return 0


# ---------------------------------------------------------------------------
# output objects
# ---------------------------------------------------------------------------
def write_outputs(ROOT, out_path, rows, keys_list, provenance):
    f = ROOT.TFile.Open(out_path, "UPDATE")
    if not f or f.IsZombie():
        raise AuditError("cannot open %s for UPDATE" % out_path, EXIT_NODE)
    KEEP.append(f)
    f.cd()
    t = ROOT.TTree("ForgeAudit", "NtupleForge audit: one row per input file (forge_audit.py v%d)" % AUDIT_VERSION)
    t.SetAutoSave(0)
    KEEP.append(t)
    s_file = ROOT.std.string()
    KEEP.append(s_file)
    t.Branch("file", s_file)
    buf = {}
    for name, code in (("n_tree", "Q"), ("n_in", "Q"), ("n_pass", "Q"), ("n_neg", "Q"), ("runs_count", "Q"),
                       ("first_entry", "Q"), ("max_entries", "Q")):
        buf[name] = array(code, [0])
        t.Branch(name, buf[name], "%s/l" % name)
    for name in ("sumw", "sumw2", "sumw_pass", "runs_sumw", "runs_sumw2"):
        buf[name] = array("d", [0.0])
        t.Branch(name, buf[name], "%s/D" % name)
    buf["is_mc"] = array("B", [0])
    t.Branch("is_mc", buf["is_mc"], "is_mc/O")
    buf["code_n"] = array("Q", [0] * NCODE)
    t.Branch("code_n", buf["code_n"], "code_n[%d]/l" % NCODE)
    buf["code_sumw"] = array("d", [0.0] * NCODE)
    t.Branch("code_sumw", buf["code_sumw"], "code_sumw[%d]/D" % NCODE)
    for r in rows:
        s_file.assign(r["file"])
        for name in ("n_tree", "n_in", "n_pass", "n_neg", "runs_count", "first_entry", "max_entries",
                     "sumw", "sumw2", "sumw_pass", "runs_sumw", "runs_sumw2"):
            buf[name][0] = r[name]
        buf["is_mc"][0] = 1 if r["is_mc"] else 0
        for i in range(NCODE):
            buf["code_n"][i] = r["code_n"][i]
            buf["code_sumw"][i] = r["code_sumw"][i]
        t.Fill()
    t.Write()
    n_keys = None
    if any(k is not None for k in keys_list):
        n_keys = 0
        k = ROOT.TTree("ForgeTTbbKeys", "NtupleForge: input events with genTtbarId %% 100 in %d..%d, before the skim"
                       % (KEY_CODES[0], KEY_CODES[-1]))
        k.SetAutoSave(0)
        KEEP.append(k)
        kb = {"run": array("I", [0]), "luminosityBlock": array("I", [0]), "event": array("Q", [0]),
              "genTtbarId": array("i", [0]), "genWeight": array("f", [0.0]), "pass": array("B", [0])}
        for name, leaf in (("run", "i"), ("luminosityBlock", "i"), ("event", "l"), ("genTtbarId", "I"),
                           ("genWeight", "F"), ("pass", "O")):
            k.Branch(name, kb[name], "%s/%s" % (name, leaf))
        for keys in keys_list:
            if keys is None:
                continue
            cols = [keys["run"], keys["luminosityBlock"], keys["event"], keys["genTtbarId"], keys["genWeight"],
                    keys["forge_pass"]]
            for i in range(len(cols[0])):
                kb["run"][0] = int(cols[0][i])
                kb["luminosityBlock"][0] = int(cols[1][i])
                kb["event"][0] = int(cols[2][i])
                kb["genTtbarId"][0] = int(cols[3][i])
                kb["genWeight"][0] = float(cols[4][i])
                kb["pass"][0] = 1 if cols[5][i] else 0
                k.Fill()
                n_keys += 1
        k.Write()
    p = ROOT.TTree("ForgeProvenance", "NtupleForge: one row per job, json of how the file was made")
    p.SetAutoSave(0)
    KEEP.append(p)
    s_json, s_skim, s_git = ROOT.std.string(), ROOT.std.string(), ROOT.std.string()
    KEEP.extend([s_json, s_skim, s_git])
    p.Branch("json", s_json)
    p.Branch("skim", s_skim)
    p.Branch("git", s_git)
    s_json.assign(json.dumps(provenance, sort_keys=True))
    s_skim.assign(str(provenance.get("skim", "")))
    s_git.assign(str(provenance.get("git", "")))
    p.Fill()
    p.Write()
    f.Close()
    if f.TestBit(getattr(ROOT.TFile, "kWriteError", 1 << 14)):
        raise AuditError("write error on %s (disk full?)" % out_path, EXIT_NODE)
    return n_keys


def output_entries(ROOT, out_path):
    f = ROOT.TFile.Open(out_path)
    if not f or f.IsZombie():
        raise AuditError("cannot open the output %s" % out_path, EXIT_NODE)
    KEEP.append(f)
    t = f.Get("Events")
    n = int(t.GetEntries()) if t else -1
    f.Close()
    if n < 0:
        raise AuditError("no Events tree in the output %s" % out_path, EXIT_NODE)
    return n


# ---------------------------------------------------------------------------
# the whole job
# ---------------------------------------------------------------------------
def provenance_of(args, skim, formula, rvec, inputs):
    return {"forge_audit_version": AUDIT_VERSION, "skim": skim or forge_skims.NONE, "formula": formula or "",
            "rvec": rvec or "", "branch_file": os.path.basename(args.branch_selection),
            "branch_md5": md5_of(args.branch_selection), "git": getattr(args, "forge_git", None) or "unknown",
            "cmssw": os.environ.get("CMSSW_VERSION", ""), "host": platform.node(),
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "inputs": [lfn_of(x) for x in inputs],
            "max_events": args.max_events or 0, "first_entry": args.first_entry or 0,
            "imports": list(args.imports or [])}


def run_job(ROOT, args, run_postprocessor, logger):
    """run_postprocessor(): NanoAODTools with args.output_file (merge mode).
    Returns the exit code (see the module docstring)."""
    skim = args.skim if args.skim not in (None, "", forge_skims.NONE) else None
    formula, rvec = forge_skims.get(skim)
    LAST_FAIL[0] = ""
    INPUT_LFN.clear()
    INPUT_LFN.update(getattr(args, "input_lfn", None) or {})
    pin_error_level(ROOT, logger)
    declare(ROOT)
    rows, keys_list = [], []
    t0 = time.time()
    n_out = -1
    pp_error = audit_error = None
    pp_tb = audit_tb = ""
    with CapturedStderr() as cap:
        try:
            run_postprocessor()
        except Exception as e:           # NanoAODTools itself: exit 1 as before --audit existed
            pp_error, pp_tb = e, traceback.format_exc()
        if pp_error is None:
            try:
                n_out = output_entries(ROOT, args.output_file)
                for i, fname in enumerate(args.input_files):
                    row, keys, evts = audit_file(ROOT, fname, rvec, args.first_entry or 0, args.max_events)
                    rows.append(row)
                    keys_list.append(keys)
                    if i == 0:
                        print_evt_lines(evts)
                    forge_line("FILE", row["file"], "n_in=%d" % row["n_in"], "n_pass=%d" % row["n_pass"],
                               "sumw=%s" % fmt(row["sumw"]), "runs_sumw=%s" % fmt(row["runs_sumw"]),
                               "runs_count=%d" % row["runs_count"], "t_s=%.1f" % row["t_s"])
            except Exception as e:
                audit_error, audit_tb = e, traceback.format_exc()
    if pp_error is not None:
        logger.error("NanoAODTools PostProcessor failed: %s: %s\n%s" % (type(pp_error).__name__, pp_error, pp_tb))
        forge_line("JOB", "files=%d" % len(args.input_files), "n_in=-1", "n_pass=-1", "n_out=-1",
                   "exit=%d" % EXIT_NODE)
        LAST_FAIL[0] = "NanoAODTools: %s: %s" % (type(pp_error).__name__, str(pp_error)[:300])
        return EXIT_NODE
    if audit_error is not None:
        if isinstance(audit_error, AuditError):
            code = audit_error.code
        elif is_read_exception(audit_error) or cap.n_errors:
            code = EXIT_READ
        else:
            code = EXIT_AUDIT
        logger.error("forge audit failed: %s: %s\n%s" % (type(audit_error).__name__, audit_error, audit_tb))
        forge_line("CHECK", "audit", "FAIL", "%s: %s" % (type(audit_error).__name__, str(audit_error)[:300]))
        LAST_FAIL[0] = "audit: %s: %s" % (type(audit_error).__name__, str(audit_error)[:300])
        if cap.n_errors:
            forge_line("CHECK", "C2e", "FAIL", "%d ROOT error line(s), first: %s"
                       % (cap.n_errors, cap.first_error.strip()[:200]))
            LAST_FAIL[0] += "; C2e: %d ROOT error line(s), first: %s" % (cap.n_errors, cap.first_error.strip()[:200])
        forge_line("JOB", "files=%d" % len(args.input_files), "n_in=-1", "n_pass=-1", "n_out=%d" % n_out,
                   "exit=%d" % code)
        return code
    checks = closure(rows, n_out, cap.n_errors, cap.first_error, skim, cap.benign)
    for name, level, detail in checks:
        forge_line("CHECK", name, level, detail)
    code = exit_code_of(checks)
    if code:
        LAST_FAIL[0] = "; ".join("%s FAIL: %s" % (name, str(detail)[:200]) for name, level, detail in checks
                                 if level == "FAIL")
    if code == 0:
        try:
            n_keys = write_outputs(ROOT, args.output_file, rows, keys_list,
                                   provenance_of(args, skim, formula, rvec, args.input_files))
            forge_line("CHECK", "write", "PASS", "ForgeAudit %d row(s), %s, ForgeProvenance, in %s"
                       % (len(rows), "ForgeTTbbKeys %d row(s)" % n_keys if n_keys is not None
                          else "no ForgeTTbbKeys (no genTtbarId)", args.output_file))
        except Exception as e:
            forge_line("CHECK", "write", "FAIL", "%s: %s" % (type(e).__name__, str(e)[:300]))
            code = e.code if isinstance(e, AuditError) else EXIT_NODE
            LAST_FAIL[0] = "write: %s: %s" % (type(e).__name__, str(e)[:300])
    forge_line("JOB", "files=%d" % len(rows), "n_in=%d" % sum(r["n_in"] for r in rows),
               "n_pass=%d" % sum(r["n_pass"] for r in rows), "n_out=%d" % n_out, "t_s=%.1f" % (time.time() - t0),
               "exit=%d" % code)
    return code


def print_evt_lines(evts):
    gt = evts.get("genTtbarId")
    for j in range(len(evts["run"])):
        forge_line("EVT", "%d:%d:%d" % (int(evts["run"][j]), int(evts["luminosityBlock"][j]), int(evts["event"][j])),
                   "nj20=%d" % int(evts["forge_nj20"][j]), "ht20=%.2f" % float(evts["forge_ht20"][j]),
                   "pass=%d" % (1 if evts["forge_pass"][j] else 0),
                   "gtid=%s" % (int(gt[j]) if gt is not None else "-"))
