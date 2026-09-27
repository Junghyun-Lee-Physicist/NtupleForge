#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
size_options.py -- output volume of the v15 hadronic production, with the
branch lists as they are and with an event skim. Measured, not guessed.

Per sample (a key of one of the four v15 hadronic crabConfigs) it
  1. picks one file of the dataset with dasgoclient (the first, sorted, with
     at least -n events) and opens it via AAA;
  2. applies the config's branch_file to the Events tree the way NanoAODTools
     applies outputbranchsel (SetBranchStatus("*",1), then every
     keep/drop/keepmatch/dropmatch rule in order; branchselection.py);
  3. "meta": adds up the compressed size of the kept branches over the WHOLE
     input file, without copying (right when the input is LZMA:9 like the
     output; the input compression setting is printed, 209 = LZMA:9);
  4. "base": copies the first -n events with TTree::CopyTree into an LZMA:9
     file (run_postproc.py writes COMPRESSION = "LZMA:9");
  5. for every skim, copies the passing events of that local copy into
     another LZMA:9 file (and records the smallest stored Jet_pt, i.e. the
     threshold NanoAOD itself applied);
  6. subtracts the size of an empty copy (the per-file tree header), so the
     numbers are bytes per INPUT event that scale with the event count.
Scratch files are deleted. One row per sample is appended to a TSV at once,
so an interrupted run resumes where it stopped (rows whose signature = branch
file + skims + -n matches are reused; --fresh measures the selected samples
again and the new row wins).

It then PROJECTS the four configs: every dataset is mapped to a measurement
group (ttbar had / semilep / dilep incl. TTbb and ttH(bb), multi-top, tt+X,
QCD and W/Z+jets by HT bin with the nearest measured HT edge, single top,
diboson, jet PD, muon PD) and scaled by its DAS event count from the 09-23
review tables; the tree header is added once per DAS file. A group with no
sample in its own era borrows the other era's, scaled by the ratio of the two
eras' reference-group base sizes (MC tt_semilep, Data pd_jet).

Per-branch table and slim drafts. The compressed size of every kept branch
(whole input file, base copy, every skim copy) also goes to
script/runlogs/size_options_branches.tsv. From it, without copying anything
again, the projection prices the slim drafts
script/drafts/<branch_file>_slim{A,B,C}.txt written by
script/make_slim_branchlists.py (named branches removed, events unchanged;
a list without its own slimC uses its slimB) and ends with one table: TOTAL TB
per branch list (rows) and event selection (columns). A draft edited after
the run is re-priced by --project-only.

    python3 script/size_options.py --dry-run        # mapping + DAS files; opens no ROOT file
    python3 script/size_options.py                  # measure every sample, then project
    python3 script/size_options.py --project-only   # projection again from the TSVs (re-prices drafts)
    python3 script/size_options.py --only 2024:MC:TTbar_Hadronic

Skims. All are looser than the analyzer, which in EVERY selecting mode
requires nJets >= 6 (pT > 30 after JES/JER, |eta| < 2.4, jet ID), the 6th
jet above 40 GeV and HT > 500 (tempTTHH/include/SelectionCuts.h; kCutSequence
in ttHHanalyzer_unified.cc, steps 4, 5 and 7 are kSelEnforceAll):
  6jcount    Sum$(abs(Jet_eta)<2.5)>=6   (no pT cut beyond what NanoAOD stored)
  6j20       Sum$(Jet_pt>20 && abs(Jet_eta)<2.5)>=6
  6j25       Sum$(Jet_pt>25 && abs(Jet_eta)<2.5)>=6
  6j30       Sum$(Jet_pt>30 && abs(Jet_eta)<2.5)>=6
  6j20ht400  6j20 && Sum$(Jet_pt*(Jet_pt>20 && abs(Jet_eta)<2.5))>400
JEC margin. The analyzer needs six jets above 40 GeV after its own JES/JER,
so a skim at a stored pT of 20 / 25 / 30 GeV loses an event only if one of
those jets moves up by more than 100 / 60 / 33 %. HT is built from jets above
20 GeV, which contains every analyzer jet (pT > 30 after corrections) unless
one moves up by more than 50 %; the analyzer's HT > 500 then implies the
skim's HT > 400 unless the pT-weighted mean shift of the jets exceeds 25 %.

Calibration. ZZ and JetMET0_Run2024H went through the real CRAB pilot
(09-24, docs/09 sec 21, ledger V44): 1.056 and 0.780 kB per event over the
whole dataset, file headers and the Runs/LuminosityBlocks/MetaData trees
included. The script prints its own number for those two next to them.

Known bias. A skim copy of few events holds one basket (~150 B) per branch
that a production file spreads over many more events, so a low-pass skim is
overstated by at most n_branches x 150 B / n per input event (printed as
'bias<=' per sample; conservative).

WHY (2026-09-24): the user wants the production within 5-10 TB; with today's
lists it projects to 12.1-17.4 TB (docs/09 sec 21, ledger V44).

