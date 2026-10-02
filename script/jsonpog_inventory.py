#!/usr/bin/env python3
# jsonpog_inventory.py
#
# Read-only inventory of the central correctionlib payloads (jsonpog-integration on CVMFS):
# which era directories exist, which files, and for every correction its name, version,
# inputs, output and the values its string/int inputs can take (category keys), the
# ranges of its binned inputs, and -- when a correction is a flat table of numbers keyed by
# a category (BTV *_wp_values) -- the numbers themselves.
#
# Why: the analyzer needs the exact 2024 payload names (b-tag WPs and SF methods, jet veto
# map key and type, jet ID corrections, JEC/JER tags, pileup key) before EraConfig 2024 is
# written (tempTTHH docs/PLAN_v15_2018UL_2024.md section 9, Stage 0). Memory and web pages
# are not a source for these; the payload is.
#
# Standard library only (gzip + json): runs on the lxplus host python3 without cmsenv,
# and does not depend on the correctionlib version.
#
# Usage:
#   python3 script/jsonpog_inventory.py                                   # default root, eras 2024 + 2017_UL + 2018_UL
#   python3 script/jsonpog_inventory.py --era-regex '^2024' --pog BTV JME LUM
#   python3 script/jsonpog_inventory.py --root /path/to/jsonpog-integration --full
#   python3 script/jsonpog_inventory.py --file POG/BTV/2024_Summer24/btagging.json.gz
#
# Output: one line per fact, '|' separated, first field the record type:
#   INV      run header (root, time, python, filters)
#   POGDIR   a POG directory and all of its era subdirectories (so unexpected names show up)
#   FILE     a payload file: bytes, mtime (UTC), schema version, number of corrections
#   CORR     one correction: name, version, inputs (name:type), output, description (cut)
#   KEYS     the category keys an input takes inside one correction (string/int inputs)
#   EDGES    the range (flow binnings included) and the number of bins (min-max over its binnings) of a binned input
#            inside one correction
#   VALUES   key=value when a correction is one category of plain numbers (e.g. WP thresholds); ' | default=...'
#            when that category also has a default (a number, or 'node' if the other keys go to a sub-tree)
#   COMPOUND a compound correction and its stack
#   SKIP     a correction whose detail was not printed (file over --max-detail corrections)
#   ERR      something could not be read (the run goes on; exit code 3 at the end)
#   SUMMARY  counts
# Exit code: 0 all read, 2 bad arguments / root missing, 3 at least one ERR line.
from __future__ import annotations

import argparse
import datetime
import gzip
import json
import os
import re
import sys

DEFAULT_ROOT = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration"
DEFAULT_POGS = ["BTV", "JME", "LUM", "EGM", "MUO"]
DEFAULT_ERA_REGEX = r"^(2024|2017_UL|2018_UL)"
MAX_NODES = 5_000_000  # per correction; a guard against pathological files


