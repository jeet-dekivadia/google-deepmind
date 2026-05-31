"""
HALO Video - Interactive Video QA System for YouTube analysis with Gemini AI
"""

__version__ = "1.0.8"
__author__ = "Jeet Dekivadia"
__email__ = "jeet.university@gmail.com"
__description__ = "Interactive Video QA System - AI-powered YouTube video analysis with question-answering capabilities"

def main():
    """Run the HALO Video CLI without importing CLI dependencies at package import time."""
    from .cli import main as cli_main

    return cli_main()

__all__ = ["main"]
