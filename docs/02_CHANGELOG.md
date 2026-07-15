# Changelog

All notable changes to NtupleForge. Reconstructed from git history
(`dev260412_TTbarCategory` branch) and curated into logical milestones rather
than raw commits. Dates are approximate (derived from commit/backup
timestamps; `26MMDD` suffixes seen in the repo decode as `20YY-MM-DD`).

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased] — 2026-07-15: A14 — beam-parallel energy overflow (background CRAB crash)

### Fixed
- **`_energy()` OverflowError on status-21 incoming partons** (first CRAB
  production attempt of the §2b background rebuild; QCD_HT 2017UL): beam-
  parallel legs carry pt≈0 and NanoAOD eta ~ O(1e4) → `math.cosh` overflow.
  Now returns the −999 sentinel for |eta| > 50 (+ defensive OverflowError
  catch). Standalone v1.9.1 applies the identical `SafeEnergy()` at all four
  energy sites — the C++ would have silently written `inf` instead of
  crashing, which the validator would have flagged as module/standalone
  mismatches. Both test harnesses gained the regression (E3 incoming legs at
  eta ±23000). See troubleshooting A14; MiniAOD comparison note added to the
  audit §8 (MiniAOD stored real `genPar->energy()` for these rows —
  unrecoverable from NanoAOD).

---

## [Unreleased] — 2026-07-11: standalone package renamed → TopCPVGenCategorizer

- The standalone reference implementation `SSBGenCategorizer` is renamed
  **`TopCPVGenCategorizer` (v1.9)**: class, files, directory, include guards,
  `TopCPVGenStatusBit` namespace, condor scripts, and all package docs.
  External MiniAOD names quoted as reference (`SSBAnalyzer`, `SSBTree`,
  `SSBCorrections`, `SSBCPVCalc`) are real upstream identifiers and stay
  verbatim (D-2026-07-01-rename-topcpv scope). Output format unchanged
  (`GenCatTree`, branch names, event-id keys) → `validate_topcpvcat.py` and
  existing GenCatTree outputs remain compatible. Living NtupleForge doc
  references updated; historical CHANGELOG entries left as written.

---

## [Unreleased] — 2026-07-10: background selection = MiniAOD §1.6; standalone v1.8 sync

### Changed (audit §2b resolution — module `topCPVCategorizer.py`)
- **`FillBackgroundSelection` rebuilt MiniAOD-faithful**: picked = every
  `statusFlags.isHardProcess` particle (the NanoAOD equivalent of MiniAOD's
  status-21–23 `TreePar`; hadronizer-independent, so the HERWIG branch collapses
  too) **+** status-1/2 leptons (|pdg| 11–16) whose **direct** mother is a
  top/Z/W/H — both scanned in ascending index, matching MiniAOD's ordering.
  Removed: the last-copy-boson base set, the recursive off-flavour descent, and
  the hard-process-τ rescue loop. Fixes both §2b risks: explicit-Z Z→ττ now
  −30 (was −60, τ double count) and boson-less ME ℓℓ now ±22/26 (was 0).
  `_FROM_HARD_PROCESS` constant removed (no longer used); `_IS_HARD_PROCESS`
  (bit 7) added.

### Standalone `SSBGenCategorizer` updated to v1.8 (synchronized)
- v1.7 (pre-2026-06-28-restoration) was uploaded and three-way compared
  (standalone ↔ module ↔ MiniAOD origin). Divergences found & fixed in the
  standalone, adopting the module's MiniAOD-faithful behaviour: ① direct
  channel over the **full** selected list (was: slots 8–11 only + background
  forced to 0); ② `Channel_Idx_Final` via the GenPart daughter-map walk with
  GenPar append and <14/>14 sign rules (was: `GenDressedLepton` count —
  branches no longer read); ③ background selection rebuilt as above (was:
  one-level boson daughters + τ rescue); ④ `Channel_Idx_Expanded` (+ Loop
  summary counter) added.

