#!/usr/bin/sh

set -e

function color_echo {
    echo -e "\033[1;32m$1\033[0m"
}

function warning_echo {
    echo -e "\033[1;33m$1\033[0m"
}

if [ -f /etc/os-release ]; then
    source /etc/os-release
else
    warning_echo "Could not determine the OS distribution."
    ID="unknown"
fi

color_echo "Distribution ID: $ID"

function arch_install_tesseract {
    # Install the required packages
    color_echo "Installing Tesseract OCR dependencies..."
    sudo pacman -Sy --needed $(cat pacman-deps.txt)

    # Install Tesseract OCR Script
    if [ ! -f /usr/share/tessdata/script/Latin.traineddata ]; then
      echo "Downloading Latin traineddata..."
      sudo mkdir -p /usr/share/tessdata/script
      sudo curl "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/script/Latin.traineddata" -o /usr/share/tessdata/script/Latin.traineddata
    fi
}

# Check if the OS is Arch Linux
if [ "$ID" == "arch" ]; then
  arch_install_tesseract
else
    warning_echo "Only Arch Linux is supported for installing tesseract dependencies. Please install the required packages manually."
fi

# Install python packages
color_echo "Installing Python packages..."
poetry install

# Install pre-commit hooks
color_echo "Installing pre-commit hooks..."
poetry run pre-commit install
