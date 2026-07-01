# `ssb_gencat` — gen-level categorization for the CPV analysis

> **Purpose:** index for the CPV gen-level categorizer docs. **Audience:** anyone
> touching `modules/ssbGenCategorizer.py` or the `config_CPV*` ntuples.
> **Status:** active (NanoAODv9). **Updated:** 2026-06-28.

This folder documents the NanoAOD module that reproduces the **MiniAOD
`SSBAnalyzer`** gen-level top-decay categorization (the reference of truth). The
standalone C++ `SSBGenCategorizer` is a companion reproduction held to the same
MiniAOD behaviour, not itself the reference.

## Read in this order (local numbering)

1. **[`01_module.md`](01_module.md)** — how to run the module and the exact branches
   it emits (start here for production wiring).
2. **[`02_faithfulness_vs_miniaod.md`](02_faithfulness_vs_miniaod.md)** — the audit:
   where the port agrees with or differs from the MiniAOD origin, and which
   differences were restored vs. are unrecoverable.
3. **[`03_miniaod_origin.md`](03_miniaod_origin.md)** — verbatim MiniAOD `SSBAnalyzer`
   source the port is measured against.
4. **`GenPart_channel_definition.md`** *(SSBGen package)* — the channel-code
   convention (lepton sums, τ sign, jet digit codes).

## Key facts (one-line each, details in the files above)

- **Reference = MiniAOD `SSBAnalyzer`** (`03_miniaod_origin.md`); the audit's
  restorations are applied to **both** the module and the standalone SSBGen
  (`../04_DECISIONS.md` → D-2026-06-28-miniaod-reference).
- `Channel_Idx` summed over the **full** selected list (background channels
  recovered); `Channel_Idx_Final` resolves τ→ℓ by walking the GenPart daughter map
  and **appends the τ daughter to GenPar** (`01_module.md`).
- Derived branches only, prefix `SSBGenCat_`; raw gen collections come from the
  full-NanoAOD passthrough. Additive `Channel_Idx_Expanded` diagnostic.
- Kept (audit §3/§4/§6): last-copy top, explicit W⁻ daughters, `GenBJet` via
  `GenJet_hadronFlavour`. Unrecoverable from NanoAOD: `GenBHad` hadron kinematics,
  official `FromTopWeakDecay`, GenJet HCal/ECal energy, B-frag weights.
- Byte-identity is validated on lxplus with `script/validate_ssbgencat.py`
  (no ROOT / test file / network in the dev container).