### Added (cross-validation without ROOT)
- `script/test_reader_lifecycle.py` extended to 4 synthetic events (2× ttbar
  signal incl. `Channel_Jets` 2112/1212 asserts, explicit-Z Z→ττ, boson-less
  ME μμ). The standalone ships `validation/crosscheck/` (stub-ROOT headers +
  harness): both implementations produce **identical** derived values on the
  same events (compiled with g++ 13, `-Wall -Wextra` clean, all asserts pass).

### Pending on lxplus
- Rebuild the standalone v1.8 with real ROOT; rerun `validate_topcpvcat.py`
  (event-matched, both codebases now MiniAOD-faithful **and** mutually
  identical); one-time `TTree::Draw` sanity on the DY production (§2b).

---

## [Unreleased] — 2026-07-02 (3): re-audit vs MiniAOD + validator hardening

### Fixed
- **`script/validate_topcpvcat.py` latent crash + dead comparisons** (found in
  the 2026-07-02 re-audit, before first lxplus use): the branch-presence guard
  used `GetBranch(x) is None`, but PyROOT returns a **null TBranch object,
  never Python `None`**, so the guard could not fire and the first missing
  passthrough name would have crashed `getattr`; several passthrough names did
  not exist on the NanoAOD side at all (`GenJet_energy`,
  `GenJet_{Parton,Hadron}Flavour` capitalization, `PSWeight_n`), making those
  comparisons silent no-ops. Now: passthrough is a `(GenCatTree name, Events
  name)` pair list with real NanoAOD names, presence is checked on **both**
  trees with truthiness and a one-time WARNING per skipped pair, `UChar_t`
  elements are coerced (`bytes/str → int`) before comparison, and unmatched
  event counts are reported in both directions.

### Documented (audit addendum, `TopCPV/02_faithfulness_vs_miniaod.md`)
- **§2b (new): background selection construction diverges from MiniAOD** —
  module/standalone pick last-copy bosons + recursive descendants + a τ-only
  rescue, vs MiniAOD's whole-hard-process base set; two concrete risks
  (explicit-Z→ττ double count → −60 vs −30; boson-less ME ℓℓ → 0 instead of
  ±22/26) with `TTree::Draw` discriminators to run on the fresh DY output.
  Module ≡ standalone, so the validator cannot see this — it is vs MiniAOD only.
- **§8 amended:** slots 0/1 and t/t̄ mother fields necessarily differ (NanoAOD
  prunes beam protons; −1/placeholder vs MiniAOD's real proton rows and
  `Mom=(0,1), nMo=2`). Channel-neutral, unrecoverable.
- **§5 strengthened:** τ→ℓ walk verified statement-by-statement against origin
  §2.2 (map order, descendant order, push-before-check, ν-triggered removal,
  sign rules) — order-exact.
- **§3 note:** background `GenTop` = −999 scalars vs MiniAOD's empty vectors
  (cosmetic).

---

## [Unreleased] — 2026-07-02 (2): fix A13 — pre-register branch readers (2nd CRAB crash)

### Fixed
- **Second MC CRAB production crash** (`config_CPV2017UL_MC`, 2026-07-02): every
  MC job died on the first event with `ReferenceError: attempt to access a
  null-pointer` on an in-bounds `mom[i]` (DYJets) or a segfault in
  `TObjectArrayReader::At` (QCD). Root cause proved from
  `treeReaderArrayTools.py` @ CMSSW_14_2_X: lazily creating a reader mid-loop
  triggers `_remakeAllReaders` (new TTreeReader, all readers recreated),
  silently invalidating every reader object bound earlier — our back-to-back
  local binds in `analyze()` produced 7 remakes before the first element read.
  **Fix:** `beginFile` now pre-registers every reader
  (`GEN_ARRAY_BRANCHES`/`GEN_COUNTER_BRANCHES` via
  `inputTree.arrayReader/valueReader`) while the TTreeReader is clean → the
  loop is remake-free and bound locals stay valid; plus fail-fast on partial
  gen inputs and a self-healing `_read_arrays` batch binder (re-binds once +
  warns if a future unregistered read sneaks in). Incident:
  `05_troubleshooting.md` **A13**; rule: `06_nanoaod_branch_access.md`
  Pitfall 4; decision: D-2026-07-02-prewarm-readers.
