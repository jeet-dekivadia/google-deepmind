# HALO Quick Start Guide

Get HALO running on your system in minutes!

## 🚀 Quick Installation

### Option 1: Automated Installation (Recommended)

**macOS/Linux:**
```bash
# Clone the repository
git clone https://github.com/jeetdekivadia/halo.git
cd halo

# Run the installation script
chmod +x install.sh
./install.sh
```

**Windows:**
```cmd
# Clone the repository
git clone https://github.com/jeetdekivadia/halo.git
cd halo

# Run the installation script
install.bat
```

### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/jeetdekivadia/halo.git
cd halo

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install HALO
pip install -e .
```

## 🔐 API Key Setup

### 1. Get Your Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key

### 2. Set Up Environment Variables

**macOS/Linux:**
```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your_gemini_api_key_here"
```

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your_gemini_api_key_here
```

## 🧪 Test Your Installation

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the test script
python test_installation.py
```

You should see:
```
🚀 HALO Installation Test
==================================================
🧪 Testing HALO imports...
✅ HALO package imported successfully
✅ Core components imported successfully
...
🎉 All tests passed! HALO is ready to use.
```

## 🎬 Try the Demo

### Python Demo
```bash
python demo.py
```

### Jupyter Notebook Demo
```bash
jupyter notebook demo.ipynb
```

### Command Line Interface
```bash
# Get help
halo --help

# Process a video (mock mode)
halo process video.mp4 --query "What are the main topics?"

# Ask a question
halo ask video.mp4 "What was the conclusion?"
```

## 📝 Basic Usage

```python
from halo import HALOPipeline, load_config

# Load configuration (automatically picks up API keys)
config = load_config()

# Initialize pipeline
pipeline = HALOPipeline()

# Process a video
chunks, results, metrics = pipeline.process_video(
    "path/to/your/video.mp4",
    query="What are the main topics discussed?"
)

# Ask follow-up questions
answer = pipeline.ask_question("What conclusions were drawn?")
print(answer.response_text)
```

## 🔧 Configuration

HALO uses environment variables for configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Your Gemini API key | Required |
| `HF_TOKEN` | HuggingFace token (for speaker diarization) | Optional |
| `HALO_USE_MOCK` | Use mock responses for development | `True` |
| `HALO_DEBUG_MODE` | Enable debug logging | `False` |

## 🐛 Troubleshooting

### Common Issues

**1. Import Error: No module named 'numpy'**
```bash
pip install -r requirements.txt
```

**2. Python version error**
```bash
python3 --version  # Should be 3.10 or higher
```

**3. API key not found**
```bash
echo $GEMINI_API_KEY  # Should show your key
```

**4. Permission denied on install script**
```bash
chmod +x install.sh
```

### Getting Help

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/jeetdekivadia/halo/issues)
- **Email**: jeet.university@gmail.com

## 🎯 Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Explore the demo notebook**: `demo.ipynb`
3. **Try with your own videos**: Use the CLI or Python API
4. **Join the community**: [GitHub Discussions](https://github.com/jeetdekivadia/halo/discussions)

---

**Happy video processing with HALO! 🎬🤖** 