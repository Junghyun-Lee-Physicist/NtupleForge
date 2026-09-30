#!/usr/bin/env python3
"""
NtupleForge: NanoAOD Post-Processing Framework
==============================================

Description:
    This script serves as a lightweight wrapper around the standard CMS NanoAODTools PostProcessor.
    It facilitates event skimming (cuts), branch slimming (keep/drop), and the application of 
    custom analysis modules (Python-based) to NanoAOD Ntuples.

Mechanism:
    1. Parses input arguments (Input files, Modules, Branch selection).
    2. Load specified Python modules dynamically.
    3. Configures the PostProcessor engine with hardcoded defaults for consistency.
    4. Runs the event loop, producing a new ROOT file (Skim).
    5. Optionally merges multiple outputs into a single file if --output-file is specified.

Usage Examples:
    # 1. Basic Split Mode (One output per input)
    python3 script/run_postproc.py input1.root input2.root \
        -b branches/branch_keep_and_drop.txt \
        -I modules.jetsMETcut:MODULES

    # 2. Merge Mode (Hadd multiple inputs into one output)
    python3 script/run_postproc.py input*.root \
        -b branches/branch_keep_and_drop.txt \
        -I modules.jetsMETcut:MODULES \
        --output-file merged_skim.root

    # 3. DEAD EXAMPLE -- kept only to explain the --ttcat-* flags below.
    #    modules/ttbarCategorizer.py DOES NOT EXIST in this repository
    #    (modules/ holds noop, topCPVCategorizer, jetsMETcut,
    #    nanoaod_branch_access), so this command fails at import and the
    #    three --ttcat-* flags are parsed but have no effect.
    #    python3 script/run_postproc.py input.root \
    #        -b branches/branch_ttHHto4b_hadronic_2017UL.txt \
    #        -I modules.ttbarCategorizer:MODULES \
    #        -N 1000 --ttcat-debug-csv --ttcat-debug-csv-path /tmp/ttcat.csv

[Note on YAML Configuration]
When submitting jobs via CRAB using 'submit_crab.py', the arguments for this script 
(such as --imports and --branch-selection) are derived from the YAML config file 
(e.g., 'crabConfig/config_crabTest.yaml'). 
Make sure the values in the YAML file correctly point to existing files and modules.

[Event skim and audit (2026-09-28, docs/12_fastpath_workflow_plan.md section 2.3)]
--skim NAME is the PRODUCTION event selection: NAME is one of the table in
forge_skims.py (none, 6jcount, 6j20, 6j25, 6j30, 6j20ht400) and its TTreeFormula
goes to PostProcessor(cut=...). With no python module (modules/noop.py)
NanoAODTools selects with TTree::Draw('>>elist') and copies with CopyTree, all
C++; Runs and LuminosityBlocks are still copied whole. --cut stays the
validation-only preselection described at its argument; the two exclude each
other. --audit (needs --output-file) reads every input file once more with
RDataFrame after the copy, checks the closure and appends ForgeAudit,
ForgeTTbbKeys and ForgeProvenance to the output (forge_audit.py); a closure
FAIL gives exit 5, read trouble 85, an input the audit cannot open 84, an audit
error 7 (codes chosen for CRAB's retry policy, forge_audit.py). Without the
two flags nothing changes. submit_crab.py sets both from the YAML keys
`skim:` and `audit:` and ships forge_skims.py and forge_audit.py.

[Input fallback (2026-09-30, docs/05_troubleshooting.md A24)]
--input-fallback URL: CRAB can run a job at a site that does not hold its input
(CMS overflow); cmsRun falls back to AAA there, NanoAODTools does not (it turns
the LFN into the site's PFN with edmFileUtil and opens that, so the job dies
with 'file ... does not exist' and CRAB reports 50115). With the flag every LFN
(/store/...) is first opened at the site the same way; if that fails, URL + LFN
(e.g. root://cms-xrd-global.cern.ch//store/...) is copied with xrdcp into
./forge_aaa/store/... and the job reads the copy (reading through AAA event by
event was 9-59 events/s in P5); only if the copy fails does it read URL + LFN
directly. A FORGE|INPUT line says which (resolve_inputs); ForgeAudit and
ForgeProvenance record the LFN. submit_crab.py adds the flag unless YAML
`aaa_fallback: false`.

[Branch Selection Policy — INPUT vs OUTPUT]
The keep/drop file passed via -b is applied ONLY to the OUTPUT tree
(`outputbranchsel`). The INPUT tree is NOT filtered (`branchsel=None`),
so modules can freely read any branch present in the source NanoAOD,
including gen-level branches (GenPart_*, GenJet_*, genTtbarId) needed
for ttbar categorization.

Why this matters:
    Setting `branchsel=args.branch_selection` (the previous behaviour)
    applied `drop *` to BOTH input and output. The driver then re-
    enabled only the listed `keep` branches on the input tree, but
    the way nanoAOD-tools normalizes wildcard rules vs explicit names
    sometimes left vector branches in a "hasattr=True / len()=0"
    zombie state. Result: 1000/1000 events fell into the NOGEN path
    of ttbarCategorizer despite GenPart being listed in keep rules.
    See debugging session 2026-04-06.

Author: Junghyun Lee (NtupleForge)
"""

