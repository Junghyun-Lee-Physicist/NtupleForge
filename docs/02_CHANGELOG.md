# Changelog

All notable changes to NtupleForge. Reconstructed from git history
(`dev260412_TTbarCategory` branch) and curated into logical milestones rather
than raw commits. Dates are approximate (derived from commit/backup
timestamps; `26MMDD` suffixes seen in the repo decode as `20YY-MM-DD`).

The format loosely follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased], 2026-10-01: 2024 failures diagnosed (A27, A28); P7.1 decided (copy-first input, exit codes through the FJR), not yet used on the grid

### Found
- `docs/05_troubleshooting.md` A27: the 2024 50115 jobs at T1_US_FNAL (all 201 of `WJetsToQQ_HT400to800`): the P7 probe opened
  `root://cmsxrootd-site.fnal.gov//store/...`, and the next open of the same URL, by NanoAODTools, got `[3011] No servers are
  available to read the file`; no job report, 50115, and CRAB's three retries ended the same way at FNAL. Whether the second open
  itself is refused is being checked (lxplus three-open test, FNAL finished-job count; workspace RUNBOOK section 17).
- `docs/05_troubleshooting.md` A28: CRAB does not get a scriptExe's exit code as it is. Its wrapper (CRABServer `CMSRunAnalysis.py`)
  uses the first `FrameworkError` of `FrameworkJobReport.xml` and only without one the application exit code, which was 5 for our
  1 and our 85 alike (job logs of 2024); `RetryJob.py` does not retry 5. So the audit's 85 at Brunel (`[3005] I/O limit exceeded`,
  6,072 s at 24 Hz) was recorded as 5 and not retried; without a report CRAB records 50115 (retried). The CRAB column of A23 (84 / 85
  "retried at another site") never applied (an AI design error of 2026-09-28); A23 and A24 carry a correction note.

### Added (P7.1, DECIDED in `03_DECISIONS.md` D-2026-10-01-p71 by the user; only new tasks use it: running tasks keep their sandbox)
- `script/run_postproc.py --input-copy`: a remote site PFN (`root://`, `roots://`, `xroot://`) is copied with `xrdcp -f -N` into
  `./forge_in/store/...` first and NanoAODTools and the audit read the copy (one remote open). If that copy fails: the AAA copy of
  `--input-fallback`, then the PFN opened at the site (`FORGE|INPUT|<lfn>|local|<pfn>|stream (<why the copies failed>)`), then AAA
  directly; the reasons of every failed step are kept in the line. A local PFN is not copied; without `--input-fallback` a failed
  site gives `FORGE|INPUT|<lfn>|none|<why>` and the LFN unchanged. FORGE|INPUT reasons may now be 500 characters (was 200).
- `script/run_postproc.py fjr_mark_error()`: a non-zero `--audit` code puts `<FrameworkError ExitStatus Type="Forge...">` first in the
  report NanoAODTools wrote (`CRAB_ERROR`: 85 -> 8021 and 84 -> 8020, retried at another site; 1 after the copy -> 1, retried;
  5 -> 80005 and 7 -> 80007, not retried; the reason in printable ASCII) and prints `FORGE|FJR|...`; nothing without a report (50115
  as before) or with one that does not parse. `forge_audit.LAST_FAIL` holds the one-line reason. The exit codes do not change.
- `crab/crab_script.py`: logs the code CRAB will take from the report when its first `FrameworkError` is run_postproc.py's; the exit
  code is passed on as before.
- `crab/submit_crab.py`: YAML `input_copy: true|false` (default true: `--input-copy` in `crab_args.txt`), preflight line `input copy`
  (WARN when off).
- `script/forge_campaign_audit.py` T1: the jobs that copied their input from the site, with that xrdcp time, and those that read it
  at the site after both copies failed.

### Review (independent agent, 2026-10-01; both mock suites reproduced, CRABServer sources read)
- Fixed: `crab_script.py` exited 0 when the report carried a Forge `FrameworkError` (from the CRAB3AdvancedTopic twiki); the wrapper
  source reads the report whatever the exit code, and exit 0 would have turned an unregistered `FrameworkError` into a success, so
  the exit code is passed on again. Code 1 went to 8033, which `RetryJob.py` does not retry: now 1 (retried). Control characters in
  the reason made the report unparseable (expat): printable ASCII only. After a failed site copy the site was opened before the AAA
  copy, the very open-then-reopen pattern of A27: the AAA copy now comes first. The RUNBOOK section 17 resubmit generator could
  give two `crab resubmit` lines for one task (the second can be refused while the first is processed): one line per task now;
  the job table missed the `toRetry` state; the replica check gave dataset-level site names only: now with DAS fractions.
- Recorded: CRAB prints `Postprocessing failed` in the exit-code column of some jobs (11 fields): they go to the plain resubmit, as
  intended. Hypothesis wording in README, `run_postproc.py` and the preflight line made factual. The "no partial copy left" checks
  could not fail (the mock xrdcp wrote nothing): the failing mock now leaves a partial file.

### Validated (offline, this session)
- `test_forge_audit_mock.py` 96 checks (20 new: the report marking for 85 / 84 / 5 / 7 / 1, no report, an unparseable report, a reason
  with control characters, the site copy, the AAA copy after a failed site copy, both copies failing, all failing, a local PFN, without
  `--input-fallback`, `crab_script.py` passing the code on); `test_submit_crab_mock.py` 52 (4 new); nine mutations of the new code each
  make named checks fail. Real ROOT: 6 new checks in `test_forge_audit_root.py` (the copy with real NanoAODTools, the AAA copy after a
  failed site copy, all copies failing, a real report marked by a C2r FAIL, `crab_script.py` in a flattened job directory) and 1 in
  `test_forge_campaign_audit_root.py`: in the AI session with real ROOT 6.40 and NanoAODTools 26/26 and 22/22 ALL PASS; on lxplus
  (ROOT 6.30) next (workspace RUNBOOK section 18).

## [Unreleased], 2026-09-30 (2): P6 done, 2024 production submitted (P7), 2018UL Data campaign audit passed (P8); records only

### Added
- `docs/05_troubleshooting.md` A26: a submission where every task is FAILED and the summary column shows only curl's progress
  meter: the CRAB server answered `502 Bad Gateway` to the client's first query (`info?subresource=delegatedn`) before any request
  was sent (2024 MC, 13:19 UTC). Diagnosis from the transcript without its signature lines, a check that no task reached the server
  (`crab tasks`), removal of the stale project directories only when none has a `.requestcache`, and the same submit line again
  (60 OK at 16:31 UTC). A possible later change to `submit_crab.py` (show the `HTTP/1.1 NNN` or `curl: (N)` line in the summary) is
  noted, not made.

### Changed
- `docs/05_troubleshooting.md` A24: the diagnosis says that a CRAB project directory is `<jobID>/crab_<key>` with `-` turned into
  `_` (`submit_crab.py`: `req_name = key.replace("-", "_")`); the resolution record has `ST_t_top` (169/169 after the second plain
  resubmit, no whitelist needed) and the lxplus test of the fallback on a real LFN (EOS open fails, xrdcp 2,600 MB in 149 s,
  closure PASS on 2,000 events).
- Plan `12`: P6 DONE, P7 SUBMITTED, P8 2018UL Data PASS; `01_STATUS.md` row 21; `09` section 27.

### Validated
- Ledger V53 (the pilot Data audit, now 82/82: ALL PASS, the output event set equal to the no-skim pilot after the RVec
  expression), V54 (the P7 code on lxplus: tests 76 / ALL PASS / 20, the real-LFN fallback, preflights MC 41/0/0 and Data 39/2/0),
  V55 (the 2018UL Data campaign audit at KNU: 8 datasets, 1,466/1,466 outputs, sum of `Events` = DAS 1,660,950,742, 773.7 GB).

## [Unreleased], 2026-09-30: input fallback to AAA, audit v2 (C2r and C3 can fail a job), 2024 wall time 1440 min (D-2026-09-30-p7); P6 KNU audit

### Added
- `script/run_postproc.py --input-fallback URL`: CRAB can run a job at a site that does not hold its input (CMS overflow); cmsRun
  falls back to AAA there, NanoAODTools does not (it opens the site's PFN from `edmFileUtil -d`), so the job died in two minutes
  with 50115 (2018UL, docs/05 A24). With the flag every LFN is opened at the site first, the same way. If that fails, URL + LFN
  (`root://cms-xrd-global.cern.ch//store/...`) is copied with `xrdcp -f -N` into `./forge_aaa/store/...` (timeout 3600 s) and
  NanoAODTools and the audit read the copy: reading through AAA event by event ran at 9 and 59 events/s in P5, hours to a day for
  the largest 2024 file (2 GB, 611k events), while xrdcp moved 269 MB in 15 s. Only if the copy fails is URL + LFN read directly.
  The probe's ROOT error lines are silenced (`gErrorIgnoreLevel` kFatal for the probe only, restored on every path): a missing
  local replica is not a read error of the job, and the campaign audit's L1 counts every `Error in <` line of the job log (C2e's
  capture starts later). The reasons are kept: one `FORGE|INPUT|<lfn>|local|<pfn>`, or
  `FORGE|INPUT|<lfn>|fallback|<url>|<why the site failed>|copy (<MB> MB in <s> s) <path>` or `...|stream (<why the copy failed>)`
  line per input. `ForgeAudit`, `ForgeProvenance` and `FORGE|FILE` record the LFN given, not the name opened (`args.input_lfn`,
  `forge_audit.INPUT_LFN`). Other names are kept; without the flag nothing changes. A15 (the 2026-07-27 fallback, reverted then)
  is marked superseded; A24 says how its reasons were met.
- `crab/submit_crab.py`: YAML `aaa_fallback` (default true: `--input-fallback root://cms-xrd-global.cern.ch/` in `crab_args.txt`;
  false gives the arguments of before; `"root://<host>[:<port>]/"` picks another redirector) and `site_blacklist` (a list or a
  comma string of CRAB site names or wildcards such as `T2_US_*` -> `config.Site.blacklist`); an invalid value (`"root://"`
  alone, a number, `T0_...`) stops before any CRAB call. Preflight lines `input fallback` (WARN when off), `site blacklist`,
  `job resources` (max_memory, max_runtime).
- `script/forge_campaign_audit.py` T1: the counted jobs whose log has a `FORGE|INPUT ... |fallback|` line, their xrdcp time
  (outside the payload times) and those that read the input directly without a copy.
- `docs/05_troubleshooting.md` A24 (overflow and the missing AAA fallback: symptoms, diagnosis with `crab status --long`,
  `crab getlog --short` and `dasgoclient site file=`, handling for running and for new tasks, a "resolution record" to fill in)
  and A25 (60322 at stage-out, T2_US_Vanderbilt refusing an X509 write).

