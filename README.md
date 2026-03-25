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
├── scripts/
│   └── run_postproc.py       # Main executable for post-processing
├── modules/
│   ├── jetsMETcut.py         # Example simple analyzer module containing logic class & list
│   └── noop.py               # Empty module
├── branches/
│   └── branch_keep_and_drop.txt
├── crab/
│   ├── submit_crab.py        # CRAB submission manager (reads YAML)
│   ├── crab_script.py        # Worker node wrapper script
│   └── PSet.py               # Fake parameter set for CRAB
└── crabConfig/
    └── config_ttHH2017UL.yaml  # YAML configuration for CRAB
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

## 🧬 Module Structure (modules)

Analysis modules inherit from the `Module` class of `NanoAODTools`.
Locally, we store them in **`modules/`** directory to follow the standard NanoAODTools convention.
**Note:** When running on CRAB, inputs are flattened, so modules run as top-level files on the worker node.

**Implementation (`modules/jetsMETcut.py`):**
```python
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class JetSelection(Module):
    def analyze(self, event):
        return True 

# The framework loads this LIST variable
MODULES = [JetSelection()]
```


## 🔧 Configuration

### 1. Key User Arguments

These are the arguments you will use most frequently via the command line.

- **`input_files`**: A list of ROOT file paths. Supports both XRootD (`root://`) and local paths.
    
- **`-I`, `--imports`**: Python modules to load. Here, a **"module"** refers to Python code that applies cuts, calculates new variables, or modifies branches.
    
    - **Format**: `package.module:LIST_NAME` (e.g., `modules.jetsMETcut:MODULES`).
        
    - **Default**: If `:LIST_NAME` is omitted, the script looks for a list named `modules` by default.
        
- **`-b`, `--branch-selection`**: Path to a text file defining rules for keeping or dropping branches.
    
- **`-o`, `--output-file`**: (Optional) Target filename for merging. If provided, all input files are merged into this single output file.
    

### 2. Internal Defaults (Hardcoded)

To minimize errors during CRAB submission, the following settings are fixed inside `scripts/run_postproc.py`. You can enable or modify them by editing the script directly.

- **Output Directory**: Always set to the current directory (`.`) to ensure compatibility with CRAB worker nodes.
    
- **Cut String**: `None`. You have two safe options to apply cuts:
    
    1. **Modify the script**: Replace `None` with your string directly in `scripts/run_postproc_v2.py`.
        
        - _Example 1 (Simple)_: `CUT_STRING = "nJet > 2"` (Only keep events with more than 2 jets)
            
        - _Example 2 (Complex)_: `CUT_STRING = "nJet > 2 && MET_pt > 100 && abs(Jet_eta[0]) < 2.4"` (Events with >2 Jets, MET > 100, and leading Jet within tracker acceptance)
            
    2. **Use Modules**: Implement logic inside your Python module (e.g., `if event.nJet < 2: return False`).
        
    
    - _Note_: Avoid passing complex cut strings via command line arguments to prevent CRAB submission errors.
        
- **Postfix**: `_Skim` (Applies only when not merging).
    
- **Compression**: `LZMA:9` (High compression). This is the default setting in `NanoAODTools`.
    
- **Friend Mode**: `False`.


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

## 🦀 CRAB Submission

The submission script is a **Smart Manager** that handles submission, status check, and auto-resubmission.

### YAML Configuration

The CRAB jobs are defined in a YAML file (e.g., `crabConfig/config_crabTest.yaml`).

- **`common`**: Settings shared across all jobs (site, output path, modules, etc.).
    
- **`datasets`**: List of datasets to process.
    
**Important**: The `module` and `branch_selection` fields in the YAML file are passed as arguments (`-I` and `-b`) to the `run_postproc.py` script on the worker node. Ensure these paths and module names are correct.

### Commands

**1. Submit / Auto-Resubmit** Submits new jobs or resubmits failed ones automatically.

```Bash
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml
```

**2. Check Status** Checks the status of all jobs defined in the YAML file.

```Bash
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml --status
```

**3. Kill All Jobs**
If you need to stop all running jobs defined in a specific campaign configuration (e.g., due to wrong settings or priority changes), use the --kill flag.

