#!/bin/bash
# Run a validation test suite using the improved EdgePrompt validation architecture

# Set environment variables (use .env if available)
if [ -f .env ]; then
    echo "Loading environment from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Set the log level to DEBUG for more detailed output
export LOG_LEVEL=DEBUG

echo "Running test suite with improved validation architecture..."
echo "================================================================="

# Run a test suite with the structured_prompting_guardrails.json configuration
python -m runner.runner_cli --config configs/test_suites/structured_prompting_guardrails.json \
    --output data/validation_test \
    --log-level $LOG_LEVEL

# Display successful completion message
if [ $? -eq 0 ]; then
    echo "================================================================="
    echo "Test completed successfully. Results saved to data/validation_test/"
    echo "You can analyze results with: python -m scripts.analyze_results data/validation_test/"
else
    echo "================================================================="
    echo "Test failed with errors. Check logs for details."
fi 