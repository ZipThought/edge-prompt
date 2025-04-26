#!/bin/bash
# EdgePrompt Research Environment Setup Script
# This script is idempotent - it can be run multiple times without causing issues

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

# Make sure we're in the /research directory
if [[ $(basename "$PWD") != "research" ]]; then
    echo -e "${RED}Error: This script must be run from the /research directory.${NC}"
    echo "Please change to the research directory:"
    echo "  cd /home/cyharyanto/edge-prompt/research"
    exit 1
fi

echo -e "${BOLD}===== EdgePrompt Research Environment Setup =====${NC}"
echo "This script will set up the Python environment for EdgePrompt research."

# Check for system dependencies
echo "Checking system dependencies..."
MISSING_DEPS=()

# Check for pkg-config
if ! command -v pkg-config &> /dev/null; then
    MISSING_DEPS+=("pkg-config")
fi

# Check for cmake
if ! command -v cmake &> /dev/null; then
    MISSING_DEPS+=("cmake")
fi

# Check for gcc/g++
if ! command -v g++ &> /dev/null; then
    MISSING_DEPS+=("gcc")
fi

# Check for make
if ! command -v make &> /dev/null; then
    MISSING_DEPS+=("make")
fi

# Inform about missing dependencies
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}The following system dependencies are missing and required for building packages:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    
    echo -e "\nOn Arch Linux, you can install them with:"
    echo -e "  sudo pacman -S ${MISSING_DEPS[*]}\n"
    
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup aborted. Please install the required dependencies and run this script again."
        exit 1
    fi
fi

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python not found. You need to install Python first.${NC}"
    echo "On Arch Linux, run:"
    echo "  sudo pacman -S python python-pip"
    
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup aborted. Please install Python and run this script again."
        exit 1
    fi
fi

# Determine Python command (python or python3)
PYTHON_CMD="python"
if ! command -v python &> /dev/null && command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

# Try to get Python version
PYTHON_VERSION=""
if command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo -e "${GREEN}✓${NC} Using $PYTHON_VERSION"
else
    echo -e "${YELLOW}Warning: Unable to determine Python version.${NC}"
fi

# Check for pip
PIP_CMD="pip"
if ! command -v pip &> /dev/null && command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
fi

if ! command -v $PIP_CMD &> /dev/null; then
    echo -e "${YELLOW}pip not found. If you continue, virtual environment creation may fail.${NC}"
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup aborted. Please install pip and run this script again."
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    
    # Try different methods for creating a virtual environment
    if command -v $PYTHON_CMD &> /dev/null && $PYTHON_CMD -m venv --help &> /dev/null; then
        $PYTHON_CMD -m venv venv
    elif command -v virtualenv &> /dev/null; then
        virtualenv venv
    else
        echo -e "${RED}Error: Cannot create virtual environment.${NC}"
        echo "Please install virtualenv first:"
        echo "  $PIP_CMD install virtualenv"
        exit 1
    fi
    
    if [ -d "venv" ]; then
        echo -e "${GREEN}✓${NC} Virtual environment created in ./venv"
    else
        echo -e "${RED}Error: Failed to create virtual environment.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo -e "${GREEN}✓${NC} Virtual environment activated."
else
    echo -e "${RED}Error: Cannot find venv/bin/activate${NC}"
    exit 1
fi

# Check if activation worked by testing if python is from venv
if [[ ! "$(which python)" == *"/venv/"* ]] && [[ ! "$(which python3)" == *"/venv/"* ]]; then
    echo -e "${RED}Error: Virtual environment activation failed.${NC}"
    echo "Please try to manually activate the virtual environment:"
    echo "  source venv/bin/activate"
    exit 1
fi

# Install dependencies
echo "Installing required packages..."
if command -v $PIP_CMD &> /dev/null; then
    # First, upgrade pip and install wheel
    $PIP_CMD install --upgrade pip wheel setuptools
    
    # Create a modified requirements file without problematic packages for initial setup
    echo "Creating simplified requirements for initial setup..."
    grep -v "sentencepiece\|bitsandbytes" requirements.txt > requirements_simplified.txt
    
    # Install simplified requirements
    echo "Installing core requirements..."
    $PIP_CMD install -r requirements_simplified.txt
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to install core packages.${NC}"
        echo "You may need to install additional development libraries."
        exit 1
    else
        echo -e "${GREEN}✓${NC} Successfully installed core packages."
    fi
    
    # Ask if user wants to attempt installing the more complex packages
    echo -e "\n${YELLOW}Some packages require additional system dependencies and compilation:${NC}"
    echo "  - sentencepiece (requires cmake, pkg-config, and C++ compiler)"
    echo "  - bitsandbytes (requires CUDA for full functionality)"
    echo ""
    read -p "Do you want to attempt installing these packages? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Attempting to install additional packages..."
        
        # Try installing sentencepiece (may fail if dependencies are missing)
        $PIP_CMD install sentencepiece || echo -e "${YELLOW}Failed to install sentencepiece. You may need to install it manually later.${NC}"
        
        # Try installing bitsandbytes (may fail without CUDA)
        $PIP_CMD install bitsandbytes || echo -e "${YELLOW}Failed to install bitsandbytes. You may need to install it manually later.${NC}"
    else
        echo -e "${YELLOW}Skipping installation of additional packages.${NC}"
        echo "You can try installing them manually later if needed."
    fi
    
    # Clean up
    rm requirements_simplified.txt
    
    echo -e "${GREEN}✓${NC} Package installation process completed."
else
    echo -e "${RED}Error: pip not available in virtual environment.${NC}"
    exit 1
fi

# Create/update .env file
echo "Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo -e "${GREEN}✓${NC} .env file created from example."
else
    echo -e "${GREEN}✓${NC} .env file already exists."
