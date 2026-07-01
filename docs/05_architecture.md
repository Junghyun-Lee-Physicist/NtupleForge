# Architecture — NanoAOD PostProcessor and Module Structure

This document explains the machinery NtupleForge sits on top of: where the
CMS `PostProcessor` lives inside CMSSW, what it does, how the per-event
module framework works, and how NtupleForge's driver wires it all together.
Read this before writing a new module or touching `run_postproc.py`.

---

## 1. What NtupleForge is

NtupleForge is a **thin, non-invasive wrapper** around the standard CMS
`PhysicsTools/NanoAODTools` `PostProcessor`. It never patches the upstream
package; it only adds a driver script, a few analysis modules, branch
keep/drop lists, and CRAB3 submission glue. The goal is to run NanoAOD
post-processing (skim / slim / add branches) reproducibly, both locally and
on the grid, without forking CMSSW.

In the **current** direction the pipeline is configured as a *full NanoAOD
passthrough*: the post-processor copies the input through unchanged and the
tt+jets categorization is done downstream in the main analyzer. The
historical configuration — a categorizer module that wrote `ttCat_*`
branches, plus an aggressive slimming list, plus an optional skim cut — is
preserved verbatim under [`legacy/code/`](legacy/code/) and documented in
[`09_legacy_ttbar_pipeline.md`](09_legacy_ttbar_pipeline.md).

---

## 2. Where the PostProcessor lives in CMSSW

The framework is `PhysicsTools/NanoAODTools`, checked out into a CMSSW
release area:

```bash
cmsrel CMSSW_14_2_1            # el8_amd64_gcc12 — needs lxplus8 / cmssw-el8
cd CMSSW_14_2_1/src
cmsenv
git cms-init
git cms-addpkg PhysicsTools/NanoAODTools
```

The relevant Python lives under
`PhysicsTools/NanoAODTools/python/postprocessing/`:

| Path (under that prefix)            | Role |
|-------------------------------------|------|
| `framework/postprocessor.py`        | The `PostProcessor` class — the engine. |
| `framework/eventloop.py`            | The `Module` base class + the event loop. |
| `framework/datamodel.py`            | `Event`, `Collection`, `Object` wrappers over the TTree. |
| `framework/output.py` / `treeReaderArrayTools.py` | Output tree writing and the `TTreeReaderArray` access path. |
| `framework/branchselection.py`      | Parser for `keep`/`drop` rule files. |

After `git cms-addpkg`, **`scram b`** is required at least once — it
compiles the package and, importantly, puts the package on the Python path
so `from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor
import PostProcessor` resolves.

The upstream reference is the CMSSW GitHub mirror:
<https://github.com/cms-sw/cmssw/tree/CMSSW_14_2_X/PhysicsTools/NanoAODTools>

---

## 3. What the PostProcessor does

`PostProcessor` opens each input ROOT file, reads its `Events` tree, runs an
**ordered list of `Module` objects** on every event, and writes a new
`Events` tree containing (a) the surviving events and (b) any new branches
the modules declared. Non-`Events` trees (`Runs`, `LuminosityBlocks`) are
copied through so downstream normalization (gen-weight sums) still works.

Key constructor parameters (as used in `script/run_postproc.py`):

| Parameter         | Meaning |
|-------------------|---------|
| `outputDir`       | Where output files are written. NtupleForge hardcodes `"."` for CRAB worker compatibility. |
| `inputFiles`      | List of ROOT paths (local or `root://` XRootD). |
| `cut`             | A TTree selection string applied before the modules. `None` = no cut (recommended; apply cuts inside a module instead). |
| `modules`         | The ordered list of `Module` instances to run. |
| `branchsel`       | **Input** tree branch filter. See §7 — NtupleForge sets this to `None` (read everything). |
| `outputbranchsel` | **Output** tree branch filter — the keep/drop file passed via `-b`. |
| `compression`     | Output compression, e.g. `LZMA:9` (high ratio) or `LZ4:4` (fast). |
| `postfix`         | Suffix for split-mode output files (`_Skim`). |
| `haddFileName`    | If set, all outputs are merged (`hadd`) into this one file. |
| `maxEntries` / `firstEntry` | Event-range control. |
| `provenance` / `fwkJobReport` | Write provenance metadata / a `FrameworkJobReport.xml`. `fwkJobReport=True` is required for CRAB. |

