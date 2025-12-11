#!/usr/bin/env python3
"""
NtupleForge CRAB Manager
=============================
[Description]
Reads a YAML configuration file and manages CRAB jobs (Submit, Status, Resubmit).
Uses 'crab/crab_script.py' as the worker node wrapper.

[Usage]
python3 crab/submit_crab.py --config crabConfig/campaign_ttbar_SemiLeptonic_v1.yaml
python3 crab/submit_crab.py --config crabConfig/campaign_ttbar_SemiLeptonic_v1.yaml --status
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
    conf.General.workArea = common.get('jobID', 'crab_projects_default_name')
    
    # -- JobType --
    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py'
    
    # [KEY] Use the separated Python wrapper
    conf.JobType.scriptExe = 'crab/crab_script.py' 
    
    conf.JobType.maxMemoryMB = common.get('max_memory', 2500)
    conf.JobType.maxJobRuntimeMin = common.get('max_runtime', 600)
    
    # Files to ship to worker node
    # Note: We ship 'scripts/run_postproc.py' explicitly.
    # CRAB will flatten directory structure, placing it in root dir on worker.
    conf.JobType.inputFiles = ['scripts/run_postproc.py']
    
    if os.path.exists('modules'): conf.JobType.inputFiles.append('modules')
    if os.path.exists('branches'): conf.JobType.inputFiles.append('branches')
    
    # Explicit branch selection file if not in 'branches/'
    branch_sel = common.get('branch_selection')
    if branch_sel and 'branches' not in branch_sel:
         conf.JobType.inputFiles.append(branch_sel)

    # -- Arguments File Generation --
    # To avoid HTTP 400 errors, we write arguments to a file and ship it.
    args_file = "crab_args.txt"
    with open(args_file, "w") as f:
        if branch_sel: f.write(f"-b\n{os.path.basename(branch_sel)}\n")
        if common.get('module'): f.write(f"-I\n{common.get('module')}\n")
        if common.get('max_events'): f.write(f"-N\n{common.get('max_events')}\n")
        # Note: Output filename is enforced in wrapper to 'tree.root' for merging
    
    conf.JobType.inputFiles.append(args_file)
    conf.JobType.scriptArgs = [] # Empty to rely on file injection

    # -- Data & Site --
    conf.Data.inputDBS = 'global'
    conf.Data.splitting = common.get('splitting', 'EventAwareLumiBased')
    conf.Data.unitsPerJob = common.get('units_per_job', 50000)
    conf.Data.publication = False
    
    username = getUsername()
    base_out = common.get('output_base', f'/store/user/{username}/')
    conf.Data.outLFNDirBase = base_out
    
    conf.Site.storageSite = common.get('site', 'T3_KR_KNU')

    # 3. Process Jobs
    for short_name, dataset in datasets.items():
        # Clean request name
        campaign_name = os.path.splitext(os.path.basename(args.config))[0]
        req_name = f"{campaign_name}_{short_name}"
        req_name = req_name.replace("-", "_")[:95]
        
        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        conf.Data.outputDatasetTag = short_name
        
        project_dir = os.path.join(conf.General.workArea, "crab_" + req_name)
        
        print(f"[{short_name}]")
        print(f"Dataset: {dataset}")

        # -- STATUS Check --
        if args.status:
            if os.path.isdir(project_dir):
                logger.info("Action: Checking STATUS")
                try:
                    subprocess.run(["crab", "status", "-d", project_dir], check=True)
                except:
                    logger.error("Status check failed.")
            else:
                logger.warning("Project directory not found. Not submitted yet.")
            print("-" * 60)
            continue

        # -- SUBMIT / RESUBMIT Logic --
        if os.path.isdir(project_dir):
            logger.info(f"Project exists at {project_dir}")
            logger.info("Action: RESUBMIT")
            try:
                crabCommand('resubmit', dir=project_dir)
            except HTTPException as hte:
                logger.error(f"Resubmit Failed: {hte.headers}")
            except Exception as e:
                logger.error(f"Resubmit Failed: {e}")
        else:
            logger.info("New Project. Action: SUBMIT")
            try:
                crabCommand('submit', config=conf)
            except HTTPException as hte:
                logger.error(f"Submit Failed: {hte.headers}")
            except Exception as e:
                logger.error(f"Submit Failed: {e}")
        
        print("-" * 60)

    # Cleanup temp file
    if os.path.exists(args_file):
        os.remove(args_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YAML based CRAB Manager")
    parser.add_argument("-c", "--config", required=True, help="Path to YAML config")
    parser.add_argument("--status", action="store_true", help="Check status instead of submit")
    
    args = parser.parse_args()
    main(args)
