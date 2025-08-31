#!/usr/bin/env python3
"""
Basic tests for HALO pipeline components.

This script tests the core functionality of the HALO framework
to ensure all components work together correctly.
"""

import sys
import os
import unittest
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from halo import HALOPipeline
from halo.models import (
    ChunkingConfig, CacheConfig, GeminiConfig,
    VideoChunk, ProcessingResult, TranscriptionSegment
)
from halo.extractors import AudioExtractor, VideoExtractor, TextExtractor
from halo.chunkers import RuleBasedChunker
from halo.cache import ThreeTierCache
from halo.gemini import GeminiAPI


class TestHALOComponents(unittest.TestCase):
    """Test basic HALO components functionality."""
    
    def setUp(self):
        """Set up test configurations."""
        self.chunking_config = ChunkingConfig(
            max_chunk_duration=180.0,
            min_chunk_duration=30.0,
            use_rl_chunker=False
        )
        
        self.cache_config = CacheConfig(
            use_fakeredis=True,
            l2_similarity_threshold=0.85
        )
        
        self.gemini_config = GeminiConfig(
            model_name="gemini-1.5-flash",
            use_mock=True
        )
    
    def test_pipeline_initialization(self):
        """Test that HALO pipeline initializes correctly."""
        pipeline = HALOPipeline(
            chunking_config=self.chunking_config,
            cache_config=self.cache_config,
            gemini_config=self.gemini_config
        )
        
        self.assertIsNotNone(pipeline)
        self.assertIsNotNone(pipeline.audio_extractor)
        self.assertIsNotNone(pipeline.video_extractor)
        self.assertIsNotNone(pipeline.text_extractor)
        self.assertIsNotNone(pipeline.rule_chunker)
        self.assertIsNotNone(pipeline.cache)
        self.assertIsNotNone(pipeline.gemini_api)
    
    def test_extractors_initialization(self):
        """Test that extractors initialize correctly."""
        audio_extractor = AudioExtractor()
        video_extractor = VideoExtractor()
        text_extractor = TextExtractor()
        
        self.assertIsNotNone(audio_extractor.whisper_model)
        self.assertIsNotNone(text_extractor.embedding_model)
    
    def test_chunker_initialization(self):
        """Test that chunkers initialize correctly."""
        rule_chunker = RuleBasedChunker(self.chunking_config)
        self.assertIsNotNone(rule_chunker)
        self.assertEqual(rule_chunker.config.max_chunk_duration, 180.0)
    
    def test_cache_initialization(self):
        """Test that cache initializes correctly."""
        cache = ThreeTierCache(self.cache_config)
        self.assertIsNotNone(cache)
        self.assertIsNotNone(cache.redis_client)
    
    def test_gemini_api_initialization(self):
        """Test that Gemini API initializes correctly."""
        gemini_api = GeminiAPI(self.gemini_config)
        self.assertIsNotNone(gemini_api)
        self.assertTrue(gemini_api.config.use_mock)
    
    def test_mock_video_processing(self):
        """Test mock video processing workflow."""
        pipeline = HALOPipeline(
            chunking_config=self.chunking_config,
            cache_config=self.cache_config,
            gemini_config=self.gemini_config
        )
        
        # Create mock transcription segments
        mock_segments = [
            TranscriptionSegment(
                start_time=0, end_time=30,
                text="Welcome to this presentation about artificial intelligence.",
                confidence=0.9
            ),
            TranscriptionSegment(
                start_time=30, end_time=60,
                text="Today we'll discuss machine learning algorithms.",
                confidence=0.9
            ),
            TranscriptionSegment(
                start_time=60, end_time=90,
                text="Deep learning has revolutionized many fields.",
                confidence=0.9
            )
        ]
        
        # Create mock chunks
        chunks = []
        for i in range(2):
            start_time = i * 45
            end_time = (i + 1) * 45
            chunk_segments = [
                seg for seg in mock_segments
                if seg.start_time >= start_time and seg.end_time <= end_time
            ]
            
            chunk = VideoChunk(
                chunk_id=f"test_chunk_{i:04d}",
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                transcription=" ".join([seg.text for seg in chunk_segments]),
                transcription_segments=chunk_segments,
                chunking_method="rule_based",
                coherence_score=0.85,
                fragmentation_penalty=0.1
            )
            chunks.append(chunk)
        
        # Test chunk processing
        for chunk in chunks:
            result = pipeline.gemini_api.process_chunk(chunk)
            self.assertIsNotNone(result)
            self.assertEqual(result.chunk_id, chunk.chunk_id)
            self.assertGreater(result.tokens_used, 0)
            self.assertGreaterEqual(result.cost, 0.0)
    
    def test_cache_operations(self):
        """Test cache operations."""
        cache = ThreeTierCache(self.cache_config)
        
        # Test put and get operations
        test_key = "test_key"
        test_value = {"data": "test_value"}
        
        cache.put(test_key, test_value, level=1)
        retrieved_value = cache.get(test_key)
        
        self.assertEqual(retrieved_value, test_value)
        
        # Test cache statistics
        stats = cache.get_stats()
        self.assertIn('total_requests', stats)
        self.assertIn('hit_rate', stats)
    
    def test_question_answering(self):
        """Test question answering functionality."""
        pipeline = HALOPipeline(
            chunking_config=self.chunking_config,
            cache_config=self.cache_config,
            gemini_config=self.gemini_config
        )
        
        # Create mock chunks
        mock_chunks = [
            VideoChunk(
                chunk_id="test_chunk_0001",
                start_time=0,
                end_time=60,
                duration=60,
                transcription="This is a test video about artificial intelligence and machine learning.",
                transcription_segments=[],
                chunking_method="rule_based",
                coherence_score=0.85,
                fragmentation_penalty=0.1
            )
        ]
        
        pipeline.chunks = mock_chunks
        
        # Test question answering
        question = "What is this video about?"
        answer = pipeline.ask_question(question)
        
        self.assertIsNotNone(answer)
        self.assertIsNotNone(answer.response_text)
        self.assertGreater(answer.tokens_used, 0)
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Test valid configurations
        valid_chunking = ChunkingConfig(
            max_chunk_duration=300.0,
            min_chunk_duration=30.0
        )
        self.assertEqual(valid_chunking.max_chunk_duration, 300.0)
        
        valid_cache = CacheConfig(
            l1_max_size=1000,
            use_fakeredis=True
        )
        self.assertEqual(valid_cache.l1_max_size, 1000)
        
        valid_gemini = GeminiConfig(
            model_name="gemini-1.5-flash",
            use_mock=True
        )
        self.assertEqual(valid_gemini.model_name, "gemini-1.5-flash")


def run_basic_tests():
    """Run basic tests and print results."""
    print("🧪 Running HALO Basic Tests")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestHALOComponents)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1) 