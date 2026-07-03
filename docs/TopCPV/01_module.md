# `topCPVCategorizer` module reference

> **Purpose:** how to run the NtupleForge NanoAOD module that reproduces the
> MiniAOD `SSBAnalyzer` gen-level categorization, and exactly which branches it
> emits. **Audience:** analysts wiring the CPV ntuple production. **Status:**
> active (NanoAODv9). **Updated:** 2026-07-01.
> Deep algorithm/physics live in `03_miniaod_origin.md`, `02_faithfulness_vs_miniaod.md`,
> and the standalone TopCPV package `docs/TECHNICAL.md`; this file does not repeat them.

## BLUF

`modules/topCPVCategorizer.py` reproduces the MiniAOD `SSBAnalyzer` gen-level
categorization (the reference of truth; see `03_miniaod_origin.md`) from the NanoAOD
`GenPart` collection. It writes derived branches only — the raw gen collections
come from the full-NanoAOD passthrough — under the `TopCPVCat_` prefix, plus the
additive diagnostic `Channel_Idx_Expanded`. The standalone TopCPV C++ has been
updated to the same behaviour, so the two should agree. **MC only** (GenPart-less
inputs are a logged no-op, not a crash — see "MC-only behaviour" below).

## What it emits (prefix `TopCPVCat_`)

Derived branches (added by this module):

- `isSignal` (`O`) — both a top and an antitop last-copy found.
- `SelectedIdx[12]` (`I`) — the 12-slot family-tree indices (slots 0,1 = protons
  = −1; 2,3 = t,t̄; 4,5 = W⁺,b; 6,7 = W⁻,b̄; 8,9 = W⁺ daughters; 10,11 = W⁻
  daughters). All −1 for background slots 4–11.
- `GenPar_Count` + `GenPar_{Idx,pdgId,Status,pt,eta,phi,mass,energy,Mom1_Idx,
  Mom2_Idx,Dau1_Idx,Dau2_Idx,Mom_Counter,Dau_Counter}` — the family-tree records
  (12 slots for signal, **plus one entry per leptonic-τ daughter** appended by the
  §2.2 τ resolution; variable for background).
- `GenTop_{pt,eta,phi,energy}`, `GenAnTop_{pt,eta,phi,energy}` — top/antitop
  kinematics (last copy). **Use these for CPV** top/antitop momenta.
- `Channel_{Idx,Idx_Final,Lepton_Count,Lepton_Count_Final,Jets,Jets_Abs,
  Tau_Lepton,Visible_Tau}` — the channel codes (see `GenPart_channel_definition.md`).
  `Tau_Lepton` and `Visible_Tau` are NanoAOD bonuses (not in MiniAOD).
- `Channel_Idx_Expanded` — additive diagnostic (see below).
- `GenBJet_Count`/`GenBHad_Count` + `GenBJet_{pt,eta,phi,energy}` +
  `GenBHad_{pt,eta,phi,energy,FromTopWeakDecay,Flavour}` — ghost-B-tagged gen-jets
  and their matched b-quark proxy.

**Not** emitted (already in the passthrough Events tree with identical values):
`GenJet_*`, `GenMET_*`, `PSWeight_*`, `run`/`luminosityBlock`/`event`. Re-emitting
them would collide with the passthrough names and duplicate data.

## `Channel_Idx_Expanded` — additive diagnostic

Does **not** change `Channel_Idx` (which stays MiniAOD-identical):

- `= Channel_Idx` when the selection is well-formed;
- `= -999` when `isSignal` is true but any of slots 2–11 is `< 0` (the 12-slot
  build failed — the NanoAOD analogue of MiniAOD's `SelectedPar.size() != 12`,
  whose only trace in MiniAOD was a `cerr`).

So genuine all-hadronic stays `Channel_Idx == Channel_Idx_Expanded == 0`, while an
unclassifiable signal event is `Channel_Idx == 0` but `Channel_Idx_Expanded == -999`.
The end-of-job line prints the unclassifiable rate.

## Fidelity statement (READ THIS)

The **reference is the MiniAOD `SSBAnalyzer`**, not the standalone TopCPV. This
module follows MiniAOD, with the audit's restorations applied
(`02_faithfulness_vs_miniaod.md` §9, `../03_DECISIONS.md` → D-2026-06-28-miniaod-reference):

- **Background channel** (§2): `Channel_Idx` summed over the **full** selected list
  (MiniAOD §2.1) — background boson-decay channels recovered, not forced to 0.
