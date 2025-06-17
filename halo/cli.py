"""
Command-line interface for HALO framework.

This module provides a CLI for running the HALO pipeline on videos
and interacting with the results.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .pipeline import HALOPipeline
from .models import ChunkingConfig, CacheConfig, GeminiConfig

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="HALO - Hierarchical Abstraction for Longform Optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a video with default settings
  halo process video.mp4

  # Process with specific query
  halo process video.mp4 --query "What are the main topics discussed?"

  # Use RL-based chunking
  halo process video.mp4 --use-rl-chunker

  # Ask a question about processed video
  halo ask video.mp4 "What was the conclusion?"

  # Export results to JSON
  halo process video.mp4 --export results.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process a video through HALO pipeline')
    process_parser.add_argument('video_path', help='Path to input video file')
    process_parser.add_argument('--query', help='Optional query to ask about the video')
    process_parser.add_argument('--use-rl-chunker', action='store_true', help='Use RL-based chunking')
    process_parser.add_argument('--export', help='Export results to JSON file')
    process_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Ask command
    ask_parser = subparsers.add_parser('ask', help='Ask a question about a processed video')
    ask_parser.add_argument('video_path', help='Path to input video file')
    ask_parser.add_argument('question', help='Question to ask about the video')
    ask_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Cache command
    cache_parser = subparsers.add_parser('cache', help='Manage cache')
    cache_parser.add_argument('action', choices=['clear', 'stats'], help='Cache action')
    cache_parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    return parser


def process_video(args) -> int:
    """Process a video through the HALO pipeline."""
    video_path = Path(args.video_path)
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return 1
    
    try:
        # Initialize pipeline
        pipeline = HALOPipeline()
        
        # Process video
        logger.info(f"Processing video: {video_path}")
        chunks, results, metrics = pipeline.process_video(
            str(video_path),
            query=args.query,
            use_rl_chunker=args.use_rl_chunker
        )
        
        # Export results if requested
        if args.export:
            pipeline.export_results(args.export)
            logger.info(f"Results exported to: {args.export}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return 1


def ask_question(args) -> int:
    """Ask a question about a video."""
    video_path = Path(args.video_path)
    
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return 1
    
    try:
        # Initialize pipeline
        pipeline = HALOPipeline()
        
        # Process video first (if not already processed)
        logger.info(f"Processing video: {video_path}")
        chunks, results, metrics = pipeline.process_video(str(video_path))
        
        # Ask question
        logger.info(f"Asking question: {args.question}")
        answer = pipeline.ask_question(args.question)
        
        # Print answer
        print("\n" + "="*60)
        print("QUESTION ANSWER")
        print("="*60)
        print(f"Question: {args.question}")
        print(f"Answer: {answer.response_text}")
        print(f"Processing time: {answer.processing_time:.2f}s")
        print(f"Tokens used: {answer.tokens_used:,}")
        print(f"Cost: ${answer.cost:.4f}")
        print("="*60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error asking question: {e}")
        return 1


def manage_cache(args) -> int:
    """Manage cache operations."""
    try:
        pipeline = HALOPipeline()
        
        if args.action == 'clear':
            pipeline.clear_cache()
            logger.info("Cache cleared successfully")
        elif args.action == 'stats':
            stats = pipeline.get_cache_stats()
            print("\n" + "="*40)
            print("CACHE STATISTICS")
            print("="*40)
            print(f"Total Requests: {stats['total_requests']}")
            print(f"L1 Hits: {stats['l1_hits']}")
            print(f"L2 Hits: {stats['l2_hits']}")
            print(f"L3 Hits: {stats['l3_hits']}")
            print(f"Misses: {stats['misses']}")
            print(f"Hit Rate: {stats['hit_rate']:.2%}")
            print(f"L1 Size: {stats['l1_size']}")
            print(f"L2 Size: {stats['l2_size']}")
            print(f"L3 Size: {stats['l3_size']}")
            print(f"Total Size: {stats['total_size']}")
            print("="*40)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error managing cache: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Execute command
    if args.command == 'process':
        return process_video(args)
    elif args.command == 'ask':
        return ask_question(args)
    elif args.command == 'cache':
        return manage_cache(args)
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 