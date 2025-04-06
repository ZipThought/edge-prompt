#!/bin/bash
# EdgePrompt Research Test Runner
# Executes all test suites in sequence

set -e

# Directory setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESEARCH_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$RESEARCH_DIR/configs"
DATA_DIR="$RESEARCH_DIR/data"
PYTHON="python3"

# Ensure output directories exist
mkdir -p "$DATA_DIR/raw"
mkdir -p "$DATA_DIR/processed"
mkdir -p "$RESEARCH_DIR/figures"

echo "EdgePrompt Research Test Runner"
echo "==============================="
echo "Research directory: $RESEARCH_DIR"

# Check Python environment
if ! command -v $PYTHON &> /dev/null; then
    echo "Python not found! Please install Python 3.10 or above."
    exit 1
fi

echo "Using Python: $($PYTHON --version)"

# Check if virtual environment exists, if not create it
if [ ! -d "$RESEARCH_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv "$RESEARCH_DIR/.venv"
    source "$RESEARCH_DIR/.venv/bin/activate"
    pip install -U pip
    pip install -r "$RESEARCH_DIR/requirements.txt"
else
    source "$RESEARCH_DIR/.venv/bin/activate"
fi

# Function to run a test suite
run_test_suite() {
    local suite=$1
    local output_dir="$DATA_DIR/raw/$(basename $suite .json)"
    
    echo ""
    echo "Running test suite: $suite"
    echo "Output directory: $output_dir"
    
    mkdir -p "$output_dir"
    
    $PYTHON -m research.runner.runner_cli \
        --config "$suite" \
        --output "$output_dir" \
        --log-level INFO
        
    echo "Test suite complete: $suite"
}

# Execute all test suites
echo ""
echo "Executing test suites..."

test_suites=(
    "$CONFIG_DIR/test_suites/multi_stage_validation.json"
    "$CONFIG_DIR/test_suites/neural_symbolic_validation.json"
    "$CONFIG_DIR/test_suites/resource_optimization.json"
)

for suite in "${test_suites[@]}"; do
    if [ -f "$suite" ]; then
        run_test_suite "$suite"
    else
        echo "Warning: Test suite not found: $suite"
    fi
done

# Process results and generate figures
echo ""
echo "Processing results..."
$PYTHON "$SCRIPT_DIR/analyze_results.py"

echo ""
echo "Generating figures..."
$PYTHON "$SCRIPT_DIR/render_figures.py"

echo ""
echo "All tests completed successfully!"
echo "Results available in: $DATA_DIR"
echo "Figures available in: $RESEARCH_DIR/figures" 