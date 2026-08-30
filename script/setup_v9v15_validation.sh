# =============================================================================
# CPV v9 <-> v15 event-matched validation -- ONE-STOP SESSION SETUP
#
#   SOURCE this, do not execute:
#       source script/setup_v9v15_validation.sh
#
#   The ONLY things you must do by hand first:
#       ssh junghyun@lxplus.cern.ch
#       cd /afs/cern.ch/user/j/junghyun/CMSSW_14_2_1/src && cmssw-el8
#   (the el8 container spawns a new shell, so it cannot be entered from here)
#
#   Everything else -- cmsenv, git pull, grid proxy, every environment
#   variable, the two pinned NanoAOD inputs, the shared-lumi cut -- is done
#   below. Idempotent: safe to source again in the same shell.
#
#   After sourcing you have these commands:
#       nf_status     what is set / present right now
#       nf_smoke      30 s check that drop-* keeps the module's TopCPVCat_*
#       nf_v9         event-matched run on the v9 file      (~15 min)
#       nf_v15        event-matched run on the v15 file     (~15 min)
#       nf_compare    event-by-event v9 vs v15 comparison
#
# OVERRIDES (export before sourcing)
#   NF_RELEASE   CMSSW release dir   default /afs/cern.ch/user/j/junghyun/CMSSW_14_2_1
#   NF_CACHE     input file cache    default /tmp   (set to EOS to stop re-downloading 5 GB)
#   NF_WORK      scratch dir         default /tmp/nfwork
#   NF_EOSOUT    finished outputs    default /eos/user/<u>/<user>/nfout
#   NF_PULL      set to 0 to skip git pull
#
# WHY THE LFNs ARE PINNED
#   v9 and v15 NanoAOD of this dataset have an IDENTICAL MiniAODv2 parent but
#   completely different file boundaries: the first file of each has ZERO
#   events in common. The pair below was found by ranking all 398 v15 files
#   against the v9 file's lumi list -- 143 shared lumis, ~143k events per side.
#   `dasgoclient ... | head -1` would silently pick a different file and the
#   overlap would vanish. Never substitute it. See docs/08.
#
# WHY YOU MUST NOT RUN FROM THE REPO
#   run_postproc.py hardcodes OUTPUT_DIR="." (CRAB requires outputs in cwd), so
#   the intermediate <input>_Skim.root always lands in the CURRENT directory.
#   On 2026-08-28 one 143k-event run put 610 MB into AFS home and filled the
#   10 GB quota to 99 %. This script cds you to $WORK for that reason.
# =============================================================================

# --- must be sourced ---------------------------------------------------------
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "ERROR: source this file, do not execute it:"
    echo "       source script/setup_v9v15_validation.sh"
    exit 1
fi

# history expansion off: '!!' inside double quotes is silently replaced by the
# previous command, which mangles pasted commands (docs/08 2절 Step 0).
set +H

echo "============================================================="
echo " CPV v9<->v15 validation setup"
echo "============================================================="

# --- 0. el8 check ------------------------------------------------------------
if ! grep -qs 'release 8' /etc/redhat-release; then
    echo ">> WARNING: this does not look like el8."
    echo ">>          CMSSW_14_2_1 needs:  cmssw-el8"
fi

# --- 1. locate the repo ------------------------------------------------------
export NF_RELEASE="${NF_RELEASE:-/afs/cern.ch/user/j/junghyun/CMSSW_14_2_1}"
_nf_here="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." 2>/dev/null && pwd )"
if [ -n "$_nf_here" ] && [ -d "$_nf_here/modules" ]; then
    export REPO="$_nf_here"
elif [ -n "${CMSSW_BASE:-}" ] && [ -d "$CMSSW_BASE/src/NtupleForge/modules" ]; then
    export REPO="$CMSSW_BASE/src/NtupleForge"
elif [ -d "$NF_RELEASE/src/NtupleForge/modules" ]; then
    export REPO="$NF_RELEASE/src/NtupleForge"
else
    echo ">> ERROR: cannot locate the NtupleForge repo."
    echo ">>        set NF_RELEASE, or source this from inside the repo."
    unset _nf_here
    return 1
fi
unset _nf_here
echo "   REPO = $REPO"

# --- 2. cmsenv ---------------------------------------------------------------
if [ -z "${CMSSW_BASE:-}" ]; then
    if [ -d "$NF_RELEASE/src" ]; then
        echo ">> cmsenv ($NF_RELEASE)"
        _nf_pwd="$PWD"
        cd "$NF_RELEASE/src" && eval "$(scram runtime -sh)"
        cd "$_nf_pwd"; unset _nf_pwd
    else
        echo ">> WARNING: $NF_RELEASE/src not found -- run cmsenv yourself"
    fi