Needs cmssw-el8 + cmsenv (PyROOT, PyYAML), dasgoclient and a VOMS proxy; both
work inside the container (run_localcheck_2024_MC_20260923_073608.log).
Writes only its scratch directory and the two TSVs. Wrap with script/runlog.sh.
Python 3.6 compatible (no f-strings), ASCII only.

Exit: 0 ok | 1 a sample failed, or a dataset could not be projected |
      2 bad arguments | 4 PyROOT missing
"""
import argparse
import csv
import fnmatch
import hashlib
import math
import os
import re
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XRD = "root://cms-xrd-global.cern.ch/"
LZMA9 = 209            # TFile compress = 100 * algorithm + level; kLZMA = 2
BASKET_OVERHEAD_B = 150
DEFAULT_TSV = "script/runlogs/size_options_meas.tsv"
DEFAULT_BR_TSV = "script/runlogs/size_options_branches.tsv"
SLIM_TIERS = ("slimA", "slimB", "slimC")
ERAS = ("2024", "2018UL")

CONFIGS = [   # (era, tier, crabConfig, review table with DAS nevents / nfiles)
    ("2024", "MC", "crabConfig/config_ttHH2024_v15_had_MC.yaml",
     "script/drafts/review_das_ttHH_2024_v15_20260923_0851.tsv"),
    ("2024", "Data", "crabConfig/config_ttHH2024_v15_had_Data.yaml",
     "script/drafts/review_das_ttHH_2024_v15_20260923_0851.tsv"),
    ("2018UL", "MC", "crabConfig/config_ttHH2018UL_v15_had_MC.yaml",
     "script/drafts/review_das_ttHH_2018UL_v15_20260923_0853.tsv"),
    ("2018UL", "Data", "crabConfig/config_ttHH2018UL_v15_had_Data.yaml",
     "script/drafts/review_das_ttHH_2018UL_v15_20260923_0853.tsv"),
]

# (era, tier, config key). Chosen so that every group holding many events is
# measured in its own era; the group comes from group_of().
SAMPLES = [
    ("2024", "MC", "TTbar_Hadronic"),
    ("2024", "MC", "TTbar_SemiLep"),
    ("2024", "MC", "TTbar_DiLep"),
    ("2024", "MC", "TTHHto4b"),
    ("2024", "MC", "ttHToNonbb"),
    ("2024", "MC", "QCD_HT200to400"),
    ("2024", "MC", "QCD_HT400to600"),
    ("2024", "MC", "QCD_HT600to800"),
    ("2024", "MC", "QCD_HT1000to1200"),
    ("2024", "MC", "QCD_HT1500to2000"),
    ("2024", "MC", "WJetsToQQ_HT400to800"),
    ("2024", "MC", "WJetsToQQ_HT800to1500"),
    ("2024", "MC", "ZJetsToQQ_HT400to800"),
    ("2024", "MC", "ZJetsToQQ_HT1500to2500"),
    ("2024", "MC", "ST_t_top_had"),
    ("2024", "MC", "ST_t_top_lep"),
    ("2024", "MC", "ST_tW_top_had"),
    ("2024", "MC", "WW"),
    ("2024", "MC", "ZZ"),
    ("2024", "Data", "JetMET0_Run2024C-MINIv6NANOv15-v1"),
    ("2024", "Data", "JetMET0_Run2024G-MINIv6NANOv15-v2"),
    ("2024", "Data", "JetMET0_Run2024H-MINIv6NANOv15-v2"),
    ("2024", "Data", "Muon0_Run2024G-MINIv6NANOv15-v1"),
    ("2018UL", "MC", "TTbar_Hadronic"),
    ("2018UL", "MC", "TTbar_SemiLep"),
    ("2018UL", "MC", "TTbar_DiLep"),
    ("2018UL", "MC", "ST_t_top"),
    ("2018UL", "MC", "QCD_HT300to500"),
    ("2018UL", "MC", "QCD_HT500to700"),
    ("2018UL", "MC", "QCD_HT700to1000"),
    ("2018UL", "MC", "QCD_HT1000to1500"),
    ("2018UL", "Data", "JetHT_Run2018A"),
    ("2018UL", "Data", "JetHT_Run2018D"),
    ("2018UL", "Data", "SingleMuon_Run2018D"),
]

JET6 = "Sum$(Jet_pt>%d && abs(Jet_eta)<2.5)>=6"
SKIMS = [
    ("6jcount", "Sum$(abs(Jet_eta)<2.5)>=6"),
    ("6j20", JET6 % 20),
    ("6j25", JET6 % 25),
    ("6j30", JET6 % 30),
    ("6j20ht400", JET6 % 20 + " && Sum$(Jet_pt*(Jet_pt>20 && abs(Jet_eta)<2.5))>400"),
]

# CRAB pilot output over the whole dataset, kB per event (docs/09 sec 21, V44)
PILOT_KB = {("2024", "MC", "ZZ"): 1.056,
            ("2024", "Data", "JetMET0_Run2024H-MINIv6NANOv15-v2"): 0.780}

# samples whose kept bytes are also broken down by branch family
BREAKDOWN = set([("2024", "MC", "TTbar_Hadronic"),
                 ("2024", "Data", "JetMET0_Run2024G-MINIv6NANOv15-v2"),
                 ("2018UL", "MC", "TTbar_Hadronic"),
                 ("2018UL", "Data", "JetHT_Run2018D")])

ERA_REF = {"MC": "tt_semilep", "Data": "pd_jet"}
FAMILY_FALLBACK = {"wjets": "zjets", "zjets": "wjets"}


def group_of(tier, key):
    """Measurement group of a config key. HT-binned groups are 'family:edge'."""
    if tier == "Data":
        return "pd_muon" if re.match(r"(SingleMuon|Muon\d?)_", key) else "pd_jet"
    m = re.match(r"QCD_HT(\d+)to", key)
    if m:
        return "qcd:" + m.group(1)
    m = re.match(r"([WZ])JetsToQQ_HT(\d+)to", key)
    if m:
        return ("wjets:" if m.group(1) == "W" else "zjets:") + m.group(2)
    if re.search(r"TTHH|TTZH|TTZZ|TT4b|TTTT|TTTW|TTWH|TTWW|TTWZ", key):
        return "multitop"
    if re.match(r"(TTbar|TTbb|ttHTobb)_", key):
        if re.search(r"Hadronic|_had$", key):
            return "tt_had"
        if re.search(r"SemiLep|_semilep$", key):
            return "tt_semilep"
        if re.search(r"DiLep|_dilep$", key):
            return "tt_dilep"
    if re.match(r"(ttH|tH[qW]|TTZ|TTW|TTNuNu|TTLL)", key):
        return "ttx"
    if key.startswith("ST_tW_"):
        return "st_tw"
    if key.startswith("ST_"):
        if key.endswith("_had"):
            return "st_had"
        if key.endswith("_lep"):
            return "st_lep"
        return "st_incl"
    if key in ("WW", "WZ", "ZZ"):
        return "vv"
    return "other"


def resolve(era, tier, group, avail):
    """(source era, source group) that stands in for (era, tier, group), or None.
    avail: set of (era, tier, group) with a measurement. Order: same family in
    the same era, same family in the other era, then the fallback family."""
    fam, _, edge = group.partition(":")
    fams = [fam] + ([FAMILY_FALLBACK[fam]] if fam in FAMILY_FALLBACK else [])
    for f in fams:
        for e in [era] + [x for x in ERAS if x != era]:
            if edge:
                cands = []
                for (ae, at, ag) in avail:
                    af, _, aedge = ag.partition(":")
                    if ae == e and at == tier and af == f and aedge:
                        cands.append((abs(math.log(float(aedge) / float(edge))), ag))
                if cands:
                    return e, min(cands)[1]
            elif (e, tier, f) in avail:
                return e, f
    return None


def branch_group(name):
    for p in ("HLT_", "Flag_", "L1_"):
        if name.startswith(p):
            return p + "*"
    if name.startswith("n") and name[1:2].isupper():
        name = name[1:]
    return name.split("_")[0]


def load_config(path):
    import yaml
    with open(os.path.join(REPO, path)) as f:
        c = yaml.safe_load(f)
    return c["common"], c["datasets"]


def load_review(path):
    ev = {}
    with open(os.path.join(REPO, path)) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            ev[row["dataset"]] = (int(row["nevents"]), int(row["nfiles"]))
    return ev


def read_rules(path):
    """Same parsing as NanoAODTools BranchSelection: '#' comments, 'op pattern'."""
    rules = []
    with open(os.path.join(REPO, path)) as f:
        for line in f:
            line = re.sub(r"#.*", "", line.strip()).strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 2 or parts[0] not in ("keep", "drop", "keepmatch", "dropmatch"):
                print("WARN %s: ignored line %r (NanoAODTools ignores it too)" % (path, line))
                continue
            rules.append((parts[0], parts[1]))
    return rules


def apply_rules(tree, rules):
    """NanoAODTools BranchSelection.selectBranches, on a PyROOT TTree."""
    tree.SetBranchStatus("*", 1)
    names = [b.GetName() for b in tree.GetListOfBranches()]
    for op, pat in rules:
        stat = 1 if op.startswith("keep") else 0
        if op.endswith("match"):
            rx = re.compile("(:?%s)$" % pat)
            for n in names:
                if re.match(rx, n):
                    tree.SetBranchStatus(n, stat)
        else:
            tree.SetBranchStatus(pat, stat)


def signature(branch_file, n):
    h = hashlib.md5()
    with open(os.path.join(REPO, branch_file), "rb") as f:
        h.update(f.read())
    h.update(("|".join(e for _, e in SKIMS) + "|n=%d" % n).encode("ascii"))
    return h.hexdigest()[:12]


def das(query):
    out = subprocess.run(["dasgoclient", "-query", query], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
    if out.returncode != 0:
        raise RuntimeError("dasgoclient failed (%d) for %s: %s"
                           % (out.returncode, query, out.stderr.strip()[:200]))
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def pick_file(dataset, nmin):
    """(lfn, nevents): first file (sorted) with >= nmin events, else the largest.
    nevents is -1 when DAS did not give per-file counts."""
    files = []
    try:
        for l in das("file dataset=%s | grep file.name, file.nevents" % dataset):
            m = re.search(r"(/store/\S+?\.root)", l)
            nums = re.findall(r"\b(\d+)\b", l.replace(m.group(1), " ")) if m else []
            if m and nums:
                files.append((m.group(1), int(nums[-1])))
    except (RuntimeError, subprocess.TimeoutExpired):
        files = []
    if files:
        files.sort()
        for name, nev in files:
            if nev >= nmin:
                return name, nev
        return max(files, key=lambda x: x[1])
    plain = sorted(l for l in das("file dataset=%s" % dataset) if l.endswith(".root"))
    if not plain:
        raise RuntimeError("DAS lists no file for " + dataset)
    return plain[0], -1


def leaf_count(branch):
    """Name of the count branch of an array branch, '' for a scalar."""
    leaves = branch.GetListOfLeaves()
    if leaves.GetEntries() < 1:
        return ""
    lc = leaves.At(0).GetLeafCount()
    return lc.GetName() if lc else ""


def measure(ROOT, url, rules, nmax, skims, workdir, tag, breakdown):
    f = ROOT.TFile.Open(url)
    if not f or f.IsZombie():
        raise RuntimeError("cannot open " + url)
    t = f.Get("Events")
    if not t:
        raise RuntimeError("no Events tree in " + url)
    res = {"n_file": int(t.GetEntries()), "comp": int(f.GetCompressionSettings()),
           "groups": {}, "skims": {}}
    res["n_in"] = int(min(nmax, res["n_file"]))
    if res["n_in"] <= 0:
        raise RuntimeError("empty Events tree in " + url)
    # dead patterns make SetBranchStatus print errors; check_branchlist.py reports those
    old = ROOT.gErrorIgnoreLevel
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    try:
        apply_rules(t, rules)
    finally:
        ROOT.gErrorIgnoreLevel = old
    kept = [b for b in t.GetListOfBranches() if t.GetBranchStatus(b.GetName())]
    res["n_kept"] = len(kept)
    res["meta_bytes"] = 0
    res["br"] = {}   # branch -> {"count": name, "meta": bytes, "base": bytes, <skim>: bytes}
    for b in kept:
        z = int(b.GetZipBytes())
        res["meta_bytes"] += z
        res["br"][b.GetName()] = {"count": leaf_count(b), "meta": z}
        if breakdown:
            g = branch_group(b.GetName())
            res["groups"][g] = res["groups"].get(g, 0) + z

    base_path = os.path.join(workdir, tag + "_base.root")
    out = ROOT.TFile(base_path, "RECREATE", "", LZMA9)
    out.cd()
    tb = t.CopyTree("", "", res["n_in"])
    if not tb:
        raise RuntimeError("CopyTree gave nothing for " + url)
    tb.Write()
    for b in tb.GetListOfBranches():
        res["br"].setdefault(b.GetName(), {"count": "", "meta": 0})["base"] = int(b.GetZipBytes())
    out.Close()
    f.Close()
    res["base_bytes"] = os.path.getsize(base_path)

    fb = ROOT.TFile.Open(base_path)
    tbb = fb.Get("Events")
    p = os.path.join(workdir, tag + "_empty.root")
    e = ROOT.TFile(p, "RECREATE", "", LZMA9)
    e.cd()
    te = tbb.CloneTree(0)
    te.Write()
    e.Close()
    res["empty_bytes"] = os.path.getsize(p)
    os.remove(p)
    res["jet_ptmin"] = float(tbb.GetMinimum("Jet_pt"))   # 0 if no Jet_pt, huge if no jet
    for name, expr in skims:
        p = os.path.join(workdir, tag + "_" + name + ".root")
        o = ROOT.TFile(p, "RECREATE", "", LZMA9)
        o.cd()
        tk = tbb.CopyTree(expr)
        if not tk:
            raise RuntimeError("skim %s: TTreeFormula rejected %s" % (name, expr))
        nk = int(tk.GetEntries())
        tk.Write()
        for b in tk.GetListOfBranches():
            res["br"].setdefault(b.GetName(), {"count": "", "meta": 0})[name] = int(b.GetZipBytes())
        o.Close()
        res["skims"][name] = (nk, os.path.getsize(p))
        os.remove(p)
    fb.Close()
    os.remove(base_path)
    return res


# ---- TSV persistence ---------------------------------------------------------
FIELDS = (["utc", "era", "tier", "key", "group", "sig", "dataset", "lfn", "n_file", "n_in",
           "comp", "n_kept", "meta_bytes", "empty_bytes", "base_bytes", "jet_ptmin", "wall_s"]
          + [s[0] + x for s in SKIMS for x in ("_pass", "_bytes")])


def load_tsv(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if all(r.get(k) not in (None, "") for k in FIELDS):
                rows[(r["era"], r["tier"], r["key"], r["sig"])] = r   # last row wins
    return rows


def append_tsv(path, row):
    new = not os.path.exists(path)
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "a") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(dict((k, row[k]) for k in FIELDS))


BR_TREES = ["meta", "base"] + [s for s, _ in SKIMS]
BR_FIELDS = ["utc", "sig", "era", "tier", "key", "branch", "count"] + BR_TREES


def append_br_tsv(path, row, br):
    new = not os.path.exists(path)
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "a") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        if new:
            w.writerow(BR_FIELDS)
        for name in sorted(br):
            v = br[name]
            w.writerow([row["utc"], row["sig"], row["era"], row["tier"], row["key"], name, v.get("count", "")]
                       + [v.get(t, 0) for t in BR_TREES])


def load_br_tsv(path):
    """(era, tier, key, sig, utc) -> {branch: {"count": name, <tree>: bytes}}; bad lines skipped."""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            try:
                v = dict((t, int(r[t])) for t in BR_TREES)
                v["count"] = r["count"] or ""
                out.setdefault((r["era"], r["tier"], r["key"], r["sig"], r["utc"]), {})[r["branch"]] = v
            except (KeyError, TypeError, ValueError):
                continue
    return out


def slim_file(branch_file, tier, drafts="script/drafts"):
    return os.path.join(drafts, os.path.basename(branch_file).replace(".txt", "_%s.txt" % tier))


def kept_by_rules(br, rules):
    """Branches of a per-branch table that a rule list keeps: NanoAODTools order,
    ROOT wildcards (fnmatch-like, case-sensitive), and ROOT activating the count
    branch of every active array branch (as in make_slim_branchlists.py)."""
    st = dict((n, True) for n in br)
    for op, pat in rules:
        v = op.startswith("keep")
        if op.endswith("match"):
            rx = re.compile("(:?%s)$" % pat)
            hits = [n for n in st if re.match(rx, n)]
        else:
            hits = [n for n in st if fnmatch.fnmatchcase(n, pat)]
        for n in hits:
            st[n] = v
    for n, v in br.items():
        c = v.get("count")
        if st[n] and c and c in st:
            st[c] = True
    return set(n for n in st if st[n])


def slim_entry(row, br, keep):
    """entry(row) for the subset `keep` of the kept branches: every size scaled by
    that subset's share of the compressed bytes in the same tree."""
    e = entry(row)
    tot = dict((t, sum(v.get(t, 0) for v in br.values())) for t in BR_TREES)
    part = dict((t, sum(br[n].get(t, 0) for n in keep)) for t in BR_TREES)
    frac = dict((t, part[t] / float(tot[t]) if tot[t] else 0.0) for t in BR_TREES)
    share = len(keep) / float(len(br)) if br else 0.0
    out = {"base": e["base"] * frac["base"], "meta": part["meta"] / float(row["n_file"]) / 1000.0,
           "hdr": e["hdr"] * share, "bias": e["bias"] * share}
    for s, _ in SKIMS:
        out[s] = (e[s][0], e[s][1] * frac[s])
    return out


