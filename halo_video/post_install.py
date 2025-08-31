#!/usr/bin/env python3
"""
Post-installation welcome message for HALO Video
Built by Jeet Dekivadia during Google Summer of Code at Google DeepMind
"""

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()

def show_welcome():
    """Show welcome message after installation"""
    welcome_panel = Panel(
        """[bold green]HALO Video v1.0.5 installed successfully![/bold green]

[yellow]HALO: Hierarchical Abstraction for Longform Optimization[/yellow]
[dim]Built by Jeet Dekivadia during Google Summer of Code 2025 at Google DeepMind[/dim]

[green]What HALO does:[/green]
Optimizes Gemini API usage for long-context YouTube video analysis
through intelligent frame extraction and hierarchical processing.

[yellow]Quick Start:[/yellow]
1. Get your free Gemini API key: [blue]https://makersuite.google.com/app/apikey[/blue]
2. Run: [bold cyan]halo-video[/bold cyan]
3. Follow the guided setup

[yellow]Key Features:[/yellow]
• AI-powered frame analysis with Google Gemini Vision
• 90% reduction in API calls through smart optimization
• Automatic FFmpeg installation and setup  
• Cross-platform support (Windows, macOS, Linux)
• Production-ready with comprehensive error handling

[yellow]Commands:[/yellow]
• [cyan]halo-video[/cyan] - Start interactive CLI
• [cyan]halo-video --help[/cyan] - View all options

[dim]Repository: https://github.com/jeet-dekivadia/google-deepmind[/dim]
[dim]Contact: jeet.university@gmail.com[/dim]""",
        title="[bold blue]Welcome to HALO Video[/bold blue]",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    
    console.print(welcome_panel)

if __name__ == "__main__":
    show_welcome()
