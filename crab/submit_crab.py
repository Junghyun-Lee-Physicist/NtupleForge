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
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --kill      # kill all tasks (never submits)

[Exit status] (2026-09-23)
0 = every CRAB call of this run succeeded or had nothing to do.
1 = at least one submit / resubmit / kill / status query failed, a stale project
    dir blocked a dataset, or datasets were skipped after a proxy failure.
The SUMMARY block printed at the end names each one; script/runlog.sh records
the code as EXIT. Before 2026-09-23 every failure was logged and the script
still exited 0 (the 2024 pilot: "Submit Failed: Problems delegating My-proxy",
EXIT 0; docs/05_troubleshooting.md A22).

[Interactive prompt] CRAB delegates a 30-day credential to myproxy and renews
it when less than 15 days are left; that renewal asks for the GRID pass phrase
on the terminal. Paste crab commands one line at a time, or run
`crab createmyproxy --days 30` alone first, so no pasted line is read as the
pass phrase.
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

# --- recipe / skim / audit (2026-09-28, docs/12_fastpath_workflow_plan.md 2.2-2.3) ---
# YAML `common` keys, all optional (absent = exactly the behaviour before):
#   recipe: slim            the only recipe implemented here (categorize / derive = Phase 0)
#   skim:   none | 6jcount | 6j20 | 6j25 | 6j30 | 6j20ht400   (script/forge_skims.py)
#   audit:  true | false    default: true when a skim is set, else false
# A skim or the audit ships script/forge_skims.py and script/forge_audit.py and
# adds --skim / --audit / --forge-git to crab_args.txt (run_postproc.py).
FORGE_FILES = ("script/forge_skims.py", "script/forge_audit.py")


def forge_options(common):
    """(recipe, skim or None, audit) from the YAML common block; ValueError if invalid."""
    recipe = common.get("recipe") or "slim"
    if recipe != "slim":
        raise ValueError("recipe %r is not implemented in this submitter (only 'slim'; categorize / derive "
                         "are Phase 0, docs/11_unified_forge_plan.md)" % (recipe,))
    skim = common.get("skim")
    skim = None if skim in (None, "", "none") else str(skim)
    if skim is not None:
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, os.path.join(repo, "script"))
        try:
            import forge_skims
        except ImportError as e:
            raise ValueError("skim %r set but script/forge_skims.py is not importable (%s)" % (skim, e))
        if skim not in forge_skims.NAMES:
            raise ValueError("skim %r is not in script/forge_skims.py (known: %s)"
                             % (skim, ", ".join(forge_skims.NAMES)))
    audit = common.get("audit")
    if audit is None:
        audit = skim is not None
    elif not isinstance(audit, bool):
        raise ValueError("audit must be true or false, got %r" % (audit,))
    return recipe, skim, audit


# --- input fallback / site blacklist (2026-09-30, D-2026-09-30-p7, docs/05 A24) ---
# YAML `common` keys, both optional:
#   aaa_fallback:   true (default) | false | "root://<redirector>/"
#                   true adds --input-fallback root://cms-xrd-global.cern.ch/ to
#                   crab_args.txt: a job CRAB ran at a site without its input
#                   (overflow) copies it through AAA (xrdcp) and reads the copy
#                   instead of dying with 50115 (run_postproc.py resolve_inputs).
#                   false = the behaviour before 2026-09-30.
#   site_blacklist: [T2_US_Xyz, ...] or "T2_US_Xyz,T2_..."  -> config.Site.blacklist
#                   (CRAB site names, or a CRAB wildcard such as T2_US_*)
AAA_REDIRECTOR = "root://cms-xrd-global.cern.ch/"
REDIRECTOR_RE = re.compile(r"^root://[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:[0-9]+)?/?$")
SITE_RE = re.compile(r"^T[1-3]_[A-Z]{2}(_[A-Za-z0-9]+)+$")     # the pattern CRAB checks a site name with
SITE_GLOB_RE = re.compile(r"^T[1-3]_[A-Za-z0-9_]*\*$")         # a wildcard (CRAB expands it)


