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

## D-2026-07-02-prewarm-readers — pre-register all branch readers in beginFile; no mid-loop reader creation
**DECIDED · 2026-07-02 · complements D-2026-07-01-count-branch-length (which was necessary but not sufficient)**

- **Context.** The count-branch fix (A12) removed the out-of-bounds probe, but
  the second CRAB production still crashed (A13): nanoAOD-tools'
  `_remakeAllReaders` rebuilds every reader on a new TTreeReader whenever a
  reader is lazily added mid-loop, invalidating previously bound reader
  objects. Proved from the CMSSW_14_2_X source and reproduced in-container
  against the real framework files.
- **Decision.** The module declares its complete input-branch set
  (`GEN_ARRAY_BRANCHES`, `GEN_COUNTER_BRANCHES`) and `beginFile` registers all
  readers via `inputTree.arrayReader/valueReader` before the first `gotoEntry`
  (clean reader → no remake). `analyze()` binds locals through
  `_read_arrays()`, which re-binds once and warns if the reader version ever
  changes mid-pass (future-edit safety net). Partial gen inputs fail fast in
  `beginFile`.
- **Alternatives.** (a) `Collection`/`Object` everywhere → also correct
  (per-access re-resolution is remake-immune), but pays a `getattr` +
  `Object.__getattr__` per element in the hot loop; pre-registration gives the
  same safety with direct array reads. Documented as the always-safe
  alternative in `06_nanoaod_branch_access.md` Pitfall 4. (b) Re-binding
  locals per use without pre-registration → still incurs remakes on event 0
  and leaves a trap for edits. (c) Patching the framework → rejected before
  (fork maintenance).
- **Status.** Framework-level test passes in-container (real
  `treeReaderArrayTools`/`datamodel`/`eventloop`, mock ROOT with cppyy
  lifetimes). **Real-ROOT confirmation on lxplus pending.**

## D-2026-07-02-per-tier-configs — CPV configs split into _Data / _MC files
**DECIDED · 2026-07-02 · closes the OPEN item in D-2026-06-27-cpv-configs; root fix for A11**

- **Context.** The combined `config_CPV<era>UL.yaml` held ONE `branch_file` and
  ONE `analysis_module` for a mixed data+MC `datasets:` block, so the
  2026-07-01 submission ran data with the MC branch list and the MC-only gen
  module (`05_troubleshooting.md` A11). The module-side no-op guard prevents
  the crash but not the wrong branch list.
- **Decision.** Each era config is split by DAS tier (path suffix `/NANOAOD` =
  data, `/NANOAODSIM` = MC) into
  `config_CPV<era>_Data.yaml` — `modules/noop.py` + `branch_CPV_Run2_Data.txt` —
  and `config_CPV<era>_MC.yaml` — `modules/topCPVCategorizer.py` +
  `branch_CPV_Run2_MC.txt`. The combined files are **removed** so the mixed
  wiring cannot be resubmitted by habit. Dataset counts preserved
  (2016preVFP 30+73, 2016postVFP 15+75, 2017UL 29+73, 2018UL 12+74). jobID /
  output_base placeholders carry a `_Data`/`_MC` suffix so the two campaigns
  don't share a tag by accident.
- **Alternatives.** Extending the schema (per-tier sections in one YAML +
  `submit_crab.py` changes) → rejected for now: more code on the submission
  path for the same effect; two files per era is explicit and needs zero code.
  Revisit if per-tier fields multiply.
- **Status.** YAML-parse verified in-container; **a real CRAB submission must
  confirm** (no CRABClient here).

## D-2026-07-01-rename-topcpv — rename ssbGenCategorizer → topCPVCategorizer; SSBAnalyzer preserved
**DECIDED · 2026-07-01**

- **Context.** The module family carried the historical "SSB" name inherited
  from the MiniAOD analyzer lineage; the analysis it serves is top CP-violation
  (TopCPV). The name should say what it is for.
- **Decision.** Rename all artifacts **we own**: module file/class
  (`topCPVCategorizer.py` / `TopCPVCategorizer`), **branch prefix**
  (`TopCPVCat_`), debug env (`TOPCPVCAT_DEBUG`), validator
  (`validate_topcpvcat.py`), docs dir (`docs/TopCPV/`), and the "SSBGen"
  shorthand for the standalone C++ (now "the standalone TopCPV"). **Preserve
  the external MiniAOD class name `SSBAnalyzer` verbatim everywhere** — it is
  the reference of truth and not ours to rename; renaming it in quotes/
  transcriptions would falsify the reference (`TopCPV/03_miniaod_origin.md`).
- **Consequences.** Ntuples produced before/after the rename have different
  derived-branch prefixes (`SSBGenCat_*` vs `TopCPVCat_*`); downstream readers
  must switch. Rename-safety (00_PROMPT §7) was applied: `submit_crab.py`
  ships sibling helpers name-agnostically and derives `-I` from the config's
  module path, `config_CPV*` updated, repo-wide grep shows zero stale tokens;
  a real CRAB submission must still confirm (no CRAB here).
