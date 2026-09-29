#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forge_campaign_audit.py -- audit of a whole NtupleForge CRAB campaign where its
outputs are stored (KNU /pnfs), dataset by dataset (docs/12_fastpath_workflow_plan.md
P6 for the 2024 skim pilot, P8 for the productions; docs/05_troubleshooting.md A23).

    python3 script/forge_campaign_audit.py -c crabConfig/<config>.yaml --das script/drafts/review_das_<...>.tsv
        [--base /pnfs/knu.ac.kr/data/cms/store/user/junghyun] [--reference-config crabConfig/<no-skim config>.yaml]
        [--scan-logs] [--only KEY ...] [--tsv OUT.tsv] [--threads N]

For every dataset key of the config the outputs are looked up in the CRAB layout
    <base>/<output_base>/<primary dataset>/<key>/<YYMMDD_hhmmss>/<NNNN>/forgedNtuple_<job>.root
Files under a directory named failed/ are the outputs of failed jobs and files
under log/ the job log tarballs: neither counts as an output of the dataset.
Checks (FAIL makes the exit code 1; WARN does not):
  D1  FAIL  outputs == DAS nfiles (FileBased, one input file per job) and job ids 1..nfiles, none missing or extra
  D2  FAIL  (audit) every output has ForgeAudit and ForgeProvenance, and its Events == the sum of its n_pass
  D3  FAIL  (audit) every input LFN in exactly one ForgeAudit row; distinct inputs == DAS nfiles
  D4  FAIL  sum of n_in (audit), or of the output Events (no skim, no audit), == DAS nevents
  D5  FAIL  (audit) one skim, one git commit and one branch-list md5 in all ForgeProvenance rows
  D6  WARN  (audit, MC) sum of Runs genEventCount == sum of n_in, and sum of genWeight vs Runs genEventSumw
            (relative difference above 1e-6), for the dataset and for every file read whole (the largest
            relative difference and its file: the number that sets the C3 limit of the job audit)
  D7  WARN  files under failed/: they must stay out of every file list (tempTTHH make_filelists.py walks all
            directories, so it would count a failed job's output next to the retry's)
  D8  WARN  more than one task directory (<YYMMDD_hhmmss>) for the key
  K   FAIL  (audit, MC with genTtbarId) ForgeTTbbKeys: rows per output == its ForgeAudit count of codes 53..55,
            the keys with pass = 1 == the output events with codes 53..55, and with --reference-config every
            key == the reference events with codes 53..55 (before the skim)
  X7  FAIL  (--reference-config) the (run, lumi, event) set of the outputs == the set of the reference campaign's
            outputs of the same dataset (made without a skim) that pass this campaign's skim (RVec expression).
            K and X7 compare multisets: a key twice on both sides is in the dataset itself, a key twice on one
            side is a doubled job or reference
  D0  FAIL  an output that cannot be opened or read (ROOT 6.30 TFile.Open raises OSError): the run goes on
  L1  FAIL  (--scan-logs) a ROOT error line (Error in <, SysError in <, Fatal in <; not the SetBranchStatus lines
            of C2w) in the log tarball of a job whose output is counted, or a log without the NanoAODTools end
            line (Total time ...: then the tarball does not hold the job output and proves nothing): for
            campaigns without --audit, the read error check C2e after the fact
  T1  INFO  (--scan-logs) job time from the logs: NanoAODTools Total time and, with the audit, t_s of FORGE|JOB
            (median and largest); WARN when a counted job's FORGE|JOB line says exit != 0
