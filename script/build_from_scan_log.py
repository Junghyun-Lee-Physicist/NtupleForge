#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_from_scan_log.py -- turn a das_scan.sh log into REVIEWABLE artifacts.

Generalization of script/build_ul18_from_log.py (2026-07-26), which was
hardwired to UL18 x NanoAODv9 (era string, lumi, Run2018[A-D] regex, the
"JetHT/SingleMuon" PD tuple, and a hand-written `groups` list that KeyErrors on
any sample a year does not have).

Created 2026-08-17 for the v9 || v15 parallel campaign.
2026-09-16: Run 3 Data variants kept as separate rows (--data-variants, default
'auto' = all for Run 3 eras); Data flavour re-productions (BTVNano, JMENano)
excluded and listed; canonical match tolerates the v15 Data string without
'_MiniAODv2_'. 2026-09-17: in canonical (Run 2) mode a '<RunEra>-<proc>_vN-vM'
variant becomes its own row '<PD>_<RunEra>_vN' (UL16 v15 Run2016B ver1/ver2);
RESULT mode PINNED (registry PRIMARY = full dataset path) bypasses DEFAULT_EXCLUDE. Tested on das_ttHH_2024/2025_v15_20260916_*.log and on
das_ttHH_2018UL_v15_20260903_1016.log (review tables only; config emission
dry-run on a NOT_FOUND-free copy of the 2024 log).

DESIGN POINT -- this tool's FIRST output is a review table, not a config.
The workflow is: scan on lxplus -> read the table with a human -> then emit the
config. A generator that silently drops or invents a dataset is worse than no
generator, so every ambiguity is reported rather than resolved.

------------------------------------------------------------------------------
USAGE

    # 1. always start here: human-readable table + machine TSV
    python3 script/build_from_scan_log.py script/das/das_ttHH_2018UL_v15_<stamp>.log

    # 2. once the table looks right, emit the NtupleForge config
    python3 script/build_from_scan_log.py <log> --emit-config \
        --job-tag ttHH2018UL_v15_fullNano_v1 \
        --branch-file branches/branch_keep_all.txt

    # 2b. v15 per-tier lists: one _MC and one _Data draft (CPV convention),
    #     '{tier}' in --job-tag becomes MC / Data. --allow-notfound lets a config
    #     out while KNOWN-absent samples are still NOT_FOUND (written as a
    #     commented block); any other NOT_FOUND still refuses.
    python3 script/build_from_scan_log.py <log> --emit-config \
        --registry script/samples_registry_run3.txt \
        --job-tag ttHH2024_v15_had_{tier}_v1 \
        --branch-file branches/branch_hadronic_2024_v15_MC.txt \
        --data-branch-file branches/branch_hadronic_2024_v15_Data.txt

    # 3. optional side artifacts
    python3 script/build_from_scan_log.py <log> --emit-xsec-json \
        --xsec-ref ../tempTTHH/data/samples_2017UL.json
    python3 script/build_from_scan_log.py <log> --emit-gencat-snippet
    python3 script/build_from_scan_log.py <log> --emit-topcpv-datasets

    # 4. THE POINT OF THE WHOLE EXERCISE: diff two scans
    python3 script/build_from_scan_log.py script/das/das_ttHH_2018UL_v9_<s>.log \
        --compare script/das/das_ttHH_2018UL_v15_<s>.log

OUTPUTS land in script/drafts/ (review tables, config drafts; 2026-09-22 layout) unless --outdir is given. Nothing is written to
crabConfig/ automatically -- the emitted config gets a .draft suffix and you
copy it in after review. That is deliberate: an auto-overwritten config is how
config_CPV2017UL_MC.yaml lost 60 datasets on 2026-07-26.

------------------------------------------------------------------------------
EXIT CODES
    0  ok
    2  bad arguments / unreadable log
    3  the log is internally inconsistent (NOT_FOUND rows, duplicate keys,
       missing META) -- the review table IS still written; the config is not
    4  --emit-xsec-json asked for but a sample has no cross-section reference
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import OrderedDict

# Campaign substrings that mark a non-standard reprocessing. Substring match
# against the campaign (processed-string) field of MC datasets. FSUL covers
# FSUL16/17/18 (fast sim). The Run 3 tokens (2026-09-16, ttHH/03_run3_plan.md
# section 6 item 2a) are a second safety net: das_scan.sh already anchors the
# MC query on the GT, so flavour campaigns such as
# RunIII2024Summer24NanoAODv15-JMENanoV15_150X..., -BTVNanoV15_, -FS_, -NoPU_,
# -FlatPU0to120_, -EpsilonPU_, -EGMNanoV15_, -MUOPOGNano_, -mg35x_ normally
# never reach this script.
DEFAULT_EXCLUDE = ("JMENano", "PUFor", "PU35For", "FSUL", "BPH_",
                   "BTVNano", "-FS_", "NoPU", "FlatPU", "EpsilonPU", "EGMNano",
                   "MUOPOG", "mg35x", "_pilot")

