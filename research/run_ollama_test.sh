#!/bin/bash
# Script to run tests using only the Ollama backend

# Set the output directory to include timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="data/ollama_test_${TIMESTAMP}"

echo "Running Ollama backend test..."
echo "Results will be saved to: ${OUTPUT_DIR}"

# Run the test using the Ollama-specific config
./run_test.sh --config configs/test_suites/test_ollama.json --output ${OUTPUT_DIR} "$@"