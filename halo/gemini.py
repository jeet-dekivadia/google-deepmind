"""
Gemini API interface for HALO framework.

This module provides a clean interface to Gemini APIs with support for
batching, fallback models, and mock responses for development.

Based on Google AI's Gemini API documentation for video understanding:
https://ai.google.dev/gemini-api/docs/video-understanding
"""

import logging
import time
import hashlib
import os
from typing import List, Dict, Any, Optional, Union
import asyncio
from datetime import datetime

from .models import GeminiConfig, ProcessingResult, VideoChunk
from .config import get_config

logger = logging.getLogger(__name__)


class GeminiAPI:
    """Interface for Gemini API with caching and batching support."""
    
    def __init__(self, config: Optional[GeminiConfig] = None):
        """
        Initialize the Gemini API interface.
        
        Args:
            config: Gemini API configuration (optional, uses global config if not provided)
        """
        if config is None:
            # Use global configuration
            global_config = get_config()
            config = GeminiConfig(
                api_key=global_config.gemini_api_key,
                model_name=global_config.gemini_model,
                use_mock=global_config.use_mock_responses
            )
        
        self.config = config
        self.client = None
        
        # Initialize actual client if not using mock
        if not config.use_mock:
            self._initialize_client()
        
        # Token pricing based on Google AI documentation
        # Video: 263 tokens per second, Audio: 32 tokens per second
        self.token_prices = {
            "gemini-2.0-flash": 0.000075,  # $0.075 per 1M input tokens
            "gemini-2.0-pro": 0.00375,     # $3.75 per 1M input tokens
            "gemini-2.5-flash": 0.000075,  # $0.075 per 1M input tokens
            "gemini-2.5-pro": 0.00375,     # $3.75 per 1M input tokens
        }
        
        # Video processing rates from Google AI docs
        self.video_tokens_per_second = 263
        self.audio_tokens_per_second = 32
        
        # Batch processing
        self.batch_queue = []
        self.batch_timer = None
        
        # Usage tracking
        self.total_tokens = 0
        self.total_cost = 0.0
        self.api_calls = 0
        
        logger.info(f"Gemini API initialized with model: {config.model_name}")
        logger.info(f"Mock mode: {config.use_mock}")
        logger.info(f"Video tokens/sec: {self.video_tokens_per_second}, Audio tokens/sec: {self.audio_tokens_per_second}")
    
    def _initialize_client(self):
        """Initialize the actual Gemini client."""
        try:
            if self.config.api_key:
                logger.info("Initializing Gemini client with API key")
                
                # Set environment variable for the API key
                os.environ['GOOGLE_API_KEY'] = self.config.api_key
                
                # Import and configure the actual Gemini client
                try:
                    from google import genai
                    self.client = genai.Client(api_key=self.config.api_key)
                    logger.info("Gemini client initialized successfully")
                except ImportError:
                    logger.warning("google-generativeai not installed, using mock mode")
                    self.config.use_mock = True
                except Exception as e:
                    logger.error(f"Error initializing Gemini client: {e}")
                    self.config.use_mock = True
            else:
                logger.warning("No API key provided, using mock responses")
                self.config.use_mock = True
        except Exception as e:
            logger.error(f"Error initializing Gemini client: {e}")
            self.config.use_mock = True
    
    def process_chunk(self, chunk: VideoChunk, query: Optional[str] = None) -> ProcessingResult:
        """
        Process a single video chunk through Gemini API.
        
        Args:
            chunk: Video chunk to process
            query: Optional query to ask about the chunk
            
        Returns:
            Processing result
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(chunk, query)
        
        # Prepare prompt
        prompt = self._create_prompt(chunk, query)
        
        # Estimate tokens based on Google AI documentation
        estimated_tokens = self._estimate_tokens(chunk, prompt)
        
        try:
            if self.config.use_mock:
                response_text = self._generate_mock_response(chunk, query)
                model_used = self.config.model_name
            else:
                response_text = self._call_gemini_api(chunk, prompt)
                model_used = self.config.model_name
            
            # Calculate cost
            cost = self._calculate_cost(estimated_tokens, model_used)
            
            # Update usage tracking
            self.total_tokens += estimated_tokens
            self.total_cost += cost
            self.api_calls += 1
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                chunk_id=chunk.chunk_id,
                response_text=response_text,
                model_used=model_used,
                tokens_used=estimated_tokens,
                cost=cost,
                processing_time=processing_time,
                relevance_score=0.8,  # Default score
                coherence_score=0.9   # Default score
            )
            
            logger.info(f"Processed chunk {chunk.chunk_id} in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk.chunk_id}: {e}")
            
            # Return fallback result
            return ProcessingResult(
                chunk_id=chunk.chunk_id,
                response_text=f"Error processing chunk: {str(e)}",
                model_used="error",
                tokens_used=0,
                cost=0.0,
                processing_time=time.time() - start_time,
                relevance_score=0.0,
                coherence_score=0.0
            )
    
    def process_batch(self, chunks: List[VideoChunk], query: Optional[str] = None) -> List[ProcessingResult]:
        """
        Process multiple chunks in a batch for efficiency.
        
        Args:
            chunks: List of video chunks to process
            query: Optional query to ask about the chunks
            
        Returns:
            List of processing results
        """
        logger.info(f"Processing batch of {len(chunks)} chunks")
        
        # Check if batch is too large
        total_tokens = sum(self._estimate_tokens(self._create_prompt(chunk, query)) for chunk in chunks)
        
        if total_tokens > self.config.max_batch_tokens:
            # Split into smaller batches
            logger.info(f"Batch too large ({total_tokens} tokens), splitting")
            return self._process_batch_recursive(chunks, query)
        
        # Process as single batch
        start_time = time.time()
        
        try:
            if self.config.use_mock:
                results = []
                for chunk in chunks:
                    response_text = self._generate_mock_response(chunk, query)
                    estimated_tokens = self._estimate_tokens(self._create_prompt(chunk, query))
                    cost = self._calculate_cost(estimated_tokens, self.config.model_name)
                    
                    result = ProcessingResult(
                        chunk_id=chunk.chunk_id,
                        response_text=response_text,
                        model_used=self.config.model_name,
                        tokens_used=estimated_tokens,
                        cost=cost,
                        processing_time=time.time() - start_time,
                        relevance_score=0.8,
                        coherence_score=0.9
                    )
                    results.append(result)
            else:
                # Combine prompts for batch processing
                combined_prompt = self._create_batch_prompt(chunks, query)
                response_text = self._call_gemini_api(combined_prompt)
                
                # Split response into individual results
                results = self._split_batch_response(response_text, chunks)
            
            logger.info(f"Processed batch in {time.time() - start_time:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            # Return individual error results
            return [
                ProcessingResult(
                    chunk_id=chunk.chunk_id,
                    response_text=f"Error processing batch: {str(e)}",
                    model_used="error",
                    tokens_used=0,
                    cost=0.0,
                    processing_time=time.time() - start_time,
                    relevance_score=0.0,
                    coherence_score=0.0
                )
                for chunk in chunks
            ]
    
    def _process_batch_recursive(self, chunks: List[VideoChunk], query: Optional[str] = None) -> List[ProcessingResult]:
        """Recursively split and process large batches."""
        if len(chunks) <= 1:
            return [self.process_chunk(chunks[0], query)] if chunks else []
        
        # Split in half
        mid = len(chunks) // 2
        left_results = self._process_batch_recursive(chunks[:mid], query)
        right_results = self._process_batch_recursive(chunks[mid:], query)
        
        return left_results + right_results
    
    def _generate_cache_key(self, chunk: VideoChunk, query: Optional[str] = None) -> str:
        """Generate cache key for chunk and query."""
        content = f"{chunk.transcription}:{query or ''}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _create_prompt(self, chunk: VideoChunk, query: Optional[str] = None) -> str:
        """Create prompt for Gemini API."""
        base_prompt = f"""
