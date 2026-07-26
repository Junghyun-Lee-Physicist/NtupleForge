#!/bin/bash
# =============================================================================
# das_ul18_scan.sh — UL17 -> UL18 dataset discovery for NtupleForge
# =============================================================================
# PURPOSE
#   For every sample in crabConfig/config_ttHH2017UL.yaml (campaign
#   campaign_ttHH2017UL_fullNano_v20), find the equivalent RunIISummer20UL18
#   NanoAODv9 dataset via DAS, and dump nevents/nfiles/size for each hit.
#   The log of this script is the input for writing config_ttHH2018UL*.yaml
#   and data/samples_2018UL.json (nevents column of the beamer backup table).
#
# USAGE (lxplus)
#   voms-proxy-init -voms cms -rfc --valid 72:00
#   ./das_ul18_scan.sh                 2>&1 | tee das_ul18_scan_$(date +%Y%m%d_%H%M).log
#   ./das_ul18_scan.sh --ul17-nevents  2>&1 | tee das_ul17_check_$(date +%Y%m%d_%H%M).log
#
#   --ul17-nevents : additionally re-dump the UL17 dataset summaries, to
#                    cross-check the nevents already stored in
#                    tempTTHH/data/samples_2017UL.json.
#
# OUTPUT FORMAT (machine-readable lines)
#   DS|<sampleKey17>|<dataset>|nevents=<N>|nfiles=<N>|size_TB=<X>
#   RESULT|<sampleKey17>|<EXACT|RELAXED|NOT_FOUND>|<n_datasets_found>
#
# QUERY STRATEGY
#   MC  : Q1 exact primary  : /<PRIMARY17>/RunIISummer20UL18NanoAODv9*/NANOAODSIM
#         Q2 relaxed primary: /<PRIMARY17 up to _TuneCP5>*/RunIISummer20UL18NanoAODv9*/NANOAODSIM
#            (only if Q1 empty — catches naming drift, e.g. the UL17 DYJets
#             "TuneCP5_PSweights" variant that may not exist under the same
#             name in UL18)
#         The campaign wildcard catches all versions AND ext datasets
#         (RunIISummer20UL18NanoAODv9-106X_upgrade2018_realistic_v16_L1v1[_extN]-vN).
#   Data: /<PRIMARY>/Run2018*-UL2018_MiniAODv2_NanoAODv9*/NANOAOD
#         (one query per primary dataset; lists all 2018 eras A-D incl. the
#          Run2018D *_GT36 variants — pick per-era entries by hand from the log)
#
# KNOWN 2018 CAVEATS (decide from the log, do NOT guess):
#   - BTagCSV may not exist as a 2018 primary dataset. If Q returns nothing,
#     the b-tag-side data stream for 2018 must be decided separately (user).
#   - 2018 eras are A/B/C/D (2017 was B..F). Era-by-era keys in the YAML will
#     therefore differ in count.
#   - HEM15/16 veto (2018 only) is an ANALYZER-level concern, not a sample
#     selection concern — no action here.
#
# Source of the UL17 list below: crabConfig/config_ttHH2017UL.yaml, generated
# 2026-07-26. If the YAML changes, regenerate this list (one fact, one place:
# the YAML is the canonical list; this embedded copy exists only because
# lxplus-side PyYAML availability is not guaranteed).
# =============================================================================

set -u

command -v dasgoclient >/dev/null 2>&1 || { echo "FATAL: dasgoclient not found (run on lxplus with CMS env)"; exit 1; }
voms-proxy-info -exists 2>/dev/null || { echo "FATAL: no valid VOMS proxy (voms-proxy-init -voms cms -rfc)"; exit 2; }

DO_UL17_CHECK=0
[[ "${1:-}" == "--ul17-nevents" ]] && DO_UL17_CHECK=1

# --- helper: dump summary for one dataset ------------------------------------
das_summary () {
    local key="$1" ds="$2"
    local js
    js=$(dasgoclient -query "summary dataset=${ds}" -json 2>/dev/null)
    python3 - "$key" "$ds" <<'EOF' "$js"
import sys, json
key, ds = sys.argv[1], sys.argv[2]
raw = sys.argv[3] if len(sys.argv) > 3 else ""
nev = nf = "NA"; tb = "NA"
try:
    j = json.loads(raw)
    s = j[0]["summary"][0]
    nev, nf = s.get("nevents", "NA"), s.get("nfiles", "NA")
    tb = "%.3f" % (s.get("file_size", 0) / 1e12)
except Exception:
    pass
print(f"DS|{key}|{ds}|nevents={nev}|nfiles={nf}|size_TB={tb}")
EOF
}

