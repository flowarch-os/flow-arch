#!/bin/bash

# Exit on error
set -e

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Clean up previous work directory to avoid file conflicts
if [ -d "work" ]; then
    echo "Cleaning up previous work directory..."
    sudo rm -rf work
fi

# Ensure output directory exists
mkdir -p out

# Run mkarchiso
echo "Starting Flow Arch ISO build..."
sudo mkarchiso -v -w work -o out .

echo "Build complete! Your ISO is in the 'out' directory."
