"""
Main HALO pipeline for end-to-end video processing.

This module orchestrates the complete pipeline from video input to
processed results, including feature extraction, chunking, caching,
and Gemini API processing.
"""

import logging
import time
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio

from .models import (
    VideoChunk, ProcessingResult, PipelineMetrics, 
    ChunkingConfig, CacheConfig, GeminiConfig
)
from .extractors import AudioExtractor, VideoExtractor, TextExtractor
from .chunkers import RuleBasedChunker, RLChunker
from .cache import ThreeTierCache
from .gemini import GeminiAPI

logger = logging.getLogger(__name__)


class HALOPipeline:
    """Main pipeline for Hierarchical Abstraction for Longform Optimization."""
    
    def __init__(
        self,
        chunking_config: Optional[ChunkingConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        gemini_config: Optional[GeminiConfig] = None
    ):
        """
        Initialize the HALO pipeline.
        
        Args:
            chunking_config: Configuration for chunking strategies
            cache_config: Configuration for caching system
            gemini_config: Configuration for Gemini API
        """
        # Set default configurations
        self.chunking_config = chunking_config or ChunkingConfig()
        self.cache_config = cache_config or CacheConfig()
        self.gemini_config = gemini_config or GeminiConfig()
        
        # Initialize components
        self.audio_extractor = AudioExtractor()
        self.video_extractor = VideoExtractor()
        self.text_extractor = TextExtractor()
        
        self.rule_chunker = RuleBasedChunker(self.chunking_config)
        self.rl_chunker = RLChunker(self.chunking_config)
        
        self.cache = ThreeTierCache(self.cache_config)
        self.gemini_api = GeminiAPI(self.gemini_config)
        
        # Pipeline state
        self.chunks: List[VideoChunk] = []
        self.results: List[ProcessingResult] = []
        self.metrics = PipelineMetrics(total_duration=0.0)
        
        logger.info("HALO pipeline initialized")
    
    def process_video(
        self, 
        video_path: str, 
        query: Optional[str] = None,
        use_rl_chunker: bool = False
    ) -> Tuple[List[VideoChunk], List[ProcessingResult], PipelineMetrics]:
        """
        Process a video through the complete HALO pipeline.
        
        Args:
            video_path: Path to input video file
            query: Optional query to ask about the video
            use_rl_chunker: Whether to use RL-based chunking
            
        Returns:
            Tuple of (chunks, results, metrics)
        """
        start_time = time.time()
        logger.info(f"Starting HALO pipeline for video: {video_path}")
        
        try:
            # Step 1: Extract video metadata
            logger.info("Step 1: Extracting video metadata")
            video_metadata = self.video_extractor.extract_video_metadata(video_path)
            
            # Step 2: Extract multimodal features
            logger.info("Step 2: Extracting multimodal features")
            features = self._extract_features(video_path)
            
            # Step 3: Create chunks
            logger.info("Step 3: Creating video chunks")
            self.chunks = self._create_chunks(features, video_metadata.duration, use_rl_chunker)
            
            # Step 4: Process chunks through Gemini API
            logger.info("Step 4: Processing chunks through Gemini API")
            self.results = self._process_chunks(query)
            
            # Step 5: Calculate metrics
            logger.info("Step 5: Calculating metrics")
            self.metrics = self._calculate_metrics(start_time)
            
            # Step 6: Print summary
            self._print_summary()
            
            logger.info("HALO pipeline completed successfully")
            return self.chunks, self.results, self.metrics
            
        except Exception as e:
            logger.error(f"Error in HALO pipeline: {e}")
            raise
    
    def _extract_features(self, video_path: str) -> Dict[str, Any]:
        """Extract all multimodal features from video."""
        features = {}
        
        # Audio features
        logger.info("Extracting audio features")
        try:
            audio_features, sample_rate = self.audio_extractor.extract_audio_features(video_path)
            features['audio_features'] = audio_features
            features['sample_rate'] = sample_rate
        except Exception as e:
            logger.warning(f"Error extracting audio features: {e}")
            features['audio_features'] = None
            features['sample_rate'] = 44100
        
        # Transcription
        logger.info("Transcribing audio")
        try:
            transcription_segments = self.audio_extractor.transcribe_audio(video_path)
            features['transcription_segments'] = transcription_segments
        except Exception as e:
            logger.warning(f"Error transcribing audio: {e}")
            features['transcription_segments'] = []
        
        # Speaker diarization
        logger.info("Performing speaker diarization")
        try:
            speaker_segments = self.audio_extractor.perform_speaker_diarization(video_path)
            features['speaker_segments'] = speaker_segments
        except Exception as e:
            logger.warning(f"Error performing speaker diarization: {e}")
            features['speaker_segments'] = []
        
        # Scene detection
        logger.info("Detecting scene changes")
        try:
            scene_segments = self.video_extractor.detect_scene_changes(video_path)
            features['scene_segments'] = scene_segments
        except Exception as e:
            logger.warning(f"Error detecting scene changes: {e}")
            features['scene_segments'] = []
        
        # Frame features
        logger.info("Extracting frame features")
        try:
            frame_features = self.video_extractor.extract_frame_features(video_path, sample_rate=30)
            features['frame_features'] = frame_features
        except Exception as e:
            logger.warning(f"Error extracting frame features: {e}")
            features['frame_features'] = None
        
        # Topic modeling
        logger.info("Performing topic modeling")
        try:
            if features['transcription_segments']:
                texts = [seg.text for seg in features['transcription_segments']]
                self.text_extractor.setup_topic_modeling()
                topic_segments = self.text_extractor.perform_topic_modeling(texts)
                features['topic_segments'] = topic_segments
            else:
                features['topic_segments'] = []
        except Exception as e:
            logger.warning(f"Error performing topic modeling: {e}")
            features['topic_segments'] = []
        
        # Text embeddings
        logger.info("Extracting text embeddings")
        try:
            if features['transcription_segments']:
                texts = [seg.text for seg in features['transcription_segments']]
                embeddings = self.text_extractor.extract_embeddings(texts)
                features['text_embeddings'] = embeddings
            else:
                features['text_embeddings'] = None
        except Exception as e:
            logger.warning(f"Error extracting text embeddings: {e}")
            features['text_embeddings'] = None
        
        return features
    
    def _create_chunks(
        self, 
        features: Dict[str, Any], 
        video_duration: float,
        use_rl_chunker: bool
    ) -> List[VideoChunk]:
        """Create video chunks using selected chunking strategy."""
        transcription_segments = features.get('transcription_segments', [])
        speaker_segments = features.get('speaker_segments', [])
        scene_segments = features.get('scene_segments', [])
        topic_segments = features.get('topic_segments', [])
        
        if use_rl_chunker and self.chunking_config.use_rl_chunker:
            logger.info("Using RL-based chunking")
            
            # Train RL chunker if needed
            if transcription_segments:
                self.rl_chunker.train(transcription_segments, episodes=100)  # Reduced for MVP
            
            chunks = self.rl_chunker.create_chunks(
                transcription_segments, speaker_segments, 
                scene_segments, topic_segments, video_duration
            )
        else:
            logger.info("Using rule-based chunking")
            chunks = self.rule_chunker.create_chunks(
                transcription_segments, speaker_segments, 
                scene_segments, topic_segments, video_duration
            )
        
        # Add embeddings to chunks
        if features.get('text_embeddings') is not None:
            self._add_embeddings_to_chunks(chunks, features['text_embeddings'], transcription_segments)
        
        return chunks
    
    def _add_embeddings_to_chunks(
        self, 
        chunks: List[VideoChunk], 
        embeddings: np.ndarray, 
        transcription_segments: List
    ):
        """Add text embeddings to chunks."""
        for chunk in chunks:
            # Find segments within this chunk
            chunk_segments = [
                seg for seg in transcription_segments
                if seg.start_time >= chunk.start_time and seg.end_time <= chunk.end_time
            ]
            
            if chunk_segments:
                # Get indices of these segments
                segment_indices = [
                    i for i, seg in enumerate(transcription_segments)
                    if seg in chunk_segments
                ]
                
                # Average embeddings for this chunk
                chunk_embeddings = embeddings[segment_indices].mean(axis=0)
                chunk.embeddings = chunk_embeddings
    
    def _process_chunks(self, query: Optional[str] = None) -> List[ProcessingResult]:
        """Process chunks through Gemini API with caching."""
        results = []
        
        # Process in batches for efficiency
        batch_size = self.gemini_config.batch_size
        
        for i in range(0, len(self.chunks), batch_size):
            batch_chunks = self.chunks[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: chunks {i+1}-{min(i+batch_size, len(self.chunks))}")
            
            batch_results = self._process_batch_with_cache(batch_chunks, query)
            results.extend(batch_results)
        
        return results
    
    def _process_batch_with_cache(
        self, 
        chunks: List[VideoChunk], 
        query: Optional[str] = None
    ) -> List[ProcessingResult]:
        """Process a batch of chunks with caching."""
        results = []
        
        for chunk in chunks:
            # Generate cache key
            cache_key = self._generate_cache_key(chunk, query)
            
            # Check cache first
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for chunk {chunk.chunk_id}")
                results.append(cached_result)
                continue
            
            # Process through Gemini API
            logger.debug(f"Processing chunk {chunk.chunk_id} through API")
            result = self.gemini_api.process_chunk(chunk, query)
            
            # Cache the result
            self.cache.put(cache_key, result, level=1)
            
            results.append(result)
        
        return results
    
    def _generate_cache_key(self, chunk: VideoChunk, query: Optional[str] = None) -> str:
        """Generate cache key for chunk and query."""
        content = f"{chunk.transcription}:{query or ''}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_metrics(self, start_time: float) -> PipelineMetrics:
        """Calculate pipeline metrics."""
        total_duration = time.time() - start_time
        
        # Calculate token and cost totals
        total_tokens = sum(result.tokens_used for result in self.results)
        total_cost = sum(result.cost for result in self.results)
        
        # Get cache statistics
        cache_stats = self.cache.get_stats()
        
        # Calculate chunking metrics
        coherence_scores = [chunk.coherence_score for chunk in self.chunks]
        avg_chunk_duration = np.mean([chunk.duration for chunk in self.chunks]) if self.chunks else 0.0
        
        # Calculate API metrics
        api_calls = len([r for r in self.results if r.model_used != "error"])
        avg_response_time = np.mean([r.processing_time for r in self.results]) if self.results else 0.0
        
        metrics = PipelineMetrics(
            total_duration=total_duration,
            total_tokens=total_tokens,
            total_cost=total_cost,
            cache_hits=cache_stats['l1_hits'] + cache_stats['l2_hits'] + cache_stats['l3_hits'],
            cache_misses=cache_stats['misses'],
            cache_hit_rate=cache_stats['hit_rate'],
            num_chunks=len(self.chunks),
            avg_chunk_duration=avg_chunk_duration,
            coherence_scores=coherence_scores,
            api_calls=api_calls,
            avg_response_time=avg_response_time
        )
        
        return metrics
    
    def _print_summary(self):
        """Print pipeline summary."""
        logger.info("=" * 60)
        logger.info("HALO PIPELINE SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"Video Processing:")
        logger.info(f"  Total Duration: {self.metrics.total_duration:.2f}s")
        logger.info(f"  Chunks Created: {self.metrics.num_chunks}")
        logger.info(f"  Avg Chunk Duration: {self.metrics.avg_chunk_duration:.1f}s")
        logger.info(f"  Avg Coherence Score: {np.mean(self.metrics.coherence_scores):.3f}")
        
        logger.info(f"\nAPI Usage:")
        logger.info(f"  Total Tokens: {self.metrics.total_tokens:,}")
        logger.info(f"  Total Cost: ${self.metrics.total_cost:.4f}")
        logger.info(f"  API Calls: {self.metrics.api_calls}")
        logger.info(f"  Avg Response Time: {self.metrics.avg_response_time:.2f}s")
        
        logger.info(f"\nCache Performance:")
        logger.info(f"  Cache Hits: {self.metrics.cache_hits}")
        logger.info(f"  Cache Misses: {self.metrics.cache_misses}")
        logger.info(f"  Hit Rate: {self.metrics.cache_hit_rate:.2%}")
        
        logger.info("=" * 60)
    
    def ask_question(self, question: str) -> ProcessingResult:
        """
        Ask a question about the processed video.
        
        Args:
            question: Question to ask
            
        Returns:
            Processing result
        """
        if not self.chunks:
            raise ValueError("No chunks available. Run process_video() first.")
        
        logger.info(f"Asking question: {question}")
        
        # Find relevant chunks (simple keyword matching for MVP)
        relevant_chunks = self._find_relevant_chunks(question)
        
        if not relevant_chunks:
            # Use all chunks if no specific relevance found
            relevant_chunks = self.chunks
        
        # Ask follow-up question
        result = self.gemini_api.ask_followup_question(relevant_chunks, question)
        
        logger.info(f"Question answered in {result.processing_time:.2f}s")
        return result
    
    def _find_relevant_chunks(self, question: str) -> List[VideoChunk]:
        """Find chunks relevant to the question."""
        if not self.chunks:
            return []
        
        # Simple keyword-based relevance for MVP
        question_lower = question.lower()
        relevant_chunks = []
        
        for chunk in self.chunks:
            # Check if question keywords appear in chunk transcription
            chunk_lower = chunk.transcription.lower()
            
            # Simple relevance score based on keyword overlap
            question_words = set(question_lower.split())
            chunk_words = set(chunk_lower.split())
            
            overlap = len(question_words.intersection(chunk_words))
            relevance_score = overlap / len(question_words) if question_words else 0
            
            if relevance_score > 0.1:  # Threshold for relevance
                relevant_chunks.append(chunk)
        
        return relevant_chunks
    
    def get_chunk_summary(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed summary of a specific chunk."""
        chunk = next((c for c in self.chunks if c.chunk_id == chunk_id), None)
        if not chunk:
            return None
        
        result = next((r for r in self.results if r.chunk_id == chunk_id), None)
        
        summary = {
            'chunk_id': chunk.chunk_id,
            'start_time': chunk.start_time,
            'end_time': chunk.end_time,
            'duration': chunk.duration,
            'transcription': chunk.transcription,
            'coherence_score': chunk.coherence_score,
            'fragmentation_penalty': chunk.fragmentation_penalty,
            'num_speakers': len(chunk.speakers),
            'num_scenes': len(chunk.scenes),
            'topics': [t.topic_name for t in chunk.topics],
            'chunking_method': chunk.chunking_method
        }
        
        if result:
            summary.update({
                'response': result.response_text,
                'tokens_used': result.tokens_used,
                'cost': result.cost,
                'processing_time': result.processing_time,
                'relevance_score': result.relevance_score,
                'coherence_score': result.coherence_score
            })
        
        return summary
    
    def export_results(self, output_path: str):
        """Export results to file."""
        import json
        from datetime import datetime
        
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics.dict(),
            'chunks': [chunk.dict() for chunk in self.chunks],
            'results': [result.dict() for result in self.results],
            'cache_stats': self.cache.get_stats()
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Results exported to {output_path}")
    
    def clear_cache(self):
        """Clear all cache levels."""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats() 