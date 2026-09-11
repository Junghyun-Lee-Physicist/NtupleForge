#!/bin/bash
# =============================================================================
#  das_inventory.sh -- dump EVERY dataset of a campaign (any DBS status) into a
#  TSV with status / events / files / size / creation date, then match our
#  registry and free-text tokens against it LOCALLY and CASE-INSENSITIVELY.
#
#  Why (2026-09-10): das_discover_run3.sh asked DAS for TT4b*/TTbbbb* and got
#  NONE, but the sample exists as TT4B_TuneCP5_13p6TeV_madgraph-pythia8 -- DAS
#  wildcards are case-sensitive. Asking DAS for the whole campaign once and
#  doing the matching here removes that failure mode, and the same pass records
#  the numbers we kept looking up by hand (nevents, nfiles, size, status).
#
#  Usage (lxplus, OUTSIDE the cmssw container, with a voms proxy; on shells
#  where 'bash' is aliased use /bin/bash):
#    /bin/bash script/das_inventory.sh --campaign '<processed-dataset pattern>' [options]
#
#  Required
#    --campaign PAT     processed-dataset pattern, e.g.
#                       'RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2*'
#                       'RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1*'
#                       (the trailing * catches -vN and _ext1-vN; flavour re-productions
#                        such as JMENanoV15_150X... do NOT match because their
#                        processed string starts differently)
#  Options
#    --tier TIER        data tier (default NANOAODSIM)
#    --tag TAG          short tag for the output file name (default: derived from campaign)
#    --out FILE         TSV path (default script/das_inventory_<tag>_<YYYYmmdd_HHMM>.tsv)
#    --registry FILE    samples_registry(_run3).txt: every MC PRIMARY is looked up
#                       case-insensitively -> EXACT / CASE_ONLY / NOT_FOUND report
#    --grep TOKENS      comma-separated substrings, matched case-insensitively
#                       against the PRIMARY names (e.g. tt4b,tthh,sherpa,2jets)
#    --details MODE     which datasets get the per-dataset status/summary query:
#                       matching (default: only registry/grep matches), all, none
#    --limit N          stop after N datasets (smoke test)
#    --keep-flavours    do not drop JMENano/BTVNano/... names from the match report
#
#  Output
#    <out>              TSV: dataset  primary  processed  tier  status  nevents  nfiles  size_TB  created
#                       (status/nevents/... are '-' for datasets without a details query)
#    <out>.names.txt    plain list of every dataset the campaign query returned
#    <out>.match.txt    the registry / grep report (also printed)
#
#  DAS calls
#    list    : dasgoclient -query "dataset status=* dataset=/*/<campaign>/<tier>"
#              (falls back to 52 first-letter queries /A*/../z*/ if DAS refuses /*/)
#    details : dasgoclient -query "dataset status=* dataset=<ds>" -json
#              and, when nevents is missing there, "summary dataset=<ds>"
# =============================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMPAIGN="" ; TIER="NANOAODSIM" ; TAG="" ; OUT="" ; REGISTRY="" ; GREP_TOKENS=""
DETAILS="matching" ; LIMIT=0 ; KEEP_FLAVOURS=0

usage () { sed -n '/^# =====/,/^# =====/p' "$0" | sed -n '2,200p' | sed 's/^# \{0,2\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --campaign)      CAMPAIGN="$2"; shift 2 ;;
    --tier)          TIER="$2"; shift 2 ;;
    --tag)           TAG="$2"; shift 2 ;;
    --out)           OUT="$2"; shift 2 ;;
    --registry)      REGISTRY="$2"; shift 2 ;;
    --grep)          GREP_TOKENS="$2"; shift 2 ;;
    --details)       DETAILS="$2"; shift 2 ;;
    --limit)         LIMIT="$2"; shift 2 ;;
    --keep-flavours) KEEP_FLAVOURS=1; shift ;;
    -h|--help)       usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage; exit 2 ;;
  esac
done
[[ -n "$CAMPAIGN" ]] || { echo "--campaign is required" >&2; exit 2; }
command -v dasgoclient >/dev/null || { echo "dasgoclient not in PATH (source the CMS environment / run outside the container)" >&2; exit 3; }
case "$DETAILS" in matching|all|none) ;; *) echo "--details must be matching|all|none" >&2; exit 2 ;; esac

