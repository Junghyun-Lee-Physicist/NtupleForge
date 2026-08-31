#!/usr/bin/env bash
# =============================================================================
#  das_scan.sh  --  era x NanoAOD-version parameterized DAS enumeration
# =============================================================================
#  Generalization of script/das_ul18_scan.sh (2026-07-26), which was hardwired
#  to UL18 x NanoAODv9 in 13 places. This version takes the era and the NanoAOD
#  version as arguments and reads the sample list from
#  script/samples_registry.txt, so adding a year or a NanoAOD version is a
#  command-line change, not an edit.
#
#  Created 2026-08-17 for the v9 || v15 parallel campaign (2017UL + 2018UL,
#  Run 3 later).
#
#  WHAT IT DOES NOT DO: it never constructs a full DAS path. Only the PRIMARY
#  dataset name (from the registry) and the CAMPAIGN PREFIX (from the era table
#  below) are ours; the global tag, the _extN suffix and the -vN suffix always
#  come back from DAS. This is the same rule TTHHGenCategoryTools states for
#  MiniAOD parents ("Never assume the -vN suffix from the nano child") and it
#  exists because the suffixes are assigned independently per dataset.
#
# -----------------------------------------------------------------------------
#  USAGE (lxplus, inside the CMS environment, with a valid proxy)
#
#    voms-proxy-init -voms cms -rfc --valid 72:00
#
#    # (0) DISCOVERY -- what NanoAOD campaigns exist at all for this era?
#    #     RUN THIS FIRST for any version you have not used before (v15!).
#    #     It is cheap (a handful of queries) and it is the only honest way to
#    #     learn the v15 campaign string. Do not guess it.
#    bash script/das_scan.sh --era 2018UL --probe
#
#    # (1) FULL SCAN -- enumerate every registry sample for one (era, version)
#    bash script/das_scan.sh --era 2017UL --nano v9  --out script/das_2017UL_v9_$(date +%Y%m%d_%H%M).log
#    bash script/das_scan.sh --era 2018UL --nano v9  --out script/das_2018UL_v9_$(date +%Y%m%d_%H%M).log
#    bash script/das_scan.sh --era 2017UL --nano v15 --out script/das_2017UL_v15_$(date +%Y%m%d_%H%M).log
#    bash script/das_scan.sh --era 2018UL --nano v15 --out script/das_2018UL_v15_$(date +%Y%m%d_%H%M).log
#
#    # (2) one example file per dataset, for the branch-inventory step
#    bash script/das_scan.sh --era 2018UL --nano v9 --sample-file --only TTbar_SemiLep,JetHT
#
#    # (3) the registry covers TWO workstreams -- pick one, or you scan both
#    bash script/das_scan.sh --era 2017UL --nano v9 --workstream ttHH
#    bash script/das_scan.sh --era 2017UL --nano v9 --workstream CPVval   # 13-sample subset
#
#  Then feed the log to:  python3 script/build_from_scan_log.py <log>
#
# -----------------------------------------------------------------------------
#  OPTIONS
#    --era ERA          REQUIRED unless --list-eras. See the era table below.
#    --nano VER         NanoAOD version token, e.g. v9 / v12 / v15.
#                       REQUIRED except in --probe mode.
#    --probe            Discovery mode: enumerate ALL NanoAOD campaigns visible
#                       for a few probe primaries, MC and Data. Ignores --nano
#                       (or, if --nano is given, additionally runs a narrowed
#                       query for that version). Emits CAMP| lines.
#    --sample-file      Additionally emit one example LFN per dataset (FILE|).
#    --only K1,K2,...   Restrict to these registry keys (comma separated).
#    --workstream TAG   Restrict to registry rows whose WORKSTREAM column carries
#                       this tag. The registry covers TWO analyses whose sample
#                       lists deliberately differ, so WITHOUT this flag a scan
#                       enumerates BOTH (172 rows) and most of the other
#                       workstream's samples are wasted queries. Tags:
#                         ttHH    the ttHH -> 4b campaign        (64 rows)
#                         CPV     the top-CPV / SSB campaign     (109 rows)
#                         CPVval  the 13-sample CPV cross-validation subset
#                       Combine with --only for a hand-picked subset.
#    --registry PATH    Registry file (default: <script dir>/samples_registry.txt)
#    --out PATH         Write the log here AND to stdout. If omitted, stdout
#                       only -- then you must `tee` it yourself, and the
#                       builder needs the path.
#    --list-eras        Print the era table and exit 0.
#    -h | --help        This header.
#
#  EXIT CODES
#    0  scan completed (individual NOT_FOUND samples do NOT change this --
#       check the RESULT| lines; build_from_scan_log.py fails loudly on them)
#    1  dasgoclient not found (not on lxplus / no CMS env)
#    2  no valid VOMS proxy
#    3  bad arguments / unknown era
#    4  registry file unreadable, or the era/workstream/only filters selected 0 rows
#
#  OUTPUT FORMAT (machine-readable lines; everything else is human commentary)
#    META|era=<ERA>|nano=<VER>|mc_campaign=<PREFIX>|data_runera=<R>|data_proc=<P>|registry=<PATH>|workstream=<TAG>|utc=<ISO8601>
#    DS|<key>|<dataset>|nevents=<N>|nfiles=<N>|size_TB=<X>
#    RESULT|<key>|<EXACT|RELAXED|NOT_FOUND>|<n_datasets_found>
#    CAMP|<MC|DATA>|<primary>|<campaign>                       (--probe)
#    FILE|<key>|<dataset>|<lfn>                                (--sample-file)
#
#  The DS|/RESULT| formats are byte-compatible with das_ul18_scan.sh so the old
#  2026-07-26 log stays parseable by the new builder.
#
#  PROVENANCE: commit the log. It is the sole input of build_from_scan_log.py
#  and contains no credentials (unlike CRAB submission transcripts -- see
#  docs/05_troubleshooting.md A17). .gitignore already carves out script/das_*.log.
# =============================================================================

