#!/usr/bin/env python3
"""
NtupleForge CRAB Manager
=============================
[Description]
Reads a YAML configuration file and manages CRAB jobs (Submit, Status, Report,
Resubmit, Kill). Uses 'crab/crab_script.py' as the worker node wrapper.

[Usage]
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml             # submit (auto-resubmits existing tasks)
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --status    # full crab status per task
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --report    # compact per-sample job-state summary
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --resubmit  # explicit resubmit of failed jobs
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --kill      # kill all tasks
"""

import os
import sys
import glob
import argparse
import yaml
import shutil
import logging
import subprocess
import io
import contextlib
import datetime
import json
import re

# CRAB imports are GUARDED so that `--preflight` can run (and report the problem
# as a check result) in a shell where crab-setup.sh has not been sourced.
# Any other action still needs CRAB and will fail fast via _require_crab().
CRAB_IMPORT_ERROR = None
try:
    from CRABClient.UserUtilities import config, getUsername
    from CRABAPI.RawCommand import crabCommand
except Exception as _crab_exc:          # ImportError, or CRABClient env errors
    CRAB_IMPORT_ERROR = _crab_exc

    def config(*_a, **_k):
        raise RuntimeError("CRABClient unavailable: %s" % CRAB_IMPORT_ERROR)

    def getUsername(*_a, **_k):
        return os.environ.get("USER", "UNKNOWN_USER")

    def crabCommand(*_a, **_k):
        raise RuntimeError("CRABClient unavailable: %s" % CRAB_IMPORT_ERROR)


def _require_crab():
    if CRAB_IMPORT_ERROR is not None:
        logger.error("CRABClient could not be imported: %s", CRAB_IMPORT_ERROR)
        logger.error("Source it once per session:")
        logger.error("  source /cvmfs/cms.cern.ch/common/crab-setup.sh")
        sys.exit(1)

try:
    from http.client import HTTPException
except ImportError:
    from httplib import HTTPException

# Logging Setup
logging.basicConfig(level=logging.INFO, format='[submit_crab] : %(message)s')
logger = logging.getLogger("Submitter")

# --- Job-state buckets for --report -----------------------------------------
# CRAB job states shown as their own column in the compact report.
#
# MIRRORED in TTHHGenCategoryTools/TtbarIdExtender/crab/submit_ttbarIdExtend.py
# (--report added there 2026-07-27). The duplication is deliberate: the two
# repos are separate checkouts with different CMSSW releases, so they cannot
# share a module -- but the columns, the "others" rule and the unknown-state
# warning must stay identical or the two campaigns' reports stop being
# comparable. Change both, or neither.
REPORT_COLUMNS = ["finished", "running", "idle", "transferring", "failed"]
# Known-but-minor states folded into "others" WITHOUT raising an unknown warning.
KNOWN_OTHER_STATES = {
    "unsubmitted", "cooloff", "held", "killed", "killing",
    "toRetry", "on hold", "resubmitting",
}

def summarize_status(jobs_per_status):
    """Bucket a CRAB ``jobsPerStatus`` dict into the report columns + 'others'.

    Returns ``(row, unknown)`` where ``row`` maps each REPORT_COLUMNS entry plus
    ``others`` and ``total`` to a count, and ``unknown`` is the set of state
    names that are neither a column nor a known-other state -- i.e. states the
    code does not recognise, so the caller can warn about them.
    """
    row = {c: 0 for c in REPORT_COLUMNS}
    row["others"] = 0
    unknown = set()
    for state, n in (jobs_per_status or {}).items():
        if state in REPORT_COLUMNS:
            row[state] += n
        else:
            row["others"] += n
            if state not in KNOWN_OTHER_STATES:
                unknown.add(state)
    row["total"] = sum(row[c] for c in REPORT_COLUMNS) + row["others"]
    return row, unknown

def print_report(rows):
    """Print a compact per-sample job-state table. ``rows``: list of (name, row)."""
    cols = REPORT_COLUMNS + ["others", "total"]
    head = {"finished": "done", "running": "run", "idle": "idle",
            "transferring": "transf", "failed": "fail", "others": "other",
            "total": "total"}
    name_w = max([len("sample")] + [len(n) for n, _ in rows])
    header = f"{'sample':<{name_w}}  " + "  ".join(f"{head[c]:>6}" for c in cols)
    bar = "=" * len(header)
    print("\n" + bar)
    print("CRAB job report (per sample)  [done=finished, transf=transferring]")
    print(bar)
    print(header)
    print("-" * len(header))
    agg = {c: 0 for c in cols}
    for name, row in rows:
        print(f"{name:<{name_w}}  " + "  ".join(f"{row[c]:>6}" for c in cols))
        for c in cols:
            agg[c] += row[c]
    print("-" * len(header))
    print(f"{'TOTAL':<{name_w}}  " + "  ".join(f"{agg[c]:>6}" for c in cols))
    print(bar)

