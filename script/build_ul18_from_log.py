#!/usr/bin/env python3
"""Build UL18 campaign config + xsec DB from a das_ul18_scan.sh log.

Inputs : script/das_ul18_scan_<timestamp>.log  (DS| lines)
         crabConfig/config_ttHH2017UL.yaml     (key order / grouping reference)
         tempTTHH/data/samples_2017UL.json     (xsec/BR/refs — reused, 13 TeV)
Outputs: crabConfig/config_ttHH2018UL.yaml
         tempTTHH/data/samples_2018UL.json

Selection rules (D: 2026-07-26, user-confirmed):
 - MC: keep only the standard campaign RunIISummer20UL18NanoAODv9-106X_..._L1v1[_extN]-vN;
   drop special reprocessings (JMENano, PUFor*, PU35For*, FSUL18, BPH).
 - ext1/ext2 become separate keys "<base>_ext1/2" (UL17 convention). New in UL18: TTWW_ext1.
 - Data: non-GT36 chosen (consistency with UL17; JEC/JER re-applied from jsonpog anyway).
   GT36 twins are emitted as comments. OPEN: confirm official XPOG recommendation.
 - BTagCSV: no 2018 primary dataset exists (DAS NOT_FOUND) -> omitted; OPEN in docs.
 - frac_neg_weight: unknown for UL18 -> null (recompute at prescan).
 - _meta lumi 59.83 /fb: preliminary, OPEN (user will confirm from LUM twiki).
"""
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # NtupleForge/
# log path: 1st CLI arg, else the newest das_ul18_scan_*.log under script/ (any depth)
_argl = [a for a in sys.argv[1:] if not a.startswith("-")]
if _argl:
    LOG = Path(_argl[0])
else:
    _cands = sorted((ROOT / "script").rglob("das_ul18_scan_*.log"))
    if not _cands:
        sys.exit("FATAL: no das_ul18_scan_*.log found under script/ — pass one as argument")
    LOG = max(_cands, key=lambda p: p.stat().st_mtime)
JSON17 = ROOT.parent / "tempTTHH/data/samples_2017UL.json"
OUT_YAML = ROOT / "crabConfig/config_ttHH2018UL.yaml"
OUT_JSON = ROOT.parent / "tempTTHH/data/samples_2018UL.json"
OUT_YAML_PRESCAN = ROOT / "crabConfig/config_ttHH2018UL_prescan.yaml"

EXCLUDE = ("JMENano", "PUFor", "PU35For", "FSUL18", "BPH_")

def parse_log():
    mc, data = OrderedDict(), OrderedDict()
    for line in LOG.read_text().splitlines():
        if not line.startswith("DS|"):
            continue
        _, key, ds, nev, nf, _sz = line.split("|")
        nev, nf = int(nev.split("=")[1]), int(nf.split("=")[1])
        camp = ds.split("/")[2]
        if ds.endswith("NANOAODSIM"):
            if any(x in camp for x in EXCLUDE):
                continue
            m = re.search(r"_(ext\d)-v\d+$", camp)
            outkey = f"{key}_{m.group(1)}" if m else key
            if outkey in mc:
                sys.exit(f"FATAL: duplicate MC key {outkey} ({ds})")
            mc[outkey] = (ds, nev, nf)
        else:  # data
            pd = ds.split("/")[1]
            era = re.match(r"(Run2018[A-D])", ds.split("/")[2]).group(1)
            outkey = f"{pd}_{era}"
            gt36 = "_GT36" in camp
            data.setdefault(outkey, {})["gt36" if gt36 else "plain"] = (ds, nev, nf)
    return mc, data