# Run 3 eras (das_scan.sh era tokens). For these, Data processing variants of
# one run era are DISJOINT run ranges, not re-processings of the same runs:
# Run2024I-MINIv6NANOv15-v2 and Run2024I-MINIv6NANOv15_v2-v1 are both needed,
# and so are Run2025C-PromptReco-v1 and -v2 (T0 prompt, split by run). The
# Run 2 rule "canonical = highest -vN, rest = alternates" would silently drop
# runs here (seen on the 2026-09-16 logs: 155M events of Run2025C demoted to
# an alternate). See _split_data_variants() and --data-variants.
RUN3_ERAS = ("2022", "2022EE", "2023", "2023BPix", "2024", "2025")

# Data flavour re-productions (POG-specific NanoAOD content) that the relaxed
# das_scan.sh data query pulls in next to the standard one: for v15 the query
# 'Run2018A-UL2018*NanoAODv15*' returns UL2018_BTVNanoAODv15-v1,
# UL2018_JMENanoAODv15-v2 AND UL2018_NanoAODv15-v2. Before 2026-09-16 the first
# of them (alphabetical) became the canonical row when the META data_proc still
# carried the v9-style 'UL2018_MiniAODv2_NanoAODv15' (no exact match). They are
# excluded here and listed in the review table, never used.
DATA_EXCLUDE = ("BTVNano", "JMENano")


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def parse_log(path, data_proc_override=None, data_variants="auto"):
    """Return (meta, mc, data, files, notfound, dup).

    meta      dict from the META| line ({} if absent -- old logs have none)
    mc        OrderedDict outkey -> (dataset, nevents, nfiles, size_TB)
    data      OrderedDict "<PD>_<RunEra>" -> {"plain": tuple, "alt": [tuple,...]}
              (data_variants "all", or "auto" on a Run 3 era: one row per DBS
              processing variant, keyed "<PD>_<processed string>", no alternates)
    files     dict key -> lfn   (from --sample-file scans)
    notfound  list of keys whose RESULT| line said NOT_FOUND
    dup       list of (outkey, dataset) that collided with an existing key
    """
    meta, files, notfound, dup = {}, {}, [], []
    mc, data_raw = OrderedDict(), OrderedDict()

    # Keys whose registry PRIMARY is a pinned full dataset path (das_scan.sh
    # RESULT mode PINNED, 2026-09-17): their DS line may sit in a flavour
    # sub-campaign on purpose, so DEFAULT_EXCLUDE must not drop it. RESULT
    # comes after the DS line in the log, hence this pre-pass.
    pinned = set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("RESULT|"):
                parts = line.rstrip("\n").split("|")
                if len(parts) >= 3 and parts[2] == "PINNED":
                    pinned.add(parts[1])
    if pinned:
        meta["_pinned"] = sorted(pinned)

    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")

            if line.startswith("META|"):
                for tok in line.split("|")[1:]:
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        meta[k] = v
                continue

            if line.startswith("RESULT|"):
                parts = line.split("|")
                if len(parts) >= 3 and parts[2] == "NOT_FOUND":
                    notfound.append(parts[1])
                continue

            if line.startswith("FILE|"):
                parts = line.split("|")
                if len(parts) >= 4:
                    files.setdefault(parts[1], parts[3])
                continue

            if not line.startswith("DS|"):
                continue

            parts = line.split("|")
            if len(parts) < 6:
                continue
            _, key, ds, nev_s, nf_s, sz_s = parts[:6]
            nev = _intfield(nev_s)
            nf = _intfield(nf_s)
            sz = sz_s.split("=", 1)[1] if "=" in sz_s else "NA"

            fields = ds.split("/")
            if len(fields) < 4:
                continue
            camp, tier = fields[2], fields[3]

            if tier.endswith("SIM"):                      # NANOAODSIM -> MC
                if key not in pinned and any(x in camp for x in DEFAULT_EXCLUDE):
                    continue
                m = re.search(r"_(ext\d+)", camp)
                outkey = "%s_%s" % (key, m.group(1)) if m else key
                if outkey in mc:
                    dup.append((outkey, ds))
                    continue
                mc[outkey] = (ds, nev, nf, sz)
            else:                                          # NANOAOD -> Data
                pd = fields[1]
                if any(x in camp for x in DATA_EXCLUDE):
                    meta.setdefault("_data_excluded", []).append(ds)
                    continue
                m = re.match(r"(Run\d{4}[A-Z]?)", camp)
                era = m.group(1) if m else camp.split("-")[0]
                outkey = "%s_%s" % (pd, era)
                data_raw.setdefault(outkey, []).append((ds, nev, nf, sz, camp))

    proc = data_proc_override or meta.get("data_proc", "")
    if data_proc_override:
        meta.setdefault("data_proc", data_proc_override)
    if data_variants == "auto":
        data_variants = "all" if meta.get("era", "") in RUN3_ERAS else "canonical"
    meta["data_variants"] = data_variants
    data = _split_data_variants(data_raw, proc, keep_all=(data_variants == "all"))
    return meta, mc, data, files, notfound, dup


def _intfield(tok):
    """'nevents=123' -> 123 ; anything unparseable -> None (never crash)."""
    try:
        return int(tok.split("=", 1)[1])
    except (IndexError, ValueError):
        return None


