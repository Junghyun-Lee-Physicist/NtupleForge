# Status — NtupleForge

> **Purpose:** the single place to answer "where are we right now?" for any
> contributor (human or AI) joining cold. **Audience:** all. **Updated:**
> 2026-06-27. Keep this current; details/why live in `04_DECISIONS.md` and `03_CHANGELOG.md`.

## Active workstreams

### CPV (top CP-violation) gen categorization — IN PROGRESS
- **Reference = MiniAOD `SSBAnalyzer`** (not the standalone SSBGen). The audit's
  restorations (`ssb_gencat/02_faithfulness_vs_miniaod.md` §9) are applied to **both**
  the module and the standalone SSBGen C++ — see `04_DECISIONS.md`
  → D-2026-06-28-miniaod-reference.
- **Module:** `modules/ssbGenCategorizer.py` — MiniAOD-faithful (full-list channel,
  τ→ℓ gen-tree walk + GenPar append, `Channel_Idx_Expanded`). Logic-tested in the
  dev container (all-hadronic / semileptonic-τ / background). **DONE** pending
  lxplus byte-identity validation.
- **SSBGen C++ (companion):** the standalone `SSBGenCategorizer` was updated in
  lockstep (same restorations). **Must be compiled on lxplus** — there is no ROOT
  in the dev container, so the C++ is syntax-reviewed but not compile-tested.
- **Configs:** `crabConfig/config_CPV{2016preVFPUL,2016postVFPUL,2017UL,2018UL}.yaml`
  — datasets transcribed from the user lists (NanoAODv9). **Datasets final;
  `common:` fields are placeholders.**
- **Branch lists:** `branches/branch_CPV_Run2_{Data,MC}.txt` added.
- **Validation tool:** `script/validate_ssbgencat.py`.

### ttHH → 4b — EXISTING
- `crabConfig/config_ttHH2017UL.yaml` (91 datasets, UL17 NanoAODv9). Stable.

## OPEN / next steps (CPV)

1. **lxplus build + validation.** Compile the updated SSBGen C++ on lxplus
   (no ROOT in the dev container), then run `validate_ssbgencat.py` on a real
   NanoAODv9 file (module output vs standalone SSBGen `GenCatTree`). Ints must
   match exactly; floats within tol.
2. **Config `common:` fields.** Set jobID / output_base / splitting for real.
3. **Per-tier `branch_file`.** Data and MC need different branch lists; the schema
   holds one (currently MC). Split into `_Data`/`_MC` configs or extend the schema.
4. **Dataset-path anomalies to verify on DAS** (normalized/flagged by the loader,
   cannot be checked offline):
   - 2016postVFP MC `QCD_Pt_170to300_TuneCP5_13TeV_pythia8`: campaign has `104X`
     (others `106X`) — likely a typo.
   - 2016preVFP / 2016postVFP MC: `QCD_Pt_3200toInf...` appears twice (normal +
     `-pilot_106X`); the pilot one is emitted as a commented `# [DUP]` line.
   - 2 paths had a missing leading `/` (2016postVFP QCD_Pt-600To800_Mu,
     QCD_Pt-170to300_EM) — prepended.
   - 2017 MC `DYJetsToLL_M-50_TuneCP5_madgraphMLM`: had an extra stray field and a
     missing `/` — normalized.
5. **NanoAODv15 migration.** Campaign strings change; re-derive dataset paths.
6. **Restorations (#2/#5/#1).** Applied to both module and SSBGen as of
   2026-06-28 (`04_DECISIONS.md` D-2026-06-28-miniaod-reference). Unrecoverable items
   (GenBHad hadron kinematics, official FromTopWeakDecay, GenJet HCal/ECal energy,
   B-frag weights) remain best-effort / friend-tree only.

## Documentation
- **2026-06-27:** added `04_DECISIONS.md` (decision log) and `01_STATUS.md` (both were
  missing vs. the documentation guideline) and `ssb_gencat/README.md` (subdir index).
- **2026-06-28 (guideline v2):** docs numbered in reading order (`NN_name.md`); added
  `00_PROMPT.md` (AI/contributor working agreement); renamed the PyROOT helper to
  `modules/nanoaod_branch_access.py` and the CPV branch lists to
  `branch_CPV_Run2_{Data,MC}.txt`; added `SSBGENCAT_DEBUG` guarded logging. See
  `04_DECISIONS.md` → D-2026-06-28-docs-v2.
