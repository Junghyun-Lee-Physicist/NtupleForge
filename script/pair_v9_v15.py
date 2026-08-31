#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pair_v9_v15.py -- find a comparable FILE PAIR across two NanoAOD versions.

THE PROBLEM
-----------
v9 and v15 of the same dataset share an identical MiniAOD parent, so the same
events exist on both sides. But the NanoAOD job splitting differs per campaign,
so the FILE boundaries do not correspond at all: on 2026-08-30 the first file of
v9 and the first file of v15 of TTToSemiLeptonic had **zero** events in common,
even though their luminosity-block RANGES overlapped almost completely. Event
order inside a lumi is preserved (it comes from the MiniAOD), but which lumis
land in which output file is not.

So an event-matched v9<->v15 comparison needs a pair of files that actually
share luminosity blocks, plus the shared-lumi list to restrict both runs to
(run_postproc.py --cut). This finds them.

WHY IT NEEDS NO FILE ACCESS
---------------------------
`dasgoclient -query="file,lumi dataset=..."` returns the lumi list of every
file. Both sides come from DAS, so the pairing is pure metadata -- seconds, no
xrdcp, no ROOT.

FLAVOUR VARIANTS
----------------
JMENano / BTVNano / PFNano re-productions of the same campaign carry different
branch content and different file splitting. They are excluded unless
--allow-flavours is given; the plain campaign with the highest -vN wins.

USAGE
-----
    # by dataset, explicit
    python3 script/pair_v9_v15.py \\
        --ds-a /TTToSemiLeptonic.../RunIISummer20UL17NanoAODv9-.../NANOAODSIM \\
        --ds-b /TTToSemiLeptonic.../RunIISummer20UL17NanoAODv15-.../NANOAODSIM

    # by registry key, resolving both campaigns from the era table
    python3 script/pair_v9_v15.py --sample TTbar_SemiLep --era 2017UL \\
        --nano-a v9 --nano-b v15 --out-dir script/pairs

    # several samples at once
    python3 script/pair_v9_v15.py --era 2017UL --nano-a v9 --nano-b v15 \\
        --sample TTbar_SemiLep --sample TTbar_Hadronic --sample TTbb_Hadronic

OUTPUT
------
One JSON per sample under --out-dir (default script/pairs/), holding the two
LFNs, the shared lumi list and the ready-made `--cut` expression, plus a
one-line summary on stdout.

EXIT CODES
----------
    0  every requested sample got a pair
    2  at least one sample has NO shared lumi (comparison impossible)
    3  at least one dataset could not be resolved on DAS
    4  bad arguments / dasgoclient missing
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

FLAVOUR = re.compile(r"(JMENano|BTVNano|PFNano|BTVNanoV\d+|JMENanoAOD|BTVNanoAOD)", re.I)
VN = re.compile(r"-v(\d+)/[A-Z]+$")

# era -> MC campaign prefix, mirroring script/das_scan.sh's era table. Kept
# small on purpose: this tool only needs the MC side.
ERA_MC = {
    "2016preVFPUL": "RunIISummer20UL16NanoAODAPV%s",
    "2016postVFPUL": "RunIISummer20UL16NanoAOD%s",
    "2017UL": "RunIISummer20UL17NanoAOD%s",
    "2018UL": "RunIISummer20UL18NanoAOD%s",
}


