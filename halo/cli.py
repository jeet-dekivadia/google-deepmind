import sys
import os
if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

"""
HALO Interactive CLI for Gemini batch prediction with YouTube video, chunking, and caching.
Beautiful, conversational, and cost-efficient.
"""
import asyncio
import json
import tempfile
import base64
from typing import List, Dict, Any
import yt_dlp
import ffmpeg
import whisper
import google.generativeai as genai
from PIL import Image
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align
from rich import box
from halo.gemini_batch_predictor import GeminiBatchPredictor
from halo.transcript_utils import chunk_transcript, find_relevant_chunk
from config import GEMINI_API_KEY

console = Console()

HALO_BANNER = r'''
[bold cyan]
........................................................................
.  _   _    _    _     ___   
. | | | |  / \  | |   / _ \  
. | |_| | / _ \ | |  | | | | 
. |  _  |/ ___ \| |__| |_| | 
. |_| |_/_/   \_\____|\___/  
........................................................................
[/bold cyan]
'''

# Helper: Estimate tokens (roughly 1 token ≈ 4 chars)
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

# Helper: Download YouTube video and extract audio
def extract_video_id(youtube_url: str) -> str:
    """Extracts the video ID from a YouTube URL."""
    import re
    match = re.search(r"(?:v=|youtu.be/)([\w-]+)", youtube_url)
    return match.group(1) if match else "unknown"