# --- helper: query + report one MC sample ------------------------------------
scan_mc () {
    local key="$1" primary="$2"
    echo ""
    echo "### MC ${key}  (UL17 primary: ${primary})"
    local q1="/${primary}/RunIISummer20UL18NanoAODv9*/NANOAODSIM"
    mapfile -t hits < <(dasgoclient -query "dataset=${q1}" 2>/dev/null)
    local mode="EXACT"
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        mode="RELAXED"
        local prefix="${primary%%_TuneCP5*}"
        local q2="/${prefix}*/RunIISummer20UL18NanoAODv9*/NANOAODSIM"
        echo "  (exact primary empty -> relaxed query: ${q2})"
        mapfile -t hits < <(dasgoclient -query "dataset=${q2}" 2>/dev/null)
    fi
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        echo "RESULT|${key}|NOT_FOUND|0"
        return
    fi
    local n=0
    for ds in "${hits[@]}"; do
        [[ -z "$ds" ]] && continue
        das_summary "$key" "$ds"
        n=$((n+1))
    done
    echo "RESULT|${key}|${mode}|${n}"
}

# --- helper: query + report one Data primary dataset -------------------------
scan_data () {
    local primary="$1"
    echo ""
    echo "### DATA ${primary}"
    local q="/${primary}/Run2018*-UL2018_MiniAODv2_NanoAODv9*/NANOAOD"
    mapfile -t hits < <(dasgoclient -query "dataset=${q}" 2>/dev/null)
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        echo "RESULT|${primary}|NOT_FOUND|0"
        return
    fi
    local n=0
    for ds in "${hits[@]}"; do
        [[ -z "$ds" ]] && continue
        das_summary "${primary}_2018" "$ds"
        n=$((n+1))
    done
    echo "RESULT|${primary}|EXACT|${n}"
}

# =============================================================================
# UL17 sample list: "<sampleKey17> <primary dataset name>"
# ext-datasets (TTZHTo4b_ext1 etc.) share the primary of their base sample and
# are covered by the campaign wildcard — they are intentionally not repeated.
# =============================================================================
MC_SAMPLES=(
  "TTHHto4b TTHHTo4b_TuneCP5_13TeV-madgraph-pythia8"
  "TTbar_SemiLep TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8"
  "TTbar_Hadronic TTToHadronic_TuneCP5_13TeV-powheg-pythia8"
  "TTbar_DiLep TTTo2L2Nu_TuneCP5_13TeV-powheg-pythia8"
  "TTbb_SemiLep TTbb_4f_TTToSemiLeptonic_TuneCP5-Powheg-Openloops-Pythia8"
  "TTbb_Hadronic TTbb_4f_TTToHadronic_TuneCP5-Powheg-Openloops-Pythia8"
  "TTbb_DiLep TTbb_4f_TTTo2L2Nu_TuneCP5-Powheg-Openloops-Pythia8"
  "QCD_HT200to300 QCD_HT200to300_TuneCP5_13TeV-madgraphMLM-pythia8"
  "QCD_HT300to500 QCD_HT300to500_TuneCP5_13TeV-madgraphMLM-pythia8"
  "QCD_HT500to700 QCD_HT500to700_TuneCP5_13TeV-madgraphMLM-pythia8"
  "QCD_HT700to1000 QCD_HT700to1000_TuneCP5_13TeV-madgraphMLM-pythia8"
  "QCD_HT1000to1500 QCD_HT1000to1500_TuneCP5_13TeV-madgraphMLM-pythia8"
  "QCD_HT1500to2000 QCD_HT1500to2000_TuneCP5_13TeV-madgraphMLM-pythia8"
  "QCD_HT2000toInf QCD_HT2000toInf_TuneCP5_13TeV-madgraphMLM-pythia8"
  "ttHTobb ttHTobb_M125_TuneCP5_13TeV-powheg-pythia8"
  "ttHToNonbb ttHToNonbb_M125_TuneCP5_13TeV-powheg-pythia8"
  "tHq THQ_ctcvcp_4f_Hincl_TuneCP5_13TeV_madgraph_pythia8"
  "tHW THW_ctcvcp_5f_Hincl_TuneCP5_13TeV_madgraph_pythia8"
  "TTZToBB TTZToBB_TuneCP5_13TeV-amcatnlo-pythia8"
  "TTWJetsToQQ TTWJetsToQQ_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8"
  "TTWJetsToLNu TTWJetsToLNu_TuneCP5_13TeV-amcatnloFXFX-madspin-pythia8"
  "TTZToLLNuNu TTZToLLNuNu_M-10_TuneCP5_13TeV-amcatnlo-pythia8"
  "TTZHTo4b TTZHTo4b_TuneCP5_13TeV-madgraph-pythia8"
  "TTZZTo4b TTZZTo4b_TuneCP5_13TeV-madgraph-pythia8"
  "TTWW TTWW_TuneCP5_13TeV-madgraph-pythia8"
  "TTWH TTWH_TuneCP5_13TeV-madgraph-pythia8"
  "TTWZ TTWZ_TuneCP5_13TeV-madgraph-pythia8"
  "TTTW TTTW_TuneCP5_13TeV-madgraph-pythia8"
  "TTTT TTTT_TuneCP5_13TeV-amcatnlo-pythia8"
  "TT4b TT4b_TuneCP5_13TeV_madgraph_pythia8"
  "ST_t_top ST_t-channel_top_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8"
  "ST_t_antitop ST_t-channel_antitop_4f_InclusiveDecays_TuneCP5_13TeV-powheg-madspin-pythia8"
  "ST_tW_top ST_tW_top_5f_inclusiveDecays_TuneCP5_13TeV-powheg-pythia8"
  "ST_tW_antitop ST_tW_antitop_5f_inclusiveDecays_TuneCP5_13TeV-powheg-pythia8"
  "ST_s_lep ST_s-channel_4f_leptonDecays_TuneCP5_13TeV-amcatnlo-pythia8"
  "ST_s_had ST_s-channel_4f_hadronicDecays_TuneCP5_13TeV-amcatnlo-pythia8"
  "WW WW_TuneCP5_13TeV-pythia8"
  "WZ WZ_TuneCP5_13TeV-pythia8"
  "ZZ ZZ_TuneCP5_13TeV-pythia8"
  "WJetsToQQ_HT400to600 WJetsToQQ_HT-400to600_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToQQ_HT600to800 WJetsToQQ_HT-600to800_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToQQ_HT800toInf WJetsToQQ_HT-800toInf_TuneCP5_13TeV-madgraphMLM-pythia8"
  "ZJetsToQQ_HT400to600 ZJetsToQQ_HT-400to600_TuneCP5_13TeV-madgraphMLM-pythia8"
  "ZJetsToQQ_HT600to800 ZJetsToQQ_HT-600to800_TuneCP5_13TeV-madgraphMLM-pythia8"
  "ZJetsToQQ_HT800toInf ZJetsToQQ_HT-800toInf_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT70To100 WJetsToLNu_HT-70To100_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT100To200 WJetsToLNu_HT-100To200_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT200To400 WJetsToLNu_HT-200To400_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT400To600 WJetsToLNu_HT-400To600_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT600To800 WJetsToLNu_HT-600To800_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT800To1200 WJetsToLNu_HT-800To1200_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT1200To2500 WJetsToLNu_HT-1200To2500_TuneCP5_13TeV-madgraphMLM-pythia8"
  "WJetsToLNu_HT2500ToInf WJetsToLNu_HT-2500ToInf_TuneCP5_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT70to100 DYJetsToLL_M-50_HT-70to100_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT100to200 DYJetsToLL_M-50_HT-100to200_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT200to400 DYJetsToLL_M-50_HT-200to400_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT400to600 DYJetsToLL_M-50_HT-400to600_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT600to800 DYJetsToLL_M-50_HT-600to800_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT800to1200 DYJetsToLL_M-50_HT-800to1200_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT1200to2500 DYJetsToLL_M-50_HT-1200to2500_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
  "DYJetsToLL_M50_HT2500toInf DYJetsToLL_M-50_HT-2500toInf_TuneCP5_PSweights_13TeV-madgraphMLM-pythia8"
)

