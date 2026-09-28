# script/ -- tools, registries, and the records they produce

Layout since 2026-09-22 (before that every file sat flat in this directory).

| Where | What | Committed? |
|---|---|---|
| `script/*.sh`, `script/*.py` | the tools (DAS scan / inventory / status, branch inventories and checks, config builder, run logging, local checks, v9-v15 validation, output-volume projection `size_options.py`, slim-draft generator `make_slim_branchlists.py`) and offline tests (`test_*.py`; `test_submit_crab_mock.py` checks `crab/submit_crab.py` without CRAB, `test_size_options_mock.py` checks `size_options.py` without ROOT or DAS) | yes |
| `script/condor/` | `submit_size_options.sh` (fresh VOMS proxy, then `condor_submit`) + `size_options.sub` + `size_options_job.sh`: the output-volume measurement as one HTCondor job on CERN batch (2026-09-28; the interactive run died with the ssh connection) | yes |
| `script/samples_registry.txt`, `script/samples_registry_run3.txt` | the sample registries (Run 2 / Run 3), the single source for `das_scan.sh` and `build_from_scan_log.py` | yes |
| `script/inventory_manifest_*.txt` | rows for `sweep_inventories.sh` (which datasets to dump one file of) | yes |
| `script/validate_v9.json` | settings for `validate_topcpvcat.py` (v9 test) | yes |
| `script/das/` | DAS scan logs (`das_ttHH_<era>_<ver>_<stamp>.log`, the INPUT of the builder), Run 3 probe / discover logs, the 2026-07-26 UL18 scan, the v9-vs-v15 compare table, `missing_in_v15_2017UL.tex` | yes |
| `script/das/inventory_dumps/` | full-campaign DAS dumps of `das_inventory.sh` (`.tsv` + `.match.txt` + `.names.txt`, 5-9 MB each): the evidence behind the cross-campaign audits in `docs/10_validation_ledger.md` | yes |
| `script/das/sherpa/` | DAS listings of Sherpa tt+jets samples (Run 2, Run 3, status) gathered for the MC request discussion | yes |
| `script/drafts/` | `build_from_scan_log.py` output: `review_das_*.{md,tsv}` and `config_das_*.yaml.draft`; `make_slim_branchlists.py` output: `branch_hadronic_*_slim{A,B,C}.txt`; a draft becomes real only when copied to `crabConfig/` or `branches/` by hand (2026-09-28: slimB copied into the four v15 hadronic lists under an `ADOPTED` block header; the drafts are still made from the part above that block, and `make_slim_branchlists.py --check` checks the block) | yes |
| `script/inventory/` | one-file branch inventories (`inv_*.tsv`) and v9-v15 diffs (`diff_*.txt`) from `dump_branch_inventory.py` / `sweep_inventories.sh` | yes |
| `script/runlogs/` | `runlog.sh` records of every lxplus step (`run_<step>_<stamp>.log`) + `LEDGER.tsv` + `size_options_meas.tsv` (one row per sample measured by `size_options.py`) + `size_options_branches.tsv` (its per-branch compressed sizes; since 2026-09-28 every row comes from one child process per sample with no ROOT error line, and rows of the earlier version have another signature and are not used); `nocommit/` holds anything that mentions crab (CRAB transcripts carry pre-signed credentials, never commit) | yes, except `nocommit/` |

Default output locations follow this layout: `das_inventory.sh` writes to `das/inventory_dumps/`, `build_from_scan_log.py` to `drafts/`,
`das_scan.sh` / `das_discover_run3.sh` take `--out script/das/...` (see their headers), `sweep_inventories.sh` to `inventory/`, `runlog.sh` to `runlogs/`.