- **Validation:** reproduced and fixed against the *actual* CMSSW_14_2_X
  framework sources (`treeReaderArrayTools`/`datamodel`/`eventloop`) over a
  cppyy-lifetime mock ROOT in the dev container: old pattern reproduces the
  exact CRAB error; fixed module runs the real `eventLoop` with zero reader
  rebuilds (46 branches, correct signal quantities; data no-op intact).
  **Still unverified against real ROOT — lxplus `-N 10` + `validate_topcpvcat.py`
  before resubmission.**

---

## [Unreleased] — 2026-07-02: CPV configs split per tier (_Data / _MC)

### Changed
- **`crabConfig/config_CPV<era>UL.yaml` (combined) → `config_CPV<era>_Data.yaml`
  + `config_CPV<era>_MC.yaml`** for all four eras; combined files removed.
  Data configs: `modules/noop.py` + `branches/branch_CPV_Run2_Data.txt`;
  MC configs: `modules/topCPVCategorizer.py` + `branches/branch_CPV_Run2_MC.txt`.
  Split by DAS tier suffix; dataset counts preserved (30+73 / 15+75 / 29+73 /
  12+74). Closes the per-tier OPEN item and the config half of incident A11
  (`03_DECISIONS.md` → D-2026-07-02-per-tier-configs). YAML-parse verified
  in-container; **unverified on CRAB** — submit one small data task first.

---

## [Unreleased] — 2026-07-01: TopCPV rename, CRAB crash fixes, docs restructure

### Changed (rename — no logic change by itself)
- **Module renamed** `modules/ssbGenCategorizer.py` → **`modules/topCPVCategorizer.py`**;
  class `SSBGenCategorizer` → **`TopCPVCategorizer`**; **branch prefix**
  `SSBGenCat_` → **`TopCPVCat_`**; debug env `SSBGENCAT_DEBUG` → **`TOPCPVCAT_DEBUG`**;
  validator `script/validate_ssbgencat.py` → **`script/validate_topcpvcat.py`**;
  the standalone C++ shorthand "SSBGen" → "TopCPV" in prose. The **external
  MiniAOD class name `SSBAnalyzer` is intentionally preserved** everywhere (it
  is the reference of truth, not our code). `config_CPV*` `analysis_module`
  entries updated. Rename safety per `00_PROMPT.md` §7: `crab/submit_crab.py`
  ships every sibling `.py` name-agnostically and derives `-I` from the config
  basename, and a repo-wide grep confirms zero stale `SSBGen*`/`ssb_gencat`
  tokens — **a real CRAB job must still confirm** (no CRAB in the dev container).
  See `03_DECISIONS.md` → D-2026-07-01-rename-topcpv.
  ⚠️ **Old and new ntuples differ in branch names** (`SSBGenCat_*` vs
  `TopCPVCat_*`) — downstream readers must switch prefixes.
- **Docs restructured into per-workstream subdirectories**: `docs/ssb_gencat/` →
  **`docs/TopCPV/`**; `02_physics.md` → **`ttHH/01_physics.md`**;
  `09_legacy_ttbar_pipeline.md` → **`ttHH/02_legacy_ttbar_pipeline.md`**;
  `docs/legacy/` → **`docs/ttHH/legacy/`**; new local index `ttHH/README.md`.
  Root docs renumbered contiguously (§3.1): `03_CHANGELOG`→`02_CHANGELOG`,
  `04_DECISIONS`→`03_DECISIONS`, `05_architecture`→`04_architecture`,
  `06_troubleshooting`→`05_troubleshooting`,
  `07_nanoaod_branch_access`→`06_nanoaod_branch_access`,
  `08_DeveloperGuideline`→`07_DeveloperGuideline`. All cross-links rewritten;
  link check passed. `00_PROMPT.md` stays the **single** prompt doc covering
  both workstreams. Top-level `README.md` and `docs/README.md` rewritten in
  Korean. See D-2026-07-01-docs-topcpv-tthh-split.