- **τ → ℓ final channel** (§5): `Channel_Idx_Final` resolved by **walking the
  GenPart daughter map** (MiniAOD §2.2); the resolved τ daughter is **appended to
  GenPar**, so `GenPar_Count` grows for leptonic-τ events. `GenDressedLepton` not used.
- **Kept** (physically preferable / NanoAOD-inherent): last-copy top for GenPar
  slots (CPV momenta come from `GenTop`/`GenAnTop`), explicit W⁻ daughters,
  `GenBJet` via `GenJet_hadronFlavour`.
- **NanoAOD bonuses** (not in MiniAOD): `Channel_Visible_Tau`, `Channel_Tau_Lepton`.
- **Unrecoverable from NanoAOD**: `GenBHad` hadron kinematics (b-quark proxy),
  official `GenBHad_FromTopWeakDecay` (mother-chain recompute), `GenJet_HCal/ECalEnergy`,
  B-frag weights.

The standalone TopCPV C++ has been updated to the **same** behaviour, so the two
should agree (validate with `script/validate_topcpvcat.py`). Integer/categorization
branches match exactly; float branches to `float32` precision.

## Branch access rules this module obeys (MANDATORY for edits)

See `../06_nanoaod_branch_access.md` and `../00_PROMPT.md` §6:

- Collection lengths come from the **count branch** — `count(event, "GenPart")`,
  `count(event, "GenJet")`, `opt_count(event, "GenVisTau")` — **never** from
  probing the array (out-of-bounds `TTreeReaderArray.At()` segfaults; that was
  CRAB incident A12 on 2026-07-01). Elements are indexed only in-bounds.
- `UChar_t` elements (`GenJet_hadronFlavour`, …) are compared through `to_int()`.
- **All readers are pre-registered in `beginFile`** (`GEN_ARRAY_BRANCHES` /
  `GEN_COUNTER_BRANCHES` via `inputTree.arrayReader/valueReader`) so the event
  loop never triggers a reader rebuild — lazily creating a reader mid-loop
  invalidates every previously bound reader object (CRAB incident A13,
  2026-07-02). New branch reads MUST be added to those lists.
- Branch presence is detected in `beginFile` from
  `inputTree.GetListOfBranches()` — not `hasattr` (A5), not
  `inputTree.GetBranch(...) is None` (A11).

## MC-only behaviour (data / non-gen inputs)

If `GenPart_pdgId` is absent from the input branch list, `beginFile` logs one
line and the module becomes a **no-op for that file**: no output branches are
defined, `analyze` passes every event through (`return True`). This replaces the
pre-2026-07-01 behaviour (a `RuntimeError` guard that in practice failed to fire
and let the job crash inside `analyze` — `../05_troubleshooting.md` A11).
A no-op is still the wrong way to run data: **keep the module out of data
configs** and use `branch_CPV_Run2_Data.txt` there.

## Input dependency

Reads `GenPart`, `GenJet`(+`hadronFlavour`), `GenVisTau` (optional) from the
input. The MC branch list drops `GenVisTau*` from the **output** — fine,
because modules read the full input tree and only the derived
`Channel_Visible_Tau` is written. Keep `branch_file` as an output selection
(NanoAODTools default) so the input `GenVisTau` stays readable here.

## How to run

In a `config_CPV<era>_MC.yaml` (MC configs only — data configs use `modules/noop.py`; see D-2026-07-02-per-tier-configs), the analysis module points at this file:

```yaml
analysis_module: ["modules/topCPVCategorizer.py", "MODULES"]
```

The file exposes `MODULES = [TopCPVCategorizer()]`. The default branch list is
MC. For a quick local sanity run on lxplus:

```bash
python3 script/run_postproc.py <MC_nanoaod.root> \
  -I modules.topCPVCategorizer:MODULES \
  -b branches/branch_CPV_Run2_MC.txt \
  -N 10
```

Optional guarded debug printout for the first N events: `TOPCPVCAT_DEBUG=N`
(environment variable; 0/off by default).

## Validation

`script/validate_topcpvcat.py` matches events by `(run, luminosityBlock, event)`
and compares the module output against a standalone TopCPV `GenCatTree` run on the
same file — integers exactly, floats within `--ftol`. Run it on lxplus once per
campaign change:

```bash
python script/validate_topcpvcat.py --nano slimmedNtuple.root --gencat gencat.root
```
