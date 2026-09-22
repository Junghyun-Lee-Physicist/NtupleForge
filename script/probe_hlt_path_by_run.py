#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_hlt_path_by_run.py -- in which runs does a NanoAOD Data dataset carry a
given HLT branch? Schema-only probe, one file per sampled run.

WHY (2026-09-17, docs/01_STATUS.md 22n)
  The first file of /JetHT/Run2018A-UL2018_NanoAODv15-v2 (runs 316058-316719)
  has no HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94 and no
  HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59 -- the two six-jet paths the
  analyzer requires for 2018 (requireTriggerBranches2018_() FATALs without
  them). Run2018B files have them. The HLT branch set of a NanoAOD file is the
  trigger menu of the runs the file covers, so sampling files by run brackets
  the run where a path entered (or left) the menu. DAS knows runs and files;
  it does not know the menu. This script combines the two.

RESULT (2026-09-18, run_probe_2018{A,B}_sixjet_20260918_07*.log)
  UL2018 NanoAODv15 files are not run-ordered: every sampled 2018A file spans
  almost the whole era (e.g. 315257-316995), so the method resolves to the
  era boundary here. 2018A: 9 files, all four flags 0 0 1 1 (old pair only).
  2018B: 6 files, all 1 1 1 1. Schema alone brackets the 2p94 / 1p59 entry
  between run 316995 (end of 2018A) and the first 2018B file (317080-317696);
  AN2019_094 Table 28 gives the run: 317509, inside 2018B (docs/08 7.4).

USAGE (lxplus, inside cmssw-el8 after cmsenv; needs dasgoclient + ROOT + proxy)
    python3 script/probe_hlt_path_by_run.py \\
        --dataset /JetHT/Run2018A-UL2018_NanoAODv15-v2/NANOAOD \\
        --paths HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94,HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59 \\
        --min-run 316700 --every 2

  --every N     probe every N-th run of the dataset (after --min-run / before
                --max-run). Files usually span several runs, so neighbouring
                runs often map to the same file; each file is opened once.
  --max-files   safety cap on distinct files opened (default 40).
  --dry-run     list the runs and files that would be probed, open nothing.

OUTPUT (stdout, one line per probed run, then a summary)
    RUN|<run>|<lfn>|<file_min_run>-<file_max_run>|<path>=0/1 ...
    SUMMARY|<path>|first_file_with=<min run of that file or ->|last_file_without=<max run or ->

  Read the summary as a bracket: the path entered the menu somewhere between
  last_file_without and first_file_with. Files overlap in runs, so the two
  numbers can be close or even inverted by one file; that is the resolution
  of this method, not an error.

EXIT  0 ok, 2 bad arguments / no runs, 3 dasgoclient failure, 4 ROOT failure
Read-only: nothing is written except stdout. Wrap with script/runlog.sh.

PYTHON  Must parse on the el8 system Python 3.6 too (that is what `python3` is
        inside cmssw-el8 BEFORE cmsenv), so that a missing cmsenv is reported
        as "FATAL: PyROOT not importable ..." (exit 4) instead of a SyntaxError.
        2026-09-18: batch 3 hit exactly that (a `from __future__ import
        annotations` line, 3.7+ only, hid the real cause). No type annotations,
        no f-strings, no walrus in this file.