### Fixed (first CPV CRAB production crashes, 2026-07-01)
- **MC segfault** (`TTZToQQ`, every job): `safe_len`'s out-of-bounds indexing
  probe on a raw `TTreeReaderArray` (`GenPart_pdgId`) hit ROOT undefined
  behaviour (`TObjectArrayReader::At` → `TBranchProxy::Setup` → SIGSEGV).
  **Lengths now come from the count branch** via new helpers
  `count(event, "X")` / `opt_count(event, "X")` in
  `modules/nanoaod_branch_access.py`; `safe_len` was de-fanged (no probe;
  fails fast) and deprecated for collections. The old "nGenPart is unreliable"
  doctrine was a mis-attribution of the A4 zombie-branch bug and is corrected
  in `06_nanoaod_branch_access.md`. Incident: `05_troubleshooting.md` **A12**;
  decision: D-2026-07-01-count-branch-length.
- **Data crash** (`SingleElectron_Run2017B`, every job): the MC-only guard
  `inputTree.GetBranch("GenPart_pt") is None` did not fire through the
  nanoAOD-tools wrapper, so data reached `analyze` and died on
  `Unknown branch GenPart_pdgId`. `beginFile` now detects presence via
  `GetListOfBranches()` (the A5 pattern) and a GenPart-less file makes the
  module a logged **no-op** instead of crashing. Data/MC config split remains
  OPEN (`01_STATUS.md`). Incident: `05_troubleshooting.md` **A11**.
- Both fixes are **logic-tested in-container only** (stub harness: data no-op;
  synthetic ttbar event writes 46 branches, `GenPar_Count=12`,
  `GenBJet_Count=1`). **Unverified on real NanoAOD** — validate on lxplus
  (`-N 10` local run, then `validate_topcpvcat.py`) before resubmitting.

### Added
- `count()` / `opt_count()` in `modules/nanoaod_branch_access.py` (count-branch
  collection lengths); Pitfall 3 (branch-presence detection) documented in
  `06_nanoaod_branch_access.md`.
- `docs/ttHH/README.md` — local index for the ttHH workstream docs.

---

## [Unreleased] — CPV gen-level categorizer (MiniAOD-faithful)

Added the NanoAOD module + CRAB configs to produce the top-CP-violation (CPV)
gen-categorization ntuples. **Reference of truth = the MiniAOD `SSBAnalyzer`**
(not the intermediate standalone TopCPV); the audit's restorations are applied to
**both** the module and the standalone TopCPV C++ (see `03_DECISIONS.md` →
D-2026-06-28-miniaod-reference).

### Added
- **`modules/topCPVCategorizer.py`** — reproduces the MiniAOD `SSBAnalyzer`
  gen-level categorization from the NanoAOD `GenPart` collection. Emits **derived
  branches only**, prefix `TopCPVCat_` (12-slot family tree, `Channel_*` codes,
  top/antitop kinematics, ghost-B GenBJet/GenBHad); raw gen collections come from
  the full-NanoAOD passthrough. **MiniAOD-faithful channel:** `Channel_Idx` summed
  over the full selected list (§2.1, recovers background channels); `Channel_Idx_Final`
  resolves τ→ℓ by walking the GenPart daughter map (§2.2) and **appends the τ
  daughter to GenPar** (so `GenPar_Count` grows for leptonic-τ events). Additive
  `Channel_Idx_Expanded` diagnostic + end-of-job unclassifiable counter. NanoAOD
  bonuses kept (`Channel_Visible_Tau`, `Channel_Tau_Lepton`); last-copy top, explicit
  W⁻ daughters, `GenBJet` via `GenJet_hadronFlavour` kept (audit §3/§4/§6). MC only.
  Uses `to_int`/`safe_len` from the re-instated `modules/nanoaod_branch_access.py`
  (mandatory; see `06_nanoaod_branch_access.md`). Logic-tested in-container (all-hadronic /
  semileptonic-τ / background); byte-identity vs. TopCPV to confirm on lxplus.
