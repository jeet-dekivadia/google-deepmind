"""
Batch prediction engine for Gemini API with long context and context caching.
Handles batching, context windowing, caching, and interconnected questions.
"""
import asyncio
import httpx
import json
import hashlib
from typing import List, Dict, Optional, Any
from .context_cache import InMemoryCache, PersistentCache
from .transcript_utils import chunk_transcript, get_context_window

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
MAX_BATCH_SIZE = 10  # Adjust based on Gemini API rate limits
MAX_RETRIES = 3
TIMEOUT = 30

class GeminiBatchPredictor:
    """
    Handles batch prediction with Gemini API, long context, and context caching.
    """
    def __init__(
        self,
        api_key: str,
        use_persistent_cache: bool = False,
        cache_db_path: str = "context_cache.db"
    ) -> None:
        self.api_key = api_key
        self.cache = PersistentCache(cache_db_path) if use_persistent_cache else InMemoryCache()
        self.client = httpx.AsyncClient(timeout=TIMEOUT)

    async def close(self) -> None:
        await self.client.aclose()

    def _make_cache_key(self, video_id: str, question: str, context: str, start_time: Optional[str] = None, end_time: Optional[str] = None) -> str:
        """
        Create a cache key that is unique per video, question, and context window.
        """
        context_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()[:16]
        return json.dumps({
            "video_id": video_id,
            "q": question,
            "context_hash": context_hash,
            "start": start_time,
            "end": end_time
        })

    async def _call_gemini_api(self, context: str, question: str) -> Optional[str]:
        payload = {
            "contents": [
                {"parts": [
                    {"text": f"Context: {context}\nQuestion: {question}"}
                ]}
            ]
        }
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.post(GEMINI_API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                # Gemini API returns answer in data['candidates'][0]['content']['parts'][0]['text']
                candidates = data.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
                return None
            except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"[ERROR] API call failed after {MAX_RETRIES} attempts: {e}")
                    return None
                await asyncio.sleep(2 ** attempt)

    async def predict_batch(
        self,
        transcript: str,
        questions: List[Dict[str, Any]],
        use_chunking: bool = True,
        video_id: Optional[str] = None,
        context_override: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Predict answers for a batch of questions.
        Each question dict may include 'question', 'start_time', 'end_time'.
        Returns list of dicts with 'question', 'answer', and 'timestamp' (if available).
        """
        results = []
        context_chunks = chunk_transcript(transcript) if use_chunking else [transcript]
        for q in questions:
            question = q["question"]
            start_time = q.get("start_time")
            end_time = q.get("end_time")
            # Use override context if provided (for chunked/expanded context)
            context = context_override if context_override is not None else get_context_window(transcript, start_time, end_time)
            cache_key = self._make_cache_key(video_id or "unknown", question, context, start_time, end_time)
            # Try cache first
            answer = None
            if isinstance(self.cache, InMemoryCache):
                answer = self.cache.get(cache_key)
            else:
                answer = await self.cache.get(cache_key)
            if answer:
                results.append({"question": question, "answer": answer, "timestamp": start_time or ""})
                continue
            # If context too long, chunk and pick the chunk containing the timestamp
            if len(context) > MAX_BATCH_SIZE * 4000:
                context = context_chunks[0]
            # Call Gemini API
            answer = await self._call_gemini_api(context, question)
            if answer:
                if isinstance(self.cache, InMemoryCache):
                    self.cache.set(cache_key, answer)
                else:
                    await self.cache.set(cache_key, answer)
            results.append({"question": question, "answer": answer or "[No answer]", "timestamp": start_time or ""})
        return results