- **Alternatives.** Keep the SSB name → rejected (opaque to newcomers, and
  actively confusing next to the *preserved* `SSBAnalyzer` reference). Rename
  `SSBAnalyzer` too → rejected (external reference; would corrupt the verbatim
  origin doc).

## D-2026-07-01-count-branch-length — collection lengths from the count branch; array probing banned
**DECIDED · 2026-07-01 · supersedes the A3 "array length" doctrine**

- **Context.** The first CPV CRAB production segfaulted on MC:
  `safe_len(event.GenPart_pdgId)` → `len()` `TypeError` on the raw
  `TTreeReaderArray` proxy (CMSSW_14_2_1) → fallback **out-of-bounds indexing
  probe** → `TTreeReaderArray::At(i≥size)` is ROOT undefined behaviour →
  SIGSEGV (not a catchable exception). Incident `05_troubleshooting.md` A12.
- **Re-examination of the premise.** The probe existed because of A3
  ("`nGenPart`/`nGenJet` are unreliable as lengths; use the array"). Revisiting
  the 2026-04 session: A3's broken counters were observed **while A4 was
  active** (input keep/drop → zombie branches). A4's fix (`branchsel=None`,
  input read in full) removed the counters' failure mode; A3's doctrine was a
  mis-attributed symptom, not an independent fact. With the input unfiltered,
  `nX` is the canonical NanoAOD length (format guarantee `nX == len(X_*)`).
- **Decision.** All collection lengths in Python modules come from the **count
  branch**: `count(event, "X")` / `opt_count(event, "X")` (new helpers in
  `nanoaod_branch_access.py`, reading `event.nX` through `to_int`). Element
  access is **in-bounds only**. `safe_len` is de-fanged (no probe; fails fast
  with `TypeError`) and deprecated for collections. Docs corrected
  (`06_nanoaod_branch_access.md` Pitfall 2 + history).
- **Alternatives.** (a) Full `Collection(event, "X")` rewrite (standard
  nanoAOD-tools idiom) → equivalent length source (`nX`), but constructs an
  `Object` per element in the hot loop and is a much larger diff for identical
  semantics; `count()` keeps the minimal change. Acceptable later if per-object
  access is wanted. (b) Keep the probe but bound it by `GetSize()` → rejected:
  `GetSize()` on an un-setup proxy is itself the crashing call path; any
  array-side probing keeps UB in reach. (c) Patch nanoAOD-tools upstream →
  rejected (fork maintenance; see `06_nanoaod_branch_access.md`).
- **Status.** Logic-tested in-container (stub harness). **Byte-identity and
  real-file behaviour must be confirmed on lxplus** (`-N 10` +
  `validate_topcpvcat.py`) before production.

## D-2026-07-01-docs-topcpv-tthh-split — per-workstream doc dirs; ONE prompt doc at the root
**DECIDED · 2026-07-01**

- **Context.** The repo now hosts two workstreams (TopCPV production, ttHH
  passthrough + legacy record). Flat `docs/` mixed their reference material;
  the prompt-doc question (one vs per-dir) needed an explicit call.
- **Decision.** (a) Workstream reference docs live in subdirectories with local
  numbering and local READMEs: **`docs/TopCPV/`** (module reference, audit,
  MiniAOD origin) and **`docs/ttHH/`** (physics, legacy pipeline record,
  `legacy/` archive). (b) **Cross-cutting logs stay at the root** — STATUS,
  CHANGELOG, DECISIONS, troubleshooting, architecture, branch-access — because
  both workstreams share one pipeline and one incident history (one fact, one
  place; guideline §7: different change-axes → separate docs; shared
  change-axis → shared doc). (c) **One prompt doc**, root `00_PROMPT.md`,
  covering both workstreams with per-workstream reference-of-truth entries.
  Root docs renumbered contiguously after the moves (§3.1); links rewritten in
  the same change; link check passed.
- **Alternatives.** Per-directory `00_PROMPT.md` instances → rejected: the
  working agreement (environment limits, validation duties, style, change
  discipline) is identical for both workstreams, so two copies would duplicate
  ~90% of the contract and drift (§4 "one fact, one place"); the parts that
  *do* differ (reference of truth, branch prefix) are two short bullets, not a
  document. Keeping physics/legacy docs flat at the root → rejected: their
  change-axis is per-workstream and the flat numbering forced unrelated
  renumbering on every addition.

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
  was load-bearing (dropping it broke the CRAB sandbox — see `05_troubleshooting.md`
  A0). It now ships every sibling `.py`, and `topCPVCategorizer.py` hardens its import
  with a `__file__`-based `sys.path` insert for CRAB's flat import context.
  (d) Rename the CPV branch lists `branchlist_Run2_{Data,MC}.txt` →
  `branch_CPV_Run2_{Data,MC}.txt`. (e) Add off-by-default guarded logging to the
  categorizer (`TOPCPVCAT_DEBUG=N`).
