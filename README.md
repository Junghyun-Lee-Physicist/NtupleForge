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

1. Activate lxplus8 or Singularity using `cmssw-el8` to build an AlmaLinux 8 (el8) environment.

2. `cmsenv` (CMSSW environment)
 
3. `voms-proxy-init --voms cms` (If accessing remote files)

4. Set up crab environment using `source /cvmfs/cms.cern.ch/crab3/crab.sh`

## 📂 Project Structure

Recommended directory layout for organizing your analysis:

```
NtupleForge/
├── scripts/
│   ├── run_postproc.py               # Main executable for post-processing
│   └── test_ttbar_categorizer.py     # Standalone test for tt+jets categorizer
├── modules/
│   ├── ttbarCategorizer.py           # tt+jets event categorizer (AN-2022/122, AN-19-094)
│   ├── jetsMETcut.py                 # Example simple analyzer module
│   └── noop.py                       # Empty module
├── branches/
│   ├── branch_keep_and_drop.txt
│   └── branch_ttHHto4b_hadronic_2017UL.txt
├── crab/
│   ├── submit_crab.py                # CRAB submission manager (reads YAML)
│   ├── crab_script.py                # Worker node wrapper script
│   └── PSet.py                       # Fake parameter set for CRAB
└── crabConfig/
    └── config_ttHH2017UL.yaml        # YAML configuration for CRAB
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
    
    1. **Modify the script**: Replace `None` with your string directly in `scripts/run_postproc.py`.
        
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

## ⚠️ NanoAOD ↔ Python Interfacing Pitfalls

When the analyzer (C++) reads NanoAOD branches via `treestream` or
`makeClass`, ROOT's typed `SetBranchAddress<int>` widens compact
storage types transparently and the user code never sees the
underlying bytes. **The Python side is different.** When NanoAOD-tools
exposes branches through its `Event` wrapper in newer CMSSW releases
(observed in `CMSSW_14_2_1`, ROOT ≥ 6.30), some branches come back as
**raw `TTreeReaderArray<T>` proxies** with two surprising behaviours
that have caused real silent-failure bugs in this project. Both are
captured in `modules/_nanoaod_compat.py` as small helpers; **all
NtupleForge Python modules touching NanoAOD vector branches should
import from there**, never re-implement the conversion inline.

### Pitfall 1 — `UChar_t` branches return `bytes`, not `int`

NanoAOD stores ID and flavour fields (`Jet_jetId`, `Jet_puId`,
`Jet_hadronFlavour`, `Jet_partonFlavour`, `GenJet_hadronFlavour`,
`FatJet_jetId`, `FatJet_hadronFlavour`, `SubJet_hadronFlavour`,
`Muon_*Id`, `Electron_*Id`, ...) as ROOT `UChar_t` (1-byte unsigned
int). PyROOT exposes elements of these as **single-byte `bytes`
objects** (e.g. `b'\x05'`), not as Python `int`. Direct comparison
with integer literals **always returns False**:

```python
event.GenJet_hadronFlavour[j] == 5      # b'\x05' == 5  →  False
```

The cut silently kills every event and the categorization output
collapses to the wrong category. This is exactly the bug that put
1000/1000 TTHHTo4b signal events into `tt+LF` during the 2026-04-06
debugging session.

**Fix**: import and call `to_int()` at every UChar_t comparison site.

```python
from modules._nanoaod_compat import to_int

if to_int(event.Jet_jetId[j]) < 4:
    continue
if to_int(event.GenJet_hadronFlavour[j]) == 5:
    ...
```

`to_int()` is idempotent and free on already-`int` inputs (fast path),
so wrapping every UChar_t access is essentially zero cost.

To verify whether a suspect branch is `UChar_t`:

```python
import ROOT
f = ROOT.TFile.Open("nanoaod_file.root")
t = f.Get("Events")
leaf = t.GetBranch("GenJet_hadronFlavour").GetLeaf("GenJet_hadronFlavour")
print(leaf.GetTypeName())   # 'UChar_t' is the danger flag
```

The C++ analyzer side is **not** affected — `treestream` binds NanoAOD
`UChar_t` branches to `vector<int>` and ROOT does the type widening at
read time.

### Pitfall 2 — Raw `TTreeReaderArray` has no `len()`

Python `len()` raises `TypeError` on raw `TTreeReaderArray<T>` proxies.
The proxy supports ROOT's `GetSize()` method and integer indexing, so
the size has to be queried through one of those fallback paths.

**Fix**: import and call `safe_len()` instead of `len()`.

```python
from modules._nanoaod_compat import safe_len