Prints a FORGE-CAMPAIGN line and the checks per dataset, a TOTAL line and a RESULT
line. Exit 0 all PASS (WARN allowed), 1 a FAIL, 2 bad arguments. Read-only.
Needs PyROOT, numpy and PyYAML (cmsenv). ASCII only.
Offline test with real ROOT and NanoAODTools: script/test_forge_campaign_audit_root.py.
"""
import argparse
import collections
import json
import os
import re
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DEFAULT_BASE = "/pnfs/knu.ac.kr/data/cms/store/user/junghyun"
OUT_PREFIXES = ("forgedNtuple_", "slimmedNtuple_")
TASKDIR_RE = re.compile(r"^\d{6}_\d{6}$")
JOBID_RE = re.compile(r"_(\d+)\.root$")
LOGID_RE = re.compile(r"_(\d+)\.log\.tar\.gz$")
ERR_PREFIXES = ("Error in <", "SysError in <", "Fatal in <")
BENIGN_RE = re.compile(r"^Error in <TTree::SetBranchStatus>: (?:unknown branch|No branch name is matching wildcard) -> ")
# the last line NanoAODTools PostProcessor.run() prints before hadd and the job report (CMSSW 14_2_X postprocessor.py)
TOTAL_RE = re.compile(r"Total time ([0-9.]+) sec\. to process (\d+) events")
C3_TOL = 1e-6
NCODE = 101                             # ForgeAudit code_n[NCODE] (forge_audit.NCODE, audit version 1)
KEY_IDX = (1 + 53, 1 + 54, 1 + 55)      # its bins of genTtbarId % 100 in 53..55 (forge_audit.KEY_CODES)
EXAMPLES = 5


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------
def load_config(path):
    import yaml
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    common = cfg.get("common", {}) or {}
    datasets = cfg.get("datasets", {}) or {}
    skim = common.get("skim")
    skim = None if skim in (None, "", "none") else str(skim)
    audit = common.get("audit")
    audit = (skim is not None) if audit is None else bool(audit)
    return {"path": path, "output_base": str(common.get("output_base", "")).strip("/"), "datasets": datasets,
            "skim": skim, "audit": audit}


def load_das(path):
    """{key: (nevents, nfiles, dataset)} from a review_das_*.tsv (type key nevents nfiles size_TB dataset)."""
    out = {}
    with open(path) as f:
        head = f.readline().rstrip("\n").split("\t")
        col = dict((c, i) for i, c in enumerate(head))
        for c in ("key", "nevents", "nfiles", "dataset"):
            if c not in col:
                raise ValueError("%s: no column %r in the header %s" % (path, c, head))
        for line in f:
            p = line.rstrip("\n").split("\t")
            if len(p) < len(head):
                continue
            out[p[col["key"]]] = (int(p[col["nevents"]]), int(p[col["nfiles"]]), p[col["dataset"]])
    return out


def primary_of(dataset):
    parts = [x for x in str(dataset).split("/") if x]
    return parts[0] if parts else ""


def find_outputs(base, output_base, dataset, key):
    """The files of one dataset key in the CRAB layout."""
    d0 = os.path.join(base, output_base, primary_of(dataset), key)
    res = {"dir": d0, "exists": os.path.isdir(d0), "task_dirs": [], "outputs": [], "failed": [], "logs": []}
    if not res["exists"]:
        return res
    res["task_dirs"] = sorted(x for x in os.listdir(d0) if TASKDIR_RE.match(x) and os.path.isdir(os.path.join(d0, x)))
    for root, dirs, files in os.walk(d0):
        dirs.sort()
        parts = os.path.relpath(root, d0).split(os.sep)
        in_failed, in_log = "failed" in parts, "log" in parts
        for name in sorted(files):
            p = os.path.join(root, name)
            if name.startswith(OUT_PREFIXES) and name.endswith(".root"):
                (res["failed"] if in_failed else res["outputs"] if not in_log else []).append(p)
            elif name.endswith(".log.tar.gz") and not in_failed:
                res["logs"].append(p)
    return res


def job_id(path, rx=JOBID_RE):
    m = rx.search(os.path.basename(path))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# one output file
# ---------------------------------------------------------------------------
def read_output(ROOT, path):
    info = {"path": path, "bytes": os.path.getsize(path), "events": -1, "rows": [], "prov": [], "audit": False,
            "n_keys": None, "error": ""}
    try:
        f = ROOT.TFile.Open(path)          # ROOT 6.30 raises OSError when the open fails
    except OSError as e:
        info["error"] = "cannot open: %s" % e
        return info
    if not f or f.IsZombie():
        info["error"] = "cannot open"
        return info
    try:
        t = f.Get("Events")
        info["events"] = int(t.GetEntries()) if t else -1
        a = f.Get("ForgeAudit")
        p = f.Get("ForgeProvenance")
        k = f.Get("ForgeTTbbKeys")
        info["audit"] = bool(a) and bool(p)
        info["n_keys"] = int(k.GetEntries()) if k else None
        if a:
            for i in range(int(a.GetEntries())):
                a.GetEntry(i)
                codes = [int(a.code_n[j]) for j in range(NCODE)]
                info["rows"].append({"file": str(a.file), "n_in": int(a.n_in), "n_pass": int(a.n_pass),
                                     "sumw": float(a.sumw), "runs_count": int(a.runs_count),
                                     "runs_sumw": float(a.runs_sumw), "is_mc": bool(a.is_mc),
                                     "max_entries": int(a.max_entries), "first_entry": int(a.first_entry),
                                     "code_sum": sum(codes), "code_key": sum(codes[j] for j in KEY_IDX)})
        if p:
            for i in range(int(p.GetEntries())):
                p.GetEntry(i)
                try:
                    info["prov"].append(json.loads(str(p.json)))
                except ValueError:
                    info["prov"].append({"_bad_json": True})
    except Exception as e:                  # a damaged tree: the file counts as unreadable (D0)
        info["error"] = "cannot read: %s: %s" % (type(e).__name__, str(e)[:200])
    finally:
        f.Close()
    return info


# ---------------------------------------------------------------------------
# event keys (X7)
# ---------------------------------------------------------------------------
def key_array(np, arrs):
    """(run, lumi, event) as one 16-byte item per event: sortable and comparable in numpy."""
    hi = (arrs["run"].astype(np.uint64) << np.uint64(32)) | arrs["luminosityBlock"].astype(np.uint64)
    lo = arrs["event"].astype(np.uint64)
    two = np.ascontiguousarray(np.stack([hi, lo], axis=1))
    return two.view(np.dtype((np.void, 16))).ravel()


def decode_key(np, item):
    hi, lo = np.frombuffer(item.tobytes(), dtype=np.uint64)
    return int(hi >> np.uint64(32)), int(hi & np.uint64(0xFFFFFFFF)), int(lo)


def str_vector(ROOT, files):
    vec = ROOT.std.vector("string")()
    for p in files:
        vec.push_back(p)
    return vec


def event_keys(ROOT, np, files, rvec=None, tree="Events", cols=()):
    """(keys of the entries passing rvec, entries in total, {col: array} of the extra columns)."""
    df = ROOT.RDataFrame(tree, str_vector(ROOT, files))
    n_all = df.Count()
    if rvec:
        df = df.Filter("(bool)(%s)" % rvec, "filter")
    arrs = df.AsNumpy(["run", "luminosityBlock", "event"] + list(cols))
    return key_array(np, arrs), int(n_all.GetValue()), arrs


def has_column(ROOT, files, name, tree="Events"):
    return bool(ROOT.RDataFrame(tree, str_vector(ROOT, files[:1])).HasColumn(name))


def compare_keys(np, got, want, names=("the outputs", "the reference"), what="the reference after the skim"):
    """(ok, detail): got and want the same multiset of keys (a key twice on one side must be twice on the other:
    a doubled job or a doubled reference fails, duplicates already in the dataset do not)."""
    g, w = np.sort(got), np.sort(want)
    dup_g = len(g) - len(np.unique(g))
    dup_w = len(w) - len(np.unique(w))
    if len(g) == len(w) and np.array_equal(g, w):
        return True, "%d events, the same (run, lumi, event) set as %s%s" % (
            len(g), what, " (%d key(s) twice, on both sides)" % dup_g if dup_g else "")
    only_g = np.setdiff1d(g, w)
    only_w = np.setdiff1d(w, g)
    ex = [decode_key(np, x) for x in list(only_g[:EXAMPLES]) + list(only_w[:EXAMPLES])]
    return False, ("%s %d events, %s %d; only in %s %d, only in %s %d, duplicate keys in %s %d, in %s %d%s"
                   % (names[0].replace("the ", ""), len(g), what, len(w), names[0], len(only_g), names[1], len(only_w),
                      names[0], dup_g, names[1], dup_w,
                      "; e.g. %s" % ", ".join("%d:%d:%d" % e for e in ex[:EXAMPLES]) if ex else ""))


# ---------------------------------------------------------------------------
# logs (L1, T1)
# ---------------------------------------------------------------------------
def scan_log(path):
    """One CRAB log tarball: {n: ROOT error lines (SetBranchStatus lines excluded), first: the first one,
    total_s: NanoAODTools Total time of the last such line or None, forge: {field: value} of the last
    FORGE|JOB line or None}."""
    res = {"n": 0, "first": "", "total_s": None, "forge": None}
    with tarfile.open(path, "r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            fh = tf.extractfile(m)
            if fh is None:
                continue
            for raw in fh:
                line = raw.decode("utf-8", "replace").rstrip("\n")
                for part in line.split("\r"):
                    part = part.strip()
                    if part.startswith(ERR_PREFIXES) and not BENIGN_RE.match(part):
                        res["n"] += 1
                        if not res["first"]:
                            res["first"] = "%s: %s" % (m.name, part[:200])
                    elif part.startswith("FORGE|JOB|"):
                        res["forge"] = dict(x.split("=", 1) for x in part.split("|")[2:] if "=" in x)
                    else:
                        t = TOTAL_RE.search(part)
                        if t:
                            res["total_s"] = float(t.group(1))
    return res


def spread(vals):
    """'median X s, largest Y s (job J)' of [(value, job)]."""
    v = sorted(vals)
    return "median %.0f s, largest %.0f s (job %s)" % (v[len(v) // 2][0], v[-1][0], v[-1][1])


# ---------------------------------------------------------------------------
# one dataset
# ---------------------------------------------------------------------------
def audit_dataset(ROOT, np, args, cfg, ref_cfg, key, dataset, das, rvec):
    checks = []

    def add(name, level, detail):
        checks.append((name, level, detail))

    found = find_outputs(args.base, cfg["output_base"], dataset, key)
    row = {"key": key, "outputs": len(found["outputs"]), "das_nfiles": None, "das_nevents": None, "n_in": None,
           "n_out": 0, "n_pass": None, "bytes": 0, "failed": len(found["failed"]), "sumw": None, "runs_sumw": None,
           "rel_max": None}
    if key not in das:
        add("DAS", "FAIL", "no DAS numbers for %s in %s" % (key, args.das))
        return row, checks
    nevents, nfiles, das_ds = das[key]
    row["das_nfiles"], row["das_nevents"] = nfiles, nevents
    if das_ds != dataset:
        add("DAS", "FAIL", "the config's dataset %s is not the DAS table's %s" % (dataset, das_ds))
    if not found["exists"]:
        add("D1", "FAIL", "no directory %s" % found["dir"])
        return row, checks

    # D1 outputs and job ids
    ids = [job_id(p) for p in found["outputs"]]
    want = set(range(1, nfiles + 1))
    have = set(i for i in ids if i is not None)
    missing, extra = sorted(want - have), sorted(have - want)
    dup_ids = len(ids) - len(set(ids))
    ok = len(found["outputs"]) == nfiles and not missing and not extra and dup_ids == 0
    add("D1", "PASS" if ok else "FAIL",
        "outputs %d, DAS files %d%s%s%s" % (len(found["outputs"]), nfiles,
                                            ", missing jobs %s" % short(missing) if missing else "",
                                            ", jobs beyond the DAS count %s" % short(extra) if extra else "",
                                            ", %d job ids twice" % dup_ids if dup_ids else ""))
    if len(found["task_dirs"]) > 1:
        add("D8", "WARN", "%d task directories: %s" % (len(found["task_dirs"]), ", ".join(found["task_dirs"])))
    if found["failed"]:
        add("D7", "WARN", "%d file(s) under failed/ (jobs %s): keep them out of every file list"
            % (len(found["failed"]), short(sorted(set(job_id(p) for p in found["failed"]))) ))

    # read every output
    infos = []
    t0 = time.time()
    for i, p in enumerate(found["outputs"]):
        infos.append(read_output(ROOT, p))
        if (i + 1) % 200 == 0:
            sys.stderr.write("  %s: %d / %d outputs read (%.0f s)\n" % (key, i + 1, len(found["outputs"]), time.time() - t0))
    bad = [x for x in infos if x["error"] or x["events"] < 0]
    if bad:
        add("D0", "FAIL", "%d output(s) unreadable or without Events, e.g. %s (%s)"
            % (len(bad), bad[0]["path"], bad[0]["error"] or "no Events tree"))
    row["bytes"] = sum(x["bytes"] for x in infos)
    row["n_out"] = sum(max(x["events"], 0) for x in infos)

    if cfg["audit"]:
        noaudit = [x for x in infos if not x["audit"]]
        c1 = [x for x in infos if x["audit"] and x["events"] != sum(r["n_pass"] for r in x["rows"])]
        add("D2", "PASS" if not noaudit and not c1 else "FAIL",
            "every output has ForgeAudit + ForgeProvenance and Events == its n_pass" if not noaudit and not c1 else
            "%d without the audit trees (e.g. %s), %d with Events != n_pass (e.g. %s)"
            % (len(noaudit), noaudit[0]["path"] if noaudit else "-", len(c1), c1[0]["path"] if c1 else "-"))
        rows = [r for x in infos for r in x["rows"]]
        files = [r["file"] for r in rows]
        dups = sorted(f for f, c in collections.Counter(files).items() if c > 1)
        partial = [r for r in rows if r["max_entries"] or r["first_entry"]]
        ok = not dups and len(set(files)) == nfiles and not partial
        add("D3", "PASS" if ok else "FAIL",
            "distinct inputs %d, DAS files %d%s%s" % (len(set(files)), nfiles,
                                                     ", inputs in two rows: %s" % short(dups) if dups else "",
                                                     ", %d row(s) read only part of their file" % len(partial)
                                                     if partial else ""))
        row["n_in"] = sum(r["n_in"] for r in rows)
        row["n_pass"] = sum(r["n_pass"] for r in rows)
        add("D4", "PASS" if row["n_in"] == nevents else "FAIL",
            "sum of n_in %d, DAS nevents %d (difference %+d)" % (row["n_in"], nevents, row["n_in"] - nevents))
        prov = [p for x in infos for p in x["prov"]]
        vals = dict((k, sorted(set(str(p.get(k)) for p in prov))) for k in ("skim", "git", "branch_md5"))
        ok = all(len(v) == 1 for v in vals.values()) and vals["skim"] == [cfg["skim"] or "none"]
        add("D5", "PASS" if ok else "FAIL", "skim %s, git %s, branch md5 %s (config skim %s)"
            % (short(vals["skim"]), short(vals["git"]), short(vals["branch_md5"]), cfg["skim"] or "none"))
        if rows and all(r["is_mc"] for r in rows):
            row["sumw"] = sum(r["sumw"] for r in rows)
            row["runs_sumw"] = sum(r["runs_sumw"] for r in rows)
            rc = sum(r["runs_count"] for r in rows)
            rel = rel_diff(row["sumw"], row["runs_sumw"])
            whole = [r for r in rows if not r["max_entries"] and not r["first_entry"]]
            per = sorted((rel_diff(r["sumw"], r["runs_sumw"]), r["file"]) for r in whole)
            n_cnt = sum(1 for r in whole if r["runs_count"] != r["n_in"])
            row["rel_max"] = per[-1][0] if per else None
            ok = rc == row["n_in"] and rel <= C3_TOL and n_cnt == 0 and (not per or per[-1][0] <= C3_TOL)
            add("D6", "PASS" if ok else "WARN",
                "Runs genEventCount %d vs n_in %d; sum genWeight %.9g vs Runs genEventSumw %.9g, relative difference %.3g;"
                " per file (%d read whole): genEventCount != n_in in %d, largest relative difference %s"
                % (rc, row["n_in"], row["sumw"], row["runs_sumw"], rel, len(whole), n_cnt,
                   "-" if not per else "%.3g (%s)" % per[-1] if per[-1][0] else "0"))
            ttbb_check(ROOT, np, args, infos, ref_cfg, key, dataset, add)
    else:
        if cfg["skim"]:
            add("D4", "WARN", "a skim without the audit: the input event count is not recorded; output events %d"
                % row["n_out"])
        else:
            add("D4", "PASS" if row["n_out"] == nevents else "FAIL",
                "sum of output Events %d, DAS nevents %d (difference %+d; no skim, so every input event is kept)"
                % (row["n_out"], nevents, row["n_out"] - nevents))

    # X7 against the reference campaign
    if ref_cfg is not None:
        if key not in ref_cfg["datasets"]:
            add("X7", "INFO", "no %s in the reference config" % key)
        elif ref_cfg["skim"]:
            add("X7", "FAIL", "the reference config %s has a skim (%s); it must keep every event"
                % (ref_cfg["path"], ref_cfg["skim"]))
        elif ref_cfg["datasets"][key] != dataset:
            add("X7", "FAIL", "the reference config has another dataset for %s: %s" % (key, ref_cfg["datasets"][key]))
        elif not found["outputs"] or bad:
            add("X7", "FAIL", "not compared: %d output(s), %d unreadable" % (len(found["outputs"]), len(bad)))
        else:
            ref = find_outputs(args.base, ref_cfg["output_base"], ref_cfg["datasets"][key], key)
            if not ref["outputs"]:
                add("X7", "FAIL", "no reference outputs under %s" % ref["dir"])
            else:
                t1 = time.time()
                try:
                    got, n_got, _ = event_keys(ROOT, np, found["outputs"])
                    want_keys, n_ref, _ = event_keys(ROOT, np, ref["outputs"], rvec)
                except Exception as e:
                    add("X7", "FAIL", "not compared, reading failed: %s: %s" % (type(e).__name__, str(e)[:300]))
                else:
                    ok, detail = compare_keys(np, got, want_keys)
                    note = "; reference %d outputs, %d events (DAS %d)%s; %.0f s" % (
                        len(ref["outputs"]), n_ref, nevents,
                        "" if n_ref == nevents else " INCOMPLETE" if n_ref < nevents else " EXCESS", time.time() - t1)
                    add("X7", "PASS" if ok and n_ref == nevents else "FAIL", detail + note)

    # L1 log scan, T1 job time
    if args.scan_logs:
        used = set(i for i in ids if i is not None)
        logs = [p for p in found["logs"] if job_id(p, LOGID_RE) in used]
        hits, first, unread, no_end, t_nano, t_forge, bad_exit, no_forge = [], "", 0, [], [], [], [], []
        for p in logs:
            j = job_id(p, LOGID_RE)
            try:
                res = scan_log(p)
            except Exception:               # TarError, OSError, EOFError, zlib.error on a damaged tarball
                unread += 1
                continue
            if res["n"]:
                hits.append(j)
                first = first or res["first"]
            if res["total_s"] is None:
                no_end.append(j)
            else:
                t_nano.append((res["total_s"], j))
            fj = res["forge"]
            if fj is None:
                no_forge.append(j)
            else:
                if fj.get("exit") != "0":
                    bad_exit.append(j)
                try:
                    t_forge.append((float(fj["t_s"]), j))
                except (KeyError, ValueError):
                    pass
        ok = not hits and unread == 0 and len(logs) == len(used) and not no_end
        add("L1", "PASS" if ok else "FAIL",
            "logs %d of %d counted jobs, unreadable %d, jobs with ROOT error lines %d%s, logs without the"
            " NanoAODTools end line %d%s%s"
            % (len(logs), len(used), unread, len(hits), " (%s)" % short(sorted(hits)) if hits else "",
               len(no_end), " (%s)" % short(sorted(no_end)) if no_end else "", "; first: %s" % first if first else ""))
        parts = ["payload time only (the CRAB wrapper and the stage-out come on top)"] if t_nano or t_forge else []
        if t_nano:
            parts.append("NanoAODTools Total time of %d jobs: %s" % (len(t_nano), spread(t_nano)))
        if t_forge:
            parts.append("FORGE|JOB t_s of %d jobs: %s" % (len(t_forge), spread(t_forge)))
        if cfg["audit"] and no_forge:
            parts.append("%d log(s) without a FORGE|JOB line (%s)" % (len(no_forge), short(sorted(no_forge))))
        if bad_exit:
            parts.append("FORGE|JOB exit != 0 in %d counted job(s) (%s)" % (len(bad_exit), short(sorted(bad_exit))))
        add("T1", "WARN" if bad_exit or (cfg["audit"] and no_forge) else "INFO",
            "; ".join(parts) if parts else "no job time in the logs")
    return row, checks


def rel_diff(a, b):
    """|a - b| / |b|; 0 when both are 0 (an empty file), inf when only b is."""
    if b:
        return abs(a - b) / abs(b)
    return 0.0 if not a else float("inf")


def ttbb_check(ROOT, np, args, infos, ref_cfg, key, dataset, add):
    """K: ForgeTTbbKeys of the outputs (MC with the audit) against the ForgeAudit code counts, the output
    events and, with a reference campaign, the reference events (codes 53..55 before the skim)."""
    audited = [x for x in infos if x["audit"] and not x["error"]]
    if not any(x["n_keys"] is not None or any(r["code_sum"] for r in x["rows"]) for x in audited):
        add("K", "INFO", "no genTtbarId in the inputs, no ForgeTTbbKeys")
        return
    miss = [x for x in audited if x["n_keys"] is None]
    wrong = [x for x in audited if x["n_keys"] is not None and x["n_keys"] != sum(r["code_key"] for r in x["rows"])]
    with_tree = [x["path"] for x in audited if x["n_keys"] is not None]
    n_keys = sum(x["n_keys"] for x in audited if x["n_keys"] is not None)
    n_code = sum(r["code_key"] for x in audited for r in x["rows"])
    fails, notes = [], []
    if miss or wrong:
        fails.append("%d output(s) without ForgeTTbbKeys (e.g. %s), %d whose row count != its ForgeAudit count of"
                     " codes 53..55 (e.g. %s)" % (len(miss), os.path.basename(miss[0]["path"]) if miss else "-",
                                                 len(wrong), os.path.basename(wrong[0]["path"]) if wrong else "-"))
    try:
        if with_tree:
            ttbb_events(ROOT, np, args, with_tree, ref_cfg, key, dataset, fails, notes)
    except Exception as e:
        fails.append("not compared, reading failed: %s: %s" % (type(e).__name__, str(e)[:300]))
    add("K", "FAIL" if fails else "PASS", "ForgeTTbbKeys %d rows, ForgeAudit codes 53..55 %d; %s"
        % (n_keys, n_code, "; ".join(fails + notes)))


def ttbb_events(ROOT, np, args, with_tree, ref_cfg, key, dataset, fails, notes):
    """The event-level part of K: pass=1 keys vs the output events, all keys vs the reference."""
    import forge_audit
    keys, _, arrs = event_keys(ROOT, np, with_tree, tree="ForgeTTbbKeys", cols=("pass",))
    on = np.asarray(arrs["pass"]).astype(bool)
    if has_column(ROOT, with_tree, "genTtbarId"):
        out_keys, _, _ = event_keys(ROOT, np, with_tree, forge_audit.KEY_FILTER)
        ok, det = compare_keys(np, keys[on], out_keys, ("the pass=1 keys", "the output events with codes 53..55"),
                               "the output events with codes 53..55")
        (notes if ok else fails).append("pass=1: " + det)
    else:
        notes.append("the outputs keep no genTtbarId: pass=1 keys not compared with them")
    if ref_cfg is not None and ref_cfg["datasets"].get(key) == dataset and not ref_cfg["skim"]:
        ref = find_outputs(args.base, ref_cfg["output_base"], dataset, key)
        if ref["outputs"] and has_column(ROOT, ref["outputs"], "genTtbarId"):
            ref_keys, _, _ = event_keys(ROOT, np, ref["outputs"], forge_audit.KEY_FILTER)
            ok, det = compare_keys(np, keys, ref_keys, ("the keys", "the reference"),
                                   "the reference events with codes 53..55")
            (notes if ok else fails).append("reference: " + det)
        else:
            notes.append("no reference outputs with genTtbarId: keys not compared with the reference")


def short(seq, n=8):
    seq = list(seq)
    return ", ".join(str(x) for x in seq[:n]) + (" ... (%d)" % len(seq) if len(seq) > n else "") if seq else "-"


def fmt(x):
    return "-" if x is None else ("%.12g" % x if isinstance(x, float) else str(x))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-c", "--config", required=True, help="the crabConfig YAML the campaign was submitted with")
    ap.add_argument("--das", required=True, help="script/drafts/review_das_*.tsv with nevents and nfiles per key")
    ap.add_argument("--base", default=DEFAULT_BASE, help="storage path of /store/user/<user> (default %s)" % DEFAULT_BASE)
    ap.add_argument("--reference-config", default=None,
                    help="config of a campaign WITHOUT a skim on the same datasets (X7 event by event)")
    ap.add_argument("--scan-logs", action="store_true",
                    help="L1: ROOT error lines in the job log tarballs; T1: job time from the same logs")
    ap.add_argument("--only", nargs="+", default=None, help="only these dataset keys")
    ap.add_argument("--tsv", default=None, help="also write one row per dataset to this TSV file")
    ap.add_argument("--threads", type=int, default=4,
                    help="RDataFrame threads with --reference-config (X7, K; 0 = single-threaded)")
    args = ap.parse_args()
    try:
        cfg = load_config(args.config)
        ref_cfg = load_config(args.reference_config) if args.reference_config else None
        das = load_das(args.das)
    except (OSError, ValueError, ImportError) as e:
        print("FATAL: %s" % e, file=sys.stderr)
        return 2
    if not cfg["output_base"] or not cfg["datasets"]:
        print("FATAL: %s has no common.output_base or no datasets" % args.config, file=sys.stderr)
        return 2
    if not os.path.isdir(os.path.join(args.base, cfg["output_base"])):
        print("FATAL: %s does not exist (wrong --base, or nothing staged out yet)"
              % os.path.join(args.base, cfg["output_base"]), file=sys.stderr)
        return 2
    keys = [k for k in cfg["datasets"] if args.only is None or k in args.only]
    if args.only:
        unknown = sorted(set(args.only) - set(cfg["datasets"]))
        if unknown:
            print("FATAL: not in %s: %s" % (args.config, ", ".join(unknown)), file=sys.stderr)
            return 2
    try:
        import ROOT
        import numpy as np
    except ImportError as e:
        print("FATAL: %s (run after cmsenv)" % e, file=sys.stderr)
        return 2
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kError
    rvec = None
    if cfg["skim"]:
        import forge_skims
        import forge_audit
        forge_audit.declare(ROOT)            # forge_ht() for 6j20ht400
        rvec = forge_skims.get(cfg["skim"])[1]
    if ref_cfg is not None and args.threads > 0:
        ROOT.EnableImplicitMT(args.threads)

    print("campaign %s: output_base %s, skim %s, audit %s, %d dataset(s); reference %s; base %s"
          % (os.path.basename(args.config), cfg["output_base"], cfg["skim"] or "none", "on" if cfg["audit"] else "off",
             len(keys), ref_cfg["output_base"] if ref_cfg else "-", args.base))
    fails, results = 0, []
    tot = {"outputs": 0, "das_nfiles": 0, "n_in": 0, "das_nevents": 0, "n_out": 0, "bytes": 0, "failed": 0}
    for key in keys:
        row, checks = audit_dataset(ROOT, np, args, cfg, ref_cfg, key, cfg["datasets"][key], das, rvec)
        verdict = "FAIL" if any(c[1] == "FAIL" for c in checks) else "WARN" if any(c[1] == "WARN" for c in checks) \
            else "PASS"
        fails += verdict == "FAIL"
        n_ev = row["n_in"]
        print("FORGE-CAMPAIGN|%s|outputs=%d/%s|n_in=%s/%s|n_out=%d|pass=%s|MB=%.1f|kB/ev=%s|failed_dir=%d|%s"
              % (key, row["outputs"], fmt(row["das_nfiles"]), fmt(row["n_in"]), fmt(row["das_nevents"]), row["n_out"],
                 "%.2f%%" % (100.0 * row["n_out"] / n_ev) if n_ev else "-", row["bytes"] / 1e6,
                 "%.3f" % (row["bytes"] / 1000.0 / row["n_out"]) if row["n_out"] else "-", row["failed"], verdict))
        for name, level, detail in checks:
            print("   %-3s %-4s %s" % (name, level, detail))
        sys.stdout.flush()
        results.append((row, verdict))
        for k in tot:
            tot[k] += row[k] or 0
    have_n_in = any(r["n_in"] is not None for r, _ in results)
    print("TOTAL|datasets=%d|outputs=%d/%d|n_in=%s/%d|n_out=%d|GB=%.3f|failed_dir=%d"
          % (len(keys), tot["outputs"], tot["das_nfiles"], tot["n_in"] if have_n_in else "-", tot["das_nevents"],
             tot["n_out"], tot["bytes"] / 1e9, tot["failed"]))
    if args.tsv:
        with open(args.tsv, "w") as f:
            cols = ["key", "outputs", "das_nfiles", "n_in", "das_nevents", "n_pass", "n_out", "bytes", "failed",
                    "sumw", "runs_sumw", "rel_max"]
            f.write("\t".join(cols + ["verdict"]) + "\n")
            for row, verdict in results:
                f.write("\t".join(fmt(row[c]) for c in cols) + "\t" + verdict + "\n")
        print("wrote %s" % args.tsv)
    print("RESULT: %s" % ("ALL PASS" if not fails else "%d of %d dataset(s) FAIL" % (fails, len(keys))))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