def _split_data_variants(data_raw, data_proc, keep_all=False):
    """Pick the canonical dataset per (PD, RunEra); the rest become alternates.

    Canonical = the one whose campaign is exactly '<RunEra>-<data_proc>-vN'
    (no extra token such as _GT36 between the processing string and -vN),
    highest N. This replaces the UL18-specific `"_GT36" in camp` test and works
    for any era/version without a code change.

    keep_all=True (Run 3, or --data-variants all): every variant is its own row,
    keyed '<PD>_<processed string>' (e.g. JetMET0_Run2024I-MINIv6NANOv15_v2-v1),
    and nothing is demoted to an alternate. Sorted by processed string so the
    output is deterministic.
    """
    out = OrderedDict()
    if keep_all:
        for key, variants in data_raw.items():
            pd = key.split("_", 1)[0]
            for tup in sorted(variants, key=lambda t: t[4]):
                out["%s_%s" % (pd, tup[4])] = {"plain": tup, "alt": []}
        return out
    # Accepted processing strings: the META one, and (v15 Data drops the
    # '_MiniAODv2_' token: Run2018A-UL2018_NanoAODv15-v2) the same string with
    # that token removed, so a v9-style META data_proc still finds the canonical
    # v15 row instead of falling back to the alphabetically first dataset.
    procs = [data_proc] if data_proc else []
    if data_proc and "_MiniAODv2_" in data_proc:
        procs.append(data_proc.replace("_MiniAODv2_", "_"))
    proc_re = "|".join(re.escape(x) for x in procs)
    for key, variants in data_raw.items():
        # '<RunEra>-<proc>_vN-vM' is a SEPARATE run range, not a re-processing
        # of the same runs: UL16 v15 JetHT has Run2016B-HIPM_UL2016_NanoAODv15-v1
        # (= v9 ver1, runs 272760-273017) and ..._NanoAODv15_v2-v1 (= ver2, runs
        # 273150-275376; measured 2026-09-17). Demoting the '_v2' one to an
        # alternate would silently drop 133.8M events, so it gets its own row,
        # keyed '<PD>_<RunEra>_vN'. Only the plain '-vM' forms compete for the
        # canonical slot below.
        extra_rows = []
        competing = []
        for tup in variants:
            m2 = re.match(r"^Run\d{4}[A-Z]?-(?:" + proc_re + r")_v(\d+)-v\d+$", tup[4]) \
                if proc_re else None
            if m2:
                extra_rows.append(("%s_v%s" % (key, m2.group(1)), tup))
            else:
                competing.append(tup)
        plain, alts = None, []
        best_v = -1
        for tup in competing:
            camp = tup[4]
            m = re.match(r"^Run\d{4}[A-Z]?-(?:" + proc_re + r")-v(\d+)$", camp) \
                if proc_re else None
            if m and int(m.group(1)) > best_v:
                if plain is not None:
                    alts.append(plain)
                plain, best_v = tup, int(m.group(1))
            else:
                alts.append(tup)
        if plain is None and competing:      # no exact match -- do not guess
            variants_sorted = sorted(competing, key=lambda t: t[4])
            plain, alts = variants_sorted[0], variants_sorted[1:]
        if plain is not None:
            out[key] = {"plain": plain, "alt": alts}
        for k2, tup in sorted(extra_rows, key=lambda x: x[0]):
            out[k2] = {"plain": tup, "alt": []}
    return out


# ---------------------------------------------------------------------------
# artifacts
# ---------------------------------------------------------------------------

def provenance(path, meta):
    """Honest provenance: real log name + sha256, never a frozen literal.

    build_ul18_from_log.py stamped the string
    'NtupleForge/script/das_ul18_scan_20260726_1657.log' into every output
    regardless of which log was actually read -- re-running against a new log
    produced files that claimed the old one.
    """
    h = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
    return OrderedDict([
        ("source_log", os.path.basename(path)),
        ("source_log_sha256_16", h),
        ("era", meta.get("era", "UNKNOWN")),
        ("nano_version", meta.get("nano", "UNKNOWN")),
        ("mc_campaign_prefix", meta.get("mc_campaign", "UNKNOWN")),
        ("data_processing_prefix", meta.get("data_proc", "UNKNOWN")),
        ("scan_utc", meta.get("utc", "UNKNOWN")),
    ])