set -u

# -----------------------------------------------------------------------------
# ERA TABLE
# -----------------------------------------------------------------------------
# @V@ is replaced by the --nano token.
#
# MC_CAMPAIGN : campaign PREFIX for NANOAODSIM. A trailing '*' is added by the
#               query, which absorbs the global tag, _extN and -vN.
# DATA_RUNERA : acquisition-era prefix for NANOAOD (e.g. Run2018 -> Run2018A..D)
# DATA_PROC   : processing-string prefix for NANOAOD.
#
# Sources: the v9 strings are the ones actually used and DAS-verified in
# crabConfig/config_ttHH{2017,2018}UL.yaml and config_CPV*.yaml. The 2016
# preVFP/postVFP split (NanoAODAPV / HIPM_) follows the standard UL naming.
# For any version other than v9 these are BEST-GUESS TEMPLATES -- run --probe
# and correct the table before trusting a scan.
#
# ⚠ THE DATA PROCESSING STRING IS NOT THE SAME SHAPE ACROSS VERSIONS.
# v9  : /JetHT/Run2017B-UL2017_MiniAODv2_NanoAODv9-v1/NANOAOD
# v15 : /JetHT/Run2017B-UL2017_NanoAODv15-v1/NANOAOD        <- no 'MiniAODv2_'
# Substituting @V@ into the v9 template therefore asks for a dataset that does
# not exist, and the scan reports NOT_FOUND for data that is in fact fully
# available (all of Run2017B-F, JetHT and BTagCSV). That happened on
# 2026-08-31 and produced the wrong conclusion "NanoAODv15 is an MC-only
# campaign". scan_data() now falls back to a relaxed query the way the MC path
# already did. See docs/05_troubleshooting.md A19 -- same class of error:
# concluding absence from a single assumed query pattern.
era_table () {
  case "$1" in
    2016preVFPUL)  MC_CAMPAIGN="RunIISummer20UL16NanoAODAPV@V@"
                   DATA_RUNERA="Run2016"
                   DATA_PROC="HIPM_UL2016_MiniAODv2_NanoAOD@V@" ;;
    2016postVFPUL) MC_CAMPAIGN="RunIISummer20UL16NanoAOD@V@"
                   DATA_RUNERA="Run2016"
                   DATA_PROC="UL2016_MiniAODv2_NanoAOD@V@" ;;
    2017UL)        MC_CAMPAIGN="RunIISummer20UL17NanoAOD@V@"
                   DATA_RUNERA="Run2017"
                   DATA_PROC="UL2017_MiniAODv2_NanoAOD@V@" ;;
    2018UL)        MC_CAMPAIGN="RunIISummer20UL18NanoAOD@V@"
                   DATA_RUNERA="Run2018"
                   DATA_PROC="UL2018_MiniAODv2_NanoAOD@V@" ;;
    # --- Run 3 placeholders. UNVERIFIED: run --probe before enabling. The
    #     sample primaries also change (TuneCP5_13p6TeV) -- add Run-3 rows to
    #     the registry, do not reuse the 13 TeV ones.
    2022)          MC_CAMPAIGN="Run3Summer22NanoAOD@V@"
                   DATA_RUNERA="Run2022"
                   DATA_PROC="22Sep2023" ;;
    2022EE)        MC_CAMPAIGN="Run3Summer22EENanoAOD@V@"
                   DATA_RUNERA="Run2022"
                   DATA_PROC="22Sep2023" ;;
    2023)          MC_CAMPAIGN="Run3Summer23NanoAOD@V@"
                   DATA_RUNERA="Run2023"
                   DATA_PROC="22Sep2023" ;;
    2023BPix)      MC_CAMPAIGN="Run3Summer23BPixNanoAOD@V@"
                   DATA_RUNERA="Run2023"
                   DATA_PROC="22Sep2023" ;;
    *) return 1 ;;
  esac
  return 0
}

