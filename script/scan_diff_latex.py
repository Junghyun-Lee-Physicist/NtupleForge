#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_diff_latex.py -- which registry samples exist in NanoAOD version A but not in B?

Reads two das_scan.sh logs (same era, different --nano) and answers, per registry
key, one of three things:

    EXACT      the campaign string matched as configured
    RELAXED    found only through das_scan.sh's relaxed fallback  -> a human must
               look at WHICH dataset was matched (it may be a different primary,
               a different generator, or a different -vN); nevents often differ
    NOT_FOUND  nothing on DAS for that primary in that campaign

and emits (1) a plain-text verification listing and (2) LaTeX tables:

    Table 1  keys present in A and NOT_FOUND in B          <- "v9 has it, v15 does not"
    Table 2  keys RELAXED in B, with the dataset that matched and both nevents

WHY TWO TABLES
--------------
On 2026-08-31 the 2017UL v15 scan gave 47 EXACT / 11 RELAXED / 6 NOT_FOUND. The 6
are the real gap. But among the 11 RELAXED, the seven QCD_HT* keys and TTTW
matched datasets with nevents 30-90 % away from v9 -- i.e. probably a different
production, not the same events with a new release. Listing only NOT_FOUND would
hide that. Data (JetHT/BTagCSV/SingleMuon) is RELAXED for a benign reason: the
v15 Data processing string drops "MiniAODv2_" (docs/05 A20).

FLAVOURS
--------
A key can have several DS| lines (plain + JMENano/BTVNano/PFNano/PUFor* re-runs).
The plain campaign is chosen for the numbers; flavours are ignored, like
pair_v9_v15.py does. Note: for 2017UL TTToSemiLeptonic the v9 *JMENano* flavour
has 354.9M events while the plain v9 has 346.1M -- the plain v9 is the one that
is 2.61 % short of its MiniAOD parent (docs/09 5).

USAGE
-----
    python3 script/scan_diff_latex.py \
        --a script/das_ttHH_2017UL_v9_<stamp>.log \
        --b script/das_ttHH_2017UL_v15_<stamp>.log \
        --label-a v9 --label-b v15 \
        --registry script/samples_registry.txt \
        --tex script/missing_in_v15_2017UL.tex

EXIT
----
    0 ok, 2 bad input