fi

# Interactive setup for .env file
echo "Setting up environment variables..."

# Function to update env variable
update_env_var() {
    local var_name=$1
    local var_prompt=$2
    local default_value=$3
    local secret=$4
    
    # Get current value if exists
    current_value=$(grep -o "^$var_name=.*" .env | cut -d= -f2)
    
    # If empty or comment, use default
    if [[ -z "$current_value" || "$current_value" == "#"* ]]; then
        current_value=$default_value
    fi
    
    # Display prompt, hiding the value if it's a secret
    if [[ "$secret" == "true" ]]; then
        if [[ -n "$current_value" && "$current_value" != "$default_value" ]]; then
            echo -n "$var_prompt [current value hidden, press Enter to keep]: "
        else
            echo -n "$var_prompt [press Enter for none]: "
        fi
    else
        echo -n "$var_prompt [press Enter for '$current_value']: "
    fi
    
    # Read input (hidden if secret)
    if [[ "$secret" == "true" ]]; then
        read -s new_value
        echo  # Add newline after hidden input
    else
        read new_value
    fi
    
    # If user entered nothing, keep current value
    if [[ -z "$new_value" ]]; then
        new_value=$current_value
    fi
    
    # Update .env file
    if grep -q "^$var_name=" .env; then
        sed -i "s|^$var_name=.*|$var_name=$new_value|" .env
    else
        echo "$var_name=$new_value" >> .env
    fi
}

# Update environment variables
update_env_var "LM_STUDIO_URL" "LM Studio URL" "http://localhost:1234" "false"
update_env_var "OPENAI_API_KEY" "OpenAI API Key" "" "true"
update_env_var "ANTHROPIC_API_KEY" "Anthropic API Key" "" "true"
update_env_var "LOG_LEVEL" "Log Level (DEBUG, INFO, WARNING, ERROR)" "DEBUG" "false"

# Optionally enable mock mode
echo -n "Enable mock mode? This avoids using real API calls [y/N]: "
read enable_mock
if [[ "$enable_mock" =~ ^[Yy]$ ]]; then
    if grep -q "^MOCK_MODE=" .env; then
        sed -i "s|^MOCK_MODE=.*|MOCK_MODE=true|" .env
    else
        echo "MOCK_MODE=true" >> .env
    fi
    echo -e "${GREEN}✓${NC} Mock mode enabled."
else
    if grep -q "^MOCK_MODE=" .env; then
        sed -i "s|^MOCK_MODE=.*|MOCK_MODE=false|" .env
    else
        echo "MOCK_MODE=false" >> .env
    fi
    echo -e "${GREEN}✓${NC} Mock mode disabled (will use real API calls)."
fi

# Check model configuration
echo "Checking model configuration..."
if [ -f "configs/model_configs.json" ]; then
    echo -e "${GREEN}✓${NC} Model configuration found."
else
    echo -e "${RED}Error: Model configuration file not found at configs/model_configs.json.${NC}"
    echo "Make sure the configs directory is properly set up."
fi

# Check test suite
echo "Checking test suite configuration..."
if [ -f "configs/test_suites/ab_test_suite.json" ]; then
    echo -e "${GREEN}✓${NC} Test suite configuration found."
else
    echo -e "${YELLOW}Warning: Default test suite not found at configs/test_suites/ab_test_suite.json.${NC}"
    echo "You may need to specify a custom test suite with --config when running tests."
fi

# Set PYTHONPATH
echo "Setting PYTHONPATH to include the research directory..."
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Add PYTHONPATH to virtual environment activation script
if ! grep -q "export PYTHONPATH" venv/bin/activate; then
    echo "export PYTHONPATH=\$PYTHONPATH:$(pwd)" >> venv/bin/activate
    echo -e "${GREEN}✓${NC} PYTHONPATH added to virtual environment activation script."
else
    echo -e "${GREEN}✓${NC} PYTHONPATH already configured in virtual environment."
fi

# Ask if we should run verification
echo -n "Do you want to run validation verification now? [Y/n]: "
read run_verification
if [[ ! "$run_verification" =~ ^[Nn]$ ]]; then
    echo "Running validation verification..."
    
    # Try to run verification script
    python verify_validation.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} Validation verification passed!"
    else
        echo -e "${YELLOW}Warning: Validation verification failed.${NC}"
        echo "This might be expected if the environment is not fully set up."
        echo "You can try again later after installing all dependencies."
    fi
else
    echo "Skipping validation verification."
fi

# Setup complete
echo ""
echo -e "${BOLD}===== Environment Setup Complete =====${NC}"
echo ""
echo "To use this environment:"
echo ""
echo "1. Always make sure you're in the research directory:"
echo "   cd /home/cyharyanto/edge-prompt/research"
echo ""
echo "2. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "3. If using LM Studio for local models:"
echo "   - Start LM Studio and load your models"
echo "   - Ensure the server is running on the URL specified in .env"
echo ""
echo "4. Run experiments with:"
echo "   ./run_test.sh"
echo ""
echo "   Or with custom settings:"
echo "   ./run_test.sh --config configs/test_suites/custom_suite.json --output data/custom_test"
echo ""
echo "5. To use mock mode (no API calls):"
echo "   MOCK_MODE=true ./run_test.sh"
echo ""
echo -e "${BOLD}Note on Dependencies:${NC}"
echo "Some Python packages require system dependencies for compilation:"
echo "  - sentencepiece: requires cmake, pkg-config, and a C++ compiler"
echo "  - bitsandbytes: requires CUDA for full functionality"
echo ""
echo "On Arch Linux, install them with:"
echo "  sudo pacman -S cmake pkg-config gcc make"
echo ""
echo -e "${BOLD}Happy researching!${NC}"