- **`crabConfig/config_CPV{2016preVFPUL,2016postVFPUL,2017UL,2018UL}.yaml`** —
  per-era CRAB configs (named to stay distinct from the ttHH `config_ttHH*`
  lists), datasets transcribed from the user-provided UL lists (NanoAODv9:
  103/90/102/86 datasets). **Only `datasets:` is final; all `common:` fields are
  placeholders.** The loader normalized/flagged several transcription artifacts
  (2 missing leading `/`, a `104X` campaign typo, two `QCD_Pt_3200toInf` pilot
  duplicates emitted as commented `# [DUP]` lines, one extra-field/`/`-missing DY
  line) — all to verify on DAS (`01_STATUS.md`).
- **`branches/branch_CPV_Run2_{Data,MC}.txt`** — the CPV output branch lists
  (drop IsoTrack/LowPtElectron/SoftActivityJet/SubJet/Tau/boostedTau/HLT then
  re-keep specific HLT; MC also drops GenIsolatedPhoton/GenVisTau/HTXS/
  SubGenJetAK8). Note: the MC list drops `GenVisTau*` from the *output*, which the
  module reads from the *input* — keep `branch_file` as an output selection.
- **`script/validate_topcpvcat.py`** — lxplus equivalence checker (matches events
  by run/lumi/event; ints exact, floats within `--ftol`).
- **`docs/03_DECISIONS.md`** (decision log) and **`docs/01_STATUS.md`** (status) — both
  were missing vs. the documentation guideline; created here. **`docs/TopCPV/`**
  gained a `README.md` index and a `01_module.md` module reference.
- **`docs/00_PROMPT.md`** — AI/contributor working agreement (instance of the
  documentation contract §8): persona, reference of truth (MiniAOD), environment
  limits (no ROOT/compile here), and the validation + change-notification duties.

### Changed (documentation guideline v2 adoption)
- **Docs numbered in reading order** (`NN_name.md`), per the contract §3.1:
  `01_STATUS` → `ttHH/01_physics` → `02_CHANGELOG` → `03_DECISIONS` → `04_architecture`
  → `05_troubleshooting` → `06_nanoaod_branch_access` → `07_DeveloperGuideline` →
  `ttHH/02_legacy_ttbar_pipeline`; `TopCPV/` given local numbering
  (`01_module` / `02_faithfulness_vs_miniaod` / `03_miniaod_origin`). `README.md`
  stays unnumbered and lists the order. All cross-links rewritten.
- **Branch lists renamed** `branchlist_Run2_{Data,MC}.txt` →
  **`branch_CPV_Run2_{Data,MC}.txt`** (CPV-scoped names); `config_CPV*` `branch_file`
  references updated.
- **PyROOT helper renamed** `modules/_nanoaod_compat.py` →
  **`modules/nanoaod_branch_access.py`** (clearer role); the `topCPVCategorizer`
  import and the doc (now `06_nanoaod_branch_access.md`) updated. The archived copy
  under `docs/ttHH/legacy/code/` keeps its original name for historical accuracy.
- **`topCPVCategorizer` guarded validation logging**: env `TOPCPVCAT_DEBUG=N` prints
  per-event derived quantities for the first N events, then stays silent (never logs
  unboundedly in the event loop). Off by default.

