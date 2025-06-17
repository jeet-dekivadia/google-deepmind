"""
Configuration management for HALO framework.

This module provides secure configuration handling with environment variable support
and validation for API keys and other sensitive settings.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class HALOConfig(BaseModel):
    """Main configuration class for HALO framework."""
    
    # API Configuration
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key")
    hf_token: Optional[str] = Field(None, description="HuggingFace token for speaker diarization")
    
    # Model Configuration
    gemini_model: str = Field("gemini-1.5-flash", description="Default Gemini model")
    whisper_model: str = Field("base", description="Whisper model size")
    embedding_model: str = Field("all-MiniLM-L6-v2", description="Sentence embedding model")
    
    # Processing Configuration
    max_video_duration: float = Field(3600.0, description="Maximum video duration in seconds")
    max_chunk_duration: float = Field(300.0, description="Maximum chunk duration in seconds")
    min_chunk_duration: float = Field(30.0, description="Minimum chunk duration in seconds")
    
    # Cache Configuration
    use_redis: bool = Field(False, description="Use real Redis instead of fakeredis")
    redis_host: str = Field("localhost", description="Redis host")
    redis_port: int = Field(6379, description="Redis port")
    redis_db: int = Field(0, description="Redis database number")
    
    # Development Configuration
    use_mock_responses: bool = Field(True, description="Use mock responses for development")
    debug_mode: bool = Field(False, description="Enable debug logging")
    save_intermediate_results: bool = Field(True, description="Save intermediate processing results")
    
    # Output Configuration
    output_dir: str = Field("./halo_output", description="Output directory for results")
    export_format: str = Field("json", description="Export format (json, pickle, csv)")
    
    @validator('gemini_api_key', pre=True, always=True)
    def validate_gemini_api_key(cls, v):
        """Validate and load Gemini API key from environment if not provided."""
        if v is None:
            v = os.getenv('GEMINI_API_KEY')
            if v:
                logger.info("Loaded Gemini API key from environment variable")
            else:
                logger.warning("No Gemini API key provided. Using mock responses.")
        return v
    
    @validator('hf_token', pre=True, always=True)
    def validate_hf_token(cls, v):
        """Validate and load HuggingFace token from environment if not provided."""
        if v is None:
            v = os.getenv('HF_TOKEN')
            if v:
                logger.info("Loaded HuggingFace token from environment variable")
            else:
                logger.warning("No HuggingFace token provided. Speaker diarization may be limited.")
        return v
    
    @validator('output_dir')
    def validate_output_dir(cls, v):
        """Ensure output directory exists."""
        output_path = Path(v)
        output_path.mkdir(parents=True, exist_ok=True)
        return str(output_path.absolute())
    
    class Config:
        env_prefix = "HALO_"
        case_sensitive = False


def load_config(config_path: Optional[str] = None) -> HALOConfig:
    """
    Load HALO configuration from file or environment variables.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        HALOConfig instance
    """
    if config_path and Path(config_path).exists():
        # Load from file (future enhancement)
        logger.info(f"Loading configuration from {config_path}")
        # TODO: Implement file-based configuration loading
        pass
    
    # Load from environment variables
    config = HALOConfig()
    
    logger.info("HALO Configuration loaded:")
    logger.info(f"  Gemini Model: {config.gemini_model}")
    logger.info(f"  Whisper Model: {config.whisper_model}")
    logger.info(f"  Embedding Model: {config.embedding_model}")
    logger.info(f"  Use Mock: {config.use_mock_responses}")
    logger.info(f"  Output Dir: {config.output_dir}")
    
    return config


def save_config(config: HALOConfig, config_path: str) -> None:
    """
    Save configuration to file.
    
    Args:
        config: HALOConfig instance
        config_path: Path to save configuration
    """
    output_path = Path(config_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(config.json(indent=2))
    
    logger.info(f"Configuration saved to {config_path}")


def get_default_config() -> HALOConfig:
    """Get default configuration for development."""
    return HALOConfig(
        use_mock_responses=True,
        debug_mode=True,
        save_intermediate_results=True
    )


# Global configuration instance
_config: Optional[HALOConfig] = None


def get_config() -> HALOConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(config: HALOConfig) -> None:
    """Set global configuration instance."""
    global _config
    _config = config 