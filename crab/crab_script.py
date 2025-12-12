#!/usr/bin/env python3
"""
NtupleForge CRAB Wrapper
=============================
This script runs on the worker node.
It prepares the environment and executes 'run_postproc.py'.
"""

import os
import sys
import subprocess
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO, format='[crab_script] : %(message)s')
logger = logging.getLogger("Wrapper")

def main():
    logger.info("="*60)
    logger.info(f"Wrapper Started on Host: {os.uname().nodename}")
    logger.info(f"Current Directory: {os.getcwd()}")
    logger.info("="*60)

    # ------------------------------------------------------------------
    # 1. Environment Setup
    # ------------------------------------------------------------------
    # CRAB flattens input files. We must add PWD to PYTHONPATH.
    cwd = os.getcwd()
    if "PYTHONPATH" in os.environ:
        os.environ["PYTHONPATH"] = f"{cwd}:{os.environ['PYTHONPATH']}"
    else:
        os.environ["PYTHONPATH"] = cwd
    
    # Also attempt to add 'scripts' if it exists (though usually flattened)
    if os.path.exists("scripts"):
        os.environ["PYTHONPATH"] = f"{cwd}/scripts:{os.environ['PYTHONPATH']}"

    logger.info(f"PYTHONPATH set to: {os.environ['PYTHONPATH']}")

    # ------------------------------------------------------------------
    # 2. Parse Arguments from CRAB Wrapper
    # ------------------------------------------------------------------
    # CRAB passes: <JobReport.xml> <InputFile1> <InputFile2> ...
    if len(sys.argv) < 2:
        logger.error("No arguments received from CRAB.")
        sys.exit(1)

    # First arg is JobReport (Ignored here, managed by PostProcessor FWK report)
    job_report = sys.argv[1] 
    
    # Filter input ROOT files
    input_files = []
    for arg in sys.argv[2:]:
        if arg.endswith('.root'):
            input_files.append(arg)
        elif arg.endswith('.xml'):
            pass 
        else:
            logger.warning(f"Unknown argument ignored: {arg}")

    logger.info(f"Input Files ({len(input_files)}): {input_files}")

    # ------------------------------------------------------------------
    # 3. Locate Main Script
    # ------------------------------------------------------------------
    script_name = "run_postproc.py"
    main_script = None

    if os.path.exists(script_name):
        main_script = script_name
        logger.info(f"Found main script in PWD: {main_script}")
    elif os.path.exists(f"scripts/{script_name}"):
        main_script = f"scripts/{script_name}"
        logger.info(f"Found main script in subfolder: {main_script}")
    else:
        logger.error(f"CRITICAL: {script_name} not found!")
        subprocess.run(["ls", "-R"])
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Inject User Arguments
    # ------------------------------------------------------------------
    # We look for 'crab_args.txt' which contains -b, -I, etc.
    args_file = "crab_args.txt"
    extra_flags = []

    if os.path.exists(args_file):
        logger.info(f"Loading arguments from {args_file}")
        try:
            with open(args_file, "r") as f:
                # Read lines, strip whitespace, and ignore empty lines
                for line in f:
                    clean_line = line.strip()
                    if clean_line:
                        extra_flags.append(clean_line)
        except Exception as e:
            logger.error(f"Failed to read args file: {e}")
            sys.exit(1)
            
        # [Output Policy] Enforce merging into 'tree.root'
        extra_flags.append("--output-file=tree.root")
    else:
        logger.warning(f"{args_file} not found. Running with defaults.")


    # ------------------------------------------------------------------
    # 5. Execution
    # ------------------------------------------------------------------
    # Syntax: python3 run_postproc.py . [inputs] [flags] --no-check
    cmd = [sys.executable, main_script, "."] + input_files + extra_flags + ["--no-check"]
    
    logger.info("-" * 60)
    logger.info(f"Command: {' '.join(cmd)}")
    logger.info("-" * 60)

    try:
        # Flush buffers to ensure logs appear in order
        sys.stdout.flush()
        subprocess.run(cmd, check=True)
        logger.info("✅ Post-processing completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Execution failed with exit code {e.returncode}")
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()
