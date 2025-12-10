import os
import argparse
import time
from CRABClient.UserUtilities import config
from CRABAPI.RawCommand import crabCommand
try:
    from http.client import HTTPException
except ImportError:
    from httplib import HTTPException

def submit_or_resubmit(args):
    conf = config()
    
    # --- [3] Log & Output Location Configuration ---
    # CRAB logs will be saved under: <work_area>/crab_<requestName>/
    # Example: crab_projects/crab_Campagin_v1_TTToSemiLeptonic/crab.log
    conf.General.transferOutputs = True
    conf.General.transferLogs = True
    conf.General.workArea = args.work_area

    # --- JobType ---
    conf.JobType.pluginName = 'Analysis'
    conf.JobType.psetName = 'crab/PSet.py' 
    conf.JobType.scriptExe = 'crab/crab_script.sh' 
    conf.JobType.maxMemoryMB = 2500
    conf.JobType.maxJobRuntimeMin = 600
    
    # --- Data ---
    conf.Data.inputDBS = 'global'
    conf.Data.splitting = 'FileBased'
    conf.Data.unitsPerJob = args.units_per_job
    conf.Data.outputDatasetTag = args.name
    conf.Site.storageSite = args.site
    conf.Data.publication = False
    conf.Data.outLFNDirBase = f"/store/user/junghyun/ttHHSlimed/"


    # --- Files to Ship ---
    conf.JobType.inputFiles = ['scripts/run_postproc.py']
    if os.path.exists('modules'): conf.JobType.inputFiles.append('modules')
    if os.path.exists('branches'): conf.JobType.inputFiles.append('branches')
    if args.branch_sel and 'branches' not in args.branch_sel:
        conf.JobType.inputFiles.append(args.branch_sel)

    # --- [2] Argument Management (Clean) ---
    # Create arguments file inside the 'crab' folder to avoid cluttering root
    # or use a hidden file. Here we generate it in the CWD but remove it later or keep it for debug.
    # Let's verify arguments first.
    
    args_file_name = "crab_args.txt"
    with open(args_file_name, "w") as f:
        if args.branch_sel: 
            f.write(f"-b\n{os.path.basename(args.branch_sel)}\n")
        if args.imports:
            f.write("-I\n")
            for imp in args.imports: f.write(f"{imp}\n")
        if args.max_events: 
            f.write(f"-N\n{args.max_events}\n")
        if args.postfix: 
            f.write(f"--postfix\n{args.postfix}\n")
            
    conf.JobType.inputFiles.append(args_file_name)
    conf.JobType.scriptArgs = [] # Keep empty to bypass server validation

    # --- Dataset List ---
    # Look in dataSetPath/
    list_path = os.path.join("dataSetPath", args.sample_list)
    if not os.path.exists(list_path):
        print(f"[Error] Sample list not found in dataSetPath/: {args.sample_list}")
        return

    with open(list_path, 'r') as f:
        datasets = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Found {len(datasets)} datasets.")

    # --- Main Loop ---
    for dataset in datasets:
        ds_parts = dataset.split('/')
        req_name = f"{args.name}_{ds_parts[1]}" if len(ds_parts) >= 3 else f"{args.name}_{dataset.replace('/', '_')}"
        req_name = req_name[:95]
        
        conf.General.requestName = req_name
        conf.Data.inputDataset = dataset
        
        project_dir = os.path.join(args.work_area, "crab_" + req_name)
        
        if os.path.exists(project_dir):
            print(f"Project exists: {project_dir}")
            print(" -> Attempting RESUBMIT")
            try:
                crabCommand('resubmit', dir=project_dir)
            except Exception as e:
                print(f" -> Resubmit Failed: {e}")
        else:
            print(f"Creating new project: {req_name}")
            print(" -> Attempting SUBMIT")
            try:
                crabCommand('submit', config=conf)
            except Exception as e:
                print(f" -> Submit Failed: {e}")
                
    # Optional: Clean up args file? 
    # os.remove(args_file_name) # Uncomment if you want it gone, but keeping it helps debugging

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--sample-list", required=True)
    parser.add_argument("--site", required=True)
    parser.add_argument("--work-area", default="crab_projects")
    parser.add_argument("--branch-sel")
    parser.add_argument("--imports", nargs="+")
    parser.add_argument("--units-per-job", type=int, default=1)
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--postfix", default="_Skim")

    args = parser.parse_args()
    submit_or_resubmit(args)
