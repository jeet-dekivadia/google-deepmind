#!/bin/bash

# HALO Video - Installation Script for Unix/Linux/macOS
# Google Summer of Code 2025 - Google DeepMind
# Author: Jeet Dekivadia

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Banner
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                         HALO Video                            ║${NC}"
echo -e "${CYAN}║               AI-Powered Video Analysis                       ║${NC}"
echo -e "${CYAN}║                                                               ║${NC}"
echo -e "${CYAN}║           Google Summer of Code 2025 - Google DeepMind       ║${NC}"
echo -e "${CYAN}║                    Author: Jeet Dekivadia                     ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running with appropriate permissions
if [[ $EUID -eq 0 ]]; then
    print_warning "This script is running as root. This is not recommended for Python package installation."
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Installation cancelled."
        exit 1
    fi
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python version
get_python_version() {
    if command_exists python3; then
        python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    elif command_exists python; then
        python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    else
        echo "0.0"
    fi
}

# Function to compare version numbers
version_ge() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Detect system
print_header "🔍 System Detection"
OS="Unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    if command_exists lsb_release; then
        DISTRO=$(lsb_release -si)
        VERSION=$(lsb_release -sr)
        print_status "Detected: $DISTRO $VERSION"
    else
        print_status "Detected: Linux (Unknown distribution)"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    VERSION=$(sw_vers -productVersion)
    print_status "Detected: macOS $VERSION"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="Windows"
    print_status "Detected: Windows (via $OSTYPE)"
else
    print_warning "Detected: Unknown OS ($OSTYPE)"
fi

# Check Python installation
print_header "🐍 Python Environment Check"
PYTHON_CMD=""
if command_exists python3; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(get_python_version)
    print_status "Found Python 3: $(which python3) (version $PYTHON_VERSION)"
elif command_exists python; then
    PYTHON_VERSION=$(get_python_version)
    if [[ $PYTHON_VERSION == 3.* ]]; then
        PYTHON_CMD="python"
        print_status "Found Python 3: $(which python) (version $PYTHON_VERSION)"
    else
        print_error "Found Python $PYTHON_VERSION, but Python 3.8+ is required"
        exit 1
    fi
else
    print_error "Python 3 is not installed or not in PATH"
    print_status "Please install Python 3.8 or later from https://python.org"
    exit 1
fi

# Check Python version compatibility
if version_ge "$PYTHON_VERSION" "3.8"; then
    print_success "Python $PYTHON_VERSION is compatible"
else
    print_error "Python $PYTHON_VERSION is not supported. Please install Python 3.8 or later."
    exit 1
fi

# Check pip installation
print_header "📦 Package Manager Check"
PIP_CMD=""
if command_exists pip3; then
    PIP_CMD="pip3"
    print_status "Found pip3: $(which pip3)"
elif command_exists pip; then
    PIP_CMD="pip"
    print_status "Found pip: $(which pip)"
else
    print_error "pip is not installed"
    print_status "Installing pip..."
    if [[ "$OS" == "macOS" ]]; then
        if command_exists brew; then
            brew install python3
        else
            print_error "Please install Homebrew or pip manually"
            exit 1
        fi
    elif [[ "$OS" == "Linux" ]]; then
        if command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y python3-pip
        elif command_exists yum; then
            sudo yum install -y python3-pip
        elif command_exists dnf; then
            sudo dnf install -y python3-pip
        else
            print_error "Unable to install pip automatically. Please install manually."
            exit 1
        fi
    fi
    
    # Recheck after installation
    if command_exists pip3; then
        PIP_CMD="pip3"
    elif command_exists pip; then
        PIP_CMD="pip"
    else
        print_error "pip installation failed"
        exit 1
    fi
fi

# Upgrade pip
print_status "Upgrading pip to latest version..."
$PYTHON_CMD -m pip install --upgrade pip

# Check for virtual environment (recommended)
print_header "🔧 Environment Setup"
if [[ -n "$VIRTUAL_ENV" ]]; then
    print_success "Virtual environment detected: $VIRTUAL_ENV"
elif [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    print_success "Conda environment detected: $CONDA_DEFAULT_ENV"
else
    print_warning "No virtual environment detected"
    echo "It's recommended to use a virtual environment to avoid conflicts."
    echo ""
    echo "To create a virtual environment:"
    echo "  python3 -m venv halo_video_env"
    echo "  source halo_video_env/bin/activate"
    echo ""
    read -p "Do you want to continue with global installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Installation cancelled. Please set up a virtual environment first."
        exit 1
    fi
fi

# Install HALO Video
print_header "🚀 Installing HALO Video"
print_status "Installing halo-video from PyPI..."

# Install with progress
$PIP_CMD install halo-video --upgrade

# Verify installation
print_header "✅ Verification"
print_status "Verifying installation..."

# Test import
if $PYTHON_CMD -c "import halo_video; print(f'HALO Video v{halo_video.__version__} installed successfully')" 2>/dev/null; then
    VERSION=$($PYTHON_CMD -c "import halo_video; print(halo_video.__version__)")
    print_success "HALO Video v$VERSION installed successfully!"
else
    print_error "Installation verification failed"
    exit 1
fi

# Test CLI
if $PYTHON_CMD -m halo_video --help >/dev/null 2>&1; then
    print_success "Command-line interface is working"
else
    print_warning "CLI test failed, but package is installed"
fi

# Check FFmpeg (will be auto-installed by imageio-ffmpeg)
print_status "Checking FFmpeg availability..."
if $PYTHON_CMD -c "import imageio_ffmpeg; print('FFmpeg available via imageio-ffmpeg')" 2>/dev/null; then
    print_success "FFmpeg is available"
else
    print_warning "FFmpeg check inconclusive (will be auto-installed when needed)"
fi

# Installation complete
print_header "🎉 Installation Complete!"
echo ""
print_success "HALO Video has been successfully installed!"
echo ""
echo -e "${CYAN}📋 Quick Start:${NC}"
echo "1. Set up your Google Gemini API key:"
echo "   export GEMINI_API_KEY='your-api-key-here'"
echo ""
echo "2. Analyze a video:"
echo "   halo-video path/to/your/video.mp4"
echo ""
echo "3. Get help:"
echo "   halo-video --help"
echo ""
echo -e "${CYAN}📚 Documentation:${NC}"
echo "• Project Repository: https://github.com/jeet-dekivadia/google-deepmind"
echo "• PyPI Package: https://pypi.org/project/halo-video/"
echo "• GSoC Documentation: GSoC_PROJECT_DOCUMENTATION.md"
echo ""
echo -e "${CYAN}🎓 Academic Context:${NC}"
echo "• Google Summer of Code 2025 project"
echo "• Developed at Google DeepMind"
echo "• Research focus: AI-powered video analysis optimization"
echo ""
echo -e "${CYAN}🤝 Support:${NC}"
echo "• Issues: https://github.com/jeet-dekivadia/google-deepmind/issues"
echo "• Contributing: See CONTRIBUTING.md"
echo "• Contact: Jeet Dekivadia (jeet.dekivadia@example.com)"
echo ""
print_success "Ready to analyze videos with AI! 🎬🤖"
