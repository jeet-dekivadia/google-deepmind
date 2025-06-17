"""
HALO - Hierarchical Abstraction for Longform Optimization

A modular, efficient, and production-ready Python framework for processing 
long-form videos through Gemini APIs while minimizing cost and maximizing 
context retention.
"""

__version__ = "0.1.0"
__author__ = "Jeet Dekivadia"
__email__ = "jeet.dekivadia@gmail.com"

from .pipeline import HALOPipeline
from .models import VideoChunk, ProcessingResult, CacheEntry
from .extractors import AudioExtractor, VideoExtractor, TextExtractor
from .chunkers import RuleBasedChunker, RLChunker
from .cache import ThreeTierCache
from .gemini import GeminiAPI

__all__ = [
    "HALOPipeline",
    "VideoChunk", 
    "ProcessingResult",
    "CacheEntry",
    "AudioExtractor",
    "VideoExtractor", 
    "TextExtractor",
    "RuleBasedChunker",
    "RLChunker",
    "ThreeTierCache",
    "GeminiAPI",
] 