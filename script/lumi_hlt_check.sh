#!/bin/bash
# lumi_hlt_check.sh -- golden-JSON luminosity per era and the effective (prescale-weighted) luminosity of HLT paths,
# with brilcalc, for one data-taking year. Read-only: writes brilcalc's full output only under a temporary directory.
#
# Why: the analyzer's 2024 normalization must be the luminosity of the runs we actually processed (eras C-I; the
# golden JSON also covers 2024B), and the 2024 hadronic trigger OR may only use paths that were unprescaled
# (tempTTHH docs/PLAN_v15_2018UL_2024.md section 9, Stage 0, decision D4). Branch presence in NanoAOD says that a path
# was in the menu, not that it was unprescaled.
#
# Usage (lxplus, outside the container, no proxy needed):
#   /bin/bash script/lumi_hlt_check.sh                       # 2024 defaults below
#   /bin/bash script/lumi_hlt_check.sh --json FILE --eras "C:379412:380252 D:380253:380947" --paths "HLT_PFHT1050_v*"
#   /bin/bash script/lumi_hlt_check.sh --dry-run             # print the brilcalc commands only
# Options:
#   --json FILE       golden JSON (default: the 2024 golden JSON on EOS, below)
#   --normtag FILE    repeatable; default: normtag_BRIL.json and normtag_PHYSICS.json, those that exist
#   --eras "L:B:E .." label:first_run:last_run per era (default: 2024 C-I, NtupleForge docs/ttHH/03_run3_plan.md row 2)
#   --paths "P .."    brilcalc --hltpath patterns, one call each (default: HLT_PFHT*  HLT_IsoMu2*  HLT_Ele30_WPTight_Gsf_v*)
#   --hlt-normtag F   normtag for the --hltpath calls (default: the first --normtag)
#   --dry-run         print what would run, run nothing
# Environment: LUMI_NT_DIR (normtag directory), LUMI_BRILWS_ENV (env file that defines brilcalc; default the LUM POG
#   brilws-docker one), LUMI_BRILCONDA_BIN (fallback bin directory). brilcalc reads a copy of the JSON in the work directory.
# Output: '== <what>' header lines, then brilcalc's own summary block (from its 'Summary' line to the end, lines cut at
#   400 characters) for each call; JSON|..., NORMTAG|..., ENV|... fact lines; ERR|... for a call that failed;
#   HLTSUM|<normtag>|<path>|versions=|recorded=|of_eras_total= per HLT path: brilcalc lists every path VERSION on its own
#   row and each version covers only part of the year, so the versions are summed and divided by the recorded lumi of the
#   era range (same normtag). of_eras_total ~ 1: never prescaled in those runs; < 1: prescaled at some point, or the path
#   was added (or removed) during the year -- look at that path era by era before concluding.
# Exit 0 all calls ran, 2 setup problem, 3 at least one brilcalc call failed.
set -u
set -f   # no pathname expansion: the --hltpath patterns contain '*'
JSON=/eos/user/c/cmsdqm/www/CAF/certification/Collisions24/Cert_Collisions2024_378981_386951_Golden.json
NT_DIR=${LUMI_NT_DIR:-/cvmfs/cms-bril.cern.ch/cms-lumi-pog/Normtags}
BRILWS_ENV=${LUMI_BRILWS_ENV:-/cvmfs/cms-bril.cern.ch/cms-lumi-pog/brilws-docker/brilws-env}
BRILCONDA_BIN=${LUMI_BRILCONDA_BIN:-/cvmfs/cms-bril.cern.ch/brilconda310/bin}
NORMTAGS=()
ERAS="C:379412:380252 D:380253:380947 E:380948:381943 F:381944:383779 G:383780:385813 H:385814:386408 I:386409:387121"
PATHS="HLT_PFHT* HLT_IsoMu2* HLT_Ele30_WPTight_Gsf_v*"
HLT_NT=""
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON="$2"; shift 2 ;;
    --normtag) NORMTAGS+=("$2"); shift 2 ;;
    --eras) ERAS="$2"; shift 2 ;;
    --paths) PATHS="$2"; shift 2 ;;
    --hlt-normtag) HLT_NT="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "ERR|unknown argument $1"; exit 2 ;;
  esac
