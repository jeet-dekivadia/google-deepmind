"""
Data models for HALO framework using Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
import numpy as np


class VideoMetadata(BaseModel):
    """Metadata about the input video."""
    duration: float = Field(..., description="Video duration in seconds")
    fps: float = Field(..., description="Frames per second")
    resolution: tuple = Field(..., description="Video resolution (width, height)")
    audio_sample_rate: int = Field(..., description="Audio sample rate in Hz")
    file_size: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Video format")


class SpeakerSegment(BaseModel):
    """Represents a speaker segment with timing information."""
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    speaker_id: str = Field(..., description="Unique speaker identifier")
    confidence: float = Field(..., description="Speaker detection confidence")


class SceneSegment(BaseModel):
    """Represents a scene segment with timing information."""
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    scene_id: int = Field(..., description="Unique scene identifier")
    confidence: float = Field(..., description="Scene change confidence")


class TranscriptionSegment(BaseModel):
    """Represents a transcription segment with timing and text."""
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Transcription confidence")
    speaker_id: Optional[str] = Field(None, description="Associated speaker ID")


class TopicSegment(BaseModel):
    """Represents a topic segment with timing and topic information."""
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    topic_id: int = Field(..., description="Unique topic identifier")
    topic_name: str = Field(..., description="Topic name/label")
    confidence: float = Field(..., description="Topic detection confidence")


class VideoChunk(BaseModel):
    """Represents a semantically coherent video chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    duration: float = Field(..., description="Chunk duration in seconds")
    
    # Content
    transcription: str = Field(..., description="Full transcription text")
    transcription_segments: List[TranscriptionSegment] = Field(default_factory=list)
    
    # Metadata
    speakers: List[SpeakerSegment] = Field(default_factory=list)
    scenes: List[SceneSegment] = Field(default_factory=list)
    topics: List[TopicSegment] = Field(default_factory=list)
    
    # Features
    embeddings: Optional[np.ndarray] = Field(None, description="Text embeddings")
    audio_features: Optional[np.ndarray] = Field(None, description="Audio features")
    visual_features: Optional[np.ndarray] = Field(None, description="Visual features")
    
    # Chunking metadata
    chunking_method: str = Field(..., description="Method used for chunking")
    coherence_score: float = Field(..., description="Semantic coherence score")
    fragmentation_penalty: float = Field(0.0, description="Fragmentation penalty")
    
    class Config:
        arbitrary_types_allowed = True


class ProcessingResult(BaseModel):
    """Result of processing a video chunk through Gemini API."""
    chunk_id: str = Field(..., description="Associated chunk ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # API response
    response_text: str = Field(..., description="Gemini API response text")
    model_used: str = Field(..., description="Gemini model used")
    tokens_used: int = Field(..., description="Number of tokens used")
    cost: float = Field(..., description="API cost in USD")
    
    # Processing metadata
    processing_time: float = Field(..., description="Processing time in seconds")
    cache_hit: bool = Field(False, description="Whether result was cached")
    cache_level: Optional[int] = Field(None, description="Cache level hit (1-3)")
    
    # Quality metrics
    relevance_score: float = Field(..., description="Response relevance score")
    coherence_score: float = Field(..., description="Response coherence score")


class CacheEntry(BaseModel):
    """Entry in the three-tier cache system."""
    key: str = Field(..., description="Cache key")
    value: Any = Field(..., description="Cached value")
    timestamp: datetime = Field(default_factory=datetime.now)
    access_count: int = Field(0, description="Number of times accessed")
    size_bytes: int = Field(..., description="Size in bytes")
    cache_level: int = Field(..., description="Cache level (1-3)")
    
    class Config:
        arbitrary_types_allowed = True


class PipelineMetrics(BaseModel):
    """Metrics collected during pipeline execution."""
    total_duration: float = Field(..., description="Total processing time")
    total_tokens: int = Field(0, description="Total tokens used")
    total_cost: float = Field(0.0, description="Total API cost")
    
    # Cache metrics
    cache_hits: int = Field(0, description="Number of cache hits")
    cache_misses: int = Field(0, description="Number of cache misses")
    cache_hit_rate: float = Field(0.0, description="Cache hit rate")
    
    # Chunking metrics
    num_chunks: int = Field(0, description="Number of chunks created")
    avg_chunk_duration: float = Field(0.0, description="Average chunk duration")
    coherence_scores: List[float] = Field(default_factory=list)
    
    # API metrics
    api_calls: int = Field(0, description="Number of API calls made")
    avg_response_time: float = Field(0.0, description="Average API response time")


class ChunkingConfig(BaseModel):
    """Configuration for video chunking strategies."""
    # Rule-based chunking
    max_chunk_duration: float = Field(300.0, description="Maximum chunk duration in seconds")
    min_chunk_duration: float = Field(30.0, description="Minimum chunk duration in seconds")
    speaker_change_threshold: float = Field(0.8, description="Speaker change confidence threshold")
    scene_change_threshold: float = Field(0.7, description="Scene change confidence threshold")
    
    # RL chunking
    use_rl_chunker: bool = Field(False, description="Whether to use RL-based chunking")
    rl_model_path: Optional[str] = Field(None, description="Path to trained RL model")
    rl_training_episodes: int = Field(1000, description="Number of training episodes")
    
    # Coherence scoring
    coherence_threshold: float = Field(0.7, description="Minimum coherence score")
    fragmentation_penalty_weight: float = Field(0.3, description="Weight for fragmentation penalty")


class CacheConfig(BaseModel):
    """Configuration for the three-tier cache system."""
    # Level 1: Exact match cache
    l1_max_size: int = Field(1000, description="Maximum entries in L1 cache")
    l1_ttl: int = Field(3600, description="L1 cache TTL in seconds")
    
    # Level 2: Semantic cache
    l2_max_size: int = Field(500, description="Maximum entries in L2 cache")
    l2_ttl: int = Field(7200, description="L2 cache TTL in seconds")
    l2_similarity_threshold: float = Field(0.85, description="Semantic similarity threshold")
    
    # Level 3: Summary cache
    l3_max_size: int = Field(200, description="Maximum entries in L3 cache")
    l3_ttl: int = Field(86400, description="L3 cache TTL in seconds")
    
    # Redis configuration
    redis_host: str = Field("localhost", description="Redis host")
    redis_port: int = Field(6379, description="Redis port")
    redis_db: int = Field(0, description="Redis database number")
    use_fakeredis: bool = Field(True, description="Use fakeredis for testing")


class GeminiConfig(BaseModel):
    """Configuration for Gemini API integration."""
    api_key: Optional[str] = Field(None, description="Gemini API key")
    model_name: str = Field("gemini-1.5-flash", description="Gemini model to use")
    max_tokens: int = Field(8192, description="Maximum tokens per request")
    temperature: float = Field(0.1, description="Sampling temperature")
    
    # Batching
    batch_size: int = Field(5, description="Number of chunks to batch")
    max_batch_tokens: int = Field(32000, description="Maximum tokens per batch")
    
    # Fallback
    fallback_model: str = Field("gemini-1.5-pro", description="Fallback model")
    use_mock: bool = Field(True, description="Use mock responses for development") 