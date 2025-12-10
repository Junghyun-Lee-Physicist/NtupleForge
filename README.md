# NtupleForge ⚒️

**NtupleForge** provides utilities for running NanoAOD post-processing without modifying the upstream `PhysicsTools/NanoAODTools` package directly and CRAB3 submission.

- [Link to CMSSW NanoAODTools framework](https://github.com/cms-sw/cmssw/tree/CMSSW_14_2_X/PhysicsTools/NanoAODTools)

## 🛠️ Setup

Prepare a CMSSW area, check out the official NanoAOD tools, and clone `NtupleForge`.
   *(Note: `scram b` is required to compile and update python paths)*

> [!NOTE]
   > **Environment Check**: Before installing CMSSW, please log in to **lxplus8** (`ssh <user>@lxplus8.cern.ch`) or set up a Singularity container using `cmssw-el8`.
   > This step is mandatory because `CMSSW_14_2_1` requires the **el8_amd64_gcc12** architecture.


   ```bash
   cmsrel CMSSW_14_2_1
   cd CMSSW_14_2_1/src
   cmsenv
   
   # Setup standard NanoAODTools
   git cms-init
   git cms-addpkg PhysicsTools/NanoAODTools
   
   # Clone NtupleForge
   git clone https://github.com/Junghyun-Lee-Physicist/NtupleForge.git
   
   # Compile to setup environment
   scram b -j 8
   cd NtupleForge
   ```

## ⚠️ Prerequisites

Ensure your environment is ready before running scripts.

1. Activate lxplus8 or Singularity using cmssw-el8 to build an Alma9 environment.

2. `cmsenv` (CMSSW environment)
 
3. `voms-proxy-init --voms cms` (If accessing remote files)

4. Set up crab environment using `source /cvmfs/cms.cern.ch/crab3/crab.sh`

## 📂 Project Structure

Recommended directory layout for organizing your analysis:

```
NtupleForge/
├── scripts/               # Executables (run_postproc.py, dump_branches.py)
├── modules/               # Python analysis modules (e.g., jetsMETcut.py, noop.py)
├── branches/              # Branch selection files (e.g., branch_keep_and_drop.txt)
├── dataSetPath/           # Sample lists (.txt)
├── crab/                  # CRAB submission utilities
```

## 🧠 Code Architecture

The core script `scripts/run_postproc.py` follows the standard `NanoAODTools` workflow. Here is the conceptual skeleton:

```
# Skeleton of run_postproc.py
def main():
    # 1. Parse Arguments
    args = parse_args()

    # 2. Expand Inputs
    # Convert .txt lists to ROOT file paths
    files = expand(args.input_files)

    # 3. Load Modules (Strict Mode)
    # Syntax "module:List" allows loading specific lists like 'MODULES'
    modules = []
    for imp in args.imports:
        mod_name, list_name = parse_import_string(imp)
        loaded_mod = import_module(mod_name)
        modules.extend(getattr(loaded_mod, list_name))

    # 4. Initialize Engine
    p = PostProcessor(
        outputDir, 
        inputFiles,
        cut=args.cut, 
        modules=modules,
        branchsel=args.branch_sel,
        haddFileName=args.output_file # Optional Auto-Merge
    )

    # 5. Run Event Loop
    p.run()
```

## 🚀 Local Quick Start

### Scenario A: Simple Slimming (No-Op)

Performs only branch selection (Keep/Drop) without any event filtering logic. Uses `modules.noop`.

- **Module**: `modules.noop` (No cut logic)
    
- **Branch Selection**: `branches/branch_keep_and_drop.txt`
    
- **Max Events**: 1000
    

```
# Syntax: python3 scripts/run_postproc.py [INPUTs...] -b [BRANCH_SEL] -I [MODULE] -N [MAX_EVENTS]
python3 scripts/run_postproc.py \
  root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root \
  -b branches/branch_keep_and_drop.txt \
  -I modules.noop \
  -N 1000
```

### Scenario B: Merge Mode (Hadd) with Offset

Processes multiple inputs and merges them into a single output file using the `-o` flag. Starts processing from the 100th entry.

- **Module**: `modules.noop`
    
- **Branch Selection**: `branches/branch_keep_and_drop.txt`
    
- **Output**: Merged into `skimmed_merged.root`
    
- **First Entry**: 100
    
- **Max Events**: 1000
    

```
python3 scripts/run_postproc.py \
  root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root \
  root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/AC357503-8E32-0445-89E6-D3BD6BB1B5DC.root \
  -b branches/branch_keep_and_drop.txt \
  -I modules.noop \
  -o skimmed_merged.root \
  --first-entry 100 \
  -N 1000
```

### Scenario C: Basic Split Mode with Module

Runs the `jetsMETcut` module to apply cuts. Input files are processed individually, producing one output file per input.

- **Module**: `modules.jetsMETcut:MODULES` (Applies Jet/MET cuts)
    
- **Branch Selection**: `branches/branch_keep_and_drop.txt`
    
- **Max Events**: 1000
    

```
python3 scripts/run_postproc.py \
  root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/549451D9-10EC-704C-8568-23FF9D40C9F4.root \
  root://cms-xrd-global.cern.ch///store/mc/RunIISummer20UL17NanoAODv9/TTToSemiLeptonic_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/AC357503-8E32-0445-89E6-D3BD6BB1B5DC.root \
  -b branches/branch_keep_and_drop.txt \
  -I modules.jetsMETcut:MODULES \
  -N 1000
```


### 4. Validate Output
Check how many events survived the skim.
```
python3 scripts/validate_events.py "output_local/*.root"
```

## 🦀 CRAB Submission & Resubmission

The crab/submit_crab.py script is a Smart Manager.

It reads datasets from dataSetPath/.

It iterates through the list.

If a task already exists, it attempts to RESUBMIT failed jobs.

If a task is new, it SUBMITS it.

### Step 1: Prepare Sample List

Place your list in `dataSetPath/samples.txt`.

```
/TTToSemiLeptonic_.../RunII.../NANOAODSIM
/DyJetsToLL_.../RunII.../NANOAODSIM
```

### Step 2: Run Manager

You can run this command multiple times. It will submit new tasks and fix broken ones automatically.

Note: We do NOT pass --cut anymore. The cut is inside modules.jetsMETcut.

```
python3 crab/submit_crab.py \
  --name "Campagin_v4_ModuleCut" \
  --sample-list samples.txt \
  --site T3_KR_KNU \
  --branch-sel branches/branch_keep_and_drop.txt \
  --imports modules.jetsMETcut:MODULES
```

🔍 Debugging Tips

- Arguments Check: Check `stdout` of a running job to see the "Command Line Arguments Received" section.

Failures: If a job fails, just run the submit command again. The script will detect the existing directory and trigger `crab resubmit`.