done
if [ ${#NORMTAGS[@]} -eq 0 ]; then
  for f in normtag_BRIL.json normtag_PHYSICS.json; do [ -f "$NT_DIR/$f" ] && NORMTAGS+=("$NT_DIR/$f"); done
fi
echo "== normtag directory $NT_DIR"
ls -l "$NT_DIR" 2>&1 | sed 's/^/DIR|/' | head -40
[ ${#NORMTAGS[@]} -gt 0 ] || { echo "ERR|no normtag found under $NT_DIR (pass --normtag)"; exit 2; }
for f in "${NORMTAGS[@]}"; do
  if [ -f "$f" ]; then echo "NORMTAG|$f|present|bytes=$(stat -c %s "$f")|mtime=$(date -u -r "$f" +%Y-%m-%dT%H:%M:%SZ)"; else echo "ERR|normtag $f missing"; exit 2; fi
done
[ -n "$HLT_NT" ] || HLT_NT="${NORMTAGS[0]}"

echo "== golden JSON directory $(dirname "$JSON")"
ls -l "$(dirname "$JSON")" 2>&1 | sed 's/^/DIR|/' | head -40
[ -f "$JSON" ] || { echo "ERR|golden JSON $JSON not readable (EOS mounted? on lxplus /eos/user is)"; exit 2; }
python3 - "$JSON" <<'EOF'
import hashlib, json, os, sys
p = sys.argv[1]
b = open(p, "rb").read()
d = json.loads(b)
runs = sorted(int(r) for r in d)
nls = sum(hi - lo + 1 for r in d for lo, hi in d[r])
print("JSON|%s|bytes=%d|md5=%s|runs=%d|first=%d|last=%d|ls=%d" % (p, len(b), hashlib.md5(b).hexdigest(), len(runs),
                                                                  runs[0], runs[-1], nls))
EOF

if [ $DRY -eq 0 ]; then
  shopt -s expand_aliases   # an env file may define brilcalc as an alias; run() below is parsed after this block
  if ! command -v brilcalc >/dev/null 2>&1; then
    if [ -f "$BRILWS_ENV" ]; then
      # third-party file: no nounset/noglob while it is read, and nounset stays off (its alias or function may use unset
      # variables when it runs); noglob comes back because the --hltpath patterns below contain '*'
      set +u +f
      # shellcheck disable=SC1090
      source "$BRILWS_ENV"
      set -f
      how="env:$BRILWS_ENV"
    else
      export PATH=$HOME/.local/bin:$BRILCONDA_BIN:$PATH; how="path:$BRILCONDA_BIN"
    fi
  else
    how=PATH
  fi
  if ! command -v brilcalc >/dev/null 2>&1; then
    echo "ERR|brilcalc not found (tried PATH, $BRILWS_ENV, $BRILCONDA_BIN). Put brilcalc on PATH in this shell, or give the env file that defines it as LUMI_BRILWS_ENV=<file>, then rerun."
    exit 2
  fi
  v=$(brilcalc --version 2>&1 | tail -1)
  echo "ENV|brilcalc=$v|setup=$how"
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/lumi_hlt_check.XXXXXX")
# brilcalc may run inside a container (brilws-docker) that does not see /eos: give it a copy under the work directory
cp "$JSON" "$work/golden.json" || { echo "ERR|cannot copy $JSON to $work"; exit 2; }
GJ=$work/golden.json
fails=0
OUT=""
run() {  # $1 = header, rest = brilcalc arguments; sets OUT to the file with brilcalc's full output
  local head="$1"; shift
  echo "== $head"
  echo "CMD|brilcalc $*"
  OUT=""
  [ $DRY -eq 1 ] && return 0
  OUT="$work/$(echo "$head" | tr -c 'A-Za-z0-9_.-' '_').txt"
  if brilcalc "$@" > "$OUT" 2>&1; then
    sed -n '/[Ss]ummary/,$p' "$OUT" | cut -c1-400
    if ! grep -q '[Ss]ummary' "$OUT"; then echo "ERR|$head: no Summary block; last lines:"; tail -5 "$OUT" | cut -c1-400; fails=$((fails+1)); fi
  else
    echo "ERR|$head: brilcalc exit $?; last lines:"; tail -8 "$OUT" | cut -c1-400; fails=$((fails+1))
  fi
  return 0
}
recorded_of() {  # the totrecorded column (7th '|' field) of the numeric row after brilcalc's Summary line
  awk -F'|' 'f && /^\| *[0-9]/ {v=$7} /[Ss]ummary/ {f=1} END {gsub(/ /, "", v); print v}' "$1"
}
first=$(echo "$ERAS" | tr ' ' '\n' | head -1 | cut -d: -f2)
last=$(echo "$ERAS" | tr ' ' '\n' | tail -1 | cut -d: -f3)
TOT=""
for nt in "${NORMTAGS[@]}"; do
  ntn=$(basename "$nt" .json)
  run "LUMI $ntn whole-json" lumi -i "$GJ" --normtag "$nt" -u /fb
  run "LUMI $ntn eras $first-$last" lumi -i "$GJ" --normtag "$nt" -u /fb --begin "$first" --end "$last"
  [ "$nt" = "$HLT_NT" ] && [ -n "$OUT" ] && TOT=$(recorded_of "$OUT")
  for e in $ERAS; do
    IFS=: read -r lab b en <<< "$e"
    run "LUMI $ntn era $lab $b-$en" lumi -i "$GJ" --normtag "$nt" -u /fb --begin "$b" --end "$en"
  done
done
ntn=$(basename "$HLT_NT" .json)
if [ $DRY -eq 0 ] && [ -z "$TOT" ]; then
  # --hlt-normtag not among --normtag: get the era-range total with it too
  run "LUMI $ntn eras $first-$last" lumi -i "$GJ" --normtag "$HLT_NT" -u /fb --begin "$first" --end "$last"
  [ -n "$OUT" ] && TOT=$(recorded_of "$OUT")
fi
for p in $PATHS; do
  run "HLT $ntn $p eras $first-$last" lumi -i "$GJ" --normtag "$HLT_NT" -u /fb --begin "$first" --end "$last" --hltpath "$p"
  if [ -n "$OUT" ] && [ -s "$OUT" ]; then
    awk -F'|' -v tot="${TOT:-0}" -v nt="$ntn" '/[Ss]ummary/ {f=1} f && /^\| *HLT_/ {
        p = $2; gsub(/ /, "", p); sub(/_v[0-9]+$/, "", p); r = $7; gsub(/ /, "", r); s[p] += r; n[p]++ }
      END { for (k in s) printf "HLTSUM|%s|%s|versions=%d|recorded=%.4f|of_eras_total=%s\n", nt, k, n[k], s[k],
                                 (tot > 0 ? sprintf("%.4f", s[k] / tot) : "n/a") }' "$OUT" | sort
  fi
done
echo "WORKDIR|$work (full brilcalc outputs, not committed)"
[ $fails -eq 0 ] && exit 0 || exit 3