n = safe_len(event.GenPart_pdgId, branch_name="GenPart_pdgId")
for i in range(n):
    ...
```

`safe_len()` is a 3-tier fallback: it tries `len()` first (fast path
for wrapped arrays), then `GetSize()` (works on raw proxies), then
integer-indexing probe (last resort). The first time path 1 fails for
a given branch type or name, a single warning is emitted to stderr;
subsequent calls are silent.

The optional `branch_name=` argument controls the warning identity —
passing the branch name gets a per-branch warning, omitting it gets
one warning per type.

### Why these helpers exist instead of monkey-patching nanoAOD-tools

The "right" fix would be to patch nanoAOD-tools' `Event` wrapper to
auto-convert UChar_t elements and to expose `__len__` on its raw
proxies. We don't because:

* Patching upstream creates a fork to maintain across CMSSW versions.
* The shim is small (≈100 lines, two functions, no dependencies).
* Future bugs of similar shape (other compact ROOT types behaving
  oddly under PyROOT) can be added to the same module without
  touching upstream code.

If a future CMSSW release ships a fixed `Event` wrapper, both helpers
become no-ops via their fast paths and no NtupleForge code needs to
change.

### CRAB sandbox convention for helper modules

CRAB worker nodes flatten the sandbox into the worker's cwd, so any
helper module that an analysis module imports must be shipped
explicitly. NtupleForge follows a single convention to make this
automatic:

> **Private helper modules in `modules/` are named with a leading
> underscore** (e.g. `modules/_nanoaod_compat.py`).

`scripts/submit_crab.py` auto-includes every file matching
`modules/_*.py` in the CRAB sandbox alongside the analysis module.
You don't need to list them in the YAML — they ride along
automatically.

The analysis module must use a **dual-mode import** so it works both
locally (as a package) and on the CRAB worker (as a flat top-level
file):

```python
try:
    from ._nanoaod_compat import to_int, safe_len   # local: package
except ImportError:
    from _nanoaod_compat import to_int, safe_len    # CRAB: flat cwd
```

The `try`/`except ImportError` pattern is the only thing that needs
to be different in the source code. Everything else — local
development, local validation runs, CRAB submission — uses the same
files.

## 🔀 Driver Branch Selection Policy

`scripts/run_postproc.py` distinguishes between **input** and **output**
branch filtering. The keep/drop file passed via `-b` is applied **only
to the output tree**:

```python
PostProcessor(
    ...,
    branchsel       = None,                       # input: read everything
    outputbranchsel = args.branch_selection,      # output: apply keep/drop
    ...
)
```

This is critical for modules that read gen-level information.
`ttbarCategorizer.py` needs `genTtbarId`, `GenPart_*`, and `GenJet_*`
to be readable from the input tree; if any of those are disabled,
the categorizer either silently mis-classifies events or fails with
`unknown branch` errors during output writing.

### Why not pass the same file to both?

The earlier version of the driver passed `branchsel=args.branch_selection,
outputbranchsel=args.branch_selection`, meaning the same `drop *`/`keep`
rules were applied twice. The result depended on the exact way
nanoAOD-tools normalizes wildcard rules vs explicit names: vector
branches that were listed in the `keep` rules sometimes ended up in a
zombie `hasattr=True / len()=0` state on the input tree, even though
they appeared correctly in the output.

In the 2026-04-06 debugging session this caused 1000/1000 events to
fall into the categorizer's `NO_GENTTBARID` path despite `keep
genTtbarId` being present. The fix is to never apply the keep/drop
file to the input tree — read everything, write only what's listed.

### Defense-in-depth in modules

`ttbarCategorizer.py` additionally calls `inputTree.SetBranchStatus(name, 1)`
for every required input branch in `beginFile()`, as a safeguard
against any future driver regression or alternative driver that might
disable input branches. This is logged at the start of every input file:

```
[TtbarCategorizer] beginFile: re-enabled 14/14 required input branches
                              (0 not present in this file)
