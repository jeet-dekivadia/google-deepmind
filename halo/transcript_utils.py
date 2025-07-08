"""
Utilities for handling long transcripts for Gemini API context.
Includes chunking and context windowing to fit API limits.
"""
from typing import List, Tuple
import re

MAX_CONTEXT_TOKENS = 30720  # Gemini 1.5 Pro (as per docs)


def chunk_transcript(transcript: str, max_tokens: int = MAX_CONTEXT_TOKENS, overlap: int = 2000) -> List[str]:
    """
    Splits a transcript into overlapping chunks that fit within the max token limit.
    Assumes 1 token ≈ 4 characters (rough estimate, adjust as needed).
    """
    approx_token_len = max_tokens * 4
    approx_overlap = overlap * 4
    chunks = []
    i = 0
    while i < len(transcript):
        chunk = transcript[i:i+approx_token_len]
        chunks.append(chunk)
        i += approx_token_len - approx_overlap
    return chunks


def get_context_window(transcript: str, start_time: str = None, end_time: str = None) -> str:
    """
    Extracts a segment of the transcript between start_time and end_time.
    Assumes transcript is formatted with timestamps (e.g., [00:10:00] ...).
    Returns the relevant segment as context.
    """
    if not start_time and not end_time:
        return transcript
    lines = transcript.splitlines()
    context_lines = []
    in_window = False if start_time else True
    for line in lines:
        if start_time and start_time in line:
            in_window = True
        if in_window:
            context_lines.append(line)
        if end_time and end_time in line:
            break
    return '\n'.join(context_lines)


def find_relevant_chunk(question: str, chunks: List[str]) -> str:
    """
    Finds the most relevant chunk for a question using simple keyword matching.
    (For production, replace with semantic search/embeddings.)
    """
    keywords = re.findall(r'\w+', question.lower())
    best_chunk = ''
    best_score = 0
    for chunk in chunks:
        score = sum(chunk.lower().count(k) for k in keywords)
        if score > best_score:
            best_score = score
            best_chunk = chunk
    return best_chunk if best_chunk else chunks[0]  # fallback to first chunk 