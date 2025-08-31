"""
Multimodal feature extractors for HALO framework.

This module provides extractors for audio, video, and text features
from long-form videos to enable semantic chunking and analysis.
"""

import os
import logging
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import numpy as np
import librosa
import cv2
from scenedetect import detect, ContentDetector, AdaptiveDetector
import whisper
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook

from .models import (
    VideoMetadata, SpeakerSegment, SceneSegment, 
    TranscriptionSegment, TopicSegment
)

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extracts audio features and performs speaker diarization."""
    
    def __init__(self, whisper_model: str = "base", device: str = "cpu"):
        """
        Initialize the audio extractor.
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            device: Device to run models on (cpu, cuda)
        """
        self.whisper_model = whisper.load_model(whisper_model)
        self.device = device
        self.speaker_pipeline = None
        
    def setup_speaker_diarization(self, auth_token: str):
        """Setup speaker diarization pipeline."""
        try:
            self.speaker_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=auth_token
            )
            logger.info("Speaker diarization pipeline initialized")
        except Exception as e:
            logger.warning(f"Could not initialize speaker diarization: {e}")
            self.speaker_pipeline = None
    
    def extract_audio_features(self, video_path: str) -> Tuple[np.ndarray, int]:
        """
        Extract audio features from video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (audio_features, sample_rate)
        """
        try:
            # Load audio using librosa
            audio, sr = librosa.load(video_path, sr=None)
            
            # Extract MFCC features
            mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            
            # Extract spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
            
            # Combine features
            features = np.vstack([
                mfcc,
                spectral_centroids.reshape(1, -1),
                spectral_rolloff.reshape(1, -1)
            ])
            
            logger.info(f"Extracted audio features: {features.shape}")
            return features, sr
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {e}")
            raise
    
    def transcribe_audio(self, video_path: str) -> List[TranscriptionSegment]:
        """
        Transcribe audio using Whisper.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of transcription segments
        """
        try:
            # Transcribe with timestamps
            result = self.whisper_model.transcribe(
                video_path, 
                word_timestamps=True,
                verbose=False
            )
            
            segments = []
            for segment in result["segments"]:
                transcription_segment = TranscriptionSegment(
                    start_time=segment["start"],
                    end_time=segment["end"],
                    text=segment["text"].strip(),
                    confidence=segment.get("avg_logprob", 0.0)
                )
                segments.append(transcription_segment)
            
            logger.info(f"Transcribed {len(segments)} segments")
            return segments
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    def perform_speaker_diarization(self, video_path: str) -> List[SpeakerSegment]:
        """
        Perform speaker diarization using pyannote.audio.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of speaker segments
        """
        if self.speaker_pipeline is None:
            logger.warning("Speaker diarization pipeline not initialized")
            return []
        
        try:
            with ProgressHook() as hook:
                diarization = self.speaker_pipeline(video_path, hook=hook)
            
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segment = SpeakerSegment(
                    start_time=turn.start,
                    end_time=turn.end,
                    speaker_id=speaker,
                    confidence=1.0  # pyannote doesn't provide confidence scores
                )
                segments.append(speaker_segment)
            
            logger.info(f"Detected {len(segments)} speaker segments")
            return segments
            
        except Exception as e:
            logger.error(f"Error performing speaker diarization: {e}")
            return []


class VideoExtractor:
    """Extracts video features and detects scene changes."""
    
    def __init__(self, scene_threshold: float = 30.0):
        """
        Initialize the video extractor.
        
        Args:
            scene_threshold: Threshold for scene change detection
        """
        self.scene_threshold = scene_threshold
    
    def extract_video_metadata(self, video_path: str) -> VideoMetadata:
        """
        Extract basic video metadata.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Video metadata
        """
        try:
            cap = cv2.VideoCapture(video_path)
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            # Get file size
            file_size = os.path.getsize(video_path)
            
            cap.release()
            
            metadata = VideoMetadata(
                duration=duration,
                fps=fps,
                resolution=(width, height),
                audio_sample_rate=44100,  # Default assumption
                file_size=file_size,
                format=Path(video_path).suffix[1:].upper()
            )
            
            logger.info(f"Extracted video metadata: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting video metadata: {e}")
            raise
    
    def detect_scene_changes(self, video_path: str) -> List[SceneSegment]:
        """
        Detect scene changes using PySceneDetect.
        
        Args:
            video_path: Path to video file
            
        Returns:
            List of scene segments
        """
        try:
            # Detect scenes using content-based detection
            scenes = detect(video_path, ContentDetector(threshold=self.scene_threshold))
            
            segments = []
            for i, scene in enumerate(scenes):
                scene_segment = SceneSegment(
                    start_time=scene[0].get_seconds(),
                    end_time=scene[1].get_seconds(),
                    scene_id=i,
                    confidence=0.8  # Default confidence for content detection
                )
                segments.append(scene_segment)
            
            logger.info(f"Detected {len(segments)} scene changes")
            return segments
            
        except Exception as e:
            logger.error(f"Error detecting scene changes: {e}")
            return []
    
    def extract_frame_features(self, video_path: str, sample_rate: int = 1) -> np.ndarray:
        """
        Extract frame-level features for visual analysis.
        
        Args:
            video_path: Path to video file
            sample_rate: Sample every Nth frame
            
        Returns:
            Array of frame features
        """
        try:
            cap = cv2.VideoCapture(video_path)
            features = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_rate == 0:
                    # Convert to grayscale and resize for efficiency
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    resized = cv2.resize(gray, (64, 64))
                    
                    # Extract simple features (histogram)
                    hist = cv2.calcHist([resized], [0], None, [256], [0, 256])
                    hist = hist.flatten() / hist.sum()  # Normalize
                    
                    features.append(hist)
                
                frame_count += 1
            
            cap.release()
            
            if features:
                features_array = np.array(features)
                logger.info(f"Extracted {features_array.shape[0]} frame features")
                return features_array
            else:
                return np.array([])
                
        except Exception as e:
            logger.error(f"Error extracting frame features: {e}")
            return np.array([])


class TextExtractor:
    """Extracts text features and performs topic modeling."""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the text extractor.
        
        Args:
            embedding_model: Sentence transformer model name
        """
        self.embedding_model = SentenceTransformer(embedding_model)
        self.topic_model = None
        
    def setup_topic_modeling(self, num_topics: int = 10):
        """Setup BERTopic for topic modeling."""
        try:
            self.topic_model = BERTopic(
                nr_topics=num_topics,
                verbose=True
            )
            logger.info("Topic modeling pipeline initialized")
        except Exception as e:
            logger.warning(f"Could not initialize topic modeling: {e}")
            self.topic_model = None
    
    def extract_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Extract sentence embeddings.
        
        Args:
            texts: List of text strings
            
        Returns:
            Array of embeddings
        """
        try:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
            logger.info(f"Extracted embeddings: {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error extracting embeddings: {e}")
            raise
    
    def perform_topic_modeling(self, texts: List[str]) -> List[TopicSegment]:
        """
        Perform topic modeling on text segments.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of topic segments
        """
        if self.topic_model is None:
            logger.warning("Topic modeling pipeline not initialized")
            return []
        
        try:
            # Fit topic model
            topics, probs = self.topic_model.fit_transform(texts)
            
            # Get topic info
            topic_info = self.topic_model.get_topic_info()
            
            segments = []
            for i, (text, topic_id) in enumerate(zip(texts, topics)):
                if topic_id != -1:  # Skip outlier topics
                    topic_name = topic_info[topic_info['Topic'] == topic_id]['Name'].iloc[0]
                    confidence = probs[i][topic_id] if probs is not None else 0.8
                    
                    topic_segment = TopicSegment(
                        start_time=i * 30.0,  # Approximate timing
                        end_time=(i + 1) * 30.0,
                        topic_id=int(topic_id),
                        topic_name=topic_name,
                        confidence=float(confidence)
                    )
                    segments.append(topic_segment)
            
            logger.info(f"Detected {len(segments)} topic segments")
            return segments
            
        except Exception as e:
            logger.error(f"Error performing topic modeling: {e}")
            return []
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            embeddings = self.embedding_model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0 