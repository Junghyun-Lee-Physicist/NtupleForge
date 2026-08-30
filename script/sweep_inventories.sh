#!/usr/bin/env bash
# =============================================================================
# sweep_inventories.sh -- dump branch inventories for MANY datasets at once.
#
#   bash script/sweep_inventories.sh [manifest]     # default: the 2017UL manifest
#   bash script/sweep_inventories.sh - <<'EOF'      # or feed rows on stdin
#   2017B_v9_Data   /JetHT/Run2017B-UL2017_MiniAODv2_NanoAODv9*/NANOAOD
#   EOF
#
# Manifest rows are:  <label> <whitespace> <DAS dataset pattern>
# Blank lines and '#' comments are ignored. Existing inventories are SKIPPED,
# so re-running is cheap and idempotent.
#
# WHY
# ---
# Branch presence is not a property of the NanoAOD version alone. It varies by
# primary dataset, by tier (Data vs MC) and -- for HLT -- by RUN ERA, because
# the HLT branch set is the trigger menu of the run range the dataset covers.
# Measured 2026-08-30 on 2017UL v9:
#
#     Run2017B  1208 Events / 269 HLT     Run2017E  1612 / 526
#     Run2017C  1523 / 479                Run2017F  1666 / 580
#     Run2017D  1570 / 526                UL17 MC   1666 / 569
#
# Judging "this branch does not exist" from ONE file produced a wrong and
# expensive conclusion once already (docs/05_troubleshooting.md A19). Sweep
# first, then cross-tabulate with script/branch_presence_matrix.py.
#
# COST
# ----
# Cheap. dump_branch_inventory.py reads only the TTree schema, never the event
# data, so XRootD is fine here -- a few seconds per dataset, no xrdcp. (The
# "always copy to /tmp first" rule in docs/08 2절 Step 2 applies to EVENT LOOPS,
# not to schema dumps.)
#
# Needs: a valid grid proxy, dasgoclient, ROOT.
# =============================================================================
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="${NF_INVENTORY_DIR:-$REPO/script/inventory}"
MANIFEST="${1:-$REPO/script/inventory_manifest_2017UL.txt}"

mkdir -p "$OUTDIR"

if ! voms-proxy-info -e >/dev/null 2>&1; then
    echo "ERROR: no valid grid proxy. Run:"
    echo "       voms-proxy-init -voms cms -rfc -valid 192:00"
    exit 2
fi

if [ "$MANIFEST" = "-" ]; then
    SRC=/dev/stdin
elif [ -f "$MANIFEST" ]; then
    SRC="$MANIFEST"
else
    echo "ERROR: no such manifest: $MANIFEST"; exit 3
fi

echo "========================================================================"
echo " sweep_inventories.sh   out=$OUTDIR"
echo " manifest=$MANIFEST"
echo "========================================================================"

n_ok=0; n_skip=0; n_fail=0
while read -r label pattern _rest; do
    case "${label:-}" in ""|\#*) continue ;; esac
    [ -n "${pattern:-}" ] || { echo "!! no dataset for label '$label'"; n_fail=$((n_fail+1)); continue; }

    out="$OUTDIR/inv_${label}.tsv"
    if [ -s "$out" ]; then
        nb=$(awk -F'\t' '$1=="Events"' "$out" | wc -l)
        nh=$(awk -F'\t' '$1=="Events" && $2 ~ /^HLT_/' "$out" | wc -l)
        printf "  have  %-22s Events=%-5s HLT=%-5s %s\n" "$label" "$nb" "$nh" "(skip)"
        n_skip=$((n_skip+1)); continue
    fi

    ds=$(dasgoclient -query="dataset=$pattern" 2>/dev/null | head -1)
    if [ -z "$ds" ]; then
        printf "  MISS  %-22s no dataset matches %s\n" "$label" "$pattern"
        n_fail=$((n_fail+1)); continue
    fi
    lfn=$(dasgoclient -query="file dataset=$ds" 2>/dev/null | head -1)
    if [ -z "$lfn" ]; then
        printf "  MISS  %-22s dataset has no files: %s\n" "$label" "$ds"
        n_fail=$((n_fail+1)); continue
    fi

    if python3 "$REPO/script/dump_branch_inventory.py" \
            "root://cms-xrd-global.cern.ch/$lfn" --label "$label" -o "$out" >/dev/null 2>&1; then
        nb=$(awk -F'\t' '$1=="Events"' "$out" | wc -l)
        nh=$(awk -F'\t' '$1=="Events" && $2 ~ /^HLT_/' "$out" | wc -l)
        printf "  OK    %-22s Events=%-5s HLT=%-5s %s\n" "$label" "$nb" "$nh" "$ds"
        n_ok=$((n_ok+1))
    else
        printf "  FAIL  %-22s could not read %s\n" "$label" "$lfn"
        rm -f "$out"
        n_fail=$((n_fail+1))
    fi
done < "$SRC"

echo "------------------------------------------------------------------------"
echo " dumped=$n_ok  skipped=$n_skip  failed=$n_fail"
echo " next: python3 script/branch_presence_matrix.py --inventory-dir $OUTDIR \\"
echo "           --profile main --mc --era 2017 --partial-only"
echo "------------------------------------------------------------------------"
[ "$n_fail" -eq 0 ]
