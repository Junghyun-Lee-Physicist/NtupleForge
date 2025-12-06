import os
import argparse
from CRABClient.UserUtilities import config

def submit(args):
    conf = config()
    
    # --- General ---
    conf.General.requestName = args.name
    conf.General.transferOutputs = True
    conf.General.transferLogs = True # Important for debugging
    conf.General.workArea = args.work_area

    # --- JobType ---
    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py' 
    conf.JobType.scriptExe = 'crab/crab_script.sh' 
    
    # --------------------------------------------------------
    # Files to send to Grid
    # --------------------------------------------------------
    # We send the structure: scripts/, modules/, branches/
    conf.JobType.inputFiles = [
        'scripts/run_postproc.py', 
    ]
    
    # Automatically ship 'modules' folder if it exists
    if os.path.exists('modules'):
        conf.JobType.inputFiles.append('modules')
        
    # Ship branch selection file specifically
    if args.branch_sel:
        conf.JobType.inputFiles.append(args.branch_sel)
        
    # Construct Arguments
    script_args = []
    if args.cut:
        script_args.append(f'-c={args.cut}')
    if args.branch_sel:
        script_args.append(f'-b={os.path.basename(args.branch_sel)}')
    if args.imports:
        script_args.append(f'-I={" ".join(args.imports)}')
    if args.max_events:
        script_args.append(f'-N={args.max_events}')
    if args.postfix:
        script_args.append(f'--postfix={args.postfix}')

    conf.JobType.scriptArgs = script_args
    
    conf.JobType.maxMemoryMB = 2500
    conf.JobType.maxJobRuntimeMin = 600

    # --- Data & Resubmission ---
    conf.Data.inputDBS = 'global'
    conf.Data.splitting = 'FileBased'
    conf.Data.unitsPerJob = args.units_per_job
    conf.Data.outputDatasetTag = args.name
    conf.Site.storageSite = args.site
    
    # Read Sample List
    if not os.path.exists(args.sample_list):
        print(f"Error: {args.sample_list} not found.")
        return

    with open(args.sample_list, 'r') as f:
        datasets = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    from CRABAPI.RawCommand import crabCommand
    from httplib import HTTPException

    for dataset in datasets:
        # Create unique request name
        ds_parts = dataset.split('/')
        req_name = f"{args.name}_{ds_parts[1]}" if len(ds_parts) >= 3 else f"{args.name}_{dataset.replace('/', '_')}"
        
        conf.General.requestName = req_name[:95]
        conf.Data.inputDataset = dataset
        
        print(f"Submitting: {conf.General.requestName}")
        try:
            crabCommand('submit', config = conf)
        except HTTPException as hte:
            print(f"Failed: {hte.headers}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--sample-list", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--work-area", default="crab_projects")
    parser.add_argument("--cut")
    parser.add_argument("--branch-sel")
    parser.add_argument("--imports", nargs="+")
    parser.add_argument("--units-per-job", type=int, default=1)
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--postfix", default="_Skim")

    args = parser.parse_args()
    submit(args)