def write_table(out_md, out_tsv, meta, mc, data, files, notfound, dup, prov):
    era = meta.get("era", "?")
    ver = meta.get("nano", "?")
    L = ["# DAS scan review -- era=%s nano=%s" % (era, ver), ""]
    for k, v in prov.items():
        L.append("- **%s**: `%s`" % (k, v))
    L += ["",
          "MC keys: **%d**  |  Data keys: **%d**  |  NOT_FOUND: **%d**  |  duplicate-key collisions: **%d**"
          % (len(mc), len(data), len(notfound), len(dup)),
          ""]

    if notfound:
        L += ["## NOT_FOUND (registry expects these for this era, DAS has none)",
              "", "These block config emission. Either the sample really does not exist for",
              "this era/version -- then narrow the ERAS column in samples_registry.txt and",
              "record why -- or the campaign prefix in the das_scan.sh era table is wrong.",
              ""]
        L += ["- `%s`" % k for k in notfound] + [""]

    if dup:
        L += ["## DUPLICATE KEY COLLISIONS", "",
              "Two DAS datasets collapsed onto one key. Decide which one to keep, or add",
              "an ext-style suffix. The second one was DROPPED from the tables below.", ""]
        L += ["- `%s`  <-  `%s`" % (k, d) for k, d in dup] + [""]

    tot_ev = sum(v[1] for v in mc.values() if v[1])
    tot_f = sum(v[2] for v in mc.values() if v[2])
    tot_tb = sum(float(v[3]) for v in mc.values() if v[3] not in ("NA", ""))

    L += ["## MC (%d)" % len(mc), ""]
    if meta.get("_pinned"):
        L += ["NOTE: PINNED (registry PRIMARY is a full dataset path; flavour exclusion skipped): "
              + ", ".join("`%s`" % k for k in meta["_pinned"]), ""]
    L += ["| key | nevents | nfiles | TB | dataset |",
          "|---|---:|---:|---:|---|"]
    for k, (ds, nev, nf, sz) in mc.items():
        L.append("| `%s` | %s | %s | %s | `%s` |" %
                 (k, _fmt(nev), _fmt(nf), sz, ds))
    L += ["| **total** | **%s** | **%s** | **%.2f** | |" % (_fmt(tot_ev), _fmt(tot_f), tot_tb), ""]

    d_ev = sum(v["plain"][1] for v in data.values() if v["plain"][1])
    d_f = sum(v["plain"][2] for v in data.values() if v["plain"][2])
    L += ["## Data (%d)" % len(data), ""]
    if meta.get("_data_excluded"):
        L += ["NOTE: %d flavour re-production dataset(s) (%s) were EXCLUDED from the rows below:"
              % (len(meta["_data_excluded"]), ", ".join(DATA_EXCLUDE))]
        L += ["- `%s`" % d for d in meta["_data_excluded"]] + [""]
    if meta.get("data_variants") == "all":
        L += ["NOTE: data_variants=all (Run 3 default). Every DBS processing variant of a run era is",
              "its own row, keyed `<PD>_<processed string>`, because in Run 3 the variants are",
              "disjoint run ranges (e.g. `Run2024I-MINIv6NANOv15-v2` + `Run2024I-MINIv6NANOv15_v2-v1`,",
              "`Run2025C-PromptReco-v1` + `-v2`). Nothing is demoted to an alternate. Use",
              "`--data-variants canonical` to get the Run 2 behaviour.", ""]
    L += [
          "| key | nevents | nfiles | TB | dataset | alternates |",
          "|---|---:|---:|---:|---|---|"]
    for k, v in data.items():
        ds, nev, nf, sz, _ = v["plain"]
        alt = "<br>".join("`%s`" % a[0] for a in v["alt"]) or "-"
        L.append("| `%s` | %s | %s | %s | `%s` | %s |" % (k, _fmt(nev), _fmt(nf), sz, ds, alt))
    L += ["| **total** | **%s** | **%s** | | | |" % (_fmt(d_ev), _fmt(d_f)), ""]

    # CRAB 10,000-jobs-per-task guard. The submitter does not compute this yet
    # (NtupleForge docs/01_STATUS.md, "OPEN gap"), and we already have nfiles.
    over = [(k, v[2]) for k, v in mc.items() if v[2] and v[2] > 9000]
    over += [(k, v["plain"][2]) for k, v in data.items() if v["plain"][2] and v["plain"][2] > 9000]
    L += ["## CRAB job-count guard (units_per_job = 1)", ""]
    if over:
        L += ["**WARNING** -- these datasets are within 10% of, or above, the hard",
              "server-side limit of 10,000 jobs per task. Above it `crab submit` reports",
              "SUCCESS and the task silently sits at SUBMITREFUSED with an all-zero",
              "--report, and --resubmit cannot rescue it (D-2026-07-27-crab-job-limit,",
              "and it actually happened to TTbar_SemiLep in the sibling repo on",
              "2026-07-27 at 10,010 jobs). Raise units_per_job for these.", ""]
        L += ["- `%s`: %s files -> %s jobs" % (k, _fmt(n), _fmt(n)) for k, n in over]
    else:
        L += ["OK -- largest dataset is %s files (< 10,000 jobs at units_per_job=1)." %
              _fmt(max([v[2] for v in mc.values() if v[2]] +
                       [v["plain"][2] for v in data.values() if v["plain"][2]] or [0]))]
    L.append("")

    if files:
        L += ["## Example file per dataset (--sample-file)", "",
              "Feed these to `script/dump_branch_inventory.py` to get the branch schema.", ""]
        L += ["- `%s`: `%s`" % (k, v) for k, v in files.items()] + [""]

    _write(out_md, "\n".join(L) + "\n")

    T = ["type\tkey\tnevents\tnfiles\tsize_TB\tdataset"]
    for k, (ds, nev, nf, sz) in mc.items():
        T.append("MC\t%s\t%s\t%s\t%s\t%s" % (k, nev, nf, sz, ds))
    for k, v in data.items():
        ds, nev, nf, sz, _ = v["plain"]
        T.append("DATA\t%s\t%s\t%s\t%s\t%s" % (k, nev, nf, sz, ds))
    _write(out_tsv, "\n".join(T) + "\n")


def _fmt(n):
    return "{:,}".format(n) if isinstance(n, int) else "NA"


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("[build] wrote %s" % path)


def read_registry(path):
    """key -> group, preserving registry order (for config grouping)."""
    order, group = [], {}
    if not path or not os.path.isfile(path):
        return order, group
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            f = line.split()
            if len(f) < 5:
                continue
            order.append(f[1])
            group[f[1]] = f[4]
    return order, group


