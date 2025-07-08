"""
Configuration utilities for Gemini API key and settings.
"""
import os
from typing import Optional

GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("Gemini API key not found. Set GEMINI_API_KEY environment variable or edit config.py.") 