def entry(row):
    """Per-input-event numbers of one TSV row (kB), plus pass fractions."""
    n = float(row["n_in"])
    empty = float(row["empty_bytes"])
    e = {"base": max(0.0, float(row["base_bytes"]) - empty) / n / 1000.0,
         "meta": float(row["meta_bytes"]) / float(row["n_file"]) / 1000.0,
         "hdr": empty, "bias": int(row["n_kept"]) * BASKET_OVERHEAD_B / n / 1000.0}
    for s, _ in SKIMS:
        e[s] = (int(row[s + "_pass"]) / n,
                max(0.0, float(row[s + "_bytes"]) - empty) / n / 1000.0)
    return e


def mean_entry(entries):
    k = float(len(entries))
    m = {}
    for q in ("base", "meta", "hdr", "bias"):
        m[q] = sum(x[q] for x in entries) / k
    for s, _ in SKIMS:
        m[s] = (sum(x[s][0] for x in entries) / k, sum(x[s][1] for x in entries) / k)
    return m


def print_sample(row, epf, br=None, slims=()):
    e = entry(row)
    cells = "  ".join("%5.3f %6.3f" % e[s] for s, _ in SKIMS)
    print("%-6s %-4s %-34s %-11s %6s %6.3f %6.3f  %s  %5.1f %6.3f %5s %4s" % (
        row["era"], row["tier"], row["key"], row["group"], row["n_in"], e["base"], e["meta"],
        cells, e["hdr"] / 1000.0, e["bias"], row["comp"], row["n_kept"]))
    ptmin = float(row["jet_ptmin"])
    print("       %s s, smallest stored Jet_pt %s, %s" % (
        row["wall_s"], "%.1f GeV" % ptmin if 0 < ptmin < 1e6 else "n/a", row["lfn"]))
    if br:
        tot = float(sum(v["meta"] for v in br.values())) or 1.0
        cells = []
        for tn, rules, own in slims:
            if own:
                keep = kept_by_rules(br, rules)
                cells.append("%s -%.1f%% (%d br)" % (tn, 100.0 * (1.0 - sum(br[n]["meta"] for n in keep) / tot), len(keep)))
        if cells:
            print("       slim drafts on the whole input file: " + ", ".join(cells))
    k = (row["era"], row["tier"], row["key"])
    if k in PILOT_KB and epf:
        mine = e["base"] + e["hdr"] / epf / 1000.0
        print("       calibration: CRAB pilot %.3f kB/event (whole dataset, all trees);"
              " this sample %.3f incl. header share (meta-based %.3f); ratio pilot/this %.3f"
              % (PILOT_KB[k], mine, e["meta"] + e["hdr"] / epf / 1000.0, PILOT_KB[k] / mine if mine else 0.0))


