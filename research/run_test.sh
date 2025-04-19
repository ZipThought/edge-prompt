#!/bin/bash
# Run EdgePrompt validation test using environment variables from .env

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
    echo "Warning: .env file not found. Make sure necessary environment variables (API keys, LM Studio URL) are set manually."
fi

# Set Log Level (can be overridden by .env)
export LOG_LEVEL=${LOG_LEVEL:-"DEBUG"} 

echo "Environment configured using .env (or manual export):"
echo "- LM Studio URL: ${LM_STUDIO_URL:-"Not Set"}"
echo "- Log Level: $LOG_LEVEL"
# Note: API keys are not printed for security

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
echo "Verification passed! Running test suite with EdgePrompt validation architecture..."
echo "================================================================="

# Run the actual test suite - runner_cli will use environment variables
python -m runner.runner_cli \
    --config configs/test_suites/ab_test_suite.json \
    --output data/validation_test \
    --log-level $LOG_LEVEL

# Check if test was successful
if [ $? -eq 0 ]; then
    echo "================================================================="
    echo "Test completed successfully. Results saved in data/validation_test/"
    echo "You can analyze results with: python -m scripts.analyze_results data/validation_test/"
else
    echo "================================================================="
    echo "Test failed with errors. Check logs for details."
fi 