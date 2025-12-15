#!/bin/bash

# Loop through all directories starting with "crab_"
for dir in crab_*; do
    if [ -d "$dir" ]; then
        echo "================================================="
        echo "Killing tasks in directory: $dir"
        echo "================================================="
        
        # Execute crab kill
        crab kill -d "$dir"
        
        echo ""
    fi
done

echo "All kill commands processed."
