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

## D-2026-09-11-run2-scope-2016 — the Run 2 request covers all four era-halves; QCD-HT switches to the PSWeights name
**DECIDED · 2026-09-11 · user decision · detail: `09_v15_migration_log.md` §16**

- **Context.** The Run 2 v15 work had only ever looked at UL17 and UL18 (every ttHH registry row read
  `2017UL,2018UL`); 2016 appeared only in the CPV workstream. Before the MC request went out, 2016 was
  checked with `das_inventory.sh` on four campaigns: UL16 preVFP / postVFP NanoAODv15
  (`RunIISummer20UL16NanoAODAPVv15-150X_mcRun2_asymptotic_preVFP_v1*`,
  `RunIISummer20UL16NanoAODv15-150X_mcRun2_asymptotic_v1*`) and the two matching v9 campaigns as a baseline.
- **Result.** The **four Run 2 v15 `NOT_FOUND` key sets are identical** (27 keys each, diff = 0): the same five
  samples are missing in 2016 as in 2017/2018 (`TTHHto4b`, `TT4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`), and they are
  all present in 2016 v9 (129 EXACT / 7 NOT_FOUND there, the 7 being the QCD-HT naming below). `TTZToQQ` exists
  in 2016 v15 as well (6.28M / 5.40M), so D-2026-09-11-ttz-hadronic-from-ttzqq holds for 2016 unchanged.
- **Decision.** (a) The central request is the five samples in **all four era-halves — 28 datasets, ≈162M events**
  (2016: 7 datasets and 27.1M events per half, NanoAODv9 counts; MiniAODv2 parents not yet queried).
  (b) All 62 ttHH rows of `samples_registry.txt` now carry
  `2016postVFPUL,2016preVFPUL,2017UL,2018UL`; each era selects 45 `had` MC rows.
  (c) **QCD-HT PRIMARY changed** from `QCD_HT<bin>_TuneCP5_13TeV-madgraphMLM-pythia8` (the v9 name, which exists
  in no v15 campaign) to `QCD_HT<bin>_TuneCP5_PSWeights_13TeV-madgraph-pythia8`, which is EXACT in all four v15
  campaigns — same process and bin edges, so the KEY, xsec entry, filelists and patch names are unchanged. The CPV
  rows already pointed at these datasets under their own keys, which is what confirmed the choice (2016 also has a
  `-madgraphMLM-pythia8` PSWeights variant; not used, so one name covers all four halves).
- **Consequences.** A v15 scan of 2017/2018 now resolves QCD-HT, so the "27 NOT_FOUND" of the 2026-09-11 morning
  inventory becomes 20 (of which `had`: the five requested samples + `TTTW`). `TTTW` stays broken for v15 by
  design — its v15 replacement is two charge-split datasets and needs two KEYs plus two xsec entries (OPEN, noted
  in the registry; no central request is involved). Data PDs were **not** extended to 2016: `JetHT` / `BTagCSV`
  need the per-run-era row pattern the CPV rows use (`<PD>_Run2016B-ver1`, …) and a DAS scan first.
  **The analyzer side of 2016 was not part of this decision and is not free**: `tempTTHH` carries only
  `data/samples_2017UL.json` and `samples_2018UL.json`, and `tempTTHH/docs/reference/LUMI_SOURCES.md`
  documents 2017–2018 luminosity only. Using 2016 needs xsec tables for both halves, 2016 luminosity,
  golden JSON, trigger paths and efficiencies, b-tag SFs and JEC/JER for 2016. The request is placed now
  because production takes months; extending the analysis to 2016 is separate work that has not been scoped.
- **Alternatives considered.** (a) Keep 2017/2018 only and request 2016 later — rejected by the user: the same
  five samples, the same production step, and a second request means a second wait. (b) Give 2016 its own
  registry file (the D-R3-3 precedent) — rejected: only QCD-HT differed, and it turned out to differ by version,
  not by year. (c) A second QCD-HT row with disjoint ERAS — unnecessary once the PSWeights name was found to
  cover all four.

---

