import os
import argparse
from CRABClient.UserUtilities import config
from CRABAPI.RawCommand import crabCommand
try:
    from http.client import HTTPException
except ImportError:
    from httplib import HTTPException

def submit_or_resubmit(args):
    conf = config()
    
    # --- Configuration ---
    conf.General.transferOutputs = True
    conf.General.transferLogs = True
    conf.General.workArea = args.work_area
    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py' 
    conf.JobType.scriptExe = 'crab/crab_script.sh' 
    conf.JobType.maxMemoryMB = 2500
    conf.JobType.maxJobRuntimeMin = 600
    conf.Data.inputDBS = 'global'
    conf.Data.splitting = 'FileBased'
    conf.Data.unitsPerJob = args.units_per_job
    conf.Data.outputDatasetTag = args.name
    conf.Site.storageSite = args.site

    # --- Files to Ship ---
    conf.JobType.inputFiles = ['scripts/run_postproc.py']
    if os.path.exists('modules'): conf.JobType.inputFiles.append('modules')
    if args.branch_sel: conf.JobType.inputFiles.append(args.branch_sel)

    # --- Arguments File (Bypass HTTP 400) ---
    args_file_name = "crab_args.txt"
    with open(args_file_name, "w") as f:
        if args.cut: f.write(f"-c\n{args.cut}\n")
        if args.branch_sel: f.write(f"-b\n{os.path.basename(args.branch_sel)}\n")
        if args.imports:
            f.write("-I\n")
            for imp in args.imports: f.write(f"{imp}\n")
        if args.max_events: f.write(f"-N\n{args.max_events}\n")
        if args.postfix: f.write(f"--postfix\n{args.postfix}\n")
    
    conf.JobType.inputFiles.append(args_file_name)
    conf.JobType.scriptArgs = [f"@{args_file_name}"]

    # --- Read Dataset List ---
    # Look in dataSetPath/ first, then local
    list_path = os.path.join("dataSetPath", args.sample_list)
    if not os.path.exists(list_path):
        list_path = args.sample_list # Fallback to local
        if not os.path.exists(list_path):
            print(f"[Error] Sample list not found in dataSetPath/ or local: {args.sample_list}")
            return

    with open(list_path, 'r') as f:
        datasets = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Found {len(datasets)} datasets to process.")

    # --- Main Loop ---
    for dataset in datasets:
        ds_parts = dataset.split('/')
        req_name = f"{args.name}_{ds_parts[1]}" if len(ds_parts) >= 3 else f"{args.name}_{dataset.replace('/', '_')}"
        req_name = req_name[:95]
        
        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        
        # Check if project directory exists
        project_dir = os.path.join(args.work_area, "crab_" + req_name)
        
        if os.path.exists(project_dir):
            print(f"\n[INFO] Project exists: {project_dir}")
            print(f"       -> Attempting RESUBMIT (failed jobs only)")
            try:
                crabCommand('resubmit', dir=project_dir)
            except HTTPException as hte:
                print(f"[Error] Resubmit failed: {hte.headers}")
            except Exception as e:
                print(f"[Error] Resubmit failed: {e}")
        else:
            print(f"\n[INFO] New Project: {req_name}")
            print(f"       -> Attempting SUBMIT")
            try:
                crabCommand('submit', config=conf)
            except HTTPException as hte:
                print(f"[Error] Submit failed: {hte.headers}")
            except Exception as e:
                print(f"[Error] Submit failed: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--sample-list", required=True, help="Filename inside dataSetPath/")
    parser.add_argument("--site", required=True)
    parser.add_argument("--work-area", default="crab_projects")
    parser.add_argument("--cut")
    parser.add_argument("--branch-sel")
    parser.add_argument("--imports", nargs="+")
    parser.add_argument("--units-per-job", type=int, default=1)
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--postfix", default="_Skim")

    args = parser.parse_args()
    submit_or_resubmit(args)