**Split vs merge mode.** If `haddFileName` is `None`, the post-processor
produces one output file per input (split mode, suffix `postfix`). If
`haddFileName` is set, it merges all outputs into that single file.

---

## 4. The event-loop framework and the `Module` contract

Every analysis module subclasses
`PhysicsTools.NanoAODTools.postprocessing.framework.eventloop.Module` and
overrides a subset of these hooks, called by the engine in this order:

```
beginJob()                                   # once, before any file
  for each input file:
    beginFile(inputFile, outputFile,         # once per file:
              inputTree, wrappedOutputTree)   #   declare output branches here
    for each event:
      analyze(event)  -> bool                 #   per event: True = keep, False = drop
    endFile(inputFile, outputFile,
            inputTree, wrappedOutputTree)
endJob()                                     # once, after all files
```

Rules that matter in practice (each one is a bug we have actually hit):

1. **Declare output branches in `beginFile`**, via
   `wrappedOutputTree.branch(name, type_code)`. Type codes: `"O"` = Bool,
   `"I"` = Int, `"F"` = Float, `"i"`/`"l"` for unsigned/long, etc.
2. **The base class does not inject `self.out`.** Each module must capture
   the wrapped output tree itself, e.g. `self.out = wrappedOutputTree`, so
   `analyze` can call `self.out.fillBranch(name, value)`.
3. **`analyze` must return a bool.** `True` keeps the event, `False` drops
   it. A module that only *adds* branches returns `True` unconditionally.
4. **Fill every declared branch on every event.** If a branch is declared
   but not filled on some event, it carries a stale value. The categorizer
   pattern is: reset all category branches to a default at the top of
   `analyze`, then set the chosen one.

The driver loads modules through a `package.module:LIST_NAME` string
(e.g. `-I modules.jetsMETcut:MODULES`). The module file exposes a list
variable — by convention `MODULES` — that holds **instances** (not classes):

```python
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class JetSelection(Module):
    def analyze(self, event):
        return True

MODULES = [JetSelection()]          # the driver iterates over this list
```

A minimal "do nothing" module is just an empty list — see
[`../modules/noop.py`](../modules/noop.py), used for pure passthrough/slim
runs. A minimal cut module is [`../modules/jetsMETcut.py`](../modules/jetsMETcut.py),
which demonstrates the gatekeeper pattern (drop obviously-uninteresting
events, but do **not** filter object collections — leave that to the
analyzer for flexibility and speed).

---

## 5. How modules are organized (`modules/` directory)

Locally, modules live in `modules/` so they form a Python package and can
be imported as `modules.<name>`. **On a CRAB worker the sandbox is
flattened** into the worker's cwd, so the same module is imported as a
top-level file `<name>`. Two conventions handle this split:

- **Robust helper import (flat / CRAB-safe).** CRAB flattens the sandbox and
  imports the analysis module *flat* (top-level, no parent package), so a relative
  import fails on the worker. Put the module's own directory on `sys.path` via
  `__file__`, then import the sibling helper:

  ```python
  import os, sys
  _HERE = os.path.dirname(os.path.abspath(__file__))
  if _HERE not in sys.path:
      sys.path.insert(0, _HERE)
  from nanoaod_branch_access import to_int, safe_len
  ```

- **Helper shipping (co-location, not naming).** `crab/submit_crab.py` auto-includes
  **every** sibling `.py` in the analysis module's directory (except the module
  itself and dunders) in the CRAB sandbox, so helpers ride along without being
  listed in the YAML. (Previously only `modules/_*.py` shipped, which coupled a
  helper's *name* to whether it shipped — renaming a helper without the leading
  underscore silently dropped it and broke the job at import time; see
  [`06_troubleshooting.md`](06_troubleshooting.md).) Why a helper shim is needed at
  all is its own story — see [`07_nanoaod_branch_access.md`](07_nanoaod_branch_access.md).

Driver/CLI-flag plumbing without coupling the driver to a specific class is
done with the **env-var contract + factory** pattern: the driver sets
environment variables from its argparse flags, and the module's
`make_default_module()` factory reads them at import time when building
`MODULES`. The legacy categorizer uses this for its debug flags; see
[`09_legacy_ttbar_pipeline.md`](09_legacy_ttbar_pipeline.md) §"CLI flags".

