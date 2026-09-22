#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
localcheck_summary.py -- one line per local post-processing output: did the
v15 branch list + noop module produce a sane file?

    python3 script/localcheck_summary.py localcheck_v15/out_*.root

Prints, per file:
    <file> | Events <n> | branches <n> | HLT_ <n> | run/lumi/event <y/n> |
    genWeight <y/n> | genTtbarId <y/n> | Runs.genEventSumw <y/n> | zombie <y/n>

WHY (2026-09-22, README section "UL18 campaign replay order" step 2, lesson A14): a branch
list that passes the schema check (check_branchlist.py, dead 0) has still
never been run through NanoAODTools on a real file of that era. One file per
(era, tier) with -N 500 is the cheapest proof before CRAB. MC files must keep
genWeight / genTtbarId and the Runs tree sums; Data files must not (y there
would mean the wrong list). Exit 0 always; the human reads the table.
Needs PyROOT (cmssw-el8 + cmsenv). Read-only.
"""
import sys


def main(paths):
    try:
        import ROOT
    except ImportError:
        print("FATAL: PyROOT not importable; run inside cmssw-el8 after cmsenv", file=sys.stderr)
        return 4
    ROOT.gROOT.SetBatch(True)
    ROOT.gErrorIgnoreLevel = ROOT.kError
    if not paths:
        print("usage: localcheck_summary.py <out.root> [...]", file=sys.stderr)
        return 2
    for p in paths:
        f = ROOT.TFile.Open(p)
        if not f or f.IsZombie():
            print("%s | ZOMBIE or unreadable" % p)
            continue
        ev = f.Get("Events")
        runs = f.Get("Runs")
        if not ev:
            print("%s | no Events tree" % p)
            f.Close()
            continue
        names = [b.GetName() for b in ev.GetListOfBranches()]
        has = lambda n: "y" if n in names else "n"
        key3 = "y" if all(k in names for k in ("run", "luminosityBlock", "event")) else "n"
        sumw = "y" if (runs and runs.GetBranch("genEventSumw")) else "n"
        print("%s | Events %d | branches %d | HLT_ %d | run/lumi/event %s | genWeight %s | genTtbarId %s | Runs.genEventSumw %s"
              % (p, ev.GetEntries(), len(names), sum(1 for n in names if n.startswith("HLT_")),
                 key3, has("genWeight"), has("genTtbarId"), sumw))
        f.Close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
