#!/bin/bash

# Define the source directory
SOURCE_DIR="./bird"

# Get the output directory from command line argument or use default
if [ $# -eq 0 ]; then
    OUTPUT_DIR="./output_mbgp"
    echo "No argument provided. Using default output directory: $OUTPUT_DIR"
else
    OUTPUT_DIR="$1"
    echo "Using provided output directory: $OUTPUT_DIR"
fi

# Check if the source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory '$SOURCE_DIR' does not exist."
    exit 1
fi

# Check if the output directory exists
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Error: Output directory '$OUTPUT_DIR' does not exist."
    exit 1
fi

# Loop through all subdirectories in the output directory
for dir in "$OUTPUT_DIR"/*; do
    if [[ -d "$dir" && ( "$dir" == *"/rnode_"* || "$dir" == *"/rs_"* ) ]]; then
        # Define the destination path
        DEST_DIR="$dir/bird"
        
        # Copy the bird directory to the current subdirectory
        if [ -d "$DEST_DIR" ]; then
            echo "Directory '$DEST_DIR' already exists. Skipping."
        else
            cp -r "$SOURCE_DIR" "$DEST_DIR"
            echo "Copied '$SOURCE_DIR' to '$DEST_DIR'."
        fi
    fi
done

echo "All eligible directories processed for $OUTPUT_DIR."
