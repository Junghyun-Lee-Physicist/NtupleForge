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
        self.failures = []

    def env(self, mode="ok"):
        env = dict(os.environ)
        env["PYTHONPATH"] = self.mock + os.pathsep + env.get("PYTHONPATH", "")
        env["PATH"] = self.bindir + os.pathsep + env.get("PATH", "")
        env["MOCK_MODE"] = mode
        env["MOCK_CALLS"] = self.calls
        return env

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
        if os.path.exists(self.calls):
            os.remove(self.calls)
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

        n = len(r.failures)
        print("-" * 60)
        print("RESULT: %s" % ("ALL PASS" if n == 0 else "%d FAILED: %s" % (n, ", ".join(r.failures))))
        return 0 if n == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