## D-2026-09-11-ttz-hadronic-from-ttzqq — Run 2 on v15: ttZ(hadronic Z) from `TTZToQQ`; `TTZToBB` not requested
**DECIDED · 2026-09-11 · user decision · detail: `ttHH/03_run3_plan.md` §4.7, `09_v15_migration_log.md` §15**

- **Context.** `TTZToBB_TuneCP5_13TeV-amcatnlo-pythia8` (the Run 2 v9 analysis
  sample for ttZ, Z→bb) has no NanoAODv15 (UL17, UL18) and was one of the six
  samples for which a central "NanoAODv15 from MiniAODv2" request — or, as
  fallback, the enriched private production (TTHHGenCategoryTools D17) — was
  planned. The 2026-09-11 campaign inventory showed that v15 does carry the
  inclusive `TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8` (UL17 13.98M, UL18 19.82M,
  VALID), which Run 2 v9 never used in the ttHH workstream.
- **Decision.** The Run 2 v15 analysis takes ttZ with a hadronic Z from
  `TTZToQQ` (Z→bb + cc + light), exactly as Run 3 does (`TTZ-ZtoQQ-1Jets`;
  same registry KEY `TTZToQQ`, so xsec table and filelists stay year-generic).
  `TTZToBB` is demoted to workstream `alt` (v9-only; never combined with
  `TTZToQQ` — Z→bb double counting). Consequences: the central request and the
  enriched fallback list shrink from six to **five** samples (`TTHHto4b`,
  `TT4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`; 14 datasets, ≈108M MiniAODv2 events);
  the v9 → v15 ttZ treatment changes (documented in the migration log).
- **Why it is also the better choice for the fully hadronic channel.** The
  4b selection is entered by ttZ(bb) directly and by ttZ(cc) / ttZ(light)
  through mistags; v9 modelled only the bb slice. The inclusive sample covers
  all three with one cross section (σ(ttZ)·BR(Z→qq)), and the Z→bb component
  is ~22 % of Z→qq (PDG branching ratios, not a project document), i.e. about
  3.0M / 4.3M events in UL17 / UL18. **How much statistics this background
  actually needs was not checked against a project document** — the relative
  ttZ yield in our selection is not recorded in `ttHH/01_physics.md` or the
  analyzer docs. Treat the sufficiency claim as OPEN until it is checked
  against the analyzer's own yields.
- **Open item this touches.** The ttZ cross section is already flagged:
  `TTZToBB` = 861 fb (ttHH AN Tab.16) versus ttZ = 841 fb (AN Tab.9), definition
  unresolved (`tempTTHH/docs/CHANGELOG.md`, `00_START_HERE.md` §4 "물리 값 확정").
  Switching to `TTZToQQ` replaces that entry with σ(ttZ)·BR(Z→qq), so the
  definition must be settled when the new xsec entry is written, not before.
- **Alternatives considered.** (a) Request `TTZToBB` NanoAODv15 from MiniAODv2
  with the other five — rejected: one more production for a sample whose
  physics the existing `TTZToQQ` already contains, and a Run 2 / Run 3
  asymmetry. (b) Private enriched production of `TTZToBB` — rejected for the
  same reason (D17 list shrinks instead).
- *(Scope note, same day: the five-sample list is unchanged but now covers all
  four Run 2 era-halves — 28 datasets, ≈162M — see
  D-2026-09-11-run2-scope-2016. The "14 datasets, ≈108M" above was the
  2017/2018-only figure at the time of writing.)*

---

## D-2026-09-07-run3-scope — Run 3 on NanoAODv15 only, separate registry, no name guessing, `had` first
**DECIDED (D-R3-1…5) / PROPOSED (D-R3-6) · 2026-09-07 · detail table: `ttHH/03_run3_plan.md` §1**

- **Context.** The ttHH → 4b pipeline is being widened to Run 3 while the
  Run 2 v9 → v15 migration is closing. Run 3 primary-dataset names, PDs, MC
  campaigns, HT binning, cleaning rules and cross sections all differ from
  Run 2, and CMS twiki pages could not be opened in the working session.