def tier_tag(job_tag, tier):
    """Job tag for one tier. '{tier}' in --job-tag is replaced (MC / Data);
    without a placeholder the tier is appended, so the two drafts never share
    a jobID / output_base."""
    if "{tier}" in job_tag:
        return job_tag.replace("{tier}", tier)
    return "%s_%s" % (job_tag, tier)


def emit_config(path, meta, mc, data, prov, args, reg_order, reg_group, tier=None):
    """Emit a draft crabConfig YAML by string concatenation (no PyYAML).

    Grouping is driven by samples_registry.txt, so a sample that a year does not
    have simply does not appear -- unlike build_ul18_from_log.py's hand-written
    `groups` list, which raised KeyError.

    tier: None  -> one config with MC and Data (v9 habit, branch_keep_all.txt);
          "MC"  -> MC datasets only, branch_file = --branch-file;
          "Data"-> Data datasets only, branch_file = --data-branch-file.
    2026-09-19: v15 MC and Data branch lists differ (prefiring weights, gen
    branches, era HLT sets), and submit_crab.py has ONE common.branch_file, so
    the CPV convention (config_<...>_MC.yaml + config_<...>_Data.yaml) is the
    only way to give each tier its list. --data-branch-file switches this on.
    """
    era, ver = meta.get("era", "ERA"), meta.get("nano", "VER")
    tag = args.job_tag or ("ttHH%s_%s_v1" % (era, ver))
    branch_file = args.branch_file
    if tier == "MC":
        data = OrderedDict()
        tag = tier_tag(tag, "MC")
    elif tier == "Data":
        mc = OrderedDict()
        tag = tier_tag(tag, "Data")
        branch_file = args.data_branch_file
    tier_note = "  [%s only]" % tier if tier else ""

    L = ["# " + "=" * 74,
         "# ttHH -> 4b  |  era %s  |  NanoAOD %s   -- GENERATED DRAFT%s" % (era, ver, tier_note),
         "# " + "=" * 74,
         "# Generated by script/build_from_scan_log.py from:",
         "#   %s  (sha256[:16] %s, scanned %s)" %
         (prov["source_log"], prov["source_log_sha256_16"], prov["scan_utc"]),
         "# MC campaign prefix   : %s*" % prov["mc_campaign_prefix"],
         "# Data processing prefix: %s*" % prov["data_processing_prefix"],
         "#",
         "# Regeneration is idempotent: the same log gives a byte-identical file",
         "# (no timestamp is written). Review this draft, then copy it over the real",
         "# crabConfig/ file yourself -- this tool never overwrites one.",
         "#",
         "# !! CRAB REFUSES ANY TASK WITH MORE THAN 10,000 JOBS, server-side, AFTER",
         "# !! `crab submit` has already reported SUCCESS. The task then sits at",
         "# !! SUBMITREFUSED forever with an all-zero --report row and --resubmit",
         "# !! cannot rescue it -- the dataset silently produces nothing.",
         "# !! njobs = ceil(nfiles / units_per_job). Check the review table's",
         "# !! 'CRAB job-count guard' section before lowering units_per_job.",
         "# " + "=" * 74]
    if tier is None and mc and data:
        L += ["# !! MC and Data share common.branch_file below. Fine for",
              "# !! branch_keep_all.txt; NOT for the v15 per-tier lists (MC has",
              "# !! L1PreFiringWeight/gen branches, Data has era HLT sets). Re-run with",
              "# !! --data-branch-file to get one _MC and one _Data draft.",
              "# " + "=" * 74]
    L += ["",
         "common:",
         # jobID = CRAB workArea directory (created in the repo root); the 'campaign_' prefix
         # is what .gitignore excludes (v9 convention: campaign_ttHH2018UL_fullNano_v1).
         # output_base = /store/user/<user>/<output_base> keeps the bare tag.
         '  jobID: "campaign_%s"' % tag,
         '  site: "%s"' % args.site,
         '  output_base: "%s"' % tag,
         '  analysis_module: ["%s", "MODULES"]' % args.module,
         '  branch_file: "%s"' % branch_file,
         '  splitting: "FileBased"',
         "  units_per_job: %d" % args.units_per_job,
         "",
         "datasets:"]

    # MC, grouped in registry order; ext keys follow their base key.
    listed, groups_seen = set(), []
    by_group = OrderedDict()
    for base in reg_order:
        g = reg_group.get(base, "misc")
        for k in mc:
            if k == base or re.match(re.escape(base) + r"_ext\d+$", k):
                by_group.setdefault(g, []).append(k)
                listed.add(k)
    leftover = [k for k in mc if k not in listed]
    if leftover:
        by_group.setdefault("UNGROUPED", []).extend(leftover)

    for g, keys in by_group.items():
        L.append("  # --- %s ---" % g)
        for k in keys:
            L.append('  %s: "%s"' % (k, mc[k][0]))
        L.append("")
        groups_seen.append(g)

    pds = []
    for k in data:
        pd = k.rsplit("_Run", 1)[0]
        if pd not in pds:
            pds.append(pd)
    for pd in pds:
        L.append("  # --- Data (%s) --- canonical processing; alternates commented" % pd)
        for k, v in data.items():
            if not k.startswith(pd + "_Run"):
                continue
            L.append('  %s: "%s"' % (k, v["plain"][0]))
            for a in v["alt"]:
                L.append('  # %s: "%s"   # alternate processing -- OPEN, confirm against the AN' % (k, a[0]))
        L.append("")

    if leftover:
        L += ["  # !! UNGROUPED keys above are not in samples_registry.txt.",
              "  # !! Add them to the registry (or explain why not) before submitting."]
    allowed_nf = getattr(args, "_allowed_notfound", []) or []
    if allowed_nf and tier != "Data":
        L += ["  # --- NOT in this campaign yet (NOT_FOUND in the scan, allowed by --allow-notfound) ---",
              "  # --- add them in a later config when the central request or the enriched production lands ---"]
        L += ["  # %s: NOT_FOUND" % k for k in allowed_nf]
        L.append("")

    _write(path, "\n".join(L) + "\n")
    if leftover:
        print("[build] WARNING: %d key(s) not in the registry: %s" % (len(leftover), leftover))


