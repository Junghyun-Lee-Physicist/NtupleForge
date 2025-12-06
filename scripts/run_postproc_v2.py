#!/usr/bin/env python3
import os
import sys
import argparse
import importlib
from PhysicsTools.NanoAODTools.postprocessing.framework.postprocessor import PostProcessor

# Add the python directory to sys.path to allow importing internal modules
# Assuming this script is in NtupleForge/scripts/ and we want to import from NtupleForge/python/
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)
sys.path.append(os.path.join(base_dir, 'python'))

# Import custom environment checker
try:
    from utils.env_check import validate_environment
except ImportError:
    # Fallback if running directly without strict package structure
    print("Warning: Could not import utils.env_check. Skipping checks.")
    def validate_environment(): pass
    sys.exit()

def main():
    parser = argparse.ArgumentParser(description="NtupleForge: NanoAOD Post-Processing Framework")
    parser.add_argument("output_dir", type=str, help="Output directory")
    parser.add_argument("input_files", type=str, nargs="+", help="Input files (local or root://)")
    parser.add_argument("-c", "--cut", type=str, default=None, help="Cut string (e.g., 'nMuon>1')")
    parser.add_argument("-b", "--branch-selection", type=str, default=None, help="Path to branch selection file (keep_and_drop.txt)")
    parser.add_argument("-I", "--imports", type=str, nargs="+", help="Modules to import (e.g., configs.modules_cut_basic myConstructor)")
    parser.add_argument("--friend", action="store_true", help="Run in friend mode")
    parser.add_argument("--no-check", action="store_true", help="Skip environment checks")

    args = parser.parse_args()

    # 1. Environment Check
    if not args.no_check:
        validate_environment()

    # 2. Dynamic Module Loading
    modules = []
    if args.imports:
        # Expected format: module_path constructor_name [args...]
        # Example: configs.modules_cut_basic constructor
        # If user provides just: configs.modules_noop (assumes constructor is 'constructor' or similar?) 
        # NanoAODTools standard: -I <python_module_name> <function_name>
        
        # Let's handle the list of imports.
        # The argparse nargs='+' puts everything in a list. We need to parse pairs or groups.
        # Implementation note: For simplicity, let's assume one module for now or handle standard string parsing.
        # But here, we follow the provided simpler logic: Load user defined modules.
        
        # Simple parsing logic for: -I configs.modules_cut_basic
        # We assume the file has a list named 'modules' or a function returning it, 
        # or we instantiate the class specified.
        
        # Refined Logic based on typical usage:
        # python scripts/run_postproc.py ... -I configs.modules_cut_basic
        
        for imp_str in args.imports:
            # Try to import the module path
            try:
                mod = importlib.import_module(imp_str)
                # Look for a variable named 'modules' inside that file
                if hasattr(mod, 'modules'):
                    modules.extend(mod.modules)
                    print(f"[INFO] Loaded modules from {imp_str}")
                else:
                    print(f"[WARNING] Module {imp_str} loaded but no 'modules' list found.")
            except ImportError as e:
                print(f"[ERROR] Could not import {imp_str}: {e}")
                sys.exit(1)

    # 3. Setup PostProcessor
    print(f"[INFO] Input Files: {len(args.input_files)} files detected.")
    print(f"[INFO] Output Directory: {args.output_dir}")
    print(f"[INFO] Cut: {args.cut}")
    print(f"[INFO] Branch Selection: {args.branch_selection}")
    print(f"[INFO] Active Modules: {len(modules)}")

    p = PostProcessor(
        args.output_dir,
        args.input_files,
        cut=args.cut,
        branchsel=args.branch_selection,
        outputbranchsel=args.branch_selection, # Usually same for skim/slim
        modules=modules,
        friend=args.friend,
        provenance=True,
        fwkJobReport=True # Useful for CRAB
    )

    # 4. Run
    p.run()
    print("[INFO] Processing completed successfully.")

if __name__ == "__main__":
    main()
