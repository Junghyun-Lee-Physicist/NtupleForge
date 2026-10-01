#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_forge_campaign_audit_root.py -- script/forge_campaign_audit.py on a fake
storage tree in the CRAB layout, with outputs made by the real run_postproc.py
(real ROOT and NanoAODTools: lxplus or KNU after cmsenv; no grid, no CRAB).

Builds, in a temp dir, NanoAOD-like inputs (the maker of test_forge_audit_root.py),
then two campaigns of the same datasets: a reference made without a skim (the
09-24 no-skim pilot) and one with --skim 6j20 --audit (the 09-29 skim pilot),
each output at <base>/<output_base>/<primary>/<key>/<YYMMDD_hhmmss>/0000/forgedNtuple_<job>.root,
plus a failed/ copy, log tarballs and a DAS table. Checks the verdicts on the good
tree and on broken copies of it: a missing job, an input processed twice, an
output made with another skim, an output without the audit, a wrong DAS count, a
ROOT error line in a log, a log without the job output, a ForgeTTbbKeys row
missing, an input whose Runs genEventSumw disagrees (D6 per file), and
damage that must give a FAIL line, not a traceback: an output that is not a ROOT
file, a corrupt log tarball, a reference campaign copied twice.

    python3 script/test_forge_campaign_audit_root.py      # last line: RESULT: ALL PASS (N checks)
    python3 script/test_forge_campaign_audit_root.py -v   # also print every output of the audit tool