---

## 6. Writing your own module — add a branch, apply a cut

This is the copy-followable recipe. Anyone who reads this section should be
able to produce a working branch-adding or event-cutting module without
looking anywhere else. Both examples are complete and runnable.

### 6.1 A module that ADDS a branch

Goal: compute a new per-event quantity from existing branches and write it to
the output ntuple. Example: scalar jet HT (`Σ Jet_pt`) and a boolean flag.

Create `modules/myVars.py`:

```python
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class MyVars(Module):
    """Adds two output branches: Jet_HT (Float) and pass_HT500 (Bool)."""

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        # (a) capture the wrapped output tree — the base class does NOT
        #     inject self.out for you.
        self.out = wrappedOutputTree
        # (b) declare every output branch here, with a type code:
        #     "F" Float, "I" Int, "O" Bool, "i" UInt, "l" Long, ...
        self.out.branch("Jet_HT",     "F")
        self.out.branch("pass_HT500", "O")

    def analyze(self, event):
        # nJet / Jet_pt are scalar/Float NanoAOD branches → safe to read
        # directly. (For UChar_t or vector branches read through the compat
        # shim — see 07_nanoaod_branch_access.md.)
        njet = event.nJet
        ht = 0.0
        for i in range(njet):
            ht += event.Jet_pt[i]

        # (c) fill EVERY declared branch on EVERY event, or it carries a
        #     stale value from the previous event.
        self.out.fillBranch("Jet_HT", ht)
        self.out.fillBranch("pass_HT500", ht > 500.0)

        return True          # adding branches only → never drop the event

# The driver loads this list (instances, not classes):
MODULES = [MyVars()]
```

Run it. **The output branch file must `keep` the new branches**, or they are
computed and then dropped on write:

```bash
# minimal keep file, e.g. branches/keep_myvars.txt:
#   keep *
#   keep Jet_HT
#   keep pass_HT500
python3 script/run_postproc.py <input.root> \
  -I modules.myVars:MODULES \
  -b branches/keep_myvars.txt \
  -N 1000
```

(With `keep *` the new branches are already covered; list them explicitly
only when slimming with `drop *`.)

### 6.2 A module that applies a CUT (skim)

Goal: drop whole events that fail a selection. Return `False` from `analyze`
to drop, `True` to keep. The live example is
[`../modules/jetsMETcut.py`](../modules/jetsMETcut.py); the shape is:

```python
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class MyCut(Module):
    def __init__(self, njet_min=6, met_min=300.0):
        self.njet_min = int(njet_min)
        self.met_min  = float(met_min)

    def analyze(self, event):
        if event.MET_pt < self.met_min:   return False   # drop
        if event.nJet   < self.njet_min:  return False   # drop
        return True                                       # keep

MODULES = [MyCut(njet_min=6, met_min=300.0)]
```

```bash
python3 script/run_postproc.py <input.root> \
  -I modules.myCut:MODULES \
  -b branches/branch_keep_all.txt \
  -N 1000
```

**Design rule (observed throughout NtupleForge): a skim drops whole events
only — it does NOT filter object collections** (don't remove individual jets
here). "Good object" definitions change between analysis phases; hardcoding
object selection at production time forces a full ntuple re-production on
every change. Do object-level selection in the analyzer (compiled C++ /
RDataFrame), which is faster and preserves rejected objects for sideband and
fake-rate studies.

### 6.3 Combine, order, and run on CRAB

- **Add + cut in one module**: do the cut first (`return False` early), then
  fill branches and `return True`. Or list two modules:
  `MODULES = [MyCut(), MyVars()]` — they run **in list order**, and a `False`
  from an earlier module stops later modules for that event.
- **Multiple module files**: pass several `-I` specs, e.g.
  `-I modules.myCut:MODULES -I modules.myVars:MODULES`.
- **CRAB**: point the YAML at the module + keep file; the dataset list and
  everything else is unchanged:

  ```yaml
  analysis_module: ["modules/myVars.py", "MODULES"]
  branch_file:     "branches/keep_myvars.txt"
  ```

  `submit_crab.py` ships the module, every `modules/_*.py` helper, and the
  keep file automatically.

