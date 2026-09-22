#!/usr/bin/env bash
# =============================================================================
# das_status.sh -- DBS status (VALID / PRODUCTION / INVALID / ...) of every
# dataset matching one or more DAS patterns, one TSV row per dataset:
#
#     <dataset>  <status>  <nevents>  <nfiles>
#
#   /bin/bash script/das_status.sh "/TTTW*-DR1*/RunIISummer20UL1*NanoAODv15-150X*/NANOAODSIM"
#   /bin/bash script/das_status.sh /A/B/NANOAODSIM /C/D/NANOAODSIM
#
# WHY (2026-09-19). `dasgoclient -query "dataset=..."` lists VALID datasets
# only; `dataset status=*` lists every status but prints no status column;
# `summary dataset=` prints event counts but no status either. The 2026-09-18
# TTTW+/- check (run_probe_tttw_v15_20260918_060303.log) therefore proved
# existence and event counts but not VALID, and the UL17 v15 inventory has a
# `-v1` TTToHadronic that is INVALID with 0 events -- a `-v1` is not VALID by
# default. This script reads the status from the -json record, the same walk
# as das_inventory.sh (keys `status` / `dataset_access_type`).
#
# Needs: dasgoclient + a valid proxy (outside the CMSSW container is fine).
# Exit 0 = every dataset answered; 2 = no proxy; 3 = a pattern matched nothing.
# Read-only. Wrap with script/runlog.sh.
# =============================================================================
set -u

if ! voms-proxy-info -exists >/dev/null 2>&1; then
    echo "ERROR: no valid grid proxy. Run: voms-proxy-init -voms cms -rfc -valid 192:00" >&2
    exit 2
fi
[[ $# -ge 1 ]] || { echo "usage: das_status.sh <dataset-or-pattern> [...]" >&2; exit 3; }

rc=0
printf 'dataset\tstatus\tnevents\tnfiles\n'
for pat in "$@"; do
    mapfile -t hits < <(dasgoclient -query "dataset status=* dataset=${pat}" 2>/dev/null)
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        printf 'NO_MATCH\t%s\n' "$pat" >&2; rc=3; continue
    fi
    for ds in "${hits[@]}"; do
        js=$(dasgoclient -query "dataset status=* dataset=${ds}" -json 2>/dev/null)
        python3 - "$ds" "$js" <<'PYEOF'
import sys, json
ds, raw = sys.argv[1], sys.argv[2]
want = {"status": ("status", "dataset_access_type"), "nevents": ("nevents", "num_event"),
        "nfiles": ("nfiles", "num_file")}
found = {}
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            for name, keys in want.items():
                if k in keys and name not in found and v not in (None, ""):
                    found[name] = v
            walk(v)
    elif isinstance(o, list):
        for x in o:
            walk(x)
try:
    walk(json.loads(raw) if raw.strip() else [])
except Exception:
    pass
print("\t".join([ds, str(found.get("status", "-")), str(found.get("nevents", "-")), str(found.get("nfiles", "-"))]))
PYEOF
    done
done
exit $rc