- **Decision.**
  1. **Eras** 2022, 2022EE, 2023, 2023BPix, 2024; 2025 investigated first
     (campaign existence), produced only if a golden JSON and MC campaign exist.
  2. **NanoAODv15 only** — one schema for Run 2 UL re-nano and Run 3, one set
     of tools (`compare_v9_v15.py`, branch inventories).
  3. **`script/samples_registry_run3.txt` is a separate file.** The Run 2
     registry's premise "PRIMARY is era-independent" breaks at 13.6 TeV. KEYs
     stay identical to Run 2 so xsec DB, filelists and patch-file names carry
     across years.
  4. **No dataset-name guessing.** Primary names enter the Run 3 registry only
     from `script/das_discover_run3.sh` `HIT|` lines (family wildcards answered
     by DAS). Same rule `das_scan.sh` already enforces for campaign strings.
  5. **`had`/`lep` use tags** in the WORKSTREAM column (Run 2 rows tagged today:
     47/16/1). **Production order: `--workstream had` first** — the leptonic
     set (DY, W→ℓν) exists for data/MC agreement tests, not for the signal
     region. User decision 2026-09-07.
  6. (PROPOSED) 13.6 TeV cross sections are taken fresh (XSDB / GenXSecAnalyzer);
     no reuse of `samples_2017UL.json` values.
- **Alternatives considered.** (a) One registry with an era-conditional PRIMARY
  column — rejected: every reader would need era logic and the 2-column join
  key breaks. (b) Hand-writing Run 3 names from memory to save a DAS round —
  rejected: Summer22 → Summer24 naming drifts even within Run 3; the 2018 scan
  showed 8 of 63 Run 2 names already needed relaxed matching. (c) Produce
  had+lep together — rejected by the user; lep doubles QCD-free CPU for a
  cross-check sample set.
- **Status notes.** Everything in `03_run3_plan.md` §2 marked "기억" (from
  memory) is not yet a decision input — it must be verified against the twiki
  before any value is coded (OPEN item 23 in `01_STATUS.md`).
- **Amendment, same day (after the DAS probe + discovery).** **D-R3-7 —
  PROPOSED:** the first Run 3 round is **2024 + 2025 with Summer24 NanoAODv15 MC**
  (PPD: no 2025 MC campaign yet). 2022/2022EE/2023/2023BPix are deferred: their
  v15 re-nano is partial — the same 70 standard datasets per era (ttbar, ttV,
  single top t/s/tW, VV, QCD-PT, DY, W→ℓν), no signal / ttbb / QCD-HT / ttH / tH / ttVV — so a v15-only
  hadronic set cannot be assembled for them without mixing in NanoAODv12, which
  D-R3-2 forbids. Revisit when a fuller v15 re-nano exists. Also recorded: Summer24
  v15 carries the ttHH signal and the former "absent six" centrally — including
  `TT4b`, which the 2026-09-07 text listed as missing: it exists as
  `TT4B_TuneCP5_13p6TeV_madgraph-pythia8` and was missed by a case-sensitive DAS
  pattern (corrected 2026-09-10, `03_run3_plan.md` §4.6) — so D17 (enriched
  NanoAOD) does **not** extend to Run 3 (`03_run3_plan.md` §4.5).
- **D-R3-8 (2026-09-10) — `TT4b` in Run 3 = central `TT4B`.** No private tt+4b
  production and no `TTBB*`-based substitute for Run 3; the registry key `TT4b`
  maps to `TT4B_TuneCP5_13p6TeV_madgraph-pythia8` (Summer24 NanoAODv15, 9.9M).
  A Sherpa tt+4b sample, if ever produced, is a generator-comparison sample, not
  a replacement.
- **D-R3-9 (2026-09-11, proposed — confirm) — ttH(bb) in Run 3 = the three
  top-decay-split samples.** `TTH-Hto2B-TTto4Q / -TTtoLNu2Q / -TTto2L2Nu_Par-M-125_TuneCP5_13p6TeV_powheg-pythia8`
  (Summer24 NanoAODv15, all VALID, 29.62M / 29.22M / 29.57M events, DAS
  2026-09-11) enter the registry as `ttHTobb_had / _semilep / _dilep`
  (workstream `had`, all three — SL/DL tops also pass a hadronic selection, as
  for ttbar). The top-decay-inclusive `TTH-Hto2B_Par-M-125` (2.44M) is demoted
  to `alt` and must never be added to the split set (double counting); its key
  `ttHTobb` is kept so the Run 2 ↔ Run 3 key map stays complete. Consequence:
  the xsec table needs σ(ttH)·BR(H→bb)·BR(tt→X) per key (D-R3-6), and no ttH(bb)
  request or question goes to the conveners.

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