```

Other modules that depend on specific input branches should follow the
same pattern.

## 🔧 `run_postproc.py` argument summary

| Flag | Required | Description |
|---|---|---|
| `input_files` (positional) | ✓ | One or more ROOT files (XRootD or local) |
| `-I`, `--imports` | ✓ | Module list spec, e.g. `modules.ttbarCategorizer:MODULES` |
| `-b`, `--branch-selection` | ✓ | Output keep/drop file (input is always read in full) |
| `-o`, `--output-file` | | If set, hadd all outputs into this single file |
| `-N`, `--max-events` | | Limit events processed; default = all |
| `--first-entry` | | Skip the first N entries; default 0 |
| `--ttcat-debug-csv` | | Enable ttbarCategorizer per-event CSV (validation only) |
| `--ttcat-debug-csv-path` | | Override CSV output path; default `./ttcat_debug.csv` |
| `--ttcat-quiet` | | Suppress ttbarCategorizer endJob stderr report |

The three `--ttcat-*` flags are passed to the categorizer module via
the environment variables `TTCAT_DEBUG_CSV`, `TTCAT_DEBUG_CSV_PATH`,
and `TTCAT_QUIET`. They are picked up by `make_default_module()` in
`modules/ttbarCategorizer.py`. Other modules can follow the same
pattern (env-var contract + factory function) for their own CLI
flags without coupling the driver to specific module classes.

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

Classifies tt+jets events by the heavy-flavour content of jets that do
**not** originate from the top-quark decay. Used by downstream stitching
of 5FS / 4FS / dedicated tt+4b samples and by per-category systematic
uncertainties. Follows CMS AN-19-094 (ttH→bb) §6.1.2 and CMS AN-2022/122
(ttHH→4b) §3.1.

### Why categorize at all

Standard inclusive 5FS ttbar samples (`TTToHadronic`, `TTToSemiLeptonic`)
model additional b-quarks via the parton shower, which is subject to
large PS-tune uncertainties at high jet multiplicities. The cure is
"sample stitching": keep only the LF/cc events from the 5FS sample and
take all b-jet topologies from a dedicated 4FS sample (`TTbb_4f`) that
generates the additional b-quarks at matrix-element level. The
categorizer assigns each event to one of five mutually-exclusive
categories so the stitching cuts can be applied per category, not per
sample. Per-category systematic uncertainties (e.g. the 50% rate prior
on `tt+2b`) also need this labelling.

### The five categories

The branch names use **explicit jet/hadron suffixes** to remove the
historical ambiguity of `tt+2b` (where the "2" refers to b-hadrons
inside one jet, not to the number of b-jets). "Additional" means
**not** from the top decay chain. Acceptance: `pT > 20 GeV`,
`|η| < 2.4`.

| Branch                  | AN short name | Definition |
|-------------------------|---------------|------------|
| `ttCat_LightFlavour`    | `tt+LF`       | No additional b- or c-jets |
| `ttCat_AddCjet`         | `tt+cc`/`tt+C`| ≥1 additional c-jet, no additional b-jet |
| `ttCat_Add1Bjet_1Had`   | `tt+b`        | 1 additional b-jet containing 1 b-hadron (wide-angle g→bb, one b out of acceptance) |
| `ttCat_Add1Bjet_2Had`   | `tt+2b`       | 1 additional b-jet containing ≥2 b-hadrons (collinear g→bb merged into one jet) |
| `ttCat_Add2Bjet`        | `tt+bb`       | ≥2 additional b-jets |

The ttHH AN §3.2 defines two extra categories `tt+bbb` (≥3 additional
b-jets) and `tt+4b` (=4 additional b-jets), bringing the AN total to 7.
We deliberately do **not** split them out — see "Why five and not seven"
below — and `ttCat_Add2Bjet` covers all of `tt+bb`, `tt+bbb`, and
`tt+4b` as a single bucket.

### Two algorithms, two branch sets

Both algorithms run on every ttbar event. Their results are written to
**parallel branch namespaces** so downstream code can compare them
without re-running anything.

**Primary set** (`ttCat_*`) — derived from the NanoAOD-stored
`genTtbarId` integer, which is the output of the official CMS
GenHFHadronMatcher → GenTtbarCategorizer plugin chain. This is the
AN-cited tool. **Downstream stitching and histogram splitting MUST use
these branches.**

**Cross-check set** (`ttCatXval_*`) — re-derived from raw GenPart and
GenJet info using a Python implementation of the same logic
(last-copy B/C hadron identification, top-ancestor mother-chain walk,
ΔR-matching to gen-jets in acceptance). Uses a different algorithmic
strategy than the POG ghost-clustering, so the two paths are genuinely
independent estimators. **Used ONLY for validation and algorithmic
systematics. NEVER for stitching or histogram decisions.**

The two sets typically agree on >97% of ttbar events; residual
disagreements concentrate in the 51/52/53 boundary region (1 vs 2
b-jets, single vs overlapping hadrons) and reveal either GenPart
mother-walker weak points or GenHFHadronMatcher edge cases.

### Output branches

Twelve branches per event:

```
Primary set (genTtbarId)                 Cross-check set (GenPart algorithm)
ttCat_LightFlavour          : Bool       ttCatXval_LightFlavour     : Bool
ttCat_AddCjet               : Bool       ttCatXval_AddCjet          : Bool
ttCat_Add1Bjet_1Had         : Bool       ttCatXval_Add1Bjet_1Had    : Bool
ttCat_Add1Bjet_2Had         : Bool       ttCatXval_Add1Bjet_2Had    : Bool
ttCat_Add2Bjet              : Bool       ttCatXval_Add2Bjet         : Bool
ttCatSource                 : Int        ttCatXvalSource            : Int
```

Exactly one Bool is True per ttbar event in each set; on non-ttbar
events all ten Bool branches are False and both source codes are 2
(NO_TTBAR).

Source codes:

| `ttCatSource` | meaning |
|---|---|
| 0 (`GENTTBARID`)    | `genTtbarId` decoded successfully |
| 2 (`NO_TTBAR`)      | `genTtbarId == -1`; sample is not ttbar |
| 3 (`NO_GENTTBARID`) | branch missing (should not happen on standard NanoAODv9 ttbar) |

| `ttCatXvalSource` | meaning |
|---|---|
| 0 (`GENPART`)    | GenPart algorithm ran successfully |
| 2 (`NO_TTBAR`)   | primary path said no ttbar; xval skipped to save CPU |
| 3 (`NO_GENINFO`) | `GenPart_*` / `GenJet_*` branches missing in input |

Code 1 in both source branches is reserved (was a fallback path in
earlier versions, now removed).

### Why five and not seven

The ttHH AN §3.2 defines `tt+bbb` (≥3 additional b-jets) and `tt+4b`
(=4 additional b-jets) as additional categories. We do not split them
out because:

1. **GenTtbarCategorizer cannot distinguish them.** The CMSSW source
   (`TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc` lines
   282–300) only inspects the leading two additional b-jets and encodes
   their per-jet hadron multiplicity into codes 53/54/55. The actual
   jet count (2, 3, 4, ...) is not stored anywhere in the integer.
   Recovering bbb-vs-4b from `genTtbarId` is information-theoretically
   impossible.

2. **The ttHH AN constructs bbb/4b at sample level.** §3.4 lines
   320–328 define "Option1" (use the dedicated LO `tt+4b` sample to
   construct both bbb and 4b classes) and "Option2" (use NLO 4FS
   `tt+bb` and slice the high-multiplicity tail). Neither option uses
   per-event GenHFHadronMatcher labelling to separate bbb from 4b.

3. **The final analysis merges them anyway.** ttHH AN §3.4 line 328:
   *"The tt+bbb and tt+4b are also combined into one class tt+nb,
   which is later used as one of the output node in the DNN"*. The
   bbb-vs-4b split has no effect on the final discriminant.

The GenPart-based algorithm in `ttCatXval_*` could in principle
distinguish bbb from 4b (it has direct access to b-jet counts), but
since the result is not used by any downstream consumer, we collapse
its output into the same five categories for consistency with the
primary set. If a future analysis decides to split them, the algorithm
is preserved in the source and only the branch declaration needs
extending.

### Module instantiation

The module file exports both a factory function and a ready-to-use
`MODULES` list, so you can load it with the standard driver syntax:

```bash
python3 scripts/run_postproc.py <input.root> \
  -I modules.ttbarCategorizer:MODULES \
  -b branches/branch_ttHHto4b_hadronic_2017UL.txt
