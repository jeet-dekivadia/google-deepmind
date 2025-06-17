#!/usr/bin/env python3
"""
HALO Demo: Hierarchical Abstraction for Longform Optimization

This script demonstrates the HALO framework for optimizing Gemini API usage 
in long-form video analysis.

Usage:
    python demo.py
"""

import sys
import os
import logging
import numpy as np
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import HALO components
from halo import HALOPipeline
from halo.models import ChunkingConfig, CacheConfig, GeminiConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main demo function."""
    print("HALO Demo - Hierarchical Abstraction for Longform Optimization")
    print("=" * 60)
    
    # Configure HALO pipeline components
    chunking_config = ChunkingConfig(
        max_chunk_duration=180.0,  # 3 minutes max
        min_chunk_duration=30.0,   # 30 seconds min
        speaker_change_threshold=0.8,
        scene_change_threshold=0.7,
        coherence_threshold=0.7,
        use_rl_chunker=False  # Use rule-based for demo
    )
    
    cache_config = CacheConfig(
        l1_max_size=100,
        l2_max_size=50,
        l3_max_size=20,
        l2_similarity_threshold=0.85,
        use_fakeredis=True  # Use fake Redis for demo
    )
    
    gemini_config = GeminiConfig(
        model_name="gemini-1.5-flash",
        max_tokens=8192,
        temperature=0.1,
        batch_size=3,
        use_mock=True  # Use mock responses for demo
    )
    
    print("Configuration:")
    print(f"  Chunking: {chunking_config.max_chunk_duration}s max, {chunking_config.min_chunk_duration}s min")
    print(f"  Cache: L1={cache_config.l1_max_size}, L2={cache_config.l2_max_size}, L3={cache_config.l3_max_size}")
    print(f"  Gemini: {gemini_config.model_name}, batch_size={gemini_config.batch_size}")
    
    # Initialize HALO pipeline
    pipeline = HALOPipeline(
        chunking_config=chunking_config,
        cache_config=cache_config,
        gemini_config=gemini_config
    )
    
    print("✅ HALO Pipeline initialized successfully")
    
    # Simulate video processing with mock data
    print("\n📝 Simulating video processing with mock data...")
    
    # Create mock chunks and results for demonstration
    from halo.models import VideoChunk, ProcessingResult, TranscriptionSegment
    
    # Mock transcription segments
    mock_segments = [
        TranscriptionSegment(start_time=0, end_time=30, text="Welcome to this presentation about artificial intelligence.", confidence=0.9),
        TranscriptionSegment(start_time=30, end_time=60, text="Today we'll discuss machine learning algorithms and their applications.", confidence=0.9),
        TranscriptionSegment(start_time=60, end_time=90, text="Deep learning has revolutionized many fields including computer vision.", confidence=0.9),
        TranscriptionSegment(start_time=90, end_time=120, text="Let's explore some practical examples and use cases.", confidence=0.9),
        TranscriptionSegment(start_time=120, end_time=150, text="In conclusion, AI is transforming our world in remarkable ways.", confidence=0.9)
    ]
    
    # Create mock chunks
    chunks = []
    results = []
    
    for i in range(3):
        start_time = i * 50
        end_time = (i + 1) * 50
        chunk_segments = [seg for seg in mock_segments if seg.start_time >= start_time and seg.end_time <= end_time]
        
        chunk = VideoChunk(
            chunk_id=f"chunk_{i:04d}",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            transcription=" ".join([seg.text for seg in chunk_segments]),
            transcription_segments=chunk_segments,
            chunking_method="rule_based",
            coherence_score=0.85 + (i * 0.05),
            fragmentation_penalty=0.1
        )
        chunks.append(chunk)
        
        # Create mock result
        result = ProcessingResult(
            chunk_id=chunk.chunk_id,
            response_text=f"Mock analysis of chunk {i+1}: This segment discusses AI and machine learning topics with good coherence.",
            model_used="gemini-1.5-flash",
            tokens_used=150 + (i * 50),
            cost=0.0001 + (i * 0.00005),
            processing_time=0.5 + (i * 0.2),
            relevance_score=0.8 + (i * 0.05),
            coherence_score=0.85 + (i * 0.05)
        )
        results.append(result)
    
    # Update pipeline state
    pipeline.chunks = chunks
    pipeline.results = results
    
    print(f"✅ Mock processing completed!")
    print(f"   Chunks created: {len(chunks)}")
    print(f"   Results generated: {len(results)}")
    
    # Display chunk information
    print("\n📊 CHUNK ANALYSIS")
    print("=" * 50)
    
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}: {chunk.chunk_id}")
        print(f"  Duration: {chunk.duration:.1f}s ({chunk.start_time:.1f}s - {chunk.end_time:.1f}s)")
        print(f"  Coherence Score: {chunk.coherence_score:.3f}")
        print(f"  Fragmentation Penalty: {chunk.fragmentation_penalty:.3f}")
        print(f"  Transcription: {chunk.transcription[:100]}...")
        print(f"  Method: {chunk.chunking_method}")
    
    # Ask questions about the processed video
    questions = [
        "What are the main topics discussed in this video?",
        "How does the speaker explain machine learning?",
        "What conclusions are drawn about AI?"
    ]
    
    print("\n❓ INTERACTIVE Q&A DEMO")
    print("=" * 50)
    
    for i, question in enumerate(questions, 1):
        print(f"\nQuestion {i}: {question}")
        print("-" * 40)
        
        try:
            answer = pipeline.ask_question(question)
            print(f"Answer: {answer.response_text}")
            print(f"Processing Time: {answer.processing_time:.2f}s")
            print(f"Tokens Used: {answer.tokens_used:,}")
            print(f"Cost: ${answer.cost:.6f}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Get cache statistics
    cache_stats = pipeline.get_cache_stats()
    
    print("\n🗄️  CACHE PERFORMANCE")
    print("=" * 50)
    print(f"Total Requests: {cache_stats['total_requests']}")
    print(f"L1 Hits (Exact Match): {cache_stats['l1_hits']}")
    print(f"L2 Hits (Semantic): {cache_stats['l2_hits']}")
    print(f"L3 Hits (Summary): {cache_stats['l3_hits']}")
    print(f"Cache Misses: {cache_stats['misses']}")
    print(f"Overall Hit Rate: {cache_stats['hit_rate']:.2%}")
    print(f"\nCache Sizes:")
    print(f"  L1 Cache: {cache_stats['l1_size']} entries")
    print(f"  L2 Cache: {cache_stats['l2_size']} entries")
    print(f"  L3 Cache: {cache_stats['l3_size']} entries")
    print(f"  Total: {cache_stats['total_size']} entries")
    
    # Export results to JSON
    export_path = "halo_demo_results.json"
    pipeline.export_results(export_path)
    
    print(f"\n✅ Results exported to: {export_path}")
    print(f"   File contains: chunks, results, metrics, and cache statistics")
    print(f"   Use this data for further analysis or integration")
    
    # Summary
    print("\n🎯 HALO DEMO SUMMARY")
    print("=" * 50)
    print(f"✅ Successfully processed video with {len(chunks)} chunks")
    print(f"✅ Generated {len(results)} analysis results")
    print(f"✅ Maintained {np.mean([chunk.coherence_score for chunk in chunks]):.3f} average coherence")
    print(f"✅ Implemented three-tier caching with {cache_stats['hit_rate']:.2%} hit rate")
    print(f"✅ Demonstrated interactive Q&A capabilities")
    
    print("\n🚀 NEXT STEPS")
    print("=" * 30)
    print("1. Replace mock responses with real Gemini API calls")
    print("2. Test with longer videos (1+ hours)")
    print("3. Train and evaluate RL chunker on real data")
    print("4. Implement advanced semantic caching strategies")
    print("5. Add support for real-time video processing")
    print("6. Integrate with production systems")

if __name__ == "__main__":
    main() 