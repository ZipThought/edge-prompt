#!/bin/bash
# Script to run tests using only the LM Studio backend

# Set the output directory to include timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="data/lmstudio_test_${TIMESTAMP}"

echo "Running LM Studio backend test..."
echo "Results will be saved to: ${OUTPUT_DIR}"

# Run the test using the LM Studio-specific config
./run_test.sh --config configs/test_suites/test_lmstudio.json --output ${OUTPUT_DIR} "$@"