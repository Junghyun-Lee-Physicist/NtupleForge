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
    python3 scripts/run_postproc.py input1.root input2.root \
        -b branches/branch_keep_and_drop.txt \
        -I modules.jetsMETcut:MODULES

    # 2. Merge Mode (Hadd multiple inputs into one output)
    python3 scripts/run_postproc.py input*.root \
        -b branches/branch_keep_and_drop.txt \
        -I modules.jetsMETcut:MODULES \
        --output-file merged_skim.root

Author: Junghyun Lee (NtupleForge)
"""

import os
import sys
import argparse
import importlib
import logging
import datetime
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
                        help="Path to branch selection file (keep/drop rules)")

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

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Hardcoded Configuration (Default Settings)
    # -------------------------------------------------------------------------
    # To avoid argument parsing errors in CRAB, complex settings are managed here.
    # Modify these values directly if needed.
    
    OUTPUT_DIR  = "."         # Output directory (Always current dir for CRAB compatibility)
    CUT_STRING  = None        # Recommended: Apply cuts inside the module's analyze() function
    POSTFIX     = "_Skim"     # Suffix for split output mode
    COMPRESSION = "LZMA:9"    # Compression algorithm (Use "LZ4:4" for faster testing)
    FRIEND      = False       # Run in friend tree mode
    NO_OUT      = False       # If True, skip writing output file (for debugging)
    JUST_COUNT  = False       # If True, only count events and exit

    # -------------------------------------------------------------------------
    # Validation & Loading
    # -------------------------------------------------------------------------

    # 1. Validate Branch Selection File
    if os.path.exists(args.branch_selection):
        logger.info(f"Branch Selection File loaded: {args.branch_selection}")
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
    logger.info("Initializing PostProcessor engine...")
    
    try:
        p = PostProcessor(
            outputDir=OUTPUT_DIR,
            inputFiles=args.input_files,
            cut=CUT_STRING,
            branchsel=args.branch_selection,
            outputbranchsel=args.branch_selection,
            modules=active_modules,
            compression=COMPRESSION,
            friend=FRIEND,
            postfix=POSTFIX,
            noOut=NO_OUT,
            justcount=JUST_COUNT,
            maxEntries=args.max_events,
            firstEntry=args.first_entry,
            haddFileName=args.output_file, # Triggers merge if not None
            provenance=True, # Save provenance metadata in the output file
            fwkJobReport=True, # Set "True" for CRAB job
        )
        
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