def main():
    mc, data = parse_log()
    j17 = json.load(open(JSON17))

    # ---- samples_2018UL.json -------------------------------------------------
    out = OrderedDict()
    out["_meta"] = {
        "era": "2018UL",
        "campaign": "RunIISummer20UL18 NanoAODv9",
        "config": "campaign_ttHH2018UL_fullNano_v1",
        "lumi_fb_inv": 59.83,
        "lumi_ref": "OPEN (preliminary): LUM POG 2018UL standard value 59.83 /fb; "
                    "to be confirmed by user from CMS LumiRecommendationsRun2 / brilcalc.",
        "source_log": "NtupleForge/script/das_ul18_scan_20260726_1657.log",
        "note": "xsec/BR/kfactor/refs copied from samples_2017UL.json (same 13 TeV values); "
                "nevents/nfiles from DAS (UL18). frac_neg_weight=null until prescan. "
                "Data = non-GT36 (OPEN: confirm XPOG recommendation). BTagCSV PD does not exist in 2018.",
    }
    miss_ref = []
    for key, (ds, nev, nf) in mc.items():
        refkey = key if key in j17 else re.sub(r"_ext\d$", "", key)
        if refkey not in j17:
            miss_ref.append(key); continue
        e = dict(j17[refkey])          # copy xsec/BR/refs/notes
        e["das_path"], e["nevents"], e["nfiles"] = ds, nev, nf
        e["frac_neg_weight"] = None    # OPEN: recompute from UL18 prescan
        out[key] = e
    for key, variants in data.items():
        ds, nev, nf = variants["plain"]
        out[key] = {"das_path": ds, "is_data": True, "cross_section_fb": None,
                    "br": None, "kfactor": None, "nevents": nev, "nfiles": nf}
        if "gt36" in variants:
            out[key]["alt_gt36_das_path"] = variants["gt36"][0]
    if miss_ref:
        sys.exit(f"FATAL: no UL17 xsec reference for {miss_ref}")
    json.dump(out, open(OUT_JSON, "w"), indent=1, ensure_ascii=False)

    # ---- config_ttHH2018UL.yaml ---------------------------------------------
    L = []
    L.append("""# Campaign Configuration — ttHH 2018UL (full-NanoAOD passthrough)
# ===========================
# Generated by script/build_ul18_from_log.py from
# script/das_ul18_scan_20260726_1657.log (dasgoclient, lxplus 2026-07-26).
# Mirrors crabConfig/config_ttHH2017UL.yaml (key names = project-wide sample keys).
# 2018 specifics:
#  - Data eras A-D (2017 was B-F). Non-GT36 NanoAODv9 chosen for consistency with
#    UL17; the GT36 re-nano twins are listed as comments (OPEN: confirm XPOG rec.).
#  - BTagCSV primary dataset does NOT exist in 2018 — CONFIRMED by the broad
#    forensic queries of das_ul18_scan.sh v2 (2026-07-26): 0 hits for
#    /BTagCSV/Run2018*/* under ANY tier and ANY dataset status. It is not a
#    naming change: the Run2018A vs Run2017C PD inventory diff shows the 2018
#    PD consolidation dropped BTagCSV, HTMHT, FSQJet1/2, HighPt*, and merged
#    SingleElectron/SinglePhoton/DoubleEG -> EGamma. (BTagMu does exist in 2018
#    but is the BTV muon-tagged calibration PD, not the FH b-tag jet stream.)
#    => For 2018 the FH b-tag quad-jet HLT paths live in JetHT, so JetHT alone
#    covers the hadronic trigger menu. ANALYZER IMPACT (not this file): the
#    2017 orthogonality split (4J3T -> BTagCSV, 6J/HT -> JetHT with veto,
#    ttHHanalyzer_unified.cc ~L295-360) collapses to a JetHT-only OR in 2018,
#    and the 2018 path names differ (…TriplePFBTagDeepCSV_4p5 etc.).
#  - New vs UL17: TTWW_ext1 (UL18 has a large ext1 production).
#  - HEM15/16 veto is an analyzer-level concern — nothing to do here.
common:
  jobID: "campaign_ttHH2018UL_fullNano_v1"
  site: "T3_KR_KNU"
  output_base: "ttHH2018UL_fullNano_v1"
  analysis_module: ["modules/noop.py", "MODULES"]
  branch_file: "branches/branch_keep_all.txt"
  splitting: "FileBased"
  units_per_job: 1

datasets:
""")
    groups = [
        ("--- Signal (ttHH) ---", ["TTHHto4b"]),
        ("--- ttbar inclusive (5FS, powheg+pythia8) [ Key Backgrounds ] ---",
         ["TTbar_SemiLep", "TTbar_Hadronic", "TTbar_DiLep"]),
        ("--- tt+bb (4FS, Powheg-OpenLoops+pythia8) ---",
         ["TTbb_SemiLep", "TTbb_Hadronic", "TTbb_DiLep"]),
        ("--- QCD multijet (HT binned) ---",
         [k for k in mc if k.startswith("QCD_")]),
        ("--- ttH (M125) ---", ["ttHTobb", "ttHToNonbb"]),
        ("--- tH (single-top + H) ---", ["tHq", "tHW"]),
        ("--- ttV, hadronic V decay ---", ["TTZToBB", "TTWJetsToQQ"]),
        ("--- ttV, leptonic V decay ---", ["TTWJetsToLNu", "TTZToLLNuNu"]),
        ("--- ttVV / rare tt+X (NB: base + ext1 combined for statistics) ---",
         ["TTZHTo4b", "TTZHTo4b_ext1", "TTZZTo4b", "TTZZTo4b_ext1",
          "TTWW", "TTWW_ext1", "TTWH", "TTWZ", "TTTW", "TTTT", "TT4b"]),
        ("--- Single top (non-Higgs) ---",
         [k for k in mc if k.startswith("ST_")]),
        ("--- Diboson (WW, WZ, ZZ) ---", ["WW", "WZ", "ZZ"]),
        ("--- V+jets, V->qq (hadronic), HT binned ---",
         [k for k in mc if k.startswith(("WJetsToQQ", "ZJetsToQQ"))]),
        ("--- W+jets, W->lnu (leptonic), gen-HT binned; base+ext combined ---",
         [k for k in mc if k.startswith("WJetsToLNu")]),
        ("--- Z+jets / DY, Z->ll (M-50, leptonic), gen-HT binned ---",
         [k for k in mc if k.startswith("DYJetsToLL")]),
    ]
    listed = set()
    for title, keys in groups:
        L.append(f"  # {title}")
        for k in keys:
            L.append(f'  {k}: "{mc[k][0]}"')
            listed.add(k)
        L.append("")
    leftover = [k for k in mc if k not in listed]
    if leftover:
        sys.exit(f"FATAL: MC keys not covered by any group: {leftover}")

    for pd in ("JetHT", "SingleMuon"):
        L.append(f"  # --- Data ({pd}) --- (non-GT36; GT36 twin commented, OPEN)")
        for key, variants in data.items():
            if not key.startswith(pd):
                continue
            L.append(f'  {key}: "{variants["plain"][0]}"')
            if "gt36" in variants:
                L.append(f'  # {key}: "{variants["gt36"][0]}"   # GT36 alternative')
        L.append("")
    L.append("  # --- Data (BTagCSV) --- ABSENT in 2018: CONFIRMED (0 hits, any tier, any status;\n"
             "  #     2018 PD consolidation also dropped HTMHT/FSQJet/HighPt*, merged EGamma).\n"
             "  #     FH b-tag quad-jet HLT paths live in JetHT for 2018 -> JetHT alone suffices.\n"
             "  #     Analyzer must drop the 2017 BTagCSV/JetHT orthogonality veto for 2018.\n")
    OUT_YAML.write_text("\n".join(L))

    # ---- config_ttHH2018UL_prescan.yaml (slim smoke-test campaign) ----------
    # Same MC dataset list; Data = JetHT only (user decision 2026-07-26: BTagCSV
    # does not exist in 2018 and SingleMuon is only needed for the later trigger
    # SF study, so the smoke test carries JetHT alone). Slim output branches.
    P = ["""# Campaign Configuration — ttHH 2018UL PRESCAN SMOKE TEST (slim branches)
# ===========================
# Generated by script/build_ul18_from_log.py (same DAS log as the full config).
# PURPOSE: cheapest possible end-to-end check that the UL18 samples produce
# correctly, and that tempTTHH `prescan` (Sigma-genW) runs on the output.
# NOT for physics — the real production uses config_ttHH2018UL.yaml with
# branch_keep_all.txt, after the ttHH categorization work is folded in
# (then rerun for BOTH 2017 and 2018).
#
# Slim output branches: branches/branch_prescan_slim_2018.txt (see its header:
# Sigma-genW comes from the `Runs` tree, which the post-processor copies through
# untouched; only the Events tree is filtered). The list is ERA-SPECIFIC because
# a `keep` pattern matching no branch makes ROOT print a SetBranchStatus error
# per job (2017 CSV-era HLT names do not exist in 2018 - confirmed 2026-07-27).
#
# units_per_job = 1 (NOT larger): the INPUT is read in full regardless of the
# slim OUTPUT selection (A4: PostProcessor branchsel=None), so job runtime
# scales with input files, not output size. 1 file/job is the value proven by
# the 2017 campaign; the biggest 2018 samples (TTbar_SemiLep 476M evt over 391
# files) would risk the CRAB walltime at 5 files/job.
# Data = JetHT only (2018 has no BTagCSV PD; SingleMuon deferred to trigger SF).
common:
  jobID: "campaign_ttHH2018UL_prescanSlim_v1"
  site: "T3_KR_KNU"
  output_base: "ttHH2018UL_prescanSlim_v1"
  analysis_module: ["modules/noop.py", "MODULES"]
  branch_file: "branches/branch_prescan_slim_2018.txt"
  splitting: "FileBased"
  units_per_job: 1

datasets:
"""]
    for title, keys in groups:
        P.append(f"  # {title}")
        for k in keys:
            P.append(f'  {k}: "{mc[k][0]}"')
        P.append("")
    P.append("  # --- Data (JetHT only; see header) ---")
    for key, variants in data.items():
        if key.startswith("JetHT"):
            P.append(f'  {key}: "{variants["plain"][0]}"')
    P.append("")
    P.append("  # --- Data (SingleMuon) --- intentionally EXCLUDED from the smoke test;\n"
             "  #     present in config_ttHH2018UL.yaml for the later trigger-SF study.\n"
             "  # --- Data (BTagCSV) --- does not exist in 2018 (confirmed).\n")
    OUT_YAML_PRESCAN.write_text("\n".join(P))

    nmc = len(mc); ndata = len(data)
    print(f"[build_ul18] MC keys: {nmc} (UL17: 76) | Data keys: {ndata} | json entries: {len(out)-1}")
    print(f"[build_ul18] wrote {OUT_YAML}")
    print(f"[build_ul18] wrote {OUT_YAML_PRESCAN} (MC {nmc} + JetHT only)")
    print(f"[build_ul18] wrote {OUT_JSON}")

if __name__ == "__main__":
    main()