## D-2026-07-10-background-hardprocess — MiniAOD-faithful background selection, synchronized

**Decision.** The background (`!isSignal`) selected-particle list is built, in
BOTH the NtupleForge module and the standalone (v1.8), as: every
`statusFlags.isHardProcess` particle, then every status-1/2 lepton
(11 ≤ |pdg| ≤ 16) whose **direct** mother is a top/Z/W/H — both scans in
ascending GenPart index. No recursion, no τ-rescue loop, no proton rows.

**Why.** MiniAOD §1.6 builds background `SelectedPar` = beam protons + ALL
status-21–23 particles + `FinalPar` entries with a direct boson mother.
`isHardProcess` is the copy-specific NanoAOD equivalent of "status 21–23" and is
hadronizer-independent (collapses the HERWIG branch, cf. §7 of the origin doc).
The previous heuristic (last-copy bosons + descendants + fromHardProcess-τ
rescue) provably diverged: τ counted twice when both copies survive pruning
(explicit-Z Z→ττ → −60 vs MiniAOD −30), and e/μ lost entirely in records with
no boson row (ME-level ℓℓ → 0 vs ±22/26). Protons are pruned from NanoAOD →
unrecoverable (documented in audit §8); no placeholder rows since the background
branch has no fixed layout to preserve.

**Alternatives rejected.** (a) Keep heuristic + document — rejected: the
divergence hits real DY/TTZ samples used in the analysis. (b) Placeholder
proton rows for count parity — rejected: fake rows are not MiniAOD's real
protons and buy nothing downstream. (c) Fix module only — rejected: module ≡
standalone identity is what `validate_topcpvcat.py` certifies; both moved
together (standalone v1.8).

**Evidence.** Synthetic-event regression in `script/test_reader_lifecycle.py`
(Python) and `TopCPVGenCategorizer/validation/crosscheck/` (C++, stub ROOT;
package renamed from `SSBGenCategorizer`, 2026-07-11):
identical values from both implementations on ttbar signal / explicit-Z Z→ττ /
boson-less μμ. Real-file check pending on lxplus (audit §2b Draw one-liners).

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

## D-2026-08-17-no-logs-in-git — verbose run logs never go in the repo; CRAB submit transcripts never, period
**DECIDED · 2026-08-17**

- **Decision.** Do not commit run logs. Two tiers:
  1. **Never, under any circumstance: CRAB submission/status transcripts.**
     `crab submit` echoes the **pre-signed S3 POST policy and signature** it uses
     to upload the task sandbox to `crabcache_prod`. Committing the transcript
     publishes a credential. This repo is public.
  2. **Not by default: any other bulk run log** (local `-N` test output, condor
     job logs, hadd transcripts). They are large, regenerable, and reviewing a
     diff against them is meaningless.
- **The one deliberate exception.** `script/das_ul18_scan_*.log` **is** tracked.
  It is not a run log but the *input* that `script/build_ul18_from_log.py`
  parses — the provenance for the generated UL18 configs — and it contains only
  `dasgoclient` query output, no credentials. `.gitignore` says so inline so
  nobody "cleans it up".
- **Context.** On 2026-07-27, commit `33e3030` ("log") added
  `submit_UL18_full_20260727_1120.log` — **1.52 MB, 16,715 lines** — plus
  `localcheck_UL18/`. It was removed from HEAD afterwards, but a public repo's
  history keeps it reachable by blob URL. The embedded policy carried
  `"expiration": "2026-07-27T10:23:37Z"` and had already expired when this was
  noticed, so **no rotation is required** and no CERN/CMS credential of the user
  is exposed by it. The lesson is the pattern, not this instance.
