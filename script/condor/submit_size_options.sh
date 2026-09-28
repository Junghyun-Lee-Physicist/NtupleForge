#!/bin/bash
# =============================================================================
# submit_size_options.sh -- make a FRESH VOMS proxy, then submit the [7c]
# measurement job (size_options.sub). A new proxy every time, so an old proxy
# file that is about to expire can never be the one the job gets.
#
#   /bin/bash script/condor/submit_size_options.sh      # asks for the grid pass phrase
#
# Run on the lxplus EL9 HOST (condor_submit is not inside cmssw-el8); the
# current directory does not matter. The proxy goes to ~/private (AFS, readable
# by you only), condor copies it into the job (x509userproxy in the .sub).
# The job itself sets up CMSSW with cmsenv inside the CMSSW el8 image, see
# size_options_job.sh. ASCII only.
# =============================================================================
set -u
NF="$(cd "$(dirname "$0")/../.." && pwd)"
PROXY="${HOME}/private/x509up_ntupleforge"
LOGDIR="${HOME}/condor_size_options"
IMG="/cvmfs/unpacked.cern.ch/registry.hub.docker.com/cmssw/el8:x86_64"

command -v condor_submit >/dev/null 2>&1 || { echo "FATAL: no condor_submit here; run this on the lxplus host, not inside cmssw-el8"; exit 2; }
[ -d "${IMG}" ] || { echo "FATAL: the CMSSW el8 image is not visible: ${IMG}"; exit 2; }
[ -f "${NF}/script/condor/size_options.sub" ] || { echo "FATAL: no size_options.sub under ${NF}"; exit 2; }
mkdir -p "${HOME}/private" "${LOGDIR}"

voms-proxy-init --voms cms --rfc --valid 96:00 --out "${PROXY}" || { echo "FATAL: voms-proxy-init failed, nothing submitted"; exit 3; }
export X509_USER_PROXY="${PROXY}"
echo "proxy : ${PROXY}  ($(voms-proxy-info -file "${PROXY}" -timeleft 2>/dev/null) s left)"
echo "repo  : ${NF}  ($(git -C "${NF}" --no-optional-locks log --oneline -1 2>/dev/null))"
echo "logs  : ${LOGDIR}"

cd "${NF}" || exit 2
export PWD="${NF}"   # the .sub passes $ENV(PWD) to the job as the NtupleForge directory
condor_submit script/condor/size_options.sub
