"""
Configuration utilities for Gemini API key and settings.

SETUP INSTRUCTIONS:
1. Copy this file to config.py
2. Set your GEMINI_API_KEY environment variable, OR
3. Replace 'your_api_key_here' with your actual API key (NOT RECOMMENDED for production)

Get your free API key at: https://makersuite.google.com/app/apikey
"""
import os
from typing import Optional

# Recommended: Use environment variable
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

# Alternative: Set directly (NOT RECOMMENDED - remove before committing to git)
# GEMINI_API_KEY = "your_api_key_here"

if not GEMINI_API_KEY:
    raise RuntimeError(
        "Gemini API key not found. Please:\n"
        "1. Set GEMINI_API_KEY environment variable, OR\n"
        "2. Edit config.py with your API key\n"
        "Get your free API key at: https://makersuite.google.com/app/apikey"
    )