"""
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "script")
sys.path.insert(0, SCRIPT)
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "   -> %s" % (str(detail)[-1500:],)))


def write(path, text):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(path, "w") as f:
        f.write(text)


def add_log(path, text):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        os.makedirs(d)
    with tarfile.open(path, "w:gz") as tf:
        data = text.encode("utf-8")
        ti = tarfile.TarInfo("cmsRun-stdout.log")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))


TOTAL_LINE = "Total time 1.0 sec. to process 800 events. Rate = 800.0 Hz.\n"


def rewrite_tree(ROOT, path, name, branches, rows):
    """Replace the TTree `name` of a file by one with `branches` [(name, array code, leaf)] and `rows`."""
    from array import array
    f = ROOT.TFile.Open(path, "UPDATE")
    f.Delete("%s;*" % name)
    t = ROOT.TTree(name, name)
    t.SetAutoSave(0)
    buf = {}
    for b, code, leaf in branches:
        buf[b] = array(code, [0])
        t.Branch(b, buf[b], "%s/%s" % (b, leaf))
    for r in rows:
        for (b, _, _), v in zip(branches, r):
            buf[b][0] = v
        t.Fill()
    t.Write()
    f.Close()


def read_rows(ROOT, path, name, cols):
    f = ROOT.TFile.Open(path)
    t = f.Get(name)
    rows = []
    for i in range(int(t.GetEntries())):
        t.GetEntry(i)
        rows.append(tuple(getattr(t, c) for c in cols))
    f.Close()
    return rows


def main():
    try:
        import ROOT
    except ImportError:
        print("FATAL: PyROOT not importable; run after cmsenv")
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
    import test_forge_audit_root as tfa
    tmp = tempfile.mkdtemp(prefix="test_forge_campaign_audit_")
    try:
        inp = os.path.join(tmp, "inputs")
        os.makedirs(inp)
        base = os.path.join(tmp, "store_user")
        br_mc = os.path.join(tmp, "br_mc.txt")
        write(br_mc, "drop *\nkeep run\nkeep luminosityBlock\nkeep event\nkeep nJet\nkeep Jet_*\nkeep genWeight\n"
                     "keep genTtbarId\n")
        br_data = os.path.join(tmp, "br_data.txt")
        write(br_data, "drop *\nkeep run\nkeep luminosityBlock\nkeep event\nkeep nJet\nkeep Jet_*\n")
        mc_ds, data_ds = "/ZZprim/Fake-mc-v1/NANOAODSIM", "/JetFake/Run2024X-v1/NANOAOD"
        # three MC inputs and two Data inputs, distinct runs so that every (run, lumi, event) is unique
        ins = {"ZZ": [], "JetFake_Run2024X-v1": [], "ZZw": []}
        n_ev = {"ZZ": 0, "JetFake_Run2024X-v1": 0, "ZZw": 0}
        for j in range(3):
            p = os.path.join(inp, "mc_%d.root" % (j + 1))
            n_ev["ZZ"] += tfa.make(ROOT, p, 700 + 100 * j, True, seed=10 + j, run=1 + j, edges=(j == 0))
            ins["ZZ"].append(p)
        for j in range(2):
            p = os.path.join(inp, "data_%d.root" % (j + 1))
            n_ev["JetFake_Run2024X-v1"] += tfa.make(ROOT, p, 900, False, seed=20 + j, run=381001 + j, edges=False)
            ins["JetFake_Run2024X-v1"].append(p)
        # one MC input whose Runs genEventSumw is off by 5e-6: above D6's 1e-6, below the job audit's C3 FAIL
        # limit 1e-5 (audit v2, D-2026-09-30-p7: a genEventCount mismatch now fails the job, C2r)
        p = os.path.join(inp, "mcw_1.root")
        n_ev["ZZw"] = tfa.make(ROOT, p, 500, True, seed=40, run=9, edges=False)
        ins["ZZw"].append(p)
        runs = read_rows(ROOT, p, "Runs", ("run", "genEventCount", "genEventSumw", "genEventSumw2"))
        rewrite_tree(ROOT, p, "Runs", [("run", "I", "i"), ("genEventCount", "q", "L"), ("genEventSumw", "d", "D"),
                                       ("genEventSumw2", "d", "D")],
                     [(int(r[0]), int(r[1]), float(r[2]) * (1 + 5e-6), float(r[3])) for r in runs])
        wz_ds = "/ZZwprim/Fake-mc-v1/NANOAODSIM"
        prim = {"ZZ": "ZZprim", "JetFake_Run2024X-v1": "JetFake", "ZZw": "ZZwprim"}
        brs = {"ZZ": br_mc, "JetFake_Run2024X-v1": br_data, "ZZw": br_mc}
        logs_text = {}

        def produce(key, job, extra, out_path):
            os.makedirs(os.path.join(tmp, "work"), exist_ok=True)
            work = tempfile.mkdtemp(dir=os.path.join(tmp, "work"))
            cmd = [sys.executable, os.path.join(SCRIPT, "run_postproc.py"), ins[key][job - 1], "-I", "modules.noop:MODULES",
                   "-b", brs[key], "-o", "forgedNtuple.root"] + extra
            p = subprocess.run(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            if p.returncode != 0:
                raise RuntimeError("run_postproc failed (%d): %s" % (p.returncode, p.stdout[-1500:]))
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            shutil.move(os.path.join(work, "forgedNtuple.root"), out_path)
            logs_text[out_path] = p.stdout

        def task(ob, key, ts):
            return os.path.join(base, ob, prim[key], key, ts, "0000")

        # reference campaign (no skim) and skim campaign
        for key, (ref_ob, skim_ob) in (("ZZ", ("ref_MC", "skim_MC")), ("JetFake_Run2024X-v1", ("ref_Data", "skim_Data"))):
            for job in range(1, len(ins[key]) + 1):
                o = os.path.join(task(ref_ob, key, "260924_000000"), "forgedNtuple_%d.root" % job)
                produce(key, job, [], o)
                add_log(os.path.join(os.path.dirname(o), "log", "cmsRun_%d.log.tar.gz" % job), logs_text[o])
                o = os.path.join(task(skim_ob, key, "260929_000000"), "forgedNtuple_%d.root" % job)
                produce(key, job, ["--skim", "6j20", "--audit", "--forge-git", "abc123def456"], o)
                add_log(os.path.join(os.path.dirname(o), "log", "cmsRun_%d.log.tar.gz" % job), logs_text[o])
        o = os.path.join(task("skim_MCw", "ZZw", "260929_000000"), "forgedNtuple_1.root")
        produce("ZZw", 1, ["--skim", "6j20", "--audit", "--forge-git", "abc123def456"], o)
        # a failed job's copy (CRAB stages the output of a failed job under failed/)
        zz_skim = task("skim_MC", "ZZ", "260929_000000")
        os.makedirs(os.path.join(zz_skim, "failed"))
        shutil.copy(os.path.join(zz_skim, "forgedNtuple_2.root"), os.path.join(zz_skim, "failed", "forgedNtuple_2.root"))
        # a benign SetBranchStatus line in one reference log, a read error in another
        zz_ref = task("ref_MC", "ZZ", "260924_000000")
        add_log(os.path.join(zz_ref, "log", "cmsRun_1.log.tar.gz"),
                "Error in <TTree::SetBranchStatus>: No branch name is matching wildcard -> LHE_*\nall good\n" + TOTAL_LINE)
        das = os.path.join(tmp, "das.tsv")
        write(das, "type\tkey\tnevents\tnfiles\tsize_TB\tdataset\nMC\tZZ\t%d\t3\t0\t%s\nData\tJetFake_Run2024X-v1\t%d\t2\t0\t%s\n"
              % (n_ev["ZZ"], mc_ds, n_ev["JetFake_Run2024X-v1"], data_ds))
        das_w = os.path.join(tmp, "das_w.tsv")
        write(das_w, "type\tkey\tnevents\tnfiles\tsize_TB\tdataset\nMC\tZZw\t%d\t1\t0\t%s\n" % (n_ev["ZZw"], wz_ds))
        das_bad = os.path.join(tmp, "das_bad.tsv")
        write(das_bad, "type\tkey\tnevents\tnfiles\tsize_TB\tdataset\nMC\tZZ\t%d\t3\t0\t%s\n" % (n_ev["ZZ"] + 1, mc_ds))
        cfgs = {}
        skim_keys = '  skim: "6j20"\n  audit: true\n'
        for name, ob, key, ds, extra in (("skimMC", "skim_MC", "ZZ", mc_ds, skim_keys),
                                         ("refMC", "ref_MC", "ZZ", mc_ds, ""),
                                         ("skimData", "skim_Data", "JetFake_Run2024X-v1", data_ds, skim_keys),
                                         ("refData", "ref_Data", "JetFake_Run2024X-v1", data_ds, ""),
                                         ("skimMCw", "skim_MCw", "ZZw", wz_ds, skim_keys)):
            cfgs[name] = os.path.join(tmp, "config_%s.yaml" % name)
            write(cfgs[name], 'common:\n  output_base: "%s"\n%sdatasets:\n  %s: "%s"\n' % (ob, extra, key, ds))

        def run(*a):
            p = subprocess.run([sys.executable, os.path.join(SCRIPT, "forge_campaign_audit.py"), "--base", base]
                               + list(a), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            if "-v" in sys.argv[1:]:
                print(p.stdout)
            return p.returncode, p.stdout

        def level(out, name):
            return [l.split()[1] for l in out.splitlines() if l.strip().startswith(name + " ")]

        # 1. the good skim campaign against the reference
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--reference-config", cfgs["refMC"], "--threads", "0")
        check("skim MC vs reference: exit 0; D1-D6, K (with the reference) and X7 PASS; D7 WARN for the failed/ copy",
              rc == 0 and all(level(out, d) == ["PASS"] for d in ("D1", "D2", "D3", "D4", "D5", "D6", "K", "X7"))
              and level(out, "D7") == ["WARN"] and "RESULT: ALL PASS" in out and "reference: " in out
              and "pass=1: " in out, out)
        check("skim MC: the failed/ copy is not counted (outputs=3/3)", "outputs=3/3" in out, out)
        rc, out = run("-c", cfgs["skimData"], "--das", das, "--reference-config", cfgs["refData"], "--threads", "2")
        check("skim Data vs reference (2 threads): exit 0, X7 PASS, no D6 and no K (Data)",
              rc == 0 and level(out, "X7") == ["PASS"] and not level(out, "D6") and not level(out, "K"), out)
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--scan-logs")
        check("skim MC with the log scan: L1 PASS, T1 INFO with the NanoAODTools and FORGE|JOB times of 3 jobs",
              rc == 0 and level(out, "L1") == ["PASS"] and level(out, "T1") == ["INFO"]
              and "Total time of 3 jobs" in out and "FORGE|JOB t_s of 3 jobs" in out, out)
        # job 1 copied its input through the fallback (xrdcp), job 2 read it through the fallback directly
        lg1, lg2 = [os.path.join(zz_skim, "log", "cmsRun_%d.log.tar.gz" % j) for j in (1, 2)]
        for lg in (lg1, lg2):
            shutil.copy(lg, lg + ".keep")
        url = "root://cms-xrd-global.cern.ch//store/mc/x/%d.root"
        add_log(lg1, ("FORGE|INPUT|/store/mc/x/1.root|fallback|" + url + "|OSError: Failed to open file /cms/store/mc/x/"
                      "1.root|copy (2040 MB in 131 s) /srv/forge_aaa/store/mc/x/1.root\n") % 1 + TOTAL_LINE
                + "FORGE|JOB|files=1|n_in=700|n_pass=50|n_out=50|t_s=12.0|exit=0\n")
        add_log(lg2, ("FORGE|INPUT|/store/mc/x/2.root|fallback|" + url + "|OSError: Failed to open file /cms/store/mc/x/"
                      "2.root|stream (xrdcp exit 54: Run: [ERROR] Server responded with an error: [3011] No servers are "
                      "available to read the file.)\n") % 2 + TOTAL_LINE
                + "FORGE|JOB|files=1|n_in=700|n_pass=50|n_out=50|t_s=12.0|exit=0\n")
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--scan-logs")
        check("jobs that read their input through the fallback: T1 counts them (jobs 1, 2), L1 still PASS",
              rc == 0 and level(out, "T1") == ["INFO"] and "through the fallback (AAA) in 2 job(s) (1, 2)" in out
              and level(out, "L1") == ["PASS"], out)
        check("... T1 gives the xrdcp time of job 1 and names job 2 as read without a copy",
              "xrdcp time (not in the times above) median 131 s, largest 131 s (job 1)" in out
              and "read directly without a copy (slow) in 1 (2)" in out, out)
        # --input-copy (P7.1, docs/05 A27): job 1 copied its input from the site, job 2's site copy failed and it
        # read the input at the site directly
        pfn = "root://cmsxrootd-site.fnal.gov//store/mc/x/%d.root"
        add_log(lg1, ("FORGE|INPUT|/store/mc/x/1.root|copy|" + pfn + "|copy (2600 MB in 21 s) "
                      "/srv/forge_in/store/mc/x/1.root\n") % 1 + TOTAL_LINE
                + "FORGE|JOB|files=1|n_in=700|n_pass=50|n_out=50|t_s=12.0|exit=0\n")
        add_log(lg2, ("FORGE|INPUT|/store/mc/x/2.root|local|" + pfn + "|stream (xrdcp exit 54: Run: [ERROR] "
                      "Server responded with an error: [3011] No servers are available to read the file.)\n") % 2
                + TOTAL_LINE + "FORGE|JOB|files=1|n_in=700|n_pass=50|n_out=50|t_s=12.0|exit=0\n")
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--scan-logs")
        check("--input-copy: T1 counts the site copy of job 1 with its xrdcp time, names job 2 (site copy failed), "
              "no fallback, L1 PASS",
              rc == 0 and level(out, "T1") == ["INFO"] and "input copied from the site first (--input-copy) in 1 job(s), "
              "xrdcp time (not in the times above) median 21 s, largest 21 s (job 1)" in out
              and "the copy from the site failed and the input was read at the site directly in 1 job(s) (2)" in out
              and "through the fallback" not in out and level(out, "L1") == ["PASS"], out)
        for lg in (lg1, lg2):
            shutil.move(lg + ".keep", lg)
        rc, out = run("-c", cfgs["skimMCw"], "--das", das_w)
        check("Runs genEventSumw off by 5e-6 in one file: D6 WARN naming the file and the relative difference, exit 0",
              rc == 0 and level(out, "D6") == ["WARN"] and "genEventCount != n_in in 0" in out
              and "largest relative difference 5e-06 (" in out and level(out, "K") == ["PASS"], out)
        # 2. the reference campaign itself (no skim, no audit) with the log scan
        rc, out = run("-c", cfgs["refMC"], "--das", das, "--scan-logs")
        check("reference MC, no audit: D4 from the Events sum PASS, L1 PASS (a SetBranchStatus line is not an error)",
              rc == 0 and level(out, "D4") == ["PASS"] and level(out, "L1") == ["PASS"], out)
        add_log(os.path.join(zz_ref, "log", "cmsRun_2.log.tar.gz"),
                "Error in <TBranch::GetBasket>: File: root://x//store/y.root at byte:1, entry:2759\n" + TOTAL_LINE)
        rc, out = run("-c", cfgs["refMC"], "--das", das, "--scan-logs")
        check("a ROOT read error line in the log of job 2: L1 FAIL naming job 2, exit 1",
              rc == 1 and level(out, "L1") == ["FAIL"] and "ROOT error lines 1 (2)" in out
              and "end line 0" in out, out)
        add_log(os.path.join(zz_ref, "log", "cmsRun_2.log.tar.gz"), "all good\n" + TOTAL_LINE)
        add_log(os.path.join(zz_ref, "log", "cmsRun_3.log.tar.gz"), "the wrapper only, no job output\n")
        rc, out = run("-c", cfgs["refMC"], "--das", das, "--scan-logs")
        check("a log without the NanoAODTools end line (job 3): L1 FAIL naming job 3, exit 1",
              rc == 1 and level(out, "L1") == ["FAIL"] and "end line 1 (3)" in out and "ROOT error lines 0" in out, out)
        # 3. broken copies of the skim campaign
        f3 = os.path.join(zz_skim, "forgedNtuple_3.root")
        shutil.move(f3, f3 + ".away")
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--reference-config", cfgs["refMC"], "--threads", "0")
        check("job 3 missing: D1, D3, D4 and X7 FAIL, exit 1",
              rc == 1 and all(level(out, d) == ["FAIL"] for d in ("D1", "D3", "D4", "X7")) and "missing jobs 3" in out, out)
        shutil.move(f3 + ".away", f3)
        dup = os.path.join(zz_skim, "forgedNtuple_4.root")
        shutil.copy(os.path.join(zz_skim, "forgedNtuple_1.root"), dup)
        rc, out = run("-c", cfgs["skimMC"], "--das", das)
        check("input 1 processed twice (job 4 = copy of job 1): D1 (extra job) and D3 (input in two rows) FAIL",
              rc == 1 and level(out, "D1") == ["FAIL"] and level(out, "D3") == ["FAIL"] and "inputs in two rows" in out, out)
        os.remove(dup)
        f2 = os.path.join(zz_skim, "forgedNtuple_2.root")
        shutil.move(f2, f2 + ".keep")
        produce("ZZ", 2, ["--skim", "6j25", "--audit", "--forge-git", "abc123def456"], f2)
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--reference-config", cfgs["refMC"], "--threads", "0")
        check("job 2 made with another skim (6j25): D5 and X7 FAIL",
              rc == 1 and level(out, "D5") == ["FAIL"] and level(out, "X7") == ["FAIL"] and "only in the reference" in out,
              out)
        os.remove(f2)
        shutil.copy(os.path.join(zz_ref, "forgedNtuple_2.root"), f2)
        rc, out = run("-c", cfgs["skimMC"], "--das", das)
        check("job 2 without the audit trees: D2 FAIL", rc == 1 and level(out, "D2") == ["FAIL"], out)
        os.remove(f2)
        shutil.move(f2 + ".keep", f2)
        f1 = os.path.join(zz_skim, "forgedNtuple_1.root")
        shutil.copy(f1, f1 + ".keep")
        kcols = ("run", "luminosityBlock", "event", "genTtbarId", "genWeight", "pass")
        krows = read_rows(ROOT, f1, "ForgeTTbbKeys", kcols)
        rewrite_tree(ROOT, f1, "ForgeTTbbKeys", [("run", "I", "i"), ("luminosityBlock", "I", "i"), ("event", "Q", "l"),
                                                 ("genTtbarId", "i", "I"), ("genWeight", "f", "F"), ("pass", "B", "O")],
                     [(int(r[0]), int(r[1]), int(r[2]), int(r[3]), float(r[4]), 1 if r[5] else 0) for r in krows[1:]])
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--reference-config", cfgs["refMC"], "--threads", "2")
        check("job 1 lost one ForgeTTbbKeys row (2 threads): K FAIL (row count, and 1 only in the reference), X7 still PASS",
              rc == 1 and level(out, "K") == ["FAIL"] and "row count != its ForgeAudit count" in out
              and "only in the reference 1" in out and level(out, "X7") == ["PASS"] and len(krows) > 1, out)
        shutil.move(f1 + ".keep", f1)
        # damage: FAIL lines and a RESULT line, never a traceback
        shutil.move(f3, f3 + ".away")
        write(f3, "not a ROOT file " * 20)
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--reference-config", cfgs["refMC"], "--threads", "0")
        check("job 3 is not a ROOT file: D0 FAIL, X7 FAIL (not compared), a RESULT line, no traceback",
              rc == 1 and level(out, "D0") == ["FAIL"] and level(out, "X7") == ["FAIL"] and "not compared" in out
              and "RESULT: 1 of 1 dataset(s) FAIL" in out and "Traceback" not in out, out)
        os.remove(f3)
        shutil.move(f3 + ".away", f3)
        lg = os.path.join(zz_skim, "log", "cmsRun_2.log.tar.gz")
        shutil.copy(lg, lg + ".keep")
        raw = bytearray(open(lg, "rb").read())
        mid = len(raw) // 2
        raw[mid:mid + 16] = b"\xff" * 16
        open(lg, "wb").write(bytes(raw))
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--scan-logs")
        check("a corrupt log tarball (job 2): L1 FAIL, a RESULT line, no traceback",
              rc == 1 and level(out, "L1") == ["FAIL"] and "RESULT: 1 of 1 dataset(s) FAIL" in out
              and "Traceback" not in out, out)
        shutil.move(lg + ".keep", lg)
        zz_ref_task = os.path.dirname(zz_ref)
        twice = os.path.join(os.path.dirname(zz_ref_task), "260925_000000")
        shutil.copytree(zz_ref_task, twice)
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--reference-config", cfgs["refMC"], "--threads", "0")
        check("the reference copied into a second task directory: X7 FAIL (EXCESS, keys twice in the reference), K FAIL",
              rc == 1 and level(out, "X7") == ["FAIL"] and "EXCESS" in out and "in the reference 182" in out
              and level(out, "K") == ["FAIL"], out)
        shutil.rmtree(twice)
        rc, out = run("-c", cfgs["skimMC"], "--das", das_bad)
        check("DAS nevents off by one: D4 FAIL with the difference", rc == 1 and level(out, "D4") == ["FAIL"]
              and "difference -1" in out, out)
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--tsv", os.path.join(tmp, "out.tsv"))
        rows = open(os.path.join(tmp, "out.tsv")).read().splitlines() if os.path.exists(os.path.join(tmp, "out.tsv")) else []
        check("restored tree: exit 0 again, TSV with one row", rc == 0 and len(rows) == 2 and rows[1].endswith("WARN"),
              (rc, rows, out[-600:]))
        rc, out = run("-c", cfgs["skimMC"], "--das", das, "--base", os.path.join(tmp, "nowhere"))
        check("a base without the campaign: exit 2", rc == 2, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    n_fail = RESULTS.count(False)
    print("RESULT: %s (%d checks)" % ("ALL PASS" if n_fail == 0 else "%d FAILED" % n_fail, len(RESULTS)))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
