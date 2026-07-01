# Decision log — NtupleForge

> **Purpose:** the *why* behind non-obvious choices, with alternatives and
> current status, so no async contributor (human or AI) silently reopens a
> settled decision or treats a proposal as settled. **Append-only**; supersede by
> adding a new entry that flips an old one's status, don't edit history.
> **Audience:** all contributors. **Started:** 2026-06-27.
>
> Status vocabulary: **DECIDED** / **PROPOSED** / **OPEN** / **DEPRECATED**.
> Format: `ID — title` · status · date · context · decision · alternatives.

---

## D-2026-06-28-docs-v2 — adopt documentation-guideline v2 conventions
**DECIDED · 2026-06-28**

- **Context.** The documentation contract was upgraded to v2 (reading-order file
  numbering §3.1; the prompt-doc type §8). This repo adopts it.
- **Decision.** (a) Number content docs `NN_name.md` in reading order; `README.md`
  stays the unnumbered index. (b) Add `00_PROMPT.md`, the AI/contributor working
  agreement. (c) Rename the PyROOT helper `_nanoaod_compat.py` →
  `nanoaod_branch_access.py` (role-clear name); keep the archived legacy copy's name.
  **This required decoupling helper *shipping* from *naming*:** `crab/submit_crab.py`
  used to auto-include helpers by globbing `modules/_*.py`, so the leading underscore
  was load-bearing (dropping it broke the CRAB sandbox — see `06_troubleshooting.md`
  A0). It now ships every sibling `.py`, and `ssbGenCategorizer.py` hardens its import
  with a `__file__`-based `sys.path` insert for CRAB's flat import context.
  (d) Rename the CPV branch lists `branchlist_Run2_{Data,MC}.txt` →
  `branch_CPV_Run2_{Data,MC}.txt`. (e) Add off-by-default guarded logging to the
  categorizer (`SSBGENCAT_DEBUG=N`).
- **Alternatives.** Keep flat (unnumbered) docs → rejected: reading order was
  implicit and easy to get wrong for a cold reader. Keep `_nanoaod_compat.py` →
  rejected: the name did not convey its role (it is not a temporary shim; it is the
  NanoAOD branch-access layer). Numbering subdirs globally → rejected in favour of
  per-subdir local numbering (`ssb_gencat/01_…`), per §3.1.

## D-2026-06-28-miniaod-reference — MiniAOD `SSBAnalyzer` is the reference; restorations applied to BOTH codebases
**DECIDED · 2026-06-28 · supersedes D-2026-06-27-CPV-parity**

- **Context.** The reference of truth is the **MiniAOD `SSBAnalyzer` code**
  (`ssb_gencat/03_miniaod_origin.md`), *not* the intermediate standalone
  `SSBGenCategorizer`. SSBGen is itself a NanoAOD reproduction of MiniAOD and had
  documented gaps. So "match SSBGen byte-for-byte" was the wrong target; the right
  target is MiniAOD fidelity, and **both** the standalone SSBGen **and** the
  NtupleForge module must be updated to it.
- **Decision.** Apply the audit's restorations (`02_faithfulness_vs_miniaod.md` §9)
  to **both** codebases:
  1. **Background channel (§2).** `Channel_Idx`/`Channel_Lepton_Count` are summed
     over the **full** selected-particle list (MiniAOD §2.1), not just slots 8–11,
     so background boson-decay channels are recovered instead of forced to 0.
  2. **τ → ℓ final channel (§5).** `Channel_Idx_Final` resolves each selected τ by
     **walking the GenPart daughter map** (MiniAOD §2.2), and the resolved τ
     daughter is **appended to the GenPar family tree** via the same FillGenPar /
     PushGenPar the 12 slots use — so `GenPar_Count` grows for leptonic-τ events,
     matching MiniAOD. `GenDressedLepton` is no longer used.
  3. **Diagnostic (§1).** `Channel_Idx_Expanded` (additive) is kept in both;
     `Channel_Idx` stays MiniAOD-identical (0 on all-hadronic *or* malformed). SSBGen
     also re-emits the MiniAOD `cerr` on a malformed selection.
- **Kept (audit §3/§4/§6, physically preferable or NanoAOD-inherent).** Last-copy
  top for GenPar slots (CPV momenta from the faithful `GenTop`/`GenAnTop`); explicit
  W⁻ daughters; `GenBJet` via `GenJet_hadronFlavour`. **Unrecoverable from NanoAOD:**
  `GenBHad` hadron kinematics (b-quark proxy), official `GenBHad_FromTopWeakDecay`
  (mother-chain recompute), `GenJet_HCal/ECalEnergy`, B-frag weights.
