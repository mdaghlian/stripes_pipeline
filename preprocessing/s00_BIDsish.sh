#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <folder_path> <sub_id> <task_name>"
    echo "Example: $0 ./data sub-03 colbw"
    exit 1
fi

# Assign arguments to variables
TARGET_DIR=$1
SUB=$2
TASK=$3

# Ensure jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: 'jq' is not installed. Please install it."
    exit 1
fi

# Move into the target directory
cd "$TARGET_DIR" || { echo "Error: Cannot enter directory $TARGET_DIR"; exit 1; }

# Loop through all JSON files in the directory
for json_file in *.json; do
    # Skip if no json files found
    [ -e "$json_file" ] || continue

    # Extract the run number from the second element of BidsGuess array
    # Use [0-9][0-9]* instead of [0-9]\+ for better BSD sed compatibility
    run_num=$(jq -r '.BidsGuess[1] // empty' "$json_file" | sed -n 's/.*_run-\([0-9][0-9]*\).*/\1/p')

    if [[ -n "$run_num" ]]; then
        # Convert run number: subtract 9 to map 10->1, 11->2, ..., 19->10
        # Then zero-pad to 2 digits
        corrected_run=$((run_num - 9))
        run_padded=$(printf "%02d" $corrected_run)
        
        # Define the new base name (e.g., sub-03_task-colbw_run-01_bold)
        new_base="${SUB}_task-${TASK}_run-${run_padded}_bold"

        echo "Processing: $json_file (run-$run_num -> run-$run_padded) -> ${new_base}.json"

        # Rename the matching .nii or .nii.gz file if it exists
        for ext in ".nii" ".nii.gz"; do
            nii_file="${json_file%.json}${ext}"
            if [[ -f "$nii_file" ]]; then
                mv "$nii_file" "${new_base}${ext}"
            fi
        done

        # Rename the .json file last
        mv "$json_file" "${new_base}.json"
    else
        echo "Warning: No run number found in $json_file. Skipping."
    fi
done

echo "Done!"