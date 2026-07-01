# `ssbGenCategorizer` module reference

> **Purpose:** how to run the NtupleForge NanoAOD module that reproduces the
> SSBGenCategorizer gen-level categorization, and exactly which branches it emits.
> **Audience:** analysts wiring the CPV ntuple production. **Status:** active
> (NanoAODv9). **Updated:** 2026-06-27.
> Deep algorithm/physics live in `03_miniaod_origin.md`, `02_faithfulness_vs_miniaod.md`,
> and the SSBGen package `docs/TECHNICAL.md`; this file does not repeat them.

## BLUF

`modules/ssbGenCategorizer.py` reproduces the MiniAOD `SSBAnalyzer` gen-level
categorization (the reference of truth; see `03_miniaod_origin.md`) from the NanoAOD
`GenPart` collection. It writes derived branches only — the raw gen collections
come from the full-NanoAOD passthrough — under the `SSBGenCat_` prefix, plus the
additive diagnostic `Channel_Idx_Expanded`. The standalone SSBGen C++ has been
updated to the same behaviour, so the two should agree. MC only.

## What it emits (prefix `SSBGenCat_`)

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

The **reference is the MiniAOD `SSBAnalyzer`**, not the standalone SSBGen. This
module follows MiniAOD, with the audit's restorations applied
(`02_faithfulness_vs_miniaod.md` §9, `../04_DECISIONS.md` → D-2026-06-28-miniaod-reference):

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

The standalone SSBGen C++ has been updated to the **same** behaviour, so the two
should agree (validate with `script/validate_ssbgencat.py`). Integer/categorization
branches match exactly; float branches to `float32` precision.

## Input dependency

Reads `GenPart`, `GenJet`(+`hadronFlavour`), `GenDressedLepton`, `GenVisTau` from
the input. The MC branch list drops `GenVisTau*` from the **output** — fine,
because modules read the full input tree and only the derived
`Channel_Visible_Tau` is written. Keep `branch_file` as an output selection
(NanoAODTools default) so the input `GenVisTau` stays readable here.

## How to run

In a `config_CPV<year>UL.yaml`, point the analysis module at this file:

```yaml
analysis_module: ["modules/ssbGenCategorizer.py", "MODULES"]
```

The file exposes `MODULES = [SSBGenCategorizer()]`. The default branch list is
MC; the categorizer raises on data (no `GenPart`), so keep it out of data configs.

## Validation

`script/validate_ssbgencat.py` matches events by `(run, luminosityBlock, event)`
and compares the module output against a standalone SSBGen `GenCatTree` run on the
same file — integers exactly, floats within `--ftol`. Run it on lxplus once per
campaign change:

```bash
python script/validate_ssbgencat.py --nano slimmedNtuple.root --gencat gencat.root
```