```

Internally, `MODULES` is just `[make_default_module()]`, where
`make_default_module()` reads three environment variables (set by
`run_postproc.py` from its CLI flags — see the next subsection) and
passes them to the constructor. This indirection means the
`MODULES` list is constructed at import time using whatever options
the driver placed in the environment, without anyone having to write
a separate setup file.

If you want to construct the categorizer with explicit options
inside your own helper module (e.g. for unit tests or alternative
drivers), call the constructor directly:

```python
from modules.ttbarCategorizer import TtbarCategorizer

cat = TtbarCategorizer(debug_csv=True, debug_csv_path="/tmp/test.csv")
```

### CLI flags (in `run_postproc.py`)

Three optional flags control the categorizer's debug behaviour. They
do **not** affect the production branches — those are written
unconditionally — only the optional CSV dump and the endJob report.

| Flag | Default | Effect |
|---|---|---|
| `--ttcat-debug-csv` | off | Write per-event CSV with both algorithms' decisions side by side. **Do not enable for CRAB jobs**: the file is not staged out. |
| `--ttcat-debug-csv-path PATH` | `./ttcat_debug.csv` | Where to write the CSV (only effective with `--ttcat-debug-csv`). |
| `--ttcat-quiet` | off | Suppress the endJob stderr report (source distribution + category counts + confusion matrix). |

The flags are passed to the module via the environment variables
`TTCAT_DEBUG_CSV`, `TTCAT_DEBUG_CSV_PATH`, `TTCAT_QUIET`. The driver
sets these before importing modules; `make_default_module()` reads
them and instantiates accordingly.

### Usage

```bash
# Production run (CRAB or local). Both branch sets are written;
# no CSV; endJob report is on by default.
python3 scripts/run_postproc.py <input.root> \
  -I modules.ttbarCategorizer:MODULES \
  -b branches/branch_ttHHto4b_hadronic_2017UL.txt \
  -N 1000

