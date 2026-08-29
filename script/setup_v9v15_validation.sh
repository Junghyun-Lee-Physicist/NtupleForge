# =============================================================================
# v9 <-> v15 event-matched validation -- session bootstrap
#
#   SOURCE this, do not execute:
#       source script/setup_v9v15_validation.sh
#
# A fresh lxplus session loses everything this restores: the shell variables,
# the two NanoAOD files under /tmp (per-node and periodically cleaned), and the
# shared-lumi cut expression. Idempotent -- safe to source repeatedly.
#
# WHY THE LFNs ARE PINNED
# -----------------------
# The v9 and v15 NanoAOD of this dataset have an IDENTICAL MiniAODv2 parent but
# completely different file boundaries: the first file of each has ZERO events
# in common. The two files below were paired by luminosity-block overlap
# (143 shared lumis ~ 143k events per side, found by ranking all 398 v15 files
# against the v9 file's lumi list). `dasgoclient ... | head -1` would silently
# pick a different file and the overlap would vanish. Never substitute it.
# See docs/08_branch_schema_migration.md.
#
# CACHE
# -----
# Set NF_CACHE to a persistent area so the 5 GB is not re-fetched every session:
#     export NF_CACHE=/eos/user/j/junghyun/nanocache      # then source this
# Default is /tmp, which is per-node on lxplus and gets cleaned.
# =============================================================================

# --- must be sourced, not executed ------------------------------------------
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "ERROR: source this file, do not execute it:"
    echo "       source script/setup_v9v15_validation.sh"
    exit 1
fi

# --- history expansion off (a '!!' inside double quotes silently becomes the
#     previous command; see docs/08 section 2 Step 0) -------------------------
set +H

export NF_CACHE="${NF_CACHE:-/tmp}"
mkdir -p "$NF_CACHE" 2>/dev/null

# --- pinned inputs -----------------------------------------------------------
export LFN_V9='/store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root'
export LFN_V15P='/store/mc/RunIISummer20UL17NanoAODv15/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/150X_mc2017_realistic_v1-v2/2560000/12804c46-d060-4a27-b333-a6254f4dc02c.root'

export LOCAL_V9="$NF_CACHE/nano_v9_local.root"
export LOCAL_V15P="$NF_CACHE/nano_v15_paired.root"
export CUT_FILE="$NF_CACHE/shared_cut.txt"
export LUMI_FILE="$NF_CACHE/shared_lumis.txt"

export DS_V9='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM'
export DS_V15='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2/NANOAODSIM'
export DS_MINI='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1/MINIAODSIM'
export INV=script/inventory

# --- proxy -------------------------------------------------------------------
if ! voms-proxy-info -e >/dev/null 2>&1; then
    echo ">> no valid grid proxy; run:  voms-proxy-init -voms cms -rfc -valid 192:00"
fi

# --- fetch -------------------------------------------------------------------
_nf_fetch() {                      # _nf_fetch <LFN> <local path>
    if [ -s "$2" ]; then
        echo "have   $2  ($(du -h "$2" 2>/dev/null | cut -f1))"
        return 0
    fi
    echo ">>     fetching $2"
    xrdcp -f "root://cms-xrd-global.cern.ch/$1" "$2"
}
_nf_fetch "$LFN_V9"   "$LOCAL_V9"
_nf_fetch "$LFN_V15P" "$LOCAL_V15P"

# --- shared-lumi cut ---------------------------------------------------------
if [ -s "$CUT_FILE" ]; then
    echo "have   $CUT_FILE"
elif [ -s "$LOCAL_V9" ] && [ -s "$LOCAL_V15P" ]; then
    echo ">>     rebuilding shared-lumi cut"
    python3 - "$LOCAL_V9" "$LOCAL_V15P" "$CUT_FILE" "$LUMI_FILE" <<'PY'
import sys, ROOT, numpy as np
ROOT.gROOT.SetBatch(True)
f9, f15, cutf, lumf = sys.argv[1:5]
def lumis(fn):
    d = ROOT.RDataFrame("LuminosityBlocks", fn).AsNumpy(["luminosityBlock"])
    return set(np.asarray(d["luminosityBlock"]).astype(np.int64).tolist())
L9, L15 = lumis(f9), lumis(f15)
sh = sorted(L9 & L15)
if not sh:
    sys.exit("ERROR: zero shared lumi blocks -- the file pairing is wrong")
expr = "||".join("luminosityBlock==%d" % l for l in sh)
open(cutf, "w").write(expr)
open(lumf, "w").write("\n".join(map(str, sh)))
print("       v9=%d lumi  v15paired=%d lumi  shared=%d  (~%d events per side)"
      % (len(L9), len(L15), len(sh), 1000 * len(sh)))
PY
else
    echo ">>     cut not built (input files missing)"
fi

if [ -s "$CUT_FILE" ]; then
    export CUT="$(cat "$CUT_FILE")"
else
    unset CUT
fi

# --- summary -----------------------------------------------------------------
echo "-------------------------------------------------------------"
echo "  NF_CACHE     = $NF_CACHE"
echo "  LOCAL_V9     = $LOCAL_V9"
echo "  LOCAL_V15P   = $LOCAL_V15P"
echo "  CUT          = ${#CUT} bytes  (expect 3573)"
echo "  INV          = $INV"
echo "-------------------------------------------------------------"
echo "  next:  python3 script/run_postproc.py \"\$LOCAL_V9\"   -I modules.topCPVCategorizer:MODULES -b branches/branch_CPV_Run2_MC.txt     --cut \"\$CUT\" -o matched_v9.root"
echo "         python3 script/run_postproc.py \"\$LOCAL_V15P\" -I modules.topCPVCategorizer:MODULES -b branches/branch_CPV_Run2_MC_v15.txt --cut \"\$CUT\" -o matched_v15.root"
