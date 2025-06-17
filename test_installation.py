#!/usr/bin/env python3
"""
HALO Installation Test Script

This script tests the basic installation and import of HALO components
to ensure everything is working correctly.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test importing HALO components."""
    print("🧪 Testing HALO imports...")
    
    try:
        # Test basic imports
        import halo
        print("✅ HALO package imported successfully")
        
        # Test core components
        from halo import HALOPipeline, HALOConfig, get_config
        print("✅ Core components imported successfully")
        
        # Test models
        from halo.models import VideoChunk, ProcessingResult, PipelineMetrics
        print("✅ Data models imported successfully")
        
        # Test extractors
        from halo.extractors import AudioExtractor, VideoExtractor, TextExtractor
        print("✅ Extractors imported successfully")
        
        # Test chunkers
        from halo.chunkers import RuleBasedChunker, RLChunker
        print("✅ Chunkers imported successfully")
        
        # Test cache
        from halo.cache import ThreeTierCache
        print("✅ Cache system imported successfully")
        
        # Test Gemini API
        from halo.gemini import GeminiAPI
        print("✅ Gemini API imported successfully")
        
        # Test configuration
        from halo.config import load_config
        print("✅ Configuration system imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")
    
    try:
        from halo.config import load_config, HALOConfig
        
        # Test default configuration
        config = HALOConfig()
        print("✅ Default configuration created successfully")
        
        # Test configuration loading
        config = load_config()
        print("✅ Configuration loaded successfully")
        
        print(f"   Gemini Model: {config.gemini_model}")
        print(f"   Whisper Model: {config.whisper_model}")
        print(f"   Use Mock: {config.use_mock_responses}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_pipeline_initialization():
    """Test pipeline initialization."""
    print("\n🚀 Testing pipeline initialization...")
    
    try:
        from halo import HALOPipeline
        from halo.models import ChunkingConfig, CacheConfig, GeminiConfig
        
        # Test with default configs
        pipeline = HALOPipeline()
        print("✅ Pipeline initialized with default configs")
        
        # Test with custom configs
        chunking_config = ChunkingConfig(max_chunk_duration=300.0)
        cache_config = CacheConfig(use_fakeredis=True)
        gemini_config = GeminiConfig(use_mock=True)
        
        pipeline = HALOPipeline(
            chunking_config=chunking_config,
            cache_config=cache_config,
            gemini_config=gemini_config
        )
        print("✅ Pipeline initialized with custom configs")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline initialization error: {e}")
        return False

def test_mock_processing():
    """Test mock video processing."""
    print("\n🎬 Testing mock video processing...")
    
    try:
        from halo import HALOPipeline
        from halo.models import ChunkingConfig, CacheConfig, GeminiConfig
        
        # Create pipeline with mock settings
        pipeline = HALOPipeline(
            chunking_config=ChunkingConfig(max_chunk_duration=300.0),
            cache_config=CacheConfig(use_fakeredis=True),
            gemini_config=GeminiConfig(use_mock=True)
        )
        
        # Test mock chunk creation
        from halo.models import VideoChunk, TranscriptionSegment
        
        # Create a mock chunk
        mock_segments = [
            TranscriptionSegment(
                start_time=0, end_time=30,
                text="This is a test transcription segment.",
                confidence=0.9
            )
        ]
        
        chunk = VideoChunk(
            chunk_id="test_chunk_0001",
            start_time=0,
            end_time=30,
            duration=30,
            transcription="This is a test transcription.",
            transcription_segments=mock_segments,
            chunking_method="rule_based",
            coherence_score=0.85,
            fragmentation_penalty=0.1
        )
        
        print("✅ Mock chunk created successfully")
        
        # Test mock processing
        result = pipeline.gemini_api.process_chunk(chunk)
        print("✅ Mock processing completed successfully")
        print(f"   Response: {result.response_text[:50]}...")
        print(f"   Tokens: {result.tokens_used}")
        print(f"   Cost: ${result.cost:.6f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock processing error: {e}")
        return False

def test_cli():
    """Test CLI functionality."""
    print("\n💻 Testing CLI...")
    
    try:
        from halo.cli import create_parser
        
        parser = create_parser()
        print("✅ CLI parser created successfully")
        
        # Test help
        help_output = parser.format_help()
        if "HALO" in help_output and "process" in help_output:
            print("✅ CLI help output looks correct")
        else:
            print("⚠️  CLI help output may be incomplete")
        
        return True
        
    except Exception as e:
        print(f"❌ CLI error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 HALO Installation Test")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Pipeline Initialization", test_pipeline_initialization),
        ("Mock Processing", test_mock_processing),
        ("CLI", test_cli),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! HALO is ready to use.")
        print("\n🎯 Next steps:")
        print("1. Set up your API keys (see README.md)")
        print("2. Run: python demo.py")
        print("3. Or: jupyter notebook demo.ipynb")
        print("4. Or: halo --help")
    else:
        print("⚠️  Some tests failed. Please check the installation.")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure all dependencies are installed: pip install -r requirements.txt")
        print("2. Check Python version (3.10+ required)")
        print("3. Ensure you're in the correct directory")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 