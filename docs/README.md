# NtupleForge Documentation

Technical documentation for NtupleForge. The top-level
[`../README.md`](../README.md) covers only setup and the commands needed to
run the pipeline; everything deeper lives here.

Docs are **numbered in reading order** (`NN_name.md`) — read them in sequence to
understand the project and its latest state. See the documentation contract
`DOCUMENTATION_GUIDELINE` (§3.1 numbering, §8 the prompt doc).

> **Editing the code?** Read **[`00_PROMPT.md`](00_PROMPT.md)** (the AI/contributor
> working agreement) and **[`08_DeveloperGuideline.md`](08_DeveloperGuideline.md)**
> first, then the rest in order before making changes.

## Reading order

- **[00_PROMPT.md](00_PROMPT.md)** — Working agreement for AI/contributors: persona,
  the reference of truth (MiniAOD), what this environment can't do (no ROOT/compile),
  and the validation + change-notification duties. Read first.
- **[01_STATUS.md](01_STATUS.md)** — "Where are we right now?": active workstreams
  (ttHH, CPV) and the open next-steps list.
- **[02_physics.md](02_physics.md)** — Physics basis: the ttHH→4b analysis target,
  why tt+jets is categorized, 5FS/4FS stitching, the five categories, the
  `genTtbarId` encoding, and why five and not seven.
- **[03_CHANGELOG.md](03_CHANGELOG.md)** — Curated change history (append-only),
  including the full-NanoAOD passthrough shift and the CPV categorizer.
- **[04_DECISIONS.md](04_DECISIONS.md)** — Decision log: the *why* behind non-obvious
  choices, with alternatives and DECIDED/PROPOSED/OPEN/DEPRECATED status. Append-only.
- **[05_architecture.md](05_architecture.md)** — The framework NtupleForge sits on:
  the CMS `PostProcessor`, the per-event `Module` loop, how `modules/` is organized,
  **a copy-followable how-to for writing a module (adding branches / cuts)**, and the
  input-vs-output branch-selection rule.
- **[ssb_gencat/](ssb_gencat/README.md)** — Component reference for the CPV gen-level
  categorizer (`modules/ssbGenCategorizer.py`): module + branches
  ([01_module.md](ssb_gencat/01_module.md)), the MiniAOD-faithfulness audit, and the
  verbatim MiniAOD origin. Validated by `script/validate_ssbgencat.py`.
- **[06_troubleshooting.md](06_troubleshooting.md)** — Consolidated incident log
  (every bug: symptom, signature, root cause, fix, validation) and how validation works.
- **[07_nanoaod_branch_access.md](07_nanoaod_branch_access.md)** — The mandatory
  PyROOT read helpers (`modules/nanoaod_branch_access.py`: `to_int`, `safe_len`) and
  the two pitfalls they guard (`UChar_t`-as-bytes; unreliable scalar counters).
  Essential before any module reads NanoAOD vector branches from Python.
- **[08_DeveloperGuideline.md](08_DeveloperGuideline.md)** — Contributor rules: read
  all docs first, log every change (changelog) and every problem+fix (troubleshooting),
  and which doc each record goes in.
- **[09_legacy_ttbar_pipeline.md](09_legacy_ttbar_pipeline.md)** — Full record of the
  retired tt+jets categorization pipeline (custom `Module` + branches + slimming list +
  skim cut) and a rebuild checklist. Verbatim source under [`legacy/code/`](legacy/code/).

## The `legacy/` archive

[`legacy/code/`](legacy/code/) holds verbatim, **unmaintained** copies of the code
that ran the old categorization pipeline — the categorizer module, the compat shim
(archived under its original name `_nanoaod_compat.py`), the slimming branch list,
the branch inventories, and the original CRAB config. Nothing here is on the build
or import path; it is reference material. To rebuild a similar pipeline, copy the
relevant files back into the live tree (checklist in
[09_legacy_ttbar_pipeline.md](09_legacy_ttbar_pipeline.md) §9).