```Bash
python3 crab/submit_crab.py --config crabConfig/config_ttHH2017UL.yaml --kill
```

This command iterates through all datasets listed in the YAML file and sends a crab kill command to their respective project directories.

## 🧬 tt+jets Event Categorizer (`modules/ttbarCategorizer.py`)

Classifies tt+jets events into sub-categories based on the flavour of additional jets **not** originating from top-quark decays, following CMS AN-2022/122 (ttHH→4b) and CMS AN-19-094 (ttH→bb).

### Categories
| Category   | Definition |
|------------|------------|
| `tt+LF`    | No additional heavy-flavour jets |
| `tt+cc`    | Additional charm jet(s), no additional b-jets |
| `tt+b`     | 1 additional b-jet from a single B hadron |
| `tt+2b`    | 1 additional b-jet from ≥2 overlapping B hadrons (collinear g→bb) |
| `tt+bb`    | Exactly 2 additional b-jets |
| `tt+bbb`   | Exactly 3 additional b-jets (ttHH-specific) |
| `tt+4b`    | ≥4 additional b-jets (ttHH-specific) |
| `noTTJets` | Non-tt events |

### Output Branches
`ttCat_LF`, `ttCat_cc`, `ttCat_b`, `ttCat_2b`, `ttCat_bb`, `ttCat_bbb`, `ttCat_4b`, `ttCat_noTTJets` (Bool),
`nAdditionalBJets`, `nAdditionalBHadrons`, `nMatchedBHadrons`, `nAdditionalCJets` (Int).

### Usage
```bash
# Standard mode
python3 scripts/run_postproc.py <input.root> \
  -I modules.ttbarCategorizer:MODULES \
  -b branches/branch_ttHHto4b_hadronic_2017UL.txt -N 1000

# Debug mode (per-event logging + end-of-job cross-validation summary)
python3 scripts/run_postproc.py <input.root> \
  -I modules.ttbarCategorizer:MODULES_DEBUG \
  -b branches/branch_ttHHto4b_hadronic_2017UL.txt -N 1000
```

### Standalone Test Script
```bash
python3 scripts/test_ttbar_categorizer.py <input.root> --max-events 50
```

### Key Implementation Details
- **Primary path**: GenPart-based B-hadron ancestry tracing + ΔR matching to GenJets (pT > 20 GeV, |η| < 2.4)
- **Fallback path**: `genTtbarId`-based when GenPart is absent (resolves up to tt+bb only)
- **tt+2b fix**: Uses per-jet B-hadron count (single jet with ≥2 matched B hadrons), not total B-hadron count
- **Cross-validation**: Debug mode compares GenPart-based result with genTtbarId, reports agreement stats
- **Robust counters**: Uses `len(event.GenPart_pdgId)` instead of `nGenPart` scalar (which can be corrupted)

## 🔄 Update / Known Issues (Dec 15, 2025)

### ⚠️ CRAB Stageout Error: Output Filename Mismatch

A critical issue has been identified where a mismatch between the `output_filename` defined in the YAML configuration and the Output Module settings in `PSet.py` causes the job to fail during the **Stageout** phase, even if the processing itself was successful.

**Error Log Snippet:**

Plaintext

```
====== Starting to check if user output files exist.
Output file slimmed.root exists.
Output file crab_args.txt exists.
ERROR: Output file tree.root does not exist.
Setting stageout wrapper exit info to {'exit_code': 60302, 'exit_acronym': 'FAILED', ...}
```

**Cause:**

- While the YAML config instructed the script to generate `slimmed.root`, CRAB's internal configuration (derived from `PSet.py`) still expected the default `tree.root`. Consequently, CRAB flagged the job as failed because it could not locate `tree.root`, ignoring the successfully created `slimmed.root`.
    

**Future Plans:**

- To resolve this permanently, I am considering implementing an **automated synchronization logic** within `submit_crab.py`.
    
- The goal is to dynamically override the Output Filename in `PSet.py` with the value provided in the YAML configuration at submission time. This will ensure consistency between the configuration and the actual CMSSW execution, preventing human errors and stageout failures.