def emit_xsec_json(path, meta, mc, data, prov, ref_path):
    """samples_<ERA>_<VER>.json for tempTTHH: xsec/BR copied from a reference
    year's DB, nevents/nfiles/das_path taken from this scan."""
    if not os.path.isfile(ref_path):
        sys.exit("FATAL: --xsec-ref '%s' not readable" % ref_path)
    ref = json.load(open(ref_path, encoding="utf-8"))
    out = OrderedDict()
    out["_meta"] = OrderedDict(prov)
    out["_meta"]["note"] = (
        "xsec/BR/kfactor copied from %s (13 TeV values are year-independent); "
        "das_path/nevents/nfiles from this scan; frac_neg_weight must be "
        "recomputed from this era's prescan." % os.path.basename(ref_path))
    out["_meta"]["lumi_fb_inv"] = None
    out["_meta"]["lumi_ref"] = "OPEN -- set from the LUM POG recommendation for this era, and re-run brilcalc on this analysis' certified JSON."

    missing = []
    for k, (ds, nev, nf, _sz) in mc.items():
        refkey = k if k in ref else re.sub(r"_ext\d+$", "", k)
        if refkey not in ref:
            missing.append(k)
            continue
        e = dict(ref[refkey])
        e["das_path"], e["nevents"], e["nfiles"] = ds, nev, nf
        e["frac_neg_weight"] = None
        out[k] = e
    for k, v in data.items():
        ds, nev, nf, _sz, _c = v["plain"]
        e = OrderedDict([("das_path", ds), ("is_data", True),
                         ("cross_section_fb", None), ("br", None), ("kfactor", None),
                         ("nevents", nev), ("nfiles", nf)])
        if v["alt"]:
            e["alt_das_paths"] = [a[0] for a in v["alt"]]
        out[k] = e

    if missing:
        print("FATAL: no cross-section reference in %s for: %s" %
              (os.path.basename(ref_path), missing), file=sys.stderr)
        print("       A new sample must not silently get a null cross section.", file=sys.stderr)
        return 4
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    print("[build] wrote %s" % path)
    return 0


STITCH_KEYS = ("TTbar_SemiLep", "TTbar_Hadronic", "TTbar_DiLep",
               "TTbb_SemiLep", "TTbb_Hadronic", "TTbb_DiLep", "TT4b")


def emit_gencat_snippet(path, meta, mc, prov):
    """nano_child: lines for TTHHGenCategoryTools/TtbarIdExtender/crab/datasets.yaml.

    Only the 7 stitching samples. Note this is the NANO side only -- the CRAB
    production input there is MiniAODv2 and is NanoAOD-version-independent, so
    changing the NanoAOD version does NOT require re-running the extender.
    """
    L = ["# nano_child paths for era=%s NanoAOD=%s" % (meta.get("era"), meta.get("nano")),
         "# source: %s (sha256[:16] %s)" % (prov["source_log"], prov["source_log_sha256_16"]),
         "#",
         "# Paste into TtbarIdExtender/crab/datasets.yaml. If you are keeping BOTH",
         "# v9 and v15 around, do NOT overwrite the existing nano_child -- turn it",
         "# into a per-version mapping, e.g.",
         "#     nano_children: { v9: \"...\", v15: \"...\" }",
         "# and give the two a separate `verified` flag each. The MiniAOD `dataset:`",
         "# field is unaffected by the NanoAOD version.",
         "#",
         "# REMINDER: these are the only 7 samples the ttbar-ID extension needs.",
         "# The patch files (ttnb_<KEY>.root) are a function of the YEAR ALONE --",
         "# 7 per year, not 14. The NanoAOD version only changes which events the",
         "# validation match covers, not the patch content.",
         ""]
    for k in STITCH_KEYS:
        if k in mc:
            L.append('      # %s' % k)
            L.append('      nano_child: "%s"' % mc[k][0])
        else:
            L.append('      # %s : NOT IN THIS SCAN' % k)
    _write(path, "\n".join(L) + "\n")


