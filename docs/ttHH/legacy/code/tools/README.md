# Archived QA tool

`validate_events.py` — skim-efficiency / bookkeeping checker (output
`Events.num_entries` vs Σ `Runs.genEventCount`, summed across files).
**Unmaintained**, archived because the current pipeline is a full passthrough
with no skim to measure. Method, usage, and its important limits are
documented in [`../../../02_legacy_ttbar_pipeline.md`](../../../02_legacy_ttbar_pipeline.md)
§8. Copy it back into `script/` if a skim is reintroduced.
