#!/usr/bin/env bash
# =============================================================================
#  das_discover_run3.sh -- find the Run 3 (13.6 TeV) NanoAOD datasets by FAMILY
# =============================================================================
#  Run 3 primary dataset names differ from Run 2 (TTto4Q instead of TTToHadronic,
#  QCD-4Jets_HT-* instead of QCD_HT*, Wto2Q-3Jets_HT-* instead of WJetsToQQ_HT-*,
#  ...) and we do NOT guess them (the das_scan.sh rule: only DAS decides what
#  exists). This script asks DAS one wildcard per physics FAMILY per era and
#  prints every dataset it finds, so that script/samples_registry_run3.txt can
#  be filled from facts. It is the Run 3 counterpart of "--probe": cheap
#  (a few dozen queries), no summaries, no event counts -- das_scan.sh does that
#  afterwards on the registry it produced.
#
#  USAGE (lxplus HOST or container, valid proxy; dasgoclient from cvmfs)
#    bash script/das_discover_run3.sh --era 2022 --nano v15 \
#         --out script/das_discover_2022_v15_$(date +%Y%m%d_%H%M).log
#    bash script/das_discover_run3.sh --era 2023BPix --nano v15 --mc-only
#    bash script/das_discover_run3.sh --era 2024 --nano v15 --data-only
#
#  Campaign prefixes are the same table as das_scan.sh's era_table (re-declared
#  here to stay self-contained). 2025 has no MC campaign yet: PPD (Run3 2025
#  Summary Table, 20 Jan 2026) says use RunIII2024Summer24 MC, so --era 2025
#  scans Summer24 MC + Run2025 PromptReco data. 2024 = Summer24 MC + the
#  Run2024*-MINIv6NANOv15-v* re-processing (both verified from a reference
#  analysis list, 2026-09-07). Prompt data: keep EVERY -vN of an era (PPD note).
#
#  OUTPUT (machine-readable; commentary starts with '###')
#    META|era=<ERA>|nano=<VER>|mc_campaign=<PREFIX>|data_runera=<R>|data_proc=<P>|utc=<ISO8601>
#    HIT|MC|<family>|<use>|<dataset>              one line per dataset found
#    HIT|DATA|<pd>|<use>|<dataset>
#    NONE|MC|<family>|<pattern>                    the wildcard found nothing
#    CAMP|DATA|<pd>|<campaign>                     every campaign of that PD (proc-string discovery)
#  <use> is the ttHH-workstream tag proposed for the family: had (hadronic
#  channel background/signal), lep (leptonic-selection data/MC test: DY, W->lnu,
#  Muon/EGamma PDs) or had,lep. It is a PROPOSAL -- the registry decides.
# =============================================================================
set -u

ERA=""; NANO="v15"; OUT=""; MC_ONLY=0; DATA_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --era)  ERA="${2:-}";  shift 2 ;;
    --nano) NANO="${2:-}"; shift 2 ;;
    --out)  OUT="${2:-}";  shift 2 ;;
    --mc-only)   MC_ONLY=1;   shift ;;
    --data-only) DATA_ONLY=1; shift ;;
    -h|--help) sed -n '/^#/!q;p' "$0" | tail -n +2 | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    *) echo "FATAL: unknown argument '$1'" >&2; exit 3 ;;
  esac
done
[[ -z "$ERA" ]] && { echo "FATAL: --era is required (2022 2022EE 2023 2023BPix 2024 2025)" >&2; exit 3; }

case "$ERA" in
  2022)     MC_CAMPAIGN="Run3Summer22NanoAOD${NANO}";       DATA_RUNERA="Run2022"; DATA_PROC="NanoAOD${NANO}" ;;
  2022EE)   MC_CAMPAIGN="Run3Summer22EENanoAOD${NANO}";     DATA_RUNERA="Run2022"; DATA_PROC="NanoAOD${NANO}" ;;
  2023)     MC_CAMPAIGN="Run3Summer23NanoAOD${NANO}";       DATA_RUNERA="Run2023"; DATA_PROC="NanoAOD${NANO}" ;;
  2023BPix) MC_CAMPAIGN="Run3Summer23BPixNanoAOD${NANO}";   DATA_RUNERA="Run2023"; DATA_PROC="NanoAOD${NANO}" ;;
  2024)     MC_CAMPAIGN="RunIII2024Summer24NanoAOD${NANO}"; DATA_RUNERA="Run2024"; DATA_PROC="MINIv6NANO${NANO}" ;;
  2025)     MC_CAMPAIGN="RunIII2024Summer24NanoAOD${NANO}"; DATA_RUNERA="Run2025"; DATA_PROC="PromptReco" ;;   # no 2025 MC yet: PPD says use Summer24
  *) echo "FATAL: not a Run 3 era: $ERA" >&2; exit 3 ;;
esac

DAS="$(command -v dasgoclient || echo /cvmfs/cms.cern.ch/common/dasgoclient)"
[[ -x "$DAS" ]] || { echo "FATAL: dasgoclient not found"; exit 1; }
voms-proxy-info -exists 2>/dev/null || { echo "FATAL: no valid VOMS proxy"; exit 2; }
if [[ -n "$OUT" ]]; then mkdir -p "$(dirname "$OUT")"; exec > >(tee "$OUT") 2>&1; fi

echo "### das_discover_run3.sh era=$ERA nano=$NANO  $(date -u +%FT%TZ)"
echo "META|era=${ERA}|nano=${NANO}|mc_campaign=${MC_CAMPAIGN}|data_runera=${DATA_RUNERA}|data_proc=${DATA_PROC}|utc=$(date -u +%FT%TZ)"

