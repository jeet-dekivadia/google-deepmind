@echo off
REM HALO Installation Script for Windows
REM Hierarchical Abstraction for Longform Optimization

echo 🚀 HALO Installation Script
echo ==========================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ❌ Error: Failed to create virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment created

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated

REM Upgrade pip
echo.
echo ⬆️  Upgrading pip...
python -m pip install --upgrade pip

REM Install package and development dependencies
echo.
echo 📚 Installing HALO and development dependencies...
pip install -e ".[dev]"
if errorlevel 1 (
    echo ❌ Error: Failed to install HALO and dependencies
    pause
    exit /b 1
)

echo.
echo ✅ HALO installation completed successfully!
echo.

REM Check for API keys
echo 🔐 API Key Configuration
echo =======================
echo.

if "%GEMINI_API_KEY%"=="" (
    echo ⚠️  GEMINI_API_KEY not found in environment variables
    echo    To set it up, run:
    echo    set GEMINI_API_KEY=your_api_key_here
    echo.
) else (
    echo ✅ GEMINI_API_KEY found in environment
)

if "%HF_TOKEN%"=="" (
    echo ⚠️  HF_TOKEN not found in environment variables
    echo    To set it up, run:
    echo    set HF_TOKEN=your_huggingface_token_here
    echo.
) else (
    echo ✅ HF_TOKEN found in environment
)

echo.
echo 🎯 Next Steps:
echo ==============
echo 1. Activate the virtual environment:
echo    venv\Scripts\activate.bat
echo.
echo 2. Set up your API keys (see README.md for instructions)
echo.
echo 3. Run the demo:
echo    python demo.py
echo.
echo 4. Or start the Jupyter notebook:
echo    jupyter notebook demo.ipynb
echo.
echo 5. Use the CLI:
echo    halo-video --help
echo.
echo 📚 For more information, see README.md
echo.
echo 🎉 Happy video processing with HALO!
echo.
pause 