def check_voms():
    """Checks if VOMS proxy is valid."""
    try:
        subprocess.run(["voms-proxy-info", "--exists"], check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        logger.error("VOMS Proxy missing or expired.")
        logger.error("Run: voms-proxy-init --voms cms --valid 168:00")
        sys.exit(1)

# =============================================================================
# PREFLIGHT (--preflight) — read-only pre-submission checker
# =============================================================================
# Everything CRAB needs is verified here BEFORE a single task is created, and the
# whole transcript is written to a log file so it can be pasted into a review.
# Exit status: 0 = all PASS/WARN, 1 = at least one FAIL. Nothing is submitted and
# nothing is created except the log file.
class _Preflight:
    def __init__(self, log_path):
        self.rows = []          # (level, check, detail)
        self.log_path = log_path
        self.lines = []

    def _emit(self, level, check, detail):
        self.rows.append((level, check, detail))
        line = "[%-4s] %-34s %s" % (level, check, detail)
        print(line)
        self.lines.append(line)

    def ok(self, check, detail=""):
        self._emit("PASS", check, detail)

    def warn(self, check, detail=""):
        self._emit("WARN", check, detail)

    def fail(self, check, detail=""):
        self._emit("FAIL", check, detail)

    def note(self, text):
        print(text)
        self.lines.append(text)

    def finish(self):
        n_fail = sum(1 for l, _, _ in self.rows if l == "FAIL")
        n_warn = sum(1 for l, _, _ in self.rows if l == "WARN")
        n_pass = sum(1 for l, _, _ in self.rows if l == "PASS")
        self.note("-" * 78)
        self.note("PREFLIGHT SUMMARY: %d PASS, %d WARN, %d FAIL" % (n_pass, n_warn, n_fail))
        if n_fail:
            self.note("RESULT: NOT READY TO SUBMIT -- fix the FAIL items above.")
        else:
            self.note("RESULT: READY TO SUBMIT" + (" (review the WARNs first)" if n_warn else ""))
        try:
            with open(self.log_path, "w") as f:
                f.write("\n".join(self.lines) + "\n")
            print("Log written: %s" % self.log_path)
        except OSError as e:
            print("WARNING: could not write log file %s: %s" % (self.log_path, e))
        return 1 if n_fail else 0


_DATASET_RE = re.compile(r"^/[^/]+/[^/]+/(NANOAOD|NANOAODSIM|MINIAOD|MINIAODSIM|USER)$")


def run_preflight(args):
    """Read-only verification of everything needed to submit `args.config`."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cfg_tag = os.path.splitext(os.path.basename(args.config))[0]
    pf = _Preflight("preflight_%s_%s.log" % (cfg_tag, ts))

    pf.note("=" * 78)
    pf.note("NtupleForge CRAB PREFLIGHT (read-only)")
    pf.note("  config : %s" % args.config)
    pf.note("  cwd    : %s" % os.getcwd())
    pf.note("  time   : %s" % datetime.datetime.now().isoformat(timespec="seconds"))
    pf.note("  DAS check: %s" % ("ON (--check-das)" if args.check_das else "OFF (add --check-das to query DAS)"))
    pf.note("=" * 78)

    # ---- 1. config file ------------------------------------------------------
    if not os.path.exists(args.config):
        pf.fail("config file", "not found: %s" % args.config)
        return pf.finish()
    pf.ok("config file", args.config)
    try:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        pf.fail("config YAML parse", str(e).replace("\n", " ")[:160])
        return pf.finish()
    pf.ok("config YAML parse", "ok")

    common = (cfg or {}).get("common", {}) or {}
    datasets = (cfg or {}).get("datasets", {}) or {}

    # ---- 2. common: required keys -------------------------------------------
    for key in ("jobID", "site", "output_base", "analysis_module", "branch_file",
                "splitting", "units_per_job"):
        if key in common and common[key] not in (None, ""):
            pf.ok("common.%s" % key, str(common[key]))
        else:
            pf.fail("common.%s" % key, "missing or empty -- submit_crab.py would fall back to a default")
    split = str(common.get("splitting", ""))
    if split not in ("FileBased", "Automatic", "LumiBased", "EventAwareLumiBased"):
        pf.warn("common.splitting value", "unrecognised: %r" % split)

    # ---- 3. analysis module + shipped siblings ------------------------------
    module_cfg = common.get("analysis_module")
    if isinstance(module_cfg, list) and len(module_cfg) == 2:
        mod_path, list_var = module_cfg
        if os.path.exists(mod_path):
            pf.ok("module file", mod_path)
            try:
                src = open(mod_path).read()
                if re.search(r"^\s*%s\s*=" % re.escape(str(list_var)), src, re.M):
                    pf.ok("module list variable", "%s found in %s" % (list_var, os.path.basename(mod_path)))
                else:
                    pf.fail("module list variable",
                            "%r not assigned in %s (PostProcessor would import nothing)"
                            % (list_var, mod_path))
            except OSError as e:
                pf.fail("module file read", str(e))
            sibs = sorted(os.path.basename(p) for p in
                          glob.glob(os.path.join(os.path.dirname(mod_path) or ".", "*.py"))
                          if os.path.basename(p) != os.path.basename(mod_path))
            pf.ok("module siblings shipped", ", ".join(sibs) if sibs else "(none)")
        else:
            pf.fail("module file", "not found: %s" % mod_path)
    else:
        pf.fail("common.analysis_module", "must be [path, list_name]; got %r" % (module_cfg,))

    # ---- 4. branch selection file ------------------------------------------
    bsel = common.get("branch_file")
    if bsel and os.path.exists(bsel):
        rules = [l.strip() for l in open(bsel) if l.strip() and not l.strip().startswith("#")]
        keeps = [r for r in rules if r.split()[0].lower() == "keep"]
        drops = [r for r in rules if r.split()[0].lower() == "drop"]
        pf.ok("branch file", "%s (%d rules: %d keep / %d drop)" % (bsel, len(rules), len(keeps), len(drops)))
        bad = [r for r in rules if r.split()[0].lower() not in ("keep", "drop")]
        if bad:
            pf.fail("branch file syntax", "non keep/drop rule(s): %s" % bad[:3])
        slim = any(r.lower().replace(" ", "") == "drop*" for r in rules)
        if slim:
            kept = {r.split()[1] for r in keeps if len(r.split()) > 1}
            pf.ok("branch file mode", "SLIM ('drop *' present) -- output keeps %d explicit patterns" % len(kept))
            for must in ("run", "luminosityBlock", "event"):
                (pf.ok if must in kept else pf.fail)(
                    "slim keeps %s" % must,
                    "present" if must in kept else "MISSING -- event id needed by every downstream tool")
            for must in ("genWeight", "genTtbarId"):
                (pf.ok if must in kept else pf.warn)(
                    "slim keeps %s" % must,
                    "present" if must in kept else
                    "absent -- MC prescan would silently mis-bin (defaults to 0); intended only for Data-only configs")
        else:
            pf.ok("branch file mode", "PASSTHROUGH (no 'drop *')")
    else:
        pf.fail("branch file", "not found: %r" % bsel)

    # ---- 5. Rule 6: output filename hardcoded in two places ------------------
    here = os.path.dirname(os.path.abspath(__file__))
    pset = os.path.join(here, "PSet.py")
    submit_src = open(os.path.abspath(__file__)).read()
    m_sub = re.search(r'out_name\s*=\s*"([^"]+)"', submit_src)
    m_pset = None
    if os.path.exists(pset):
        m_pset = re.search(r"fileName\s*=\s*cms\.untracked\.string\('([^']+)'\)", open(pset).read())
    if m_sub and m_pset:
        if m_sub.group(1) == m_pset.group(1):
            pf.ok("Rule 6 output filename", "%s (submit_crab.py == PSet.py)" % m_sub.group(1))
        else:
            pf.fail("Rule 6 output filename",
                    "MISMATCH: submit_crab.py=%s vs PSet.py=%s" % (m_sub.group(1), m_pset.group(1)))
    else:
        pf.fail("Rule 6 output filename", "could not parse (submit=%s, PSet=%s)" % (bool(m_sub), bool(m_pset)))

    # ---- 6. worker-side files ----------------------------------------------
    for rel in ("crab/PSet.py", "crab/crab_script.py", "script/run_postproc.py"):
        p = os.path.join(os.path.dirname(here), rel) if not rel.startswith("crab/") else os.path.join(here, os.path.basename(rel))
        (pf.ok if os.path.exists(p) else pf.fail)("worker file %s" % rel,
                                                  p if os.path.exists(p) else "not found: %s" % p)

    # ---- 7. environment ----------------------------------------------------
    if CRAB_IMPORT_ERROR is None:
        pf.ok("CRABClient import", "ok")
    else:
        pf.fail("CRABClient import",
                "%s -- run: source /cvmfs/cms.cern.ch/common/crab-setup.sh" % CRAB_IMPORT_ERROR)
    for var in ("CMSSW_BASE", "SCRAM_ARCH"):
        (pf.ok if os.environ.get(var) else pf.fail)("env %s" % var,
                                                    os.environ.get(var, "unset -- run cmsenv"))
    try:
        out = subprocess.run(["voms-proxy-info", "-timeleft"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True)
        left = int((out.stdout or "0").strip() or 0)
        if left <= 0:
            pf.fail("VOMS proxy", "expired/absent -- voms-proxy-init -voms cms -rfc --valid 168:00")
        elif left < 24 * 3600:
            pf.warn("VOMS proxy", "only %.1f h left" % (left / 3600.0))
        else:
            pf.ok("VOMS proxy", "%.1f h left" % (left / 3600.0))
    except (OSError, ValueError) as e:
        pf.fail("VOMS proxy", "voms-proxy-info unusable: %s" % e)
    if os.access(os.getcwd(), os.W_OK):
        pf.ok("cwd writable", "crab_args.txt / log can be written here")
    else:
        pf.fail("cwd writable", "%s is not writable" % os.getcwd())

    # ---- 8. datasets -------------------------------------------------------
    pf.note("-" * 78)
    if not datasets:
        pf.fail("datasets", "config has no datasets")
        return pf.finish()
    pf.ok("dataset count", str(len(datasets)))
    seen, dups, malformed, tiers = {}, [], [], {}
    for key, ds in datasets.items():
        if not isinstance(ds, str) or not _DATASET_RE.match(ds):
            malformed.append((key, ds))
            continue
        tiers[ds.rsplit("/", 1)[1]] = tiers.get(ds.rsplit("/", 1)[1], 0) + 1
        if ds in seen:
            dups.append((key, seen[ds]))
        seen[ds] = key
    if malformed:
        pf.fail("dataset path syntax", "%d malformed, e.g. %s" % (len(malformed), malformed[:2]))
    else:
        pf.ok("dataset path syntax", "all %d match /primary/processed/TIER" % len(datasets))
    if dups:
        pf.fail("duplicate datasets", "%s" % dups[:3])
    else:
        pf.ok("duplicate datasets", "none")
    pf.ok("tier mix", ", ".join("%s=%d" % kv for kv in sorted(tiers.items())))
    mc = [k for k, v in datasets.items() if v.endswith("SIM")]
    data = [k for k, v in datasets.items() if not v.endswith("SIM")]
    pf.ok("MC / Data split", "%d MC, %d Data" % (len(mc), len(data)))
    if data and bsel and os.path.exists(bsel):
        rules = [l.strip() for l in open(bsel) if l.strip() and not l.strip().startswith("#")]
        if any(r.split()[1:2] == ["genWeight"] for r in rules if r.split()[0].lower() == "keep"):
            pf.ok("Data + MC-only keeps", "harmless: keep patterns matching nothing are ignored")

    # ---- 9. per-task preview (names/paths CRAB will use) --------------------
    # getUsername() talks to the proxy/CRAB config, so it can raise when the
    # proxy is expired. Never let that abort the preflight: the whole point is
    # to always reach finish() and leave a complete log.
    try:
        username = getUsername()
    except Exception as e:
        username = os.environ.get("USER", "UNKNOWN_USER")
        pf.warn("CRAB getUsername()", "failed (%s); preview uses $USER=%s" % (e, username))
    base_out = str(common.get("output_base", "")).lstrip("/")
    work_area = common.get("jobID", "crab_projects")
    pf.note("-" * 78)
    pf.note("Per-task preview (workArea=%s, storage=%s):" % (work_area, common.get("site")))
    pf.note("  outLFNDirBase = /store/user/%s/%s" % (username, base_out))
    for i, (key, ds) in enumerate(sorted(datasets.items())):
        if i >= args.preview and args.preview >= 0:
            pf.note("  ... (%d more; use --preview -1 for all)" % (len(datasets) - args.preview))
            break
        pf.note("  %-30s requestName=%-30s %s" % (key, key, ds))
    existing = [d for d in glob.glob(os.path.join(work_area, "crab_*")) if os.path.isdir(d)]
    if existing:
        pf.warn("existing CRAB projects", "%d dir(s) in %s -- submit would clash/skip: e.g. %s"
                % (len(existing), work_area, os.path.basename(existing[0])))
    else:
        pf.ok("existing CRAB projects", "none in %s" % work_area)

    # ---- 10. optional DAS existence check ----------------------------------
    if args.check_das:
        pf.note("-" * 78)
        if subprocess.run(["which", "dasgoclient"], stdout=subprocess.PIPE).returncode != 0:
            pf.fail("dasgoclient", "not found -- cannot check dataset existence")
        else:
            # NOTE (2026-07-27 fix): the PLAIN-TEXT output of
            # `dasgoclient -query "summary dataset=..."` is a column layout, not
            # `nevents=N`, so the old regex matched nothing and reported ALL
            # datasets as unresolvable (false FAIL on all 81, lxplus log
            # 20260727_094941). Use -json and read summary[0].nevents, exactly
            # as script/das_ul18_scan.sh does (that path is proven on lxplus).
            missing, total_ev = [], 0
            for key, ds in sorted(datasets.items()):
                q = subprocess.run(["dasgoclient", "-query", "summary dataset=%s" % ds,
                                    "-json"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                nev = None
                try:
                    for rec in json.loads(q.stdout or "[]"):
                        for smry in (rec.get("summary") or []):
                            if smry.get("nevents") is not None:
                                nev = int(smry["nevents"])
                                break
                        if nev is not None:
                            break
                except (ValueError, TypeError, KeyError):
                    nev = None
                if nev is None:      # fall back to a plain-text scrape
                    m = re.search(r"nevents\s*[:=]\s*(\d+)", q.stdout or "")
                    nev = int(m.group(1)) if m else None
                if nev is None:
                    missing.append(key)
                else:
                    total_ev += nev
            if missing:
                pf.fail("DAS dataset existence", "%d not resolvable: %s" % (len(missing), missing[:5]))
            else:
                pf.ok("DAS dataset existence", "all %d found, total nevents=%s"
                      % (len(datasets), format(total_ev, ",")))
    return pf.finish()


def main(args):
    _require_crab()
    check_voms()

    # 1. Load Configuration
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)

    with open(args.config, 'r') as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"YAML Error: {e}")
            sys.exit(1)

    common = cfg.get('common', {})
    datasets = cfg.get('datasets', {})
    
    logger.info(f"Loaded Configuration: {args.config}")
    logger.info(f"Common Work Area: {common.get('jobID', 'crab_projects')}")
    logger.info(f"Target Datasets: {len(datasets)}")
    logger.info("="*60)

    # 2. Setup CRAB Configuration
    conf = config()
    
    # -- General --
    conf.General.transferOutputs = True
    conf.General.transferLogs = True
    conf.General.workArea = common.get('jobID', 'crab_projects')
    
    # -- JobType --
    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py'
    conf.JobType.scriptExe = 'crab/crab_script.py' 
    conf.JobType.maxMemoryMB = common.get('max_memory', 2500)
    
    splitting_mode = common.get('splitting', 'Automatic')
    if splitting_mode != 'Automatic':
        conf.JobType.maxJobRuntimeMin = common.get('max_runtime', 600)


    # ------------------------------------------------------
    # Input Filename Logic
    # ------------------------------------------------------
    # Files to ship to worker node
    # CRAB will flatten directory structure, placing it in root dir on worker.
    conf.JobType.inputFiles = ['script/run_postproc.py'] # Main Script

    # ------------------------------------------------------
    # Module Handling (List-based YAML)
    # ------------------------------------------------------
    # YAML Format: analysis_module: ["modules/jetsMETcut.py", "MODULES"]
    
    module_cfg = common.get('analysis_module') # Returns a list: [path, list_name]
    worker_module_arg = None # Will store string "jetsMETcut:MODULES" for worker

    if module_cfg and len(module_cfg) == 2:
        local_path = module_cfg[0]  # e.g., "modules/jetsMETcut.py"
        list_var   = module_cfg[1]  # e.g., "MODULES"

        if os.path.exists(local_path):
            conf.JobType.inputFiles.append(local_path)
            logger.info(f"Adding Module File: {local_path}")

            # ------------------------------------------------------
            # Auto-include helper modules from the same directory.
            #
            # CRAB flattens the sandbox into the worker's cwd, so any
            # helper module the analysis module imports must be shipped
            # explicitly. We ship EVERY sibling ".py" in the module
            # directory (except the analysis module itself and dunders).
            #
            # NOTE: previously only files matching "_*.py" were auto-
            # included, which coupled a helper's *name* to whether it
            # shipped — renaming a helper without a leading underscore
            # silently dropped it from the sandbox and broke the job at
            # import time. Naming is now decoupled from shipping.
            #
            # The analysis module must still resolve the helper import
            # in a flat/top-level context (CRAB imports it flat): put
            # its own directory on sys.path via __file__, then import.
            # ------------------------------------------------------
            module_dir = os.path.dirname(local_path) or "."
            analysis_basename = os.path.basename(local_path)
            helper_files = sorted(
                h for h in glob.glob(os.path.join(module_dir, "*.py"))
                if os.path.basename(h) != analysis_basename
                and not os.path.basename(h).startswith("__")
            )
            for h in helper_files:
                conf.JobType.inputFiles.append(h)
                logger.info(f"  -> Auto-included helper: {h}")

            # Prepare Argument for Worker Node
            # Worker sees flat files. "modules/jetsMETcut.py" -> "jetsMETcut.py"
            # Argument format: "jetsMETcut:MODULES" (drop extension, append list var)
            file_basename = os.path.basename(local_path) # jetsMETcut.py
            module_name_only = os.path.splitext(file_basename)[0] # jetsMETcut
            worker_module_arg = f"{module_name_only}:{list_var}"
            
        else:
            logger.error(f"CRITICAL: Module file not found at {local_path}")
            sys.exit(1)
    elif module_cfg:
        logger.error(f"YAML Error: 'analysis_module' must be a list with 2 elements [path, list_name]. Got: {module_cfg}")
        sys.exit(1)

    # ------------------------------------------------------
    # Branch File Handling
    # ------------------------------------------------------
    branch_sel = common.get('branch_file') # Renamed from branch_path
    
    if branch_sel:
        if os.path.exists(branch_sel):
            conf.JobType.inputFiles.append(branch_sel)
            logger.info(f"Adding Branch File: {branch_sel}")
        else:
            logger.error(f"CRITICAL: Branch file not found at {branch_sel}")
            sys.exit(1)
            
    # Add YAML Config (Provenance)
    conf.JobType.inputFiles.append(args.config)


    # ------------------------------------------------------
    # Output Filename Logic
    # ------------------------------------------------------
    # Default output filename (should match process.output.fileName in the PSet)
    # Rule 6: must match crab/PSet.py process.output.fileName exactly.
    # 2026-07-26: renamed slimmedNtuple.root -> forgedNtuple.root (D-F).
    # NOTE: ntuples produced BEFORE this date are on disk as slimmedNtuple_*.root
    # (e.g. campaign ttHH2017UL_fullNano_v20); the downstream filelist makers
    # therefore accept both names. Do not "clean up" that dual matching until
    # every old campaign has been reproduced.
    out_name = "forgedNtuple.root"


    # -- Arguments File Generation --
    args_file = "crab_args.txt"
    with open(args_file, "w") as f:
        # Branch Arg
        if branch_sel: 
            f.write(f"-b\n{os.path.basename(branch_sel)}\n")
        
        # Module Arg (Optimized)
        if worker_module_arg: 
            f.write(f"-I\n{worker_module_arg}\n")
            
        if common.get('max_events'): 
            f.write(f"-N\n{common.get('max_events')}\n")

        # Pass the output filename to the worker node script
        f.write(f"--output-file={out_name}\n")

    conf.JobType.inputFiles.append(args_file)
    conf.JobType.scriptArgs = [] 

    # ------------------------------------------------------
    # Output Files Configuration (Provenance)
    # ------------------------------------------------------
    # Instruct CRAB to transfer these files back to the output storage.
    # 1. out_name: Main output file
    # 2. crab_args.txt: List of arguments used for the job
    # 3. YAML Config: The configuration file used for submission
    conf.JobType.outputFiles = [
        out_name,            
        ##'crab_args.txt',
        ##os.path.basename(args.config)
    ]

    # -- Data & Site --
    conf.Data.inputDBS = 'global'
    
    # [FIX] Splitting Logic (Automatic vs FileBased)
    conf.Data.splitting = splitting_mode
    
    # units_per_job means different things:
    # Automatic -> Minutes (e.g., 180)
    # FileBased -> Number of Files (e.g., 1)
    #
    # =========================================================================
    # !!  FileBased: DO NOT LOWER units_per_job WITHOUT CHECKING JOB COUNTS  !!
    # =========================================================================
    # njobs_per_task = ceil(nfiles_of_that_dataset / units_per_job), and CRAB
    # REFUSES any task with more than CRAB_MAX_JOBS_PER_TASK (= 10,000) jobs.
    # The refusal is SERVER-SIDE and looks like success from here:
    #   * crabCommand('submit') returns fine and this script logs "Submitting..."
    #   * the server then parks the task at SUBMITREFUSED with
    #     "The splitting on your task generated N jobs. The maximum number of
    #      jobs in each task is 10000"
    #   * jobsPerStatus stays empty -> `--report` shows a row of all zeros,
    #     which is indistinguishable from "submitted, not started yet"
    #   * `--resubmit` CANNOT fix it (resubmit only requeues FAILED jobs of a
    #     task that reached the scheduler); the task must be re-submitted
    # So an entire dataset can silently produce nothing for days. This is not
    # hypothetical: it happened on 2026-07-27 in the sibling repo
    # TTHHGenCategoryTools (2018 TTbar_SemiLep, 10,010 MiniAOD files at
    # units_per_job 1). Write-up: TTHHGenCategoryTools/docs/08_troubleshooting.md
    # T-19; decision + rule: that repo's docs/04_decisions.md D15.
    #
    # Why the ttHH configs here are currently safe: they run over NanoAOD, whose
    # file counts are ~20x smaller than MiniAOD. The largest 2018UL dataset BY
    # FILE COUNT is WJetsToLNu_HT200To400_ext1 with 780 files -> 780 jobs at
    # units_per_job 1 (NOT TTbar_SemiLep -- that one is largest by EVENTS,
    # 476M, but only 4th by files at 391; ranking files != ranking events, and
    # it is files that set the job count). The 2018UL campaign is 7,466 jobs
    # across 85 TASKS, and the limit is PER TASK, not per campaign -- do not read
    # the campaign total as if it were near the limit.
    # DANGER CASE for this repo: pointing a config at MiniAOD, or adding a
    # dataset with >10,000 files, while units_per_job is 1.
    #
    # NOTE (gap, 2026-07-27): unlike the extend submitter, `--preflight
    # --check-das` here does NOT yet compute per-task job counts. Until it does,
    # check by hand for any dataset you suspect is large:
    #     dasgoclient -query "summary dataset=<DS>" -json | grep -o '"nfiles":[0-9]*'
    # Raising units_per_job is always safe for this limit and, for a passthrough
    # (noop) job, has no effect on output correctness.
    user_units = common.get('units_per_job', 1)
    ##user_units = common.get('units_per_job', 180) # Default 180 mins

    conf.Data.unitsPerJob = user_units
    conf.Data.publication = False

    username = getUsername()
    base_out = common.get('output_base', '')
    if base_out:
         conf.Data.outLFNDirBase = f'/store/user/{username}/{base_out.lstrip("/")}'
    else:
         conf.Data.outLFNDirBase = f'/store/user/{username}/'

    conf.Site.storageSite = common.get('site', 'T3_KR_KNU')

    # Accumulators for --report (printed once, after the loop, so columns align)
    report_rows = []
    report_unknown = set()

    # 3. Process Jobs
    for short_name, dataset in datasets.items():
        req_name = short_name.replace("-", "_")

        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        conf.Data.outputDatasetTag = short_name

        project_dir = os.path.join(conf.General.workArea, "crab_" + req_name)

        print(f"[{short_name}] Processing...")

        # -- STATUS Action --
        if args.status:
            if os.path.isdir(project_dir):
                try:
                    subprocess.run(["crab", "status", "-d", project_dir], check=True)
                except: pass
            else:
                logger.warning("Project not found.")
            continue

        # -- REPORT Action (compact per-sample job-state summary) --
        if args.report:
            if os.path.isdir(project_dir):
                try:
                    # Silence CRAB's verbose status dump; we only want the dict.
                    with contextlib.redirect_stdout(io.StringIO()):
                        res = crabCommand('status', dir=project_dir)
                    row, unknown = summarize_status(res.get('jobsPerStatus', {}))
                    report_rows.append((short_name, row))
                    report_unknown |= unknown
                except Exception as e:
                    logger.error(f"Status query failed for {short_name}: {e}")
                    report_rows.append((short_name, summarize_status({})[0]))
            else:
                logger.warning("Project not found.")
            continue

        # -- RESUBMIT Action (explicit; failed jobs only, default resources) --
        if args.resubmit:
            if os.path.isdir(project_dir):
                logger.info("Resubmitting (explicit)...")
                try:
                    crabCommand('resubmit', dir=project_dir)
                except Exception as e:
                    logger.error(f"Resubmit Failed: {e}")
            else:
                logger.warning("Project not found (nothing to resubmit).")
            continue

        # -- SUBMIT / RESUBMIT Logic (default action) --
        if os.path.isdir(project_dir):
            logger.info("Resubmitting...")
            try:
                crabCommand('resubmit', dir=project_dir)
            except Exception as e:
                logger.error(f"Resubmit Failed: {e}")
        else:
            logger.info("Submitting...")
            try:
                crabCommand('submit', config=conf)
            except Exception as e:
                logger.error(f"Submit Failed: {e}")

        # -- KILL Action --
        if args.kill:
            if os.path.isdir(project_dir):
                logger.info("Action: KILLING Task")
                try:
                    crabCommand('kill', dir=project_dir)
                    logger.info("Kill command sent successfully.")
                except HTTPException as hte:
                    logger.error(f"Kill Failed: {hte.headers}")
                except Exception as e:
                    logger.error(f"Kill Failed: {e}")
            else:
                logger.warning(f"Project directory not found (nothing to kill): {project_dir}")
            print("-" * 60)
            continue

    # -- Post-loop: print the compact report (if requested) --
    if args.report:
        if report_rows:
            print_report(report_rows)
        if report_unknown:
            logger.warning(
                "Unknown CRAB job state(s) counted under 'others': "
                f"{sorted(report_unknown)}. The report code does not recognise "
                "these -- add them to REPORT_COLUMNS / KNOWN_OTHER_STATES in "
                "crab/submit_crab.py (see summarize_status()), and inspect the "
                "full `crab status -d <project_dir>` output for what they mean."
            )

    # -- Post-loop: remind about memory/walltime resubmits (submit & resubmit only) --
    if not (args.status or args.report or args.kill):
        logger.info("-" * 60)
        logger.info("NOTE: (re)submit here uses DEFAULT resources. Jobs that failed on "
                    "memory or walltime will fail again on a plain resubmit.")
        logger.info("      Resubmit those by hand in the CRAB project dir with raised limits, e.g.:")
        logger.info("        crab resubmit -d <workArea>/crab_<reqName> --maxmemory=4000 --maxjobruntime=2700")
        logger.info("      See docs/troubleshooting.md (CRAB resubmit) for exit codes and details.")

    # Cleanup temp file
    if os.path.exists(args_file):
        os.remove(args_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YAML based CRAB Manager")
    parser.add_argument("-c", "--config", required=True, help="Path to YAML config")
    parser.add_argument("--status", action="store_true", help="Run full 'crab status' for every task in the config")
    parser.add_argument("--report", action="store_true",
                        help="Compact per-sample job-state summary "
                             "(done/run/idle/transf/fail/other) -- simpler and "
                             "easier to read than full 'crab status'")
    parser.add_argument("--resubmit", action="store_true",
                        help="Explicitly resubmit failed jobs in existing tasks "
                             "(default resources; raise memory/walltime by hand)")
    parser.add_argument("--kill", action="store_true", help="Kill all jobs defined in the config")
    parser.add_argument("--preflight", action="store_true",
                        help="READ-ONLY pre-submission check: config schema, module + "
                             "branch file, Rule-6 output filename, worker files, CRAB/CMSSW/"
                             "proxy environment, dataset path syntax/duplicates, and a "
                             "per-task name/path preview. Submits nothing; writes "
                             "preflight_<config>_<timestamp>.log; exits non-zero on any FAIL.")
    parser.add_argument("--check-das", action="store_true",
                        help="With --preflight: additionally query DAS for every dataset "
                             "(existence + nevents). Slower (one dasgoclient call per dataset).")
    parser.add_argument("--preview", type=int, default=10,
                        help="With --preflight: how many per-task preview lines to print "
                             "(-1 = all). Default 10.")
    args = parser.parse_args()
    if args.preflight:
        sys.exit(run_preflight(args))
    main(args)
