# NtupleForge Documentation

Technical documentation for NtupleForge. The top-level
[`../README.md`](../README.md) covers only setup and the commands needed to
run the pipeline; everything deeper lives here.

> **Editing the code?** Read **[`DeveloperGuideline.md`](DeveloperGuideline.md)** first, then
> read the rest of this directory before making changes (Rule 0).

## Contents

- **[DeveloperGuideline.md](DeveloperGuideline.md)** — Guidelines for anyone editing
  NtupleForge: read all docs first, log every change (CHANGELOG) and every
  problem+fix (troubleshooting), and which doc each kind of record goes in.

- **[architecture.md](architecture.md)** — The framework NtupleForge sits on:
  where the CMS `PostProcessor` lives in CMSSW and what it does, the per-event
  `Module` event loop, how the `modules/` directory is organized, **a
  copy-followable how-to for writing your own module (adding branches /
  applying cuts)**, and the critical input-vs-output branch-selection rule.

- **[physics.md](physics.md)** — The physics basis: the ttHH→4b analysis
  target, why tt+jets is categorized, 5FS/4FS sample stitching, the five
  category definitions, the `genTtbarId` encoding, and why five categories and
  not seven.

- **[legacy_ttbar_pipeline.md](legacy_ttbar_pipeline.md)** — Full
  implementation record of the retired tt+jets categorization pipeline (custom
  `Module` + custom branches + slimming list + optional skim cut), the
  two-algorithm design, and a checklist to rebuild an equivalent. Verbatim
  source under [`legacy/code/`](legacy/code/).

- **[troubleshooting.md](troubleshooting.md)** — The consolidated incident log
  (every bug hit during development: symptom, error signature, root cause, fix,
  validation) and how the pipeline's validation mechanisms work (cross-check
  confusion matrix, debug CSV, skim-efficiency checking).

- **[nanoaod_compat.md](nanoaod_compat.md)** — Why the PyROOT compatibility
  shim (`_nanoaod_compat.py`) was needed: `UChar_t` branches returning `bytes`
  instead of `int`, and raw `TTreeReaderArray` proxies with no `len()`.
  Essential reading before any future module reads NanoAOD vector branches
  from Python.

- **[CHANGELOG.md](CHANGELOG.md)** — Curated change history, including the
  shift to full-NanoAOD passthrough and carried-forward known issues.

## Mapping to the five documentation categories

| Category | Document |
|---|---|
| Update log | [CHANGELOG.md](CHANGELOG.md) |
| Code structure, logic & how it works (incl. how to add branches/cuts) | [architecture.md](architecture.md) |
| Legacy ttbar categorization (detailed) | [legacy_ttbar_pipeline.md](legacy_ttbar_pipeline.md) |
| Problem log, fixes & validation | [troubleshooting.md](troubleshooting.md) |
| Physics basis | [physics.md](physics.md) |

(Plus [DeveloperGuideline.md](DeveloperGuideline.md) for contributor rules and
[nanoaod_compat.md](nanoaod_compat.md) for the PyROOT shim deep-dive.)

## The `legacy/` archive

[`legacy/code/`](legacy/code/) holds verbatim, **unmaintained** copies of the
code that ran the old categorization pipeline — the categorizer module, the
compat shim, the slimming branch list, the branch inventories, and the
original CRAB config. Nothing here is on the build or import path; it is
reference material. To rebuild a similar pipeline, copy the relevant files
back into the live tree (checklist in
[legacy_ttbar_pipeline.md](legacy_ttbar_pipeline.md) §9).