# Local validation run with per-event CSV dump.
python3 scripts/run_postproc.py <input.root> \
  -I modules.ttbarCategorizer:MODULES \
  -b branches/branch_ttHHto4b_hadronic_2017UL.txt \
  -N 1000 \
  --ttcat-debug-csv \
  --ttcat-debug-csv-path /tmp/ttcat_check.csv
```

### endJob report

Printed to stderr at the end of every job (unless `--ttcat-quiet`).
Contains:

* Total events processed and rate (Hz).
* Source distribution: how many events used each source code, in
  percent. A `NO_GENTTBARID > 5%` warning box flags abnormal samples.
* Production category counts: per-category event totals from the
  primary path.
* Cross-check section: agreement count, agreement percentage, and a
  5×5 confusion matrix (rows = primary decision, columns = xval
  decision). Diagonal cells are agreements; off-diagonal cells are
  disagreements.

The confusion matrix is the primary tool for spotting algorithmic
discrepancies — a healthy ttbar run shows >97% on the diagonal, with
small off-diagonal entries concentrated near the 1Bjet ↔ 2Bjet
boundary.

### Debug CSV format

One row per ttbar event. Columns:

```
run, lumi, event,
ttCatSource, ttCatXvalSource,
genTtbarId, genTtbarId_mod100,
cat_production, cat_xval, agree
```

* `cat_production` and `cat_xval`: short display names
  (`LightFlavour`, `AddCjet`, `Add1Bjet_1Had`, `Add1Bjet_2Had`,
  `Add2Bjet`, or sentinels like `NoTtbar` / `Unknown`).
* `agree`: `Y`, `N`, or `n/a` (the latter when one side could not
  produce a real category).

The CSV is convenient for awk-style offline analysis but contains
no information beyond what is already in the ntuple branches.

### Validation against the analyzer

Because both algorithms write into the ntuple, the analyzer
↔ ntuplizer cross-check reduces to a per-event branch comparison
inside the analyzer:

```cpp
// in the analyzer event loop
bool prod_a2b = event.ttCat_Add2Bjet;
bool xval_a2b = event.ttCatXval_Add2Bjet;
if (prod_a2b != xval_a2b) {
    // record discrepancy for later inspection
}
```

There is no need to re-run the categorizer on the analyzer side. The
analyzer's own `computeTtCategory` (if any) should be a thin wrapper
that reads the `ttCat_*` branches directly — it must **not**
re-implement the algorithm, since that would create a third source
of truth and break the architectural rule that the ntuplizer is the
single source of truth for categorization.

### References

The categorization logic is anchored to several authoritative sources.
When in doubt, prefer them over this README.

* **CMS GenTtbarCategorizer plugin source** —
  [`TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc`](https://github.com/cms-sw/cmssw/blob/master/TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc)
  is the definitive reference for the encoding of `genTtbarId`. Lines
  ~282–300 contain the int packing rule used by `decode_genttbarid()`
  (codes 0, 41–45, 51, 52, 53–55, etc.). Reading this file once is the
  fastest way to understand exactly what `genTtbarId%100` means.

* **CMS GenHFHadronMatcher TWiki** —
  <https://twiki.cern.ch/twiki/bin/view/CMSPublic/GenHFHadronMatcher>
  describes the ghost-clustering procedure that produces the input to
  `GenTtbarCategorizer`. The category definitions there (tt+b, tt+2b,
  tt+bb, tt+cc, tt+LF) are what we map onto our five-category schema.
  The page also explains *why* the bbb/4b split that some older notes
  mention is not present in the integer — the plugin only encodes the
  hadron multiplicity inside the leading two b-jets, not the b-jet
  count itself.

* **CMS NanoAOD ttbar categorisation TWiki** —
  <https://twiki.cern.ch/twiki/bin/view/CMS/TopModGen> (genTtbarId
  branch documentation in NanoAOD) describes how the plugin output is
  serialised into the NanoAOD `genTtbarId` branch and is the source we
  read directly in `decode_genttbarid()`.

* **ttHH AN-2022/122**, §3.1 (object & event categorisation) and §3.4
  (5FS/4FS sample stitching). The AN cites the GenHFHadronMatcher /
  GenTtbarCategorizer plugin chain as the official categoriser and
  constructs bbb/4b splits at sample level (Option1 / Option2), not
  per event. This is why our schema only has five event-level
  categories — the schema *matches the AN's per-event resolution*.

* **ttH AN-19-094**, §6.1.2 — earlier reference on the same plugin
  chain for the ttH analysis. The hadronic-channel parts that the
  ttHH AN does not cover should be cross-referenced here.

### Future TODO

These are known points of friction that we deliberately do *not* fix
right now (because they would either touch downstream code or change
branch names that other packages depend on), but which should be
addressed in the next major refactor.

* **Rename `ttCatXval_*` → something more descriptive.** The `Xval`
  ("cross-validation") prefix is opaque to anyone who hasn't read this
  README. Better candidates: `ttCatGenPart_*`, `ttCatRecomputed_*`, or
  `ttCatAlt_*`. The rename must be coordinated with the analyzer's
  `eventBuffer` regeneration and with `branch_*.txt`. Until that
  happens, the name stays as `ttCatXval_*` for backward compatibility.

* **Document the rename in NEWS / CHANGELOG** at the same time, so
  downstream consumers know what to update.

* **Analyzer-side fast-path flag (planned).** The analyzer currently
  recomputes both the GenPart and the genTtbarId-decode estimators on
  every MC event, even though their result is identical to the ntuple
  branches. Once the validation has been signed off across enough
  samples, the analyzer will gain a `validateTtCat` boolean flag (or
  CLI option) that defaults to `false`. With the flag off, the
  analyzer reads `ttCat_*` directly via `officialTtCategory()` and
  skips the four-way comparison entirely, recovering the per-event
  GenPart loop cost. With the flag on (e.g. for new sample
  validation, or after touching the categorizer), the full
  comparison runs. This README should be updated to point at the
  flag when it lands.

## 🔄 Known Issues

### ⚠️ CRAB Stageout Error: Output Filename Mismatch (Reported Dec 15, 2025)

A mismatch between the `output_filename` defined in the YAML configuration and the Output Module settings in `PSet.py` causes the job to fail during the **Stageout** phase, even if the processing itself was successful.

**Error Log Snippet:**

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