def emit_topcpv_datasets(path, meta, mc, data, prov, keys):
    """condor/datasets.txt rows for TopCPVGenCategorizer (label + DAS path)."""
    L = ["# datasets.txt rows -- era=%s NanoAOD=%s" % (meta.get("era"), meta.get("nano")),
         "# source: %s (sha256[:16] %s)" % (prov["source_log"], prov["source_log_sha256_16"]),
         "# Format: <short_name>  <DAS_dataset_path>",
         "#",
         "# The labels MUST stay 1:1 with the NtupleForge validation YAML keys --",
         "# filelists/, condor output dirs and the validation bookkeeping match by",
         "# name on both sides.",
         ""]
    want = [k.strip() for k in keys.split(",")] if keys else list(mc)
    miss = [k for k in want if k not in mc]
    w = max([len(k) for k in want] or [10])
    for k in want:
        if k in mc:
            L.append("%-*s  %s" % (w, k, mc[k][0]))
    if miss:
        L += ["", "# NOT IN THIS SCAN (fix --topcpv-keys or the registry):"] + \
             ["#   %s" % k for k in miss]
    _write(path, "\n".join(L) + "\n")


def compare(log_a, log_b, data_proc, out_md):
    """Per-key diff of two scans. This is the v9 <-> v15 (or 2017 <-> 2018) tool."""
    ma, mca, da, _fa, _na, _pa = parse_log(log_a, data_proc)
    mb, mcb, db, _fb, _nb, _pb = parse_log(log_b, data_proc)
    la = "%s/%s" % (ma.get("era", "?"), ma.get("nano", "?"))
    lb = "%s/%s" % (mb.get("era", "?"), mb.get("nano", "?"))

    L = ["# Scan comparison: **A = %s** vs **B = %s**" % (la, lb), "",
         "- A: `%s`" % os.path.basename(log_a),
         "- B: `%s`" % os.path.basename(log_b), "",
         "A key present in only one side means the sample was renamed, dropped, or",
         "not yet produced for that campaign. A **nevents** difference between two",
         "NanoAOD versions of the SAME MiniAOD parent is a red flag -- it means the",
         "two are not the same event population and any v9<->v15 comparison built on",
         "them is not apples-to-apples.", ""]

    flat_a = {k: v[:3] for k, v in mca.items()}
    flat_a.update({k: v["plain"][:3] for k, v in da.items()})
    flat_b = {k: v[:3] for k, v in mcb.items()}
    flat_b.update({k: v["plain"][:3] for k, v in db.items()})

    only_a = [k for k in flat_a if k not in flat_b]
    only_b = [k for k in flat_b if k not in flat_a]
    both = [k for k in flat_a if k in flat_b]

    L += ["## Only in A (%d)" % len(only_a), ""] + \
         (["- `%s`" % k for k in only_a] or ["(none)"]) + [""]
    L += ["## Only in B (%d)" % len(only_b), ""] + \
         (["- `%s`" % k for k in only_b] or ["(none)"]) + [""]

    diff = [k for k in both if flat_a[k][1] != flat_b[k][1]]
    L += ["## nevents differs (%d of %d common keys)" % (len(diff), len(both)), "",
          "| key | A nevents | B nevents | delta | A nfiles | B nfiles |",
          "|---|---:|---:|---:|---:|---:|"]
    for k in diff:
        a, b = flat_a[k], flat_b[k]
        d = (b[1] - a[1]) if (isinstance(a[1], int) and isinstance(b[1], int)) else "NA"
        L.append("| `%s` | %s | %s | %s | %s | %s |" %
                 (k, _fmt(a[1]), _fmt(b[1]), _fmt(d) if isinstance(d, int) else d,
                  _fmt(a[2]), _fmt(b[2])))
    if not diff:
        L.append("| (none -- every common key has identical nevents) | | | | | |")
    L.append("")

    same = len(both) - len(diff)
    L += ["## Summary", "",
          "- common keys: **%d** (identical nevents: **%d**, differing: **%d**)" % (len(both), same, len(diff)),
          "- only in A: **%d**   only in B: **%d**" % (len(only_a), len(only_b)), ""]
    _write(out_md, "\n".join(L) + "\n")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Turn a das_scan.sh log into reviewable artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    ap.add_argument("log", help="das_scan.sh log file")
    ap.add_argument("--compare", metavar="LOG_B",
                    help="diff this log (A) against LOG_B and stop")
    ap.add_argument("--outdir", help="output directory (default: script/drafts/ next to this script)")
    ap.add_argument("--registry", help="samples_registry.txt (default: next to this script)")
    ap.add_argument("--emit-config", action="store_true", help="emit a draft crabConfig YAML")
    ap.add_argument("--emit-xsec-json", action="store_true", help="emit a tempTTHH samples_*.json")
    ap.add_argument("--emit-gencat-snippet", action="store_true",
                    help="emit nano_child lines for TTHHGenCategoryTools")
    ap.add_argument("--emit-topcpv-datasets", action="store_true",
                    help="emit condor/datasets.txt rows for TopCPVGenCategorizer")
    ap.add_argument("--topcpv-keys", help="comma-separated keys for --emit-topcpv-datasets")
    ap.add_argument("--xsec-ref", default="../tempTTHH/data/samples_2017UL.json",
                    help="reference xsec DB for --emit-xsec-json")
    ap.add_argument("--job-tag", help="jobID / output_base (default: ttHH<ERA>_<VER>_v1)")
    ap.add_argument("--site", default="T3_KR_KNU")
    ap.add_argument("--module", default="modules/noop.py")
    ap.add_argument("--branch-file", default="branches/branch_keep_all.txt")
    ap.add_argument("--allow-notfound", default=None, metavar="KEY,KEY,...",
                    help="registry keys that may be NOT_FOUND in this log without blocking "
                         "--emit-config (samples known to be absent from the campaign, e.g. the "
                         "five Run 2 v15 samples under central request). They are written into the "
                         "config as a commented block. Any OTHER NOT_FOUND still refuses (exit 3).")
    ap.add_argument("--data-branch-file", default=None,
                    help="branch list for the Data tier. When given, --emit-config writes TWO "
                         "drafts, config_<stem>_MC.yaml.draft (MC keys, --branch-file) and "
                         "config_<stem>_Data.yaml.draft (Data keys, this file); '{tier}' in "
                         "--job-tag becomes MC / Data (else _MC / _Data is appended).")
    ap.add_argument("--units-per-job", type=int, default=1)
    ap.add_argument("--data-proc", help="data processing prefix, e.g. "
                    "UL2018_MiniAODv2_NanoAODv9. Only needed for pre-2026-08-17 "
                    "logs that carry no META| line; it decides which Data "
                    "processing variant is canonical and which are alternates.")
    ap.add_argument("--data-variants", choices=("auto", "canonical", "all"), default="auto",
                    help="how Data processing variants of one run era are treated. "
                         "'canonical' (Run 2 rule): highest -vN is the row, the rest are "
                         "alternates. 'all': one row per variant, no alternates (Run 3: the "
                         "variants are disjoint run ranges). 'auto' (default): 'all' when the "
                         "META era is a Run 3 era (%s), else 'canonical'." % ", ".join(RUN3_ERAS))
    args = ap.parse_args()

    if not os.path.isfile(args.log):
        sys.exit("FATAL: cannot read log '%s'" % args.log)
    outdir = args.outdir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "drafts")
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.log))[0]

    if args.compare:
        if not os.path.isfile(args.compare):
            sys.exit("FATAL: cannot read --compare log '%s'" % args.compare)
        other = os.path.splitext(os.path.basename(args.compare))[0]
        compare(args.log, args.compare, args.data_proc,
                os.path.join(outdir, "compare_%s__vs__%s.md" % (stem, other)))
        return 0

    meta, mc, data, files, notfound, dup = parse_log(args.log, args.data_proc, args.data_variants)
    prov = provenance(args.log, meta)

    if not meta:
        print("[build] NOTE: no META| line -- this looks like a pre-2026-08-17 log. "
              "era/version fields will read UNKNOWN; pass --job-tag explicitly.")

    write_table(os.path.join(outdir, "review_%s.md" % stem),
                os.path.join(outdir, "review_%s.tsv" % stem),
                meta, mc, data, files, notfound, dup, prov)

    rc = 0
    allowed = set(k for k in (args.allow_notfound or "").split(",") if k)
    unexpected_nf = [k for k in notfound if k not in allowed]
    unused_allow = sorted(allowed - set(notfound))
    if unused_allow:
        print("[build] NOTE: --allow-notfound names keys that were FOUND (stale list?): %s"
              % ", ".join(unused_allow))
    if unexpected_nf or dup:
        print("FATAL: the log is inconsistent -- %d NOT_FOUND not covered by --allow-notfound (%s), "
              "%d duplicate-key collisions. Review table written; no config emitted."
              % (len(unexpected_nf), ", ".join(unexpected_nf) or "-", len(dup)), file=sys.stderr)
        rc = 3
    elif notfound:
        print("[build] NOTE: %d NOT_FOUND key(s) explicitly allowed (%s); they are listed as a "
              "commented block in the config, not as datasets." % (len(notfound), ", ".join(notfound)))
    args._allowed_notfound = [k for k in notfound if k in allowed]

    reg = args.registry or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "samples_registry.txt")
    reg_order, reg_group = read_registry(reg)

    if args.emit_config and rc == 0:
        if args.data_branch_file:
            emit_config(os.path.join(outdir, "config_%s_MC.yaml.draft" % stem),
                        meta, mc, data, prov, args, reg_order, reg_group, tier="MC")
            emit_config(os.path.join(outdir, "config_%s_Data.yaml.draft" % stem),
                        meta, mc, data, prov, args, reg_order, reg_group, tier="Data")
        else:
            emit_config(os.path.join(outdir, "config_%s.yaml.draft" % stem),
                        meta, mc, data, prov, args, reg_order, reg_group)
    if args.emit_xsec_json and rc == 0:
        rc = emit_xsec_json(os.path.join(outdir, "samples_%s.json.draft" % stem),
                            meta, mc, data, prov, args.xsec_ref) or rc
    if args.emit_gencat_snippet and rc == 0:
        emit_gencat_snippet(os.path.join(outdir, "gencat_nano_child_%s.yaml.snippet" % stem),
                            meta, mc, prov)
    if args.emit_topcpv_datasets and rc == 0:
        emit_topcpv_datasets(os.path.join(outdir, "topcpv_datasets_%s.txt" % stem),
                             meta, mc, data, prov, args.topcpv_keys)
    return rc


if __name__ == "__main__":
    sys.exit(main())
