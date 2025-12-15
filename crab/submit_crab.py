#!/usr/bin/env python3
"""
NtupleForge CRAB Manager
=============================
[Description]
Reads a YAML configuration file and manages CRAB jobs (Submit, Status, Resubmit).
Uses 'crab/crab_script.py' as the worker node wrapper.

[Usage]
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --status
python3 crab/submit_crab.py --config crabConfig/config_crabTest.yaml --kill
"""

import os
import sys
import argparse
import yaml
import shutil
import logging
import subprocess
from CRABClient.UserUtilities import config, getUsername
from CRABAPI.RawCommand import crabCommand

try:
    from http.client import HTTPException
except ImportError:
    from httplib import HTTPException

# Logging Setup
logging.basicConfig(level=logging.INFO, format='[submit_crab] : %(message)s')
logger = logging.getLogger("Submitter")

def check_voms():
    """Checks if VOMS proxy is valid."""
    try:
        subprocess.run(["voms-proxy-info", "--exists"], check=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        logger.error("VOMS Proxy missing or expired.")
        logger.error("Run: voms-proxy-init --voms cms --valid 168:00")
        sys.exit(1)

def main(args):
    check_voms()

    # 1. Load Configuration
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)

    with open(args.config, 'r') as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(f"YAML Error: {e}")
            sys.exit(1)

    common = cfg.get('common', {})
    datasets = cfg.get('datasets', {})
    
    logger.info(f"Loaded Configuration: {args.config}")
    logger.info(f"Common Work Area: {common.get('jobID', 'crab_projects')}")
    logger.info(f"Target Datasets: {len(datasets)}")
    logger.info("="*60)

    # 2. Setup CRAB Configuration
    conf = config()
    
    # -- General --
    conf.General.transferOutputs = True
    conf.General.transferLogs = True
    conf.General.workArea = common.get('jobID', 'crab_projects')
    
    # -- JobType --
    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py'
    conf.JobType.scriptExe = 'crab/crab_script.py' 
    conf.JobType.maxMemoryMB = common.get('max_memory', 2500)
    
    splitting_mode = common.get('splitting', 'Automatic')
    if splitting_mode != 'Automatic':
        conf.JobType.maxJobRuntimeMin = common.get('max_runtime', 600)


    # ------------------------------------------------------
    # Input Filename Logic
    # ------------------------------------------------------
    # Files to ship to worker node
    # CRAB will flatten directory structure, placing it in root dir on worker.
    conf.JobType.inputFiles = ['scripts/run_postproc.py'] # Main Script

    # ------------------------------------------------------
    # Module Handling (List-based YAML)
    # ------------------------------------------------------
    # YAML Format: analysis_module: ["modules/jetsMETcut.py", "MODULES"]
    
    module_cfg = common.get('analysis_module') # Returns a list: [path, list_name]
    worker_module_arg = None # Will store string "jetsMETcut:MODULES" for worker

    if module_cfg and len(module_cfg) == 2:
        local_path = module_cfg[0]  # e.g., "modules/jetsMETcut.py"
        list_var   = module_cfg[1]  # e.g., "MODULES"

        if os.path.exists(local_path):
            conf.JobType.inputFiles.append(local_path)
            logger.info(f"Adding Module File: {local_path}")
            
            # Prepare Argument for Worker Node
            # Worker sees flat files. "modules/jetsMETcut.py" -> "jetsMETcut.py"
            # Argument format: "jetsMETcut:MODULES" (drop extension, append list var)
            file_basename = os.path.basename(local_path) # jetsMETcut.py
            module_name_only = os.path.splitext(file_basename)[0] # jetsMETcut
            worker_module_arg = f"{module_name_only}:{list_var}"
            
        else:
            logger.error(f"CRITICAL: Module file not found at {local_path}")
            sys.exit(1)
    elif module_cfg:
        logger.error(f"YAML Error: 'analysis_module' must be a list with 2 elements [path, list_name]. Got: {module_cfg}")
        sys.exit(1)

    # ------------------------------------------------------
    # Branch File Handling
    # ------------------------------------------------------
    branch_sel = common.get('branch_file') # Renamed from branch_path
    
    if branch_sel:
        if os.path.exists(branch_sel):
            conf.JobType.inputFiles.append(branch_sel)
            logger.info(f"Adding Branch File: {branch_sel}")
        else:
            logger.error(f"CRITICAL: Branch file not found at {branch_sel}")
            sys.exit(1)
            
    # Add YAML Config (Provenance)
    conf.JobType.inputFiles.append(args.config)


    # ------------------------------------------------------
    # Output Filename Logic
    # ------------------------------------------------------
    # Get output filename from YAML or default to 'tree.root'
    out_name = common.get('output_filename', 'tree.root')
    if not out_name:
        out_name = 'tree.root'


    # -- Arguments File Generation --
    args_file = "crab_args.txt"
    with open(args_file, "w") as f:
        # Branch Arg
        if branch_sel: 
            f.write(f"-b\n{os.path.basename(branch_sel)}\n")
        
        # Module Arg (Optimized)
        if worker_module_arg: 
            f.write(f"-I\n{worker_module_arg}\n")
            
        if common.get('max_events'): 
            f.write(f"-N\n{common.get('max_events')}\n")

        # Pass the output filename to the worker node script
        f.write(f"--output-file={out_name}\n")

    conf.JobType.inputFiles.append(args_file)
    conf.JobType.scriptArgs = [] 

    # ------------------------------------------------------
    # Output Files Configuration (Provenance)
    # ------------------------------------------------------
    # Instruct CRAB to transfer these files back to the output storage.
    # 1. out_name: Main output file
    # 2. crab_args.txt: List of arguments used for the job
    # 3. YAML Config: The configuration file used for submission
    conf.JobType.outputFiles = [
        out_name,            
        'crab_args.txt',
        os.path.basename(args.config)
    ]

    # -- Data & Site --
    conf.Data.inputDBS = 'global'
    
    # [FIX] Splitting Logic (Automatic vs FileBased)
    conf.Data.splitting = splitting_mode
    
    # units_per_job means different things:
    # Automatic -> Minutes (e.g., 180)
    # FileBased -> Number of Files (e.g., 1)
    user_units = common.get('units_per_job', 180) # Default 180 mins
    
    conf.Data.unitsPerJob = user_units
    conf.Data.publication = False

    username = getUsername()
    base_out = common.get('output_base', '')
    if base_out:
         conf.Data.outLFNDirBase = f'/store/user/{username}/{base_out.lstrip("/")}'
    else:
         conf.Data.outLFNDirBase = f'/store/user/{username}/'

    conf.Site.storageSite = common.get('site', 'T3_KR_KNU')

    # 3. Process Jobs
    for short_name, dataset in datasets.items():
        req_name = short_name.replace("-", "_")

        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        conf.Data.outputDatasetTag = short_name

        project_dir = os.path.join(conf.General.workArea, "crab_" + req_name)

        print(f"[{short_name}] Processing...")

        # -- STATUS Action --
        if args.status:
            if os.path.isdir(project_dir):
                try:
                    subprocess.run(["crab", "status", "-d", project_dir], check=True)
                except: pass
            else:
                logger.warning("Project not found.")
            continue

        # -- SUBMIT / RESUBMIT Logic --
        if os.path.isdir(project_dir):
            logger.info("Resubmitting...")
            try:
                crabCommand('resubmit', dir=project_dir)
            except Exception as e:
                logger.error(f"Resubmit Failed: {e}")
        else:
            logger.info("Submitting...")
            try:
                crabCommand('submit', config=conf)
            except Exception as e:
                logger.error(f"Submit Failed: {e}")

        # -- KILL Action --
        if args.kill:
            if os.path.isdir(project_dir):
                logger.info("Action: KILLING Task")
                try:
                    crabCommand('kill', dir=project_dir)
                    logger.info("Kill command sent successfully.")
                except HTTPException as hte:
                    logger.error(f"Kill Failed: {hte.headers}")
                except Exception as e:
                    logger.error(f"Kill Failed: {e}")
            else:
                logger.warning(f"Project directory not found (nothing to kill): {project_dir}")
            print("-" * 60)
            continue

    # Cleanup temp file
    if os.path.exists(args_file):
        os.remove(args_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YAML based CRAB Manager")
    parser.add_argument("-c", "--config", required=True, help="Path to YAML config")
    parser.add_argument("--status", action="store_true", help="Check status")
    parser.add_argument("--kill", action="store_true", help="Kill all jobs defined in the config")
    args = parser.parse_args()
    main(args)    

