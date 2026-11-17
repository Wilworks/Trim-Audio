"""
AudioTrimmer Pro CLI Application
Rich Terminal Telemetry & Command Dispatcher
"""

import os
import sys
import io
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

from .trimmer import get_audio_info, trim_segment, split_into_parts, parse_timecode, format_time
from .transcriber import DEFAULT_DEVICE, transcribe_audio_file, batch_transcribe_files
from .pdf_export import DEFAULT_LECTURER, create_transcript_pdf
from .summarizer import summarize_file

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

console = Console(force_terminal=True)

def render_hero_banner():
    banner = (
        "[bold cyan]TRIM AUDIO[/bold cyan]\n"
        "[bold white]Speech to searchable PDF[/bold white]\n"
        "[dim]Audio & video transcription · audio tools[/dim]"
    )
    console.print(
        Panel(
            banner,
            title="TRANSCRIPT STUDIO",
            box=box.ROUNDED,
            border_style="cyan",
            expand=False,
        )
    )

def _strip_path_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

def cmd_split(args):
    render_hero_banner()
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[bold red]❌ File not found:[/] {input_path}")
        return

    out_dir = Path(args.output) if args.output else input_path.parent / f"{input_path.stem}_trimmed"
    out_dir.mkdir(parents=True, exist_ok=True)

    info = get_audio_info(input_path)
    console.print(f"\n[bold yellow]🎵 Audio File:[/] [cyan]{input_path.name}[/cyan] ({info['duration_formatted']})")
    console.print(f"[bold green]✂️ Mode:[/] Splitting into [bold white]{args.parts}[/bold white] equal parts\n")

    results = []
    seg_dur = info["duration"] / float(args.parts)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold bright_cyan]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="bright_green"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Trimming clips...", total=args.parts)
        
        for i in range(args.parts):
            start_t = i * seg_dur
            dur = seg_dur if i < args.parts - 1 else (info["duration"] - start_t)
            out_file = out_dir / f"{input_path.stem}_Part{i+1}{input_path.suffix}"
            
            progress.update(task, description=f"Exporting Part {i+1}/{args.parts}: {out_file.name}")
            trim_segment(input_path, start_t, dur, out_file)
            p_info = get_audio_info(out_file)
            
            results.append({
                "part": i + 1,
                "filename": out_file.name,
                "path": str(out_file),
                "range": f"{format_time(start_t)} ➔ {format_time(start_t + dur)}",
                "duration": p_info["duration_formatted"],
                "size_mb": f"{p_info['size_mb']} MB"
            })
            progress.advance(task)

    table = Table(title="[bold bright_green]📊 TRIMMING RESULTS[/bold bright_green]", box=box.DOUBLE_EDGE, header_style="bold bright_cyan")
    table.add_column("#", style="bold white")
    table.add_column("Filename", style="bold yellow")
    table.add_column("Timecode Range", style="bold blue")
    table.add_column("Duration", style="bold green")
    table.add_column("Size", style="bold magenta")
    table.add_column("Status", style="bold white")

    for r in results:
        table.add_row(str(r["part"]), r["filename"], r["range"], r["duration"], r["size_mb"], "[bold black on bright_green] ✔ EXPORTED [/]")

    console.print("\n", table)
    console.print(f"\n[bold black on bright_cyan] 📁 OUTPUT FOLDER [/] Saved to: [underline]{out_dir}[/underline]\n")

    if getattr(args, "transcribe", False):
        master_txt = out_dir / "TRANSCRIPT_COMBINED.txt"
        cmd_transcribe_files([r["path"] for r in results], master_txt)
        if getattr(args, "summarize", False):
            cmd_summarize(master_txt)

def cmd_range(args):
    render_hero_banner()
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[bold red]❌ File not found:[/] {input_path}")
        return

    start_sec = parse_timecode(args.start)
    end_sec = parse_timecode(args.end)
    dur_sec = end_sec - start_sec

    out_dir = Path(args.output) if args.output else input_path.parent / "trimmed_output"
    out_file = out_dir / f"{input_path.stem}_Trimmed{input_path.suffix}"

    console.print(f"\n[bold yellow]🎵 File:[/] [cyan]{input_path.name}[/cyan]")
    console.print(f"[bold green]✂️ Range:[/] {format_time(start_sec)} ➔ {format_time(end_sec)} (Duration: {format_time(dur_sec)})\n")

    trim_segment(input_path, start_sec, dur_sec, out_file)
    p_info = get_audio_info(out_file)

    console.print(f"[bold black on bright_green] ✔ CLIP EXPORTED [/] {out_file.name} ({p_info['duration_formatted']}, {p_info['size_mb']} MB)\n")

def cmd_transcribe_files(audio_files, master_out):
    console.print("\n[bold yellow]🎙️ Phase: Running Faster-Whisper ASR Transcription...[/bold yellow]")
    res = batch_transcribe_files(audio_files, master_out)
    console.print(f"[bold black on bright_green] 🎉 TRANSCRIPTION COMPLETE [/] Total Words: {res['total_words']}")
    console.print(f"📁 Master Transcript Saved To: [underline]{res['output_path']}[/underline]\n")

def cmd_transcribe(args):
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[bold red]❌ File not found:[/] {input_path}")
        return

    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}_transcript.pdf")
    device = getattr(args, "device", DEFAULT_DEVICE)
    console.print(
        f"\n[bold yellow]🎙️ Transcribing speech from:[/] [cyan]{input_path.name}[/cyan] "
        f"using [cyan]{device}[/cyan]..."
    )
    result = transcribe_audio_file(input_path, model_name=args.model, device=device)
    pdf_path = create_transcript_pdf(result, output_path, lecturer=args.lecturer)
    console.print(f"[bold black on bright_green] ✔ TRANSCRIPT PDF GENERATED [/] Total Words: {result['word_count']}")
    console.print(f"📁 PDF Saved To: [underline]{pdf_path}[/underline]\n")

