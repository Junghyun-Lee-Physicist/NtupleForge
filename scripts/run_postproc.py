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
            # Ignore comments and empty lines
            if s and not s.startswith("#"):
                paths.append(s)
    return paths

# -------------------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="NtupleForge: NanoAOD Post-Processing Framework")
    
    # --- IO Specifications ---
    parser.add_argument("output_dir", type=str, help="Output directory")
    parser.add_argument("input_files", type=str, nargs="+", help="Input ROOT files or .txt file lists")
    parser.add_argument("--output-file", type=str, default=None, help="Merge into this filename (hadd)")
    
    # --- Selection ---
    parser.add_argument("-c", "--cut", type=str, default=None, help="TTree cut string")
    parser.add_argument("-b", "--branch-selection", type=str, default=None, help="Branch selection file path")
    
    # --- Module Imports ---
    parser.add_argument("-I", "--imports", type=str, nargs="+", 
                        help="Modules to import. Syntax: 'pkg.mod' (implies 'modules') or 'pkg.mod:ListName'")
    
    # --- Control ---
    parser.add_argument("-N", "--max-events", type=int, default=None, help="Max events to process")
    parser.add_argument("--first-entry", type=int, default=0, help="First entry index")
    parser.add_argument("--postfix", type=str, default="_Skim", help="Output filename postfix")
    parser.add_argument("--friend", action="store_true", help="Friend tree mode")
    parser.add_argument("--no-out", action="store_true", help="Skip writing output file")
    parser.add_argument("--just-count", action="store_true", help="Count events only")
    parser.add_argument("--compression", type=str, default="LZMA:9", help="Compression settings")

    args = parser.parse_args()

    # 1. Input Parsing
    logger.info("Step 1: Parsing input files...")
    final_input_files = []
    
    try:
        for f in args.input_files:
            if f.endswith(".txt"):
                logger.info(f"Expanding file list: {f}")
                final_input_files.extend(read_input_list(f))
            elif f.startswith("/"):
                # Safety check for Dataset names vs File paths
                # If a user provides a dataset name like /A/B/C instead of a file path, we warn them.
                if f.count('/') == 3 and not f.endswith('.root'):
                    logger.warning(f"Input '{f}' looks like a Dataset Name, NOT a file path.")
                    logger.warning("Local skimming requires physical file paths (root://... or /local/path/).")
            else:
                final_input_files.append(f)
                
        # Ensure we found files
        if not final_input_files:
            logger.error("No valid input files found. Exiting.")
            sys.exit(1)
            
    except Exception as e:
        logger.exception("Failed during input parsing.")
        sys.exit(1)

    # 2. Module Loading
    logger.info("Step 2: Loading modules...")
    active_modules = []
    
    if args.imports:
        for imp_str in args.imports:
            try:
                # Syntax Check: module:ListName
                if ':' in imp_str:
                    mod_name, list_name = imp_str.split(':')
                else:
                    mod_name, list_name = imp_str, 'modules'
                
                logger.info(f"Importing '{mod_name}' looking for '{list_name}'...")
                mod = importlib.import_module(mod_name)
                
                if hasattr(mod, list_name):
                    loaded_list = getattr(mod, list_name)
                    if isinstance(loaded_list, list):
                        active_modules.extend(loaded_list)
                        logger.info(f" -> Successfully loaded {len(loaded_list)} modules from {mod_name}")
                    else:
                        logger.error(f"'{list_name}' in {mod_name} is not a list!")
                        sys.exit(1)
                else:
                    logger.error(f"Module '{mod_name}' found, but variable '{list_name}' is missing.")
                    sys.exit(1)
                    
            except ImportError as e:
                logger.exception(f"Failed to import python module: {mod_name}")
                sys.exit(1)
            except Exception as e:
                logger.exception(f"Unexpected error loading module: {imp_str}")
                sys.exit(1)

    # 3. Setup PostProcessor
    logger.info("Step 3: Configuring PostProcessor...")
    logger.info(f"  - Output Dir: {args.output_dir}")
    logger.info(f"  - Input Files: {len(final_input_files)}")
    logger.info(f"  - Cut: {args.cut}")
    logger.info(f"  - Active Modules: {len(active_modules)}")
    
    try:
        # Check output dir permission/existence
        if not os.path.exists(args.output_dir):
            pass # PostProcessor will create it, but we could check write permissions here if we wanted strictness

        branchsel = args.branch_selection
        if branchsel and not os.path.exists(branchsel):
            logger.error(f"Branch selection file not found: {branchsel}")
            sys.exit(1)

        p = PostProcessor(
            outputDir=args.output_dir,
            inputFiles=final_input_files,
            cut=args.cut,
            branchsel=branchsel,
            outputbranchsel=branchsel,
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
    except Exception as e:
        logger.exception("Failed to initialize PostProcessor.")
        sys.exit(1)

    # 4. Execution
    logger.info("Step 4: Running Event Loop...")
    try:
        p.run()
        logger.info("✅ Processing completed successfully.")
    except Exception as e:
        logger.exception("❌ Critical error during event processing.")
        sys.exit(1)

if __name__ == "__main__":
    main()