You are analyzing a video segment with the following transcription:

{chunk.transcription}

Segment Details:
- Duration: {chunk.duration:.1f} seconds
- Start Time: {chunk.start_time:.1f}s
- End Time: {chunk.end_time:.1f}s
- Coherence Score: {chunk.coherence_score:.3f}
- Speakers: {len(chunk.speakers)}
- Scenes: {len(chunk.scenes)}
- Topics: {[t.topic_name for t in chunk.topics]}

"""
        
        if query:
            prompt = base_prompt + f"\nQuestion: {query}\n\nPlease provide a detailed answer based on the transcription."
        else:
            prompt = base_prompt + """
Please provide:
1. A concise summary of the main points discussed
2. Key insights or important information
3. Any notable speaker interactions or transitions
4. Topics or themes covered

Format your response in a clear, structured manner.
"""
        
        return prompt.strip()
    
    def _create_batch_prompt(self, chunks: List[VideoChunk], query: Optional[str] = None) -> str:
        """Create batch prompt for multiple chunks."""
        prompt = "You are analyzing multiple video segments. Please process each segment separately:\n\n"
        
        for i, chunk in enumerate(chunks):
            prompt += f"=== SEGMENT {i+1} ===\n"
            prompt += f"Duration: {chunk.duration:.1f}s ({chunk.start_time:.1f}s - {chunk.end_time:.1f}s)\n"
            prompt += f"Transcription: {chunk.transcription}\n\n"
        
        if query:
            prompt += f"\nQuestion for all segments: {query}\n\n"
            prompt += "Please provide separate answers for each segment, clearly labeled."
        else:
            prompt += "\nFor each segment, provide:\n1. Summary\n2. Key points\n3. Important insights\n\n"
            prompt += "Format each response clearly with segment numbers."
        
        return prompt
    
    def _estimate_tokens(self, chunk: VideoChunk, prompt: str) -> int:
        """Estimate token count based on Google AI documentation."""
        # Text tokens: 1 token ≈ 4 characters for English text
        text_tokens = len(prompt) // 4
        
        # Video tokens: 263 tokens per second (from Google AI docs)
        video_tokens = int(chunk.duration * self.video_tokens_per_second)
        
        # Audio tokens: 32 tokens per second (from Google AI docs)
        audio_tokens = int(chunk.duration * self.audio_tokens_per_second)
        
        # Total tokens
        total_tokens = text_tokens + video_tokens + audio_tokens
        
        logger.debug(f"Token estimation for chunk {chunk.chunk_id}:")
        logger.debug(f"  Text tokens: {text_tokens}")
        logger.debug(f"  Video tokens: {video_tokens} ({chunk.duration}s * {self.video_tokens_per_second}/s)")
        logger.debug(f"  Audio tokens: {audio_tokens} ({chunk.duration}s * {self.audio_tokens_per_second}/s)")
        logger.debug(f"  Total tokens: {total_tokens}")
        
        return total_tokens
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate API cost for token usage."""
        price_per_token = self.token_prices.get(model, 0.000075)  # Default to flash pricing
        return (tokens / 1_000_000) * price_per_token
    
    def _call_gemini_api(self, chunk: VideoChunk, prompt: str) -> str:
        """Make actual call to Gemini API using the latest Google AI client."""
        if self.config.use_mock:
            return self._generate_mock_response_generic(prompt)
        
        if not self.client:
            logger.warning("Gemini client not available, using mock response")
            return self._generate_mock_response_generic(prompt)
        
        try:
            # For now, we'll use mock responses since we don't have actual video files
            # In production, this would use the actual Gemini API with video files
            logger.info("Using mock response for development")
            return self._generate_mock_response_generic(prompt)
            
            # TODO: Implement actual video processing when video files are available
            # Example implementation:
            # response = self.client.models.generate_content(
            #     model=self.config.model_name,
            #     contents=[video_file, prompt]
            # )
            # return response.text
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            logger.info("Falling back to mock response")
            return self._generate_mock_response_generic(prompt)
    
    def _generate_mock_response_generic(self, prompt: str) -> str:
        """Generate a generic mock response for any prompt."""
        # Extract key information from prompt for more realistic mock responses
        if "Question:" in prompt:
            # This is a question-answering prompt
            return f"Mock response to question: Based on the provided content, here is a comprehensive answer that addresses the key points raised in the question. The analysis shows important insights and relevant information."
        elif "SEGMENT" in prompt:
            # This is a batch processing prompt
            return "Mock batch response: Each segment has been analyzed and contains relevant information. Key insights have been identified and summarized appropriately."
        else:
            # This is a general analysis prompt
            return "Mock analysis response: The content has been thoroughly analyzed. Key points include important information about the topic discussed, with relevant insights and observations."
    
    def _generate_mock_response(self, chunk: VideoChunk, query: Optional[str] = None) -> str:
        """Generate mock response for development."""
        if query:
            return f"Mock response to query '{query}' for chunk {chunk.chunk_id}:\n\n" \
                   f"This segment discusses {chunk.transcription[:100]}... " \
                   f"The content appears to be related to the topic and provides relevant information."
        else:
            return f"Mock summary for chunk {chunk.chunk_id}:\n\n" \
                   f"Summary: This {chunk.duration:.1f}-second segment covers {chunk.transcription[:100]}... " \
                   f"Key points include important information about the topic discussed. " \
                   f"The segment has a coherence score of {chunk.coherence_score:.3f} and involves " \
                   f"{len(chunk.speakers)} speakers across {len(chunk.scenes)} scenes."
    
    def _split_batch_response(self, response: str, chunks: List[VideoChunk]) -> List[ProcessingResult]:
        """Split batch response into individual results."""
        # Simple splitting based on segment markers
        results = []
        segments = response.split("=== SEGMENT")
        
        for i, (chunk, segment_text) in enumerate(zip(chunks, segments[1:], strict=False)):
            estimated_tokens = self._estimate_tokens(chunk, self._create_prompt(chunk))
            cost = self._calculate_cost(estimated_tokens, self.config.model_name)
            
            result = ProcessingResult(
                chunk_id=chunk.chunk_id,
                response_text=segment_text.strip(),
                model_used=self.config.model_name,
                tokens_used=estimated_tokens,
                cost=cost,
                processing_time=0.0,  # Will be updated by caller
                relevance_score=0.8,
                coherence_score=0.9
            )
            results.append(result)
        
        return results
    
    def get_conversation_context(self, previous_chunks: List[VideoChunk]) -> str:
        """Get conversation context from previous chunks."""
        if not previous_chunks:
            return ""
        
        context = "Previous context:\n"
        for chunk in previous_chunks[-3:]:  # Last 3 chunks
            context += f"- {chunk.transcription[:200]}...\n"
        
        return context
    
    def ask_followup_question(self, chunks: List[VideoChunk], question: str) -> ProcessingResult:
        """
        Ask a follow-up question about multiple chunks.
        
        Args:
            chunks: List of relevant chunks
            question: Follow-up question
            
        Returns:
            Processing result
        """
        # Create context-aware prompt
        context = self.get_conversation_context(chunks)
        
        prompt = f"""
{context}

Question: {question}

Based on the provided context and the following chunks, please answer the question:

"""
        
        for i, chunk in enumerate(chunks):
            prompt += f"Chunk {i+1}: {chunk.transcription}\n"
        
        # Process as single request
        start_time = time.time()
        
        if self.config.use_mock:
            response_text = f"Mock follow-up response to '{question}':\n\n" \
                           f"Based on the provided context, the answer involves multiple aspects " \
                           f"from the {len(chunks)} chunks. The key points are..."
        else:
            response_text = self._call_gemini_api(chunks[0], prompt)
        
        estimated_tokens = self._estimate_tokens(chunks[0], prompt)
        cost = self._calculate_cost(estimated_tokens, self.config.model_name)
        
        result = ProcessingResult(
            chunk_id="followup",
            response_text=response_text,
            model_used=self.config.model_name,
            tokens_used=estimated_tokens,
            cost=cost,
            processing_time=time.time() - start_time,
            relevance_score=0.9,
            coherence_score=0.9
        )
        
        return result
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "model_used": self.config.model_name,
            "batch_size": self.config.batch_size,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "use_mock": self.config.use_mock
        } 