def das(query):
    try:
        out = subprocess.run(["dasgoclient", "-query=" + query],
                             capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        sys.exit("ERROR(4): dasgoclient not found. cmsenv first.")
    return [l.strip() for l in out.stdout.splitlines() if l.strip()]


def pick_plain(datasets, allow_flavours=False):
    """Prefer the plain campaign; among equals take the highest -vN."""
    cands = datasets if allow_flavours else [d for d in datasets if not FLAVOUR.search(d)]
    if not cands:
        cands = datasets
    def key(d):
        m = VN.search(d)
        return int(m.group(1)) if m else 0
    return sorted(cands, key=key)[-1] if cands else None


def file_lumi_map(dataset):
    """{lfn: set(lumi)} straight from DAS -- no file is opened."""
    rows = das("file,lumi dataset=%s" % dataset)
    pat = re.compile(r"^(/store/\S+\.root)\s+\[([0-9,\s]+)\]\s*$")
    m, unparsed = {}, 0
    for line in rows:
        mm = pat.match(line)
        if not mm:
            unparsed += 1
            continue
        m[mm.group(1)] = {int(x) for x in mm.group(2).replace(" ", "").split(",") if x}
    return m, len(rows), unparsed


def resolve(sample_primary, era, nano, allow_flavours):
    camp = ERA_MC.get(era)
    if not camp:
        sys.exit("ERROR(4): unknown era '%s' (known: %s)" % (era, ", ".join(sorted(ERA_MC))))
    q = "/%s/%s*/NANOAODSIM" % (sample_primary, camp % nano)
    hits = das("dataset=" + q)
    return pick_plain(hits, allow_flavours), q


def registry_primary(registry, key):
    if not os.path.isfile(registry):
        return None
    for line in open(registry, encoding="utf-8", errors="replace"):
        if line.startswith("#") or not line.strip():
            continue
        f = line.split()
        if len(f) >= 3 and f[1] == key:
            return f[2]
    return None


def pair_one(ds_a, ds_b, label, out_dir, top=5):
    print("=" * 74)
    print("%s" % label)
    print("  A = %s" % ds_a)
    print("  B = %s" % ds_b)

    ma, na, ua = file_lumi_map(ds_a)
    mb, nb, ub = file_lumi_map(ds_b)
    print("  A: %d files (%d das lines, %d unparsed)" % (len(ma), na, ua))
    print("  B: %d files (%d das lines, %d unparsed)" % (len(mb), nb, ub))
    if not ma or not mb:
        print("  !! could not build a file->lumi map; cannot pair")
        return None

    # Anchor on A's largest file, then rank B against it.
    anchor = max(ma, key=lambda f: len(ma[f]))
    la = ma[anchor]
    ranked = sorted(((len(la & lb), f) for f, lb in mb.items()), reverse=True)
    print("  anchor A file: %d lumis  %s" % (len(la), anchor.split("/")[-1]))
    print("  best B files:")
    for n, f in ranked[:top]:
        print("      shared=%-6d lumis_in_file=%-6d %s" % (n, len(mb[f]), f.split("/")[-1]))

    best_n, best_f = ranked[0] if ranked else (0, None)
    if best_n == 0:
        print("  !! NO shared luminosity block -- an event-matched comparison of")
        print("     this pair is impossible. Try another anchor file, or compare")
        print("     distributions over the full datasets instead.")
        return None

    shared = sorted(la & mb[best_f])
    cut = "||".join("luminosityBlock==%d" % l for l in shared)
    rec = {"label": label, "dataset_a": ds_a, "dataset_b": ds_b,
           "lfn_a": anchor, "lfn_b": best_f,
           "n_shared_lumi": len(shared), "shared_lumis": shared, "cut": cut}
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "pair_%s.json" % label)
    with open(path, "w") as fh:
        json.dump(rec, fh, indent=2)
    print("  -> shared %d lumis, cut %d bytes  ->  %s" % (len(shared), len(cut), path))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds-a", help="dataset A (e.g. the v9 one)")
    ap.add_argument("--ds-b", help="dataset B (e.g. the v15 one)")
    ap.add_argument("--sample", action="append", default=[],
                    help="registry key (repeatable); resolves both campaigns")
    ap.add_argument("--era", default="2017UL")
    ap.add_argument("--nano-a", default="v9")
    ap.add_argument("--nano-b", default="v15")
    ap.add_argument("--registry",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "samples_registry.txt"))
    ap.add_argument("--out-dir",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "pairs"))
    ap.add_argument("--allow-flavours", action="store_true",
                    help="do not exclude JMENano/BTVNano/PFNano re-productions")
    args = ap.parse_args()

    jobs = []
    if args.ds_a and args.ds_b:
        jobs.append((args.ds_a, args.ds_b, args.ds_a.strip("/").split("/")[0]))
    for key in args.sample:
        prim = registry_primary(args.registry, key)
        if not prim:
            print("!! '%s' not in %s" % (key, args.registry)); continue
        a, qa = resolve(prim, args.era, args.nano_a, args.allow_flavours)
        b, qb = resolve(prim, args.era, args.nano_b, args.allow_flavours)
        if not a:
            print("!! %s: no %s dataset (%s)" % (key, args.nano_a, qa)); continue
        if not b:
            print("!! %s: no %s dataset (%s)" % (key, args.nano_b, qb)); continue
        jobs.append((a, b, key))

    if not jobs:
        sys.exit("ERROR(3): nothing to pair. Give --ds-a/--ds-b or --sample.")

    ok, bad = [], []
    for ds_a, ds_b, label in jobs:
        rec = pair_one(ds_a, ds_b, label, args.out_dir)
        (ok if rec else bad).append(label)

    print("=" * 74)
    print("paired: %d   failed: %d" % (len(ok), len(bad)))
    for l in ok:
        print("   OK   %s" % l)
    for l in bad:
        print("   FAIL %s" % l)
    sys.exit(2 if bad else 0)


if __name__ == "__main__":
    main()
