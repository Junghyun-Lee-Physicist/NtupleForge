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
[`README.md`](README.md) (this index) → [`04_architecture.md`](04_architecture.md)
→ [`05_troubleshooting.md`](05_troubleshooting.md).

## Rule 1 — The top-level `README.md` stays minimal

`../README.md` contains only a brief description and the commands needed to
**run** the code (setup, local run, CRAB). Everything explanatory —
internals, physics, incident history, how-tos — lives in `docs/`. If you find
yourself adding a paragraph of explanation to the README, it belongs in a
`docs/` file instead, with a one-line pointer from the README if needed.

## Rule 2 — Every change gets a CHANGELOG entry

When you change code, add an entry to [`02_CHANGELOG.md`](02_CHANGELOG.md) under
**[Unreleased]** recording:

- **what** part of the code changed (file / function / module),
- **how** it changed (the concrete edit), and
- **why** — the problem it fixes *or* the purpose it serves.

Bad: *"updated categorizer."* Good: *"`decode_genttbarid()` — tightened the
cc code range from 41–49 to 41–45 to match GenTtbarCategorizer.cc; the loose
bound let nonexistent codes fall through to `AddCjet`."*

## Rule 3 — Every problem gets a troubleshooting entry

When you hit a bug, a crash, a confusing log, or a CRAB failure, add an entry
to [`05_troubleshooting.md`](05_troubleshooting.md) Part A using the existing
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
| Any code change | [`02_CHANGELOG.md`](02_CHANGELOG.md) (always) |
| A bug / crash / failure + its fix | [`05_troubleshooting.md`](05_troubleshooting.md) Part A |
| A new validation method or a limit of an existing one | [`05_troubleshooting.md`](05_troubleshooting.md) Part B |
| Changed how the framework/driver/modules work, or a new module pattern | [`04_architecture.md`](04_architecture.md) |
| A PyROOT / NanoAOD-tools access quirk and its workaround | [`06_nanoaod_branch_access.md`](06_nanoaod_branch_access.md) |
| A branch-list / NanoAOD-schema finding, or a version migration | [`08_branch_schema_migration.md`](08_branch_schema_migration.md) |
| A physics definition, category, or sample-stitching decision | [`ttHH/01_physics.md`](ttHH/01_physics.md) |
| Anything about the retired categorization pipeline | [`ttHH/02_legacy_ttbar_pipeline.md`](ttHH/02_legacy_ttbar_pipeline.md) |
| New run command / changed CLI surface | [`../README.md`](../README.md) **and** CHANGELOG |

If a change touches several of these, update all of them — they cross-link, so
stale references are easy to spot (and easy to catch with the link check
below).

## Rule 5 — Keep the live tree and the archive separate

- **Live tree** (`script/`, `modules/`, `branches/`, `crab/`, `crabConfig/`)
  is the working full-NanoAOD-passthrough pipeline plus generic examples.
  Keep it minimal — only what is needed to run, plus illustrative examples.
- **`docs/ttHH/legacy/code/`** is verbatim, **unmaintained** reference. Do not wire
  it into the build or import path. To revive something, copy it into the live
  tree (checklist: [`ttHH/02_legacy_ttbar_pipeline.md`](ttHH/02_legacy_ttbar_pipeline.md) §9)
  and then it follows all the rules above.

## Rule 6 — Keep the CRAB output filename in sync across both places

The output filename is hardcoded in **two** files and they **must match**, or
CRAB stageout fails with exit `60302` (it validates the staged file against
the PSet output name — see [`05_troubleshooting.md`](05_troubleshooting.md) §A7):

- `crab/PSet.py` — `process.output = cms.OutputModule("PoolOutputModule",
  fileName = cms.untracked.string("<name>"))`
- `crab/submit_crab.py` — `out_name = "<name>"`

Both currently use `forgedNtuple.root` (renamed from `slimmedNtuple.root`
on 2026-07-26, D-F). **If you change one, change the
other** in the same commit. (The proper long-term fix is to have
`submit_crab.py` overwrite the PSet filename from the YAML at submission time
so there is a single source of truth; until that lands, this rule stands.)