### Fixed
- **CRAB import failure of the renamed helper** (first `config_CPV2017UL` submission
  failed fast with *"attempted relative import with no known parent package"*). Two
  coupled causes: (1) `crab/submit_crab.py` auto-included helpers only via
  `glob("modules/_*.py")`, so dropping the leading underscore in the rename removed
  `nanoaod_branch_access.py` from the sandbox; (2) the module's relative-import
  fallback cannot work in CRAB's flat (top-level) import context. Fix: `submit_crab.py`
  now ships **every** sibling `.py` (except the analysis module and dunders), and
  `topCPVCategorizer.py` puts its own dir on `sys.path` via `__file__` before importing.
  See `05_troubleshooting.md` A0. Follow-up: generalized this class of bug into
  **Rule 7 (rename/move safety)** in `07_DeveloperGuideline.md`, `00_PROMPT.md` §7, and
  the documentation contract §8.3 (flag hidden glob/hardcoded-path file couplings).

---

## [Unreleased] — Full-NanoAOD passthrough + docs restructure

The active direction changed: **NtupleForge no longer produces `ttCat_*`
branches.** tt+jets categorization moves to the main analyzer, and the
post-processor now ships full NanoAOD unchanged. The repository was
reorganized so the live tree is the minimal working pipeline and all
knowledge lives in `docs/`.

### Changed
- **Default pipeline is now full passthrough.** New
  `branches/branch_keep_all.txt` (`keep *`); live
  `crabConfig/config_ttHH2017UL.yaml` switched to `modules/noop.py` +
  `branch_keep_all.txt` (dataset list preserved, campaign id → `fullNano_v19`).
- **`crabConfig/config_ttHH2017UL.yaml` dataset list extended** (2026-06-22)
  to cover ttH-style and ttHH SL/DL (leptonic) selections, not just ttHH→4b
  fully-hadronic. Added (UL17 NanoAODv9, names resolved via dasgoclient):
  tH signals `tHq`/`tHW` and `ttHToNonbb` (AN-19-094 Tab.7-8); `ttZH`/`ttZZ`
  ext1 productions (combine with base for stats); leptonic ttV
  `TTWJetsToLNu`/`TTZToLLNuNu` (nominal
  TuneCP5 only); full leptonic `WJetsToLNu` HT-binned set (base+ext, 21 tasks)
  and `DYJetsToLL_M-50` HT-binned set (8 tasks). Single top was already
  complete (6 channels); inclusive `ttHTobb` already covers all tt decays, so
  no tt-decay-split ttH samples were added (those are SL/DL DNN-training-only,
  AN-19-094 Tab.7, and would double-count against the inclusive in baseline).
  **Open items:** low-mass `DYJetsToLL_M-10to50` and leptonic data
  (SingleElectron/DoubleMuon/DoubleEG/MuonEG) not yet added.
- **`scripts/` renamed to `script/`**, containing the essential driver
  `run_postproc.py` and the CRAB status summarizer `parse_crab_status.py`
  (moved in from the top level). Path updated in `crab/submit_crab.py`,
  `crab/crab_script.py`, and `script/run_postproc.py`.
- **`parse_crab_status.py` enriched**: a `--show-lines` flag now prints the
  raw status lines (running / transferring / failed / finished), absorbing
  the old `checkCrabstatusCommand.txt` grep recipes; `checkCrabstatusCommand.txt`
  was deleted.
- **README slimmed** (837 → ~120 lines) to setup + run commands + a pointer to
  the developer guide. All deep material moved into `docs/`.

### Added
- **`crab/submit_crab.py` gained `--report` and `--resubmit`** (2026-06-22).
  `--report` queries CRAB and prints a compact per-sample job-state table
  (done/run/idle/transf/fail/other + totals) — easier to read than full
  `crab status`; unrecognised CRAB states fall into `other` and raise a warning
  naming them (extend `REPORT_COLUMNS`/`KNOWN_OTHER_STATES`). `--resubmit`
  explicitly resubmits failed jobs in existing tasks (the default submit path
  still auto-resubmits existing tasks). Every submit/resubmit run now prints a
  reminder that memory/walltime failures need a manual
  `crab resubmit --maxmemory/--maxjobruntime` (see troubleshooting A10).