async def download_youtube_audio(youtube_url: str, output_dir: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        audio_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + '.wav'
    return audio_path

# Helper: Extract frames every 15 seconds directly from stream (no video file saved)
def extract_frames_from_url(youtube_url: str, output_dir: str) -> List[str]:
    frame_pattern = os.path.join(output_dir, "frame_%04d.jpg")
    try:
        # Extract frames directly from YouTube stream without saving video
        (
            ffmpeg
            .input(youtube_url)
            .output(frame_pattern, vf='fps=1/15', format='image2', vcodec='mjpeg')
            .run(quiet=True, overwrite_output=True)
        )
        # Collect all frame file paths
        frames = sorted([
            os.path.join(output_dir, fname)
            for fname in os.listdir(output_dir)
            if fname.startswith("frame_") and fname.endswith(".jpg")
        ])
        return frames
    except Exception as e:
        console.print(f"[yellow][WARNING] Frame extraction failed: {e}[/yellow]")
        return []

# Helper: Describe an image frame using Gemini Vision API
async def describe_image(image_path: str, frame_number: int, timestamp: float, model=None) -> str:
    try:
        # Use provided model or create new one
        if model is None:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Load and prepare the image
        img = Image.open(image_path)
        
        # Create a detailed prompt for image description
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        
        prompt = f"""Describe this video frame in ONE concise sentence. Focus only on key visual elements:
        - What people are wearing (colors, clothing types)
        - Main objects and their colors
        - Setting/location if obvious
        - Any text visible on screen
        
        Keep it brief and factual - this supplements audio transcript for visual questions only."""
        
        # Generate description using Gemini Vision
        response = model.generate_content([prompt, img])
        description = response.text.strip()
        
        return f"[Frame at {minutes:02d}:{seconds:02d}] {description}"
        
    except Exception as e:
        # Fallback description if API fails
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        console.print(f"[yellow][WARNING] Image description failed for frame {frame_number}: {e}[/yellow]")
        return f"[Frame at {minutes:02d}:{seconds:02d}] Video frame captured at this timestamp (description unavailable)."

# Helper: Transcribe audio using Whisper
async def transcribe_audio(audio_path: str) -> str:
    model = whisper.load_model("base")
    result = model.transcribe(audio_path)
    return result["text"]

# Interactive CLI
async def interactive_cli():
    console.clear()
    console.print(HALO_BANNER)
    console.print(Align.center("[bold magenta]Welcome to the HALO Interactive Video QA System![/bold magenta]", vertical="middle"))
    console.print(Align.center("[green]Ask deep questions about any YouTube video, cost-efficiently.[/green]", vertical="middle"))
    console.print("\n[bold blue]Tip:[/bold blue] Paste a YouTube link and press Enter. Type 'exit' anytime to quit.")
    console.rule("[bold cyan]START[/bold cyan]")
    youtube_url = Prompt.ask("[bold yellow]Enter YouTube video link[/bold yellow]").strip()
    if not youtube_url:
        console.print("[bold red][ERROR] No URL provided.[/bold red]")
        return
    video_id = extract_video_id(youtube_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"Downloading audio for video ID: {video_id}...", total=None)
            audio_path = await download_youtube_audio(youtube_url, tmpdir)
        console.print(f"[green][INFO] Audio saved to {audio_path}[/green]")
        
        # NEW: Extract frames directly from YouTube stream (no video file saved)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Extracting frames every 15 seconds...", total=None)
            frames = extract_frames_from_url(youtube_url, tmpdir)
        console.print(f"[green][INFO] Extracted {len(frames)} frames.[/green]")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Transcribing audio (this may take a while)...", total=None)
            transcript = await transcribe_audio(audio_path)
        
        # NEW: Describe each frame and append to transcript
        frame_descriptions = []
        if frames:
            # Initialize Gemini model once for all frames
            genai.configure(api_key=GEMINI_API_KEY)
            vision_model = genai.GenerativeModel('gemini-1.5-flash')
            
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                task = progress.add_task(description="Generating detailed frame descriptions...", total=len(frames))
                for i, frame_path in enumerate(frames):
                    timestamp = i * 15  # 15 seconds per frame
                    desc = await describe_image(frame_path, i, timestamp, vision_model)
                    frame_descriptions.append(desc)
                    progress.update(task, advance=1)
            frames_text = "\n".join(frame_descriptions)
            # Append frame descriptions to transcript
            transcript_with_images = transcript + "\n\n[Visual Context - Key frames every 15 seconds]\n" + frames_text
            console.print(f"[bold green][INFO] Audio transcript ready with {len(frames)} visual context frames. You can now ask questions![/bold green]")
        else:
            transcript_with_images = transcript
            console.print("[bold green][INFO] Transcript ready (no frames extracted). You can now ask questions![/bold green]")
        
        chunks = chunk_transcript(transcript_with_images, max_tokens=4000, overlap=500)
        total_tokens_full = estimate_tokens(transcript_with_images)
        total_tokens_sent = 0
        total_tokens_saved = 0
        cache_hits = 0
        cache_lookups = 0
        question_history = []
        console.print(Panel(f"[b]Video ID:[/b] {video_id}\n[b]Transcript length:[/b] {len(transcript_with_images)} chars, ~{total_tokens_full} tokens\n[b]Chunks created:[/b] {len(chunks)} (chunk size ~4000 tokens)", title="[bold magenta]VIDEO INFO[/bold magenta]", box=box.DOUBLE))
        console.print("[bold blue]Type your question and press Enter. Type 'exit' to quit.[/bold blue]\n")
        predictor = GeminiBatchPredictor(api_key=GEMINI_API_KEY, use_persistent_cache=True)
        try:
            while True:
                if question_history:
                    console.print(Panel("\n".join([f"[bold cyan]Q{idx+1}:[/bold cyan] {q}" for idx, q in enumerate(question_history)]), title="[bold yellow]Your Question History[/bold yellow]", style="yellow", box=box.ROUNDED))
                question = Prompt.ask("[bold yellow]\nAsk a question about the video[/bold yellow]").strip()
                if question.lower() in ("exit", "quit"): break
                question_history.append(question)
                console.rule("[bold cyan]PROCESS: Semantic Chunking & Context Selection[/bold cyan]")
                context = find_relevant_chunk(question, chunks)
                context_tokens = estimate_tokens(context)
                console.print(f"[bold]Selected chunk size:[/bold] {context_tokens} tokens (vs. {total_tokens_full} for full transcript)")
                console.print("[bold]Checking cache...[/bold]")
                cache_key = predictor._make_cache_key(video_id, question, context)
                cached = None
                if hasattr(predictor.cache, 'get'):
                    cached = predictor.cache.get(cache_key)
                    if asyncio.iscoroutine(cached):
                        cached = await cached
                cache_lookups += 1
                if cached:
                    cache_hits += 1
                    console.print(Panel(cached, title="[bold green]ANSWER (from cache)[/bold green]", style="green", box=box.ROUNDED))
                    tokens_saved = total_tokens_full - context_tokens
                    if tokens_saved > 0:
                        console.print(f"[bold green]Tokens saved this question:[/bold green] {tokens_saved}")
                    else:
                        console.print(f"[bold yellow]No tokens saved: full context was used.[/bold yellow]")
                    console.print(f"[bold green]Running total tokens saved:[/bold green] {total_tokens_saved + tokens_saved}")
                    total_tokens_saved += tokens_saved
                    continue
                with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                    progress.add_task(description="Sending context to Gemini API...", total=None)
                    questions = [{"question": question}]
                    results = await predictor.predict_batch(context, questions, use_chunking=False, video_id=video_id, context_override=context)
                console.print(Panel(results[0]["answer"], title="[bold blue]ANSWER[/bold blue]", style="blue", box=box.ROUNDED))
                total_tokens_sent += context_tokens
                tokens_saved = total_tokens_full - context_tokens
                if tokens_saved > 0:
                    console.print(f"[bold cyan]Tokens saved this question:[/bold cyan] {tokens_saved}")
                else:
                    console.print(f"[bold yellow]No tokens saved: full context was used.[/bold yellow]")
                console.print(f"[bold cyan]Running total tokens saved:[/bold cyan] {total_tokens_saved + tokens_saved}")
                total_tokens_saved += tokens_saved
                followup = Prompt.ask("[bold yellow]Is the answer satisfactory? (y/n)[/bold yellow]").strip().lower()
                if followup == 'n':
                    console.print("[bold magenta][INFO] Expanding context to more chunks...[/bold magenta]")
                    scored_chunks = [(c, sum(c.lower().count(k) for k in question.lower().split())) for c in chunks]
                    top_chunks = sorted(scored_chunks, key=lambda x: -x[1])[:3]
                    merged_context = '\n'.join([c[0] for c in top_chunks])
                    merged_tokens = estimate_tokens(merged_context)
                    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                        progress.add_task(description="Sending expanded context to Gemini API...", total=None)
                        results = await predictor.predict_batch(merged_context, questions, use_chunking=False, video_id=video_id, context_override=merged_context)
                    console.print(Panel(results[0]["answer"], title="[bold magenta]EXPANDED ANSWER[/bold magenta]", style="magenta", box=box.ROUNDED))
                    total_tokens_sent += merged_tokens
                    tokens_saved = total_tokens_full - merged_tokens
                    if tokens_saved > 0:
                        console.print(f"[bold magenta]Tokens saved (expanded):[/bold magenta] {tokens_saved}")
                    else:
                        console.print(f"[bold yellow]No tokens saved: full context was used.[/bold yellow]")
                    console.print(f"[bold magenta]Running total tokens saved:[/bold magenta] {total_tokens_saved + tokens_saved}")
                    total_tokens_saved += tokens_saved
        finally:
            await predictor.close()
        # Show summary dashboard
        console.rule("[bold green]SESSION SUMMARY[/bold green]")
        table = Table(title="Gemini API Usage Summary", show_lines=True, box=box.DOUBLE)
        table.add_column("Metric", style="bold")
        table.add_column("Value", style="cyan")
        table.add_row("Total tokens sent", str(total_tokens_sent))
        table.add_row("Total tokens saved", str(total_tokens_saved))
        table.add_row("Cache lookups", str(cache_lookups))
        table.add_row("Cache hits", str(cache_hits))
        hit_rate = f"{(cache_hits / cache_lookups * 100):.1f}%" if cache_lookups else "0%"
        table.add_row("Cache hit rate", hit_rate)
        console.print(table)
        console.print(Align.center("[bold cyan]Thank you for using HALO![/bold cyan]", vertical="middle"))
        console.print(Align.center("[green]Goodbye![/green]", vertical="middle"))

if __name__ == "__main__":
    asyncio.run(interactive_cli()) 