DATA_PRIMARIES=( "JetHT" "BTagCSV" "SingleMuon" )

# UL17 full dataset paths (for --ul17-nevents cross-check only)
UL17_DATASETS_FILE_HINT="crabConfig/config_ttHH2017UL.yaml"

echo "=============================================================="
echo " das_ul18_scan.sh  start: $(date -u +%FT%TZ)"
echo " MC primaries: ${#MC_SAMPLES[@]} | Data primaries: ${#DATA_PRIMARIES[@]}"
echo "=============================================================="

echo ""
echo "########## [1] MC: UL18 discovery ##########"
for entry in "${MC_SAMPLES[@]}"; do
    scan_mc ${entry}
done

echo ""
echo "########## [2] DATA: Run2018 discovery ##########"
for p in "${DATA_PRIMARIES[@]}"; do
    scan_data "$p"
done

if [[ ${DO_UL17_CHECK} -eq 1 ]]; then
    echo ""
    echo "########## [3] UL17 nevents cross-check ##########"
    echo "# compare against tempTTHH/data/samples_2017UL.json"
    for entry in "${MC_SAMPLES[@]}"; do
        set -- ${entry}
        key="$1"; primary="$2"
        for ds in $(dasgoclient -query "dataset=/${primary}/RunIISummer20UL17NanoAODv9*/NANOAODSIM" 2>/dev/null); do
            das_summary "UL17_${key}" "$ds"
        done
    done
    for p in "${DATA_PRIMARIES[@]}"; do
        for ds in $(dasgoclient -query "dataset=/${p}/Run2017*-UL2017_MiniAODv2_NanoAODv9*/NANOAOD" 2>/dev/null); do
            das_summary "UL17_${p}" "$ds"
        done
    done
fi

echo ""
echo "=============================================================="
echo " done: $(date -u +%FT%TZ)"
echo " grep '^RESULT|' for the per-sample verdict; grep '^DS|' for datasets."
echo " NOT_FOUND samples need manual DAS search — report the log back."
echo "=============================================================="
