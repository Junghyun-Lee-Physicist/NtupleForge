#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_forge_output.py -- read back one output of `run_postproc.py --skim NAME
--audit` with real ROOT and compare it EVENT BY EVENT with the input (plan 12
P5, cross-check X7; docs/12_fastpath_workflow_plan.md sections 2.3 and 4).

    python3 script/check_forge_output.py OUT.root INPUT.root [--first-entry K] [-N N]

The job's closure C1 compares counts only. This tool compares the sets:
  X7  the (run, luminosityBlock, event) keys in the output Events tree ==
      the keys of the input events in the same entry range that pass the RVec
      expression of the skim named in ForgeProvenance (forge_skims.py)
  K   ForgeTTbbKeys: every key with pass = 1 is in the output, none with
      pass = 0 is; the keys == the input events with genTtbarId % 100 in 53..55
  A   ForgeAudit row of this input: n_in, n_pass, sum of genWeight recomputed
It also prints ForgeProvenance and a short ForgeAudit summary.
Exit 0 all PASS, 1 a FAIL, 2 bad arguments / a file or object missing.
Read-only. Needs PyROOT and numpy (cmssw-el8 + cmsenv). ASCII only.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def keyset(arrs):
    return set(zip((int(x) for x in arrs["run"]), (int(x) for x in arrs["luminosityBlock"]),
                   (int(x) for x in arrs["event"])))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output")
    ap.add_argument("input", help="the input file the job read (local path or root:// URL)")
    ap.add_argument("--first-entry", type=int, default=0)
    ap.add_argument("-N", "--max-events", type=int, default=0)
    args = ap.parse_args()
    try:
        import ROOT
    except ImportError:
        print("FATAL: PyROOT not importable; run inside cmssw-el8 after cmsenv", file=sys.stderr)
        return 2
    ROOT.gROOT.SetBatch(True)
    import forge_skims
    import forge_audit
    forge_audit.declare(ROOT)
    fails = []

    def report(name, ok, detail):
        print("%-4s %-4s %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            fails.append(name)

    fo = ROOT.TFile.Open(args.output)
    if not fo or fo.IsZombie():
        print("FATAL: cannot open %s" % args.output, file=sys.stderr)
        return 2
    prov_obj = fo.Get("ForgeProvenance")
    audit = fo.Get("ForgeAudit")
    if not prov_obj or not audit:
        print("FATAL: %s has no ForgeProvenance / ForgeAudit (was it written with --audit?)" % args.output,
              file=sys.stderr)
        return 2
    if int(prov_obj.GetEntries()) < 1:
        print("FATAL: ForgeProvenance has no row", file=sys.stderr)
        return 2
    prov_obj.GetEntry(0)
    prov = json.loads(str(prov_obj.json))
    if int(prov_obj.GetEntries()) > 1:
        print("note: ForgeProvenance has %d rows (a merged file); using the first" % int(prov_obj.GetEntries()))
    print("ForgeProvenance: " + json.dumps(prov, sort_keys=True))
    skim = prov.get("skim")
    formula, rvec = forge_skims.get(skim)
    if (formula or "") != prov.get("formula", "") or (rvec or "") != prov.get("rvec", ""):
        report("P", False, "forge_skims.py here differs from the job's table (skim %s)" % skim)

    # the output keys
    out_keys = keyset(ROOT.RDataFrame("Events", args.output).AsNumpy(["run", "luminosityBlock", "event"]))

    # the input, same range, RVec selection
    df = ROOT.RDataFrame("Events", args.input)
    if args.first_entry or args.max_events:
        df = df.Range(args.first_entry, args.first_entry + args.max_events if args.max_events else 0)
    df = df.Define("forge_pass", "(bool)(%s)" % rvec if rvec else "true")
    cols = ["run", "luminosityBlock", "event", "forge_pass"]
    fi = ROOT.TFile.Open(args.input)
    names = set(str(b.GetName()) for b in fi.Get("Events").GetListOfBranches())
    is_mc = "genWeight" in names
    has_gtid = "genTtbarId" in names
    if is_mc:
        cols.append("genWeight")
    if has_gtid:
        cols.append("genTtbarId")
    arr = df.AsNumpy(cols)
    n_in = len(arr["run"])
    pas = arr["forge_pass"]
    in_pass = set((int(arr["run"][i]), int(arr["luminosityBlock"][i]), int(arr["event"][i]))
                  for i in range(n_in) if pas[i])
    only_out, only_in = out_keys - in_pass, in_pass - out_keys
    report("X7", not only_out and not only_in and len(out_keys) == len(in_pass),
           "output %d events, RVec-passing input events %d, only in output %d, only in RVec set %d%s"
           % (len(out_keys), len(in_pass), len(only_out), len(only_in),
              (", e.g. %s" % (sorted(only_out or only_in)[0],)) if (only_out or only_in) else ""))

    # ForgeAudit row for this input
    rows = []
    for i in range(int(audit.GetEntries())):
        audit.GetEntry(i)
        rows.append({"file": str(audit.file), "n_in": int(audit.n_in), "n_pass": int(audit.n_pass),
                     "sumw": float(audit.sumw), "runs_sumw": float(audit.runs_sumw),
                     "runs_count": int(audit.runs_count), "is_mc": bool(audit.is_mc),
                     "code_n": [int(audit.code_n[j]) for j in range(forge_audit.NCODE)]})
    print("ForgeAudit: %d row(s)" % len(rows))
    for r in rows:
        top = sorted(((n, j) for j, n in enumerate(r["code_n"]) if n), reverse=True)[:6]
        print("   %s | n_in %d | n_pass %d | sumw %.9g | Runs sumw %.9g, count %d | top codes %s"
              % (r["file"], r["n_in"], r["n_pass"], r["sumw"], r["runs_sumw"], r["runs_count"],
                 ", ".join("%s:%d" % ("neg" if j == 0 else str(j - 1), n) for n, j in top)))
    want = forge_audit.lfn_of(args.input)
    mine = [r for r in rows if r["file"] == want] or (rows[:1] if len(rows) == 1 else [])
    if not mine:
        report("A", False, "no ForgeAudit row for %s" % want)
    else:
        r = mine[0]
        sumw = float(sum(float(w) for w in arr["genWeight"])) if is_mc else 0.0
        ok = r["n_in"] == n_in and r["n_pass"] == len(in_pass) and (not is_mc or abs(r["sumw"] - sumw) <= 1e-9 * max(1.0, abs(sumw)))
        report("A", ok, "ForgeAudit n_in %d / %d, n_pass %d / %d, sumw %.9g / %.9g (row / recomputed here)"
               % (r["n_in"], n_in, r["n_pass"], len(in_pass), r["sumw"], sumw))

    # ForgeTTbbKeys
    kt = fo.Get("ForgeTTbbKeys")
    if has_gtid:
        if not kt:
            report("K", False, "MC input with genTtbarId but no ForgeTTbbKeys in the output")
        else:
            k = ROOT.RDataFrame("ForgeTTbbKeys", args.output).AsNumpy(["run", "luminosityBlock", "event", "pass"])
            kk = [(int(k["run"][i]), int(k["luminosityBlock"][i]), int(k["event"][i])) for i in range(len(k["run"]))]
            kp = set(x for x, p in zip(kk, k["pass"]) if p)
            kf = set(x for x, p in zip(kk, k["pass"]) if not p)
            want_keys = set((int(arr["run"][i]), int(arr["luminosityBlock"][i]), int(arr["event"][i]))
                            for i in range(n_in) if arr["genTtbarId"][i] >= 0 and 53 <= arr["genTtbarId"][i] % 100 <= 55)
            ok = set(kk) == want_keys and len(kk) == len(want_keys) and kp <= out_keys and not (kf & out_keys)
            report("K", ok, "keys %d (input events with code 53..55: %d), pass=1 %d all in the output: %s, "
                            "pass=0 %d none in the output: %s"
                   % (len(kk), len(want_keys), len(kp), kp <= out_keys, len(kf), not (kf & out_keys)))
    else:
        report("K", not kt, "no genTtbarId in the input, ForgeTTbbKeys %s" % ("absent" if not kt else "PRESENT"))
    print("RESULT: %s" % ("ALL PASS" if not fails else "FAIL (%s)" % ", ".join(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
