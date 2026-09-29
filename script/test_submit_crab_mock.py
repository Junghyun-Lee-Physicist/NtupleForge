#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_submit_crab_mock.py -- offline test of crab/submit_crab.py against a mock
CRABAPI that reproduces the CRABClient v3.260630 behaviours the wrapper relies
on (read in that tag's source, commit 970fabd):

  * the project dir <workArea>/crab_<requestName> is created BEFORE the VOMS
    and myproxy steps (Commands/SubCommand.py, createWorkArea), so a submit
    that fails on the proxy still leaves the dir behind;
  * <project dir>/.requestcache is written only after the server accepted the
    task (Commands/submit.py, createCache).

No CRAB, no proxy, no network, nothing outside a temporary directory.
Needs python3 + PyYAML (lxplus: inside cmssw-el8 after cmsenv; any machine
with PyYAML works).

    python3 script/test_submit_crab_mock.py        # all cases; exit 0 = all pass
    python3 script/test_submit_crab_mock.py -v     # also print every run's output

WHY (2026-09-23, docs/05_troubleshooting.md A22): the 2024 pilot submit failed
on the myproxy delegation and the wrapper still exited 0; re-running it would
have auto-resubmitted the stale project dir and failed silently again; --kill
submitted every dataset that had no project dir before killing it. Each case
below pins one of those behaviours.
"""
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPER = os.path.join(REPO, "crab", "submit_crab.py")
VERBOSE = "-v" in sys.argv[1:]

MOCK_USERUTILS = '''
class _Sec(object):
    pass
class _Conf(object):
    def __init__(self):
        for s in ("General", "JobType", "Data", "Site", "User"):
            setattr(self, s, _Sec())
def config():
    return _Conf()
def getUsername():
    return "mockuser"
'''

MOCK_EXCEPTIONS = '''
class ClientException(Exception):
    pass
class ProxyCreationException(ClientException):
    pass
class CachefileNotFoundException(ClientException):
    pass
class ConfigException(ClientException):
    pass
'''

MOCK_RAWCOMMAND = '''
import os
from CRABClient.ClientExceptions import (ProxyCreationException,
                                         CachefileNotFoundException, ConfigException)
CALLS = os.environ["MOCK_CALLS"]

def _log(line):
    with open(CALLS, "a") as f:
        f.write(line + "\\n")

def crabCommand(cmd, **kw):
    mode = os.environ.get("MOCK_MODE", "ok")
    if cmd == "submit":
        conf = kw["config"]
        name = conf.General.requestName
        dump = os.environ.get("MOCK_CONF_DUMP")
        if dump:                                     # what this task's sandbox would carry
            import json
            args = open("crab_args.txt").read() if os.path.exists("crab_args.txt") else None
            with open(dump, "a") as f:
                f.write(json.dumps({"name": name, "inputFiles": list(conf.JobType.inputFiles),
                                    "crab_args": args}) + "\\n")
        p = os.path.join(os.path.abspath(conf.General.workArea), "crab_" + name)
        _log("submit " + name)
        if os.path.exists(p):                       # createWorkArea refuses
            raise ConfigException("Working area '%s' already exists" % p)
        os.makedirs(os.path.join(p, "results"))     # createWorkArea ...
        os.makedirs(os.path.join(p, "inputs"))
        open(os.path.join(p, "crab.log"), "w").close()
        if mode == "proxyfail":                     # ... then the proxy steps
            raise ProxyCreationException("Problems delegating My-proxy.\\n"
                                         "Error trying to create credential:\\n grid-proxy-init failed")
        if mode == "fail_B_x" and name == "B_x":
            raise RuntimeError("Problem sending the request: HTTP 500")
        if mode == "weird":
            return {"commandStatus": "FAILED"}
        open(os.path.join(p, ".requestcache"), "w").close()   # createCache
        return {"requestname": "crab_" + name,
                "uniquerequestname": "260923_120000:mockuser_crab_" + name,
                "commandStatus": "SUCCESS"}
    d = kw.get("dir")
    _log("%s %s" % (cmd, os.path.basename(d)))
    if not os.path.isfile(os.path.join(d, ".requestcache")):    # loadCache
        raise CachefileNotFoundException("Cannot find .requestcache file in CRAB project directory %s" % d)
    if cmd == "resubmit":
        if mode == "resub_fail":
            return {"status": "FAILED", "commandStatus": "FAILED"}
        return None                                 # "nothing to resubmit"
    if cmd == "kill":
        return {"status": "SUCCESS", "commandStatus": "SUCCESS"}
    if cmd == "status":
        return {"commandStatus": "SUCCESS", "jobsPerStatus": {"finished": 3, "running": 1}}
    raise RuntimeError("mock: unknown command " + cmd)
'''

FAKE_VOMS = '#!/bin/sh\ncase "$*" in *-timeleft*) echo 40000;; *) exit 0;; esac\n'
# fake `crab` CLI, used by --status only: fails for crab_C
FAKE_CRAB = '#!/bin/sh\ncase "$*" in *crab_C*) echo "fake crab status: error"; exit 1;; *) echo "fake crab status ok"; exit 0;; esac\n'

CONFIG = '''common:
  jobID: "campaign_test"
  output_base: "test"
  site: "T3_KR_KNU"
  analysis_module: ["modules/noop.py", "MODULES"]
  branch_file: "branches/x.txt"
  splitting: "FileBased"
  units_per_job: 1
datasets:
  A: "/A/Run-v1/NANOAODSIM"
  B-x: "/B/Run-v1/NANOAOD"
  C: "/C/Run-v1/NANOAODSIM"
'''
CONFIG_D = CONFIG + '  D: "/D/Run-v1/NANOAODSIM"\n'
# 2026-09-28: recipe / skim / audit keys (docs/12 section 2.2)
CONFIG_SKIM = CONFIG.replace('jobID: "campaign_test"', 'jobID: "campaign_skim"').replace(
    '  units_per_job: 1\n', '  units_per_job: 1\n  skim: 6j20\n')
CONFIG_SKIM_NOAUDIT = CONFIG_SKIM.replace('  skim: 6j20\n', '  skim: 6j20\n  audit: false\n')
CONFIG_AUDIT_ONLY = CONFIG_SKIM.replace('  skim: 6j20\n', '  audit: true\n')
CONFIG_BADSKIM = CONFIG_SKIM.replace('skim: 6j20', 'skim: 6j21')
CONFIG_RECIPE = CONFIG_SKIM.replace('  skim: 6j20\n', '  recipe: derive\n')


def write(path, text, mode=0o644):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, mode)


def setup(tmp):
    repo = os.path.join(tmp, "repo")
    write(os.path.join(repo, "crab", "submit_crab.py"), open(WRAPPER).read())
    write(os.path.join(repo, "modules", "noop.py"), "MODULES = []\n")
    write(os.path.join(repo, "branches", "x.txt"), "drop *\nkeep run\nkeep luminosityBlock\nkeep event\n")
    write(os.path.join(repo, "script", "run_postproc.py"), "")
    write(os.path.join(repo, "script", "forge_skims.py"), open(os.path.join(REPO, "script", "forge_skims.py")).read())
    write(os.path.join(repo, "script", "forge_audit.py"), "")
    write(os.path.join(repo, "script", "runlogs", "LEDGER.tsv"), "utc_start\tstep\texit\n")
    # the repository's own ignore rules (preflight_*.log, campaign_*, crab_args.txt, __pycache__, ...), so that
    # case 16's git checkout tracks what the real one tracks
    write(os.path.join(repo, ".gitignore"), open(os.path.join(REPO, ".gitignore")).read())
    for name, text in (("skim", CONFIG_SKIM), ("skim_noaudit", CONFIG_SKIM_NOAUDIT), ("audit_only", CONFIG_AUDIT_ONLY),
                       ("badskim", CONFIG_BADSKIM), ("recipe", CONFIG_RECIPE)):
        write(os.path.join(repo, "crabConfig", "c_%s.yaml" % name), text)
    write(os.path.join(repo, "crabConfig", "c.yaml"), CONFIG)
    write(os.path.join(repo, "crabConfig", "cD.yaml"), CONFIG_D)
    mock = os.path.join(tmp, "mock")
    write(os.path.join(mock, "CRABClient", "__init__.py"), "")
    write(os.path.join(mock, "CRABClient", "UserUtilities.py"), MOCK_USERUTILS)
    write(os.path.join(mock, "CRABClient", "ClientExceptions.py"), MOCK_EXCEPTIONS)
    write(os.path.join(mock, "CRABAPI", "__init__.py"), "")
    write(os.path.join(mock, "CRABAPI", "RawCommand.py"), MOCK_RAWCOMMAND)
    bindir = os.path.join(tmp, "bin")
    write(os.path.join(bindir, "voms-proxy-info"), FAKE_VOMS, 0o755)
    write(os.path.join(bindir, "crab"), FAKE_CRAB, 0o755)
    return repo, mock, bindir


class Runner(object):
    def __init__(self, tmp):
        self.repo, self.mock, self.bindir = setup(tmp)
        self.calls = os.path.join(tmp, "calls.txt")
        self.dump = os.path.join(tmp, "conf_dump.txt")
        self.failures = []

    def env(self, mode="ok"):
        env = dict(os.environ)
        env["PYTHONPATH"] = self.mock + os.pathsep + env.get("PYTHONPATH", "")
        env["PATH"] = self.bindir + os.pathsep + env.get("PATH", "")
        env["MOCK_MODE"] = mode
        env["MOCK_CALLS"] = self.calls
        env["MOCK_CONF_DUMP"] = self.dump
        return env

    def dumped(self):
        import json
        if not os.path.exists(self.dump):
            return []
        return [json.loads(l) for l in open(self.dump).read().split("\n") if l.strip()]

    def mock_is_active(self):
        """Fail closed: the wrapper must import the MOCK CRAB modules, never a
        real CRABClient that crab-setup.sh may have put on the path (a real one
        would try to submit the fake datasets)."""
        p = subprocess.run([sys.executable, "-c",
                            "import CRABAPI.RawCommand as a, CRABClient.UserUtilities as b; print(a.__file__); print(b.__file__)"],
                           cwd=self.repo, env=self.env(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        files = [l for l in p.stdout.split("\n") if l.strip()]
        ok = p.returncode == 0 and len(files) == 2 and all(f.startswith(self.mock) for f in files)
        return ok, p.stdout.strip()

    def run(self, mode, *args):
        for p in (self.calls, self.dump):
            if os.path.exists(p):
                os.remove(p)
        p = subprocess.run([sys.executable, "crab/submit_crab.py"] + list(args), cwd=self.repo, env=self.env(mode),
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        calls = open(self.calls).read().split("\n")[:-1] if os.path.exists(self.calls) else []
        if VERBOSE:
            print(p.stdout)
        return p.returncode, calls, p.stdout

    def check(self, name, cond, detail=""):
        print("%-4s %s%s" % ("PASS" if cond else "FAIL", name, ("" if cond else "   <- %s" % (detail,))))
        if not cond:
            self.failures.append(name)

    def rm(self, rel):
        shutil.rmtree(os.path.join(self.repo, rel))

    def mkdir(self, rel, cache=False):
        d = os.path.join(self.repo, rel)
        os.makedirs(d)
        if cache:
            open(os.path.join(d, ".requestcache"), "w").close()


def main():
    if not os.path.isfile(WRAPPER):
        print("FATAL: %s not found" % WRAPPER)
        return 2
    try:
        import yaml  # noqa: F401  (the wrapper needs it; fail here with a clear message)
    except ImportError:
        print("FATAL: PyYAML not importable (lxplus: run inside cmssw-el8 after cmsenv)")
        return 4
    tmp = tempfile.mkdtemp(prefix="test_submit_crab_")
    try:
        r = Runner(tmp)
        ok, where = r.mock_is_active()
        if not ok:
            print("FATAL: the mock CRAB modules are not the ones imported; refusing to run the wrapper.")
            print(where)
            return 3
        c = ["-c", "crabConfig/c.yaml"]

        # 1. the 2026-09-23 pilot: proxy failure on the first dataset
        rc, calls, out = r.run("proxyfail", *c)
        r.check("1 proxy failure: exit 1", rc == 1, "rc=%d" % rc)
        r.check("1 proxy failure: one CRAB call, rest skipped", calls == ["submit A"] and "2 SKIPPED" in out, calls)
        r.check("1 proxy failure: stale-dir hint", "rm -r campaign_test/crab_A" in out)

        # 2. re-run without removing the stale dir
        rc, calls, out = r.run("ok", *c)
        r.check("2 stale dir: exit 1", rc == 1, "rc=%d" % rc)
        r.check("2 stale dir: not touched, others submitted", calls == ["submit B_x", "submit C"], calls)

        # 3. after rm -r: A submitted, B-x/C auto-resubmitted (nothing to resubmit -> WARN)
        r.rm("campaign_test/crab_A")
        rc, calls, out = r.run("ok", *c)
        r.check("3 after rm: exit 0", rc == 0, "rc=%d" % rc)
        r.check("3 after rm: submit A + resubmit B_x, C",
                calls == ["submit A", "resubmit crab_B_x", "resubmit crab_C"], calls)

        # 4. --kill never submits (D has no project dir)
        rc, calls, out = r.run("ok", "-c", "crabConfig/cD.yaml", "--kill")
        r.check("4 kill: exit 0", rc == 0, "rc=%d" % rc)
        r.check("4 kill: 3 kills, no submit/resubmit",
                calls == ["kill crab_A", "kill crab_B_x", "kill crab_C"], calls)

        # 5. --report: missing D is a WARN, exit 0
        rc, calls, out = r.run("ok", "-c", "crabConfig/cD.yaml", "--report")
        r.check("5 report: exit 0, D WARN", rc == 0 and "WARN    D" in out, "rc=%d" % rc)

        # 6. explicit --resubmit refused by the server
        rc, calls, out = r.run("resub_fail", *(c + ["--resubmit"]))
        r.check("6 resubmit refused: exit 1", rc == 1, "rc=%d" % rc)

        # 7. --status: crab CLI fails for crab_C
        rc, calls, out = r.run("ok", *(c + ["--status"]))
        r.check("7 status failure: exit 1", rc == 1 and "FAILED  C" in out, "rc=%d" % rc)

        # 8. non-proxy failure: the loop continues
        r.rm("campaign_test")
        rc, calls, out = r.run("fail_B_x", *c)
        r.check("8 HTTP 500 on B-x: continues, exit 1",
                rc == 1 and calls == ["submit A", "submit B_x", "submit C"], "rc=%d calls=%s" % (rc, calls))

        # 9. submit returning commandStatus FAILED without an exception
        r.rm("campaign_test")
        rc, calls, out = r.run("weird", *c)
        r.check("9 commandStatus FAILED: exit 1", rc == 1 and out.count("FAILED  ") == 3, "rc=%d" % rc)

        # 10. preflight: stale dir -> FAIL, live task -> WARN
        r.rm("campaign_test")
        r.mkdir("campaign_test/crab_A")
        r.mkdir("campaign_test/crab_B_x", cache=True)
        rc, calls, out = r.run("ok", *(c + ["--preflight"]))
        r.check("10 preflight: stale FAIL", "[FAIL] stale CRAB project dirs" in out)
        r.check("10 preflight: live WARN", "[WARN] existing CRAB projects" in out and "auto-RESUBMITS" in out)
        r.check("10 preflight: submitted nothing", calls == [], calls)

        # 11. an older config (no recipe / skim / audit keys): the sandbox is what it was
        r.rm("campaign_test")
        rc, calls, out = r.run("ok", *c)
        d = r.dumped()
        r.check("11 old config: exit 0, no forge files shipped, no --skim / --audit",
                rc == 0 and d and all(not any("forge_" in x for x in e["inputFiles"]) for e in d)
                and all("--skim" not in e["crab_args"] and "--audit" not in e["crab_args"] for e in d),
                (rc, d[:1]))

        # 12. skim: 6j20 -> forge files shipped, crab_args carries --skim / --audit / --forge-git
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_skim.yaml")
        d = r.dumped()
        want = "-b\nx.txt\n-I\nnoop:MODULES\n--skim\n6j20\n--audit\n--forge-git\nunknown\n--output-file=forgedNtuple.root\n"
        r.check("12 skim config: exit 0, 3 submits", rc == 0 and calls == ["submit A", "submit B_x", "submit C"],
                (rc, calls))
        r.check("12 skim config: forge_skims.py and forge_audit.py in every sandbox",
                d and all("script/forge_skims.py" in e["inputFiles"] and "script/forge_audit.py" in e["inputFiles"]
                          for e in d), d[:1])
        r.check("12 skim config: crab_args = -b, -I, --skim 6j20, --audit, --forge-git, --output-file",
                d and all(e["crab_args"] == want for e in d), (d[0]["crab_args"] if d else None, want))
        r.check("12 skim config: the transcript shows the job arguments",
                "Job arguments of tasks submitted now (crab_args.txt): -b x.txt -I noop:MODULES --skim 6j20 --audit "
                "--forge-git unknown --output-file=forgedNtuple.root" in out, out[-1200:])

        # 13. audit only: --audit without --skim
        r.rm("campaign_skim")
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_audit_only.yaml")
        d = r.dumped()
        r.check("13 audit: true without a skim: --audit, no --skim",
                rc == 0 and d and "--audit\n" in d[0]["crab_args"] and "--skim" not in d[0]["crab_args"], d[:1])

        # 14. invalid keys stop before any CRAB call
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_badskim.yaml")
        r.check("14 unknown skim: exit 1, no CRAB call", rc == 1 and calls == [] and "6j21" in out, (rc, calls))
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_recipe.yaml")
        r.check("14 recipe derive: exit 1, no CRAB call", rc == 1 and calls == [] and "not implemented" in out,
                (rc, calls))

        # 15. preflight lines
        r.rm("campaign_skim")
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_skim.yaml", "--preflight")
        r.check("15 preflight skim: recipe line with the formula, forge files, forge git WARN (no git here)",
                "[PASS] recipe" in out and "skim 6j20 = Sum$(Jet_pt>20 && abs(Jet_eta)<2.5)>=6; audit on" in out
                and "[PASS] worker file script/forge_skims.py" in out and "[PASS] worker file script/forge_audit.py" in out
                and "[WARN] forge git (ForgeProvenance)" in out and calls == [], out[-1500:])
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_badskim.yaml", "--preflight")
        r.check("15 preflight unknown skim: FAIL, exit 1", rc == 1 and "[FAIL] recipe / skim / audit" in out, rc)
        rc, calls, out = r.run("ok", "-c", "crabConfig/c_skim_noaudit.yaml", "--preflight")
        r.check("15 preflight skim with audit false: WARN audit", "[WARN] audit" in out and "audit OFF" in out,
                out[-800:])
        rc, calls, out = r.run("ok", *(c + ["--preflight"]))
        r.check("15 preflight old config: recipe line, no forge worker files",
                "[PASS] recipe" in out and "no event skim; audit off" in out and "forge_skims.py" not in out, out[-800:])

        # 16. forge git (ForgeProvenance) in a git checkout: runlog.sh appends to the tracked
        #     script/runlogs/LEDGER.tsv at every step, which must not make the code '+dirty';
        #     a modified branch list must
        if not shutil.which("git"):
            r.check("16 forge git: git in PATH (needed for this case)", False, "git not found")
        else:
            genv = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                        GIT_COMMITTER_EMAIL="t@t")
            for cmd in (["init", "-q"], ["add", "-A"], ["-c", "commit.gpgsign=false", "commit", "-q", "-m", "init"]):
                subprocess.run(["git", "-C", r.repo] + cmd, env=genv, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, check=True)
            with open(os.path.join(r.repo, "script", "runlogs", "LEDGER.tsv"), "a") as f:
                f.write("20260928_120000\tp5_step\t0\n")
            rc, calls, out = r.run("ok", "-c", "crabConfig/c_skim.yaml", "--preflight")
            r.check("16 forge git: only LEDGER.tsv modified -> PASS, no +dirty",
                    "[PASS] forge git (ForgeProvenance)" in out and "+dirty" not in out and "+untracked" not in out,
                    out[-1200:])
            # a file the jobs get but git does not know (a module sibling is shipped automatically)
            extra = os.path.join(r.repo, "modules", "zz_untracked.py")
            with open(extra, "w") as f:
                f.write("X = 1\n")
            rc, calls, out = r.run("ok", "-c", "crabConfig/c_skim.yaml", "--preflight")
            r.check("16 forge git: an untracked shipped module sibling -> WARN +untracked",
                    "[WARN] forge git (ForgeProvenance)" in out and "+untracked" in out and "+dirty" not in out,
                    out[-1200:])
            os.remove(extra)
            # a rename out of the ignored directory still counts (both sides of 'old -> new')
            subprocess.run(["git", "-C", r.repo, "mv", "script/runlogs/LEDGER.tsv", "branches/ledger_moved.txt"],
                           env=genv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
            p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'crab'); import submit_crab; "
                                "print(submit_crab.forge_git())"], cwd=r.repo, env=r.env(), stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, universal_newlines=True)
            r.check("16 forge git: a staged rename script/runlogs/ -> branches/ -> +dirty",
                    p.stdout.strip().endswith("+dirty"), p.stdout[-300:])
            subprocess.run(["git", "-C", r.repo, "mv", "branches/ledger_moved.txt", "script/runlogs/LEDGER.tsv"],
                           env=genv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
            with open(os.path.join(r.repo, "branches", "x.txt"), "a") as f:
                f.write("keep nJet\n")
            rc, calls, out = r.run("ok", "-c", "crabConfig/c_skim.yaml", "--preflight")
            r.check("16 forge git: branch list modified -> WARN +dirty",
                    "[WARN] forge git (ForgeProvenance)" in out and "+dirty" in out, out[-1200:])

        n = len(r.failures)
        print("-" * 60)
        print("RESULT: %s" % ("ALL PASS" if n == 0 else "%d FAILED: %s" % (n, ", ".join(r.failures))))
        return 0 if n == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