def cmd_summarize(args_or_path):
    if hasattr(args_or_path, "input"):
        render_hero_banner()
        input_path = Path(args_or_path.input)
        output_path = args_or_path.output
    else:
        input_path = Path(args_or_path)
        output_path = None

    if not input_path.exists():
        console.print(f"[bold red]❌ Transcript file not found:[/] {input_path}")
        return

    console.print(f"\n[bold yellow]🧠 Running AI Transcript Summarizer on:[/] [cyan]{input_path.name}[/cyan]...")
    out = summarize_file(input_path, output_path)
    console.print(f"[bold black on bright_green] ✔ AI SUMMARY GENERATED [/] Saved to: [underline]{out}[/underline]\n")

def interactive_menu():
    render_hero_banner()
    console.print("[bold yellow]Choose a workflow:[/bold yellow]")
    console.print(" 1. Transcribe audio/video to a searchable PDF")
    console.print(" 2. Split audio into equal parts")
    console.print(" 3. Trim audio by timestamp")
    console.print(" 4. Summarize an existing transcript")
    console.print(" 5. Exit\n")

    choice = input("Enter choice (1-5): ").strip()
    if choice == "1":
        f_path = _strip_path_quotes(input("Enter audio or video file path: "))
        o_path = _strip_path_quotes(input("Output PDF path (Enter for default): "))
        device = input(f"Device (mps/cpu, default {DEFAULT_DEVICE}): ").strip().lower() or DEFAULT_DEVICE
        cmd_transcribe(argparse.Namespace(
            input=f_path,
            output=o_path or None,
            lecturer=DEFAULT_LECTURER,
            model="tiny.en",
            device=device,
        ))
    elif choice == "2":
        f_path = _strip_path_quotes(input("Enter audio file path: "))
        parts = input("Number of parts (default 2): ").strip()
        parts_cnt = int(parts) if parts.isdigit() else 2
        o_dir = _strip_path_quotes(input("Output folder (Enter for default): "))
        
        class Args:
            input = f_path
            parts = parts_cnt
            output = o_dir if o_dir else None
            transcribe = False
            summarize = False

        cmd_split(Args())
    elif choice == "3":
        f_path = _strip_path_quotes(input("Enter audio file path: "))
        s_tc = input("Start time (hh:mm:ss or seconds): ").strip()
        e_tc = input("End time (hh:mm:ss or seconds): ").strip()
        o_dir = _strip_path_quotes(input("Output folder (Enter for default): "))

        class Args:
            input = f_path
            start = s_tc
            end = e_tc
            output = o_dir if o_dir else None

        cmd_range(Args())
    elif choice == "4":
        t_path = _strip_path_quotes(input("Enter path to transcript file (.txt / .md): "))
        cmd_summarize(t_path)

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio or video to searchable PDFs, with audio trimming and transcript tools."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Split
    s_parser = subparsers.add_parser("split", help="Split audio file into N equal parts")
    s_parser.add_argument("-i", "--input", required=True, help="Input audio file path")
    s_parser.add_argument("-p", "--parts", type=int, default=2, help="Number of parts (default: 2)")
    s_parser.add_argument("-o", "--output", default=None, help="Output folder")
    s_parser.add_argument("-t", "--transcribe", action="store_true", help="Automatically transcribe trimmed parts")
    s_parser.add_argument("-s", "--summarize", action="store_true", help="Generate AI summary report after transcribing")

    # Range
    r_parser = subparsers.add_parser("range", help="Trim custom timecode range")
    r_parser.add_argument("-i", "--input", required=True, help="Input audio file path")
    r_parser.add_argument("-s", "--start", required=True, help="Start timecode")
    r_parser.add_argument("-e", "--end", required=True, help="End timecode")
    r_parser.add_argument("-o", "--output", default=None, help="Output folder")

    # Summarize
    sum_parser = subparsers.add_parser("summarize", help="Generate AI summary from a transcript file")
    sum_parser.add_argument("-i", "--input", required=True, help="Path to transcript file (.txt / .md)")
    sum_parser.add_argument("-o", "--output", default=None, help="Output summary Markdown file path")

    # Transcribe speech from an audio or video file and export a PDF.
    t_parser = subparsers.add_parser("transcribe", help="Transcribe speech from audio or video into a PDF")
    t_parser.add_argument("-i", "--input", required=True, help="Input audio or video file path")
    t_parser.add_argument("-o", "--output", default=None, help="Output PDF path (defaults beside input)")
    t_parser.add_argument("--lecturer", default=DEFAULT_LECTURER, help="Lecturer name printed in the PDF")
    t_parser.add_argument("--model", default="tiny.en", help="Whisper model name (default: tiny.en)")
    t_parser.add_argument(
        "--device",
        choices=("mps", "cpu"),
        default=DEFAULT_DEVICE,
        help=f"Transcription device (default: {DEFAULT_DEVICE})",
    )

    args = parser.parse_args()

    if args.command is None:
        interactive_menu()
    elif args.command == "split":
        cmd_split(args)
    elif args.command == "range":
        cmd_range(args)
    elif args.command == "summarize":
        cmd_summarize(args)
    elif args.command == "transcribe":
        cmd_transcribe(args)

if __name__ == "__main__":
    main()
