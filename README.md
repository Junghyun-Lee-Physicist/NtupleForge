# NtupleForge ⚒️

Utilities for running CMS **NanoAOD post-processing** without modifying the
upstream `PhysicsTools/NanoAODTools` package, plus **CRAB3** submission glue.
The current default pipeline ships **full NanoAOD unchanged** (no slim, no
skim, no extra branches); event-level analysis (including tt+jets
categorization) is done downstream in the main analyzer.

📖 **Deep documentation lives in [`docs/`](docs/)** — framework internals,
the PyROOT compat shim, and the full record of the retired categorization
pipeline. This README is only what you need to *run* the code.

- Upstream framework: <https://github.com/cms-sw/cmssw/tree/CMSSW_14_2_X/PhysicsTools/NanoAODTools>

---

## 🛠️ Setup

> **Environment:** log in to **lxplus8** (`ssh <user>@lxplus8.cern.ch`) or use
> a Singularity container (`cmssw-el8`). `CMSSW_14_2_1` requires
> **el8_amd64_gcc12**.

```bash
cmsrel CMSSW_14_2_1
cd CMSSW_14_2_1/src
cmsenv

git cms-init
git cms-addpkg PhysicsTools/NanoAODTools          # standard NanoAODTools
git clone https://github.com/Junghyun-Lee-Physicist/NtupleForge.git

scram b -j 8                                       # compile + set python paths
cd NtupleForge
```

## ⚠️ Prerequisites (before running)

```bash
cmsenv                                             # CMSSW environment
voms-proxy-init --voms cms --valid 168:00          # for remote (XRootD) files
source /cvmfs/cms.cern.ch/crab3/crab.sh            # for CRAB submission
```

---

## 🚀 Run locally

Full NanoAOD passthrough (copy input through, keep every branch):

```bash
python3 script/run_postproc.py <input.root> \
  -I modules.noop \
  -b branches/branch_keep_all.txt \
  -N 1000
```

`<input.root>` may be a local path or an XRootD URL
(`root://cms-xrd-global.cern.ch//store/...`). Process multiple files by
listing them; add `-o merged.root` to `hadd` all outputs into one file.

### Driver arguments

| Flag | Required | Description |
|---|---|---|
| `input_files` (positional) | ✓ | One or more ROOT files (XRootD or local). |
| `-I`, `--imports` | ✓ | Module list, e.g. `modules.noop` or `modules.jetsMETcut:MODULES`. |
| `-b`, `--branch-selection` | ✓ | Output keep/drop file (input is always read in full). Use `branches/branch_keep_all.txt` for passthrough. |
| `-o`, `--output-file` | | If set, `hadd` all outputs into this one file. |
| `-N`, `--max-events` | | Limit events processed (default: all). |
| `--first-entry` | | Skip the first N entries (default: 0). |

To apply a skim, swap in a cut module — see the example
[`modules/jetsMETcut.py`](modules/jetsMETcut.py). To write custom branches,
see [`docs/architecture.md`](docs/architecture.md) §4.

---

## 🦀 Run on CRAB

Jobs are defined in a YAML file under [`crabConfig/`](crabConfig/). The
`analysis_module` and `branch_file` fields are forwarded to
`run_postproc.py` (`-I` / `-b`) on the worker.

```bash
# Submit. For tasks that already exist, this AUTO-RESUBMITS their failed jobs
# (submit-vs-resubmit is decided per task by whether its CRAB project dir exists),
# so re-running the same command after a submission resubmits failures.
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml

# Explicit resubmit of failed jobs only (skips the submit path)
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml --resubmit

# Full 'crab status' for every task
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml --status

# Compact per-sample job-state report (easier to read than --status)
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml --report

# Kill all jobs in the config
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml --kill
```

`--report` queries CRAB and prints one row per sample with how many jobs are
`done` (finished) / `run` / `idle` / `transf` (transferring) / `fail` / `other`,
plus a totals row. Any CRAB state the script doesn't recognise lands in `other`
and triggers a warning naming it (add it to `REPORT_COLUMNS` /
`KNOWN_OTHER_STATES` in `crab/submit_crab.py`).

> **⚠️ Memory / walltime failures:** plain (re)submit uses **default** resources,
> so jobs that failed on memory or walltime will fail again. Resubmit those by
> hand in the project dir with raised limits, e.g.
> `crab resubmit -d <workArea>/crab_<reqName> --maxmemory=4000 --maxjobruntime=2700`.
> The submit/resubmit run prints this reminder too; see
> [`docs/troubleshooting.md`](docs/troubleshooting.md) (CRAB resubmit).

`script/parse_crab_status.py` is the offline counterpart: it summarizes an
already-saved `crab status` log (no live query); add `--show-lines` for the raw
status lines (running / transferring / failed / finished):

```bash
python3 script/parse_crab_status.py crab_status.log
python3 script/parse_crab_status.py crab_status.log --show-lines
```

> **⚠️ Output filename:** it is hardcoded in **two** places that must match —
> `crab/PSet.py` (`PoolOutputModule` fileName) and `crab/submit_crab.py`
> (`out_name`), both `slimmedNtuple.root`. Changing one without the other
> breaks CRAB stageout (exit 60302). See
> [`docs/DeveloperGuideline.md`](docs/DeveloperGuideline.md) Rule 6.

---

## 🧑‍💻 Developing

Editing this code? Read **[`docs/DeveloperGuideline.md`](docs/DeveloperGuideline.md)** first.
In short: read **all** of [`docs/`](docs/) before changing anything, and log
every change (CHANGELOG) and every problem+fix (troubleshooting) as you go.

## 📂 Layout

```
NtupleForge/
├── script/
│   ├── run_postproc.py         # the driver (only script shipped to CRAB)
│   └── parse_crab_status.py    # CRAB status-log summarizer (--show-lines)
├── modules/
│   ├── noop.py                 # empty module — passthrough / slim only
│   └── jetsMETcut.py           # example skim-cut (gatekeeper) module
├── branches/
│   ├── branch_keep_all.txt     # keep * — full passthrough (default)
│   └── branch_keep_and_drop.txt# minimal slimming example
├── crab/                       # CRAB3 submission glue (submit/worker/PSet)
├── crabConfig/*.yaml           # CRAB campaign configs (dataset lists)
└── docs/                       # ← all technical docs + legacy archive
```

See [`docs/`](docs/) for everything else.