fi
echo "   CMSSW_BASE = ${CMSSW_BASE:-<unset>}"

# --- 3. git pull -------------------------------------------------------------
if [ "${NF_PULL:-1}" = "1" ]; then
    _nf_pwd="$PWD"; cd "$REPO"
    # --untracked-files=no: untracked files never block a fast-forward, and
    # script/inventory/ + validation outputs are always untracked here. Only
    # real modifications should stop the pull.
    if [ -n "$(git --no-optional-locks status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        echo ">> tracked files modified -- skipping git pull:"
        git --no-optional-locks status --short --untracked-files=no | sed 's/^/      /'
    else
        echo ">> git pull"
        git pull --ff-only 2>&1 | sed 's/^/      /'
    fi
    cd "$_nf_pwd"; unset _nf_pwd
fi

# --- 4. grid proxy -----------------------------------------------------------
if voms-proxy-info -e >/dev/null 2>&1; then
    echo "   proxy OK ($(voms-proxy-info -timeleft 2>/dev/null)s left)"
else
    echo ">> no valid grid proxy -- running voms-proxy-init"
    voms-proxy-init -voms cms -rfc -valid 192:00
fi

# --- 5. paths ----------------------------------------------------------------
export NF_CACHE="${NF_CACHE:-/tmp}"
export WORK="${NF_WORK:-/tmp/nfwork}"
export EOSOUT="${NF_EOSOUT:-/eos/user/${USER:0:1}/${USER}/nfout}"
mkdir -p "$NF_CACHE" 2>/dev/null
mkdir -p "$WORK"     2>/dev/null
mkdir -p "$EOSOUT"   2>/dev/null || echo ">> could not create $EOSOUT (EOS not mounted?)"

export INV="$REPO/script/inventory"
export BL_V9="$REPO/branches/branch_CPV_Run2_MC.txt"
export BL_V15="$REPO/branches/branch_CPV_Run2_MC_v15.txt"
export BL_VAL="$REPO/branches/branch_CPV_validation.txt"

# --- 6. pinned inputs --------------------------------------------------------
export LFN_V9='/store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root'
export LFN_V15P='/store/mc/RunIISummer20UL17NanoAODv15/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/150X_mc2017_realistic_v1-v2/2560000/12804c46-d060-4a27-b333-a6254f4dc02c.root'
export LOCAL_V9="$NF_CACHE/nano_v9_local.root"
export LOCAL_V15P="$NF_CACHE/nano_v15_paired.root"
export CUT_FILE="$NF_CACHE/shared_cut.txt"
export LUMI_FILE="$NF_CACHE/shared_lumis.txt"

export DS_V9='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1/NANOAODSIM'
export DS_V15='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2/NANOAODSIM'
export DS_MINI='/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1/MINIAODSIM'

_nf_fetch() {                      # _nf_fetch <LFN> <local path>
    if [ -s "$2" ]; then
        echo "   have $2 ($(du -h "$2" 2>/dev/null | cut -f1))"
        return 0
    fi
    echo ">> fetching $2"
    xrdcp -f "root://cms-xrd-global.cern.ch/$1" "$2"
}
_nf_fetch "$LFN_V9"   "$LOCAL_V9"
_nf_fetch "$LFN_V15P" "$LOCAL_V15P"

# --- 7. shared-lumi cut ------------------------------------------------------
if [ -s "$CUT_FILE" ]; then
    echo "   have $CUT_FILE"
elif [ -s "$LOCAL_V9" ] && [ -s "$LOCAL_V15P" ]; then
    echo ">> rebuilding shared-lumi cut"
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
open(cutf, "w").write("||".join("luminosityBlock==%d" % l for l in sh))
open(lumf, "w").write("\n".join(map(str, sh)))
print("   v9=%d lumi  v15paired=%d lumi  shared=%d  (~%d events per side)"
      % (len(L9), len(L15), len(sh), 1000 * len(sh)))
PY
fi
if [ -s "$CUT_FILE" ]; then export CUT="$(cat "$CUT_FILE")"; else unset CUT; fi

# =============================================================================
# commands
# =============================================================================
_NF_MOD="modules.topCPVCategorizer:MODULES"

nf_status() {
    echo "  REPO       $REPO"
    echo "  CMSSW_BASE ${CMSSW_BASE:-<unset>}"
    echo "  NF_CACHE   $NF_CACHE"
    echo "  WORK       $WORK   (cwd is $PWD)"
    echo "  EOSOUT     $EOSOUT"
    echo "  LOCAL_V9   $LOCAL_V9   $([ -s "$LOCAL_V9" ] && du -h "$LOCAL_V9" | cut -f1 || echo MISSING)"
    echo "  LOCAL_V15P $LOCAL_V15P  $([ -s "$LOCAL_V15P" ] && du -h "$LOCAL_V15P" | cut -f1 || echo MISSING)"
    echo "  CUT        ${#CUT} bytes (expect 3573)"
    echo "  proxy      $(voms-proxy-info -timeleft 2>/dev/null || echo NONE)s"
    ls -lh "$EOSOUT" 2>/dev/null | sed 's/^/  out: /'
}

nf_smoke() {
    cd "$WORK" || return 1
    rm -f ./*_Skim.root smoke.root
    python3 "$REPO/script/run_postproc.py" "$LOCAL_V9" -I "$_NF_MOD" \
        -b "$BL_VAL" -N 2000 -o smoke.root 2>&1 | tail -12
    python3 - <<'PY'
import ROOT
f = ROOT.TFile.Open("smoke.root")
t = f.Get("Events") if f and not f.IsZombie() else None
if not t:
    raise SystemExit("SMOKE FAIL: cannot read smoke.root")
bs = [b.GetName() for b in t.GetListOfBranches()]
cpv = [b for b in bs if b.startswith("TopCPVCat_")]
print("-" * 60)
print("total branches = %d" % len(bs))
print("TopCPVCat_*    = %d" % len(cpv))
print("events=%d  size=%.1f MB  -> %.3f kB/event"
      % (t.GetEntries(), f.GetSize() / 1e6, f.GetSize() / 1e3 / t.GetEntries()))
if not cpv:
    print()
    print("VERDICT: FAIL -- 'drop *' also removed the module's own branches.")
    print("         Add 'keep TopCPVCat_*' to branches/branch_CPV_validation.txt")
    print("         (costs one ROOT SetBranchStatus error per job) and re-run.")
else:
    print()
    print("VERDICT: OK -- module branches survive 'drop *'. Proceed to nf_v9 / nf_v15.")
PY
}

_nf_run() {                        # _nf_run <input> <branchlist> <outname>
    cd "$WORK" || return 1
    if [ -z "${CUT:-}" ]; then echo "ERROR: CUT is empty -- re-source the setup"; return 1; fi
    rm -f ./*_Skim.root
    time python3 "$REPO/script/run_postproc.py" "$1" -I "$_NF_MOD" \
        -b "$2" --cut "$CUT" -o "$EOSOUT/$3" 2>&1 | tail -25
    ls -lh "$EOSOUT/$3"
}
nf_v9()  { _nf_run "$LOCAL_V9"   "$BL_VAL" matched_v9.root;  }
nf_v15() { _nf_run "$LOCAL_V15P" "$BL_VAL" matched_v15.root; }

# cwd is $WORK after sourcing, so a bare `git pull` fails with "not a git
# repository". Use this instead.
nf_pull() { git -C "$REPO" pull --ff-only; }

# cwd is $WORK after sourcing, so RELATIVE paths into the repo fail. These
# wrappers anchor everything at $REPO so the paths are never typed by hand.
#   nf_check <branchlist> [check_branchlist args...]
#     the branch list may be a bare filename (resolved under $REPO/branches/)
nf_check() {
    local bl="$1"; shift
    [ -f "$bl" ] || bl="$REPO/branches/$bl"
    [ -f "$bl" ] || { echo "no such branch list: $1"; return 1; }
    python3 "$REPO/script/check_branchlist.py" "$bl" "$@"
}

# First v15 ttHH ntuple: pure passthrough (the ttHH configs use modules/noop.py,
# so NO module code changes are needed for v15 -- only the branch list).
#   nf_ttHH_v15 [n_events]        default 20000
nf_ttHH_v15() {
    cd "$WORK" || return 1
    local n="${1:-20000}"
    rm -f ./*_Skim.root
    time python3 "$REPO/script/run_postproc.py" "$LOCAL_V15P" \
        -I modules.noop:MODULES \
        -b "$REPO/branches/branch_hadronic_2017_v15_MC.txt" \
        -N "$n" -o "$EOSOUT/ttHH_v15_test.root" 2>&1 | tail -25
    ls -lh "$EOSOUT/ttHH_v15_test.root"
}

nf_compare() {
    python3 "$REPO/script/compare_v9_v15.py" \
        --v9 "$EOSOUT/matched_v9.root" --v15 "$EOSOUT/matched_v15.root" "$@"
}

# --- land in the scratch dir -------------------------------------------------
cd "$WORK"

echo "-------------------------------------------------------------"
nf_status
echo "-------------------------------------------------------------"
echo "  CPV:   nf_status | nf_pull | nf_smoke | nf_v9 | nf_v15 | nf_compare"
echo "  ttHH:  nf_check <branchlist> [args] | nf_ttHH_v15 [n_events]"
echo "  start with:  nf_smoke"
echo "-------------------------------------------------------------"