import os
import sys
import argparse
import importlib
import logging
import datetime
import subprocess
import time
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor


# -------------------------------------------------------------------------
# Path Configuration (For ModuleNotFoundError)
# -------------------------------------------------------------------------
# Add the parent directory (NtupleForge root) to sys.path so that 'modules' package can be found
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)


# -------------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='[run_postproc] : %(message)s')
logger = logging.getLogger("NtupleForge")


FALLBACK_DIR = "forge_aaa"      # ./forge_aaa/store/...: the copy keeps the LFN in its path (FJR, lfn_of)
FALLBACK_COPY_TIMEOUT_S = 3600


def one_line(s, n=200):
    """A reason for a FORGE|INPUT field: one line, no '|', at most n characters."""
    return " ".join(str(s).replace("|", "/").split())[:n]


def probe_open(ROOT, pfn):
    """(True, "") if ROOT opens pfn, else (False, why). ROOT's error lines of a
    failed open are not printed (gErrorIgnoreLevel kFatal for the probe only,
    restored on every path): a replica missing at this site is not a read error
    of the job, and forge_campaign_audit.py (L1) counts every 'Error in <' line
    of the job log. (forge_audit.py C2e counts only what its capture sees, which
    starts after this.)"""
    level = ROOT.gErrorIgnoreLevel
    ROOT.gErrorIgnoreLevel = ROOT.kFatal
    f = None
    try:
        f = ROOT.TFile.Open(pfn)
        if f and not f.IsZombie():
            return True, ""
        return False, "TFile::Open(%s) gave %s" % (pfn, "a zombie" if f else "no file")
    except Exception as e:              # ROOT >= 6.30 raises OSError instead of returning a null pointer
        return False, "%s: %s" % (type(e).__name__, e)
    finally:
        try:
            if f:
                f.Close()
        except Exception:
            pass
        ROOT.gErrorIgnoreLevel = level


