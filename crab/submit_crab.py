import os
import sys
import argparse
import time
from CRABClient.UserUtilities import config

def submit(args):
    # 1. Initialize CRAB Config
    conf = config()
    
    conf.General.requestName = args.name
    conf.General.transferOutputs = True
    conf.General.transferLogs = True
    conf.General.workArea = args.work_area

    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py' # Dummy PSet
    conf.JobType.scriptExe = 'crab/crab_script.sh' # Main executable
    
    # Files to send to the grid
    # We must include the scripts, configs, and python folders
    conf.JobType.inputFiles = [
        'scripts/run_postproc.py', 
        'python/utils/env_check.py',
        'python/__init__.py', # Ensure python dir is treated as package
        # Add your config files here dynamically or hardcode
        args.branch_sel,
    ]
    # Add module file if separate
    if args.module_file:
         conf.JobType.inputFiles.append(args.module_file)

    # Arguments passed to crab_script.sh -> run_postproc.py
    # We pass the rest of the flags: cut, branch-selection, etc.
    script_args = []
    if args.cut:
        script_args.append(f'-c={args.cut}') # Use = syntax to avoid parsing issues in shell
    if args.branch_sel:
        # We use os.path.basename because the file will be in the cwd of the worker
        script_args.append(f'-b={os.path.basename(args.branch_sel)}')
    if args.imports:
        script_args.append(f'-I={" ".join(args.imports)}')

    conf.JobType.scriptArgs = script_args
    
    # Parallelism
    conf.JobType.maxMemoryMB = 2500
    conf.JobType.maxJobRuntimeMin = 600

    conf.Data.inputDBS = 'global'
    conf.Data.splitting = 'FileBased'
    conf.Data.unitsPerJob = args.units_per_job
    conf.Data.publication = False # Usually False for private skims
    conf.Data.outputDatasetTag = args.name

    conf.Site.storageSite = args.site
    
    # 2. Loop over datasets
    with open(args.sample_list, 'r') as f:
        datasets = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Found {len(datasets)} datasets to submit.")
    
    from CRABAPI.RawCommand import crabCommand
    from httplib import HTTPException

    for dataset in datasets:
        # Create unique request name per dataset
        # /Primary/Secondary/Tier -> Primary_Secondary
        ds_parts = dataset.split('/')
        if len(ds_parts) >= 3:
            req_name = f"{args.name}_{ds_parts[1]}_{ds_parts[2]}"
        else:
            req_name = f"{args.name}_{dataset.replace('/', '_')}"
            
        # Shorten name if too long (CRAB limit ~100 chars)
        req_name = req_name[:95]
        
        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        
        print(f"Submitting: {req_name}")
        try:
            crabCommand('submit', config = conf)
        except HTTPException as hte:
            print(f"Failed submitting task: {hte.headers}")
        except Exception as e:
            print(f"Failed submitting task: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Submit NtupleForge Jobs to CRAB")
    parser.add_argument("--name", required=True, help="Campaign Name (e.g., Run2018_Skim_v1)")
    parser.add_argument("--sample-list", required=True, help="Text file with list of datasets")
    parser.add_argument("--site", required=True, help="T2/T3 Storage Site (e.g., T3_KR_KNU)")
    parser.add_argument("--work-area", default="crab_projects", help="Local working directory")
    
    # PostProc Args
    parser.add_argument("--cut", help="Cut string")
    parser.add_argument("--branch-sel", help="Branch selection file path")
    parser.add_argument("--module-file", help="Python file containing the module definition")
    parser.add_argument("--imports", nargs="+", help="Module imports (e.g. configs.modules_cut_basic)")
    parser.add_argument("--units-per-job", type=int, default=1, help="Files per job")

    args = parser.parse_args()
    
    # Simple check
    if not os.path.exists(args.sample_list):
        print(f"Error: Sample list {args.sample_list} not found.")
        sys.exit(1)

    submit(args)
