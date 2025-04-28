#!/bin/bash
# Script to run tests with both LM Studio and Ollama backends for comparison

# Set the output directory to include timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="data/dual_backend_test_${TIMESTAMP}"

echo "Running comprehensive test with both LM Studio and Ollama backends..."
echo "Results will be saved to: ${OUTPUT_DIR}"

# Run the test using the full config with both backends
./run_test.sh --config configs/test_suites/ab_test_suite.json --output ${OUTPUT_DIR} "$@"

echo "Test complete. You can analyze the results to compare LM Studio and Ollama performance."