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

## ⚠️ Pre-Check before Running the program

Ensure your environment is ready before running scripts.

1. `cmsenv` (CMSSW environment)

2. Activate lxplus8 or Singularity using cmssw-el8 to build an Alma9 environment.
  
3. `voms-proxy-init --voms cms` (If accessing remote files)

## 📂 Project Structure

Recommended directory layout for organizing your analysis:

```
NtupleForge/
├── scripts/               # Executables (run_postproc.py, dump_branches.py)
├── modules/               # Python analysis modules (e.g., jets_met.py, noop.py)
├── branches/              # Branch selection files (e.g., keep_and_drop.txt)
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

## 🔧 Arguments Reference

| **Argument**               | **Description**                                                           | **Example**                  |
| -------------------------- | ------------------------------------------------------------------------- | ---------------------------- |
| `output_dir`               | Destination for output files.                                             | `./output`                   |
| `input_files`              | ROOT files or `.txt` lists.                                               | `input.root`                 |
| `--output-file`            | Merge all outputs into this filename.                                     | `merged.root`                |
| `-c`, `--cut`              | TTree cut string applied **first**.                                       | `"nJet>0"`                   |
| `-b`, `--branch-selection` | File with keep/drop rules.                                                | `branches/keep_and_drop.txt` |
| `-I`, `--imports`          | Modules to load. Format: `pkg.mod` (implies `modules`) or `pkg.mod:NAME`. | `modules.jets_met:MODULES`   |
| `-N`, `--max-events`       | Max events to process.                                                    | `100`                        |
| `--no-out`                 | Do not write ROOT file (testing).                                         | (Flag)                       |

## 🚀 Usage Examples

### 1. Simple Skim (Using Noop Module)

Apply cuts and drop branches without any complex analysis logic. Explicitly using modules.noop makes the command intent clear.

```
python3 scripts/run_postproc.py output_skim input.root \
  -c "nJet > 2" \
  -b branches/keep_and_drop.txt \
  -I modules.noop
```

### 2. Running Custom Modules

Load a module defined as MODULES inside modules/jets_met.py.

```
python3 scripts/run_postproc.py output_dev input.root \
  -I modules.jets_met:MODULES \
  --max-events 1000
```

### 3. Merging Outputs (Hadd)

Process multiple files and merge them immediately.

```
python3 scripts/run_postproc.py output_merged input_*.root \
  --output-file final_skim.root \
  -c "MET_pt > 100"
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

```
python3 crab/submit_crab.py \
  --name "Campagin_v1" \
  --sample-list samples.txt \
  --site T3_KR_KNU \
  --cut "nJet > 3" \
  --branch-sel branches/keep_and_drop.txt \
  --imports modules.jets_met:MODULES
```

🔍 Debugging Tips

- Arguments Check: Check `stdout` of a running job to see the "Command Line Arguments Received" section.

Failures: If a job fails, just run the submit command again. The script will detect the existing directory and trigger `crab resubmit`.