STAMP=$(date +%Y%m%d_%H%M)
[[ -n "$TAG" ]] || TAG=$(echo "$CAMPAIGN" | sed 's/[^A-Za-z0-9]/_/g; s/__*/_/g; s/_$//' | cut -c1-40)
[[ -n "$OUT" ]] || OUT="${SCRIPT_DIR}/das_inventory_${TAG}_${STAMP}.tsv"
NAMES="${OUT}.names.txt" ; MATCH="${OUT}.match.txt"

echo "### das_inventory.sh  $(date '+%Y-%m-%d %H:%M %Z')"
echo "### campaign=${CAMPAIGN}  tier=${TIER}  details=${DETAILS}  registry=${REGISTRY:-none}  grep=${GREP_TOKENS:-none}"
echo "### out=${OUT}"

# ---- 1. dataset list ---------------------------------------------------------
list_query () { dasgoclient -query "dataset status=* dataset=/$1/${CAMPAIGN}/${TIER}" 2>/dev/null; }
: > "$NAMES"
list_query '*' | grep '^/' | sort -u > "$NAMES" || true
if [[ ! -s "$NAMES" ]]; then
  echo "### /*/ query returned nothing (DAS may refuse a wildcard primary) -> 52 first-letter queries"
  for c in A B C D E F G H I J K L M N O P Q R S T U V W X Y Z a b c d e f g h i j k l m n o p q r s t u v w x y z; do
    list_query "${c}*" | grep '^/'
  done | sort -u > "$NAMES"
fi
NTOT=$(wc -l < "$NAMES" | tr -d ' ')
echo "### datasets listed: ${NTOT}"
[[ "$NTOT" -gt 0 ]] || { echo "### nothing found -- check the campaign pattern (DAS is case-sensitive here too)"; exit 4; }

# ---- 2. decide which datasets get a details query ---------------------------
# match_primary.py: prints MATCH lines for registry primaries and grep tokens,
# plus the list of datasets that need details. All comparisons lower-cased.
python3 - "$NAMES" "$REGISTRY" "$GREP_TOKENS" "$DETAILS" "$KEEP_FLAVOURS" "$MATCH" > "${OUT}.details.list" <<'PYEOF'
import sys, re
names_f, registry, tokens, details, keep_flav, match_f = sys.argv[1:7]
flav = re.compile(r"(JMENano|BTVNano|PFNano|EGMNano|MUOPOG|FS_|FSUL|NoPU|FlatPU|EpsilonPU|PUFor|_pilot|mg35x)", re.I)
rows = []
for line in open(names_f):
    ds = line.strip()
    if not ds.startswith("/"): continue
    parts = ds.split("/")
    if len(parts) < 4: continue
    rows.append((ds, parts[1], parts[2]))
report = []
need = set()
# registry primaries
if registry:
    prims = []
    for line in open(registry):
        if not line.strip() or line.startswith("#"): continue
        f = line.split()
        if len(f) >= 3 and f[0] == "MC":
            prims.append((f[1], f[2]))
    for key, prim in prims:
        exact = [r[0] for r in rows if r[1] == prim]
        ci    = [r[0] for r in rows if r[1].lower() == prim.lower() and r[1] != prim]
        if not keep_flav == "1":
            exact = [d for d in exact if not flav.search(d.split("/")[2])]
            ci    = [d for d in ci if not flav.search(d.split("/")[2])]
        if exact:
            report.append("EXACT|%s|%s|%d" % (key, prim, len(exact)))
            need.update(exact)
        elif ci:
            report.append("CASE_ONLY|%s|%s|%s" % (key, prim, ";".join(sorted(set(d.split("/")[1] for d in ci)))))
            need.update(ci)
        else:
            # loose hint: primaries sharing the first 4 letters of the key, case-insensitive
            stem = re.sub(r"[^A-Za-z0-9]", "", key)[:4].lower()
            hint = sorted(set(r[1] for r in rows if stem and r[1].lower().startswith(stem)))
            report.append("NOT_FOUND|%s|%s|hint:%s" % (key, prim, ";".join(hint[:8])))
# grep tokens
for tok in [t.strip().lower() for t in tokens.split(",") if t.strip()]:
    hits = sorted(set(r[1] for r in rows if tok in r[1].lower()))
    report.append("GREP|%s|%d|%s" % (tok, len(hits), ";".join(hits)))
    need.update(r[0] for r in rows if tok in r[1].lower())
