# Developer Guidelines

Rules for anyone editing NtupleForge. These are not optional style notes —
they exist so the project's hard-won knowledge (every bug, every fix, every
design choice) stays recorded and discoverable instead of living only in
someone's head or in git archaeology.

---

## Rule 0 — Read all of `docs/` before you change anything

Before your first edit in a session, read **every** file in
[`docs/`](README.md). The bugs documented here are subtle and recur (silent
`UChar_t` failures, zombie input branches, `hasattr` crashes, counter
unreliability). Reading first is cheaper than rediscovering them. Start with
[`README.md`](README.md) (this index) → [`05_architecture.md`](05_architecture.md)
→ [`06_troubleshooting.md`](06_troubleshooting.md).

## Rule 1 — The top-level `README.md` stays minimal

`../README.md` contains only a brief description and the commands needed to
**run** the code (setup, local run, CRAB). Everything explanatory —
internals, physics, incident history, how-tos — lives in `docs/`. If you find
yourself adding a paragraph of explanation to the README, it belongs in a
`docs/` file instead, with a one-line pointer from the README if needed.

## Rule 2 — Every change gets a CHANGELOG entry

When you change code, add an entry to [`03_CHANGELOG.md`](03_CHANGELOG.md) under
**[Unreleased]** recording:

- **what** part of the code changed (file / function / module),
- **how** it changed (the concrete edit), and
- **why** — the problem it fixes *or* the purpose it serves.

Bad: *"updated categorizer."* Good: *"`decode_genttbarid()` — tightened the
cc code range from 41–49 to 41–45 to match GenTtbarCategorizer.cc; the loose
bound let nonexistent codes fall through to `AddCjet`."*

## Rule 3 — Every problem gets a troubleshooting entry

When you hit a bug, a crash, a confusing log, or a CRAB failure, add an entry
to [`06_troubleshooting.md`](06_troubleshooting.md) Part A using the existing
template:

- **Symptom** — what you observed.
- **Signature** — the exact error text / log snippet (paste it verbatim).
- **Root cause** — why it happened.
- **Fix** — the change that resolved it (link the commit if there is one).
- **Validated by** — how you confirmed the fix.

Do this *even if the fix was quick.* The five-bugs-in-a-row session that most
of Part A came from is the reason this rule exists: each bug looked trivial in
isolation and cost hours because it was undocumented.

## Rule 4 — Record in the doc that matches the situation

Leaving a record is the default, not an afterthought. Route it by topic:

| What you did / found | Where it goes |
|---|---|
| Any code change | [`03_CHANGELOG.md`](03_CHANGELOG.md) (always) |
| A bug / crash / failure + its fix | [`06_troubleshooting.md`](06_troubleshooting.md) Part A |
| A new validation method or a limit of an existing one | [`06_troubleshooting.md`](06_troubleshooting.md) Part B |
| Changed how the framework/driver/modules work, or a new module pattern | [`05_architecture.md`](05_architecture.md) |
| A PyROOT / NanoAOD-tools access quirk and its workaround | [`07_nanoaod_branch_access.md`](07_nanoaod_branch_access.md) |
| A physics definition, category, or sample-stitching decision | [`02_physics.md`](02_physics.md) |
| Anything about the retired categorization pipeline | [`09_legacy_ttbar_pipeline.md`](09_legacy_ttbar_pipeline.md) |
| New run command / changed CLI surface | [`../README.md`](../README.md) **and** CHANGELOG |

If a change touches several of these, update all of them — they cross-link, so
stale references are easy to spot (and easy to catch with the link check
below).

## Rule 5 — Keep the live tree and the archive separate

- **Live tree** (`script/`, `modules/`, `branches/`, `crab/`, `crabConfig/`)
  is the working full-NanoAOD-passthrough pipeline plus generic examples.
  Keep it minimal — only what is needed to run, plus illustrative examples.
- **`docs/legacy/code/`** is verbatim, **unmaintained** reference. Do not wire
  it into the build or import path. To revive something, copy it into the live
  tree (checklist: [`09_legacy_ttbar_pipeline.md`](09_legacy_ttbar_pipeline.md) §9)
  and then it follows all the rules above.

## Rule 6 — Keep the CRAB output filename in sync across both places

The output filename is hardcoded in **two** files and they **must match**, or
CRAB stageout fails with exit `60302` (it validates the staged file against
the PSet output name — see [`06_troubleshooting.md`](06_troubleshooting.md) §A7):

- `crab/PSet.py` — `process.output = cms.OutputModule("PoolOutputModule",
  fileName = cms.untracked.string("<name>"))`
- `crab/submit_crab.py` — `out_name = "<name>"`

Both currently use `slimmedNtuple.root`. **If you change one, change the
other** in the same commit. (The proper long-term fix is to have
`submit_crab.py` overwrite the PSet filename from the YAML at submission time
so there is a single source of truth; until that lands, this rule stands.)

---

## Before you commit (quick self-check)

- [ ] CHANGELOG entry added (Rule 2).
- [ ] Any new bug/fix recorded in troubleshooting (Rule 3).
- [ ] Relevant doc(s) updated (Rule 4).
- [ ] Live Python still imports/compiles
      (`python3 -m py_compile script/*.py modules/*.py crab/*.py`).
- [ ] Internal doc links resolve. A quick checker:

  ```bash
  python3 - <<'PY'
  import re, pathlib
  bad = 0
  for md in pathlib.Path("docs").rglob("*.md"):
      for m in re.finditer(r"\]\(([^)]+)\)", md.read_text()):
          t = m.group(1).split("#")[0]
          if t and not t.startswith("http") and not (md.parent / t).resolve().exists():
              print(f"BROKEN: [{md}] -> {m.group(1)}"); bad += 1
  print("OK" if not bad else f"{bad} broken link(s)")
  PY
  ```