# family | proposed use | primary wildcard(s) (space separated)
# Wildcards are PREFIXES on purpose: Summer22/23 wrote QCD-4Jets_HT-200to400 and
# TTHto2B_M-125, Summer24 moved to the Bin-/Par-/Fil- convention
# (QCD-4Jets_Bin-HT-..., TTH-Hto2B_Par-M-125, DYto2E-2Jets_Bin-0J-MLL-50 -- seen
# in a 2024 reference list, 2026-09-07). A prefix catches both spellings; the
# registry step drops what does not belong.
# DAS wildcards are CASE-SENSITIVE (DBS LIKE): TT4b* did NOT match the real
# Summer24 name TT4B_TuneCP5_13p6TeV_madgraph-pythia8 (missed on 2026-09-07,
# found 2026-09-10). Run 3 names spell b-quarks as 4B / BB (TTBBto4Q,
# TTHH-HHto4B) -- list both spellings whenever a family can carry one.
# TTtoL* (2026-09-11) catches the charge-split Sherpa names TTtoLminusNu2Q /
# TTtoLplusNu2Q / TTtoLminusNuQ that TTtoLNu2Q* does not.
# The case-proof way is script/das_inventory.sh: dump the whole campaign once
# and match locally, case-insensitively; use this script for the quick look.
MC_FAMILIES=(
  "signal_ttHH     had      TTHH*"
  "ttbar           had      TTto4Q* TTtoLNu2Q* TTtoL* TTto2L2Nu*"
  "ttbb            had      TTbb* TTBB*"
  "qcd_ht          had      QCD-4Jets* QCD_HT* QCD_Bin-HT*"
  "qcd_pt          had      QCD_PT-* QCD_Bin-PT*"
  "ttH             had      TTH* ttH*"
  "tH              had      THQ* THW* TQ*H* TW*H*"
  "ttV             had      TTZ* TTLL* TTLNu* TTW* TTNuNu*"
  "ttVV_4top       had      TTWW* TTWZ* TTZZ* TTWH* TTZH* TTTT* TTTW* TT4b* TT4B* TTbbbb* TTBBBB*"
  "singletop       had      TBbarQ* TbarBQ* TWminus* TbarWplus* TBbarto* TbarBto* ST_*"
  "diboson         had      WW* WZ* ZZ*"
  "vjets_qq        had      Wto2Q* Zto2Q*"
  "wjets_lnu       lep      WtoLNu*"
  "dy_ll           lep      DYto2L* DYto2Mu* DYto2E* DYto2Tau*"
)
DATA_PDS=(
  "JetMET   had"      "JetMET0  had"      "JetMET1  had"      "JetHT    had"
  "BTagMu   had"
  "Muon     had,lep"  "Muon0    had,lep"  "Muon1    had,lep"  "SingleMuon had,lep"
  "EGamma   lep"      "EGamma0  lep"      "EGamma1  lep"
)

if [[ $DATA_ONLY -eq 0 ]]; then
  echo ""
  echo "### MC  campaign=/${MC_CAMPAIGN}*/NANOAODSIM  -- flavour re-productions (JMENano/BTVNano/...) included; filter later"
  for row in "${MC_FAMILIES[@]}"; do
    # shellcheck disable=SC2086
    set -- $row
    fam="$1"; use="$2"; shift 2
    for pat in "$@"; do
      q="/${pat}/${MC_CAMPAIGN}*/NANOAODSIM"
      mapfile -t hits < <("$DAS" -query="dataset=${q}" 2>/dev/null | sort -u)
      if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
        echo "NONE|MC|${fam}|${q}"
      else
        for ds in "${hits[@]}"; do [[ -n "$ds" ]] && echo "HIT|MC|${fam}|${use}|${ds}"; done
      fi
    done
  done
fi

if [[ $MC_ONLY -eq 0 ]]; then
  echo ""
  echo "### DATA  ${DATA_RUNERA}*  -- first every NanoAOD campaign of the PD (proc-string discovery), then the ${DATA_PROC}* match"
  for row in "${DATA_PDS[@]}"; do
    # shellcheck disable=SC2086
    set -- $row
    pd="$1"; use="$2"
    "$DAS" -query="dataset=/${pd}/${DATA_RUNERA}*/NANOAOD" 2>/dev/null \
      | awk -F/ -v pd="$pd" 'NF>=4 && $3!="" {print "CAMP|DATA|" pd "|" $3}' | sort -u
    mapfile -t hits < <("$DAS" -query="dataset=/${pd}/${DATA_RUNERA}*-${DATA_PROC}*/NANOAOD" 2>/dev/null | sort -u)
    if [[ ${#hits[@]} -eq 0 || -z "${hits[0]:-}" ]]; then
      echo "NONE|DATA|${pd}|/${pd}/${DATA_RUNERA}*-${DATA_PROC}*/NANOAOD"
    else
      for ds in "${hits[@]}"; do [[ -n "$ds" ]] && echo "HIT|DATA|${pd}|${use}|${ds}"; done
    fi
  done
fi

echo ""
echo "### DONE era=$ERA nano=$NANO  $(date -u +%FT%TZ)"
echo "### next: fill script/samples_registry_run3.txt from the HIT| lines (drop JMENano/BTVNano/PFNano flavours),"
echo "###       then: bash script/das_scan.sh --era $ERA --nano $NANO --registry script/samples_registry_run3.txt --workstream had --out ..."