"""
import argparse
import os
import subprocess
import sys

XRD = "root://cms-xrd-global.cern.ch/"


def das(query):
    try:
        # stdout/stderr=PIPE + universal_newlines instead of capture_output/text: those two
        # keywords are 3.7+, and this must still run (and fail clearly) on the el8 system 3.6.
        out = subprocess.run(["dasgoclient", "-query", query], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, universal_newlines=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        print("FATAL: dasgoclient failed for %r: %s" % (query, e), file=sys.stderr)
        sys.exit(3)
    if out.returncode != 0:
        print("FATAL: dasgoclient rc=%d for %r: %s" % (out.returncode, query, out.stderr.strip()),
              file=sys.stderr)
        sys.exit(3)
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def select_runs(runs, min_run, max_run, every):
    """Sorted runs inside [min_run, max_run], every N-th, always keeping the
    first and the last of the window so the bracket edges are covered."""
    sel = sorted(r for r in runs if (min_run is None or r >= min_run) and (max_run is None or r <= max_run))
    if not sel:
        return []
    picked = sel[::max(1, every)]
    if picked[-1] != sel[-1]:
        picked.append(sel[-1])
    return picked


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--paths", required=True, help="comma-separated HLT branch names")
    ap.add_argument("--min-run", type=int, default=None)
    ap.add_argument("--max-run", type=int, default=None)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--max-files", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = [p for p in args.paths.split(",") if p]
    if not paths:
        print("FATAL: --paths is empty", file=sys.stderr)
        return 2

    # Environment check BEFORE the first DAS query, so a missing cmsenv is the
    # first and only message (2026-09-18 batch 3: the cause was hidden).
    ROOT = None
    if not args.dry_run:
        try:
            import ROOT as _R  # noqa: N811
            _R.gROOT.SetBatch(True)
            _R.gErrorIgnoreLevel = _R.kError
            ROOT = _R
        except ImportError:
            print("FATAL: PyROOT not importable from %s (python %d.%d, CMSSW_BASE=%s)."
                  " Run inside cmssw-el8 AFTER cmsenv."
                  % (sys.executable, sys.version_info[0], sys.version_info[1],
                     os.environ.get("CMSSW_BASE", "<unset>")), file=sys.stderr)
            return 4

    runs = []
    for tok in das("run dataset=%s" % args.dataset):
        try:
            runs.append(int(tok))
        except ValueError:
            pass
    if not runs:
        print("FATAL: no runs returned for %s" % args.dataset, file=sys.stderr)
        return 2
    picked = select_runs(runs, args.min_run, args.max_run, args.every)
    print("# dataset      : %s" % args.dataset)
    print("# runs in DAS  : %d (%d..%d); probing %d run(s), every %d, window %s..%s"
          % (len(runs), min(runs), max(runs), len(picked), args.every,
             args.min_run if args.min_run is not None else "-",
             args.max_run if args.max_run is not None else "-"))
    print("# paths        : %s" % ", ".join(paths))

    file_cache = {}      # lfn -> (min_run, max_run, {path: 0/1})
    first_with = {p: None for p in paths}
    last_without = {p: None for p in paths}
    opened = 0

    for run in picked:
        files = das("file dataset=%s run=%d" % (args.dataset, run))
        if not files:
            print("RUN|%d|<no file>|-|" % run)
            continue
        lfn = sorted(files)[0]
        if lfn not in file_cache:
            if opened >= args.max_files:
                print("# --max-files %d reached; stopping at run %d" % (args.max_files, run))
                break
            fr = [int(x) for x in das("run file=%s" % lfn) if x.isdigit()]
            fmin, fmax = (min(fr), max(fr)) if fr else (run, run)
            flags = {}
            if args.dry_run:
                flags = {p: -1 for p in paths}
            else:
                f = ROOT.TFile.Open(XRD + lfn)
                if not f or f.IsZombie():
                    print("FATAL: cannot open %s" % lfn, file=sys.stderr)
                    return 4
                t = f.Get("Events")
                if not t:
                    print("FATAL: no Events tree in %s" % lfn, file=sys.stderr)
                    f.Close()
                    return 4
                for p in paths:
                    flags[p] = 1 if t.GetBranch(p) else 0
                f.Close()
            opened += 1
            file_cache[lfn] = (fmin, fmax, flags)
            for p in paths:
                if flags[p] == 1 and (first_with[p] is None or fmin < first_with[p]):
                    first_with[p] = fmin
                if flags[p] == 0 and (last_without[p] is None or fmax > last_without[p]):
                    last_without[p] = fmax
        fmin, fmax, flags = file_cache[lfn]
        print("RUN|%d|%s|%d-%d|%s" % (run, lfn, fmin, fmax,
                                     " ".join("%s=%s" % (p, "?" if flags[p] == -1 else flags[p]) for p in paths)))

    print("# files opened : %d" % opened)
    for p in paths:
        print("SUMMARY|%s|first_file_with=%s|last_file_without=%s"
              % (p, first_with[p] if first_with[p] is not None else "-",
                 last_without[p] if last_without[p] is not None else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