- **Alternatives.** Keep flat (unnumbered) docs → rejected: reading order was
  implicit and easy to get wrong for a cold reader. Keep `_nanoaod_compat.py` →
  rejected: the name did not convey its role (it is not a temporary shim; it is the
  NanoAOD branch-access layer). Numbering subdirs globally → rejected in favour of
  per-subdir local numbering (`TopCPV/01_…`), per §3.1.

## D-2026-06-28-miniaod-reference — MiniAOD `SSBAnalyzer` is the reference; restorations applied to BOTH codebases
**DECIDED · 2026-06-28 · supersedes D-2026-06-27-CPV-parity**

- **Context.** The reference of truth is the **MiniAOD `SSBAnalyzer` code**
  (`TopCPV/03_miniaod_origin.md`), *not* the intermediate standalone
  `TopCPVCategorizer`. TopCPV is itself a NanoAOD reproduction of MiniAOD and had
  documented gaps. So "match TopCPV byte-for-byte" was the wrong target; the right
  target is MiniAOD fidelity, and **both** the standalone TopCPV **and** the
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
     `Channel_Idx` stays MiniAOD-identical (0 on all-hadronic *or* malformed). TopCPV
     also re-emits the MiniAOD `cerr` on a malformed selection.
- **Kept (audit §3/§4/§6, physically preferable or NanoAOD-inherent).** Last-copy
  top for GenPar slots (CPV momenta from the faithful `GenTop`/`GenAnTop`); explicit
  W⁻ daughters; `GenBJet` via `GenJet_hadronFlavour`. **Unrecoverable from NanoAOD:**
  `GenBHad` hadron kinematics (b-quark proxy), official `GenBHad_FromTopWeakDecay`
  (mother-chain recompute), `GenJet_HCal/ECalEnergy`, B-frag weights.
- **Kept NanoAOD bonuses (not in MiniAOD):** `Channel_Visible_Tau` (`nGenVisTau`),
  `Channel_Tau_Lepton` (# of selected τ → e/μ, now from the gen-tree walk).
- **Status.** Module: applied + logic-tested in-container. TopCPV C++: applied,
  **must be compiled on lxplus** (no ROOT in the dev container). Confirm the two
  agree with `script/validate_topcpvcat.py`.

## D-2026-06-27-CPV-parity — topCPVCategorizer defaults to TopCPV-exact output
**DEPRECATED · 2026-06-27 · superseded by D-2026-06-28-miniaod-reference**

- Interim decision (now reversed): defaulted the module to byte-exact TopCPV
  parity and left the #2/#5 restorations off. Reversed once it was clarified that
  **MiniAOD**, not TopCPV, is the reference — restorations are now applied to both.
  Retained here for history. Original rationale follows.

- **Context.** The audit (`TopCPV/02_faithfulness_vs_miniaod.md`) found the
  standalone TopCPV simplifies three things vs. its MiniAOD origin; restoring them
  (#1 diagnostic, #2 background channel, #5 τ→ℓ) would make the port *more*
  MiniAOD-faithful but would **diverge from TopCPV's own output**. The production
  requirement is output "perfectly identical to TopCPVCategorizer."
- **Decision.** The module reproduces TopCPV **exactly** for every TopCPV branch:
  background channel via the `isSignal` guard (→ 0), τ final channel via
  `GenDressedLepton`, channel from slots 8–11, last-copy top, ΔR≤0.4 ghost-B.
  The #2 and #5 MiniAOD restorations are **documented but NOT applied by default**.
  Only #1 is realized, as the *additive* `Channel_Idx_Expanded`, which changes no
  TopCPV branch (see D-…-channel-idx-expanded).
- **Alternatives.** (a) Apply #2/#5 by default → rejected: breaks byte-identity
  with TopCPV, which is the stated bar. (b) Config flag to toggle the restorations
  → deferred (added complexity now; revisit if the MiniAOD-faithful values are
  needed for backgrounds or soft-τ studies).
- **Consequence.** For non-ttbar backgrounds `Channel_Idx == 0` (as in TopCPV),
  and soft-τ final-channel edge cases follow `GenDressedLepton`. Flip only with an
  explicit decision here.

## D-2026-06-27-channel-idx-expanded — diagnostic name & semantics
**DECIDED · 2026-06-27**

- **Context.** MiniAOD folds an incomplete 12-slot build into `Channel_Idx == 0`
  (same as genuine all-hadronic) and signals it only via a printout, which TopCPV
  dropped. We want the signal back without perturbing the faithful `Channel_Idx`.
- **Decision.** Add integer `Channel_Idx_Expanded` = `Channel_Idx`, except `-999`
  when `isSignal` and any slot 2–11 `< 0`. `Channel_Idx` stays bit-identical to
  TopCPV/MiniAOD. End-of-job counter reports the rate.
- **Alternatives.** Boolean `Channel_Wellformed`/`Channel_Classified` → rejected
  in favour of the single integer (chosen name: `channel_idx_expanded`). Putting
  `-999` into `Channel_Idx` itself → rejected (would break faithful parity).

## D-2026-06-27-branch-placement — derived-only, prefixed
**DECIDED · 2026-06-27**

- **Decision.** The module writes only derived branches, under `TopCPVCat_`, and
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