"""
from __future__ import print_function

import argparse
import os
import re
import sys

FLAVOUR = re.compile(r"(JMENano|BTVNano|PFNano|PUFor|Pilot)", re.I)


def read_registry(path):
    """key -> (type, primary, group)"""
    reg = {}
    if not path or not os.path.isfile(path):
        return reg
    for line in open(path, encoding="utf-8", errors="replace"):
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split()
        if len(f) >= 6:
            reg[f[1]] = (f[0], f[2], f[4])
    return reg


def read_scan(path):
    """-> meta(dict), ds(key -> [ {dataset, nevents, nfiles} ]), result(key -> status)"""
    meta, ds, result = {}, {}, {}
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("META|"):
            for kv in line.split("|")[1:]:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    meta[k] = v
        elif line.startswith("DS|"):
            p = line.split("|")
            if len(p) < 4:
                continue
            key, dataset = p[1], p[2]
            rec = {"dataset": dataset, "nevents": None, "nfiles": None}
            for kv in p[3:]:
                if kv.startswith("nevents="):
                    rec["nevents"] = int(kv.split("=", 1)[1] or 0)
                elif kv.startswith("nfiles="):
                    rec["nfiles"] = int(kv.split("=", 1)[1] or 0)
            ds.setdefault(key, []).append(rec)
        elif line.startswith("RESULT|"):
            p = line.split("|")
            if len(p) >= 3:
                result[p[1]] = p[2]
    return meta, ds, result


def plain(recs):
    """the non-flavour dataset(s) for a key; if none, fall back to everything"""
    if not recs:
        return []
    pl = [r for r in recs if not FLAVOUR.search(r["dataset"])]
    return pl or recs


ERA_TOKEN = re.compile(r"/(Run20\d\d[A-Z])-")


def data_per_era(recs):
    """DATA: {era: record} keeping ONE dataset per run era.

    A Data key returns several DS lines per era: the plain processing plus
    re-processings with a different GT (e.g. '..._NanoAODv9_GT36-v1', two of
    them for Run2017G) and flavours (BTVNanoAODv15). Flavours are dropped by
    plain(); among what is left, the SHORTEST dataset name per era is the plain
    one (extra tokens only ever lengthen the name). Summing everything would
    double-count -- 2017UL v9 SingleMuon has 15 lines for 7 eras.
    """
    per = {}
    for r in plain(recs):
        m = ERA_TOKEN.search(r["dataset"])
        era = m.group(1) if m else r["dataset"]
        if era not in per or len(r["dataset"]) < len(per[era]["dataset"]):
            per[era] = r
    return per


VN_SUFFIX = re.compile(r"-v(\d+)/([A-Z]+)$")


def mc_datasets(recs):
    """MC: the plain datasets that carry DISTINCT events, i.e. nominal + _extN.

    A superseded re-release of the SAME production shows up as the same name
    with a higher -vN; keep only the highest -vN per name so nothing is counted
    twice. Flavours (JMENano/BTVNano/PFNano/PUFor*/Pilot) are already gone.
    2017UL v9 examples: TTZHTo4b = nominal 5.0M + ext1 5.0M (two datasets,
    both real); WJetsToLNu_HT400To600 = nominal + ext1 + ext2.
    """
    best = {}
    for r in plain(recs):
        m = VN_SUFFIX.search(r["dataset"])
        stem = VN_SUFFIX.sub("/\\2", r["dataset"]) if m else r["dataset"]
        vn = int(m.group(1)) if m else 0
        if stem not in best or vn > best[stem][0]:
            best[stem] = (vn, r)
    return [best[s][1] for s in sorted(best)]


def pick(recs, is_data):
    """-> (dataset_shown, nevents, nfiles, n_datasets, per_era_or_None)

    MC   : nominal + _extN summed (see mc_datasets); shown = the first one.
    DATA : one dataset per run era (see data_per_era), summed; the shown path
           has the era replaced by '*'.
    """
    pl = plain(recs)
    if not pl:
        return "", None, None, 0, None
    if not is_data:
        recs1 = mc_datasets(recs)
        ne = sum(r["nevents"] or 0 for r in recs1)
        nf = sum(r["nfiles"] or 0 for r in recs1)
        return recs1[0]["dataset"], ne, nf, len(recs1), None
    per = data_per_era(recs)
    recs1 = [per[e] for e in sorted(per)]
    ne = sum(r["nevents"] or 0 for r in recs1)
    nf = sum(r["nfiles"] or 0 for r in recs1)
    shown = ERA_TOKEN.sub("/Run20XX*-", recs1[0]["dataset"], count=1)
    return shown, ne, nf, len(recs1), per


def primaries_of(recs, is_data):
    """distinct primary dataset names among the counted datasets"""
    rs = [per for per in data_per_era(recs).values()] if is_data else mc_datasets(recs)
    out = []
    for r in rs:
        p = primary_of(r["dataset"])
        if p not in out:
            out.append(p)
    return out


def primary_of(dataset):
    parts = dataset.strip("/").split("/")
    return parts[0] if parts else dataset


def fmt_int(n):
    return "--" if n is None else "{:,}".format(n)


def tex_escape(s):
    return (s.replace("\\", r"\textbackslash{}").replace("_", r"\_")
             .replace("%", r"\%").replace("&", r"\&").replace("#", r"\#"))


def tex_tt(s):
    return r"\texttt{" + tex_escape(s) + "}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="scan log of version A (e.g. v9)")
    ap.add_argument("--b", required=True, help="scan log of version B (e.g. v15)")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--registry",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "samples_registry.txt"))
    ap.add_argument("--tex", help="write LaTeX here (default: stdout after the text summary)")
    ap.add_argument("--caption-era", default=None,
                    help="era text for captions; default from META|era")
    args = ap.parse_args()

    for p in (args.a, args.b):
        if not os.path.isfile(p):
            sys.exit("ERROR(2): no such file: %s" % p)

    reg = read_registry(args.registry)
    meta_a, ds_a, res_a = read_scan(args.a)
    meta_b, ds_b, res_b = read_scan(args.b)
    era = args.caption_era or meta_a.get("era") or meta_b.get("era") or "?"
    la, lb = args.label_a, args.label_b

    keys = sorted(set(res_a) | set(res_b),
                  key=lambda k: (reg.get(k, ("", "", "zzz"))[2], k))

    missing, relaxed, both_ok = [], [], []
    for k in keys:
        sa, sb = res_a.get(k, "NOT_FOUND"), res_b.get(k, "NOT_FOUND")
        typ = reg.get(k, ("?", "", ""))[0]
        # Do not depend on the registry alone: the tier in the dataset path is
        # authoritative (Data = /NANOAOD, MC = /NANOAODSIM).
        tiers = {r["dataset"].rstrip("/").split("/")[-1] for r in ds_a.get(k, []) + ds_b.get(k, [])}
        is_data = (typ == "DATA") or (tiers == {"NANOAOD"})
        if typ == "?":
            typ = "DATA" if is_data else "MC"
        da, na, nfa, cnt_a, era_a = pick(ds_a.get(k, []), is_data)
        db, nb, nfb, cnt_b, era_b = pick(ds_b.get(k, []), is_data)
        prims_a = primaries_of(ds_a.get(k, []), is_data)
        prims_b = primaries_of(ds_b.get(k, []), is_data)
        row = {"key": k, "group": reg.get(k, ("", "", "?"))[2], "type": typ,
               "sa": sa, "sb": sb, "na": na, "nb": nb,
               "da": da, "db": db, "nfa": nfa, "nfb": nfb,
               "cnt_a": cnt_a, "cnt_b": cnt_b, "era_a": era_a, "era_b": era_b,
               "prims_a": prims_a, "prims_b": prims_b,
               "prim_a": prims_a[0] if prims_a else "", "prim_b": prims_b[0] if prims_b else "",
               "prim_differs": bool(prims_a and prims_b and set(prims_a) != set(prims_b))}
        if sa != "NOT_FOUND" and sb == "NOT_FOUND":
            missing.append(row)
        elif sb == "RELAXED":
            relaxed.append(row)
        else:
            both_ok.append(row)

    # ---------------- text summary (for the human, and for the log) ----------------
    print("=" * 78)
    print("A = %s  (%s)   nano=%s  utc=%s" % (la, os.path.basename(args.a), meta_a.get("nano"), meta_a.get("utc")))
    print("B = %s  (%s)   nano=%s  utc=%s" % (lb, os.path.basename(args.b), meta_b.get("nano"), meta_b.get("utc")))
    print("keys: %d   in %s but NOT in %s: %d   RELAXED in %s: %d   exact/ok both: %d"
          % (len(keys), la, lb, len(missing), lb, len(relaxed), len(both_ok)))
    print("-" * 78)
    print("[1] present in %s, NOT_FOUND in %s" % (la, lb))
    for r in missing:
        ext = "  [%d datasets: nominal+ext]" % r["cnt_a"] if r["cnt_a"] > 1 else ""
        print("  %-22s %-9s %s=%s%s  %s" % (r["key"], r["group"], la, fmt_int(r["na"]), ext, r["da"]))
    print("-" * 78)
    print("[2] RELAXED in %s (campaign string did not match exactly -- check what was matched)" % lb)
    for r in relaxed:
        d = None if (r["na"] is None or r["nb"] is None) else r["nb"] - r["na"]
        flag = ""
        if r["prim_differs"]:
            flag = "   <-- DIFFERENT PRIMARY (a sibling sample, not the same events)"
        elif d is not None and r["na"] and abs(d) / float(r["na"]) > 0.05:
            flag = "   <-- %+.0f %% events" % (100.0 * d / r["na"])
        era_note = ""
        if r["type"] == "DATA":
            era_note = "  [sum over %d/%d run eras]" % (r["cnt_a"], r["cnt_b"])
        print("  %-22s %-9s %s=%-14s %s=%-14s%s%s"
              % (r["key"], r["group"], la, fmt_int(r["na"]), lb, fmt_int(r["nb"]), era_note, flag))
        if r["prim_differs"]:
            print("      %s primary: %s" % (la, ", ".join(r["prims_a"])))
            print("      %s primary: %s" % (lb, ", ".join(r["prims_b"])))
        else:
            print("      %s: %s" % (lb, r["db"]))
        if r["type"] == "DATA" and r["era_a"] and r["era_b"]:
            # NB: loop variable must not be called `era` -- that name holds the
            # campaign era for the LaTeX captions below (Python for-loops leak).
            for run_era in sorted(set(r["era_a"]) | set(r["era_b"])):
                ea, eb = r["era_a"].get(run_era), r["era_b"].get(run_era)
                if ea is None or eb is None:
                    print("      %-10s only in %s" % (run_era, la if ea else lb))
                elif ea["nevents"] != eb["nevents"]:
                    print("      %-10s %s=%-14s %s=%-14s (%+d)"
                          % (run_era, la, fmt_int(ea["nevents"]), lb, fmt_int(eb["nevents"]),
                             (eb["nevents"] or 0) - (ea["nevents"] or 0)))
    n_sibling = sum(1 for r in relaxed if r["prim_differs"])
    print("-" * 78)
    print("NOTE  %d of the %d RELAXED keys matched a DIFFERENT primary dataset in %s." % (n_sibling, len(relaxed), lb))
    print("      For the analysis those are closer to 'missing' than 'present' until someone")
    print("      decides the sibling is acceptable (e.g. QCD *_PSWeights* vs *madgraphMLM*).")
    print("=" * 78)

    # ---------------- LaTeX ----------------
    out = []
    w = out.append
    w("%% generated by script/scan_diff_latex.py -- do not edit by hand")
    w("%% A = %s : %s" % (la, os.path.basename(args.a)))
    w("%% B = %s : %s" % (lb, os.path.basename(args.b)))
    w("%% needs \\usepackage{booktabs}")
    w("")
    w(r"\begin{table}[htbp]")
    w(r"  \centering\small")
    w(r"  \caption{%s: samples available as NanoAOD %s but with no central NanoAOD %s (%d of %d registry keys)."
      r" These are the candidates for private production.}"
      % (tex_escape(era), tex_escape(la), tex_escape(lb), len(missing), len(keys)))
    w(r"  \label{tab:missing_%s_%s}" % (lb, era.replace(" ", "")))
    w(r"  \begin{tabular}{llrl}")
    w(r"    \toprule")
    w(r"    sample & group & %s events & %s dataset \\" % (tex_escape(la), tex_escape(la)))
    w(r"    \midrule")
    any_ext = False
    for r in missing:
        ds_tex = tex_tt(r["da"])
        if r["cnt_a"] > 1:
            any_ext = True
            ds_tex += r" {\scriptsize(+%d ext)}" % (r["cnt_a"] - 1)
        w(r"    %s & %s & %s & {\scriptsize %s} \\"
          % (tex_tt(r["key"]), tex_escape(r["group"]), fmt_int(r["na"]), ds_tex))
    w(r"    \bottomrule")
    w(r"  \end{tabular}")
    if any_ext:
        w(r"  \par\smallskip\raggedright\footnotesize Event counts include the \texttt{\_ext} extensions of the same production where they exist (\texttt{+N ext}).")
    w(r"\end{table}")
    w("")
    if relaxed:
        w(r"\begin{table}[htbp]")
        w(r"  \centering\small")
        w(r"  \caption{%s: samples found in NanoAOD %s only through a relaxed campaign match (%d keys)."
          r" A large event-count difference means a different production rather than a re-release of the same events;"
          r" the Data primary datasets differ only in the processing string (\texttt{UL2017\_NanoAODv15} vs \texttt{UL2017\_MiniAODv2\_NanoAODv9}).}"
          % (tex_escape(era), tex_escape(lb), len(relaxed)))
        w(r"  \label{tab:relaxed_%s_%s}" % (lb, era.replace(" ", "")))
        w(r"  \begin{tabular}{llrrrl}")
        w(r"    \toprule")
        w(r"    sample & group & %s events & %s events & $\Delta$ & %s primary matched \\"
          % (tex_escape(la), tex_escape(lb), tex_escape(lb)))
        w(r"    \midrule")
        for r in relaxed:
            if r["na"] is None or r["nb"] is None or not r["na"]:
                dl = "--"
            else:
                pct = 100.0 * (r["nb"] - r["na"]) / r["na"]
                dl = ("%+.2f\\%%" if abs(pct) < 0.1 else "%+.1f\\%%") % pct
            if r["prim_differs"]:
                prim_tex = r"\textbf{" + r" \\ ".join(tex_tt(p) for p in r["prims_b"]) + "}"
                if len(r["prims_b"]) > 1:
                    prim_tex = r"\begin{tabular}[t]{@{}l@{}}\textbf{" + r"} \\ \textbf{".join(tex_tt(p) for p in r["prims_b"]) + r"}\end{tabular}"
            elif r["type"] == "DATA":
                prim_tex = tex_tt(r["prim_b"]) + r" {\scriptsize(proc.\ string only)}"
            else:
                prim_tex = tex_tt(r["prim_b"])
            w(r"    %s & %s & %s & %s & %s & {\scriptsize %s} \\"
              % (tex_tt(r["key"]), tex_escape(r["group"]), fmt_int(r["na"]), fmt_int(r["nb"]), dl, prim_tex))
        w(r"    \bottomrule")
        w(r"  \end{tabular}")
        w(r"  \par\smallskip\raggedright\footnotesize Bold = a different primary dataset than the %s one (a sibling sample, not a re-release of the same events)."
          r" Data event counts are summed over all run eras of the primary dataset." % tex_escape(la))
        w(r"\end{table}")
    tex = "\n".join(out) + "\n"

    if args.tex:
        with open(args.tex, "w", encoding="utf-8") as fh:
            fh.write(tex)
        print("wrote %s" % args.tex)
    else:
        print(tex)
    return 0


if __name__ == "__main__":
    sys.exit(main())