def print_header():
    cells = "  ".join("%12s" % s for s, _ in SKIMS)
    print("%-6s %-4s %-34s %-11s %6s %6s %6s  %s  %5s %6s %5s %4s" % (
        "era", "tier", "key", "group", "n_in", "base", "meta", cells, "hdrkB", "bias<=", "comp", "nbr"))
    print("  (kB per INPUT event; every skim column is 'pass fraction, kB'; base = first n_in"
          " events copied at LZMA:9, meta = kept"
          " branches of the whole input file; hdrkB = per-file tree header; comp = input"
          " compression, 209 = LZMA:9; nbr = kept branches, pilot output had 674 (ZZ) / 646 (JetMET0 H))")


# ---- mapping and projection ------------------------------------------------------
def era_scale(era, src_era, tier, meas):
    if era == src_era:
        return 1.0
    ref = ERA_REF[tier]
    a, b = meas.get((era, tier, ref)), meas.get((src_era, tier, ref))
    if not a or not b:
        return 1.0
    mb = mean_entry(b)["base"]
    return mean_entry(a)["base"] / mb if mb > 0 else 1.0


def print_mapping(cfg):
    planned = set((e, t, group_of(t, k)) for e, t, k in SAMPLES)
    bad = 0
    print("# mapping: config dataset groups -> measured sample group (planned samples)")
    for era, tier, cpath, _ in CONFIGS:
        c = cfg[(era, tier)]
        per = {}
        for key, ds in c["datasets"].items():
            g = group_of(tier, key)
            p = per.setdefault(g, [0, 0, resolve(era, tier, g, planned)])
            p[0] += 1
            p[1] += c["review"].get(ds, (0, 0))[0]
            if ds not in c["review"]:
                print("  NO DAS EVENTS: %s %s %s" % (era, tier, key))
                bad += 1
        print("  %s %s (%d datasets)" % (era, tier, len(c["datasets"])))
        for g in sorted(per, key=lambda x: -per[x][1]):
            n, ev, src = per[g]
            print("    %-12s %3d ds %14d ev  <- %s" % (g, n, ev, "%s:%s" % src if src else "NONE"))
            if not src:
                bad += 1
    return bad


