#!/bin/bash
# =============================================================================
#  runlog.sh -- run ONE step and leave a self-describing record of it.
#
#  Why (2026-09-16): das_inventory.sh, sweep_inventories.sh and the matrix
#  script report only on stdout. What ran, when, on which git commit, with
#  which proxy/ROOT, whether it exited 0 and which files it produced lived
#  only in the terminal -- and reached the AI session as pasted text, or not
#  at all. This wrapper makes every step leave (a) a log with a header and a
#  footer and (b) one line in a ledger, both inside the repo, so "did it run
#  and did it work" is answerable from git alone.
#
#  Usage (lxplus; on shells where 'bash' is aliased use /bin/bash):
#    /bin/bash script/runlog.sh <step> -- <command> [args...]
#
#    /bin/bash script/runlog.sh ul16pre_miniaodv2 -- \
#        /bin/bash script/das_inventory.sh --tier MINIAODSIM --registry script/samples_registry.txt \
#            --tag ul16pre_miniaodv2 --campaign 'RunIISummer20UL16MiniAODAPVv2-*'
#
#  <step>  short token, [A-Za-z0-9_.-] only; becomes part of the log name.
#
#  What it leaves
#    script/runlogs/run_<step>_<UTCstamp>.log
#        header : step, start (UTC), host, user, cwd, repo, git HEAD + dirty
#                 count, the exact command, and the environment that matters
#                 (CMSSW_BASE, ROOT, dasgoclient, proxy time left)
#        body   : the command's stdout+stderr, live on the terminal too (tee)
#        footer : end (UTC), wall seconds, EXIT code, and every file under
#                 script/ and branches/ modified during the run, with sizes
#    script/runlogs/LEDGER.tsv
#        one appended line per run:
#        utc_start  step  exit  wall_s  host  git_head  log  outputs
#
#  Exit code = the command's exit code (so it can be chained with && / ||).
#
#  Credential safety (docs/03_DECISIONS.md D-2026-08-17-no-logs-in-git):
#    if the command line contains 'crab' the log is written under
#    script/runlogs/nocommit/ (gitignored) and a warning is printed. CRAB
#    transcripts embed pre-signed S3 URLs and must never reach the public repo.
#    DAS / ROOT / python steps print no credentials and their logs are small.
# =============================================================================
set -u
set -o pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage () { sed -n '2,45p' "$0" | sed 's/^# \{0,2\}//'; }

STEP=""
if [[ $# -lt 3 || "$1" == "-h" || "$1" == "--help" ]]; then usage; exit 2; fi
STEP="$1"; shift
[[ "$1" == "--" ]] || { echo "runlog.sh: expected '--' after the step name" >&2; usage; exit 2; }
shift
[[ $# -ge 1 ]] || { echo "runlog.sh: no command given" >&2; exit 2; }
[[ "$STEP" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo "runlog.sh: step must match [A-Za-z0-9_.-]+" >&2; exit 2; }

CMD=("$@")
CMDSTR="$(printf '%q ' "${CMD[@]}")"

LOGDIR="$REPO/script/runlogs"
NOCOMMIT=0
if [[ "$CMDSTR" == *crab* ]]; then
  LOGDIR="$REPO/script/runlogs/nocommit"; NOCOMMIT=1
fi
mkdir -p "$LOGDIR"

STAMP="$(date -u +%Y%m%d_%H%M%S)"
LOG="$LOGDIR/run_${STEP}_${STAMP}.log"
LEDGER="$REPO/script/runlogs/LEDGER.tsv"
MARK="$(mktemp "${TMPDIR:-/tmp}/runlog_mark.XXXXXX")"

# ---- environment facts (each guarded: absence is recorded, never fatal) -----
GIT_HEAD="n/a"; GIT_DIRTY="n/a"
if git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_HEAD="$(git -C "$REPO" --no-optional-locks rev-parse --short HEAD 2>/dev/null || echo n/a)"
  GIT_DIRTY="$(git -C "$REPO" --no-optional-locks status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')"
fi
ROOTV="$(command -v root-config >/dev/null 2>&1 && root-config --version 2>/dev/null || echo none)"
DASV="$(command -v dasgoclient >/dev/null 2>&1 && dasgoclient --version 2>/dev/null | head -1 || echo none)"
PROXY="$(command -v voms-proxy-info >/dev/null 2>&1 && voms-proxy-info -timeleft 2>/dev/null || echo none)"
HOST="$(hostname -s 2>/dev/null || hostname)"
T0=$(date +%s)

{
  echo "=== RUNLOG ================================================================"
  echo "step        : $STEP"
  echo "start_utc   : $(date -u +%FT%TZ)"
  echo "host        : $HOST   user: ${USER:-?}"
  echo "cwd         : $PWD"
  echo "repo        : $REPO"
  echo "git_head    : $GIT_HEAD   modified_tracked_files: $GIT_DIRTY"
  echo "cmd         : $CMDSTR"
  echo "CMSSW_BASE  : ${CMSSW_BASE:-<unset>}"
  echo "root        : $ROOTV"
  echo "dasgoclient : $DASV"
  echo "proxy_left_s: $PROXY"
  [[ $NOCOMMIT -eq 1 ]] && echo "NOTE        : command mentions crab -> log kept under runlogs/nocommit/ (never commit)"
  echo "==========================================================================="
} | tee "$LOG"

# ---- run --------------------------------------------------------------------
"${CMD[@]}" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}

T1=$(date +%s); WALL=$((T1 - T0))

# ---- outputs: files under script/ and branches/ newer than the start mark ----
OUTS="$(find "$REPO/script" "$REPO/branches" -type f -newer "$MARK" \
          -not -path "$LOG" -not -path "*/runlogs/*" -not -name '*.pyc' 2>/dev/null \
        | sed "s#^$REPO/##" | sort)"
rm -f "$MARK"

{
  echo "==========================================================================="
  echo "end_utc     : $(date -u +%FT%TZ)"
  echo "wall_s      : $WALL"
  echo "EXIT        : $RC"
  if [[ -n "$OUTS" ]]; then
    echo "outputs (modified during the run, under script/ and branches/):"
    while IFS= read -r f; do
      [[ -n "$f" ]] || continue
      sz=$(stat -c %s "$REPO/$f" 2>/dev/null || stat -f %z "$REPO/$f" 2>/dev/null || echo ?)
      printf '  %10s  %s\n' "$sz" "$f"
    done <<< "$OUTS"
  else
    echo "outputs     : (none under script/ or branches/)"
  fi
  echo "log         : ${LOG#$REPO/}"
  echo "=== END ==================================================================="
} | tee -a "$LOG"

# ---- ledger -----------------------------------------------------------------
if [[ $NOCOMMIT -eq 0 ]]; then
  [[ -s "$LEDGER" ]] || printf 'utc_start\tstep\texit\twall_s\thost\tgit_head\tlog\toutputs\n' > "$LEDGER"
  OUTS1="$(printf '%s' "$OUTS" | tr '\n' ';')"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$(date -u -d "@$T0" +%FT%TZ 2>/dev/null || date -u -r "$T0" +%FT%TZ)" \
    "$STEP" "$RC" "$WALL" "$HOST" "$GIT_HEAD" "${LOG#$REPO/}" "${OUTS1:-none}" >> "$LEDGER"
fi

exit "$RC"
