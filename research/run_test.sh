#!/bin/bash
# EdgePrompt Test Runner Script
# Consolidated script to run different test configurations with proper environment setup

# Default values
CONFIG_FILE="configs/test_suites/ab_test_suite.json"
OUTPUT_DIR="data/validation_test"
RUN_VERIFICATION=true

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --config) CONFIG_FILE="$2"; shift ;;
        --output) OUTPUT_DIR="$2"; shift ;;
        --skip-verification) RUN_VERIFICATION=false ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --config FILE           Use specific config file (default: configs/test_suites/ab_test_suite.json)"
            echo "  --output DIR            Output directory (default: data/validation_test)"
            echo "  --skip-verification     Skip validation architecture verification"
            echo "  --help                  Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Check if we're already in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "No active virtual environment detected."
    
    # Activate virtual environment if it exists, or create a new one
    if [ -d "venv" ]; then
        echo "Activating existing virtual environment..."
        source venv/bin/activate
    else
        echo "Creating new virtual environment..."
        python -m venv venv
        source venv/bin/activate
        
        echo "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
    fi
else
    echo "Already in virtual environment: $VIRTUAL_ENV"
    
    # Ensure dependencies are installed in the existing environment
    echo "Checking dependencies in current environment..."
    if ! python -c "import openai" &> /dev/null; then
        echo "Some dependencies appear to be missing. Installing from requirements.txt..."
        pip install -r requirements.txt
    fi
fi

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found. Make sure necessary environment variables (API keys, LM Studio URL, Ollama URL) are set manually."
fi

# Set Log Level (can be overridden by .env)
export LOG_LEVEL=${LOG_LEVEL:-"DEBUG"} 

echo "Environment configured using .env (or manual export):"
echo "- LM Studio URL: ${LM_STUDIO_URL:-"Not Set"}"
echo "- Ollama URL: ${OLLAMA_URL:-"Not Set"}"
echo "- Log Level: $LOG_LEVEL"
echo "- Test Config: $CONFIG_FILE"
echo "- Output Directory: $OUTPUT_DIR"
# Note: API keys are not printed for security

# Check if any local inference backend is set
if [[ -z "$LM_STUDIO_URL" && -z "$OLLAMA_URL" ]]; then
    echo "Warning: Neither LM_STUDIO_URL nor OLLAMA_URL is set. Tests requiring EdgeLLM execution might fail unless using mock mode."
fi

# Run verification if not skipped
if [ "$RUN_VERIFICATION" = true ]; then
    echo "================================================================="
    echo "First running verification to ensure validation architecture works..."
    echo "================================================================="

    # Run verification script
    python verify_validation.py

    if [ $? -ne 0 ]; then
        echo "Verification failed! Fix issues before proceeding with the test."
        exit 1
    fi

    echo "================================================================="
    echo "Verification passed! Proceeding with test suite..."
    echo "================================================================="
fi

echo "================================================================="
echo "Running test suite with EdgePrompt validation architecture..."
echo "================================================================="

# Run the actual test suite - runner_cli will use environment variables
python -m runner.runner_cli \
    --config "$CONFIG_FILE" \
    --output "$OUTPUT_DIR" \
    --log-level $LOG_LEVEL

# Check if test was successful
if [ $? -eq 0 ]; then
    echo "================================================================="
    echo "Test completed successfully. Results saved in $OUTPUT_DIR"
    echo "You can analyze results with: python -m scripts.analyze_results $OUTPUT_DIR"
else
    echo "================================================================="
    echo "Test failed with errors. Check logs for details."
fi