OPTS = ["base", "meta"] + [s for s, _ in SKIMS]


def project(cfg, meas, label="current branch lists", detail=True):
    avail = set(meas)
    opts = OPTS
    grand = dict((o, 0.0) for o in opts)
    missing = []
    print("")
    print("# projection, %s: TB = DAS events x kB per input event of the mapped group"
          " (+ one tree header per DAS file)" % label)
    for era, tier, cpath, _ in CONFIGS:
        c = cfg[(era, tier)]
        per = {}
        tot = dict((o, 0.0) for o in opts)
        keep = dict((s, 0.0) for s, _ in SKIMS)
        nev_all = nf_all = 0
        for key, ds in c["datasets"].items():
            g = group_of(tier, key)
            rv = c["review"].get(ds)
            src = resolve(era, tier, g, avail)
            if rv is None or src is None:
                missing.append((era, tier, g if rv is not None else "no-DAS-events:" + key,
                                rv[0] if rv else 0))
                continue
            nev, nf = rv
            nev_all += nev
            nf_all += nf
            m = mean_entry(meas[(src[0], tier, src[1])])
            sc = era_scale(era, src[0], tier, meas)
            hdr_tb = nf * m["hdr"] / 1e12
            a = per.setdefault(g, dict([(o, 0.0) for o in opts] + [("ev", 0), ("src", "")]))
            a["ev"] += nev
            a["src"] = "%s:%s" % src + ("" if sc == 1.0 else " x%.2f" % sc)
            vals = {"base": m["base"], "meta": m["meta"]}
            for s, _ in SKIMS:
                vals[s] = m[s][1]
                keep[s] += nev * m[s][0]
            for o in opts:
                v = nev * vals[o] * sc / 1e9 + hdr_tb
                a[o] += v
                tot[o] += v
        for o in opts:
            grand[o] += tot[o]
        if not detail:
            print("   %-6s %-4s TB  %s" % (era, tier, "  ".join("%s %6.2f" % (o, tot[o]) for o in opts)))
            continue
        print("== %s %s: %d datasets, %d events, %d files" % (era, tier, len(c["datasets"]), nev_all, nf_all))
        print("   TB    " + "  ".join("%s %6.2f" % (o, tot[o]) for o in opts))
        print("   kept events  " + "  ".join("%s %.3fe9 (%.1f%%)" % (s, keep[s] / 1e9, 100.0 * keep[s] / nev_all if nev_all else 0.0)
                                            for s, _ in SKIMS))
        print("   %-12s %-24s %13s  %s" % ("group", "measured as", "events", "  ".join("%9s" % o for o in opts)))
        for g in sorted(per, key=lambda x: -per[x]["base"]):
            a = per[g]
            print("   %-12s %-24s %13d  %s" % (g, a["src"], a["ev"], "  ".join("%9.3f" % a[o] for o in opts)))
    print("")
    if missing:
        agg = {}
        for era, tier, g, nev in missing:
            a = agg.setdefault((era, tier, g), [0, 0])
            a[0] += 1
            a[1] += nev
        print("# PARTIAL: %d datasets (%d events) have no measured group, so the totals"
              " below are too LOW. Missing: %s" % (len(missing), sum(m[3] for m in missing), "; ".join(
                  "%s %s %s (%d ds, %d ev)" % (k[0], k[1], k[2], v[0], v[1]) for k, v in sorted(agg.items()))))
    print("TOTAL TB   " + "  ".join("%s %6.2f" % (o, grand[o]) for o in opts) + ("  (PARTIAL)" if missing else ""))
    if detail:
        for o in opts:
            v = grand[o]
            print("   %-10s %6.2f TB  %s%s" % (o, v, "<= 5 TB" if v <= 5 else ("<= 10 TB" if v <= 10 else "> 10 TB"),
                                             "  (PARTIAL)" if missing else ""))
    return len(missing), grand


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=10000, help="events copied per sample (default 10000)")
    ap.add_argument("--only", action="append", default=[], help="era:tier:key, repeatable")
    ap.add_argument("--dry-run", action="store_true", help="mapping and DAS file choice only")
    ap.add_argument("--project-only", action="store_true", help="projection from the TSV only")
    ap.add_argument("--fresh", action="store_true",
                    help="measure the selected samples again even if the TSV has them (the new row wins)")
    ap.add_argument("--tsv", default=DEFAULT_TSV, help="measurement rows (default %s)" % DEFAULT_TSV)
    ap.add_argument("--br-tsv", default=DEFAULT_BR_TSV, help="per-branch sizes (default %s)" % DEFAULT_BR_TSV)
    ap.add_argument("--drafts", default="script/drafts", help="where the slim drafts are (default script/drafts)")
    ap.add_argument("--threads", type=int, default=4, help="ROOT implicit MT threads (default 4)")
    ap.add_argument("--redirector", default=XRD)
    ap.add_argument("--workdir", default=None, help="scratch dir (default: a new temp dir)")
    args = ap.parse_args()
    if args.n <= 0:
        print("FATAL: -n must be positive", file=sys.stderr)
        return 2

    cfg = {}
    for era, tier, cpath, rpath in CONFIGS:
        common, datasets = load_config(cpath)
        cfg[(era, tier)] = {"branch_file": common["branch_file"], "datasets": datasets,
                            "review": load_review(rpath), "path": cpath,
                            "sig": signature(common["branch_file"], args.n)}
    samples = SAMPLES
    if args.only:
        want = [tuple(o.split(":", 2)) for o in args.only]
        unknown = [":".join(w) for w in want if w not in SAMPLES]
        if unknown:
            print("FATAL: --only not in SAMPLES: %s" % ", ".join(unknown), file=sys.stderr)
            return 2
        samples = [s for s in SAMPLES if s in want]
    tsv = os.path.join(REPO, args.tsv)
    br_tsv = os.path.join(REPO, args.br_tsv)
    rows = load_tsv(tsv)
    br_rows = load_br_tsv(br_tsv)
    unmapped = print_mapping(cfg)
    slims = {}   # (era, tier) -> [(tier, rules, has its own file)]
    for era, tier, _, _ in CONFIGS:
        bf, lst, prev = cfg[(era, tier)]["branch_file"], [], None
        for tn in SLIM_TIERS:
            sp = slim_file(bf, tn, args.drafts)
            if os.path.exists(os.path.join(REPO, sp)):
                prev = read_rules(sp)
                lst.append((tn, prev, True))
            elif prev is not None:
                lst.append((tn, prev, False))
        slims[(era, tier)] = lst
        print("# slim drafts for %s: %s" % (bf, ", ".join("%s%s" % (tn, "" if own else " (= previous tier)")
                                                          for tn, _, own in lst) or "none found in script/drafts/"))
    print("# skims: " + " | ".join("%s = %s" % s for s in SKIMS))
    print("# n per sample %d | TSV %s (%d usable rows) | signatures %s" % (
        args.n, args.tsv, len(rows), " ".join("%s:%s=%s" % (e, t, cfg[(e, t)]["sig"]) for e, t, _, _ in CONFIGS)))

    def epf(era, tier, key):
        c = cfg[(era, tier)]
        rv = c["review"].get(c["datasets"].get(key))
        return float(rv[0]) / rv[1] if rv and rv[1] else 0.0

    def current(era, tier, key):
        return rows.get((era, tier, key, cfg[(era, tier)]["sig"]))

    def branches_of(era, tier, key):
        r = current(era, tier, key)
        return br_rows.get((era, tier, key, r["sig"], r["utc"])) if r else None

    fails = 0
    if not args.project_only:
        ROOT = None
        if not args.dry_run:
            try:
                import ROOT as _R
            except ImportError:
                print("FATAL: PyROOT not importable; run inside cmssw-el8 after cmsenv", file=sys.stderr)
                return 4
            _R.gROOT.SetBatch(True)
            if args.threads > 1:
                _R.EnableImplicitMT(args.threads)
            ROOT = _R
        workdir = args.workdir or tempfile.mkdtemp(prefix="size_options_")
        if not args.dry_run:
            print("# workdir %s | threads %d" % (workdir, args.threads))
            print_header()
        for era, tier, key in samples:
            c = cfg[(era, tier)]
            ds = c["datasets"].get(key)
            if ds is None:
                print("%-6s %-4s %-34s NOT IN %s" % (era, tier, key, c["path"]))
                fails += 1
                continue
            if not args.dry_run and not args.fresh and current(era, tier, key):
                print_sample(current(era, tier, key), epf(era, tier, key), branches_of(era, tier, key),
                             slims[(era, tier)])
                continue
            t0 = time.time()
            tag = re.sub(r"[^A-Za-z0-9]+", "_", "%s_%s_%s" % (era, tier, key))
            try:
                lfn, nev = pick_file(ds, args.n)
                if args.dry_run:
                    print("%-6s %-4s %-34s %-11s %8s ev  %s" % (era, tier, key, group_of(tier, key), nev, lfn))
                    continue
                r = measure(ROOT, args.redirector + lfn, read_rules(c["branch_file"]), args.n, SKIMS,
                            workdir, tag, (era, tier, key) in BREAKDOWN)
            except Exception as ex:   # keep going; the TSV keeps what worked
                print("%-6s %-4s %-34s FAILED: %s" % (era, tier, key, str(ex)[:200]))
                fails += 1
                for fn in os.listdir(workdir):   # scratch files of this sample
                    if fn.startswith(tag + "_"):
                        try:
                            os.remove(os.path.join(workdir, fn))
                        except OSError:
                            pass
                continue
            row = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "era": era, "tier": tier,
                   "key": key, "group": group_of(tier, key), "sig": c["sig"], "dataset": ds, "lfn": lfn,
                   "wall_s": "%.0f" % (time.time() - t0)}
            for k in ("n_file", "n_in", "comp", "n_kept", "meta_bytes", "empty_bytes", "base_bytes"):
                row[k] = r[k]
            row["jet_ptmin"] = "%.2f" % r["jet_ptmin"]
            for s, _ in SKIMS:
                row[s + "_pass"], row[s + "_bytes"] = r["skims"][s]
            append_tsv(tsv, row)
            append_br_tsv(br_tsv, row, r["br"])
            rows[(era, tier, key, c["sig"])] = row
            br_rows[(era, tier, key, c["sig"], row["utc"])] = r["br"]
            print_sample(row, epf(era, tier, key), r["br"], slims[(era, tier)])
            if r["groups"]:
                tot = float(sum(r["groups"].values()))
                top = sorted(r["groups"].items(), key=lambda kv: -kv[1])[:12]
                print("       kept bytes by family (whole input file): " + ", ".join(
                    "%s %.3f (%.0f%%)" % (g, b / float(r["n_file"]) / 1000.0, 100.0 * b / tot) for g, b in top))
            sys.stdout.flush()
        if not args.workdir:
            try:
                os.rmdir(workdir)
            except OSError:
                pass
        if args.dry_run:
            return 1 if (fails or unmapped) else 0

    meas = {}
    for era, tier, key in SAMPLES:
        r = current(era, tier, key)
        if r:
            meas.setdefault((era, tier, group_of(tier, key)), []).append(entry(r))
    if not meas:
        print("# nothing measured yet for these signatures; nothing to project")
        return 1
    missing, grand = project(cfg, meas)
    table = [("current", grand, missing)]

    # ---- slim drafts, priced from the per-branch table ------------------------
    for tn in SLIM_TIERS:
        meas_s, lacking, have_rules = {}, [], False
        for era, tier, key in SAMPLES:
            r = current(era, tier, key)
            if not r:
                continue
            rules = dict((t, ru) for t, ru, _ in slims[(era, tier)]).get(tn)
            br = branches_of(era, tier, key)
            if rules is None or not br:
                lacking.append("%s:%s:%s" % (era, tier, key))
                continue
            have_rules = True
            meas_s.setdefault((era, tier, group_of(tier, key)), []).append(slim_entry(r, br, kept_by_rules(br, rules)))
        if not have_rules:
            continue
        if lacking:
            print("")
            print("# %s not priced: no draft or no per-branch rows for %d measured sample(s): %s"
                  % (tn, len(lacking), ", ".join(lacking)))
            continue
        m_s, g_s = project(cfg, meas_s, label="%s drafts (script/drafts/, events as above)" % tn, detail=False)
        table.append((tn, g_s, m_s))
    print("")
    print("# TOTAL TB of the four configs: branch list (rows) x event selection (columns)")
    print("  %-8s %s" % ("list", "  ".join("%9s" % o for o in OPTS)))
    for name, g, m in table:
        print("  %-8s %s%s" % (name, "  ".join("%9.2f" % g[o] for o in OPTS), "  (PARTIAL)" if m else ""))
    return 1 if (fails or missing or unmapped) else 0


if __name__ == "__main__":
    sys.exit(main())