### Changed
- `script/forge_audit.py` audit version 2 (the trees are unchanged): C2r FAIL when `Runs.genEventCount` != entries read (whole
  file); C3 WARN above 1e-6 and FAIL above `C3_FAIL = 1e-5`; both give exit 5; both sums 0 is a PASS (0 vs 0 agrees, as the
  campaign audit's D6). `TFile.Open` raising `OSError` (ROOT 6.30) in the audit now gives 84 like a null pointer did, not 85 or 7.
  `lfn_of` drops a `?query` (as NanoAODTools' job report does).
- `crabConfig/config_ttHH2024_v15_had_{MC,Data}.yaml`: `max_runtime: 1440` (the FileBased default of 600 min would cut the slowest
  `TTbar_Hadronic` jobs: 611k input events per file, the slowest pilot job took 7,042 s on 79k).
- Tests: `test_forge_audit_mock.py` 76 checks (C2r FAIL, C3 WARN and FAIL, both sums 0, an `OSError` open -> 84, nine fallback
  cases with a mock `edmFileUtil` and `xrdcp`: local replica, no replica -> copy, a raising open, no `edmFileUtil` (PATH without
  any, also after cmsenv), xrdcp failing -> direct read, no flag, no audit (the error level is restored), a site PFN with a
  `?query` (the LFN is recorded), a non-LFN name); `test_submit_crab_mock.py` 48 checks, case 17 (default on,
  `aaa_fallback: false` = the old arguments, blacklist and 1440 reach the CRAB config, a wildcard and a redirector with a port,
  five invalid values, the preflight lines); `test_forge_audit_root.py` 20 checks (the fallback with real ROOT and NanoAODTools,
  a fake `edmFileUtil` and `xrdcp`: copy, direct read, local; no ROOT error line from the probe, the ForgeAudit file is the LFN,
  read-back PASS); `test_forge_campaign_audit_root.py` 21 checks (the D6 case is now a 5e-6 offset that the job audit lets
  through; T1 with a copy job and a direct-read job).
- `README.md`: `--input-fallback`, `aaa_fallback`, `site_blacklist`, `max_runtime`.

### Review (2026-09-30, before deploying)
- An independent review of the P7 diff (all four suites reproduced) found: the mock fallback case "no `edmFileUtil`" used the
  caller's PATH and would fail on lxplus after cmsenv (fixed: PATH without any `edmFileUtil`); the recorded LFN came from the
  site PFN and kept a `?query` (fixed: the LFN given is recorded); C3 FAILed 0 vs 0 (fixed); no test checked that the probe
  restores the error level (added, with a negative control); exceptions other than `OSError` could leave the probe (now caught,
  the input falls back); an empty `edmFileUtil` answer gave an empty reason; `job_options` accepted `"root://"` and rejected
  CRAB wildcards (fixed); RUNBOOK section 15 step 1 needed a `cd` and step 3 its md5 values. Reading through AAA directly would
  take hours to a day for a 2 GB input (P5 rates), hence the copy. Not changed: `pin_error_level` does nothing while ROOT's level
  is still unset (-1) and a `.rootrc` would raise it later (since P4; no such `.rootrc` on the grid is known); the campaign test
  no longer has an input with a `genEventCount` mismatch (audit v2 fails such a job, so D6's count branch only matters for audit
  v1 outputs such as the P6 pilot).

### Validated
- KNU (cms01, ROOT 6.30/09), `forge_campaign_audit.py` on the skim pilot (plan 12 P6, `09` section 26, ledger V53): tool test 19/19;
  MC ALL PASS (`ZZ` 76/76 and 4,800,000 input events = DAS, X7 against the 09-24 no-skim pilot the same 122,447 events, K the same
  579,624 keys; `TTbb_Hadronic` 189/189, 14,990,580 = DAS, `genEventCount` exact in every file, sum of weights 4.68e-8 off in
  every file); Data 81/82 (job 82 still running; the missing events are exactly one file's). Sizes against the 09-28 projection:
  `ZZ` +54 % (about 1.5 MB per file of non-Events trees), `TTbb_Hadronic` +32 % (65 % pass against the 52 % of its proxy),
  `JetMET0` 2024H -9.5 %; 2024 total about 2.1-2.2 TB.

## [Unreleased], 2026-09-29: lxplus checks of the 2024 skim + audit passed (plan 12 P5), skim pilot submitted (P6), campaign audit tool for KNU

### Added
- `script/forge_campaign_audit.py -c CONFIG --das script/drafts/review_das_*.tsv [--base DIR] [--reference-config CFG]
  [--scan-logs] [--only KEY ...] [--tsv OUT] [--threads N]`: read-only audit of a whole CRAB campaign where it is stored (default
  base KNU `/pnfs/knu.ac.kr/data/cms/store/user/junghyun`, CRAB layout `<output_base>/<primary>/<key>/<YYMMDD_hhmmss>/<NNNN>/`),
  dataset by dataset against the DAS numbers of the review table. D1 outputs == DAS files and job ids 1..nfiles; D2 (audit) every
  output has `ForgeAudit` + `ForgeProvenance` and its `Events` == its sum of `n_pass`; D3 (audit) every input in exactly one row, none
  read only in part; D4 sum of `n_in` (audit), or of the output `Events` for a campaign without skim and audit, == DAS nevents; D5
  (audit) one skim, one git commit, one branch-list md5; D6 WARN (audit, MC) `Runs` sums for the dataset and per file (the largest
  relative difference and its file, the number the C3 limit is set from); D7 WARN files under `failed/` (not counted; tempTTHH
  `make_filelists.py` would pick them up); D8 WARN more than one task directory; K (audit, MC) `ForgeTTbbKeys`: rows per output ==
  its `ForgeAudit` count of codes 53..55, the pass=1 keys == the output events with codes 53..55, and with a reference every key ==
  the reference events with codes 53..55 (key sets compared as multisets here and in X7); X7 (`--reference-config`, a campaign without a skim on the same dataset) the
  (run, lumi, event) set of the outputs == the reference outputs that pass the RVec expression, event by event; D0 FAIL for an
  output that cannot be opened or read (the run goes on); L1 (`--scan-logs`)
  no ROOT error line (SetBranchStatus lines of C2w excluded) in the log tarball of a counted job and every such log holds the
  NanoAODTools end line `Total time ...` (else the tarball proves nothing): the after-the-fact C2e for 2018UL, submitted without
  the audit; T1 (`--scan-logs`, INFO) job time from those logs (NanoAODTools `Total time`, and `t_s` of `FORGE|JOB` with the
  audit: median and largest), WARN when a counted job's `FORGE|JOB` says exit != 0. Prints `FORGE-CAMPAIGN|key|outputs=|n_in=|n_out=|pass=|MB=|kB/ev=|failed_dir=|verdict`,
  the checks, `TOTAL|...` and `RESULT`; exit 0 (WARN allowed), 1 a FAIL, 2 arguments or nothing under the base yet.
- `script/test_forge_campaign_audit_root.py` (real ROOT and NanoAODTools, lxplus or KNU after cmsenv): synthetic inputs, two
  campaigns made with the real `run_postproc.py` (no skim as the reference; `--skim 6j20 --audit`) in the CRAB layout under a
  temporary store with a `failed/` copy, log tarballs, a DAS table and YAML configs; 19 checks: the good trees PASS for MC and Data
  (X7 with 1 and 2 threads, K with the reference), the `failed/` copy not counted (D7 WARN), T1 from real job output, and broken
  copies each giving the expected verdict (a missing job: D1 D3 D4 X7; an input twice: D1 D3 and K; outputs of another skim: D5 X7;
  outputs without the audit: D2; DAS nevents off by one: D4; a read error line in a log, and a log without the job output: L1; a
  `ForgeTTbbKeys` row missing: K, with 2 threads; `Runs` sums off in one input: D6 WARN naming the file; the reference copied into
  a second task directory: X7 EXCESS and K), and damage that must end in a FAIL line and a RESULT line, not a traceback (an output
  that is not a ROOT file: D0, X7 not compared; a corrupt log tarball: L1). ROOT 6.40 in the AI session: 19/19 (ledger V52).

### Changed
- Workspace RUNBOOK 13 4: the local checks copy their inputs to `/tmp` first (`xrdcp` with `XRD_REQUESTTIMEOUT=120`,
  `timeout 1800`, the EU redirector as fallback), as `docs/08` section 2 Step 2 says; the run lines use `${L_MC:?}` so an empty
  variable stops them. The first version read over AAA (see Validated).
- `docs/05_troubleshooting.md` A23: the exit 5 reproduction copies the input first; the campaign audit; tempTTHH
  `make_filelists.py` walks every directory, `failed/` included.
- `README.md`, `script/README.md`: the campaign audit.

### Validated
- lxplus9105, ROOT 6.30.09, commit `039f12b` (P5, workspace RUNBOOK 13; `09` section 25, ledger V51): mock 63/63, CRAB mock ALL PASS,
  real ROOT 17/17. Real 2024 files, all `EXIT : 0` with C1, C2, C2e (0 ROOT error lines) and write PASS, read-back X7, A, K PASS:
  `TTto4Q` first 20,000 events 10,429 pass, `JetMET0` 2024C first 20,000 1,764, `ZZ` one whole file 150,800 3,775 (C2r exact, C3
  relative difference 0 but every `genWeight` is 1, so rounding is not tested; C2w WARN for the 10 LHE keep patterns, both
  SetBranchStatus messages). Branch counts 524 / 278, 484 / 270, 506 / 278 as V48 predicts. Speed: the copy step read over AAA at
  9.2 Hz (`TTto4Q`) and 58.7 Hz (`JetMET0`), from `/tmp` at 3,364 Hz (`ZZ`, job 93 s); the first `ZZ` attempt hung at the AAA open.
  Preflights of the four 2024 configs as expected (MC 38 / 0 / 0, Data 36 / 2 / 0; `forge git 039f12b40630`).
- Skim pilot submitted (P6): 3 tasks (`ZZ` 76, `TTbb_Hadronic` 189, `JetMET0_Run2024H` 82 jobs), job arguments
  `... --skim 6j20 --audit --forge-git 039f12b40630 ...`, the two helpers in the sandbox. lxplus commit `e61130c`.
- 2018UL first `--report`, 16 h after the submission: MC 2,199 / 2,277 done, 78 failed; Data 1,382 / 1,466 done, 82 failed,
  2 transferring. Exit codes: 50115 (no valid FrameworkJobReport: the payload died before NanoAODTools wrote it) for 149 jobs in
  six tasks, 50664 (wall time, 600 min) 2 + 2, 50660 (memory, 2,500 MB) 3, 60328 (stageout) 1, and 3 jobs `failed in postprocessing
  step` (the CRAB post-job, normally the output transfer). Resubmitted per task on 09-29 (50664 `--maxjobruntime=1440`, 50660
  `--maxmemory=4000`, the rest plain).

### Note
- C3 limit still open: set it from `TTbb_Hadronic` in the pilot (powheg weights, 189 whole files: D6 per file).
- Review of the campaign audit by a separate agent (before any real run): no check that can PASS on wrong data; one crash path fixed
  (ROOT 6.30 `TFile.Open` raises `OSError` instead of returning a zombie, so one unreadable output ended the run with a traceback;
  now D0 FAIL; likewise an RDataFrame error in X7 or K and a `zlib.error` from a damaged tarball become FAIL lines); comparisons
  are multisets (a key twice on both sides is the dataset, a key twice on one side is a doubled job or reference); T1 says it is
  payload time only; TSV floats with 12 digits. The same `OSError` means `forge_audit.py` gives 85 (the open prints a ROOT error
  line) or 7, not 84, for an input it cannot open; both 84 and 85 are retried at another site, so this waits for the P7 batch.
- The six plain resubmits were run through a `grep` that matched nothing CRAB prints on success (`Resubmit request sent to the
  server.`), so they printed nothing; their runlogs are the record, and all nine show `Resubmit request sent` (workspace RUNBOOK 14).

## [Unreleased], 2026-09-28 (4): event skim and job audit for 2024 (plan 12 P4; `skim: 6j20`, `audit: true`)

### Added
- `script/forge_skims.py`: the production event selections in one table (`6jcount`, `6j20`, `6j25`, `6j30`, `6j20ht400`), each
  written twice: the TTreeFormula string for `PostProcessor(cut=...)` (the strings `size_options.py` measured on 09-28; the mock test
  compares the two tables) and the same selection as an RVec expression for the audit. The HT of `6j20ht400` is a declared C++
  `forge_ht()` summing in double like `Sum$` (a NaN or inf jet pt gives NaN in both).
- `script/forge_audit.py` (`run_postproc.py --audit`): after NanoAODTools has copied and merged (`-o`, the unchanged C++ path of the
  noop module), every input file is read once more with RDataFrame over the same entry range, reading only `nJet`, `Jet_pt`,
  `Jet_eta`, `genWeight`, `genTtbarId` and the event key. Closure (plan 12 section 2.3): C1 output `Events` == events passing the RVec
  expression (without a skim: == entries read), C2 every file read to the end of its range, C2e no ROOT error line during the copy
  or the audit (fd 2 goes through a separate `tee` process: live in the job log, a copy in `forge_stderr.txt` that is scanned and
  removed; an error level that would hide Error lines is set back to kWarning), C2c the genTtbarId code histogram adds up; WARN only: C2w a keep pattern
  that matches nothing in that file (`Error in <TTree::SetBranchStatus>: unknown branch -> X` for a plain name, `No branch name is
  matching wildcard -> X` for a wildcard, e.g. `LHE_*` in a pythia-only sample; not a read error), C2a input `Events` autosave not 0, C2r `Runs.genEventCount` vs entries and C3 sum of `genWeight` vs
  `Runs.genEventSumw` (relative 1e-6) for a whole MC file; C2r and C3 become FAIL once P5 has measured real files. Only when all
  pass does it append three TTrees (autosave 0): `ForgeAudit` (one row per input: entries, passing, sums of weights, `Runs` sums,
  per `genTtbarId % 100` code count and sum of weights), `ForgeTTbbKeys` (every MC input event with code 53..55 before the skim: key,
  `genTtbarId`, `genWeight`, pass), `ForgeProvenance` (one row per job: json of skim, formulas, branch file and md5, git commit,
  CMSSW, inputs). TTrees because haddnano concatenates them (a TObjString it writes under its own text as key name). Exit codes
  follow CRABServer's retry policy (`RetryJob.py`): 0; 1 NanoAODTools failed or the output could not be written (as before);
  84 an input the audit cannot open and 85 read trouble (C2, C2e, an RDataFrame read exception), both retried at another site;
  5 a closure FAIL without read trouble and 7 an audit bug, not retried. `FORGE|EVT` (the first 20 events of the job), `FORGE|FILE`,
  `FORGE|CHECK`, `FORGE|JOB` lines as in plan 12 section 5.2.
- `script/check_forge_output.py OUT INPUT [--first-entry K] [-N n]`: read-only read-back with real ROOT. X7 the (run, lumi, event)
  set of the output == the input events in that range that pass the RVec expression (event by event, not only counts), A the
  `ForgeAudit` row recomputed, K `ForgeTTbbKeys` == the code 53..55 events, pass=1 all in the output, pass=0 none.
- Tests: `script/test_forge_audit_mock.py` (a JSON-backed mock ROOT and PostProcessor, runs anywhere: 63 checks incl. every exit
  code, the tee capture with a child process, `crab_script.py` passing the code on and printing the capture of a killed job, the
  old sandbox layout and command line) and `script/test_forge_audit_root.py` (real ROOT and NanoAODTools on synthetic
  NanoAODv15-typed files: pt exactly 20 and the next float, abs(eta) exactly 2.5, NaN and inf, no jets, Data, Data with the MC list,
  nothing passing, an empty file, an entry range, two inputs, a haddnano merge, the command line without the new flags, a
  wildcard keep that matches nothing; 17 checks). In the AI session: 63/63 and, with ROOT 6.40 and NanoAODTools 14_2_X, 17/17;
  lxplus (ROOT 6.30) in P5.
- `crabConfig/config_ttHH2024_v15_had_skimpilot{MC,Data}.yaml` (plan 12 P6): the production recipe on `ZZ` and
  `JetMET0_Run2024H` (the datasets of the 09-24 no-skim pilot, whose outputs at KNU are the reference for a dataset-level X7) and on
  `TTbb_Hadronic` (189 files, high pass rate, most events in `ForgeTTbbKeys`).

### Changed
- `script/run_postproc.py`: `--skim NAME` (its formula becomes `PostProcessor(cut=...)`; not together with the validation-only
  `--cut`, exit 2), `--audit` (needs `-o`), `--forge-git`. `forge_skims.py` / `forge_audit.py` are imported only with these flags,
  so a sandbox without them runs every older command line; without the flags the output and the log are what they were.
- `crab/submit_crab.py`: YAML `common` keys `recipe` (only `slim`), `skim`, `audit` (default true with a skim, false without, so the
  submitted 2018UL configs are unchanged); an invalid value is a preflight FAIL and stops a submit before any CRAB call (exit 1).
  With a skim or the audit the two helpers go into the sandbox and `crab_args.txt` gets `--skim`, `--audit`, `--forge-git` (the
  short commit, `+dirty` when tracked files outside `script/runlogs/` are modified, both sides of a rename counted: `runlog.sh`
  appends to `LEDGER.tsv` at every step; `+untracked` when a file the jobs get is not in git, e.g. a new module sibling, which
  is shipped automatically). Preflight lines: `recipe` (what the job will do, with the formula), the two worker files,
  `forge git` (WARN when unknown, dirty or untracked), WARN for a skim with the audit off and for a module other than noop (C1
  assumes no event is dropped). A plain submit logs `Job arguments of tasks submitted now (crab_args.txt): ...` (the file is
  removed at the end of the run; a resubmitted task keeps the sandbox of its first submission).
- `crab/crab_script.py`: when the payload fails and `forge_stderr.txt` is still there (the process died inside the capture), prints
  its first 20 lines, its ROOT error lines (at most 40, without the benign SetBranchStatus lines of C2w) and its last 20; the exit
  code is passed on as before.
- `crabConfig/config_ttHH2024_v15_had_{MC,Data}.yaml`: `skim: "6j20"`, `audit: true` (D-2026-09-28-volume); not submitted before P5
  and P6 (RUNBOOK 13).
- `script/test_submit_crab_mock.py`: cases 11-16 (old config ships nothing new; skim ships both helpers and the arguments, and the
  transcript shows them; audit without skim; unknown skim / recipe stop before CRAB; the preflight lines; `forge git` in a real git
  checkout with the repository's `.gitignore`: a modified `LEDGER.tsv` is clean, an untracked module sibling is `+untracked`, a
  rename out of `script/runlogs/` and a modified branch list are `+dirty`).
- `README.md`, `script/README.md`: the new flags, YAML keys and tools.
- `docs/05_troubleshooting.md` A23: how to read the exit code of an `--audit` job.

### Note
- Found by a dry run of workspace RUNBOOK 13 as written (the real 2024 lists on synthetic inputs, mock CRAB): a wildcard keep
  pattern that matches nothing makes ROOT print `No branch name is matching wildcard -> X` (ROOT 6.30 `tree/tree/src/TTree.cxx`),
  not `unknown branch -> X`. With only the latter treated as benign, every `ZZ` job (pythia only; the 2024 MC list keeps `LHE_*`)
  would have ended in C2e FAIL, exit 85, retried at other sites. Both are C2w now; with the old pattern 14 of the 17 real-ROOT
  checks fail. The same dry run showed that `crab_args.txt` is gone after a submit, hence the new log line.

## [Unreleased], 2026-09-28 (3): 2018UL v15 hadronic submitted with the slimB lists (plan 12 P3)

### Validated
- lxplus941, `31beadf`, workspace RUNBOOK 12: the slimB lists ran through NanoAODTools for the first time (500-event local checks,
  noop module like the CRAB jobs): 551 branches / 291 `HLT_` (2018UL MC `TTToHadronic`) and 485 / 268 (`JetHT` 2018A), exactly the
  `check_branchlist.py` prediction, gen branches present in MC only, no `Error in <` line. Preflights FAIL 0 (Data: the two expected
  gen-branch WARNs). Submitted: MC 42/42 OK, Data 8/8 OK (task names in `09` section 24); lxplus commit `ff52d5f` holds the runlogs,
  the two preflight copies and `LEDGER.tsv` only (no `nocommit/`, no S3 signature). Ledger V49.

## [Unreleased], 2026-09-28 (2): volume decided (10 TB, slimB, 2018UL without skim, 2024 `6j20`); slimB adopted in `branches/`

### Changed
- `branches/branch_hadronic_{2018,2024}_v15_{MC,Data}.txt`: slimB ADOPTED (user decision, `03_DECISIONS.md` D-2026-09-28-volume).
  Each file is the list of 09-28 unchanged plus the drop block of `script/drafts/<file>_slimB.txt`, whose header now starts
  `#  slimB, ADOPTED 2026-09-28` and gives the kept counts. Kept branches: 2018UL MC 717 -> 551 (HLT_ 325 -> 291), 2018 Data A/B/C/D
  627/686/649/664 -> 485/544/507/522, 2024 MC 703 -> 524, 2024 Data 638-648 -> 484-494. `check_branchlist.py` gives the same (A), (B)
  and (C) verdicts on all 17 inventories and the kept sets only shrink; the only HLT paths that go are `HLT_AK8PFJet*` (ledger V48).
  The preflight line becomes `168 rules: 50 keep / 118 drop` (2018 MC) and `135 rules: 26 keep / 109 drop` (2018 Data). The four
  crabConfigs are unchanged (same `branch_file` paths).
- `script/make_slim_branchlists.py`: a list with an ADOPTED block is split at that block. The drafts are made from the part above it
  (byte-identical on regeneration), and `--check` fails when the block's rules differ from a fresh draft of its tier or when the tier
  does not exist for that list; a comment that says ADOPTED without a well-formed block header is a FAIL too (nothing written), so a
  damaged header cannot switch the check off (found by the independent review of this batch). Tried in the AI session: a removed
  drop line, an edited line above the block, a wrong tier name, a header with one space after '#'.
- `script/test_size_options_mock.py`: runs a copy of `size_options.py` in a temp mirror of the repository whose lists are the part
  above an ADOPTED block, so the mock numbers do not depend on the production tier (against the adopted lists three checks failed).
  New check 47: every list's ADOPTED block is well formed (or absent). 47/47 PASS in both trees (adopted and pre-adoption); the v1-signature note still reads "equal the 09-28 lxplus log", which shows the
  part above each block is byte-identical to the 09-28 list. It now needs python >= 3.7 (it imports make_slim_branchlists.py, which
  imports check_branchlist.py); cmsenv has 3.9.
- `script/gen_hadronic_branchlists.py`: refuses to overwrite an existing list whose content differs (exit 1, `--force` overrides).
  The 08-17 generator no longer reproduces any of the four lists (edited by hand since 09-16; it still writes `keep btagWeight_*`,
  and the 2018 lists carry slimB); run on `branches/` it would have undone both without a word.

### Validated
- [7c] measurement v2, 34/34 samples (ledger V47, `09` section 23): the condor job and the interactive run both `EXIT : 0`, `FAILED` 0,
  no ROOT error line; the 22 samples that both measured agree (same LFN, pass counts exact, output bytes within 0.08 %, tree headers
  within 0.16 %), and so do the ten v1 rows (0.01 %, headers 0.14 %). TOTAL TB: today's lists without skim 15.65, slimB without skim 10.98, slimB `6j20` everywhere 3.15; the decided
  combination 5.16 (2018UL 3.05, 2024 2.11).

### Corrected
- The entry below and RUNBOOK 11 say the interactive v2 run of 09-28 "stopped with the ssh connection after two samples". It did not:
  the process went on in the `tmux.service` session on lxplus9110 and finished (`run_size_options_20260928_120729.log`, `EXIT : 0`),
  at the same time as the condor job. Both appended to the same TSV on AFS and no row was damaged (66 rows, all 27 columns).

### Note
- `size_options.py` signatures hash the list bytes, so at HEAD `--project-only` finds no current rows (exit 1, `nothing measured yet
  for these signatures`). The [7c] table stays in the runlog and is recomputed on a checkout of `5fbfdee` (the last commit before
  the adoption).

## [Unreleased], 2026-09-28: the 2018 patches pass against central NanoAODv15 (V1); size_options.py measurement v2

### Fixed
- `script/size_options.py` (measurement v2). The [7c] run of 09-28 on lxplus996 showed two faults of v1. (a) A read error passed
  silently: the site serving the 2018UL `QCD_HT500to700` file throttled the reads (`Error in <TNetXNGFile::ReadBuffer>: ... [3005] I/O
  limit exceeded and wait time hit`, then `Error in <TBranch::GetBasket>: File: root://cms-xrd-global.cern.ch//store/mc/RunIISummer20UL18NanoAODv15/QCD_HT500to700_.../073cc70c-....root
  at byte:..., entry:2759`, ten of each, 2,373 s instead of about 100 s), `TTree::CopyTree` went on with stale buffers and the row was
  recorded; TBranch then stops reporting (`file probably overwritten: stopping reporting error messages`, a limit of 10 per process).
  (b) After `QCD_HT700to1000` the process died of a segmentation violation in `CPyCppyy::op_dealloc` at a function return (runlog
  `EXIT : 129` = 128 + ROOT's `kSigSegmentationViolation`), so the four remaining 2018 samples were not measured. Now:
  every sample runs in a child process of its own (`--child`, internal; `--child-timeout`, default 3600 s), with the C-level stderr
  (fd 2) of every ROOT call captured and the error level set to kWarning in the child (not left to `.rootrc`); any `Error in <` /
  `SysError in <` / `Fatal in <` line makes the sample FAILED (no row, exit 1), the captured lines are still printed (first and last 40
  when ROOT floods; memory stays bounded), and a crash or a timeout of the child fails only that sample. An output file with TFile
  `kWriteError` (a full disk) and a scratch dir with less than `--min-free-mb` (default 500) free also fail the sample; leftovers of an
  earlier attempt are removed before a child starts and a result counts only with exit 0. The child keeps every ROOT object
  referenced and leaves with `os._exit`, so no PyROOT dealloc runs; the parent does not import ROOT. The measurement version is part
  of the row signature, so all v1 rows (2024 ttbar three of 09-27, 2018UL seven of 09-28, and whatever the second v1 command of 09-28 added
  before it was stopped) stay in the TSV as history and are not used:
  the next plain run measures all 34 samples once, resumable as before. The v1 signatures printed in the lxplus log (`28d75c077e12`,
  `261a9d8be076`, `e4c4e53fe381`, `535e676b18b8`) were recomputed from today's inputs and are equal, so exactly those rows drop out.
- `script/test_size_options_mock.py`: 46 checks (was 34). New: no current signature equals the v1 signature of the same inputs (and a
  note whether the v1 recomputation still equals the 09-28 lxplus log), ROOT imported only by child processes (34 in the
  full run), a read error in the AAA copy and one in the skim copies (FAILED, no row, errors still shown, no scratch file), a crashing
  child (that sample FAILED with its last ROOT lines shown, the next sample measured), a hanging child killed by `--child-timeout`,
  a write error, a flood of 100,000 error lines (counted, echo cut), leftovers of an earlier attempt, too little free space, PyROOT
  failing to import in the child (exit 4 with the real reason), `--child-timeout 0` (exit 2), and a ROOT `Warning` line that must not
  fail a sample. The v1 script with the new read-error check fails it (row recorded, exit 0), as it should. An independent review
  pass (a second AI agent with its own experiments: a 4 MiB tmpfs as scratch dir, a stale result file, a 200 MB error flood) found
  four faults in the first v2 draft, all fixed and re-checked: the full disk now gives `FAILED: write error on ... (disk full?)` or
  `only 4 MB free`, no row.

### Added
- `script/condor/size_options.sub` + `script/condor/size_options_job.sh`: the whole [7c] measurement as ONE HTCondor job
  (CMSSW el8 image via `MY.SingularityImage`, `getenv = False`, release set up from cvmfs in the job, `x509userproxy`, condor
  manages no output files, `+JobFlavour = "workday"`, 4 cores), because the interactive v2 run of 09-28 (lxplus9110, `0a4af6d`)
  stopped with the ssh connection after two samples. The job checks the proxy, the CMSSW environment (PyROOT, dasgoclient) and the
  offline test before measuring (exit 12 / 13 / 14), then runs the 2018UL eleven and the full set like RUNBOOK 11, and retries
  failed samples twice (after 10 min, then through `root://xrootd-cms.infn.it/`). Scratch copies go to the worker's local disk;
  only the runlogs and the two TSVs are written to AFS. Dry-run in the AI session with stubbed cvmfs / scram, the mock ROOT and
  the fake dasgoclient, clean environment (`env -i`): all measured, exit 0; a persistent read error, three FAILED passes, exit 1;
  a transient one, measured by the first retry, exit 0; no proxy, exit 12; no CMSSW environment, exit 13.
- `script/condor/submit_size_options.sh` (the user's request, same day): every submission first makes a new VOMS proxy
  (`voms-proxy-init --voms cms --rfc --valid 96:00`, into `~/private/x509up_ntupleforge`), so the job never gets an old proxy file
  close to expiry; then checks the host has `condor_submit` and the el8 image is visible, and submits from the repository. The job
  itself does what `cmsenv` does (`eval scramv1 runtime -sh`, the alias is not available in a script) inside the CMSSW el8 image.
- The two samples that the interactive v2 run finished repeat v1 exactly (2018UL `TTbar_Hadronic` 1.844 / 1.847 kB, `TTbar_SemiLep`
  1.826 / 1.831 kB, every skim column equal): without read errors v1 and v2 measure the same.

### Validated (ledger V45)
- 2018 tt+nb patches vs central NanoAODv15 (plan `docs/12` V1, TTHH O8): 6 samples, 972,574,595 events, 63 condor jobs. First run
  (cluster 13488511, 09-27) with the lxplus binary not rebuilt: 19 of 21 `TTToHadronic` chunks exit 4 (nano read failure, no retry in
  the old binary; loud, not silent). After the rebuild the 19 were resubmitted (cluster 13489070): 63/63 ok, and the aggregation says
  `OVERALL: ALL SAMPLES PASS` (`script/runlogs/run_v1_aggregate_20260928_083134.log`): nano total == v15 DAS, unmatched 0, disagree 0,
  invariants 0 for every sample. The four samples with extend == v15 give exactly the patch row counts and the same 61/62/71/72 split
  as the patch table (TTToHadronic 36,835, TTTo2L2Nu 11,790, ttbb_SemiLeptonic 37,420, ttbb_2L2Nu 15,766); the two with fewer v15 events
  give TTToSemiLeptonic 43,090 (expected 43,086) and ttbb_Hadronic 32,660 (expected 32,649). The patches serve the v15 ntuples,
  including `ttnb_TTbar_SemiLep.root`, on hold since the v9 FAIL of 07-28. Numbers: TTHHGenCategoryTools `docs/06_validation_results.md`.

### Found
- On lxplus9 a session started with plain `tmux new` is killed at logout; a session that survives logout is started with
  `systemctl --user start tmux.service` and entered with `tmux a` (CERN KB0008111, as quoted by the HSF training page "Persistent
  screen or tmux session on lxplus"). Workspace RUNBOOK 11 used plain `tmux` until 09-28 and now uses the service.

## [Unreleased], 2026-09-27: execution plan for the 2018 / 2024 stack plots, one forge with three recipes (docs only)

### Added
- `docs/12_fastpath_workflow_plan.md` (PROPOSED). The user's direction of 09-27: validation must not block production; the analyzer
  runs on the existing kind of ntuple (central NanoAODv15 slimmed here + the MiniAOD-derived tt+nb patch looked up at run time) while the
  MiniAOD products (sidecar patches, enriched NanoAOD) are cross-validated in parallel against NanoAOD `genTtbarId` and the CPV categories;
  NtupleForge does "slimmed NanoAOD / MiniAOD dictionary / MiniAOD-derived NanoAOD" under one command. Content: four tracks (production,
  analyzer, SF and plots, cross-validation) with status per step; user-facing recipe names `slim` / `categorize` / `derive` over the job types
  of `11`; a cross-validation matrix X1-X14 (identity / implication / correlation, pass criterion, tool, what it gates); a log and audit
  convention (fixed `FORGE|...` line prefixes, per event / file / job / dataset / campaign, closure checks C1-C3 that fail the job).
- Design choice recorded there: the 2024 event skim goes through the PostProcessor `cut` path (TTreeFormula entry list, C++) with a new
  named `--skim`, and the audit is a separate RDataFrame pass, because with any module present NanoAODTools loops over every input event in
  python and reads all input branches for every accepted event (`output.py` `FullOutput`, CMSSW 14_2_X). Audit objects are TTree / TObjString
  only because haddnano drops every other type (`PhysicsTools/NanoAOD/scripts/haddnano.py`). `--cut` stays validation-only.
- Speed-up proposed there: the 2018UL configs are 3,743 jobs (2,277 + 1,466 files, 09-23 review tables) against 26,947 for 2024 and
  project to 3.2-4.8 TB ([7b], V44), so if [7c] allows, 2018UL is submitted with today's noop path first and the analyzer's own prescan
  keeps working; the skim code is written for 2024 meanwhile.
- Workspace RUNBOOK section 11: environment per machine (Mac, lxplus host, lxplus el8 container for NtupleForge, lxplus el7 container for
  TTHHGenCategoryTools, KNU), an ordered table READY / WAITS, and the READY blocks: the Mac commit, the 2018 patch re-match against central
  v15 (V1, with expected numbers per sample), and the first KNU build of the 07-29 analyzer code with its unit tests and a read-only preflight.

### Found (recorded in docs/12 section 6 and in D.19 of 01_STATUS)
- 2018 standard NanoAODv15 has fewer events than MiniAOD for two ttbar samples: `TTbar_SemiLep` 460,133,000 vs 478,982,000 (the JMENano
  flavour has 478,982,000), `TTbb_Hadronic` 7,946,064 vs 8,049,064; the other four equal the extend rows. The 2017 statement "v15 covers
  100 % of MiniAOD" does not carry over to 2018. Sources: `script/das/das_ttHH_2018UL_v15_20260923_0853.log`, TTHHGenCategoryTools
  `docs/06_validation_results.md`.
- `tempTTHH/data/samples_2018UL.json` lacks three keys of the 2018UL v15 MC config (`TTZToQQ`, `TTTWminus`, `TTTWplus`) and its `das_path`
  fields are the v9 datasets.

### Sibling repository (TTHHGenCategoryTools, same day)
- `Validation/filelists/make_nano_filelists_das.sh` era `2018v15` and `Validation/data/das_nevents_2018v15.json`, so the 2018 patches can be
  re-matched against the v15 event set with the existing condor tools (their `03_changelog.md` 2026-09-27, `01_status.md` O8).

## [Unreleased], 2026-09-24 (2): output-volume measurement with event-skim options (the user's limit is 5-10 TB)

### Added
- `script/make_slim_branchlists.py` (2026-09-27, the user's question whether unused branches can go too): writes ten DRAFT slim lists
  `script/drafts/branch_hadronic_<era>_v15_<tier>_slim{A,B,C}.txt`, each the production list unchanged plus explicit `drop` lines
  (slimA: HF-only jet shapes, links into collections that are not stored, lepton/tau heads of the jet taggers, soft / low-pT / high-pT lepton
  IDs, beam-spot and GSF-mode internals, HZZ MVA, PV fit details, OtherPV, pileup-truth extras, GenVisTau, GenPart_iso, LHEPart; slimB: + tagger
  heads beyond B / CvB / CvL / QvG, lepton-MVA inputs and ID / energy internals, two jet muon-subtraction angles, `HLT_AK8PFJet*`; slimC, MC only:
  + `LHEPdfWeight`). A drop line is written only if it matches a kept branch in every inventory the list serves; branch counts 2024 MC
  703 -> 619 / 524 / 522, 2024 Data 646 -> 587 / 492 (2024G), 2018UL MC 717 -> 635 / 551 / 549, 2018 Data 664 -> 606 / 522 (2018D).
  `check_branchlist.py` gives the production verdict on all 17 inventories (all 61 / 62 requirements survive, every pattern matches; exit 3
  only for the documented v15 absence of `Jet_jetId` / `Jet_puId`). L1 was already out (`L1_*`, 412 branches) and HLT at 323 of 716.
- `script/size_options.py` also writes the compressed size of every kept branch per sample (whole input file, base copy, every skim copy) to
  `script/runlogs/size_options_branches.tsv` and prices the slim drafts from it (a draft edited later is re-priced by `--project-only`);
  the run ends with a TOTAL TB table, branch list x event selection.
- `script/size_options.py`: for 34 samples (every group of the four v15 hadronic configs that holds many events, each in its own era) it opens
  one DAS file via AAA, applies the config's branch_file the way NanoAODTools applies `outputbranchsel`, copies the first 10,000 events at
  LZMA:9 (what `run_postproc.py` writes), copies again only the events passing each of five skims (`6jcount`: at least six jets with |eta| < 2.5
  and no pT cut beyond what NanoAOD stored, the stored minimum is printed; `6j20` / `6j25` / `6j30`: six jets above 20 / 25 / 30 GeV;
  `6j20ht400`: `6j20` plus HT of the pT > 20 jets > 400), subtracts the empty-tree header, and projects the four
  configs with the DAS event counts of the 09-23 review tables. Also a whole-file estimate from the kept branches' compressed size (`meta`),
  calibration lines against the CRAB pilot (V44), a per-family breakdown for four samples, and a resumable TSV
  (`script/runlogs/size_options_meas.tsv`). All three skims are looser than the analyzer, which enforces njets >= 6 (pT > 30 after JES/JER,
  |eta| < 2.4), 6th jet > 40 and HT > 500 in every selecting mode (`tempTTHH/include/SelectionCuts.h`, `kCutSequence` steps 4, 5, 7).
  Why: with today's lists the production projects to 12.1-17.4 TB (V44). JEC margin (the user's question): six analyzer jets above 40 GeV
  after corrections means a stored-pT cut at 20 / 25 / 30 GeV loses an event only for a > 100 / 60 / 33 % upward move of such a jet; HT from
  pT > 20 jets holds every analyzer jet, so HT > 500 in the analyzer implies HT > 400 here unless the pT-weighted mean shift exceeds 25 %.
- `script/test_size_options_mock.py`: offline test with a fake dasgoclient and a mock ROOT against the real configs, review tables and branch
  lists (34 checks: mapping, DAS file choice, known sizes, TSV resume and signatures, failure handling and scratch cleanup, era scaling,
  per-branch table, slim pricing and re-pricing).

### Changed
- Workspace RUNBOOK 10: new [7c] (the measurement, the slim drafts), [7b] records the limit, [8] runs only after the skim decision is in the configs.
  STATUS row 18, `00_START_HERE.md`.

## [Unreleased], 2026-09-24: 2024 pilot outputs checked (V43), output size measured (V44); the pilot output check moved to KNU

### Changed
- Records: `09` 21 (pilot job-state snapshots, the full KNU check output, verdict, per-event sizes and the per-config volume table), ledger
  V43-V44 (BLUF: the CRAB-job check of the branch lists moved out of "open"), STATUS row 18, workspace RUNBOOK 10 ([7] result, [7b] estimate),
  `00_START_HERE.md`. Both pilots passed: 158/158 jobs done, event totals equal DAS (4,800,000 / 55,794,457), no unreadable file, schema as in the
  09-23 local checks. Sizes: MC `ZZ` 1.056 kB/event (no LHE branches, a lower bound for MC), Data `JetMET0` 2024H 0.780 kB/event; full production
  12.1-17.4 TB (MC upper bound from `09` 8b, 1.948 kB/event), replacing the 09-22 estimate of 20-26 TB.
- Workspace RUNBOOK 10 [7]: the output check now opens every pilot file under `/pnfs` at KNU. The 09-23 version copied job 1 with
  `crab getoutput`, which on lxplus left `results/` empty: CRABClient v3.260630 fetches every file with `gfal-copy` from
  `root://cms-xrd-global.cern.ch/<LFN>` (`Commands/getcommand.py` `insertXrootPfns`), so the RUNBOOK sentence "independent of AAA" was wrong
  (workspace `AI_LIMITS_AND_PROTOCOL.md` 5, failure 7).

## [Unreleased], 2026-09-23 (2): batch 6 folded in (first v15 production: 2024 + 2018UL scans, four configs, local checks, preflights; 2024 pilot submitted)

### Added
- `crabConfig/config_ttHH{2024,2018UL}_v15_had_{MC,Data}.yaml` (lxplus commit `3cb789b`; copies of the 09-23 drafts, `cmp` identical): 2024 MC 60 /
  Data 32 datasets from `script/das/das_ttHH_2024_v15_20260923_0851.log` (EXACT 64), 2018UL MC 42 / Data 8 from
  `script/das/das_ttHH_2018UL_v15_20260923_0853.log` (EXACT 41 + RELAXED 2; the five expected NOT_FOUND kept as a commented block, first real use of
  `--allow-notfound`). Together 13,486,536,452 events in 30,690 files, i.e. 30,690 jobs at units_per_job 1 (sum of the four review totals).
- `crabConfig/config_ttHH2024_v15_had_pilot{MC,Data}.yaml` (lxplus commit `72bd16f`): one dataset each (`ZZ`, `JetMET0_Run2024H-MINIv6NANOv15-v2`)
  with `_pilot` jobID / output_base; both submitted on 2026-09-23 (task names in `09` 21).

### Changed
- Records: `09` 21 (the batch), ledger V38-V42 (the two scans, the local NanoAODTools runs of the four v15 hadronic lists, six preflights, the
  wrapper mock test), STATUS row 18, workspace RUNBOOK 10 ([5] and [6] done; the [2] note on the 09-03 comparison made exact: 49 of the 50
  2018UL datasets match, `TTZToQQ` was not in the registry on 09-03), `00_START_HERE.md`. Ledger BLUF: the 2018A menu bracket (closed by
  V27-V28, V34) and the local branch-list run (V40) moved out of "open"; the CRAB-job check of the lists stays open until the pilot outputs.

## [Unreleased], 2026-09-23: `crab/submit_crab.py` reports failures (exit code, stale project dirs, `--kill` never submits); pilot submit steps split

### Fixed
- `crab/submit_crab.py` exited 0 whatever happened: every CRAB exception was caught and only logged. The 2024 pilot on 2026-09-23 ended
  `Submit Failed: Problems delegating My-proxy` with runlog `EXIT : 0`. Each dataset's outcome is now collected and printed as one
  `SUMMARY` block at the end (OK / WARN / FAILED / SKIPPED), and the exit code is 1 if anything FAILED or was SKIPPED. A submit counts as
  done only with `commandStatus: SUCCESS` and a `.requestcache` in the project dir. A proxy-type failure (`ProxyCreationException`, or
  "proxy" in the message) stops the loop: every later dataset would fail the same way and, for myproxy, ask for the GRID pass phrase again.
- Stale project dirs. CRABClient (v3.260630 source, the lxplus client) creates `<workArea>/crab_<name>` before the VOMS and myproxy steps
  and writes `.requestcache` only after the server returns a task name, so a submit that fails on the proxy leaves a dir without
  `.requestcache`. The default branch took any existing dir for a live task and auto-resubmitted it, which fails with `Cannot find
  .requestcache file` (and exited 0), so re-running the failed pilot would have done nothing. Such a dir is now reported as FAILED `stale`
  with an `rm -r` hint and CRAB is not called (`--resubmit` and `--report` the same; `--kill` warns). `--preflight` splits its old single
  WARN: stale dirs are a FAIL, live tasks a WARN saying that a plain submit auto-resubmits them (the old text "would clash/skip" was wrong).
- `--kill` ran the default submit/resubmit branch first: it resubmitted every existing task and SUBMITTED every dataset without a project
  dir, then killed them. The kill branch now comes before it and never submits.
- Smaller: `[<key>] Processing...` is flushed (under runlog.sh's pipe it printed after CRAB's own output); the resubmit hint points at
  `docs/05_troubleshooting.md` A10 (was `docs/troubleshooting.md`); an `HTTPException` without `.headers` no longer raises inside the handler.

### Added
- `script/test_submit_crab_mock.py`: offline test of the wrapper against a mock CRABAPI that follows the v3.260630 order (work area,
  then proxy, then `.requestcache`). No CRAB, proxy or network; refuses to run if a real CRABClient would be imported. 17 checks: new code
  17 PASS, the previous code 13 FAIL (proxy failure tried all datasets with rc 0; re-run over the stale dir hit `Cannot find .requestcache`
  three times with rc 0; `--kill` submitted the never-submitted dataset and then killed it). Record: `docs/05_troubleshooting.md` A22.

### Changed
- Workspace RUNBOOK 10 [4b] (new): the myproxy delegation is its own line (`crab createmyproxy --days 30`, pass phrase typed by hand), each
  submit is its own line, and "submitted" is checked by `.requestcache` instead of EXIT. The 09-23 retry with it submitted both pilot tasks
  (`260923_081917:junghyun_crab_ZZ`, `260923_082524:junghyun_crab_JetMET0_Run2024H_MINIv6NANOv15_v2`). [7] now keeps the full `--report`
  output under `script/runlogs/nocommit/` and commits only the table + SUMMARY (the wrapper lets CRAB's debug log through to the terminal,
  so submit output carries S3 signatures; the old [7] tee'd everything straight into `script/runlogs/`), and checks the pilot outputs by
  branch-name comparison with the 09-23 local checks. [8] first pulls this fix and runs the mock test, then stops at the first config whose
  submit exits non-zero. RUNBOOK 0: every crab command on its own line.

## [Unreleased], 2026-09-22 (3): `script/` and repo root tidied into directories; paths rewritten everywhere

### Changed
- `script/` kept flat 95 files; now 30 (23 tools, 2 registries, 3 manifests, `validate_v9.json`, this `README.md`). Records moved, not
  deleted: 26 DAS scan / probe / discover logs + the v9-vs-v15 compare table + `missing_in_v15_2017UL.tex` -> `script/das/`; 30
  full-campaign dumps (`das_inventory_*.tsv` + `.match.txt` + `.names.txt`) -> `script/das/inventory_dumps/`; 8 review tables and config
  drafts -> `script/drafts/`; the three Sherpa DAS listings from the repo root -> `script/das/sherpa/`; `validate_v9.json` from the root ->
  `script/`. Deleted (parked in the workspace `_to_delete/cleanup_20260922/` for the user to remove): the 3 `das_inventory_smoke_*`
  artifacts and the empty `smoke.log`. `script/README.md` documents the layout.
- Tool defaults follow the layout: `das_inventory.sh` writes to `script/das/inventory_dumps/`, `build_from_scan_log.py` to `script/drafts/`
  (was: next to the log); header examples of `das_scan.sh`, `das_discover_run3.sh`, `das_ul18_scan.sh`, `scan_diff_latex.py`,
  `build_ul18_from_log.py` (its provenance literal too) and the `.gitignore` comment updated. `build_ul18_from_log.py` already searched
  `script/` recursively, so it still finds the moved UL18 log.
- Every `script/<record>` path in `docs/` (incl. older CHANGELOG entries, rewritten mechanically so that each cited file can still be
  opened), `README.md` and the workspace documents now points at the new location; bare file names without a directory were left as they
  were. Workspace root: `RUNBOOK_UL18_*.md`, `WORKBOOK_local_test_partial_CRAB.md`, `HANDOFF_vs_LOCAL_diff_report.md`,
  `00_CONTEXT_ExpandedTtbarId_NtupleForge_Migration.md`, `patch_compare_2026-08-31.py` -> `archive_2026/`; three slide files ->
  `Materials/slides/`; four documents stay at the root (`00_START_HERE.md` 1 lists them).

## [Unreleased], 2026-09-22 (2): user decisions (drop TTWJetsToLNu; 2018UL v15 + 2024 first); builder --allow-notfound; submission batch prepared

### Added
- `script/build_from_scan_log.py --allow-notfound KEY,...`: emit a config while explicitly named keys are NOT_FOUND (written as a commented
  block); any other NOT_FOUND still refuses (exit 3); a stale allow list is reported. Needed because the 2018UL v15 campaign lacks the five
  samples under central request. Tested with a synthetic log (2 NOT_FOUND: refused without the flag, refused with a partial list, emitted with
  59 datasets + block when covered).
- `script/localcheck_summary.py`: one-line-per-file summary (Events, branches, HLT_ count, run/lumi/event, genWeight, genTtbarId,
  Runs.genEventSumw) of the 500-event local post-processing checks that precede CRAB (README step 2, lesson A14).
- Workspace RUNBOOK 10: the full submission batch for 2018UL v15 + 2024 (scan -> build -> crabConfig -> local checks -> preflight -> pilot ->
  full), with the `nocommit` / `preflight_*.log` / `campaign_*` handling spelled out.

### Changed
- `script/samples_registry_run3.txt`: `TTWJetsToLNu` row commented out (user 2026-09-22: dropped from Run 3). The 2024 had scan now selects
  60 MC + 4 DATA. D-2026-09-17-ttwlnu-pinned -> DEPRECATED; the PINNED mechanism stays.
- `build_from_scan_log.py`: `common.jobID` is now `campaign_<tag>` (CRAB workArea, gitignored by `campaign_*`, v9 convention) while
  `output_base` keeps the bare tag. The 2025 drafts in `script/` were regenerated from the same log (only these two lines changed).
- New decision D-2026-09-22-production-order (2018UL v15 + 2024 first; 2025 Data, 2016, 2017 later; analyzer generalisation later; the five
  absent 2018 samples come in a follow-up config). STATUS header, rows 4 / 18 / 18a / 19, item 22t, a "current position" block at the top of the
  v15 section; workspace `00_START_HERE.md` 4; `ttHH/03` 6 1.

## [Unreleased], 2026-09-22: batch 4 folded in (TTTW+/- VALID, 2025 rescan with PINNED); 2025 config drafts

### Added
- `script/drafts/config_das_ttHH_2025_v15_20260922_0755_{MC,Data}.yaml.draft`, `script/drafts/review_das_ttHH_2025_v15_20260922_0755.{md,tsv}` from the 09-22
  rescan `script/das/das_ttHH_2025_v15_20260922_0755.log` (EXACT 64 + PINNED 1, NOT_FOUND 0). The 2025 MC draft lists the same 61 datasets as the 2024
  MC draft (no 2025 MC campaign; Summer24 serves both), so only the Data draft is a submission candidate: 32 rows = JetMET0/1 + Muon0/1 x
  PromptReco B-G (C and F as `-v1` + `-v2`), 6,607,369,332 events, 18,494 files, job-count guard OK.

### Changed
- TTTW+/- NanoAODv15: all eight datasets read as VALID with `script/das_status.sh` (`run_probe_tttw_v15_status_20260922_055553.log` for six;
  `run_probe_tttw_v15_status_apv_20260922_061821.log` for the two UL16APV ones, which the first RUNBOOK 8 pattern missed because it lacked the
  `APV` token; AI slip, corrected as RUNBOOK 9 and run the same day). DAS side of D-2026-09-17-tttw-split closed; xsec remains. Registry comment,
  D-2026-09-17-tttw-split, STATUS row 5 / 18 / new 22s, `09` 20, ledger V35-V36 (ledger rows re-sorted ascending), `ttHH/03` 6 1, workspace
  `00_START_HERE.md`, RUNBOOK 8 done / 9 next.

## [Unreleased], 2026-09-19 (2): 2018 trigger periods from AN2019_094 cross-checked against the inventories; "A -> B boundary" corrected to run 317509

### Changed
- The 2018 six-jet menu switch is at run 317509, inside 2018B, per AN2019_094 (ttH(bb) full Run 2, FH channel, section 3.1.4 Tables 28-30; user's
  copy `Materials/TTHH/TTH_AN/AN2019_094_v20_ttHAnalysis.pdf`), consistent with the 09-18 schema probe (which could only bracket it between run
  316995 and the first 2018B file). Every AN 2018 path (periods A / B / C, the 4J3T and HT paths, the six control paths, `HLT_IsoMu27`) exists in
  the 2018 v15 and v9 inventories with the AN's period structure; UL18 MC carries the period-C set only, which is exactly the analyzer's
  `HLT_REQUIRED["2018"]`. The 2016 AN selection (Table 24) exists in all 9 UL16 v15 era files and both MC halves. Recorded in `08` 7.4 (two
  tables), STATUS 22n / rows 3 and 11, D-2026-09-18-2018A-trigger (options restated, AI recommends (a) + (c)), ledger V28 (wording) and new V34,
  `check_branchlist.py` `HLT_ERA_CONDITIONAL["2018"]` (+ `HLT_PFHT430_SixPFJet40_PFBTagCSV_1p5`, comment), `probe_hlt_path_by_run.py` docstring,
  workspace `00_START_HERE.md`.

## [Unreleased], 2026-09-19: batch 3 results folded in; first Run 3 (2024) config drafts, MC / Data split

### Added
- `script/das_status.sh`: DBS status (VALID / PRODUCTION / INVALID) + nevents + nfiles per dataset from the `-json` record, because
  `dataset status=*` lists every status without printing it and `summary` has no status column. Fake-DAS tested. First use: TTTW+/- v15
  (`..._v1-v1`; the UL17 v15 inventory has a `-v1` TTToHadronic that is INVALID with 0 events) -- workspace RUNBOOK 8.
- `script/build_from_scan_log.py --data-branch-file`: with it `--emit-config` writes `config_<stem>_MC.yaml.draft` (MC keys, `--branch-file`) and
  `config_<stem>_Data.yaml.draft` (Data keys, the Data list); `{tier}` in `--job-tag` becomes `MC` / `Data`. Reason: `crab/submit_crab.py` has one
  `common.branch_file` and the v15 MC and Data lists differ, so the CPV convention (two configs) is the only way to give each tier its list. The
  single-config path is unchanged apart from a header warning when it mixes MC and Data. Tested: 2024 log -> MC 61 / Data 32 keys, both YAML-parse,
  byte-identical on re-run.
- `script/drafts/config_das_ttHH_2024_v15_20260918_0803_{MC,Data}.yaml.draft`, `script/drafts/review_das_ttHH_2024_v15_20260918_0803.{md,tsv}`: the first Run 3
  config drafts (jobID `ttHH2024_v15_had_{MC,Data}_v1`; MC 61 datasets, 19,322 files, 13.95 TB; Data 32 = JetMET0/1 + Muon0/1 x 8 processing rows,
  7,811 files; job-count guard OK, largest 2,532 files). Drafts only: the user reviews and copies to `crabConfig/` (STATUS row 18).

### Changed
- 2018 trigger menu, measured (`script/probe_hlt_path_by_run.py`, batch 3): the 2p94 / 1p59 six-jet paths are absent from ALL sampled Run2018A v15
  files (9 files spanning runs 315257-316995) and present in all Run2018B files (6 files, 317080-319310); the v9 inventories agree. They entered
  the menu at the 2018A -> 2018B boundary, so every 2018A file lacks what `requireTriggerBranches2018_()` demands. `check_branchlist.py` 2018
  comment, `08` 7.4 / 7.5, STATUS 22n (three analyzer options), new `03_DECISIONS.md` D-2026-09-18-2018A-trigger (OPEN, user's call),
  `probe_hlt_path_by_run.py` docstring RESULT.
- v9 -> v15 per-era diff recorded (`08` 3.5): 16 v9 inventories (`inv_*_v9_*.tsv`) and 16 diffs (`diff_v9_v15_*.txt`). The physics-object part
  of the change is identical in every era (MC 126 removed / 348 added / 86 retyped incl. 2016 both halves and 2018; Data 120 / 309 / 58 in all 13
  eras); only HLT / L1 / DST / `Flag_*_pRECO` entries differ, and 2018A Data's 378 removed is the run coverage of the two sampled files.
  D-2026-09-17-ul18-v9-parked requirement satisfied.
- `script/samples_registry.txt` comments: TTTW+/- v15 event counts (8 datasets, 1,630,000-3,597,000; status still unread), BTagCSV UL16 v15 = 9
  datasets with the JetHT era structure. `03_DECISIONS.md` tttw-split / data-pd-2016 / ttwlnu-pinned (real-DAS confirmation, ledger V33) updated.
- `docs/09_v15_migration_log.md` 19 (batch 3 record incl. the failed first run and the 09-19 proxy-expired rerun), `10_validation_ledger.md`
  V27-V33, `01_STATUS.md` rows 3-6, 12, 16, new 18, items 22n / 22r, `ttHH/03_run3_plan.md` 6 1, `ttHH/04_mc_request_2026-09.md` 4; workspace
  `00_START_HERE.md` 4, RUNBOOK 7 done / 8 next (interactive `voms-proxy-init` alone in its block, same rule as `cmssw-el8`).

## [Unreleased], 2026-09-18: batch 3 first run failed without cmsenv; the two tools now say so

### Fixed
- `script/probe_hlt_path_by_run.py`: parses on the el8 system Python 3.6 (removed `from __future__ import annotations`; `capture_output`/`text`
  replaced by `PIPE`/`universal_newlines`), and the PyROOT check now runs before the first DAS query and names interpreter, version and
  `CMSSW_BASE`. Cause: the 2026-09-18 batch-3 run had no cmsenv inside `cmssw-el8` (runlog headers `CMSSW_BASE : <unset>`, `root : none`) and the
  script died with a SyntaxError at line 41 (`run_probe_2018A_sixjet_20260918_060358.log`, `..._2018B_..._060359.log`), hiding the real cause.
- `script/sweep_inventories.sh`: pre-flight `python3 -c "import ROOT"` (exit 4 with the cmsenv instructions) and the last stderr line of
  `dump_branch_inventory.py` printed on every FAIL. Same run: 16 x `FAIL ... could not read` with no visible reason
  (`run_sweep_v9_2016_2018_20260918_060400.log`). The DAS half worked: all 16 rows of `script/inventory_manifest_v9_2016_2018.txt` resolved to real
  LFNs, so the v9 patterns are verified as written; the inventories and diffs are still to be produced (workspace RUNBOOK 7, re-run version).
- Workspace (not in this repo): `RUNBOOK_lxplus_2026-09-16.md` 0 (rule: `cmssw-el8` alone, container blocks start with an `import ROOT` check) and
  7 (failure record, split blocks); `AI_LIMITS_AND_PROTOCOL.md` 5 failure 6.

## [Unreleased], 2026-09-17 (3): unified-forge plan, pinned dataset paths, TTWJetsToLNu proposal

### Added
- `docs/11_unified_forge_plan.md`: the user's direction (one tool for post-processing, MiniAOD dictionary, MiniAOD -> NanoAOD with user branches;
  absorb TTHHGenCategoryTools if it stays intuitive) turned into an inventory of existing pieces, a target layout, five rules, the two acceptance
  checks the user defined, phases 0 to 2 and risks. Recorded as D-2026-09-17-single-forge; glue = (A) `job_type: cmsrun`.
- Pinned dataset paths: a registry PRIMARY starting with `/` is queried as is. `das_scan.sh` (RESULT mode `PINNED`), `das_inventory.sh`
  (`PINNED|key|path|in_dump=N`, never NOT_FOUND), `build_from_scan_log.py` (flavour exclusion skipped for pinned keys, NOTE in the review table).
  Tested end to end with a fake `dasgoclient` (scan log -> review table); the real lxplus scan is the next check (RUNBOOK 7).

### Changed
- `script/samples_registry_run3.txt`: `TTWJetsToLNu` PRIMARY = the pinned `mg35x` dataset path with the DAS facts in the comment
  (D-2026-09-17-ttwlnu-pinned, PROPOSED by the AI; the user may revert to dropping ttW -> l nu from Run 3).
- `docs/01_STATUS.md` rows 4, 15, new 17, item 22q; `docs/README.md` index; `00_START_HERE.md` 4 (glue row); TTHHGenCategoryTools `04_decisions.md` D18.

## [Unreleased], 2026-09-17 (2): decision batch (tttW split, 2016 data PDs, v9 parked, column name, D-R3-9), builder 2016B fix, v9 manifest

Decisions are the user's (chat, 2026-09-17), recorded in `03_DECISIONS.md` D-2026-09-17-tttw-split / -data-pd-2016 / -ul18-v9-parked /
-expanded-id-column-name and the D-R3-9 status flip.

### Changed
- `script/samples_registry.txt`: `TTTWminus` / `TTTWplus` (`TTTWminus-DR1_TuneCP5_13TeV_amcatnlo-pythia8`, `TTTWplus-DR1_...`, `ttVV`, `had`, all four
  era-halves) added; `TTTW` moved to `ttVV_v9` / `alt` (v9 campaign only). `JetHT` ERAS now include both 2016 halves, `BTagCSV` too (UL16 v15 BTagCSV
  not yet looked up). MC rows 136 -> 138, `had` per era 45 -> 46.
- `script/build_from_scan_log.py`: in canonical (Run 2) mode a `<RunEra>-<proc>_vN-vM` variant becomes its own row `<PD>_<RunEra>_vN` instead of an
  alternate; without this the UL16 v15 `Run2016B-HIPM_UL2016_NanoAODv15_v2-v1` (ver2, 133.8M events) would have been dropped from a 2016 config.
  Tested on a synthetic 2016preVFP log built from the real dataset names (ledger V26).
- `docs/01_STATUS.md`: rows 4, 5, 6, 9, 10, 11, 15 updated, row 16 (v9 parked, per-era v9 inventories) added, 22p (decision batch and the
  enriched-glue explanation). `docs/ttHH/03_run3_plan.md` 6.3: 13.6 TeV ttbar split cross sections supplied by the user from a "Table 5" (source
  document not yet identified; not entered into any table until it is). `docs/ttHH/README.md` counts. `00_START_HERE.md` 4 rows.
- TTHHGenCategoryTools docs (04 D17 -> DECIDED with column name `genTtbarIdExpanded`, 11 open-decision paragraph, 03 changelog).

### Added
- `script/inventory_manifest_v9_2016_2018.txt`: 16 rows (UL16 v9 MC both halves, UL18 v9 MC, JetHT v9 per era 2016 B1/B2/C..H and 2018 A..D) so the
  v9 -> v15 diff exists per era, not only for 2017UL (requirement stated with D-2026-09-17-ul18-v9-parked). Run and diff commands: RUNBOOK 7.

### Not yet decided
- `TTWJetsToLNu` for Run 3 (standard Summer24 v15 has none; `mg35x` sub-campaign has 20,362,371 events with an mg35x MiniAODv6 parent): the user is
  re-checking DAS. Enriched production glue (`job_type: cmsrun` in NtupleForge vs `TtbarIdExtender/crab/`): explanation in STATUS 22p, recommendation
  there. Run 3 / 2016 trigger paths: no analysis decision yet; production is unaffected.

## [Unreleased], 2026-09-17: second recorded lxplus batch folded in (UL16 JetHT eras, 2016B ver1/ver2, 2018A run range)

Source: `script/runlogs/LEDGER.tsv` rows of 2026-09-17 (lxplus commit `15f377b`), read from the repository. `09_v15_migration_log.md` 18, `10_validation_ledger.md` V21 to V25.

### Changed
- `script/inventory_manifest_run3_2016.txt`: header now states what the two Run2016B v15 datasets are: `-v1` = ver1 (runs 272760-273017,
  9,726,665 events, 11 files), `_v2-v1` = ver2 (runs 273150-275376, 133,752,091 events, 145 files), disjoint, both needed.
- `branches/branch_hadronic_2016_v15_Data.txt`: header records the check against all nine UL16 era inventories (dead 0 everywhere); the AK8
  note corrected (HLT_AK8PFJet450/500 absent only in the B ver1 file; HLT_PFHT800 absent in H only). `branches/branch_CPV_Run2_Data_v15.txt`:
  nine-era result (exit 0) recorded.
- `script/check_branchlist.py`: the 2018 era-conditional comment carries the measured run range of the 2018A first file.
- `docs/ttHH/04_mc_request_2026-09.md` 4: the data-PD item now lists the nine verified UL16 JetHT v15 datasets with the B ver1/ver2 run ranges.
- `docs/08_branch_schema_migration.md` 7.1/7.3/7.4/7.5, `docs/01_STATUS.md` (table row 3 and 6, 22l-2, 22n), `docs/10_validation_ledger.md` (V21 to V25).

### Found
- The 2018A first file covers runs 316058-316719 (dataset 315257-316995): `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94` and
  `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` were not in the menu at least up to run 316719. Bracketing the first run with those paths is the
  next lxplus step (RUNBOOK 7).

## [Unreleased], 2026-09-16 (4): first recorded lxplus batch folded in: UL16 MiniAODv2 counts, Run 3 scans, 35-inventory sweep, 10 branch lists checked

Everything below reads from the run records the user produced on lxplus with `runlog.sh` (commit `a781cb3`: `script/runlogs/run_*.log`,
`LEDGER.tsv`, 12 rows, all EXIT 0 except the two matrix steps at 2 = PARTIAL, expected). Log of what ran: `09_v15_migration_log.md` 17.
Results and decisions: `08_branch_schema_migration.md` 7. Index: `10_validation_ledger.md` V11 to V20.

### Added
- `docs/10_validation_ledger.md`: the validation ledger (V01 to V20), one row per "we checked this" with date, scale, result and the evidence
  file inside the repository. Older rows were copied from 08/09; from now on `LEDGER.tsv` is the raw source and this table the human index.
- `branches/branch_hadronic_2016_v15_{MC,Data}.txt`, `branch_hadronic_2024_v15_{MC,Data}.txt`, `branch_hadronic_2025_v15_Data.txt`: derived from
  the checked 2018 v15 lists by substitution only (a scratch generator asserted every anchor); era-specific parts: L1 prefiring (kept for 2016,
  no keep for Run 3: 0 matches in all 21 Run 3 inventories), trigger notes with the measured b-tag paths, branch counts. All five: dead
  patterns 0 against every matching inventory (2024 Data 9, 2025 Data 9, Summer24 MC 3, UL16 MC 2, UL16 Data 2).
- `branches/branch_CPV_Run2_Data_v15.txt`: the v9 CPV Data list plus the v15 additions that exist in Data (`PFCand_*`, `nPFCand`,
  `FatJetPFCand_*`, `nFatJetPFCand`, `PVBS_*`, `nPVBS`, `nTauProd`; not `DST_*`, which has 0 matches in Run2017B). Checked against the eleven
  Run 2 v15 Data inventories; the only dead patterns are the deliberately shared 2016 path names (2 per 2017C..F / 2018 file, 6 in 2017B, 0 in 2016).
- `script/check_branchlist.py`: `--era 2016|2024|2025`. `HLT_REQUIRED` for these eras is EMPTY on purpose (no trigger decision yet; an empty list
  means "nothing checked", not "safe"); the candidate paths measured in the inventories are in `HLT_ERA_CONDITIONAL` and reported as information.
  `HLT_ERA_CONDITIONAL["2018"]` now lists the early-2018A DeepCSV paths (`..._2p2`, `..._1p5`). For Run 3 eras the `L1PreFiringWeight_Nom`
  requirement is dropped with a NOTE.
- `script/build_from_scan_log.py`: `--data-variants {auto,canonical,all}` (default auto = all for Run 3 eras): every DBS processing variant of a
  run era becomes its own row keyed `<PD>_<processed string>`; before, `Run2025C-PromptReco-v1` (155M events) and `Run2024I-MINIv6NANOv15_v2-v1`
  were demoted to alternates and would have been dropped from an emitted config. Data flavour re-productions (`BTVNano`, `JMENano`) are excluded
  and listed in the review table (before, the alphabetically first `UL2018_BTVNanoAODv15-v1` became the canonical `JetHT_Run2018A` for the
  2026-09-03 log because its META data_proc still carried `_MiniAODv2_`); the canonical match now also accepts the v15 string without that token.
  `DEFAULT_EXCLUDE` extended with the Run 3 flavour tokens. Tested on the 2024/2025 logs, the 2018UL 2026-09-03 log and a NOT_FOUND-free copy
  of the 2024 log with `--emit-config` (YAML parses). No output committed.

### Changed
- `branches/branch_hadronic_2017_v15_MC.txt`, `branch_hadronic_2018_v15_MC.txt`: `keep btagWeight_*` removed (no such branch in v15; it was one
  ROOT `SetBranchStatus` error per job since 2026-08-17). `branch_hadronic_2017_v15_Data.txt`: `keep HLT_QuadPFJet*` removed (0 matches in
  Run2017B, C, D, E in v9 and v15 alike; the family exists from 2017F on, and the analyzer's quad-jet path lives under `HLT_PFHT*`). All four
  headers: STATUS from UNVERIFIED to "checked 2026-09-16" with the exact re-check command; the 2018 MC prefiring VERIFY note resolved (11 branches present).
- `script/inventory_manifest_run3_2016.txt`: the two 2016 Data PATTERN rows replaced by the nine verified per-era rows from the discover log
  (B, B `_v2`, C, D, E, F with HIPM; F, G, H without). The two pattern-label inventories stay as the 2026-09-16 sweep record (cited by docs/08 7
  and the 2016 list headers); B-HIPM and F will appear twice in the presence matrix once the nine rows are swept, which is expected.
- `docs/ttHH/04_mc_request_2026-09.md` 1: 2016 columns now MiniAODv2 parent counts (preVFP `THW` 7.4M to 7.5M, preVFP total 27.1M to 27.2M; total
  162.6M, still "about 162M"); 4: the MiniAODv2 query item closed. `03_DECISIONS.md` D-2026-09-11-run2-scope-2016 (a) updated accordingly.
- `docs/ttHH/03_run3_plan.md` 6: items 1 (scan), 2 (a, b), 5 (`genTtbarId` exists in Summer24 v15), 6 (sweep) closed with pointers.
- `docs/08_branch_schema_migration.md`: new section 7 (sweep coverage, main-profile matrix, list checks, HLT tables, what is left); 3.4 UNVERIFIED note resolved.
- `docs/09_v15_migration_log.md`: section 17 (the batch, with the exact MiniAODv2 numbers and the Run 3 DATA findings). `docs/README.md`: index entry for 10.
- `docs/01_STATUS.md`: action table rewritten (14 rows), 22a/22b/24 closed, 22k numbers, new 22l (batch record), 22m (list findings), 22n (2018A early menu).

### Found, not yet fixed (tracked in 01_STATUS 22m, 22n)
- `Flag_METFilters` (combined flag) does not exist in Summer24 v15 MC nor in 2025 PromptReco Data (it does in all Run 2 v15 and 2024 Data).
- First file of `/JetHT/Run2018A-UL2018_NanoAODv15-v2` lacks `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94` and
  `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` (has the 2017-threshold DeepCSV paths instead); one-file measurement, run range unverified.
- `branch_CPV_Run2_MC_v15.txt` has `drop Scouting*` dead on UL16 v15 MC; `branch_prescan_slim_2017.txt` has three Run B calo paths dead on UL17 MC (v9 too).
- RUNBOOK expectation "MC 45" for the Run 3 scan was wrong (Run 2 count copied); the Run 3 registry selects 61 `had` MC rows.

## [Unreleased] — 2026-09-16 (3): `script/runlog.sh` — every lxplus step leaves a record in the repo

### Added
- `script/runlog.sh <step> -- <command>` — wraps one step: header (step, start UTC, host, cwd, git HEAD + modified-tracked count,
  exact command via `printf %q`, `CMSSW_BASE`, ROOT / dasgoclient versions, proxy time left), body (stdout+stderr, tee'd to the
  terminal), footer (end UTC, wall seconds, **EXIT**, every file under `script/` and `branches/` modified during the run with sizes).
  Appends one line to `script/runlogs/LEDGER.tsv`. Propagates the command's exit code. Commands mentioning `crab` are routed to
  `script/runlogs/nocommit/` (gitignored) — credential rule D-2026-08-17-no-logs-in-git. Self-tested in the dev container:
  exit-code propagation (0 / 4), output detection, nocommit routing, argument validation (exit 2). ASCII-only.
- `script/runlogs/README.md` — what the records contain and how to read them (EXIT, outputs, git_head, reproducing from `cmd`).
- `.gitignore`: `script/runlogs/nocommit/`.

### Changed
- `../../RUNBOOK_lxplus_2026-09-16.md`: every command wrapped in `runlog.sh`; a 30 s self-test gates the rest; commit step adds
  `script/runlogs/`. Reason (user, 2026-09-16): a run must leave enough of a record that both the person and the AI can see that
  the work actually happened and how it ended, not just the result files.

## [Unreleased] — 2026-09-16 (2): lxplus runbook + sweep manifest; stale CPV status corrected

### Added
- `script/inventory_manifest_run3_2016.txt` — sweep manifest for what the 2017UL manifest never covered: Summer24 MC (3 primaries),
  2024 Data per era (JetMET0 C–I, I_v2, Muon0 C), 2025 Data per era (JetMET0 B–G incl. C/F v2, Muon0 C), UL16 v15 MC both halves,
  UL17 B–F and UL18 A–D v15 **Data** (only v9 Data was swept so far), UL18 v15 MC. Every name has a recorded provenance
  (inventory TSV, discover HIT lines, docs/08 Step 1b); the two UL16 v15 Data rows are explicitly patterns pending a DAS look.
- `../../RUNBOOK_lxplus_2026-09-16.md` (workspace top level) — the lxplus session for the user: UL16 MiniAODv2 inventory,
  `das_scan.sh --era 2024|2025 --workstream had`, UL16 JetHT v15 discovery, the sweep, what to commit, and what the AI does with each result.

### Fixed
- `01_STATUS.md` CPV section still said **"BLOCKED on lxplus re-validation (-N 10 + validate_topcpvcat.py)"** from 2026-07-02,
  although Gate 4 passed on 2026-08-25 and the v9↔v15 comparison on 2026-08-30 (`09_v15_migration_log.md` §2, §6). Struck
  through with the resolution and the actual remaining campaign-scale steps. The 2026-09-16 position check in
  `00_START_HERE.md` §4 ① had copied the stale sentence; corrected there too, and recorded as failure case 4 in
  `../../AI_LIMITS_AND_PROTOCOL.md` §5.

## [Unreleased] — 2026-09-16: session-memory limits in the working agreement; open items consolidated

### Fixed
- `01_STATUS.md` group E carried **two items numbered 22h** (the 2025-campaign check of 09-11 and the full-Run-2
  scope decision of the same night), the 22x items were in insertion order rather than alphabetical, and item 22
  still quoted the pre-09-11 Run 3 registry counts (MC 78 / had 59) that item 22h contradicts. The second 22h is
  now **22k**, the block is ordered a→k, and item 22 points at the current counts.

### Added
- `01_STATUS.md` group E now opens with a **"다음 행동" table** (12 rows: what to do next, who does it and where,
  and which item it comes from). The pending actions were previously buried inside prose in 22g and 22k.
- `../../AI_LIMITS_AND_PROTOCOL.md` (workspace top level) — what an AI actually knows versus what must be
  supplied, how session memory and compaction really behave (with the 1.91M-character corpus measurement),
  which failure modes the training objective produces, the six observed cases from the 2026-09-11~14 session
  (3 failures, 3 successes), and a 14-item working protocol.

### Changed
- `00_PROMPT.md` §3: session memory added as an environment limit alongside "no ROOT, no CRABClient".
  Three rules: no bulk-loading of the docs (governance set at session start, topic docs read immediately
  before use), state what you read, and never quote a number from memory — re-open the file or re-run the
  query at the point of citation and mark unverified claims as inference. Header `Updated` 2026-07-01 → 2026-09-16.

### Verified (no change needed)
- `das_scan.sh` already handles the v15 data processing string: `scan_data()` strips `_MiniAODv2_` in a relaxed
  fallback, so extending the data PDs to 2016 is a registry-row job only, not a script fix.

### Added
- `../../AI_LIMITS_AND_PROTOCOL.md` (workspace top level) — what an AI actually knows versus what must be
  supplied, how session memory and compaction really behave (with the 1.91M-character corpus measurement),
  which failure modes the training objective produces, the six observed cases from the 2026-09-11~14 session
  (3 failures, 3 successes), and a 14-item working protocol.

### Changed
- `00_PROMPT.md` §3: session memory added as an environment limit alongside "no ROOT, no CRABClient".
  Three rules: no bulk-loading of the docs (governance set at session start, topic docs read immediately
  before use), state what you read, and never quote a number from memory — re-open the file or re-run the
  query at the point of citation and mark unverified claims as inference. Header `Updated` 2026-07-01 → 2026-09-16.

## [Unreleased] — 2026-09-14: MC request recorded; two unsourced claims corrected

### Added
- `docs/ttHH/04_mc_request_2026-09.md` — what was requested from the Hbb MC contact and why, what was **not**
  requested and why, what falls to us if it is approved, and the verbatim e-mail body. Indexed in `docs/ttHH/README.md`.

### Changed
- `03_DECISIONS.md` D-2026-09-11-ttz-hadronic-from-ttzqq: the sentence "a background that is roughly half of ttH(bb)
  in rate" was written from general knowledge, not from any project document. Replaced with the PDG branching ratio
  (attributed as such) plus an explicit OPEN on whether the statistics suffice, and linked to the existing open item
  on the ttZ cross-section definition (861 fb vs 841 fb).
- `03_DECISIONS.md` D-2026-09-11-run2-scope-2016: added the analyzer-side cost of 2016 (no `samples_2016*.json`,
  no 2016 luminosity reference, trigger / SF / JEC work), which was not stated when the decision was taken.
- `01_STATUS.md`: items 22i (request record) and 22j (2016 analyzer-side cost, unscoped).

## [Unreleased] — 2026-09-11 (night): Run 2 request = all four era-halves; QCD-HT primary fixed for v15

### Added
- `script/das/inventory_dumps/das_inventory_ul16{pre,post}_{v15,v9}_20260911_*.tsv` (+ `.names.txt`, `.match.txt`) — UL16 preVFP/postVFP,
  NanoAODv15 and v9. v15: 109 EXACT / 27 NOT_FOUND each; v9: 129 / 7. The four Run 2 v15 NOT_FOUND key sets
  (16pre, 16post, UL17, UL18) are **identical**.

### Changed
- `samples_registry.txt`: all 62 ttHH rows now read `2016postVFPUL,2016preVFPUL,2017UL,2018UL` (45 `had` MC rows per era,
  no duplicate keys). QCD-HT PRIMARY `QCD_HT<bin>_TuneCP5_13TeV-madgraphMLM-pythia8` → `QCD_HT<bin>_TuneCP5_PSWeights_13TeV-madgraph-pythia8`
  (the v9 name exists in no v15 campaign; the PSWeights name is EXACT in all four). KEYs unchanged.
  `TTTW` left as is with a comment: v15 splits it by charge (`TTTWminus/plus-DR1`), which needs two KEYs and two xsec entries (OPEN).
- Docs: `03_DECISIONS.md` **D-2026-09-11-run2-scope-2016** (DECIDED, user); `09_v15_migration_log.md` §16;
  `ttHH/03_run3_plan.md` §4.7 conclusion ③; `01_STATUS.md` 22h.
- Request to the conveners is now **five samples × four era-halves = 28 datasets, ≈162M events** (was 14 / ≈108M).

## [Unreleased] — 2026-09-11 (evening, 2): Run 2 ttZ(had) from `TTZToQQ`; request list 6 → 5

### Changed
- `samples_registry.txt`: `TTZToQQ` (`TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8`, UL17 13.98M / UL18 19.82M, v15 VALID) is
  now the ttHH `had` ttZ(hadronic Z) sample — same KEY as the Run 3 registry; `TTZToBB` demoted to `ttHH,alt`
  (v9-only, no NanoAODv15 request; never combined with `TTZToQQ`). `TTZToQQ_v15alt` row removed (merged into `TTZToQQ`).
  Counts unchanged (had 45 / lep 16 / alt 1).
- Docs: `03_DECISIONS.md` **D-2026-09-11-ttz-hadronic-from-ttzqq** (DECIDED, user); `ttHH/03_run3_plan.md` §4.7 table row
  and conclusion ③ (Run 2 request = five samples: `TTHHto4b`, `TT4b`, `TTZHTo4b`, `TTZZTo4b`, `tHW`; 14 datasets ≈108M);
  `01_STATUS.md` 22g(a) DECIDED; `09_v15_migration_log.md` §15 (ttZ treatment change, enriched fallback list 6 → 5).

## [Unreleased] — 2026-09-11 (evening): ttH(bb) split samples, 2025 campaign check

### Changed
- `samples_registry_run3.txt`: ttH(bb) now comes from the three top-decay-split Summer24 samples
  `ttHTobb_had / _semilep / _dilep` (`TTH-Hto2B-TTto4Q / -TTtoLNu2Q / -TTto2L2Nu_Par-M-125_…powheg`,
  all VALID, 29.62M / 29.22M / 29.57M events; `--grep tth-hto2b-tt` inventory 08:57 CEST); the
  top-decay-inclusive `ttHTobb` (`TTH-Hto2B_Par-M-125`, 2.44M) is demoted to workstream `alt`
  (key kept; never to be added to the split set). Counts: MC 85 = had 61 + lep 19 + alt 5, DATA 11.
- Docs: `03_run3_plan.md` §4.7 (ttH split table row, 2025-campaign check, conclusions ⑤), §5/§6 counts,
  header/BLUF; `01_STATUS.md` 22g(b) DONE, 22h; `03_DECISIONS.md` **D-R3-9** (proposed — confirm).

### Notes
- `dasgoclient -query "dataset status=* dataset=/TTto4Q_TuneCP5_13p6TeV_powheg-pythia8/RunIII2025*/NANOAODSIM"`
  returns nothing: no 2025 MC campaign on DAS (PPD statement confirmed); `--era 2025` keeps scanning Summer24.
- New inventory output on lxplus, to be committed: `script/das/inventory_dumps/das_inventory_tth_split_20260911_0857.tsv`
  (+ `.names.txt`, `.match.txt`; 16,658 datasets listed).

## [Unreleased] — 2026-09-11 (later): inventory results, `alt` registry rows

### Added
- **Inventory logs** `script/das/inventory_dumps/das_inventory_{summer24_v15_20260911_0427,ul17_v15_20260911_0433,ul18_v15_20260911_0435}.tsv`
  (+ `.names.txt`, `.match.txt`), run on lxplus. Result: `CASE_ONLY` 0 in all three campaigns —
  the 2026-09-07 conclusions stand; `TT4B` was the only case miss. Numbers in `03_run3_plan.md` §4.7.
- **Registry `alt` rows** (WORKSTREAM `ttHH,alt`, excluded by `--workstream had`):
  Run 3 `TTbar_Hadronic_FxFx2J` (`TTto4Q-2Jets_…amcatnloFXFX`, 395M VALID), `TTbar_Hadronic_MLM3J`
  (`TTto4Q-3Jets_…madgraphMLM`, 202M), `TTbar_Hadronic_Sherpa` (`TTto4Q-4Jets-1NLO3LO_TuneSherpaDef`,
  PRODUCTION 100.8M), `TTZToQQ_MLM` (`TTZ-ZtoQQ-1J_…madgraphMLM`, 9.45M); Run 2 `TTZToQQ_v15alt`
  (`TTZToQQ_TuneCP5_13TeV-amcatnlo-pythia8`, UL17 13.98M / UL18 19.82M — possible substitute for the
  absent `TTZToBB`, decision open). Commented candidate `ttHTobb_had`
  (`TTH-Hto2B-TTto4Q_Par-M-125_…`, status not yet queried).
- `das_inventory.sh`: hint matching normalised (alnum on both sides).

### Notes
- Run 2 v15 also carries tiny inclusive `TTHH_`, `TTZH_`, `TTZZ_` samples (0.3–0.5M, 1–2 files, Oct 2025):
  test-size, not substitutes. CPV workstream: 13 of its Run 2 samples have no v15 (list in §4.7).

## [Unreleased] — 2026-09-11: `das_inventory.sh` (campaign dump + case-insensitive matching + status/events TSV)

### Added
- **`script/das_inventory.sh`** — lists every dataset of a campaign with
  `status=*` (`/*/<campaign>*/<tier>`, first-letter fallback), matches the
  registry PRIMARYs and free tokens **locally and case-insensitively**
  (`EXACT` / `CASE_ONLY` / `NOT_FOUND` / `GREP`), and records per dataset
  status, nevents, nfiles, size, creation date in a TSV (details for matching
  datasets by default; `--details all|none`). Tested end-to-end against a
  `dasgoclient` stub (not yet against DAS). Procedure in `03_run3_plan.md` §4.3 (4).
- `03_run3_plan.md` §4.6: prefix audit (`TTtoL*` added to `das_discover_run3.sh`
  for the charge-split Sherpa names), the tt+jets multileg alternatives already
  in Summer24 v15 (`TTto4Q-2Jets_…amcatnloFXFX` NLO 0,1,2 jets; `TTto4Q-3Jets_…madgraphMLM`),
  and the powheg `TTto4Q` systematic variants (Hdamp, MT, CR, tune, ERD, BBDPS).

## [Unreleased] — 2026-09-10: `TT4b` found in Summer24 v15 (`TT4B`), discover script case fix, BTV UParTAK4 note

### Fixed
- **`script/samples_registry_run3.txt`** — `TT4b` row added:
  `TT4B_TuneCP5_13p6TeV_madgraph-pythia8` (Summer24 NanoAODv15, 9,898,300 events, VALID).
  The 2026-09-07 discovery reported it absent because `das_discover_run3.sh` queried
  `TT4b*`/`TTbbbb*` and DAS wildcards are case-sensitive; the Run 3 naming spells
  `4B`/`BB`. Found through the SL-channel team's dataset list (2026-09-10).
  Registry now MC 78 (`had` 59 / `lep` 19), DATA 11.
- **`script/das_discover_run3.sh`** — `TT4B*` and `TTBBBB*` added to the
  `ttVV_4top` family; header comment on case sensitivity.
- **`docs/ttHH/03_run3_plan.md`** — BLUF, §4.1, §4.4, §4.5 and §6 item 4 corrected
  (`TT4b` decision closed: use central `TT4B`); new §4.6 with the Summer24 event
  counts read from DAS (`TTtoLNu2Q` 484.5M, `TTBBtoLNu2Q` 22.5M, `TTH-Hto2B` 2.44M,
  `TTHH`/`TTZH`/`TTZZ`/`TT4B` ≈10M each) and the lesson on case-sensitive patterns.

### Added
- **BTV recommendation recorded** (03_run3_plan §2 row 9): for the re-NanoAODv15
  campaigns (Run 2, 2022/2023) the 2024 UParTv2/UParTAK4 working points apply to
  `Jet_btagUParTAK4B`; RobustParT WPs/SFs must not be reused (CMS-talk
  "UParTAK4 working points for 2022/2023 NanoAODv15", 2026-09-09).
- **`01_STATUS.md` E 22d/22e** — MC-request status (deck `ttHH_latex/GenRequest_Sep2026`,
  group feedback of 2026-09-10) and the BTV note.

## [Unreleased] — 2026-09-07: Run 3 kickoff — plan doc, era table, family discovery script, `had`/`lep` registry tags

Parallel to the enriched-NanoAOD validation batch (TTHHGenCategoryTools D17).
No physics logic changed; nothing was submitted or produced.

### Added
- **`docs/ttHH/03_run3_plan.md`** — Run 3 (2022, 2022EE, 2023, 2023BPix, 2024;
  2025 to investigate) on NanoAODv15: scope decisions D-R3-1…6, a 15-item
  event-level checklist of what Run 3 requires beyond Run 2 (jet veto maps incl.
  the 2023BPix `jetvetomap_bpix`, the Run 3 MET-filter list with
  `Flag_BadPFMuonDzFilter`/`Flag_hfNoisyHitsFilter`, `Jet_jetId` recomputation,
  PUPPI jets/MET, era JEC/JER and pileup keys, PNet/UParT taggers, FH trigger
  paths; prefiring and HEM switched OFF), each row marked measured / from
  memory / rule — **the "from memory" rows must be checked against the twiki
  before any value enters code** (the pages could not be opened in this
  session). Dataset section: Run 2 → Run 3 naming table (patterns, not names),
  campaign-string templates (all UNVERIFIED until `--probe`), the discovery
  procedure, and the `had`/`lep` production order.
- **`script/das_discover_run3.sh`** — one DAS wildcard per physics *family* per
  era (`TTto4Q_*`, `QCD-4Jets_HT-*`, `TTHH*`, `Wto2Q*`, `DYto2L*`, …; PDs
  `JetMET[0|1]`, `Muon[0|1]`, `EGamma[0|1]`, `BTagMu`, `JetHT`) → `HIT|MC|<family>|<had|lep>|<dataset>`,
  `HIT|DATA|…`, `NONE|…`, `CAMP|DATA|<pd>|<campaign>`. The only permitted source
  for primary names in `samples_registry_run3.txt` (same rule as `das_scan.sh`:
  never guess a dataset name). Mock-tested only; not yet run against DAS.

### Changed
- **`script/das_scan.sh`** — era table gains six Run 3 rows (`2022 2022EE 2023
  2023BPix 2024 2025`; MC prefixes `Run3Summer22…`, `RunIII2024Summer24…`; data
  procs `NanoAODv15` / `MINIv6NANOv15` / `PromptReco`) flagged `RUN3=1`, which
  switches `--probe` to 13.6 TeV probe primaries (`TTto4Q_…`, `TTtoLNu2Q_…`;
  PDs `JetMET`, `JetMET0`, `Muon`, `Muon0`). All six rows are UNVERIFIED
  templates until the probe has been run. Header documents the `had`/`lep`
  tags.
- **`script/samples_registry.txt`** — the 64 ttHH rows carry a use tag in the
  WORKSTREAM column: `ttHH,had` (47: signal, tt̄, tt̄bb̄, QCD, tt̄H, tH, tt̄V, tt̄VV,
  single top, diboson, W/Z→qq̄, JetHT, BTagCSV), `ttHH,lep` (16: `WJetsToLNu_HT*`,
  `DYJetsToLL_M50_HT*`), `ttHH,CPV,had,lep` (SingleMuon). Existing readers use
  columns 1, 2, 4 only; `--workstream had` selects the hadronic set. Row count,
  keys and primaries unchanged (172 rows).
- `docs/01_STATUS.md` (block E, items 21–25), `docs/README.md`,
  `docs/ttHH/README.md` — index entries.

### Decided
- `D-2026-09-07-run3-scope` in `03_DECISIONS.md` (pointer to D-R3-1…6).

### Same day, second pass — facts from the PdmVRun3Analysis twiki (r223) and the PPD Run3 2025 table
- `03_run3_plan.md` §1/§2/§4: **2025 is the primary target** (data = T0 prompt MINIAODv6/NANOv15,
  GT `150X_dataRun3_Prompt_v1`; **no 2025 MC campaign — PPD says use Summer24**, GT
  `150X_mcRun3_2024_realistic_v2`). Golden JSONs 2022–2025, era run boundaries, per-era
  golden luminosities (2024 109.95, 2025 110.63 prelim), Run 3 EGM ID names and the EE+ leak
  veto, the JME "all analyses use jetvetomap" policy and the 2022 prompt HCAL-barrel issue
  (use ReReco for 2022 A–E) moved from "from memory" to measured. 2024 campaign strings
  confirmed from a reference analysis list (`RunIII2024Summer24NanoAODv15-…_v2-vN`,
  `Run2024C..I-MINIv6NANOv15-v1|v2`); Summer24 uses the `Par-`/`Bin-`/`Fil-` naming.
- `das_scan.sh`: the 2025 row scans Summer24 MC (a NOTE line says so); sources in comments.
- `das_discover_run3.sh`: 2025 → Summer24 MC; family wildcards widened to prefixes
  (`QCD-4Jets*`, `TTH*`, `DYto2L*`, `WW*` …) so both the Summer22/23 and the Summer24
  spellings are caught.

### Same day, third pass — probe + discovery run on lxplus; Run 3 registry written
- Logs committed: `script/das/das_probe_{2022,2022EE,2023,2023BPix,2024,2025}_v15.log`,
  `script/das_discover_<era>_v15_20260907_*.log`. All six era rows of `das_scan.sh` are
  now DAS-verified (MC campaign + GT, data processing strings; `03_run3_plan.md` §4.2).
- **Findings** (§4.5): Summer24 NanoAODv15 carries the whole hadronic set centrally —
  `TTHH-HHto4B` (signal), `TTZH-ZHto4B`, `TTZZ-ZZto4B`, `THW/THQ`, `TTBBto*`, `QCD-4Jets_Bin-HT-*`,
  `Wto2Q/Zto2Q`, single top, ttVV — only `TT4b` is absent; no enriched-NanoAOD production is needed
  for Run 3. The 2022/2022EE/2023/2023BPix v15 re-nano is **partial** (the same 70 standard
  datasets per era: ttbar, ttV, single top (t/s/tW), VV, QCD-PT, DY, W→ℓν) → D-R3-7 (PROPOSED): first Run 3 round =
  2024 + 2025 with Summer24 MC. Data: 2025 `PromptReco-v1` for B–G plus `-v2` for C and F (disjoint
  runs, all kept); 2024 `MINIv6NANOv15` C–I plus `Run2024I-MINIv6NANOv15_v2`; 2023 `NanoAODv15{,_v2,_v3,_v4}`;
  2022 `NanoAODv15-v1` C–G.
- **New `script/samples_registry_run3.txt`** — 77 MC rows (58 `had`, 19 `lep`) + 11 DATA rows, every
  PRIMARY copied from a `HIT|` line. Run 2 KEYs kept where the sample is the same; new KEYs where
  Run 3 splits/merges (`TTZToQQ`, `TTTWminus/plus`, `ST_t_top_had/lep`, `ST_tW_top_had/semilep/dilep`,
  `ST_s_*`, `QCD_HT200to400…`, `WJetsToLNu_HT*_MLNu*`, `DYJetsToLL_M50to120_HT*`). `TTWJetsToLNu` is
  listed but will be NOT_FOUND (v15 has `TTLNu-1Jets` only as `mg35x_`); `BTagMu` commented out.
- `das_scan.sh`: Run 3 + v15 MC queries are **GT-anchored** (`/<primary>/<campaign>-<MC_GT_V15>*/NANOAODSIM`)
  so the flavour re-productions sharing the prefix (JMENanoV15_, BTVNanoV15_, FS_, NoPU_, FlatPU_,
  EpsilonPU_, EGMNanoV15_, MUOPOGNano_, mg35x_) are not scanned; `_pilot` datasets dropped; Run 3 eras
  auto-select `samples_registry_run3.txt` when `--registry` is not given; `META|` gains `mc_gt=`.
- Known follow-up: `build_from_scan_log.py` must keep every prompt `-vN` / `_vN` data variant for Run 3
  (today it keeps one canonical per (PD, era)); flavour EXCLUDE list to extend (`01_STATUS.md` 22b).

---

## [Unreleased] — 2026-08-30: v9 ↔ v15 event-matched 동일성 확인 (불일치 0), A18, 검증 전용 branch 목록

### Result — CPV gen categorizer 의 v9→v15 마이그레이션은 물리 결과를 바꾸지 않습니다

`TTToSemiLeptonic` UL17. lumi 로 짝지은 v9/v15 파일 쌍에서 **143,000 개의 같은
event** 를 뽑아 `script/compare_v9_v15.py` 로 `(run, luminosityBlock, event)` join 비교:

| 범위 | 비교 횟수 | 불일치 |
|---|---|---|
| `--prefix TopCPVCat_` (46 branch) | 6,578,000 | **0** |
| `--prefix ""` (61 branch) | 8,723,000 | **0** |
| `--ftol 0` (허용오차 없음, 46 branch) | 6,578,000 | **0** |

`common=143000`, `v9-only=0`, `v15-only=0`. Gate 4 (standalone C++ ≡ 모듈, v9,
2026-08-25) 와 합쳐 **v15 위의 모듈이 기준 구현체에 대해 전이적으로 검증**됐습니다 —
표준 C++ 도구가 `GenPart_statusFlags` 를 `Int_t` 로 읽어 v15 를 직접 비교할 수 없는
제약을 우회한 것입니다. `Int_t→UShort_t` / `Int_t→Short_t` 타입 변경이 물리에 영향이
없다는 것이 추론이 아니라 872 만 회 비교로 실증됐습니다. 전문: 08 6절.

**음성 대조군.** `--prefix ""` 실행이 `only in v15: GenJet_nBHadrons,
GenJet_nCHadrons` 를 보고했습니다 — 3.4절 인벤토리 diff 가 예측한 바로 그 두 개.
비교기가 차이를 실제로 감지한다는 확인이자, 독립적인 두 측정의 교차 검증입니다.

**파일 페어링이 이 비교의 어려운 부분이었습니다.** parent MiniAODv2 가 같아 event
집합은 동일한데 NanoAOD job splitting 이 버전마다 달라 파일 경계가 전혀 대응하지
않습니다 (각 데이터셋 첫 파일끼리 event 겹침 0). v9 파일의 lumi 집합 대 v15 의 398 개
파일을 겹침 순으로 랭킹해 143 lumi 를 공유하는 파일을 찾았습니다. 페어링은 특정 v9
파일에 묶여 있으므로 `setup_v9v15_validation.sh` 가 LFN 을 고정합니다.

### Added

- **`script/compare_v9_v15.py`** — 두 모듈 출력의 event-matched 비교기. 겹침이 비면
  "불일치 0" 이 아니라 **exit 3 으로 실패**합니다 (이 비교에서 깨지기 쉬운 것은 물리가
  아니라 페어링입니다). exit 1 불일치 / 2 공통 branch 없음 / 4 파일 읽기 실패.
- **`script/setup_v9v15_validation.sh`** — `source` 전용 원스톱 세션 준비: cmsenv,
  git pull, proxy, 모든 환경변수, 고정 LFN 입력 2 개, 공유 lumi cut 재생성, 스크래치
  디렉토리 이동. `nf_status` / `nf_pull` / `nf_smoke` / `nf_v9` / `nf_v15` /
  `nf_compare` 명령을 정의합니다.
- **`branches/branch_CPV_validation.txt`** — 검증 전용 최소 출력 목록. 프로덕션 목록은
  2.01 kB/event (입력 NanoAOD 2.06 kB/event 와 사실상 동일 — 버리는 collection 들이
  작고 압축이 잘 되어 이득이 없음) 였고, 143k event 실행 하나가 AFS home 을 99 % 까지
  채웠습니다. 이 목록은 **0.315 kB/event (6.4 배 감소)**. v9 와 v15 에서 이름이 바이트
  단위로 같아 **양쪽에 같은 파일**을 쓰므로 목록이 비교의 교란 요인이 되지 않습니다.
- **`script/run_postproc.py --cut`** — `PostProcessor(cut=...)` 직행. default `None`
  이라 기존 동작 불변. 두 버전을 공유 lumi 집합으로 제한해 각 ~8 분에 끝내기 위한 것
  (전체 파일 두 개는 ~3 h). 출력 event 집합을 바꾸므로 **검증 전용**이며 켜지면
  `PRESELECTION CUT ACTIVE -- VALIDATION MODE` 배너가 찍힙니다.

### Fixed

- **`05_troubleshooting.md` A18 — 앞에 `drop *` 가 오는 branch 목록은 모듈 자신의
  branch 까지 조용히 버립니다.** 스모크 테스트에서 출력이 15 branch / `TopCPVCat_*`
  **0 개** 로 나왔는데 모듈은 `processed=2000 signal=2000` 을 보고했습니다 — 완벽히
  돌고 결과를 전부 버린 것입니다. 에러도 경고도 없습니다. `branch_CPV_validation.txt`
  초안에 "모듈 branch 는 outputbranchsel 을 피해간다" 고 써 두었던 주장이 반증됐고,
  `keep TopCPVCat_*` 를 추가했습니다. 프로덕션 목록들은 leading `drop *` 가 없어
  이 함정에 걸리지 않았습니다.
- **`setup_v9v15_validation.sh`** — untracked 파일이 `git pull` 을 막던 문제
  (`--untracked-files=no`), `$WORK` 에서 bare `git pull` 이 실패하는 문제 (`nf_pull`),
  `INV` 상대경로.

### Measured

- 실효 처리율 **313 Hz (v9) / 288 Hz (v15)**, 각 ~8 분 / 143k event.
  ⚠ 로그의 `Rate = 1868.7 Hz` 는 분모가 *입력* entry 수라 틀립니다.
- `run_postproc.py` 는 `OUTPUT_DIR="."` (CRAB 요구) 이므로 중간 `_Skim.root` 가 항상
  cwd 에 떨어집니다. repo 에서 돌리면 AFS home (10 GB) 이 찹니다 — 스크래치에서
  실행하고 `-o` 에 절대경로(EOS)를 주면 병합 결과만 EOS 로 갑니다.

---

## [Unreleased] — 2026-08-28: v9 NanoAOD가 parent 대비 2.61 % 결손임을 확인, event-matched v9/v15 비교 도구

### Measured — 이 데이터셋의 v9 NanoAOD는 불완전합니다

`TTToSemiLeptonic_TuneCP5_powheg`, UL17. `dasgoclient summary` 실측:

| | nevents | nlumis | parent 대비 |
|---|---|---|---|
| `RunIISummer20UL17MiniAODv2-106X_mc2017_realistic_v9-v1` (parent) | 355,332,000 | 355,332 | — |
| `RunIISummer20UL17NanoAODv15-150X_mc2017_realistic_v1-v2` | 355,332,000 | 355,332 | **100.00 %** |
| `RunIISummer20UL17NanoAODv9-106X_mc2017_realistic_v9-v1` | 346,052,000 | 346,052 | **97.39 %** |

양쪽 모두 정확히 1000 event/lumi 이므로 차이는 **9,280 lumi = 9,280,000 event**
입니다. v9 와 v15 는 **동일한 MiniAODv2 parent** 를 가지므로(`dasgoclient parent`
로 확인), v9 쪽 NanoAOD 생산이 parent 를 다 덮지 못한 것입니다. 잃어버린 lumi 는
실패한 생산 job 이라 물리적으로 무작위이므로 **편향이 아니라 통계 손실**이고,
`genEventSumw` 를 실제로 처리한 파일에서 합산하는 한 정규화는 자기일관적입니다.
v15 마이그레이션의 추가 근거이며 그룹 보고 사안입니다.

### Measured — v9/v15 파일 경계는 전혀 대응하지 않습니다

parent 가 같아 event 집합은 동일한데, 각 데이터셋의 "첫 번째 파일" 은 event 가
**하나도 겹치지 않았습니다** (v9 1,126,000 / v15 927,000, overlap 0). lumi 범위는
[14715,353516] 과 [2579,331876] 로 크게 겹치지만 lumi *집합* 이 거의 서로소입니다
— NanoAOD job splitting 이 버전마다 다르기 때문입니다. 따라서 event-matched 비교는
**lumi 목록으로 파일을 짝지어야** 합니다: v9 파일의 lumi 집합을
`LuminosityBlocks` 트리에서 읽고, `dasgoclient -query="file,lumi dataset=..."`
(v15 398 파일) 로 겹침을 랭킹하면 143 lumi (~143k event) 를 공유하는 파일이
나옵니다. 이 페어링은 **특정 v9 파일에 묶여 있습니다** — `head -1` 로 다른 파일을
집으면 겹침이 사라집니다.

### Added

- **`script/run_postproc.py --cut`** — `PostProcessor(cut=...)` 로 직행하는
  preselection. default `None` 이라 기존 동작 불변. 두 NanoAOD 버전을 공유 lumi
  집합으로 제한해 event 단위로 비교하기 위해 존재합니다 (전체 파일 두 개를 도는
  ~3 h 대신 각 ~15 min). **출력 event 집합을 바꾸므로 검증 전용**이며, 켜지면
  `PRESELECTION CUT ACTIVE -- VALIDATION MODE` 배너가 로그에 찍힙니다. 물리 컷은
  여전히 모듈의 `analyze()` 에 둡니다.
- **`script/setup_v9v15_validation.sh`** — `source` 용 세션 부트스트랩. 새 lxplus
  세션이 잃는 것(셸 변수, `/tmp` 의 NanoAOD 2개, 공유 lumi cut 문자열)을 전부
  복구합니다. LFN 은 위 페어링 때문에 **고정**되어 있습니다. `NF_CACHE` 를 EOS 로
  두면 5 GB 재다운로드를 피할 수 있습니다.

---

## [Unreleased] — 2026-08-27: 실제 파일 기반 v9/v15 스키마 측정, v15 CPV branch 목록, check_branchlist (C) 오탐 수정

### Added

- **`docs/08_branch_schema_migration.md`** (신규) — branch 목록을 실제 NanoAOD
  파일에서 유도·검증하는 6단계 절차(복사용 명령어 포함)와, 2017UL MC로 실측한
  v9 → v15 스키마 차이 **127 removed / 370 added / 86 retyped**, 그리고
  workstream별 영향. `docs/07_DeveloperGuideline.md` 에 이를 의무화하는
  **Rule 8** 과 Rule 4 라우팅 표 항목, 커밋 체크리스트 항목 추가.
- **`branches/branch_CPV_Run2_MC_v15.txt`** — v9 목록을 실제 v15 인벤토리
  (`script/inventory/inv_2017UL_v15_MC.tsv`, Events 1903 branches)에 대고 포팅.
  v9 rule chain을 v15가 추가한 364개 Events branch에 시뮬레이션해 281개가
  살아남는 것을 확인하고, 그중 per-candidate·미사용 서브시스템 **49개**만 drop
  추가 (`PFCand_*`, `FatJetPFCand_*`, `TrackGenJetAK4_*`, `GenProton_*`,
  `PVBS_*`, `DST_*`, `Scouting*`, `nTauProd`). 새 MET/Rho(`PFMET_*`,
  `RawPFMET_*`, `TrkMET_*`, `FiducialMET_*`, `Rho_*`), 새 태거(PNet/UParT/
  globalParT3), 새 gen 컬럼(`GenJet_n{B,C}Hadrons`, `GenPart_iso`)은 의도적으로
  유지. dead HLT 2개는 v9와 동일하게 남김 — 이 파일은 "v15 스키마" 한 축만 변경.
- `script/inventory/` — `inv_2017UL_v9_MC.tsv` (1666 branches),
  `inv_2017UL_v15_MC.tsv` (1903), `diff_v9_v15_2017UL_MC.txt`.

### Fixed

- **`script/check_branchlist.py` — (C) 절의 오탐 6건.** (C)는 *입력* 스키마에
  대한 검사인데, `cpv` profile의 required 목록에 있던 모듈 **산출** branch
  (`TopCPVCat_isSignal`, `..._Channel_Idx`, `..._Channel_Idx_Expanded`,
  `..._GenPar_Count`, `..._GenBJet_Count`, `..._GenBHad_Count`)를 입력
  인벤토리에서 찾고 있었습니다. 중앙 NanoAOD에 있을 리 없으므로 v9·v15 양쪽에서
  항상 실패했습니다. required 항목에 `produced` 플래그를 도입해 (C)에서 제외하고,
  제외 개수를 출력에 찍어 조용히 넘어가지 않게 했습니다. 이 6개에 대해서는
  (B)("rule chain이 출력까지 살려 보내는가")만이 유의미한 검사입니다.
  => 이제 `rc=4` 는 순수하게 dead 패턴 문제만을 의미합니다.

### Measured (근거, 전문은 08 2절·3절)

- **XRootD 직독이 병목이지 모듈이 아님.** 2000 events 기준 lxplus WAN 2.2 Hz
  vs /tmp 로컬 199.5 Hz. WAN `noop` 실행의 CPU 사용률은 3.8 %. 모듈 자체 비용은
  `user+sys` 차이로 **1.33 s / 2000 events = 0.66 ms/event** (순수 복사 대비
  CPU +11 %). 1.126 M event 파일 ~1.57 h => CRAB wall-time 안. 앞서 제기된
  "2.2 Hz면 생산 불가" 우려는 **철회**.
- **CPV 모듈의 read set은 v15에서 이름 변경 0건, 삭제 0건.** 타입만 변경:
  `GenPart_statusFlags` Int_t->UShort_t (bit 7/13 사용 => 잘림 없음),
  `GenPart_genPartIdxMother` Int_t->Short_t, count branch들 UInt_t->Int_t.
  `GenJet_hadronFlavour` 는 UChar_t 그대로 => `to_int` 계속 필요.
- **ttHH 위험 신호**: v15에서 `Jet_puId`·`Jet_jetId`·`Jet_btagDeepB`·`Jet_qgl`·
  `ChsMET_*` 등이 대체 없이 삭제. `Jet_btagDeepFlavB` 는 생존.
- **`HLT_IsoTkMu*` / `HLT_L2DoubleMu*` 는 2017UL v9·v15 모두 dead** (각각 job당
  ROOT 에러 1줄). 2016 경로명이고 파일이 Run2 4개 era 공유이므로 삭제 금지 —
  per-era 분리가 정답. `01_STATUS.md` OPEN 참조.

---

## [Unreleased] — 2026-08-17: reconciled with the v8.1 handoff tar — three lost records restored, one mis-targeted edit corrected, log hygiene

The `NtupleForge_TopCPV_v8_1_handoff` tar (a 2026-07-15 snapshot) was diffed
against this tree file by file. **Code-wise the tar is a strict subset** — every
`.py`/`.sh`/`.yaml` in it is either identical here or superseded — so nothing was
back-ported. But three *records* had been dropped from the docs between
2026-07-15 and 2026-07-27 while the work they tracked was still undone, and one
config edit had landed on the wrong file. No physics logic changed.

### Restored (tar → here)

1. **`01_STATUS.md` OPEN #0 — condor path + validation config.** Deleted on
   2026-07-26 *without the work being done*: re-verified 2026-08-17, NtupleForge
   still has **no `condor/` directory**. Restored with its recovery pointer
   (past-chats search string), the list of lost files, and all six design
   decisions (condor=local vs CRAB=grid; worker runs `run_postproc.py` with the
   same module+branch wiring; `<dataset>_chunkNNN.root` naming shared with the
   standalone; `MY.JobBatchName`; `config.sh` in `transfer_input_files`;
   preflight `condor_submit` guard + `-s TAG`). Sub-item 1 of 2 is now **DONE**
   (see below); the `condor/` glue is still open.
2. **Ops guidance from the deleted `2026-07-15 (2)` rename entry.** The
   `forgedNtuple.root` rename is re-recorded here as `2026-07-26 (6)` (D-F), but
   two operational notes were lost with the older entry and are reinstated:
   - Anything that matches outputs **by filename** — hadd globs, pullers,
     `checkOutputs`-style scripts — must accept **both** `forgedNtuple_*` and
     `slimmedNtuple_*` during the transition. Cleaner alternative: **pair a
     rename with the next campaign tag** so each campaign directory is
     single-named. Only `make_filelists.py` was ever fixed for this.
   - The name is baked into each task's sandbox/PSet at submit time, so it takes
     effect **from the next submission**. Already-produced files keep the old
     name — and so do the remaining jobs of **in-flight tasks**.
   - Dating note: `crab/PSet.py` and `crab/submit_crab.py` in the 2026-07-15 tar
     already contain `forgedNtuple.root`, so the rename predates the `2026-07-26`
     stamped in their comments. Left as-is (harmless), recorded here.
3. **`.gitignore` rules `*.bk*` and `._*`.** Dropped in the 2026-07-26 rewrite;
   `._*` for no stated reason, `*.bk*` immediately before a `.bk` file became the
   only copy of a production config (next item).

### Corrected

4. **`config_CPV2017UL_MC.yaml` restored to its full 73 datasets;
   `config_CPV2017UL_MC_validation.yaml` created.** On 2026-07-26 the production
   config was overwritten in place (73 → 13 datasets, jobID/output_base →
   `CPV2017UL_MC_Validation`) with **no CHANGELOG / DECISIONS / STATUS entry**,
   leaving the 73 only in `config_CPV2017UL_MC.yaml.bk`. The 13-sample cut was
   correct work aimed at the wrong file: OPEN #0 had already named the intended
   target `config_CPV2017UL_MC_validation.yaml`. Restored from the `.bk` (md5
   `2c6db20cf550db67e4447b08ac1c1dd9`, identical to the tar); the subset moved to
   its own file with an explicit label contract in the header. **Re-verified:**
   the 13 keys and their DAS paths match `TopCPVGenCategorizer/condor/datasets.txt`
   1:1 — 13/13 labels, 13/13 paths, zero mismatches. Both files YAML-parse and
   pass `--preflight` (Rule 6 PASS). Decision:
   **D-2026-08-17-validation-config-split**.
   *Follow-up for the analyst:* the now-redundant `.bk` is ignored again but is
   still tracked — `git rm --cached crabConfig/config_CPV2017UL_MC.yaml.bk`.

### Log hygiene (new)

5. **Never commit CRAB transcripts — `.gitignore` hardened, A17 + decision
   added.** `crab submit` echoes the pre-signed S3 POST policy and signature used
   to upload the task sandbox to `crabcache_prod`. A history audit found two such
   blobs in this **public** repo: `submit_UL18_full_20260727_1120.log` (1.52 MB,
   commit `33e3030`) and `ttbar_SemiLeptonic_v1/.../crab.log` (6.71 MB, commit
   `c72a711`). Both are out of HEAD but reachable in history; **every signature
   in both had already expired** (2026-07-27T10:20Z and 2025-12-11T09:24Z
   respectively) and each was scoped to a single bucket+key, so **nothing needs
   rotating** and no grid credential is exposed. `.gitignore` now blocks
   `submit_*.log`, `crab_status_*.log`, `localcheck_*/`, `local_test_*.log` with
   the reason inline, and keeps the deliberate carve-out for
   `script/das/das_ul18_scan_*.log` (DAS output, no secrets, and the documented input
   of `build_ul18_from_log.py`). History rewrite is **deliberately not done** —
   recipe and rationale in `05_troubleshooting.md` **A17** and
   `03_DECISIONS.md` **D-2026-08-17-no-logs-in-git**.

### Small code fixes (behaviour-preserving)

6. **`crab/submit_crab.py` — Rule 6 check now accepts both quote styles.** The
   preflight regex only matched `cms.untracked.string('...')`, while
   `07_DeveloperGuideline.md` Rule 6 documents the double-quoted form — a
   guideline-conformant `PSet.py` produced a spurious
   `could not parse` FAIL. Now `(['"])(.+?)\1` with optional inner whitespace;
   verified against single-quoted, double-quoted and padded forms. Re-ran
   `--preflight` on both CPV MC configs: **Rule 6 PASS**, totals unchanged.
7. **`script/das_ul18_scan.sh` — USAGE header teed the log into the CWD**, but
   `build_ul18_from_log.py` only globs `script/`, so following the header
   verbatim ended in `FATAL: no das_ul18_scan_*.log found under script/`. Header
   now shows the form `README.md` already used
   (`bash script/das_ul18_scan.sh … | tee script/das_ul18_scan_….log`).
   *(An earlier note that this file was not executable was wrong — it is `0700`
   on disk; only the container copy lost the bit.)*

### Branch policy recorded

8. `origin/main` is at `c76d014` (2026-07-05), **13 commits behind** and without
   even the 2026-07-15 TopCPV state, while being the repo's default branch.
   `main` is fully contained in `devExtendedTtbarId`, so a fast-forward is
   available at any time; deliberately **not** taken mid-campaign. Recorded at
   the top of `01_STATUS.md` and as **D-2026-08-17-branch-policy**.

### Also confirmed (no action)

- `script/das/das_ul18_scan_20260726_1657.log` **is** tracked (432 lines, 33 KB), so
  the UL18 configs' provenance is reproducible from this checkout. An earlier
  reading that it was missing came from a copy step that skipped it.
- The `2026-07-27 (4)` slot is genuinely absent from this log; (3) is followed by
  (5). Nothing in the repo references it — treat the gap as a numbering slip, not
  a lost entry.

---

## [Unreleased] — 2026-07-27 (7): CRAB 10,000-jobs-per-task limit documented at every decision point

No behaviour change. A sibling repo lost a day to this and the same code path
exists here with no guard, so the trap is now written down where someone about
to change the value will actually see it.

### The trap
`splitting: FileBased` -> `njobs = ceil(nfiles / units_per_job)`. CRAB refuses
any task above **10,000 jobs**, but **server-side, after the client reported a
successful submit**. So `crab submit` looks fine, the task then sits at
`SUBMITREFUSED`, `--report` shows a row of all zeros (indistinguishable from
"not started yet"), and `--resubmit` cannot fix it -- resubmit only requeues
*failed* jobs of a task that reached the scheduler. One dataset silently
produces nothing.

### Added (comments, at the points where the value is chosen)
- `crab/submit_crab.py` at the `conf.Data.unitsPerJob` assignment.
- `crabConfig/config_ttHH2017UL.yaml` next to `units_per_job: 1`.
- `script/build_ul18_from_log.py` -- stamped into **both** generated 2018
  configs, so it survives regeneration. Verified: regenerating leaves the 85/81
  dataset configs and `samples_2018UL.json` otherwise unchanged.

### Added (docs)
- `03_DECISIONS.md` **D-2026-07-27-crab-job-limit**.
- `05_troubleshooting.md` **A16** (marked PREVENTIVE -- not yet observed here).

### Why NtupleForge is safe today, and exactly when it stops being
These configs read NanoAOD (~20x fewer files than the MiniAOD parents): largest
2018UL dataset **by file count** is `WJetsToLNu_HT200To400_ext1` at **780 files
-> 780 jobs** (`TTbar_SemiLep` is largest by events but 4th by files, 391 --
job count follows FILES). The 7,466-job
campaign is spread over **85 tasks** and the limit is **per task** -- do not read
the campaign total as if it were near the ceiling. It breaks if a config is
pointed at MiniAOD, or a >10,000-file dataset is added, with `units_per_job: 1`.

### OPEN gap
`--preflight --check-das` here does **not** compute per-task job counts. The
extend submitter in `TTHHGenCategoryTools` does (DAS `nfiles` -> FAIL above the
limit, WARN above 90%, prints the required `units_per_job`). Porting it is the
follow-up; until then the check is manual:
`dasgoclient -query "summary dataset=<DS>" -json | grep -o '"nfiles":[0-9]*'`.

Canonical rule: `TTHHGenCategoryTools/docs/04_decisions.md` **D15**;
incident: that repo's `docs/08_troubleshooting.md` **T-19**.

---

## [Unreleased] — 2026-07-27 (6): 2018 luminosity settled — 59.83 → **59.56 fb⁻¹**

### Changed
- `script/build_ul18_from_log.py` `_meta` block: `lumi_fb_inv` **59.83 → 59.56**, plus a
  full lumi provenance block mirroring the 2017 schema (uncertainty 0.84 %,
  PreLegacy 59.47, Golden JSON filename, brilcalc command, citation, 2018-only
  combine nuisance `lumi_13TeV_15161718_l = 1.0084`, and
  `lumi_brilcalc_result_fb_inv: null`).
  **Regenerated and verified byte-identical** against the hand-edited
  `tempTTHH/data/samples_2018UL.json`, and both crab configs came out unchanged —
  so the value cannot silently revert on the next regeneration.
- `docs/01_STATUS.md` OPEN (b) → **SETTLED**.

### Why
The user supplied the LUM POG page itself. Its **"Recorded Golden Legacy"** row is
the one that matches our UltraLegacy samples: **2017 = 42.07 (0.82 %)**,
**2018 = 59.56 (0.84 %)**. **59.83 appears nowhere on that page** — it had been a
placeholder. PreLegacy (42.12 / 59.47) must not be used.
Sources now linked from the docs:
<https://twiki.cern.ch/twiki/bin/viewauth/CMS/TWikiLUM> (index) and
<https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2> (the table);
cite **CMS-PAS-LUM-20-001**.

### Still open (per the TWiki itself)
The page requires re-running `brilcalc` on the analysis' own certified JSON
(run/lumi + trigger selection); the quoted numbers are full-dataset values.
2017 was done (42.0688 → 42.07); **2018 has not been**. Full change list and the
9 places lumi lives: `tempTTHH/docs/reference/LUMI_SOURCES.md`.

---

## [Unreleased] — 2026-07-27 (5): reproducibility audit — broken commands fixed, phantom feature retracted, status corrected

No production code changed. This entry records the result of auditing every
documented command against the actual CLI of the scripts it invokes.

### Fixed — commands that would have failed as written
- `README.md` "Run locally" passthrough example used `-I modules.noop`.
  `-I` takes **one** `module.path:LIST_NAME` token; with `:LIST_NAME` omitted the
  driver looks for a list literally named `modules` (lowercase), while every
  module in this repo exports `MODULES` → `list 'modules' NOT found`, exit 1.
  Now `-I modules.noop:MODULES`, and the argument table states the rule.
  (The other example, and the UL18 section, were already correct — hence the
  README contradicted itself.)

### Changed — `--ttcat-*` flags labelled DEPRECATED (dead)
- `run_postproc.py` parses `--ttcat-debug-csv`, `--ttcat-debug-csv-path`,
  `--ttcat-quiet` and passes them to `modules/ttbarCategorizer.py` **through
  environment variables — but that module does not exist in this repo**
  (`modules/` holds `noop`, `topCPVCategorizer`, `jetsMETcut`,
  `nanoaod_branch_access`). The flags are accepted and do nothing. Documented as
  such in the README argument table rather than left as an invisible trap.

### Retracted — the AAA fallback never existed in the committed code
- Entry **2026-07-27 (3)** announced `resolve_input_files()` + `--xrd-fallback`.
  That change was **fully reverted the same day** at the user's request and the
  revert was never written down, so two documents advertised a flag that raises
  `unrecognized arguments`. Both are now corrected in place:
  the changelog entry carries a **[REVERTED]** banner, and
  `05_troubleshooting.md` **A15** now opens with "There is NO AAA fallback in the
  code" plus what to do instead (let CRAB's retries move the job).
  The *reasoning* for dropping it is preserved — it is the useful part.

### Corrected — `01_STATUS.md` was describing a superseded plan
- Said the prescan CRAB submission "is the next action" and that real production
  would come "after the ttHH categorization work lands". Neither happened:
  the prescan smoke task was **killed and its project dir removed**, and the
  **full UL18 production was submitted 2026-07-27** (85 tasks / 7,466 jobs /
  6.74 TB, preflight 35 PASS / 0 FAIL) without waiting for the categorizer —
  the two campaigns are independent because the analyzer resolves
  `Expanded_genTtbarId` at runtime from patch files.
- Watch items recorded: `WJetsToLNu_HT200To400_ext1` (461/780 failed) and
  `HT70To100_ext1` (322/669) — A15-type KISTI `[3011]`, recovered by retries.
- Removed the stale OPEN "(c) jobID/splitting placeholders until first
  submission" (the submission happened). Clarified **61 MC primary datasets
  (queries) → 77 MC entries (with ext variants) → 85 total with Data**, which
  read as three inconsistent counts.

### Housekeeping
- `.gitignore`: no rule change needed, but the files deleted in the previous pass
  are still in the index — `git rm` them (see the report accompanying this
  change). Deleted a stale `script/__pycache__/run_postproc.cpython-310.pyc`
  that still contained the reverted `--no-xrd-fallback` and was the only on-disk
  evidence for the phantom feature.

---

## [Unreleased] — 2026-07-27 (3): A15 incident — documented; AAA fallback added but OPT-IN → **REVERTED, see 2026-07-27 (5)**

### Incident (A15)
- First failure of the UL18 full production: a `TTbar_SemiLep` job at
  `T2_KR_KISTI` died in 14 s with `[3011] No such file` — the bare LFN resolved
  to the local SE only, and `ROOT.TFile.Open` has no redirector fallback (cmsRun's
  `PoolSource` would have retried; our `scriptExe` path gets nothing for free).
  Rucio listed the site as holding the block, so "the site has the data" does not
  guarantee the file opens.
- **Resolution: do nothing.** The post-job log shows CRAB classifies it as
  `RECOVERABLE` → `COOLOFF` → DAGMan retries (max 3), and each retry is
  re-matched, so it can land at a site that can serve the file. That is a better
  remedy than anything the job can do for itself.
- **Not a regression:** the no-fallback structure predates all 2026-07 changes.
  It fires only when the matched site cannot serve the file, so it depends on
  replica health and scheduling luck — it was very likely absorbed silently by
  the same retries during the 2017 campaign.
- Full write-up incl. the `50115 BadFWJRXML` red herring and a diagnosis recipe:
  `05_troubleshooting.md` **A15**.

### Added (opt-in, default OFF) → **REVERTED the same day — DO NOT LOOK FOR THIS CODE**
> **[REVERTED 2026-07-27]** At the user's request the whole AAA-fallback change was
> **fully removed** from `script/run_postproc.py` (0 traces; `grep xrd` returns
> nothing). `--xrd-fallback` and `resolve_input_files()` **do not exist** — passing
> the flag gives `error: unrecognized arguments: --xrd-fallback`. Only the
> *diagnosis* half was kept (`05_troubleshooting.md` A15). The reasoning below is
> preserved as the record of why it was tried and why it was dropped.

- `script/run_postproc.py` `resolve_input_files()` + **`--xrd-fallback`**:
  probe-open inputs (local first) and re-route unreadable ones through
  `cms-xrd-global` → `xrootd-cms.infn.it` → `cmsxrootd.fnal.gov`; a file that
  opens nowhere exits **2** with an explicit list instead of a traceback from
  inside `PostProcessor.run()`.
- **Written and demoted to opt-in on the same day**, after re-assessing it at the
  user's prompting ("is this worth doing now, could it hurt?"). It is not a free
  win: (1) narrow scope — if no replica is readable anywhere, the redirector
  cannot help either, and the useful case is the one CRAB's retry already covers
  better by moving the job; (2) it can be **harmful** — a transient local failure
  is indistinguishable from a missing replica, so the job silently degrades to
  WAN streaming instead of failing fast and being re-matched, and one
  `TTbar_SemiLep` file (~1.22 M events) read 5–10× slower can exceed the 600-min
  walltime; (3) it is unproven on the grid, and shipping unproven code in a
  7,466-job sandbox is itself a risk (cf. A14).
  With the flag off, the default code path is unchanged (no probe, no extra open).
- Verified locally against a stubbed ROOT for all three paths (local OK / AAA
  rescue / unreadable → exit 2). **Never exercised on the grid.**

### Ops note
- A code fix does not reach already-submitted tasks: CRAB ships the sandbox at
  submit time, so `crab resubmit` reuses the OLD script (same trap as A14).
  Anything patched must go out as **NEW tasks**.

---

## [Unreleased] — 2026-07-27 (2): plan re-scope — injector DEFERRED, UL18 full production is the path

### Decided (user, 2026-07-27)
- **`modules/expandedTtbarIdInjector.py` is DEFERRED to a later update.** The
  project's end goal is unchanged — NtupleForge, not the analyzer, should own
  `Expanded_genTtbarId` as a baked-in branch — but writing it now would add
  new-module validation *plus a full ntuple re-production* to the critical path,
  and the immediate objective is the fastest route to UL18 control plots.
  The interim contract (analyzer-side runtime patch lookup, the 2017-proven
  path, zero new code), the cost of deferring, and the resume conditions are
  recorded in `01_STATUS.md` and in the workspace `00_CONTEXT…md` §1.
- **The slim prescan CRAB production is cancelled**, not just postponed: its
  purpose (do the UL18 samples produce? does the slim path work?) was met by
  the 2026-07-27 local run. `config_ttHH2018UL_prescan.yaml` and the two
  `branch_prescan_slim_*.txt` files are kept — they remain the cheapest way to
  re-test a new era or a new NanoAOD version.
- New runbook: workspace `archive_2026/RUNBOOK_UL18_to_controlplots.md`
  (`archive_2026/RUNBOOK_UL18_step1.md` marked SUPERSEDED).

### Added (runbook §2, Phase 1-0)
- **Pre-submission local multi-sample check** for the full production, added on
  the user's prompting after recalling the A14 incident: in the CPV campaign
  *signal passed and only the `QCD_HT*` background died* in CRAB
  (`05_troubleshooting.md` A14 — `math.cosh` overflow on status-21 beam-parallel
  partons), which a single-sample test could never have caught. The new check
  runs 4 datasets of different character (smallest MC / largest MC / `_ext1` /
  Data) at `-N 500` and asserts per sample: file opens, Events non-empty,
  ≥500 branches (i.e. `keep *` really applied), and for MC that
  `Runs.genEventSumw`, `genWeight`, `genTtbarId` are present; ROOT `Error in <`
  lines must be 0.
  **Risk assessment recorded honestly:** this campaign uses `noop.py` +
  `keep *`, so it does no per-event math and is schema-agnostic — the A14 class
  of failure *cannot* recur here, and neither can `SetBranchStatus` errors. The
  residual risks the check does cover are dataset-path typos, unreadable files
  and empty datasets; `--check-das` covers existence for all 85.

---

## [Unreleased] — 2026-07-27: first REAL lxplus run of the UL18 prescan path — 3 fixes

### Verified on lxplus (logs supplied by the user)
- **`--preflight` on `config_ttHH2018UL_prescan.yaml`: 35 PASS / 0 WARN / 0 FAIL
  → READY TO SUBMIT.** Environment (CRABClient, CMSSW_14_2_1 el8_amd64_gcc12,
  proxy 168 h), Rule 6 (`forgedNtuple.root` on both sides), all 81 datasets,
  and the outLFN/requestName preview all check out.
- **Local `-N 2000` run on a real UL18 file** (`TTbb_4f_TTTo2L2Nu…-v1`,
  xrootd): job finished successfully and the output satisfies every check the
  slim strategy depends on —
  `Runs` tree present with `genEventSumw`/`genEventSumw2`/`genEventCount`,
  `LuminosityBlocks` also passed through, Events kept exactly **15** branches
  including `run`/`luminosityBlock`/`event`/`genWeight`/`genTtbarId`.
  **The slim-branch strategy is now empirically validated, not just argued.**
- **Physics finding (feeds tempTTHH trigger work):** the 2018 NanoAOD contains
  `HLT_PFHT330PT30_QuadPFJet_75_60_45_40_TriplePFBTagDeepCSV_4p5`,
  `HLT_PFHT400_SixPFJet32_DoublePFBTagDeepCSV_2p94`,
  `HLT_PFHT450_SixPFJet36_PFBTagDeepCSV_1p59` (+ `HLT_PFHT1050`,
  `HLT_IsoMu24`, `HLT_IsoMu27`), and **none of the six 2017 CSV-era paths**.

### Fixed
- **`--check-das` reported all 81 datasets as unresolvable (false FAIL).** The
  plain-text output of `dasgoclient -query "summary dataset=…"` is a column
  layout, not `nevents=N`, so the regex never matched. Now queries with
  `-json` and reads `summary[0].nevents` — the same code path
  `script/das_ul18_scan.sh` already proved on lxplus — with a plain-text
  regex fallback. Verified against a stub dasgoclient (81/81 resolved).
- **Branch selection is now ERA-SPECIFIC:** `branch_prescan_slim.txt` →
  **`branch_prescan_slim_2018.txt`** (+ new `branch_prescan_slim_2017.txt`).
  Reason: a `keep` pattern that matches nothing is **not** silently ignored —
  ROOT prints `Error in <TTree::SetBranchStatus>: unknown branch -> …` once per
  job for each. The six 2017 CSV HLT names produced exactly that on the UL18
  file. Beyond log noise (6 lines × thousands of jobs), a real typo would be
  indistinguishable from these expected misses; with per-era lists any such
  error now means a genuine problem. The earlier claim in the old file's header
  that unmatched keeps are "harmless" was wrong and is corrected.
  The 2017 file's HLT list is taken from the analyzer's production 2017 logic
  and is marked **unverified** until a `-N` run on a UL17 file confirms it.
- **`config_ttHH2018UL_prescan.yaml`: `units_per_job` 5 → 1.** The "slim output
  ⇒ bigger jobs" reasoning was wrong: the INPUT is read in full regardless
  (A4, `branchsel=None`; the driver even logs "input is read in full"), so job
  runtime scales with input files. 1 file/job is the value the 2017 campaign
  proved; at 5 the largest 2018 samples (TTbar_SemiLep 476 M events over 391
  files ⇒ ~6.1 M events/job) would risk the CRAB walltime.
- `script/build_ul18_from_log.py` updated for both of the above so the configs
  stay reproducible; regenerated.

---

## [Unreleased] — 2026-07-26 (7): `--preflight` pre-submission checker + audit fixes

### Added
- **`crab/submit_crab.py --preflight`** — read-only, submits nothing, creates
  nothing but a log (`preflight_<config>_<timestamp>.log`), exits non-zero on
  any FAIL. Checks: config schema (`common.*` keys, splitting value), analysis
  module file + that the declared list variable is actually assigned, sibling
  `.py` files that will be shipped, branch-selection file (rule count, syntax,
  SLIM vs PASSTHROUGH, and — for SLIM — that `run`/`luminosityBlock`/`event`
  are kept and `genWeight`/`genTtbarId` are not silently dropped), **Rule 6**
  (parses the output filename out of both `PSet.py` and `submit_crab.py` and
  compares), worker files, CRABClient/CMSSW/VOMS environment, cwd writability,
  dataset path syntax + duplicates + tier mix, an outLFN/requestName preview,
  and existing CRAB project dirs that would make a submit skip. `--check-das`
  additionally resolves every dataset on DAS; `--preview N` controls listing.
- **Guarded CRAB imports:** `CRABClient`/`CRABAPI` import failures no longer
  crash the script at import time — they are reported as a preflight FAIL, and
  any real action fails fast through `_require_crab()`. This is what lets
  `--preflight` run in a shell where `crab-setup.sh` was not sourced.

### Fixed (2026-07-26 audit)
- `build_ul18_from_log.py` and the artefacts it stamps (`config_ttHH2018UL*.yaml`
  header, `samples_2018UL.json._meta.source_log`) referenced a **nonexistent**
  `script/logs/das_ul18_scan_2026-07-26.log`; corrected to the real
  `script/das/das_ul18_scan_20260726_1657.log` and regenerated (contents otherwise
  byte-identical).
- `docs/07_DeveloperGuideline.md`, `docs/05_troubleshooting.md` and `README.md`
  still stated that both Rule-6 sites use `slimmedNtuple.root`; updated to
  `forgedNtuple.root` (the rename is what the preflight now enforces).
- `.gitignore`: ignore `preflight_*.log`.

---

## [Unreleased] — 2026-07-26 (6): D-F executed — output ntuple renamed to forgedNtuple.root

### Changed (BEHAVIOUR — new productions write a different filename)
- **Producers (authoritative, Rule 6 pair kept identical):**
  `crab/PSet.py` `process.output.fileName` and `crab/submit_crab.py` `out_name`
  → **`forgedNtuple.root`** (was `slimmedNtuple.root`).
- **Consumers / file discovery — accept BOTH names**, because every ntuple
  produced before today is physically on Tier-3 as `slimmedNtuple_*.root`
  (campaign `ttHH2017UL_fullNano_v20` included). A forged-only pattern would
  make the existing 2017 filelists unregenerable:
  - `tempTTHH/make_filelists.py`: new `NTUPLE_PREFIXES = ("forgedNtuple",
    "slimmedNtuple")`, used by `find_root_files()`.
  - `TTHHGenCategoryTools/Validation/filelists/make_filelists.py`: same constant
    and same dual matching.
  Remove the legacy prefix only after every campaign has been reproduced.
- Docs/comment-only: `script/validate_topcpvcat.py` usage example,
  `TTHHGenCategoryTools/Validation/scripts/submit_hist_condor.py`,
  `Validation/tools/{makeTtbarHist,matchTtbarId}.cc` header comments.
- Rule 7 grep performed workspace-wide (not only `crab/`+`script/`+
  `crabConfig/`): the only functional hits were the two producers and the two
  filelist makers. `TtbarIdHistCompare/` (legacy, D-G),
  `tempTTHH/docs/backup_20260629/`, `docs/legacy/` and committed filelist data
  files were intentionally left untouched. Analyzer-side `TFile::Open` calls
  take their paths from the filelists, so no other code hardcodes the name.
- Verified locally: producer strings identical (Rule 6), all touched Python
  parses, `str.startswith(tuple)` matching confirmed on both prefixes.
  **unverified:** no CRAB run yet with the new name.

---

## [Unreleased] — 2026-07-26 (5): UL18 prescan smoke-test campaign (slim branches)

### Added
- **`branches/branch_prescan_slim.txt`** — minimal Events-tree selection
  (`drop *` + explicit keeps) for a cheap UL18 smoke-test production whose only
  consumer is tempTTHH `prescan`. Header documents *why it is safe*: Σgenw is
  read from `Runs.genEventSumw/genEventSumw2/genEventCount`, and output branch
  selection filters only the Events tree while the post-processor copies `Runs`
  and `LuminosityBlocks` through (04_architecture, 05_troubleshooting).
  Verified prescan Events usage in `ttHHanalyzer_unified.cc`: `genWeight`
  (L1902), `genTtbarId` (L1913/1927), `run`/`luminosityBlock`/`event`
  (L1917-18, the Expanded_genTtbarId 3-key). **Hazard the keeps guard against:**
  a missing `genTtbarId` is NOT detected — eventBuffer defaults it to 0, so
  every MC event would be silently binned as tt+LF (`sumGenW_id_0`); same for
  `genWeight` → `sumGenW_total = 0`. Also keeps the hadronic HLT bits so the
  2018 path availability (DeepCSV variants) can be checked on the slim ntuple.
- **`crabConfig/config_ttHH2018UL_prescan.yaml`** — 81 datasets: all 77 MC +
  **JetHT only** for Data (user decision: 2018 has no BTagCSV, and SingleMuon
  is only needed for the later trigger-SF study; it stays in the full config).
  `jobID/output_base = campaign_ttHH2018UL_prescanSlim_v1`, `units_per_job: 5`
  (slim output ⇒ fewer, larger jobs). Generated by
  `script/build_ul18_from_log.py` alongside the full config, so both stay in
  sync with the DAS log. YAML-schema checked against every key
  `crab/submit_crab.py` consumes. **unverified — no CRAB submission yet.**

### Verified
- UL18 sample completeness: all 85 entries carry `nevents`+`nfiles`
  (MC total 2,428,778,733; Data/JetHT+SingleMuon 1,662,166,075), and every MC
  entry has non-null xsec/BR — so the post-production prescan can be compared
  against DAS `nevents` sample by sample.
- Sample-list cross-check vs the ttH AN (AN-2019/094, non-UL, reference only):
  44/61 MC primaries appear there; 5 more (TTHHto4b, TT4b, TTZToBB, TTZHTo4b,
  TTZZTo4b) appear in the ttHH AN (AN-2022/122). Remaining 12 = the hadronic
  V→qq / high-HT V+jets bins (XSDB-sourced by design, documented in the xsec
  DB refs) plus the 5 rare-top samples in the OPEN item below.

### OPEN (found during the cross-check — values NOT changed)
- `TTTT/TTWW/TTWH/TTWZ/TTTW` carry `xsec_ref: "ttHH AN Tab.9"` in
  `samples_2017UL.json` (copied verbatim into `samples_2018UL.json`), but AN
  Table 9 lists only ttHH/ttH/tt+jets/tt+bb/tt+4b/ttZ/ttZZ/ttZH, and the AN text
  contains no ttWW/tttt/multi-top entry at all → **reference is wrong or the
  values come from elsewhere (likely XSDB); needs a source fix.**
- `TTZToBB` = 861 fb (ref: AN Tab.16) vs **AN Tab.9 ttZ = 841 fb** — confirm
  which definition/table is intended before unblinding.

---

## [Unreleased] — 2026-07-26 (4): BTagCSV-2018 absence CONFIRMED (forensic scan run)

### Verified (lxplus run, log `script/das/das_ul18_scan_20260726_1657.log`)
- **BTagCSV does not exist in 2018 — settled, not a naming issue.** The v2
  forensic queries returned **0 hits** for `/BTagCSV/Run2018*/*` under **any
  tier** and **any dataset status** (`status=*`, i.e. INVALID/DEPRECATED
  included). `/BTag*/Run2018*/NANOAOD` returns only **BTagMu** (54 datasets) —
  the BTV muon-tagged calibration PD, not the FH b-tag jet stream.
- **PD inventory diff** (Run2018A vs Run2017C, UL NanoAODv9) — the 2018 primary
  dataset consolidation: **removed** BTagCSV, DoubleEG, FSQJet1, FSQJet2,
  HTMHT, HighPtLowerPhotons, HighPtPhoton30AndZ, SingleElectron, SinglePhoton;
  **added** EGamma. 2018 = BTagMu, Charmonium, DisplacedJet, DoubleMuon,
  DoubleMuonLowMass, EGamma, JetHT, MET, MuonEG, MuOnia, SingleMuon, Tau.
- **Consequence: JetHT alone covers the 2018 FH hadronic menu** (the 4J3T
  b-tag quad-jet paths sit in JetHT for 2018). Recorded in the generated
  config's comments. **Analyzer impact (tempTTHH, FUTURE):** the 2017
  BTagCSV↔JetHT orthogonality split + veto (`ttHHanalyzer_unified.cc`
  ~L295–360) must collapse to a JetHT-only OR for 2018, and 2018 path names
  differ (`…TriplePFBTagDeepCSV_4p5`); the existing TODO at L297 covers this.
- **Reproducibility:** rerunning `script/build_ul18_from_log.py` against the
  real lxplus log reproduced `config_ttHH2018UL.yaml` and
  `samples_2018UL.json` **byte-identical** to the earlier transcription-based
  run (diff empty) — the log is the sole input and the step is idempotent.

### Changed
- `script/build_ul18_from_log.py`: log auto-discovery now globs
  `script/**/das_ul18_scan_*.log` (the log lives directly in `script/`);
  BTagCSV comment block upgraded from inference to confirmed verdict.

---

## [Unreleased] — 2026-07-26 (3): das_ul18_scan.sh v2 — broad data forensics

### Added
- **`script/das_ul18_scan.sh` §[2b]** (user request): for NOT_FOUND primaries
  (BTagCSV), widen the search — BTagCSV under any tier and `status=*`
  (catches INVALID/DEPRECATED), `BTag*`/`*BTag*` name wildcards, and a full
  primary-dataset **inventory dump for Run2018A vs Run2017C** (UL NanoAODv9,
  `PD2018|`/`PD2017|` lines) so merged/renamed PDs are identifiable from the
  log. **unverified — rerun on lxplus.** GT36 data choice stays OPEN; decision
  policy per user: follow the samples used by the ttHH AN.

---

## [Unreleased] — 2026-07-26 (2): 2018UL campaign config generated from the DAS scan

### Added
- **`crabConfig/config_ttHH2018UL.yaml`** — 85 datasets (77 MC + 8 Data), generated
  by the new **`script/build_ul18_from_log.py`** from
  **`script/das/das_ul18_scan_20260726_1657.log`** (lxplus run, transcribed DS/RESULT
  lines). Selection rules recorded in the script header: standard campaign only
  (JMENano/PUFor*/FSUL18/BPH excluded); ext1/ext2 = separate keys (new vs UL17:
  `TTWW_ext1`); Data = non-GT36 with GT36 twins as comments (**OPEN**: confirm
  XPOG recommendation); **BTagCSV absent in 2018** (DAS NOT_FOUND — PD
  discontinued in the 2018 PD restructuring; FH b-tag HLT paths live in JetHT).
  `jobID: campaign_ttHH2018UL_fullNano_v1` (placeholder until first submission).
- `tempTTHH/data/samples_2018UL.json` written by the same script (see tempTTHH
  CHANGELOG). yaml↔json cross-checked programmatically (0 mismatches).
- Campaign-string sanity: `106X_upgrade2018_realistic_v16_L1v1` verified against
  the UL18 sample list in ttHH AN-2022/122 (identical GT string) — the `L1v1`
  suffix is the 2018 L1-menu tag inside the standard UL18 MC global tag.

---

## [Unreleased] — 2026-07-26: ttHH 2018UL expansion kickoff — DAS scan script

### Added
- **`script/das_ul18_scan.sh`** — for every sample in
  `crabConfig/config_ttHH2017UL.yaml`, queries DAS for the UL18 NanoAODv9
  equivalent (exact primary, then relaxed `_TuneCP5`-prefix fallback) and
  dumps `nevents`/`nfiles`/size per hit; `--ul17-nevents` re-dumps UL17
  summaries to cross-check `tempTTHH/data/samples_2017UL.json`. Output is
  machine-readable (`DS|`/`RESULT|` lines) and is the input for the future
  `config_ttHH2018UL_{Data,MC}.yaml`. The embedded 61-primary list was
  verified 1:1 against the YAML at generation time. **unverified — requires
  lxplus (dasgoclient + VOMS proxy); bash-syntax-checked only.**
- `01_STATUS.md`: 2018UL workstream + planned `expandedTtbarIdInjector.py`
  entry registered (plan canonical in the workspace-level 00_CONTEXT doc).

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