- **Remediation status.** `.gitignore` now blocks `submit_*.log`,
  `crab_status_*.log`, `localcheck_*/`, `local_test_*.log`, `preflight_*.log`.
  Purging the blob from history is **NOT done** — it needs
  `git filter-repo --path submit_UL18_full_20260727_1120.log --invert-paths`
  (or BFG) followed by a force-push, which rewrites every SHA after `33e3030`
  and breaks anyone who has cloned. Judged not worth it for an expired,
  self-scoped credential; revisit if the repo is ever forked or archived.
  See `05_troubleshooting.md` **A17** for the full recipe.
- **Alternatives considered.** (a) Keep transcripts under `docs/` for
  provenance — rejected, the useful part is a ~20-line summary that belongs in
  `02_CHANGELOG.md` (this is already what the UL18 entries do). (b) git-lfs —
  rejected, does not solve the secret-exposure half and adds a dependency.

---

## D-2026-08-17-validation-config-split — the 13-sample CPV validation subset gets its own file
**DECIDED · 2026-08-17 · corrects an undocumented 2026-07-26 in-place edit**

- **Decision.** `crabConfig/config_CPV2017UL_MC.yaml` stays the **full 73-dataset
  2017UL MC production config**. The 13-sample cross-validation subset lives in
  `crabConfig/config_CPV2017UL_MC_validation.yaml`. Neither file is derived from
  the other at runtime — they are both hand-maintained, and the validation file
  carries an explicit label contract in its header.
- **Context.** On 2026-07-26 the production config was **overwritten in place**
  (73 → 13 datasets, `jobID`/`output_base` → `CPV2017UL_MC_Validation`) with no
  CHANGELOG, DECISIONS or STATUS entry. The full list survived only as
  `config_CPV2017UL_MC.yaml.bk` — a filename no loader reads, in a class this
  repo had previously purged and ignored, and `*.bk*` had just been dropped from
  `.gitignore` in the same pass. Meanwhile the file's own header still said
  `FINAL : the datasets: entries …` and `01_STATUS.md` still said
  `Datasets + per-tier wiring final; jobID/output_base/splitting are
  placeholders` — the exact inverse of the state on disk.
- **Why the split, not a revert.** The 13-sample cut was *correct work*: its
  labels and DAS paths match `TopCPVGenCategorizer/condor/datasets.txt` 1:1
  (re-verified 2026-08-17, 13/13 labels and 13/13 paths, zero mismatches), which
  is exactly what `script/validate_topcpvcat.py` needs so filelists, condor
  output dirs and validation bookkeeping line up by name on both sides. It was
  applied to the wrong file. `01_STATUS.md` OPEN #0 had already named the
  intended target: `config_CPV2017UL_MC_validation.yaml`.
- **Label contract.** Renaming a key in either file without the other silently
  breaks the join. Both headers say so.
- **Follow-up.** `config_CPV2017UL_MC.yaml.bk` is now redundant (byte-identical
  to the restored config) and is ignored again by `*.bk*`, but it is still
  **tracked** — untrack it with
  `git rm --cached crabConfig/config_CPV2017UL_MC.yaml.bk`.

---

## D-2026-08-17-branch-policy — `devExtendedTtbarId` is the trunk; `main` is knowingly stale
**DECIDED · 2026-08-17**

- **Decision.** Keep developing on `devExtendedTtbarId`. Do **not** merge to
  `main` implicitly. Record the fact loudly instead — `01_STATUS.md` opens with
  it — so nobody clones the default branch and builds a 2026-07-05 tree.
- **Context.** `origin/main` is at `c76d014` (2026-07-05), 13 commits behind, and
  does not contain the 2026-07-15 TopCPV v8.1 state, let alone the UL18 work.
  `git merge-base --is-ancestor origin/main HEAD` succeeds, so a **fast-forward
  merge is available at any time** — 0 conflicts, nothing to reconcile.
- **Why not just merge now.** The 2018UL full campaign (85 tasks / 7,466 jobs)
  was still in flight and its `--report` bookkeeping references this branch;
  moving the default branch mid-campaign buys nothing. Revisit once the campaign
  is declared done (`01_STATUS.md` watch items).
