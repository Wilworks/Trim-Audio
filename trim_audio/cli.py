"""
AudioTrimmer Pro CLI Application
Rich Terminal Telemetry & Command Dispatcher
"""

import os
import sys
import io
import re
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich import box
from questionary import Choice, Style, select

from .trimmer import get_audio_info, trim_segment, split_into_parts, parse_timecode, format_time
from .transcriber import DEFAULT_DEVICE, transcribe_audio_file, batch_transcribe_files
from .pdf_export import DEFAULT_AUTHOR, DEFAULT_LECTURER, create_transcript_pdf
from .notes_builder import DEFAULT_NOTES_MODEL, build_lecture_notes
from .summarizer import summarize_file

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

console = Console(force_terminal=True)
menu_style = Style([
    ("qmark", "fg:#2563eb bold"),
    ("question", "bold"),
    ("answer", "fg:#2563eb bold"),
    ("pointer", "fg:#2563eb bold"),
    ("highlighted", "fg:#2563eb bold"),
    ("selected", "fg:#2563eb"),
    ("instruction", "fg:#64748b"),
])

def render_hero_banner():
    banner = (
        "[bold white]Audio & Video Transcript Studio[/bold white]\n"
        "[dim]Turn spoken audio into a clean, searchable PDF.[/dim]"
    )
    console.print(
        Panel(
            banner,
            title="[bold cyan]TRIM AUDIO[/bold cyan]",
            box=box.ROUNDED,
            border_style="bright_blue",
            expand=False,
        )
    )

def _strip_path_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

def _prompt_timecode(label: str) -> str:
    while True:
        value = input(label).strip()
        try:
            parse_timecode(value)
            return value
        except ValueError as exc:
            console.print(f"[bold red]Invalid timecode:[/] {exc}")

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

    try:
        start_sec = parse_timecode(args.start)
        end_sec = parse_timecode(args.end)
    except ValueError as exc:
        console.print(f"[bold red]Invalid time range:[/] {exc}")
        return
    if start_sec < 0 or end_sec <= start_sec:
        console.print("[bold red]Invalid time range:[/] End time must be after the start time.")
        return
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

def _create_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40, style="blue", complete_style="bright_green"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    )

def _transcribe_with_progress(input_path, model_name, device):
    with _create_progress() as progress:
        task = progress.add_task("Loading model and decoding media...", total=None)

        def update_transcription_progress(completed, duration):
            if duration > 0:
                progress.update(
                    task,
                    description="Transcribing audio timeline",
                    total=duration,
                    completed=min(max(completed, 0), duration),
                )

        result = transcribe_audio_file(
            input_path,
            model_name=model_name,
            device=device,
            progress_callback=update_transcription_progress,
        )
        duration = float(result.get("duration") or 0)
        if duration > 0:
            progress.update(
                task,
                description="Transcription complete",
                total=duration,
                completed=duration,
            )
        else:
            progress.update(
                task,
                description="Transcription complete",
                total=1,
                completed=1,
            )
    return result

def _build_notes_with_progress(transcription, model):
    with _create_progress() as progress:
        task = progress.add_task("Preparing local lecture notes...", total=1)

        def update_notes_progress(completed, total, phase):
            progress.update(
                task,
                description=f"{phase} · {completed}/{total} model requests",
                total=total,
                completed=completed,
            )

        return build_lecture_notes(
            transcription,
            model=model,
            progress_callback=update_notes_progress,
        )

def cmd_transcribe(args):
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[bold red]❌ File not found:[/] {input_path}")
        return
    if not input_path.is_file():
        console.print(
            f"[bold red]❌ Input path is not a file. Select an audio/video file, not a folder:[/] "
            f"{input_path}"
        )
        return

    output_path = Path(args.output) if args.output else input_path.with_name(f"{input_path.stem}_transcript.pdf")
    device = getattr(args, "device", DEFAULT_DEVICE)
    console.print(
        f"\n[bold yellow]🎙️ Transcribing speech from:[/] [cyan]{input_path.name}[/cyan] "
        f"using [cyan]{device}[/cyan]..."
    )
    result = _transcribe_with_progress(input_path, model_name=args.model, device=device)
    author = getattr(args, "author", DEFAULT_AUTHOR)
    lecture_notes = None
    notes_model = None
    if getattr(args, "build_notes", True):
        notes_model = getattr(args, "notes_model", DEFAULT_NOTES_MODEL)
        try:
            lecture_notes = _build_notes_with_progress(result, model=notes_model)
        except RuntimeError as exc:
            console.print(
                f"[bold red]Could not build lecture notes; no PDF was created:[/] {exc}"
            )
            return

    pdf_path = create_transcript_pdf(
        result,
        output_path,
        lecturer=args.lecturer,
        author=author,
        lecture_notes=lecture_notes,
        notes_model=notes_model,
    )
    console.print(f"[bold black on bright_green] ✔ TRANSCRIPT PDF GENERATED [/] Total Words: {result['word_count']}")
    console.print(f"📁 PDF Saved To: [underline]{pdf_path}[/underline]\n")