- `docs/` reorganized into the documentation categories:
  - `07_DeveloperGuideline.md` — contributor rules (read all docs first; log every change
    and every problem; which doc each record goes in).
  - `04_architecture.md` — framework internals **plus a copy-followable how-to
    for writing a module that adds branches / applies cuts** (§6).
  - `ttHH/01_physics.md` — physics basis (analysis target, stitching, five categories,
    `genTtbarId` encoding, why five not seven), split out of the legacy doc.
  - `05_troubleshooting.md` — consolidated incident log (every bug: symptom,
    error signature, root cause, fix, validation) + how validation works.
  - `ttHH/02_legacy_ttbar_pipeline.md` — implementation record of the retired
    categorizer (physics delegated to `ttHH/01_physics.md`).
  - `06_nanoaod_branch_access.md` — why the PyROOT compat shim existed.
  - `02_CHANGELOG.md` — this file.
- `docs/ttHH/legacy/code/` — verbatim archive of the categorization pipeline
  (categorizer module, compat shim, slimming branch list, branch inventories,
  original CRAB config).

### Removed (from the live tree)
- `modules/ttbarCategorizer.py` (the module that used to write the twelve
  `ttCat_*` / `ttCatXval_*` categorization branches) and its
  `modules/_nanoaod_compat.py` helper → moved to `docs/ttHH/legacy/code/`. The
  categorization itself now happens in the main analyzer; the full
  implementation record is kept in `ttHH/02_legacy_ttbar_pipeline.md`.
- `branches/branch_ttHHto4b_hadronic_2017UL.txt`, `branches/branch_2017UL/`
  → archived under `docs/ttHH/legacy/code/`.
- `scripts/inspect_weights.py`, `scripts/compare_branches.py`,
  `scripts/dump_branches.py`, `scripts/test_ttbar_categorizer.py` (stale,
  8-category) → **deleted**.
- `scripts/validate_events.py` → archived to `docs/ttHH/legacy/code/tools/`
  (skim-efficiency QA; the current passthrough has no skim to measure). Its
  documentation moved to `ttHH/02_legacy_ttbar_pipeline.md` §8.
- `checkCrabstatusCommand.txt` → deleted (functionality absorbed into
  `script/parse_crab_status.py --show-lines`).
- All stale `*.bk*` editor backups deleted; `.gitignore` updated to ignore
  `*.bk*`.

## tt+jets categorization — final 5-category design (~2026-04)

The major redesign of the categorizer into its final, shipped form.

### Changed
- **Primary path switched from GenPart-based to direct `genTtbarId`
  decoding.** After confirming via `GenTtbarCategorizer.cc` that the AN-cited
  tool does not store a bbb-vs-4b distinction, `genTtbarId % 100` became the
  primary source of truth (`f701f5a` reversed once more into final form).
- **Class renamed** `TTbarJetCategorizer` → `TtbarCategorizer`; categories
  collapsed from 8 (`ttCat_LF/cc/b/2b/bb/bbb/4b/noTTJets`) to 5
  (`ttCat_LightFlavour/AddCjet/Add1Bjet_1Had/Add1Bjet_2Had/Add2Bjet`) with
  explicit jet/hadron suffixes.
- **Dropped** the `nAdditional{B,C}Jets` / `nAdditionalBHadrons` /
  `nMatchedBHadrons` count branches.

### Added
- **Dual parallel branch sets.** The GenPart algorithm was demoted to a
  cross-check, written unconditionally to `ttCatXval_*` alongside the primary
  `ttCat_*`, so the analyzer can compare both per event without re-running
  (`619b5eb`).