def utc(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean(s, n: int) -> str:
    s = "" if s is None else str(s)
    s = " ".join(s.split()).replace("|", "/")
    return s if len(s) <= n else s[: n - 3] + "..."


def fmt_num(x) -> str:
    if isinstance(x, bool):
        return str(x)
    if isinstance(x, int):
        return str(x)
    if isinstance(x, float):
        return "%.6g" % x
    return str(x)


class Acc:
    """What one correction's data tree says about its inputs."""

    def __init__(self):
        self.keys = {}       # input -> ordered list of keys (first seen order)
        self.keyset = {}     # input -> set, for dedup
        self.edges = {}      # input -> [lo, hi, nbins_min, nbins_max, n_binnings]
        self.nodes = 0
        self.truncated = False

    def add_key(self, inp, key):
        s = self.keyset.setdefault(inp, set())
        if key not in s:
            s.add(key)
            self.keys.setdefault(inp, []).append(key)

    def add_edges(self, inp, edges):
        if isinstance(edges, dict):  # uniform binning {"n":..,"low":..,"high":..}
            try:
                lo, hi, nb = float(edges["low"]), float(edges["high"]), int(edges["n"])
            except (KeyError, TypeError, ValueError):
                return
        else:
            try:
                vals = [float(e) for e in edges]
            except (TypeError, ValueError):
                return
            if not vals:
                return
            lo, hi, nb = min(vals), max(vals), len(vals) - 1
        cur = self.edges.get(inp)
        if cur is None:
            self.edges[inp] = [lo, hi, nb, nb, 1]
        else:
            cur[0] = min(cur[0], lo)
            cur[1] = max(cur[1], hi)
            cur[2] = min(cur[2], nb)
            cur[3] = max(cur[3], nb)
            cur[4] += 1


def walk(node, acc: Acc) -> None:
    """Iterative walk (deep trees, no recursion limit issue)."""
    stack = [node]
    while stack:
        n = stack.pop()
        acc.nodes += 1
        if acc.nodes > MAX_NODES:
            acc.truncated = True
            return
        if not isinstance(n, dict):
            continue  # a number (leaf) or a list of numbers
        t = n.get("nodetype")
        if t == "category":
            inp = n.get("input")
            for item in n.get("content", []) or []:
                if isinstance(item, dict):
                    acc.add_key(inp, item.get("key"))
                    stack.append(item.get("value"))
            if "default" in n and n["default"] is not None:
                stack.append(n["default"])
        elif t == "binning":
            acc.add_edges(n.get("input"), n.get("edges"))
            stack.extend(n.get("content", []) or [])
            fl = n.get("flow")
            if isinstance(fl, dict):
                stack.append(fl)
        elif t == "multibinning":
            for inp, edges in zip(n.get("inputs", []) or [], n.get("edges", []) or []):
                acc.add_edges(inp, edges)
            stack.extend(n.get("content", []) or [])
            fl = n.get("flow")
            if isinstance(fl, dict):
                stack.append(fl)
        elif t == "transform":
            stack.append(n.get("rule"))
            stack.append(n.get("content"))
        # formula / formularef / hashprng: leaves for this purpose


def flat_values(data):
    """If data is one category whose values are all plain numbers, return (input, [(key, value)], default):
    default is None (no default), a number, or 'node' (the other keys go to a sub-tree)."""
    if not isinstance(data, dict) or data.get("nodetype") != "category":
        return None
    out = []
    for item in data.get("content", []) or []:
        if not isinstance(item, dict):
            return None
        v = item.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        out.append((item.get("key"), v))
    if not out:
        return None
    d = data.get("default")
    if d is not None and not (isinstance(d, (int, float)) and not isinstance(d, bool)):
        d = "node"
    return data.get("input"), out, d


def load(path: str):
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def describe_file(path: str, tag: str, args, out, errs: list) -> int:
    """tag = 'POG|era|file'. Returns the number of corrections printed (with detail or not)."""
    try:
        st = os.stat(path)
        cset = load(path)
    except Exception as e:  # noqa: BLE001 -- report and go on
        out("ERR|%s|%s: %s" % (tag, type(e).__name__, clean(e, 200)))
        errs.append(path)
        return 0
    if not isinstance(cset, dict) or "corrections" not in cset:
        out("ERR|%s|not a correctionlib CorrectionSet (no 'corrections')" % tag)
        errs.append(path)
        return 0
    corrs = cset.get("corrections") or []
    comps = cset.get("compound_corrections") or []
    out("FILE|%s|bytes=%d|mtime=%s|schema=%s|corrections=%d|compound=%d|desc=%s" % (
        tag, st.st_size, utc(st.st_mtime), cset.get("schema_version"), len(corrs), len(comps),
        clean(cset.get("description"), 160)))
    name_re = re.compile(args.name_regex) if args.name_regex else None
    nsel = sum(1 for c in corrs if not name_re or name_re.search(str(c.get("name"))))
    detail = args.full or nsel <= args.max_detail
    nprint = 0
    for c in sorted(corrs, key=lambda x: str(x.get("name"))):
        name = str(c.get("name"))
        if name_re and not name_re.search(name):
            continue
        ins = ",".join("%s:%s" % (i.get("name"), i.get("type")) for i in (c.get("inputs") or []))
        o = c.get("output") or {}
        out("CORR|%s|%s|v=%s|in=%s|out=%s:%s|desc=%s" % (
            tag, name, c.get("version"), ins, o.get("name"), o.get("type"),
            clean(c.get("description"), args.desc_len)))
        nprint += 1
        if not detail:
            continue
        acc = Acc()
        walk(c.get("data"), acc)
        if acc.truncated:
            out("ERR|%s|%s|walk stopped after %d nodes" % (tag, name, MAX_NODES))
            errs.append(path + ":" + name)
        itypes = {i.get("name"): i.get("type") for i in (c.get("inputs") or [])}
        for inp in [i.get("name") for i in (c.get("inputs") or [])] + sorted(
                (k for k in set(acc.keys) | set(acc.edges) if k not in itypes), key=str):
            if inp in acc.keys:
                ks = acc.keys[inp]
                shown = ks[: args.max_keys]
                more = "" if len(ks) <= args.max_keys else " (+%d more)" % (len(ks) - args.max_keys)
                out("KEYS|%s|%s|%s=[%s]%s" % (tag, name, inp, ",".join(fmt_num(k) for k in shown), more))
            if inp in acc.edges:
                lo, hi, nbmin, nbmax, nbin = acc.edges[inp]
                nbs = "%d" % nbmin if nbmin == nbmax else "%d-%d" % (nbmin, nbmax)
                out("EDGES|%s|%s|%s=[%s..%s] nbins=%s binnings=%d" % (
                    tag, name, inp, fmt_num(lo), fmt_num(hi), nbs, nbin))
        fv = flat_values(c.get("data"))
        if fv:
            inp, pairs, dflt = fv
            out("VALUES|%s|%s|%s: %s%s" % (tag, name, inp, ", ".join(
                "%s=%s" % (fmt_num(k), fmt_num(v)) for k, v in pairs[: args.max_keys]),
                "" if dflt is None else " | default=%s" % fmt_num(dflt)))
    if not detail:
        out("SKIP|%s|%d corrections%s over --max-detail %d: names only (use --full or a narrower --name-regex)" % (
            tag, nsel, " matching" if name_re else "", args.max_detail))
    for cc in sorted(comps, key=lambda x: str(x.get("name"))):
        name = str(cc.get("name"))
        if name_re and not name_re.search(name):
            continue
        out("COMPOUND|%s|%s|stack=%s|in=%s" % (tag, name, ",".join(str(s) for s in (cc.get("stack") or [])),
                                              ",".join(str(i.get("name")) for i in (cc.get("inputs") or []))))
    return nprint


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__ or "jsonpog inventory",
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=DEFAULT_ROOT, help="jsonpog-integration root (default: CVMFS)")
    ap.add_argument("--pog", nargs="+", default=DEFAULT_POGS, help="POG directories (default: %(default)s)")
    ap.add_argument("--era-regex", default=DEFAULT_ERA_REGEX,
                    help="era subdirectories to read (regex on the directory name; default %(default)r)")
    ap.add_argument("--file", nargs="+", default=[],
                    help="read only these files (relative to --root or absolute); skips the directory walk")
    ap.add_argument("--name-regex", default="", help="print only corrections whose name matches")
    ap.add_argument("--max-detail", type=int, default=200,
                    help="files with more corrections than this get names only (default %(default)s)")
    ap.add_argument("--full", action="store_true", help="detail for every correction regardless of --max-detail")
    ap.add_argument("--max-keys", type=int, default=60, help="keys printed per input (default %(default)s)")
    ap.add_argument("--desc-len", type=int, default=160, help="description characters per correction")
    args = ap.parse_args(argv)

    lines = []

    def out(s: str) -> None:
        lines.append(s)
        print(s)
        sys.stdout.flush()

    if args.max_detail < 0 or args.max_keys < 1:
        print("jsonpog_inventory: --max-detail must be >= 0 and --max-keys >= 1", file=sys.stderr)
        return 2
    try:
        re.compile(args.era_regex)
        if args.name_regex:
            re.compile(args.name_regex)
    except re.error as e:
        print("jsonpog_inventory: bad regex: %s" % e, file=sys.stderr)
        return 2
    if not os.path.isdir(args.root):
        print("jsonpog_inventory: root %s is not a directory (CVMFS mounted?)" % args.root, file=sys.stderr)
        return 2

    out("INV|root=%s|time=%s|python=%s|pog=%s|era_regex=%s|name_regex=%s|max_detail=%d|full=%s" % (
        args.root, datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        sys.version.split()[0], ",".join(args.pog), args.era_regex, args.name_regex or "-",
        args.max_detail, args.full))
    errs = []
    nfiles = ncorr = 0
    if args.file:
        for f in args.file:
            p = f if os.path.isabs(f) else os.path.join(args.root, f)
            rel = os.path.relpath(p, args.root)
            parts = rel.split(os.sep)
            tag = "|".join(parts[1:3] + [os.sep.join(parts[3:])]) if len(parts) >= 4 and parts[0] == "POG" \
                else "-|-|" + rel
            if not os.path.isfile(p):
                out("ERR|%s|no such file" % tag)
                errs.append(p)
                continue
            nfiles += 1
            ncorr += describe_file(p, tag, args, out, errs)
    else:
        era_re = re.compile(args.era_regex)
        for pog in args.pog:
            d = os.path.join(args.root, "POG", pog)
            if not os.path.isdir(d):
                out("ERR|%s|-|-|no directory %s" % (pog, d))
                errs.append(d)
                continue
            eras = sorted(e for e in os.listdir(d) if os.path.isdir(os.path.join(d, e)))
            out("POGDIR|%s|eras=%s" % (pog, ",".join(eras)))
            for era in eras:
                if not era_re.search(era):
                    continue
                ed = os.path.join(d, era)
                files = sorted(f for f in os.listdir(ed)
                               if f.endswith(".json") or f.endswith(".json.gz"))
                others = sorted(f for f in os.listdir(ed) if f not in files)
                out("ERADIR|%s|%s|files=%d|other=%s" % (pog, era, len(files), ",".join(others) or "-"))
                for f in files:
                    nfiles += 1
                    ncorr += describe_file(os.path.join(ed, f), "%s|%s|%s" % (pog, era, f), args, out, errs)
    out("SUMMARY|files=%d|corrections_printed=%d|errors=%d" % (nfiles, ncorr, len(errs)))
    return 3 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