- **Kept NanoAOD bonuses (not in MiniAOD):** `Channel_Visible_Tau` (`nGenVisTau`),
  `Channel_Tau_Lepton` (# of selected τ → e/μ, now from the gen-tree walk).
- **Status.** Module: applied + logic-tested in-container. SSBGen C++: applied,
  **must be compiled on lxplus** (no ROOT in the dev container). Confirm the two
  agree with `script/validate_ssbgencat.py`.

## D-2026-06-27-CPV-parity — ssbGenCategorizer defaults to SSBGen-exact output
**DEPRECATED · 2026-06-27 · superseded by D-2026-06-28-miniaod-reference**

- Interim decision (now reversed): defaulted the module to byte-exact SSBGen
  parity and left the #2/#5 restorations off. Reversed once it was clarified that
  **MiniAOD**, not SSBGen, is the reference — restorations are now applied to both.
  Retained here for history. Original rationale follows.

- **Context.** The audit (`ssb_gencat/02_faithfulness_vs_miniaod.md`) found the
  standalone SSBGen simplifies three things vs. its MiniAOD origin; restoring them
  (#1 diagnostic, #2 background channel, #5 τ→ℓ) would make the port *more*
  MiniAOD-faithful but would **diverge from SSBGen's own output**. The production
  requirement is output "perfectly identical to SSBGenCategorizer."
- **Decision.** The module reproduces SSBGen **exactly** for every SSBGen branch:
  background channel via the `isSignal` guard (→ 0), τ final channel via
  `GenDressedLepton`, channel from slots 8–11, last-copy top, ΔR≤0.4 ghost-B.
  The #2 and #5 MiniAOD restorations are **documented but NOT applied by default**.
  Only #1 is realized, as the *additive* `Channel_Idx_Expanded`, which changes no
  SSBGen branch (see D-…-channel-idx-expanded).
- **Alternatives.** (a) Apply #2/#5 by default → rejected: breaks byte-identity
  with SSBGen, which is the stated bar. (b) Config flag to toggle the restorations
  → deferred (added complexity now; revisit if the MiniAOD-faithful values are
  needed for backgrounds or soft-τ studies).
- **Consequence.** For non-ttbar backgrounds `Channel_Idx == 0` (as in SSBGen),
  and soft-τ final-channel edge cases follow `GenDressedLepton`. Flip only with an
  explicit decision here.

## D-2026-06-27-channel-idx-expanded — diagnostic name & semantics
**DECIDED · 2026-06-27**

- **Context.** MiniAOD folds an incomplete 12-slot build into `Channel_Idx == 0`
  (same as genuine all-hadronic) and signals it only via a printout, which SSBGen
  dropped. We want the signal back without perturbing the faithful `Channel_Idx`.
- **Decision.** Add integer `Channel_Idx_Expanded` = `Channel_Idx`, except `-999`
  when `isSignal` and any slot 2–11 `< 0`. `Channel_Idx` stays bit-identical to
  SSBGen/MiniAOD. End-of-job counter reports the rate.
- **Alternatives.** Boolean `Channel_Wellformed`/`Channel_Classified` → rejected
  in favour of the single integer (chosen name: `channel_idx_expanded`). Putting
  `-999` into `Channel_Idx` itself → rejected (would break faithful parity).

## D-2026-06-27-branch-placement — derived-only, prefixed
**DECIDED · 2026-06-27**

- **Decision.** The module writes only derived branches, under `SSBGenCat_`, and
  does **not** re-emit `GenJet_*`/`GenMET_*`/`PSWeight_*`/`run`/`lumi`/`event`,
  which the full-NanoAOD passthrough already provides with identical values. No
  separate `GenCatTree`.
- **Why.** Re-emitting raw collections would collide with passthrough names and
  duplicate data; the prefix avoids collisions for the derived family branches.

## D-2026-06-27-cpv-configs — per-year config naming & temporary fields
**DECIDED · 2026-06-27**

- **Decision.** One CRAB config per era, named `config_CPV<year>UL.yaml`
  (`2016preVFPUL`, `2016postVFPUL`, `2017UL`, `2018UL`) to stay distinct from the
  ttHH lists (`config_ttHH*`). In these files **only the `datasets:` entries are
  final** (sample name + DAS path, NanoAODv9); every `common:` field is a
  placeholder for the analyst (jobID, output_base, branch_file, splitting). Data
  and MC use different branch lists (`branch_CPV_Run2_Data.txt` /
  `branch_CPV_Run2_MC.txt`); the single-field schema holds one (set to MC).
- **Status notes.** OPEN follow-ups tracked in `01_STATUS.md`: NanoAODv15 migration;
  per-tier branch_file wiring; the flagged dataset-path anomalies to verify on DAS.