- **endJob report** with source distribution, per-category counts, and a 5×5
  primary-vs-xval confusion matrix.
- **Optional per-event debug CSV** (`--ttcat-debug-csv`), off by default and
  never staged out by CRAB (`a9449a4`).
- **CLI flags via env-var + factory** (`--ttcat-debug-csv[-path]`,
  `--ttcat-quiet`) decoupled from the module class.

### Fixed
- **`tt+2b` (code 52) classification bug** (`619b5eb`).
- **Broken scalar counters.** Loops were switched from `range(nGenPart)` /
  `range(nGenJet)` (which returned `range(0)` under the raw-proxy access
  mode, classifying everything as `tt+LF`) to true array lengths via
  `safe_len()` (`1fb657b`).
- **Silent UChar_t comparison failure.** `GenJet_hadronFlavour == 5` always
  returned `False` (`b'\x05' == 5`), putting 1000/1000 signal events into
  `tt+LF`; fixed with `to_int()`. Captured in the new `_nanoaod_compat.py`.
- **Input-branch zombie state.** The driver stopped applying the keep/drop
  file to the input tree (`branchsel=None`); applying it had left
  `genTtbarId`/`GenPart_*` in a `hasattr=True / len()=0` state, sending every
  event to `NO_GENTTBARID`.
- **`hasattr` crash on data NanoAOD.** Branch-presence detection moved from
  `hasattr(event, name)` (the wrapper raises `RuntimeError`, which `hasattr`
  does not catch) to reading `inputTree.GetListOfBranches()` directly.

---

## tt+jets categorization — initial introduction (~2026-03–04)

### Added
- First ttbar categorization module (`TTbarJetCategorizer`) and the
  `GenJet_hadronFlavour` branch needed to feed it (`9be688f`).
- Enabled the categorizer in the CRAB pipeline and kept its output branches
  (`dab7120`).

### Fixed
- Aligned `_is_b_hadron` and the ΔR-matching algorithm with the C++ analyzer
  (`3bf1cdc`).

---

## Core framework and CRAB submission (earlier)

### Added
- `scripts/run_postproc.py` — driver wrapping the NanoAODTools
  `PostProcessor` (split/merge modes, dynamic `module:LIST` loading).
- `crab/{submit_crab.py,crab_script.py,PSet.py}` — YAML-driven CRAB3
  submission manager (submit / status / resubmit / kill), worker wrapper that
  reconstructs the command from `PSet.py` + `crab_args.txt`.
- `modules/{noop.py,jetsMETcut.py}` — empty passthrough module and a
  gatekeeper skim-cut example.
- Temporary CRAB status checkers (`parse_crab_status.py`, the
  `checkCrabstatusCommand.txt` grep cheatsheet) (`11251c8`, `e8a63c7`).

### Fixed / Changed
- Output-filename handling in CRAB (`9d806c0`, `edca229`) — the recurring
  PSet-vs-YAML stageout mismatch (see Known Issues below). Currently both
  sides use `slimmedNtuple.root`, but the value is still hardcoded in two
  places (`crab/PSet.py` and `crab/submit_crab.py`); a submit-time
  auto-sync remains a TODO.

---

## Known issues carried forward

- **Output filename hardcoded in two places.** `crab/PSet.py`
  (`PoolOutputModule` fileName) and `crab/submit_crab.py` (`out_name`) must
  agree or CRAB stageout fails with exit 60302. They currently agree
  (`slimmedNtuple.root`); auto-synchronizing them at submit time is the
  permanent fix.
- **`jetsMETcut.py` doc/default mismatch.** Docstring and `__init__` defaults
  say `njet≥4, MET>150`, but the shipped `MODULES` uses `njet_thr=6,
  met_thr=300`. Harmless, but confusing.
- **CRAB provenance staging disabled.** `crab_args.txt` and the YAML config
  are commented out of `submit_crab.py`'s `outputFiles`; only the main output
  is staged back.
