#!/usr/bin/env python3
import os
import sys
import argparse
import importlib
import logging
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor

# -------------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("NtupleForge")

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def read_input_list(list_path):
    """Reads a text file containing a list of ROOT files."""
    paths = []
    if not os.path.exists(list_path):
        logger.error(f"Input list file not found: {list_path}")
        sys.exit(1)
        
    with open(list_path) as f:
        for line in f:
            s = line.strip()
            if s and not s.startswith("#"):
                paths.append(s)
    return paths

# -------------------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------------------
def main():
    # Enable fromfile_prefix_chars='@' to read arguments from file (CRAB safe)
    parser = argparse.ArgumentParser(
        description="NtupleForge: NanoAOD Post-Processing Framework",
        fromfile_prefix_chars='@'
    )
    
    # --- IO ---
    parser.add_argument("output_dir", type=str, help="Output directory")
    parser.add_argument("input_files", type=str, nargs="+", help="Input ROOT files or .txt lists")
    parser.add_argument("--output-file", type=str, default=None, help="Output filename (triggers hadd)")
    
    # --- Selection ---
    parser.add_argument("-c", "--cut", type=str, default=None, help="TTree cut string")
    parser.add_argument("-b", "--branch-selection", type=str, default=None, help="Branch selection file")
    
    # --- Modules ---
    parser.add_argument("-I", "--imports", type=str, nargs="+", help="Modules to import")
    
    # --- Control ---
    parser.add_argument("-N", "--max-events", type=int, default=None, help="Max events")
    parser.add_argument("--first-entry", type=int, default=0, help="First entry")
    parser.add_argument("--postfix", type=str, default="_Skim", help="Postfix")
    parser.add_argument("--friend", action="store_true", help="Friend mode")
    parser.add_argument("--no-out", action="store_true", help="No output")
    parser.add_argument("--just-count", action="store_true", help="Count only")
    parser.add_argument("--compression", type=str, default="LZMA:9", help="Compression")
    parser.add_argument("--no-check", action="store_true", help="Skip checks")

    args = parser.parse_args()

    # [DEBUGGING] Log received arguments to ensure CRAB passed them correctly
    logger.info("="*50)
    logger.info(f"Command Line Arguments Received:")
    for arg, value in vars(args).items():
        logger.info(f"  {arg:15s}: {value}")
    logger.info("="*50)

    # 1. Parse Inputs
    final_input_files = []
    try:
        for f in args.input_files:
            if f.endswith(".txt"):
                final_input_files.extend(read_input_list(f))
            else:
                final_input_files.append(f)
                
        if not final_input_files:
            logger.error("No input files found.")
            sys.exit(1)
    except Exception as e:
        logger.exception("Input parsing failed.")
        sys.exit(1)

    # 2. Load Modules (Strict)
    active_modules = []
    if args.imports:
        for imp_str in args.imports:
            if ':' in imp_str:
                mod_name, list_name = imp_str.split(':')
            else:
                mod_name, list_name = imp_str, 'modules'
            
            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, list_name):
                    active_modules.extend(getattr(mod, list_name))
                    logger.info(f"Loaded '{list_name}' from {mod_name}")
                else:
                    logger.error(f"List '{list_name}' not found in {mod_name}")
                    sys.exit(1)
            except ImportError as e:
                logger.error(f"Failed to import {mod_name}: {e}")
                sys.exit(1)

    # 3. Initialize & Run
    logger.info(f"Starting PostProcessor with {len(active_modules)} modules...")
    
    try:
        p = PostProcessor(
            outputDir=args.output_dir,
            inputFiles=final_input_files,
            cut=args.cut,
            branchsel=args.branch_selection,
            outputbranchsel=args.branch_selection,
            modules=active_modules,
            compression=args.compression,
            friend=args.friend,
            postfix=args.postfix,
            noOut=args.no_out,
            justcount=args.just_count,
            maxEntries=args.max_events,
            firstEntry=args.first_entry,
            haddFileName=args.output_file,
            provenance=True,
            fwkJobReport=True
        )
        p.run()
        logger.info("✅ Job Completed Successfully.")
        
    except Exception as e:
        logger.exception("❌ Critical Error in PostProcessor.")
        sys.exit(1)

if __name__ == "__main__":
    main()
