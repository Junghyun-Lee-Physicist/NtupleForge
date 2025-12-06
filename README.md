# NtupleForge ⚒️

A flexible and robust framework for CMS NanoAOD post-processing and CRAB3 submission.

## ⚠️ Pre-Check

Ensure your environment is ready before running scripts.

1. `cmsenv` (CMSSW environment)

2. `voms-proxy-init --voms cms` (If accessing remote files)

## 📂 Project Structure

Recommended directory layout for organizing your analysis:

```
NtupleForge/
├── scripts/               # Executables (run_postproc.py, dump_branches.py)
├── modules/               # Python analysis modules (e.g., jets_met.py, noop.py)
├── branches/              # Branch selection files (e.g., keep_and_drop.txt)
├── crab/                  # CRAB submission utilities
└── configs/               # (Optional) Other configuration files
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
  -c "nMuon > 1" \
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

## 🦀 CRAB Submission

Use crab/submit_crab.py to submit jobs. It packages the scripts, modules, and branches directories automatically.

### Step 1: Create Sample List

File: `samples.txt`

```
/TTToSemiLeptonic_.../RunII.../NANOAODSIM
/DyJetsToLL_.../RunII.../NANOAODSIM
```

### Step 2: Submit

```
python3 crab/submit_crab.py \
  --name "Campagin_v1" \
  --sample-list samples.txt \
  --site T3_KR_KNU \
  --cut "nJet > 3" \
  --branch-sel branches/keep_and_drop.txt \
  --imports modules.jets_met:MODULES \
  --units-per-job 1
```