---

## Rule 7 — Renaming or moving a file? Grep the build/submit scripts first

File paths and **names** are load-bearing in places that are easy to forget,
because the CRAB submit/build layer references files by glob or by hardcoded
path, not by import. Renaming or moving a file can silently drop it from the
sandbox or point a driver at a path that no longer exists — and it will **not**
fail locally; it fails only on the worker, minutes into a real submission.

This actually happened: renaming `modules/_nanoaod_compat.py` →
`modules/nanoaod_branch_access.py` dropped the leading underscore that
`submit_crab.py` used to auto-include helpers (`glob("modules/_*.py")`), so the
helper was never shipped and every job died at import
(see [`05_troubleshooting.md`](05_troubleshooting.md) §A0).

**Before you rename or move any file in the live tree, grep for it** — the name,
the stem, and any glob that could match it:

```bash
git grep -n -e 'oldname'  -e 'oldstem'  -e '_\*\.py'  -e 'inputFiles' -- \
    crab/ script/ crabConfig/ modules/
```

Check specifically:
- **`crab/submit_crab.py`** — `inputFiles`, the helper-shipping glob, `branch_file`,
  the module-name derivation (basename → `-I` arg), `psetName`, `scriptExe`.
- **`script/run_postproc.py`** — any path/default it assumes.
- **`crabConfig/*.yaml`** — `analysis_module`, `branch_file` paths.
- **PSet / output-name** couplings (Rule 6).

Then update every hit **in the same commit**, and — because none of this can be
verified in a container without CRAB — say so and re-run one real CRAB job to
confirm. Prefer decoupling name from behavior (e.g. ship *all* sibling helpers,
not files matching a name pattern) so the next rename cannot break shipping.

---

## Rule 8 — Branch 목록은 손으로 쓰지 않는다: 실제 파일에서 유도한다

`branches/*.txt` 를 만들거나 고칠 때는 **반드시** 실제 NanoAOD 파일의 스키마를
덤프해서 그것에 대고 검사하십시오. 기억, 옛 인벤토리, 다른 연도의 목록에서
베끼는 것 모두 금지입니다. branch 목록의 실패는 **양방향으로 조용**하기
때문입니다 — 매치 안 되는 `keep`은 job당 ROOT 에러 한 줄로 묻히고, 빠진 branch는
`eventBuffer`가 0으로 기본값 처리해 물리를 조용히 망칩니다.

최소 절차 (전체와 복사용 명령어: [`08_branch_schema_migration.md`](08_branch_schema_migration.md) 2절):

1. `voms-proxy-init -voms cms -rfc -valid 192:00`
2. `dasgoclient -query="dataset=..."` — **plain 캠페인**을 고를 것
   (`JMENano`/`BTVNano`/`PFNano` flavour는 스키마가 다름)
3. `xrdcp` 로 **/tmp 에 복사** — lxplus에서 XRootD 직독은 90배 느립니다
   (2.2 Hz vs 199.5 Hz, 측정: 08 2절 Step 2)
4. `script/dump_branch_inventory.py` 로 인벤토리 TSV
5. `script/check_branchlist.py --inventory ... --profile ...` — exit 0이 아니면 커밋 금지
6. `script/run_postproc.py -N 2000` 으로 실제 실행 —
   스키마가 맞아도 **reader 타입 지원**은 별개 문제입니다

성능을 논할 때는 `time` 의 `user+sys` 만 쓰십시오. `real` 은 page cache에
좌우되고, 모듈을 탓하기 전에 `modules/noop.py` 로 baseline을 재야 합니다.

## Before you commit (quick self-check)

- [ ] CHANGELOG entry added (Rule 2).
- [ ] Any new bug/fix recorded in troubleshooting (Rule 3).
- [ ] Relevant doc(s) updated (Rule 4).
- [ ] Touched a `branches/*.txt`? Derived it from a real file and
      `check_branchlist.py` exits 0 (Rule 8).
- [ ] Renamed/moved a file? Grepped `crab/`, `script/`, `crabConfig/` for the
      old name/stem and any matching glob (Rule 7).
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