def job_options(common):
    """(input fallback URL or None, [blacklisted sites]) from the YAML common block; ValueError if invalid."""
    fb = common.get("aaa_fallback", True)
    if fb is True or fb is None:
        url = AAA_REDIRECTOR
    elif fb is False:
        url = None
    elif isinstance(fb, str) and REDIRECTOR_RE.match(fb.strip()):
        url = fb.strip().rstrip("/") + "/"
    else:
        raise ValueError("aaa_fallback must be true, false or a redirector URL root://<host>[:<port>]/, got %r" % (fb,))
    bl = common.get("site_blacklist")
    if bl is None:
        bl = []
    elif isinstance(bl, str):
        bl = [x.strip() for x in bl.split(",") if x.strip()]
    if not isinstance(bl, list) or not all(isinstance(x, str) for x in bl):
        raise ValueError("site_blacklist must be a list of site names, got %r" % (bl,))
    bad = [x for x in bl if not (SITE_RE.match(x) or SITE_GLOB_RE.match(x))]
    if bad:
        raise ValueError("site_blacklist: not a CMS site name: %s" % ", ".join(bad))
    return url, bl


# --- input copy (2026-10-01, P7.1, docs/05 A27) ---
# YAML `common` key, optional:
#   input_copy: true (default) | false
#               true adds --input-copy to crab_args.txt: run_postproc.py copies a
#               remote site PFN (root://) into the job directory with xrdcp first
#               and NanoAODTools and the audit read the copy (one remote access;
#               the 2024 jobs at T1_US_FNAL died on the open after the probe).
#               false = the behaviour of 2026-09-30 (open at the site, read through it).
def copy_option(common):
    """True when run_postproc.py gets --input-copy; ValueError if the YAML value is not a boolean."""
    v = common.get("input_copy", True)
    if v is None:
        return True
    if not isinstance(v, bool):
        raise ValueError("input_copy must be true or false, got %r" % (v,))
    return v


# Tracked paths whose modification does not change what a job runs: runlog.sh
# appends a line to script/runlogs/LEDGER.tsv at every step, so without this a
# checkout that has just run its local checks would always be '+dirty'.
FORGE_GIT_IGNORE = ("script/runlogs/",)


def forge_shipped(config_path, common):
    """The files of this checkout that a job gets (as main() ships them): for the
    preflight's forge git line, which runs before the CRAB config exists."""
    files = [config_path, "crab/PSet.py", "crab/crab_script.py", "script/run_postproc.py"] + list(FORGE_FILES)
    module_cfg = common.get("analysis_module")
    if isinstance(module_cfg, list) and len(module_cfg) == 2 and os.path.exists(str(module_cfg[0])):
        mod = str(module_cfg[0])
        files.append(mod)
        files += sorted(h for h in glob.glob(os.path.join(os.path.dirname(mod) or ".", "*.py"))
                        if os.path.basename(h) != os.path.basename(mod) and not os.path.basename(h).startswith("__"))
    if common.get("branch_file"):
        files.append(str(common.get("branch_file")))
    return files