ALL_ERAS="2016preVFPUL 2016postVFPUL 2017UL 2018UL 2022 2022EE 2023 2023BPix"

# Probe primaries: a ttbar MC that exists in every era, and the two PDs.
# Deliberately small -- the point is to enumerate campaigns, not samples.
PROBE_MC=( "TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8"
           "TTToHadronic_TuneCP5_13TeV-powheg-pythia8" )
PROBE_DATA=( "JetHT" "SingleMuon" )

# -----------------------------------------------------------------------------
# ARGUMENTS
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERA="" ; NANO="" ; PROBE=0 ; SAMPLE_FILE=0 ; ONLY="" ; OUT="" ; WORKSTREAM=""
REGISTRY="${SCRIPT_DIR}/samples_registry.txt"

usage () { sed -n '2,/^# ====/p' "${BASH_SOURCE[0]}" | sed 's/^#\{0,1\} \{0,1\}//' ; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --era)         ERA="${2:-}"      ; shift 2 ;;
    --nano)        NANO="${2:-}"     ; shift 2 ;;
    --registry)    REGISTRY="${2:-}" ; shift 2 ;;
    --only)        ONLY="${2:-}"     ; shift 2 ;;
    --workstream)  WORKSTREAM="${2:-}" ; shift 2 ;;
    --out)         OUT="${2:-}"      ; shift 2 ;;
    --probe)       PROBE=1           ; shift   ;;
    --sample-file) SAMPLE_FILE=1     ; shift   ;;
    --list-eras)   echo "$ALL_ERAS" | tr ' ' '\n' ; exit 0 ;;
    -h|--help)     usage ; exit 0 ;;
    *) echo "FATAL: unknown argument '$1' (try --help)" >&2 ; exit 3 ;;
  esac
done

[[ -z "$ERA" ]] && { echo "FATAL: --era is required (see --list-eras)" >&2; exit 3; }
era_table "$ERA" || { echo "FATAL: unknown era '$ERA'. Known: $ALL_ERAS" >&2; exit 3; }
if [[ $PROBE -eq 0 && -z "$NANO" ]]; then
  echo "FATAL: --nano is required unless --probe (e.g. --nano v9 / --nano v15)" >&2; exit 3
fi

# Redirect everything to the log as well, if asked. Done before the preflight so
# that a preflight failure is also recorded.
if [[ -n "$OUT" ]]; then
  mkdir -p "$(dirname "$OUT")" 2>/dev/null
  exec > >(tee "$OUT") 2>&1
fi

# -----------------------------------------------------------------------------
# PREFLIGHT -- fail fast, before any query
# -----------------------------------------------------------------------------
command -v dasgoclient >/dev/null 2>&1 || {
  echo "FATAL: dasgoclient not found (run on lxplus with the CMS environment)"; exit 1; }
voms-proxy-info -exists 2>/dev/null || {
  echo "FATAL: no valid VOMS proxy (voms-proxy-init -voms cms -rfc --valid 72:00)"; exit 2; }

MC_CAMPAIGN="${MC_CAMPAIGN//@V@/${NANO}}"
DATA_PROC="${DATA_PROC//@V@/${NANO}}"

echo "========================================================================="
echo "das_scan.sh   era=${ERA}   nano=${NANO:-<probe>}   $(date -u +%FT%TZ)"
echo "  MC campaign prefix : ${MC_CAMPAIGN}"
echo "  Data era / proc    : ${DATA_RUNERA}* / ${DATA_PROC}*"
echo "  registry           : ${REGISTRY}"
echo "  workstream filter  : ${WORKSTREAM:-<none: BOTH ttHH and CPV>}"
echo "========================================================================="
echo "META|era=${ERA}|nano=${NANO}|mc_campaign=${MC_CAMPAIGN}|data_runera=${DATA_RUNERA}|data_proc=${DATA_PROC}|registry=${REGISTRY}|workstream=${WORKSTREAM}|utc=$(date -u +%FT%TZ)"

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