def copy_input(url, lfn, timeout=FALLBACK_COPY_TIMEOUT_S):
    """xrdcp url to ./forge_aaa<lfn>: (local path, how) or (None, why). The job
    then reads a local file; reading through AAA event by event ran at 9 and 59
    events/s in P5 (docs/09 25), hours to a day for a 600k-event file, while
    xrdcp moved 269 MB in 15 s."""
    dest = os.path.join(os.getcwd(), FALLBACK_DIR + lfn)
    t0 = time.time()
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        p = subprocess.run(["xrdcp", "-f", "-N", url, dest], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        text = p.stdout.decode("utf-8", "replace")
        if p.returncode == 0 and os.path.isfile(dest):
            return dest, "copy (%.0f MB in %.0f s) %s" % (os.path.getsize(dest) / 1e6, time.time() - t0, dest)
        last = [l for l in text.splitlines() if l.strip()]
        why = "xrdcp exit %d: %s" % (p.returncode, last[-1] if last else "no output")
    except subprocess.TimeoutExpired:
        why = "xrdcp did not finish in %d s" % timeout
    except Exception as e:              # no xrdcp, a disk problem
        why = "xrdcp: %s: %s" % (type(e).__name__, e)
    try:
        if os.path.exists(dest):
            os.remove(dest)             # a partial copy
    except OSError:
        pass
    return None, why


def resolve_inputs(files, fallback, log):
    """--input-fallback: every LFN is opened at the site first, as NanoAODTools
    PostProcessor.run() would open it (edmFileUtil -d gives the site's PFN). If
    that fails, fallback + LFN (AAA) is copied into the job directory with xrdcp
    and the job reads the copy; if the copy fails too, the job reads fallback +
    LFN directly (slow, see copy_input). Other names are kept. One FORGE|INPUT
    line per LFN:
      FORGE|INPUT|<lfn>|local|<pfn>
      FORGE|INPUT|<lfn>|fallback|<url>|<why the site failed>|copy (<MB> MB in <s> s) <path>
      FORGE|INPUT|<lfn>|fallback|<url>|<why the site failed>|stream (<why the copy failed>)
    Returns (names the job opens, {name opened: LFN given}); forge_audit.py
    records the LFN, not the name opened."""
    import ROOT
    out, lfns = [], {}
    for name in files:
        name = name.strip()
        if not name.startswith("/store/"):
            out.append(name)
            continue
        why, pfn = "", ""
        try:     # the call NanoAODTools makes (postprocessor.py), stdout only
            pfn = subprocess.check_output(["edmFileUtil", "-d", "-f " + name]).decode("utf-8", "replace").strip()
            if not pfn:
                why = "edmFileUtil gave no PFN"
        except Exception as e:
            why = "edmFileUtil: %s: %s" % (type(e).__name__, e)
        if pfn:
            ok, why = probe_open(ROOT, pfn)
            if ok:
                log.info("Input %s: opened at the site as %s", name, pfn)
                print("FORGE|INPUT|%s|local|%s" % (name, pfn))
                sys.stdout.flush()
                out.append(pfn)
                lfns[pfn] = name
                continue
        url = fallback.rstrip("/") + "/" + name
        log.warning("Input %s: not readable at the site (%s); copying %s", name, one_line(why, 300), url)
        sys.stderr.flush()
        opened, how = copy_input(url, name)
        if opened:
            log.info("Input %s: the job reads the %s", name, how)
        else:
            log.warning("Input %s: the copy failed (%s); the job reads %s directly", name, one_line(how, 300), url)
            opened, how = url, "stream (%s)" % how
        print("FORGE|INPUT|%s|fallback|%s|%s|%s" % (name, url, one_line(why), one_line(how, 500)))
        sys.stdout.flush()
        out.append(opened)
        lfns[opened] = name
    return out, lfns


def main():
    # Print execution timestamp immediately
    start_time = datetime.datetime.now()
    logger.info("="*60)
    logger.info(f"Execution Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    parser = argparse.ArgumentParser(description="NtupleForge: Minimal Post-Processing Script")

    # [1] Essential Arguments
    # Input files: Accepts a list of ROOT file paths directly (relies on shell expansion)
    parser.add_argument("input_files", type=str, nargs="+", help="Input ROOT file paths (space separated)")
    
    # Module & Branch Configuration
    parser.add_argument("-I", "--imports", type=str, nargs="+", required=True,
                        help="Modules to import (Format: 'module_name:list_name', e.g., modules.jetsMETcut:MODULES)")
    parser.add_argument("-b", "--branch-selection", type=str, required=True,
                        help="Path to branch selection file (keep/drop rules for OUTPUT tree only)")

    # [2] Optional Output Configuration
    # If provided, triggers 'hadd' to merge all outputs into this filename.
    # If not provided, defaults to split mode (one output file per input file).
    parser.add_argument("-o", "--output-file", type=str, default=None, 
                        help="Merge all outputs into this filename (e.g., skimmed.root)")

    # Event Control (Default: None = Process All Events)
    parser.add_argument("-N", "--max-events", type=int, default=None, 
                        help="Max number of events to process. Default is None (Run All).")
    parser.add_argument("--first-entry", type=int, default=0,
                        help="Index of the first event to process. Default is 0.")
    parser.add_argument("--cut", type=str, default=None,
                        help="VALIDATION ONLY -- TTree preselection expression passed to "
                             "PostProcessor(cut=...). It CHANGES THE OUTPUT EVENT SET, so it "
                             "must never appear in a production CRAB config; physics cuts "
                             "belong in the module's analyze(). Intended use: restricting a "
                             "cross-version comparison to a shared set of luminosity blocks, "
                             "e.g. --cut 'luminosityBlock==12||luminosityBlock==57'. "
                             "Default None = process every entry.")
    parser.add_argument("--skim", type=str, default=None,
                        help="PRODUCTION event selection by name from forge_skims.py (none, 6jcount, "
                             "6j20, 6j25, 6j30, 6j20ht400); its formula goes to PostProcessor(cut=...). "
                             "Not together with --cut. 2024: 6j20 (docs/03_DECISIONS.md D-2026-09-28-volume).")
    parser.add_argument("--audit", action="store_true",
                        help="after the copy, read every input file again with RDataFrame, check the closure "
                             "(C1-C3) and append ForgeAudit / ForgeTTbbKeys / ForgeProvenance to --output-file "
                             "(forge_audit.py). Exit 5 closure FAIL, 85 read trouble, 84 input not openable, 7 audit error.")
    parser.add_argument("--forge-git", type=str, default=None,
                        help="git commit of the submitting checkout, recorded in ForgeProvenance (submit_crab.py)")
    parser.add_argument("--input-fallback", type=str, default=None, metavar="URL",
                        help="an LFN input (/store/...) that cannot be opened at the site is copied from URL + LFN "
                             "with xrdcp into ./forge_aaa/ and read there (URL + LFN directly if the copy fails), "
                             "e.g. root://cms-xrd-global.cern.ch/ (AAA; a job CRAB sent to a site without its input). "
                             "submit_crab.py sets it unless YAML aaa_fallback: false. Default: off, as before.")

    # [3] ttbarCategorizer Options -- DEPRECATED / DEAD
    # ────────────────────────────────────────────────────────────────────
    # These flags control the optional debug behaviour of the
    # TtbarCategorizer module (modules/ttbarCategorizer.py). They are
    # passed to the module via environment variables, which the
    # `make_default_module()` factory reads when constructing the
    # MODULES list at import time.
    #
    # !! THAT MODULE IS NOT IN THIS REPOSITORY (verified 2026-07-27).      !!
    # !! modules/ contains only: noop, topCPVCategorizer, jetsMETcut,     !!
    # !! nanoaod_branch_access. These three flags are therefore accepted   !!
    # !! and silently do nothing. Kept (not removed) so that any external  !!
    # !! caller / old CRAB sandbox passing them does not crash. If the     !!
    # !! module is never restored, delete them together with this block.   !!
    #
    # The categorizer ALWAYS writes both branch sets (`ttCat_*` and
    # `ttCatXval_*`) regardless of these flags. The flags only control
    # the optional CSV dump and the endJob stderr report.
    # ────────────────────────────────────────────────────────────────────
    parser.add_argument(
        "--ttcat-debug-csv",
        action="store_true",
        help="Enable per-event ttbarCategorizer debug CSV. The CSV "
             "duplicates information already in the ntuple branches; "
             "use only for interactive local validation. NOT staged out "
             "by CRAB — do not enable for production jobs."
    )
    parser.add_argument(
        "--ttcat-debug-csv-path",
        type=str,
        default=None,
        help="Output path for the ttcat debug CSV (only effective with "
             "--ttcat-debug-csv). Default: ./ttcat_debug.csv"
    )
    parser.add_argument(
        "--ttcat-quiet",
        action="store_true",
        help="Suppress the ttbarCategorizer endJob stderr report "
             "(source distribution + category counts + confusion matrix)."
    )

    args = parser.parse_args()

    # ────────────────────────────────────────────────────────────────────
    # Pass ttcat options through to the module via environment variables.
    # This is set BEFORE module imports happen below, so make_default_module()
    # sees the updated environment when it constructs the categorizer.
    # ────────────────────────────────────────────────────────────────────
    if args.ttcat_debug_csv:
        os.environ["TTCAT_DEBUG_CSV"] = "1"
        logger.info("ttcat: debug CSV ENABLED")
        if args.ttcat_debug_csv_path:
            os.environ["TTCAT_DEBUG_CSV_PATH"] = args.ttcat_debug_csv_path
            logger.info(f"ttcat: debug CSV path = {args.ttcat_debug_csv_path}")
        else:
            logger.info("ttcat: debug CSV path = ./ttcat_debug.csv (default)")
    elif args.ttcat_debug_csv_path:
        logger.warning(
            "--ttcat-debug-csv-path was given without --ttcat-debug-csv; "
            "the path will be ignored."
        )

    if args.ttcat_quiet:
        os.environ["TTCAT_QUIET"] = "1"
        logger.info("ttcat: endJob report SUPPRESSED")

    # --skim / --audit (forge_skims.py and forge_audit.py are imported only here,
    # so a sandbox without them still runs every older command line)
    skim_name, skim_formula = None, None
    if args.skim is not None or args.audit:
        try:
            import forge_skims
        except ImportError as e:
            logger.error("forge_skims.py is not importable (%s); it must sit next to run_postproc.py" % e)
            sys.exit(2)
        try:
            skim_formula, _rvec = forge_skims.get(args.skim)
        except KeyError as e:
            logger.error(str(e))
            sys.exit(2)
        if skim_formula:
            skim_name = args.skim
        if skim_formula and args.cut:
            logger.error("--skim and --cut exclude each other (production selection vs validation cut)")
            sys.exit(2)
    if args.audit and not args.output_file:
        logger.error("--audit needs --output-file (the audit is appended to the merged output)")
        sys.exit(2)

    # -------------------------------------------------------------------------
    # Hardcoded Configuration (Default Settings)
    # -------------------------------------------------------------------------
    # To avoid argument parsing errors in CRAB, complex settings are managed here.
    # Modify these values directly if needed.
    
    OUTPUT_DIR  = "."         # Output directory (Always current dir for CRAB compatibility)
    # Preselection. Default None = no cut; physics cuts belong in the module's
    # analyze(). --cut exists ONLY for cross-version validation (restricting two
    # runs to a shared lumi set so they can be compared event by event) and is
    # logged loudly below so it can never slip into production unnoticed.
    CUT_STRING  = skim_formula if skim_name else args.cut
    POSTFIX     = "_Skim"     # Suffix for split output mode
    COMPRESSION = "LZMA:9"    # Compression algorithm (Use "LZ4:4" for faster testing)
    FRIEND      = False       # Run in friend tree mode
    NO_OUT      = False       # If True, skip writing output file (for debugging)

    # -------------------------------------------------------------------------
    # Validation & Loading
    # -------------------------------------------------------------------------

    # 1. Validate Branch Selection File
    if os.path.exists(args.branch_selection):
        logger.info(f"Branch Selection File loaded: {args.branch_selection}")
        logger.info(f"  -> Applied to: OUTPUT tree only (input is read in full)")
        # Preview first 3 lines
        try:
            with open(args.branch_selection, 'r') as f:
                head = [next(f).strip() for _ in range(3)]
            logger.info(f"  -> Preview: {head} ...")
        except StopIteration:
            pass
    else:
        logger.error(f"Branch Selection File NOT found: {args.branch_selection}")
        sys.exit(1)

    # 2. Load Modules and Log Details
    active_modules = []
    if args.imports:
        for imp_str in args.imports:
            # Syntax: module_name:list_name (Default list name: 'modules')
            if ':' in imp_str:
                mod_name, list_name = imp_str.split(':')
            else:
                mod_name, list_name = imp_str, 'modules'
            
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, list_name):
                    loaded = getattr(mod, list_name)
                    active_modules.extend(loaded)
                    logger.info(f"Module Loaded: {mod_name} (List Variable: '{list_name}')")
                    
                    # Log internal parameters of loaded modules
                    for idx, m in enumerate(loaded):
                        class_name = m.__class__.__name__
                        logger.info(f"  -> [{idx}] Class: {class_name}")
                        
                        # Inspect and log public attributes (e.g., thresholds)
                        attrs = vars(m)
                        filtered_attrs = {k: v for k, v in attrs.items() if not k.startswith('_')}
                        if filtered_attrs:
                            logger.info(f"     Parameters: {filtered_attrs}")
                else:
                    logger.error(f"Module '{mod_name}' loaded, but list '{list_name}' NOT found.")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"Failed to import module '{mod_name}': {e}")
                sys.exit(1)

    # 3. Validate Input Files
    n_files = len(args.input_files)
    logger.info(f"Input Files Detected: {n_files}")
    if n_files > 0:
        logger.info(f"  -> First file: {args.input_files[0]}")
        if n_files > 1:
            logger.info(f"  -> ... and {n_files - 1} more files.")
    args.input_lfn = {}
    if args.input_fallback:
        # the PostProcessor and the audit both open these names; the audit records args.input_lfn[name]
        args.input_files, args.input_lfn = resolve_inputs(args.input_files, args.input_fallback, logger)

    # 4. Confirm Output Strategy
    if args.output_file:
        logger.info(f"Output Strategy: MERGE (Hadd enabled)")
        logger.info(f"  -> Final Target: {args.output_file}")
    else:
        logger.info(f"Output Strategy: SPLIT (One-to-One)")
        logger.info(f"  -> Suffix: {POSTFIX}")

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------
    logger.info("-" * 60)
    if skim_name:
        logger.info("=" * 60)
        logger.info("EVENT SKIM (production): %s", skim_name)
        logger.info("  cut = %s", CUT_STRING)
        logger.info("  Runs / LuminosityBlocks stay whole; %s", "audit ON (forge_audit.py)" if args.audit
                    else "audit OFF: nothing records the sums of weights before the skim")
        logger.info("=" * 60)
    elif CUT_STRING:
        logger.warning("=" * 60)
        logger.warning("PRESELECTION CUT ACTIVE -- VALIDATION MODE")
        logger.warning("  cut = %s", CUT_STRING)
        logger.warning("  The output event set is a SUBSET of the input. Do NOT use")
        logger.warning("  this output for production or for any yield/normalization.")
        logger.warning("=" * 60)

    logger.info("Initializing PostProcessor engine...")
    
    try:
        p = PostProcessor(
            outputDir=OUTPUT_DIR,
            inputFiles=args.input_files,
            cut=CUT_STRING,
            # ─────────────────────────────────────────────────────────
            # branchsel       = INPUT  tree filter   -> None (= read all)
            # outputbranchsel = OUTPUT tree filter   -> keep/drop file
            #
            # Do NOT pass the keep/drop file as `branchsel`. That would
            # apply `drop *` to the input tree as well and disable
            # GenPart_*/GenJet_*/genTtbarId reads, breaking modules
            # like ttbarCategorizer that need gen-level information.
            # See module docstring of run_postproc.py for full context.
            # ─────────────────────────────────────────────────────────
            branchsel=None,
            outputbranchsel=args.branch_selection,
            modules=active_modules,
            compression=COMPRESSION,
            friend=FRIEND,
            postfix=POSTFIX,
            noOut=NO_OUT,
            justcount=False, # If True, only count events and exit. At the same time, the fwkJobReport variable must be set to False.
            maxEntries=args.max_events,
            firstEntry=args.first_entry,
            haddFileName=args.output_file, # Triggers merge if not None
            provenance=True, # Save provenance metadata in the output file
            fwkJobReport=True, # Set "True" for CRAB job
        )
        
        if args.audit:
            import ROOT
            import forge_audit
            logger.info("Running Event Loop, then the forge audit...")
            try:
                code = forge_audit.run_job(ROOT, args, p.run, logger)
            except Exception:
                logger.exception("forge audit crashed outside its own checks")
                code = forge_audit.EXIT_AUDIT
            end_time = datetime.datetime.now()
            logger.info("%s at %s (exit %d)", "Job Finished Successfully" if code == 0 else "Job FAILED",
                        end_time.strftime('%Y-%m-%d %H:%M:%S'), code)
            logger.info("   Total Runtime: %s", end_time - start_time)
            sys.stdout.flush()
            sys.stderr.flush()
            forge_audit.c_flush()
            os._exit(code)   # no PyROOT teardown after the RDataFrame work (size_options.py v1 crashed in one)

        logger.info("Running Event Loop...")
        p.run()
        
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        logger.info(f"✅ Job Finished Successfully at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Total Runtime: {duration}")
        
    except Exception as e:
        logger.exception("❌ Critical Error during PostProcessor execution.")
        sys.exit(1)

if __name__ == "__main__":
    main()