def forge_git(paths=()):
    """Short commit of this checkout for ForgeProvenance. '+dirty' if tracked files
    outside script/runlogs/ are modified (both sides of a rename count), '+untracked'
    if one of `paths` (files the jobs get) is not in git; 'unknown' without git."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        head = subprocess.run(["git", "-C", repo, "rev-parse", "--short=12", "HEAD"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
        if head.returncode != 0 or not head.stdout.strip():
            return "unknown"
        st = subprocess.run(["git", "--no-optional-locks", "-C", repo, "status", "--porcelain", "--untracked-files=no"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
        if st.returncode != 0:
            return "unknown"
        changed = []
        for line in st.stdout.splitlines():
            if len(line) > 3:
                changed += [q.strip().strip('"') for q in line[3:].split(" -> ")]
        dirty = any(not q.startswith(FORGE_GIT_IGNORE) for q in changed)
        rel = []
        for q in paths:
            a = os.path.abspath(str(q))
            if a.startswith(repo + os.sep) and os.path.exists(a):
                rel.append(os.path.relpath(a, repo))
        untracked = False
        if rel:
            ls = subprocess.run(["git", "--no-optional-locks", "-C", repo, "ls-files", "--error-unmatch", "--"] + rel,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30)
            untracked = ls.returncode != 0
        return head.stdout.strip() + ("+dirty" if dirty else "") + ("+untracked" if untracked else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


# --- Outcome helpers (2026-09-23) --------------------------------------------
# CRABClient facts these rely on (read in the v3.260630 source, the client on
# lxplus that day):
#   * SubCommand.__init__ creates the project dir <workArea>/crab_<requestName>
#     (createWorkArea) BEFORE the VOMS and myproxy steps, so a submit that dies
#     on the proxy still leaves the dir behind;
#   * Commands/submit.py writes <project dir>/.requestcache (createCache) only
#     after the server has returned a task name.
# Hence a project dir WITHOUT .requestcache is stale: the server never saw that
# task. Treating it as an existing task (the auto-resubmit branch) fails with
# "Cannot find .requestcache file", and a fresh `crab submit` refuses it with
# "Working area ... already exists". Remove it and submit again.
def has_task_cache(project_dir):
    return os.path.isfile(os.path.join(project_dir, ".requestcache"))


def is_proxy_problem(exc):
    """True for a failure every later CRAB call of this run would repeat (VOMS,
    myproxy, user certificate). For myproxy each repeat would also ask for the
    GRID pass phrase again, so the loop stops instead."""
    return type(exc).__name__ == "ProxyCreationException" or "proxy" in str(exc).lower()


def one_line(text, width=160):
    s = " ".join(str(text).split())
    return s if len(s) <= width else s[:width - 3] + "..."


class Outcomes:
    """Per-dataset results of one run, printed as one SUMMARY block at the end.
    exit_code() is 1 if anything FAILED or was SKIPPED, else 0 (WARN is 0)."""

    def __init__(self, action, n_datasets):
        self.action = action
        self.n_datasets = n_datasets
        self.rows = []            # (level, key, what, detail)
        self.stale_dirs = []      # project dirs without .requestcache

    def add(self, level, key, what, detail=""):
        self.rows.append((level, key, what, one_line(detail)))

    def count(self, level):
        return sum(1 for r in self.rows if r[0] == level)

    def exit_code(self):
        return 1 if (self.count("FAILED") or self.count("SKIPPED")) else 0

    def print_summary(self):
        print("=" * 78, flush=True)
        print("SUMMARY (%s): %d dataset(s): %d OK, %d WARN, %d FAILED, %d SKIPPED"
              % (self.action, self.n_datasets, self.count("OK"), self.count("WARN"),
                 self.count("FAILED"), self.count("SKIPPED")))
        # OK rows carry information (task name, request sent) only for actions
        # that change something; for status/report the table above has them.
        levels = ("OK", "WARN", "FAILED", "SKIPPED") if self.action in ("submit", "resubmit", "kill") \
            else ("WARN", "FAILED", "SKIPPED")
        for level in levels:
            for lv, key, what, detail in self.rows:
                if lv == level:
                    print("  %-7s %-40s %-9s %s" % (lv, key, what, detail))
        if self.stale_dirs:
            print("  hint: stale project dir(s), never seen by the server (no .requestcache):")
            for d in self.stale_dirs:
                print("        rm -r %s" % d)
            print("        then submit again (the command without an action flag).")
        print("RESULT: %s" % ("OK" if self.exit_code() == 0 else "FAILED (exit 1)"))
        print("=" * 78, flush=True)


def resubmit_task(out, key, project_dir):
    """`crab resubmit` on an existing task; records the outcome in `out`.
    Returns the exception if the call raised, else None."""
    try:
        res = crabCommand('resubmit', dir=project_dir)
    except Exception as e:
        logger.error(f"Resubmit Failed: {e}")
        out.add("FAILED", key, "resubmit", e)
        return e
    if res is None:
        # CRABClient returns None when it sends nothing: no failed jobs, or the
        # task status is not available yet (its own message says which).
        out.add("WARN", key, "resubmit", "no request sent (nothing to resubmit, or status not ready; see CRAB message)")
    elif res.get('commandStatus') == 'SUCCESS':
        out.add("OK", key, "resubmit", "resubmit request sent")
    else:
        out.add("FAILED", key, "resubmit", "server did not accept the resubmit")
    return None

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

    # ---- 4b. recipe / skim / audit (2026-09-28) -------------------------------
    try:
        recipe, skim, audit = forge_options(common)
    except ValueError as e:
        pf.fail("recipe / skim / audit", str(e))
        recipe, skim, audit = None, None, False
    if recipe:
        if skim:
            import forge_skims   # forge_options put script/ on sys.path
            pf.ok("recipe", "slim (postproc; skim %s = %s; audit %s)"
                  % (skim, forge_skims.get(skim)[0], "on" if audit else "OFF"))
            if not audit:
                pf.warn("audit", "off with a skim: nothing records the sums of weights before the skim")
        else:
            pf.ok("recipe", "slim (postproc; no event skim; audit %s)" % ("on" if audit else "off"))
        if skim or audit:
            repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            for rel in FORGE_FILES:
                q = os.path.join(repo, rel)
                (pf.ok if os.path.exists(q) else pf.fail)("worker file %s" % rel, q if os.path.exists(q)
                                                          else "not found: %s" % q)
            g = forge_git(forge_shipped(args.config, common))
            (pf.warn if g == "unknown" or "+" in g else pf.ok)(
                "forge git (ForgeProvenance)", g + ("  (modified tracked files: the commit does not name the code)"
                                                    if "+dirty" in g else "")
                + ("  (a file the jobs get is not in git)" if "+untracked" in g else ""))
            if isinstance(module_cfg, list) and module_cfg and os.path.basename(str(module_cfg[0])) != "noop.py":
                pf.warn("audit closure C1", "assumes the module drops no event; %s is not modules/noop.py"
                        % module_cfg[0])

    # ---- 4c. input fallback, site blacklist, job resources (2026-09-30) ------
    try:
        fb_url, blacklist = job_options(common)
    except ValueError as e:
        pf.fail("aaa_fallback / site_blacklist", str(e))
        fb_url, blacklist = None, []
    else:
        if fb_url:
            pf.ok("input fallback", "%s (an input the job's site cannot open is copied through AAA with xrdcp "
                                    "and read from the copy; docs/05 A24)" % fb_url)
        else:
            pf.warn("input fallback", "off (aaa_fallback: false): a job CRAB runs at a site without its input "
                                      "dies with 50115 (docs/05 A24)")
        pf.ok("site blacklist", ", ".join(blacklist) if blacklist else "none")
    try:
        input_copy = copy_option(common)
    except ValueError as e:
        pf.fail("input_copy", str(e))
    else:
        if input_copy:
            pf.ok("input copy", "on (a remote site PFN is copied into the job directory with xrdcp first and read "
                                "from the copy: one remote access; docs/05 A27)")
        else:
            pf.warn("input copy", "off (input_copy: false): the job opens the site PFN twice or more (probe, "
                                  "NanoAODTools, audit); at T1_US_FNAL the open after the probe failed in 2024 "
                                  "(docs/05 A27)")
    split_mode = common.get("splitting", "Automatic")
    pf.ok("job resources", "max_memory %s MB, %s" % (
        common.get("max_memory", 2500),
        "max_runtime %s min" % common.get("max_runtime", 600) if split_mode != "Automatic"
        else "max_runtime CRAB default (Automatic splitting)"))

    # ---- 5. Rule 6: output filename hardcoded in two places ------------------
    here = os.path.dirname(os.path.abspath(__file__))
    pset = os.path.join(here, "PSet.py")
    submit_src = open(os.path.abspath(__file__)).read()
    m_sub = re.search(r'out_name\s*=\s*"([^"]+)"', submit_src)
    m_pset = None
    if os.path.exists(pset):
        # Accept BOTH quote styles: docs/07_DeveloperGuideline.md Rule 6 writes the
        # pattern with double quotes while crab/PSet.py currently uses single ones.
        # The old single-quote-only regex made a guideline-conformant PSet fail the
        # check with "could not parse" (fail-closed, but a false alarm). 2026-08-17.
        m_pset = re.search(r"""fileName\s*=\s*cms\.untracked\.string\(\s*(['"])(.+?)\1\s*\)""",
                           open(pset).read())
    pset_name = m_pset.group(2) if m_pset else None
    if m_sub and m_pset:
        if m_sub.group(1) == pset_name:
            pf.ok("Rule 6 output filename", "%s (submit_crab.py == PSet.py)" % m_sub.group(1))
        else:
            pf.fail("Rule 6 output filename",
                    "MISMATCH: submit_crab.py=%s vs PSet.py=%s" % (m_sub.group(1), pset_name))
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
            pf.ok("Data + MC-only keeps", "the output just lacks them; ROOT prints one 'Error in "
                  "<TTree::SetBranchStatus>' line per such pattern and job ('unknown branch' or 'No branch name is "
                  "matching wildcard'; --audit reports them as C2w WARN)")

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
    existing = sorted(d for d in glob.glob(os.path.join(work_area, "crab_*")) if os.path.isdir(d))
    # 2026-09-23: split the old single WARN. A dir WITHOUT .requestcache was
    # left by a submit that never reached the server (has_task_cache); the
    # submit branch now refuses it, so it is a FAIL here. A dir WITH it is a
    # live task that a plain submit auto-RESUBMITS (the old text "would
    # clash/skip" was wrong).
    stale = [d for d in existing if not has_task_cache(d)]
    live = [d for d in existing if has_task_cache(d)]
    if stale:
        pf.fail("stale CRAB project dirs",
                "%d dir(s) without .requestcache (an earlier submit never reached the server), "
                "e.g. %s -- rm -r them, then submit" % (len(stale), stale[0]))
    if live:
        pf.warn("existing CRAB projects", "%d task(s) in %s -- a plain submit auto-RESUBMITS them: e.g. %s"
                % (len(live), work_area, os.path.basename(live[0])))
    if not existing:
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
    try:
        forge_recipe, forge_skim, forge_audit_on = forge_options(common)
        input_fallback, site_blacklist = job_options(common)
        input_copy = copy_option(common)
    except ValueError as e:
        logger.error(f"YAML Error: {e}")
        sys.exit(1)
    
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

    # Event skim / audit helpers (run_postproc.py imports them only with --skim / --audit)
    if forge_skim or forge_audit_on:
        for rel in FORGE_FILES:
            if not os.path.exists(rel):
                logger.error(f"CRITICAL: {rel} not found (needed for skim / audit)")
                sys.exit(1)
            conf.JobType.inputFiles.append(rel)
            logger.info(f"Adding Forge File: {rel}")
        logger.info(f"Recipe: {forge_recipe}, skim {forge_skim or 'none'}, audit {'on' if forge_audit_on else 'off'}")


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

        if input_fallback:
            f.write(f"--input-fallback\n{input_fallback}\n")
        if input_copy:
            f.write("--input-copy\n")
        if forge_skim:
            f.write(f"--skim\n{forge_skim}\n")
        if forge_audit_on:
            f.write("--audit\n")
            shipped = list(conf.JobType.inputFiles) + [conf.JobType.psetName, conf.JobType.scriptExe]
            f.write(f"--forge-git\n{forge_git(shipped)}\n")

        # Pass the output filename to the worker node script
        f.write(f"--output-file={out_name}\n")

    # the transcript keeps what new tasks will run (the file itself is removed at the
    # end; a resubmitted task keeps the sandbox of its first submission)
    if not (args.status or args.report or args.kill or args.resubmit):
        with open(args_file) as f:
            logger.info("Job arguments of tasks submitted now (crab_args.txt): "
                        + " ".join(l.strip() for l in f if l.strip()))
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
    if site_blacklist:
        conf.Site.blacklist = list(site_blacklist)
        logger.info(f"Site blacklist: {', '.join(site_blacklist)}")

    # Accumulators for --report (printed once, after the loop, so columns align)
    report_rows = []
    report_unknown = set()

    # One action per run, first match in this order (the loop has always
    # dispatched like this; --kill now comes BEFORE the default submit branch,
    # see the KILL block).
    action = ("status" if args.status else "report" if args.report else
              "resubmit" if args.resubmit else "kill" if args.kill else "submit")
    out = Outcomes(action, len(datasets))
    items = list(datasets.items())

    # 3. Process Jobs
    for idx, (short_name, dataset) in enumerate(items):
        req_name = short_name.replace("-", "_")

        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        conf.Data.outputDatasetTag = short_name

        project_dir = os.path.join(conf.General.workArea, "crab_" + req_name)

        # flush: under runlog.sh stdout is a pipe (block-buffered) while logging
        # and CRAB write to stderr; without it this line lands after CRAB's
        # output for the same dataset (seen in the 2026-09-23 pilot transcript).
        print(f"[{short_name}] Processing...", flush=True)
        failure = None          # exception of a failed CRAB call, if any

        # -- STATUS Action --
        if args.status:
            if os.path.isdir(project_dir):
                try:
                    rc = subprocess.run(["crab", "status", "-d", project_dir]).returncode
                    detail = "crab status exit %d" % rc
                except OSError as e:
                    rc, detail = -1, "cannot run crab: %s" % e
                out.add("OK" if rc == 0 else "FAILED", short_name, "status", "" if rc == 0 else detail)
            else:
                logger.warning("Project not found.")
                out.add("WARN", short_name, "status", "no project dir (never submitted?)")
            continue

        # -- REPORT Action (compact per-sample job-state summary) --
        if args.report:
            if not os.path.isdir(project_dir):
                logger.warning("Project not found.")
                out.add("WARN", short_name, "report", "no project dir (never submitted?)")
            elif not has_task_cache(project_dir):
                logger.error("Stale project dir (no .requestcache, never reached the server): %s", project_dir)
                out.add("FAILED", short_name, "stale", project_dir)
                out.stale_dirs.append(project_dir)
            else:
                try:
                    # Silence CRAB's verbose status dump; we only want the dict.
                    with contextlib.redirect_stdout(io.StringIO()):
                        res = crabCommand('status', dir=project_dir)
                    if (res or {}).get('commandStatus') == 'FAILED':
                        raise RuntimeError("crab status returned commandStatus FAILED")
                    row, unknown = summarize_status((res or {}).get('jobsPerStatus', {}))
                    report_rows.append((short_name, row))
                    report_unknown |= unknown
                    out.add("OK", short_name, "report")
                except Exception as e:
                    logger.error(f"Status query failed for {short_name}: {e}")
                    report_rows.append((short_name, summarize_status({})[0]))
                    out.add("FAILED", short_name, "report", e)
                    failure = e
            if failure is None or not is_proxy_problem(failure):
                continue

        # -- RESUBMIT Action (explicit; failed jobs only, default resources) --
        elif args.resubmit:
            if not os.path.isdir(project_dir):
                logger.warning("Project not found (nothing to resubmit).")
                out.add("WARN", short_name, "resubmit", "no project dir (never submitted?)")
            elif not has_task_cache(project_dir):
                logger.error("Stale project dir (no .requestcache, never reached the server): %s", project_dir)
                out.add("FAILED", short_name, "stale", project_dir)
                out.stale_dirs.append(project_dir)
            else:
                logger.info("Resubmitting (explicit)...")
                failure = resubmit_task(out, short_name, project_dir)
            if failure is None or not is_proxy_problem(failure):
                continue

        # -- KILL Action (explicit). Checked BEFORE the default branch: until
        # 2026-09-23 it sat after it, so `--kill` first resubmitted every
        # existing task and SUBMITTED every dataset without a project dir, then
        # killed them.
        elif args.kill:
            if not os.path.isdir(project_dir):
                logger.warning(f"Project directory not found (nothing to kill): {project_dir}")
                out.add("WARN", short_name, "kill", "no project dir (nothing to kill)")
            elif not has_task_cache(project_dir):
                logger.warning("Stale project dir (no .requestcache): nothing on the server to kill: %s", project_dir)
                out.add("WARN", short_name, "kill", "stale dir, nothing on the server")
                out.stale_dirs.append(project_dir)
            else:
                logger.info("Action: KILLING Task")
                try:
                    res = crabCommand('kill', dir=project_dir)
                    if (res or {}).get('commandStatus') == 'FAILED':
                        logger.error("Kill Failed: the server did not accept the kill")
                        out.add("FAILED", short_name, "kill", "server did not accept the kill")
                    else:
                        logger.info("Kill command sent successfully.")
                        out.add("OK", short_name, "kill", "kill request sent")
                except HTTPException as hte:
                    logger.error(f"Kill Failed: {getattr(hte, 'headers', hte)}")
                    out.add("FAILED", short_name, "kill", getattr(hte, 'headers', hte))
                except Exception as e:
                    logger.error(f"Kill Failed: {e}")
                    out.add("FAILED", short_name, "kill", e)
                    failure = e
            print("-" * 60, flush=True)
            if failure is None or not is_proxy_problem(failure):
                continue

        # -- SUBMIT / RESUBMIT Logic (default action) --
        elif os.path.isdir(project_dir):
            if not has_task_cache(project_dir):
                # Left by an earlier submit that died before the server accepted
                # the task (see has_task_cache). Resubmitting it cannot work.
                logger.error("Stale project dir (no .requestcache, never reached the server): %s", project_dir)
                logger.error("Not resubmitting. Remove it and run this command again.")
                out.add("FAILED", short_name, "stale", project_dir)
                out.stale_dirs.append(project_dir)
                continue
            logger.info("Resubmitting...")
            failure = resubmit_task(out, short_name, project_dir)
        else:
            logger.info("Submitting...")
            try:
                res = crabCommand('submit', config=conf)
            except Exception as e:
                logger.error(f"Submit Failed: {e}")
                out.add("FAILED", short_name, "submit", e)
                failure = e
            else:
                status = (res or {}).get('commandStatus')
                if status == 'SUCCESS' and has_task_cache(project_dir):
                    out.add("OK", short_name, "submit", "task %s" % (res or {}).get('uniquerequestname', '?'))
                else:
                    out.add("FAILED", short_name, "submit", "CRAB returned commandStatus=%r, .requestcache %s"
                            % (status, "present" if has_task_cache(project_dir) else "missing"))
            if os.path.isdir(project_dir) and not has_task_cache(project_dir):
                out.stale_dirs.append(project_dir)

        # A proxy / myproxy failure would repeat for every remaining dataset
        # (and, for myproxy, ask for the GRID pass phrase each time): stop here.
        if failure is not None and is_proxy_problem(failure):
            rest = [k for k, _ in items[idx + 1:]]
            for k in rest:
                out.add("SKIPPED", k, action, "not attempted after a proxy failure")
            logger.error("Proxy/myproxy failure: stopping; %d remaining dataset(s) not attempted. "
                         "Fix the proxy (run `crab createmyproxy --days 30` ALONE and type the pass "
                         "phrase), then run the same command again.", len(rest))
            break

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
        logger.info("      See docs/05_troubleshooting.md A10 (CRAB resubmit) for exit codes and details.")

    # Cleanup temp file
    if os.path.exists(args_file):
        os.remove(args_file)

    # -- Post-loop: what happened to each dataset, and the exit code ----------
    out.print_summary()
    return out.exit_code()

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
    parser.add_argument("--kill", action="store_true",
                        help="Kill every existing task of the config (never submits; "
                             "datasets without a project dir are skipped with a WARN)")
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
    sys.exit(main(args))
