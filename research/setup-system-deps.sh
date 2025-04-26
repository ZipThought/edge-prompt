#!/bin/bash
# EdgePrompt Research System Dependencies Setup
# Run this script with sudo to install system dependencies needed for the Python packages

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run with sudo privileges.${NC}"
  echo "Please run as: sudo ./setup-system-deps.sh"
  exit 1
fi

echo -e "${BOLD}===== Installing System Dependencies for EdgePrompt Research =====${NC}"

# Update package database
echo "Updating package database..."
pacman -Sy

# Install required packages
echo "Installing required development packages..."
pacman -S --noconfirm --needed \
  python \
  python-pip \
  python-virtualenv \
  cmake \
  pkg-config \
  gcc \
  make

# Check if installation succeeded
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Successfully installed system dependencies."
else
    echo -e "${RED}Error: Failed to install some dependencies.${NC}"
    exit 1
fi

echo -e "\n${BOLD}===== System Dependencies Setup Complete =====${NC}"
echo ""
echo "Now you can run the main setup script without sudo:"
echo "  ./setup.sh"
echo ""
echo -e "${BOLD}Optionally:${NC} If you need CUDA support for GPU acceleration:"
echo "  pacman -S --noconfirm --needed cuda cudnn"