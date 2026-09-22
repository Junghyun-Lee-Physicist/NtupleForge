# script/ -- tools, registries, and the records they produce

Layout since 2026-09-22 (before that every file sat flat in this directory).

| Where | What | Committed? |
|---|---|---|
| `script/*.sh`, `script/*.py` | the tools (DAS scan / inventory / status, branch inventories and checks, config builder, run logging, local checks, v9-v15 validation) | yes |
| `script/samples_registry.txt`, `script/samples_registry_run3.txt` | the sample registries (Run 2 / Run 3), the single source for `das_scan.sh` and `build_from_scan_log.py` | yes |
| `script/inventory_manifest_*.txt` | rows for `sweep_inventories.sh` (which datasets to dump one file of) | yes |
| `script/validate_v9.json` | settings for `validate_topcpvcat.py` (v9 test) | yes |
| `script/das/` | DAS scan logs (`das_ttHH_<era>_<ver>_<stamp>.log`, the INPUT of the builder), Run 3 probe / discover logs, the 2026-07-26 UL18 scan, the v9-vs-v15 compare table, `missing_in_v15_2017UL.tex` | yes |
| `script/das/inventory_dumps/` | full-campaign DAS dumps of `das_inventory.sh` (`.tsv` + `.match.txt` + `.names.txt`, 5-9 MB each): the evidence behind the cross-campaign audits in `docs/10_validation_ledger.md` | yes |
| `script/das/sherpa/` | DAS listings of Sherpa tt+jets samples (Run 2, Run 3, status) gathered for the MC request discussion | yes |
| `script/drafts/` | `build_from_scan_log.py` output: `review_das_*.{md,tsv}` and `config_das_*.yaml.draft`; a draft becomes real only when copied to `crabConfig/` by hand | yes |
| `script/inventory/` | one-file branch inventories (`inv_*.tsv`) and v9-v15 diffs (`diff_*.txt`) from `dump_branch_inventory.py` / `sweep_inventories.sh` | yes |
| `script/runlogs/` | `runlog.sh` records of every lxplus step (`run_<step>_<stamp>.log`) + `LEDGER.tsv`; `nocommit/` holds anything that mentions crab (CRAB transcripts carry pre-signed credentials, never commit) | yes, except `nocommit/` |

Default output locations follow this layout: `das_inventory.sh` writes to `das/inventory_dumps/`, `build_from_scan_log.py` to `drafts/`,
`das_scan.sh` / `das_discover_run3.sh` take `--out script/das/...` (see their headers), `sweep_inventories.sh` to `inventory/`, `runlog.sh` to `runlogs/`.
