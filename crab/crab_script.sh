#!/bin/bash

# This script runs on the grid worker node

echo "================= NtupleForge CRAB Script ================="
echo "Starting job on " `date`
echo "User: " `whoami`
echo "Host: " `hostname`
echo "==========================================================="

# 1. Parse Arguments passed by CRAB
# CRAB passes arguments via JobType.scriptArgs
# We expect: python scripts/run_postproc.py output input [args...]
# But CRAB 'scriptExe' handles inputs differently. 
# The input file path is usually handled by PostProcessor logic finding the PSet file or passed via arguments.

# For NanoAODTools with 'scriptExe', the input file comes as a positional argument from the wrapper
# However, a simpler way is to let CRAB handle splitting, and we just run on the file provided in the directory.

# Check environment
echo "PWD: " $PWD
ls -lR .

# 2. Setup CMSSW (Already done by CRAB, but we ensure python path)
# We are in the 'src' directory of the job tarball
export PYTHONPATH=$PYTHONPATH:$PWD

# 3. Identify Input File
# CRAB3 splits the job and usually places the input file in the manifest or passes it.
# BUT, when using 'scriptExe' with 'FileBased' splitting, CRAB passes the PFN as an argument to the script if configured?
# Actually, the most robust way in NanoAODTools is using the PSet.py to locate the file, 
# OR use the 'InputFiles' parameter if we wrote a wrapper python.

# Let's assume we run the python script directly.
# We need to find the root file. CRAB transfers the specific input file for this job to the working directory if 'userInputFiles' used,
# BUT for 'Data' (DAS) dataset, CRAB does NOT download the file. It gives us the LFN/PFN.

# To simplify: We will run a python wrapper that detects the input file from the arguments passed by CRAB wrapper.
# Typically CRAB executes: scriptExe <FrameworkJobReport.xml> <inputFile1> <inputFile2> ...

# Let's look at the arguments passed to this script
echo "Arguments passed to script: $@"

# Extract the input file name (usually the last ones, but arg 1 is job report)
JOBREPORT=$1
shift
INPUTFILES="$@"

echo "Input Files: $INPUTFILES"

# 4. Run the Processor
# We call our python script. 
# NOTE: We need to make sure 'scripts/run_postproc.py' and 'configs/' are in the input tarball.

# Example Cut (Hardcoded or passed via scriptArgs)
# Ideally, we pass the cut via crab_config.py -> scriptArgs
# For now, let's assume we read arguments from a flag we set in crab_submit.py

# Run!
# We assume the user wants to run the module defined in the config
python3 scripts/run_postproc.py . $INPUTFILES --no-check "$@"

EXIT_CODE=$?

echo "PostProcessing finished with exit code: $EXIT_CODE"

if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: PostProcessing failed."
    exit $EXIT_CODE
fi

# 5. Handle Output
# We need to ensure the output file is named correctly for CRAB to pick it up.
# PostProcessor by default produces a file ending in _Skim.root or similar.
# We need to rename it to match what CRAB expects (often just whatever is declared in outputFiles)
# or just leave it if we configured outputFiles in crab config.

ls -l .
