#!/bin/bash
# =============================================================================
# size_options_job.sh -- HTCondor payload of script/condor/size_options.sub:
# the [7c] output-volume measurement (script/size_options.py) as ONE batch job,
# so it no longer depends on an ssh or tmux session (2026-09-28: the interactive
# run died twice with the ssh connection).
#
# Arguments (set by the .sub): $1 = the NtupleForge directory on AFS,
#                              $2 = the submitter's HOME (dasgoclient keeps its
#                                   cache there; getenv is False).
# Runs inside the CMSSW el8 image (MY.SingularityImage in the .sub) and sets the
# release up from cvmfs itself, like TTHHGenCategoryTools' condor jobs.
# Writes: script/runlogs/ on AFS (runlog.sh logs, LEDGER.tsv, the two TSVs;
# small text only). Scratch ROOT copies go to the worker's local disk.
# Exit: 0 all measured and projected | 1 something failed after one retry pass
#       | 11-14 setup problems (message in the .out).
# ASCII only.
# =============================================================================
NF="$1"
[ -n "$2" ] && export HOME="$2"
echo "[job] host=$(hostname) start=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "[job] os=$(cat /etc/redhat-release 2>/dev/null || echo unknown)"
echo "[job] NtupleForge=${NF}  HOME=${HOME:-unset}  X509_USER_PROXY=${X509_USER_PROXY:-unset}"
[ -d "${NF}/script" ] || { echo "[job] FATAL: no NtupleForge directory at '${NF}'"; exit 11; }
[ -r "${X509_USER_PROXY:-/nonexistent}" ] || { echo "[job] FATAL: no readable grid proxy (x509userproxy in the .sub)"; exit 12; }

# cmsset_default.sh is not 'set -u' clean, so no set -u here
source /cvmfs/cms.cern.ch/cmsset_default.sh
arch="$(ls -d "${NF}/../../.SCRAM"/*_amd64_* 2>/dev/null | head -1)"   # the release area's own arch
[ -n "${arch}" ] && export SCRAM_ARCH="$(basename "${arch}")"
cd "${NF}/.." || exit 11
eval "$(scramv1 runtime -sh)"   # cmsenv; eval of nothing succeeds, hence the check below
if [ -z "${CMSSW_BASE:-}" ] || ! command -v dasgoclient >/dev/null 2>&1 || ! python3 -c "import ROOT" >/dev/null 2>&1; then
  echo "[job] FATAL: no CMSSW environment with PyROOT and dasgoclient in $(pwd) (SCRAM_ARCH=${SCRAM_ARCH:-unset})"
  exit 13
fi
cd "${NF}" || exit 11
export TMPDIR="${_CONDOR_SCRATCH_DIR:-${TMPDIR:-/tmp}}"   # scratch copies on the worker, not on AFS
echo "[job] CMSSW_BASE=${CMSSW_BASE}  TMPDIR=${TMPDIR}  git=$(git --no-optional-locks rev-parse --short HEAD 2>/dev/null)"

mock="$(python3 script/test_size_options_mock.py | tail -1)"
echo "[job] mock test: ${mock}"
case "${mock}" in
  "RESULT: ALL PASS"*) ;;
  *) echo "[job] FATAL: the offline test of size_options.py does not pass here; nothing measured"; exit 14 ;;
esac

# 2018UL first (its decision comes first), then everything (measured rows are reused)
O=""
for k in MC:TTbar_Hadronic MC:TTbar_SemiLep MC:TTbar_DiLep MC:ST_t_top MC:QCD_HT300to500 MC:QCD_HT500to700 \
         MC:QCD_HT700to1000 MC:QCD_HT1000to1500 Data:JetHT_Run2018A Data:JetHT_Run2018D Data:SingleMuon_Run2018D; do
  O="${O} --only 2018UL:${k}"
done
/bin/bash script/runlog.sh size_options_2018 -- python3 script/size_options.py ${O}
/bin/bash script/runlog.sh size_options -- python3 script/size_options.py
rc=$?

# a failed sample has no row, so a plain rerun measures only those; throttled
# reads are often gone after a while, and another redirector may pick another replica
if [ ${rc} -ne 0 ]; then
  echo "[job] rc=${rc}: retry pass in ${SIZE_OPTIONS_RETRY_SLEEP:-600} s (only the failed samples are measured again)"
  sleep "${SIZE_OPTIONS_RETRY_SLEEP:-600}"
  /bin/bash script/runlog.sh size_options_retry -- python3 script/size_options.py
  rc=$?
fi
if [ ${rc} -ne 0 ]; then
  echo "[job] rc=${rc}: second retry through the European redirector"
  /bin/bash script/runlog.sh size_options_retry_eu -- python3 script/size_options.py --redirector root://xrootd-cms.infn.it/
  rc=$?
fi
echo "[job] end=$(date -u +%Y-%m-%dT%H:%M:%SZ) rc=${rc}"
exit ${rc}