- **Alternative.** Rename `devExtendedTtbarId` → `main` outright. Rejected for
  now: the branch name is also referenced from `TTHHGenCategoryTools` notes.

---

## D-2026-07-27-crab-job-limit — `units_per_job` must keep every task under 10,000 jobs
**DECIDED · 2026-07-27**

- **Decision.** With `splitting: FileBased`, treat **10,000 jobs per task** as a
  hard wall: `njobs = ceil(nfiles / units_per_job)`. **Never lower
  `units_per_job` without first checking the resulting per-task job count.**
  Raising it is always safe for this limit.
- **Why this is a decision and not a footnote.** CRAB does not reject an
  oversized task at submit time. The client returns success, the submitter logs
  `Submitting...`, and the **server** then parks the task at `SUBMITREFUSED`
  with `The splitting on your task generated N jobs. The maximum number of jobs
  in each task is 10000`. Because `jobsPerStatus` stays empty, `--report` shows
  a row of all zeros — indistinguishable from "not started yet" — and
  `--resubmit` cannot help (it only requeues *failed* jobs of a task that
  reached the scheduler). Net result: **one dataset silently produces nothing,
  possibly for days.** Observed 2026-07-27 in the sibling repo
  `TTHHGenCategoryTools` (2018 `TTbar_SemiLep`, 10,010 MiniAOD files at
  `units_per_job: 1`).
- **Current NtupleForge exposure: none, by luck of input tier.** These configs
  read **NanoAOD**, ~20x fewer files than the MiniAOD parents. The largest 2018UL
  dataset **by file count** is `WJetsToLNu_HT200To400_ext1` at **780 files → 780
  jobs**; next are `WJetsToLNu_HT70To100_ext1` (669) and `HT100To200_ext1` (523).
  Note `TTbar_SemiLep` is the largest by **events** (476 M) but only 4th by files
  (391) — **the job count is set by files, not events**, so rank by `nfiles`.
  The 7,466-job 2018UL campaign is spread over **85 tasks**, and the limit is
  **per task**. Do not read the campaign total as if it were near the limit.
- **When it bites here.** Pointing a config at MiniAOD, or adding a NanoAOD
  dataset with >10,000 files, while `units_per_job: 1`.
- **Enforcement (what was actually done).** Warning blocks at the code site and
  in the ttHH configs: `crab/submit_crab.py` at the `conf.Data.unitsPerJob`
  assignment (this is the one every submission passes through),
  `crabConfig/config_ttHH2017UL.yaml`, and `script/build_ul18_from_log.py` —
  the last one stamps the warning into **both** generated 2018 configs, so it
  survives regeneration.
  **Not yet annotated (known, deliberate scope):** the 8 `config_CPV*_{Data,MC}.yaml`
  files and `config_crabTest.yaml`, which also carry `splitting: FileBased` +
  `units_per_job: 1`. They are covered by the submitter-side warning above (every
  submission reads it) and their datasets are NanoAOD with at most a few hundred
  files each, but they do not carry the note locally. Add it if CPV ever moves to
  MiniAOD.
- **Known gap (OPEN).** `--preflight --check-das` here does **not** compute
  per-task job counts. The extend submitter in `TTHHGenCategoryTools` does
  (reads DAS `nfiles`, FAILs above the limit, WARNs above 90%, and prints the
  `units_per_job` needed). Porting that check is the obvious follow-up; until
  then the guard is documentation plus a manual
  `dasgoclient -query "summary dataset=<DS>" -json` check.
- **Alternative considered.** `splitting: "Automatic"` removes the limit problem
  (CRAB sizes jobs by runtime), but it obscures the job↔file mapping, which this
  pipeline relies on for partial-failure tracking and completeness checks against
  DAS `nevents`. Kept FileBased; Automatic remains PROPOSED.
- **Cross-repo canonical rule.** `TTHHGenCategoryTools/docs/04_decisions.md`
  **D15** (rule + 3-layer enforcement) and that repo's
  `docs/08_troubleshooting.md` **T-19** (incident). Local preventive entry:
  [`05_troubleshooting.md`](05_troubleshooting.md) **A16**.

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