def _clean_transcript_text(text):
    if "# MASTER AUDIO TRANSCRIPTION CONSOLIDATED REPORT" not in text:
        return text.strip()

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("# MASTER")
            or stripped.startswith("# Generated on:")
            or stripped.startswith("# Total audio clips:")
            or re.fullmatch(r"=+", stripped)
            or re.fullmatch(r"File: .+ \| Duration: .+ \| Words: \d+", stripped)
        ):
            continue
        transcript_header = re.match(r"^\s*TRANSCRIPT:\s*(.+)$", line)
        if transcript_header:
            lines.extend(["", f"## {transcript_header.group(1).strip()}", ""])
        else:
            lines.append(line)
    return "\n".join(lines).strip()

def cmd_build_notes(args):
    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[bold red]❌ Transcript file not found:[/] {input_path}")
        return
    try:
        transcript_text = _clean_transcript_text(input_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        console.print(f"[bold red]Could not read transcript:[/] {exc}")
        return
    if not transcript_text:
        console.print("[bold red]Transcript file is empty; no PDF was created.[/]")
        return

    transcription = {
        "filename": input_path.name,
        "path": str(input_path),
        "word_count": len(transcript_text.split()),
        "segments": [],
        "full_text": transcript_text,
    }
    notes_model = args.notes_model
    output_path = (
        Path(args.output)
        if args.output
        else input_path.with_name(f"{input_path.stem}_notes.pdf")
    )
    console.print(
        f"\n[bold yellow]🧠 Building lecture notes from:[/] [cyan]{input_path.name}[/cyan]"
    )
    try:
        lecture_notes = _build_notes_with_progress(transcription, model=notes_model)
    except RuntimeError as exc:
        console.print(f"[bold red]Could not build lecture notes; no PDF was created:[/] {exc}")
        return

    pdf_path = create_transcript_pdf(
        transcription,
        output_path,
        lecturer=args.lecturer,
        author=args.author,
        lecture_notes=lecture_notes,
        notes_model=notes_model,
    )
    console.print(f"[bold black on bright_green] ✔ LECTURE NOTES PDF GENERATED [/]")
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
    try:
        _run_interactive_menu()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled.[/dim]")
        return

def _run_interactive_menu():
    choice = select(
        "What would you like to do?",
        choices=[
            Choice("Transcribe audio/video  ·  searchable PDF  ·  MPS on Apple Silicon", value="transcribe"),
            Choice("Build lecture notes from a transcript  ·  local Ollama", value="notes"),
            Choice("Split audio  ·  equal parts", value="split"),
            Choice("Trim audio  ·  choose a time range", value="range"),
            Choice("Summarize a transcript", value="summarize"),
            Choice("Quit", value="quit"),
        ],
        qmark="?",
        style=menu_style,
        instruction="(Use arrow keys and press Enter)",
        use_shortcuts=True,
    ).ask()

    if choice == "transcribe":
        f_path = _strip_path_quotes(input("Enter audio or video file path: "))
        if not Path(f_path).is_file():
            console.print(
                f"[bold red]❌ Select an audio/video file, not a folder or missing path:[/] "
                f"{f_path}"
            )
            return
        o_path = _strip_path_quotes(input("Output PDF path (Enter for default): "))
        device = input(f"Device (mps/cpu, default {DEFAULT_DEVICE}): ").strip().lower() or DEFAULT_DEVICE
        lecturer = _strip_path_quotes(
            input(f"Lecturer (Enter for {DEFAULT_LECTURER}): ")
        ) or DEFAULT_LECTURER
        author = _strip_path_quotes(
            input(f"Prepared by (Enter for {DEFAULT_AUTHOR}): ")
        ) or DEFAULT_AUTHOR
        build_notes = input("Build lecture notes? (Y/n): ").strip().lower() not in {"n", "no"}
        notes_model = DEFAULT_NOTES_MODEL
        if build_notes:
            notes_model = (
                input(f"Local notes model (Enter for {DEFAULT_NOTES_MODEL}): ").strip()
                or DEFAULT_NOTES_MODEL
            )
        cmd_transcribe(argparse.Namespace(
            input=f_path,
            output=o_path or None,
            lecturer=lecturer,
            author=author,
            model="tiny.en",
            device=device,
            notes_model=notes_model,
            build_notes=build_notes,
        ))
    elif choice == "notes":
        t_path = _strip_path_quotes(input("Enter path to transcript file (.txt / .md): "))
        o_path = _strip_path_quotes(input("Output PDF path (Enter for default): "))
        lecturer = _strip_path_quotes(
            input(f"Lecturer (Enter for {DEFAULT_LECTURER}): ")
        ) or DEFAULT_LECTURER
        author = _strip_path_quotes(
            input(f"Prepared by (Enter for {DEFAULT_AUTHOR}): ")
        ) or DEFAULT_AUTHOR
        notes_model = (
            input(f"Local notes model (Enter for {DEFAULT_NOTES_MODEL}): ").strip()
            or DEFAULT_NOTES_MODEL
        )
        cmd_build_notes(argparse.Namespace(
            input=t_path,
            output=o_path or None,
            lecturer=lecturer,
            author=author,
            notes_model=notes_model,
        ))
    elif choice == "split":
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
    elif choice == "range":
        f_path = _strip_path_quotes(input("Enter audio file path: "))
        s_tc = _prompt_timecode("Start time (hh:mm:ss or seconds): ")
        e_tc = _prompt_timecode("End time (hh:mm:ss or seconds): ")
        o_dir = _strip_path_quotes(input("Output folder (Enter for default): "))

        class Args:
            input = f_path
            start = s_tc
            end = e_tc
            output = o_dir if o_dir else None

        cmd_range(Args())
    elif choice == "summarize":
        t_path = _strip_path_quotes(input("Enter path to transcript file (.txt / .md): "))
        cmd_summarize(t_path)

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio or video to searchable PDFs, with audio trimming and transcript tools.",
        epilog="Run without a command to open the interactive workflow picker.",
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
    t_parser.add_argument("--author", default=DEFAULT_AUTHOR, help="Your name printed in the PDF")
    t_parser.add_argument("--model", default="tiny.en", help="Whisper model name (default: tiny.en)")
    t_parser.add_argument(
        "--notes-model",
        default=DEFAULT_NOTES_MODEL,
        help=f"Local Ollama model for lecture notes (default: {DEFAULT_NOTES_MODEL})",
    )
    t_parser.add_argument(
        "--no-notes",
        dest="build_notes",
        action="store_false",
        help="Create a transcript-only PDF without local AI lecture notes",
    )
    t_parser.add_argument(
        "--device",
        choices=("mps", "cpu"),
        default=DEFAULT_DEVICE,
        help=f"Transcription device (default: {DEFAULT_DEVICE})",
    )

    # Build lecture notes from an existing text transcript.
    notes_parser = subparsers.add_parser(
        "notes",
        help="Build a two-part notes PDF from an existing transcript file",
    )
    notes_parser.add_argument("-i", "--input", required=True, help="Transcript text file (.txt or .md)")
    notes_parser.add_argument("-o", "--output", default=None, help="Output PDF path")
    notes_parser.add_argument(
        "--lecturer", default=DEFAULT_LECTURER, help="Lecturer name printed in the PDF"
    )
    notes_parser.add_argument("--author", default=DEFAULT_AUTHOR, help="Your name printed in the PDF")
    notes_parser.add_argument(
        "--notes-model",
        default=DEFAULT_NOTES_MODEL,
        help=f"Local Ollama model for lecture notes (default: {DEFAULT_NOTES_MODEL})",
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
    elif args.command == "notes":
        cmd_build_notes(args)

if __name__ == "__main__":
    main()
