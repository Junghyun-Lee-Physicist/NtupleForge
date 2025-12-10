#!/bin/bash

echo "=== NtupleForge CRAB Script ==="
echo "Host: " `hostname`
echo "PWD: " $PWD

# Setup Python Path
export PYTHONPATH=$PYTHONPATH:$PWD

# Parse Args
JOBREPORT=$1
shift

CMD="python3 scripts/run_postproc.py ."
FILES=""
FLAGS=""

for arg in "$@"
do
    if [[ "$arg" == *.root ]]; then
        FILES="$FILES $arg"
    elif [[ "$arg" == *.xml ]]; then
        echo "Skipping JobReport: $arg"
    else
        FLAGS="$FLAGS $arg"
    fi
done

# Run
FULL_CMD="$CMD $FILES $FLAGS --no-check"
echo "Exec: $FULL_CMD"
$FULL_CMD
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Failed code $EXIT_CODE"
    exit $EXIT_CODE
fi

ls -l