# das_summary <key> <dataset>  ->  one DS| line (and optionally a FILE| line)
das_summary () {
    local key="$1" ds="$2" js
    js=$(dasgoclient -query "summary dataset=${ds}" -json 2>/dev/null)
    python3 - "$key" "$ds" <<'EOF' "$js"
import sys, json
key, ds = sys.argv[1], sys.argv[2]
raw = sys.argv[3] if len(sys.argv) > 3 else ""
nev = nf = "NA"; tb = "NA"
try:
    s = json.loads(raw)[0]["summary"][0]
    nev, nf = s.get("nevents", "NA"), s.get("nfiles", "NA")
    tb = "%.3f" % (s.get("file_size", 0) / 1e12)
except Exception:
    pass
print("DS|%s|%s|nevents=%s|nfiles=%s|size_TB=%s" % (key, ds, nev, nf, tb))
EOF
    if [[ $SAMPLE_FILE -eq 1 ]]; then
        local lfn
        lfn=$(dasgoclient -query "file dataset=${ds}" 2>/dev/null | head -n1)
        [[ -n "${lfn:-}" ]] && echo "FILE|${key}|${ds}|${lfn}"
    fi
}

# scan_mc <key> <primary>
scan_mc () {
    local key="$1" primary="$2"
    echo ""
    echo "### MC ${key}  (primary: ${primary})"
    local q1="/${primary}/${MC_CAMPAIGN}*/NANOAODSIM"
    mapfile -t hits < <(dasgoclient -query "dataset=${q1}" 2>/dev/null)
    local mode="EXACT"
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        # Relaxed: truncate the primary at the tune token. Covers naming drift
        # between eras, e.g. the UL17 '_PSWeights' QCD/DY variants. Handles both
        # '_TuneCP5_' and '_TuneCP5-' spellings; for Run 3 the token is
        # TuneCP5_13p6TeV, which %%_TuneCP5* also truncates correctly.
        mode="RELAXED"
        local prefix="${primary%%_TuneCP5*}"
        local q2="/${prefix}*/${MC_CAMPAIGN}*/NANOAODSIM"
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

# scan_data <key> <primary(PD)>
scan_data () {
    local key="$1" pd="$2"
    echo ""
    echo "### DATA ${pd}"
    local q="/${pd}/${DATA_RUNERA}*-${DATA_PROC}*/NANOAOD"
    local how="EXACT"
    mapfile -t hits < <(dasgoclient -query "dataset=${q}" 2>/dev/null)

    # Fallback, mirroring the MC path: the processing string is not the same
    # shape across NanoAOD versions -- v9 carries '_MiniAODv2_', v15 does not.
    # Drop that segment and retry before declaring the data missing.
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        local relaxed_proc
        relaxed_proc=$(printf '%s' "${DATA_PROC}" | sed -E 's/_MiniAODv[0-9]+_/*/')
        if [[ "$relaxed_proc" != "${DATA_PROC}" ]]; then
            q="/${pd}/${DATA_RUNERA}*-${relaxed_proc}*/NANOAOD"
            echo "  (exact proc empty -> relaxed query: ${q})"
            mapfile -t hits < <(dasgoclient -query "dataset=${q}" 2>/dev/null)
            how="RELAXED"
        fi
    fi

    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        echo "RESULT|${key}|NOT_FOUND|0"
        return
    fi
    local n=0
    for ds in "${hits[@]}"; do
        [[ -z "$ds" ]] && continue
        das_summary "${key}" "$ds"
        n=$((n+1))
    done
    echo "RESULT|${key}|${how}|${n}"
}

# -----------------------------------------------------------------------------
# PROBE MODE -- discovery. Answers "what campaigns exist?", nothing else.
# -----------------------------------------------------------------------------
if [[ $PROBE -eq 1 ]]; then
    echo ""
    echo "### PROBE: every NanoAOD campaign visible for the probe primaries."
    echo "###        Read the CAMP| lines and copy the exact campaign PREFIX"
    echo "###        into the era table at the top of this script."
    for prim in "${PROBE_MC[@]}"; do
        echo ""
        echo "### PROBE MC ${prim}"
        dasgoclient -query "dataset=/${prim}/*NanoAOD*/NANOAODSIM" 2>/dev/null \
          | awk -F/ 'NF>=4 && $3!="" {print "CAMP|MC|'"${prim}"'|" $3}' | sort -u
    done
    for pd in "${PROBE_DATA[@]}"; do
        echo ""
        echo "### PROBE DATA ${pd}"
        dasgoclient -query "dataset=/${pd}/*NanoAOD*/NANOAOD" 2>/dev/null \
          | awk -F/ 'NF>=4 && $3!="" {print "CAMP|DATA|'"${pd}"'|" $3}' | sort -u
    done
    if [[ -n "$NANO" ]]; then
        echo ""
        echo "### PROBE narrowed to nano=${NANO} (does it exist for era ${ERA}?)"
        for prim in "${PROBE_MC[@]}"; do
            echo "###   ${prim}  <-  ${MC_CAMPAIGN}*"
            dasgoclient -query "dataset=/${prim}/${MC_CAMPAIGN}*/NANOAODSIM" 2>/dev/null \
              | sed 's/^/HIT|/'
        done
        for pd in "${PROBE_DATA[@]}"; do
            echo "###   ${pd}  <-  ${DATA_RUNERA}*-${DATA_PROC}*"
            dasgoclient -query "dataset=/${pd}/${DATA_RUNERA}*-${DATA_PROC}*/NANOAOD" 2>/dev/null \
              | sed 's/^/HIT|/'
        done
    fi
    echo ""
    echo "### PROBE DONE. If the narrowed query returned nothing, the campaign"
    echo "### prefix in the era table is wrong for this version -- fix it from"
    echo "### the CAMP| lines above. Do NOT run a full scan until it returns hits."
    exit 0
fi

# -----------------------------------------------------------------------------
# REGISTRY
# -----------------------------------------------------------------------------
[[ -r "$REGISTRY" ]] || { echo "FATAL: cannot read registry '${REGISTRY}'"; exit 4; }

# Filter the registry to this era (and --only), emit "TYPE KEY PRIMARY" lines.
mapfile -t ROWS < <(
  ONLY="$ONLY" ERA="$ERA" WS="$WORKSTREAM" awk '
    /^[[:space:]]*#/ {next} /^[[:space:]]*$/ {next}
    NF < 5 {next}
    {
      type=$1; key=$2; prim=$3; eras=$4; ws=(NF>=6 ? $6 : "");
      if (eras != "*" && index("," eras ",", "," ENVIRON["ERA"] ",") == 0) next;
      only=ENVIRON["ONLY"];
      if (only != "" && index("," only ",", "," key ",") == 0) next;
      want=ENVIRON["WS"];
      if (want != "" && index("," ws ",", "," want ",") == 0) next;
      print type, key, prim;
    }' "$REGISTRY"
)

if [[ ${#ROWS[@]} -eq 0 ]]; then
  echo "FATAL: registry yielded 0 samples for era=${ERA}${WORKSTREAM:+ workstream=${WORKSTREAM}}${ONLY:+ only=${ONLY}}"
  echo "       Registry tags present:"
  awk '!/^[[:space:]]*#/ && NF>=6 {n=split($6,a,","); for(i=1;i<=n;i++) print "         " a[i]}' "$REGISTRY" | sort | uniq -c
  exit 4
fi
echo "### registry: ${#ROWS[@]} sample(s) selected for era=${ERA}${WORKSTREAM:+ --workstream ${WORKSTREAM}}${ONLY:+ --only ${ONLY}}"
if [[ -z "$WORKSTREAM" ]]; then
  echo "### NOTE: no --workstream given, so BOTH the ttHH and the CPV sample lists"
  echo "###       are being scanned. Pass --workstream ttHH (or CPV / CPVval) to"
  echo "###       scan only the one you need."
fi

n_mc=0; n_data=0
for row in "${ROWS[@]}"; do
    # shellcheck disable=SC2086
    set -- $row
    rtype="$1"; rkey="$2"; rprim="$3"
    case "$rtype" in
      MC)   scan_mc   "$rkey" "$rprim" ; n_mc=$((n_mc+1)) ;;
      DATA) scan_data "$rkey" "$rprim" ; n_data=$((n_data+1)) ;;
      *)    echo "WARNING: registry row with unknown TYPE '${rtype}' skipped: ${row}" ;;
    esac
done

echo ""
echo "========================================================================="
echo "das_scan.sh DONE   era=${ERA} nano=${NANO}   MC=${n_mc} DATA=${n_data}   $(date -u +%FT%TZ)"
echo "  next: python3 script/build_from_scan_log.py ${OUT:-<this log>}"
echo "  NOTE: NOT_FOUND rows above do not fail this script. The builder does."
echo "========================================================================="
exit 0
