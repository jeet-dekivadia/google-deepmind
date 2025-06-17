"""
Video chunking strategies for HALO framework.

This module provides both rule-based and reinforcement learning-based
chunking strategies to create semantically coherent video segments.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sklearn.cluster import KMeans
from bert_score import score as bert_score
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

from .models import (
    VideoChunk, TranscriptionSegment, SpeakerSegment, 
    SceneSegment, TopicSegment, ChunkingConfig
)
from .extractors import TextExtractor

logger = logging.getLogger(__name__)


class RuleBasedChunker:
    """Rule-based chunking strategy using multimodal signals."""
    
    def __init__(self, config: ChunkingConfig):
        """
        Initialize the rule-based chunker.
        
        Args:
            config: Chunking configuration
        """
        self.config = config
        self.text_extractor = TextExtractor()
    
    def create_chunks(
        self,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List[SpeakerSegment],
        scene_segments: List[SceneSegment],
        topic_segments: List[TopicSegment],
        video_duration: float
    ) -> List[VideoChunk]:
        """
        Create chunks using rule-based strategy.
        
        Args:
            transcription_segments: List of transcription segments
            speaker_segments: List of speaker segments
            scene_segments: List of scene segments
            topic_segments: List of topic segments
            video_duration: Total video duration
            
        Returns:
            List of video chunks
        """
        logger.info("Starting rule-based chunking")
        
        # Get potential break points
        break_points = self._identify_break_points(
            transcription_segments, speaker_segments, 
            scene_segments, topic_segments
        )
        
        # Create chunks based on break points
        chunks = []
        current_start = 0.0
        chunk_id = 0
        
        for break_point in break_points:
            if break_point - current_start >= self.config.min_chunk_duration:
                chunk = self._create_chunk(
                    chunk_id, current_start, break_point,
                    transcription_segments, speaker_segments,
                    scene_segments, topic_segments
                )
                chunks.append(chunk)
                chunk_id += 1
                current_start = break_point
        
        # Handle final chunk
        if video_duration - current_start >= self.config.min_chunk_duration:
            chunk = self._create_chunk(
                chunk_id, current_start, video_duration,
                transcription_segments, speaker_segments,
                scene_segments, topic_segments
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks using rule-based strategy")
        return chunks
    
    def _identify_break_points(
        self,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List[SpeakerSegment],
        scene_segments: List[SceneSegment],
        topic_segments: List[TopicSegment]
    ) -> List[float]:
        """Identify potential break points based on multimodal signals."""
        break_points = set()
        
        # Add speaker change points
        for segment in speaker_segments:
            if segment.confidence >= self.config.speaker_change_threshold:
                break_points.add(segment.start_time)
                break_points.add(segment.end_time)
        
        # Add scene change points
        for segment in scene_segments:
            if segment.confidence >= self.config.scene_change_threshold:
                break_points.add(segment.start_time)
        
        # Add topic change points
        for segment in topic_segments:
            break_points.add(segment.start_time)
            break_points.add(segment.end_time)
        
        # Add natural sentence boundaries
        for segment in transcription_segments:
            if segment.text.strip().endswith(('.', '!', '?')):
                break_points.add(segment.end_time)
        
        # Filter and sort break points
        sorted_points = sorted(list(break_points))
        
        # Ensure minimum spacing between break points
        filtered_points = []
        last_point = 0.0
        
        for point in sorted_points:
            if point - last_point >= self.config.min_chunk_duration:
                filtered_points.append(point)
                last_point = point
        
        return filtered_points
    
    def _create_chunk(
        self,
        chunk_id: int,
        start_time: float,
        end_time: float,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List[SpeakerSegment],
        scene_segments: List[SceneSegment],
        topic_segments: List[TopicSegment]
    ) -> VideoChunk:
        """Create a single video chunk."""
        # Filter segments within time range
        chunk_transcription = [
            seg for seg in transcription_segments
            if seg.start_time >= start_time and seg.end_time <= end_time
        ]
        
        chunk_speakers = [
            seg for seg in speaker_segments
            if seg.start_time >= start_time and seg.end_time <= end_time
        ]
        
        chunk_scenes = [
            seg for seg in scene_segments
            if seg.start_time >= start_time and seg.end_time <= end_time
        ]
        
        chunk_topics = [
            seg for seg in topic_segments
            if seg.start_time >= start_time and seg.end_time <= end_time
        ]
        
        # Combine transcription text
        transcription_text = " ".join([seg.text for seg in chunk_transcription])
        
        # Calculate coherence score
        coherence_score = self._calculate_coherence_score(chunk_transcription)
        
        # Calculate fragmentation penalty
        fragmentation_penalty = self._calculate_fragmentation_penalty(
            start_time, end_time, chunk_transcription
        )
        
        chunk = VideoChunk(
            chunk_id=f"chunk_{chunk_id:04d}",
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            transcription=transcription_text,
            transcription_segments=chunk_transcription,
            speakers=chunk_speakers,
            scenes=chunk_scenes,
            topics=chunk_topics,
            chunking_method="rule_based",
            coherence_score=coherence_score,
            fragmentation_penalty=fragmentation_penalty
        )
        
        return chunk
    
    def _calculate_coherence_score(self, segments: List[TranscriptionSegment]) -> float:
        """Calculate semantic coherence score for a chunk."""
        if len(segments) < 2:
            return 1.0
        
        texts = [seg.text for seg in segments]
        
        try:
            # Calculate BERTScore for semantic coherence
            P, R, F1 = bert_score(texts, texts, lang='en', verbose=False)
            coherence_score = float(F1.mean().item())
        except Exception as e:
            logger.warning(f"Error calculating BERTScore: {e}")
            coherence_score = 0.8  # Default score
        
        return coherence_score
    
    def _calculate_fragmentation_penalty(
        self, 
        start_time: float, 
        end_time: float, 
        segments: List[TranscriptionSegment]
    ) -> float:
        """Calculate fragmentation penalty based on segment distribution."""
        if not segments:
            return 0.0
        
        # Calculate gaps between segments
        gaps = []
        for i in range(len(segments) - 1):
            gap = segments[i + 1].start_time - segments[i].end_time
            if gap > 0:
                gaps.append(gap)
        
        if not gaps:
            return 0.0
        
        # Penalty based on average gap size
        avg_gap = np.mean(gaps)
        chunk_duration = end_time - start_time
        penalty = min(avg_gap / chunk_duration, 1.0)
        
        return penalty


class ChunkingEnvironment:
    """Environment for reinforcement learning chunking."""
    
    def __init__(self, transcription_segments: List[TranscriptionSegment], config: ChunkingConfig):
        """
        Initialize the chunking environment.
        
        Args:
            transcription_segments: List of transcription segments
            config: Chunking configuration
        """
        self.segments = transcription_segments
        self.config = config
        self.text_extractor = TextExtractor()
        
        # Environment state
        self.current_position = 0.0
        self.chunks_created = []
        self.total_duration = max(seg.end_time for seg in transcription_segments)
        
    def reset(self):
        """Reset the environment."""
        self.current_position = 0.0
        self.chunks_created = []
        return self._get_state()
    
    def step(self, action: int):
        """
        Take a step in the environment.
        
        Args:
            action: 0 for continue, 1 for create chunk
            
        Returns:
            Tuple of (next_state, reward, done, info)
        """
        reward = 0.0
        done = False
        
        if action == 1:  # Create chunk
            chunk_duration = self.current_position - (self.chunks_created[-1].end_time if self.chunks_created else 0.0)
            
            if chunk_duration >= self.config.min_chunk_duration:
                # Create chunk
                chunk = self._create_chunk_at_position()
                self.chunks_created.append(chunk)
                
                # Calculate reward
                coherence_reward = chunk.coherence_score
                fragmentation_penalty = chunk.fragmentation_penalty * self.config.fragmentation_penalty_weight
                duration_penalty = max(0, (chunk_duration - self.config.max_chunk_duration) / self.config.max_chunk_duration)
                
                reward = coherence_reward - fragmentation_penalty - duration_penalty
            else:
                reward = -1.0  # Penalty for too short chunks
        
        # Move forward in time
        self.current_position += 30.0  # 30-second steps
        
        if self.current_position >= self.total_duration:
            done = True
            # Final reward based on overall quality
            if self.chunks_created:
                avg_coherence = np.mean([chunk.coherence_score for chunk in self.chunks_created])
                reward += avg_coherence
        
        return self._get_state(), reward, done, {}
    
    def _get_state(self) -> np.ndarray:
        """Get current state representation."""
        # Simple state: current position, number of chunks, average chunk duration
        num_chunks = len(self.chunks_created)
        avg_duration = np.mean([chunk.duration for chunk in self.chunks_created]) if self.chunks_created else 0.0
        
        state = np.array([
            self.current_position / self.total_duration,  # Normalized position
            num_chunks / 10.0,  # Normalized chunk count
            avg_duration / self.config.max_chunk_duration,  # Normalized duration
        ])
        
        return state
    
    def _create_chunk_at_position(self) -> VideoChunk:
        """Create a chunk ending at current position."""
        # Find segments within the chunk
        chunk_start = self.chunks_created[-1].end_time if self.chunks_created else 0.0
        chunk_end = self.current_position
        
        chunk_segments = [
            seg for seg in self.segments
            if seg.start_time >= chunk_start and seg.end_time <= chunk_end
        ]
        
        transcription_text = " ".join([seg.text for seg in chunk_segments])
        coherence_score = self._calculate_coherence_score(chunk_segments)
        fragmentation_penalty = self._calculate_fragmentation_penalty(chunk_start, chunk_end, chunk_segments)
        
        chunk = VideoChunk(
            chunk_id=f"rl_chunk_{len(self.chunks_created):04d}",
            start_time=chunk_start,
            end_time=chunk_end,
            duration=chunk_end - chunk_start,
            transcription=transcription_text,
            transcription_segments=chunk_segments,
            chunking_method="rl_based",
            coherence_score=coherence_score,
            fragmentation_penalty=fragmentation_penalty
        )
        
        return chunk
    
    def _calculate_coherence_score(self, segments: List[TranscriptionSegment]) -> float:
        """Calculate semantic coherence score."""
        if len(segments) < 2:
            return 1.0
        
        texts = [seg.text for seg in segments]
        
        try:
            P, R, F1 = bert_score(texts, texts, lang='en', verbose=False)
            coherence_score = float(F1.mean().item())
        except Exception:
            coherence_score = 0.8
        
        return coherence_score
    
    def _calculate_fragmentation_penalty(
        self, 
        start_time: float, 
        end_time: float, 
        segments: List[TranscriptionSegment]
    ) -> float:
        """Calculate fragmentation penalty."""
        if not segments:
            return 0.0
        
        gaps = []
        for i in range(len(segments) - 1):
            gap = segments[i + 1].start_time - segments[i].end_time
            if gap > 0:
                gaps.append(gap)
        
        if not gaps:
            return 0.0
        
        avg_gap = np.mean(gaps)
        chunk_duration = end_time - start_time
        penalty = min(avg_gap / chunk_duration, 1.0)
        
        return penalty


class ChunkingPolicy(nn.Module):
    """Policy network for RL chunking."""
    
    def __init__(self, state_dim: int = 3, action_dim: int = 2):
        """
        Initialize the policy network.
        
        Args:
            state_dim: Dimension of state space
            action_dim: Dimension of action space
        """
        super(ChunkingPolicy, self).__init__()
        
        self.fc1 = nn.Linear(state_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, action_dim)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=-1)
    
    def forward(self, state):
        """Forward pass through the policy network."""
        x = self.relu(self.fc1(state))
        x = self.relu(self.fc2(x))
        action_probs = self.softmax(self.fc3(x))
        return action_probs


class RLChunker:
    """Reinforcement learning-based chunking strategy."""
    
    def __init__(self, config: ChunkingConfig):
        """
        Initialize the RL chunker.
        
        Args:
            config: Chunking configuration
        """
        self.config = config
        self.policy = ChunkingPolicy()
        self.optimizer = optim.Adam(self.policy.parameters(), lr=0.001)
        
    def train(
        self, 
        transcription_segments: List[TranscriptionSegment],
        episodes: int = 1000
    ):
        """
        Train the RL chunker.
        
        Args:
            transcription_segments: List of transcription segments
            episodes: Number of training episodes
        """
        logger.info(f"Training RL chunker for {episodes} episodes")
        
        environment = ChunkingEnvironment(transcription_segments, self.config)
        
        for episode in range(episodes):
            state = environment.reset()
            episode_rewards = []
            
            while True:
                # Convert state to tensor
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
                
                # Get action probabilities
                action_probs = self.policy(state_tensor)
                action_dist = Categorical(action_probs)
                action = action_dist.sample()
                
                # Take action
                next_state, reward, done, _ = environment.step(action.item())
                episode_rewards.append(reward)
                
                # Update policy
                loss = -action_dist.log_prob(action) * reward
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                state = next_state
                
                if done:
                    break
            
            if (episode + 1) % 100 == 0:
                avg_reward = np.mean(episode_rewards)
                logger.info(f"Episode {episode + 1}, Average Reward: {avg_reward:.4f}")
        
        logger.info("RL chunker training completed")
    
    def create_chunks(
        self,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List[SpeakerSegment],
        scene_segments: List[SceneSegment],
        topic_segments: List[TopicSegment],
        video_duration: float
    ) -> List[VideoChunk]:
        """
        Create chunks using trained RL policy.
        
        Args:
            transcription_segments: List of transcription segments
            speaker_segments: List of speaker segments
            scene_segments: List of scene segments
            topic_segments: List of topic segments
            video_duration: Total video duration
            
        Returns:
            List of video chunks
        """
        logger.info("Starting RL-based chunking")
        
        environment = ChunkingEnvironment(transcription_segments, self.config)
        state = environment.reset()
        
        while True:
            # Get action from policy
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            action_probs = self.policy(state_tensor)
            action = torch.argmax(action_probs).item()
            
            # Take action
            next_state, _, done, _ = environment.step(action)
            state = next_state
            
            if done:
                break
        
        # Get created chunks
        chunks = environment.chunks_created
        
        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.chunk_id = f"rl_chunk_{i:04d}"
            
            # Add speaker, scene, and topic segments
            chunk.speakers = [
                seg for seg in speaker_segments
                if seg.start_time >= chunk.start_time and seg.end_time <= chunk.end_time
            ]
            chunk.scenes = [
                seg for seg in scene_segments
                if seg.start_time >= chunk.start_time and seg.end_time <= chunk.end_time
            ]
            chunk.topics = [
                seg for seg in topic_segments
                if seg.start_time >= chunk.start_time and seg.end_time <= chunk.end_time
            ]
        
        logger.info(f"Created {len(chunks)} chunks using RL strategy")
        return chunks
    
    def save_model(self, path: str):
        """Save the trained model."""
        torch.save(self.policy.state_dict(), path)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load a trained model."""
        self.policy.load_state_dict(torch.load(path))
        logger.info(f"Model loaded from {path}") 