### 6.4 The four rules that prevent silent failures

Every one of these is a real bug we hit (full incident log:
[`06_troubleshooting.md`](06_troubleshooting.md)):

1. **Capture `self.out` yourself** in `beginFile`; declare all branches there.
2. **Reset/fill every declared branch on every event** — an unset branch
   keeps a stale value.
3. **Read `UChar_t` and vector branches through the compat shim** (`to_int`,
   `safe_len`), never `int(event.X[i])` / `len(event.Vec)` raw — see
   [`07_nanoaod_branch_access.md`](07_nanoaod_branch_access.md).
4. **Detect optional input branches via `inputTree.GetListOfBranches()`**,
   not `hasattr(event, name)` (the Event wrapper raises `RuntimeError` on a
   missing branch, which `hasattr` does not catch, crashing the job).

---

## 7. Input vs output branch selection (the `branchsel` rule)

This is the single most error-prone knob, so it gets its own section.

NtupleForge applies the keep/drop file **only to the output tree**:

```python
PostProcessor(
    ...,
    branchsel       = None,                  # INPUT  tree: read everything
    outputbranchsel = args.branch_selection, # OUTPUT tree: apply keep/drop
)
```

**Why never pass the keep/drop file as `branchsel` too.** An earlier driver
set `branchsel = outputbranchsel = <file>`, so `drop *` was applied to the
*input* tree as well; the driver then re-enabled only the listed `keep`
branches on input. Depending on how nanoAOD-tools normalizes wildcard rules
versus explicit names, vector branches that were listed in `keep` sometimes
ended up in a `hasattr=True / len()=0` **zombie state** on the input tree
even though they appeared correctly in the output. In the 2026-04-06
debugging session this put **1000/1000** signal events into the categorizer's
`NO_GENTTBARID` path despite `keep genTtbarId` being present. The fix is the
rule above: read the input in full, filter only the output.

For full passthrough the output filter is `branches/branch_keep_all.txt`
(`keep *`). For slimming, list the branches to keep after a leading
`drop *`; the historical example is
[`legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt`](legacy/code/branches/branch_ttHHto4b_hadronic_2017UL.txt).

**Defense in depth (for modules that read specific input branches).** A
module can re-assert the branches it needs in `beginFile` via
`inputTree.SetBranchStatus(name, 1)`, as a safeguard against any future
driver regression. The legacy categorizer did exactly this for its 14
gen-level inputs. In the current passthrough configuration no module reads
gen branches, so this safeguard is not needed — but it is the right pattern
for any future branch-reading module.

---

## 8. The driver (`script/run_postproc.py`)

The driver is the only script shipped to CRAB workers. Its job:

1. Parse CLI args (`input_files`, `-I/--imports`, `-b/--branch-selection`,
   `-o/--output-file`, `-N/--max-events`, `--first-entry`, plus any
   module-specific flags it forwards via environment variables).
2. Dynamically import the requested module list(s) with the
   `module:LIST` syntax and collect the instances.
3. Construct the `PostProcessor` with the hardcoded production defaults
   (output dir `.`, no cut string, `LZMA:9`, `fwkJobReport=True`, the
   input/output `branchsel` split from §7).
4. Run the event loop; in merge mode it `hadd`s into `--output-file`.

Complex settings (cut string, compression, postfix) are **hardcoded inside
the driver** rather than exposed as CLI flags, deliberately, to avoid quoting
and argument-parsing failures during CRAB submission. To change them, edit
the constants block in `run_postproc.py`.

See [`../README.md`](../README.md) for the exact commands to run a
passthrough locally and on CRAB.

---

## 9. References

- CMSSW NanoAODTools framework:
  <https://github.com/cms-sw/cmssw/tree/CMSSW_14_2_X/PhysicsTools/NanoAODTools>
- For the categorization physics and the full historical pipeline (module +
  branch list + skim cut), see [`09_legacy_ttbar_pipeline.md`](09_legacy_ttbar_pipeline.md).
- For why the PyROOT compatibility shim existed, see
  [`07_nanoaod_branch_access.md`](07_nanoaod_branch_access.md).
- For the change history, see [`03_CHANGELOG.md`](03_CHANGELOG.md).