with open(match_f, "w") as fo:
    for l in report: fo.write(l + "\n")
for l in report: print(l, file=sys.stderr)
if details == "all":
    need = set(r[0] for r in rows)
elif details == "none":
    need = set()
for ds in sorted(need): print(ds)
PYEOF
NDET=$(wc -l < "${OUT}.details.list" | tr -d ' ')
echo "### match report written: ${MATCH}"
echo "### datasets to query for details: ${NDET}"

# ---- 3. details per dataset --------------------------------------------------
printf 'dataset\tprimary\tprocessed\ttier\tstatus\tnevents\tnfiles\tsize_TB\tcreated\n' > "$OUT"
n=0
while read -r ds; do
  [[ -n "$ds" ]] || continue
  n=$((n+1)); [[ "$LIMIT" -gt 0 && $n -gt "$LIMIT" ]] && break
  js=$(dasgoclient -query "dataset status=* dataset=${ds}" -json 2>/dev/null)
  sm=""
  row=$(python3 - "$ds" "$js" <<'PYEOF'
import sys, json, datetime
ds, raw = sys.argv[1], sys.argv[2]
want = {"status": ("status", "dataset_access_type"), "nevents": ("nevents", "num_event"),
        "nfiles": ("nfiles", "num_file"), "size": ("size", "file_size", "dataset_size"),
        "created": ("creation_time", "creation_date", "create_time")}
found = {}
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            for name, keys in want.items():
                if k in keys and name not in found and v not in (None, "", 0, "0"):
                    found[name] = v
            walk(v)
    elif isinstance(o, list):
        for x in o: walk(x)
try:
    walk(json.loads(raw) if raw.strip() else [])
except Exception:
    pass
cr = found.get("created", "-")
try:
    cr = datetime.datetime.utcfromtimestamp(int(cr)).strftime("%Y-%m-%d")
except Exception:
    pass
size = found.get("size", "-")
try: size = "%.3f" % (float(size) / 1e12)
except Exception: pass
print("\t".join(str(x) for x in [found.get("status", "-"), found.get("nevents", "-"),
                                   found.get("nfiles", "-"), size, cr]))
PYEOF
)
  status=$(echo "$row" | cut -f1); nev=$(echo "$row" | cut -f2)
  if [[ "$nev" == "-" ]]; then
    sm=$(dasgoclient -query "summary dataset=${ds}" -json 2>/dev/null)
    row2=$(python3 - "$sm" <<'PYEOF'
import sys, json
raw = sys.argv[1]
nev = nf = size = "-"
try:
    for rec in json.loads(raw):
        for s in rec.get("summary", []):
            nev = s.get("nevents", nev); nf = s.get("nfiles", nf); size = s.get("file_size", size)
except Exception:
    pass
try: size = "%.3f" % (float(size) / 1e12)
except Exception: pass
print("%s\t%s\t%s" % (nev, nf, size))
PYEOF
)
    nev=$(echo "$row2" | cut -f1); nf=$(echo "$row2" | cut -f2); sz=$(echo "$row2" | cut -f3); cr=$(echo "$row" | cut -f5)
    row=$(printf '%s\t%s\t%s\t%s\t%s' "$status" "$nev" "$nf" "$sz" "$cr")
  fi
  prim=$(echo "$ds" | cut -d/ -f2); proc=$(echo "$ds" | cut -d/ -f3); tier=$(echo "$ds" | cut -d/ -f4)
  printf '%s\t%s\t%s\t%s\t%s\n' "$ds" "$prim" "$proc" "$tier" "$row" >> "$OUT"
  echo "DS|${ds}|${row//$'\t'/|}"
done < "${OUT}.details.list"
rm -f "${OUT}.details.list"

# datasets without details still go into the TSV (names only) so the file is complete
python3 - "$NAMES" "$OUT" <<'PYEOF'
import sys
names_f, out = sys.argv[1], sys.argv[2]
have = set(l.split("\t")[0] for l in open(out).read().splitlines()[1:])
with open(out, "a") as fo:
    for line in open(names_f):
        ds = line.strip()
        if ds and ds not in have:
            p = ds.split("/")
            fo.write("\t".join([ds, p[1], p[2], p[3], "-", "-", "-", "-", "-"]) + "\n")
PYEOF
echo "### done: $(($(wc -l < "$OUT") - 1)) rows in ${OUT}"
