"""
Audio Trimming & Segmentation Engine
Powered by FFmpeg via imageio-ffmpeg
"""

import os
import subprocess
from pathlib import Path
import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def parse_timecode(tc_str: str) -> float:
    """Converts hh:mm:ss.ms or mm:ss or float seconds string into total seconds float."""
    tc_str = str(tc_str).strip()
    try:
        if ":" in tc_str:
            parts = tc_str.split(":")
            if len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
        return float(tc_str)
    except Exception:
        raise ValueError(f"Invalid timecode format: '{tc_str}'. Expected hh:mm:ss, mm:ss, or seconds.")

def format_time(seconds: float) -> str:
    """Formats float seconds into HH:MM:SS.mmm string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"

def get_audio_info(file_path: str | Path) -> dict:
    """Inspects audio duration, sample rate, channels, and file size using FFmpeg."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    cmd = [FFMPEG_EXE, "-i", str(file_path)]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    
    duration = 0.0
    bitrate = "N/A"
    sample_rate = "N/A"
    
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            duration = parse_timecode(parts)
            if "bitrate:" in line:
                bitrate = line.split("bitrate:")[1].strip()
        if "Audio:" in line:
            parts = line.split("Audio:")[1].split(",")
            if len(parts) >= 2:
                sample_rate = parts[1].strip()

    return {
        "filename": file_path.name,
        "path": str(file_path),
        "duration": duration,
        "duration_formatted": format_time(duration),
        "bitrate": bitrate,
        "sample_rate": sample_rate,
        "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
    }

def trim_segment(input_path: str | Path, start_sec: float, duration_sec: float, output_path: str | Path) -> Path:
    """Cuts an audio segment using lossless stream-copy (-c copy) with AAC re-encode fallback."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Primary lossless stream copy
    cmd = [
        FFMPEG_EXE,
        "-y",
        "-ss", str(start_sec),
        "-t", str(duration_sec),
        "-i", str(input_path),
        "-c", "copy",
        str(output_path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    
    # Fallback to AAC re-encode if stream copy fails
    if res.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        cmd = [
            FFMPEG_EXE,
            "-y",
            "-ss", str(start_sec),
            "-t", str(duration_sec),
            "-i", str(input_path),
            "-c:a", "aac",
            "-b:a", "128k",
            str(output_path)
        ]
        subprocess.run(cmd, check=True)

    return output_path

def split_into_parts(input_path: str | Path, parts_count: int, output_dir: str | Path = None) -> list[dict]:
    """Splits an audio file into N equal parts."""
    input_path = Path(input_path)
    info = get_audio_info(input_path)
    total_sec = info["duration"]
    seg_dur = total_sec / float(parts_count)

    if output_dir is None:
        output_dir = input_path.parent / f"{input_path.stem}_trimmed"
    else:
        output_dir = Path(output_dir)

    results = []
    for i in range(parts_count):
        start_t = i * seg_dur
        dur = seg_dur if i < parts_count - 1 else (total_sec - start_t)
        part_filename = f"{input_path.stem}_Part{i+1}{input_path.suffix}"
        out_file = output_dir / part_filename

        trim_segment(input_path, start_t, dur, out_file)
        p_info = get_audio_info(out_file)

        results.append({
            "part": i + 1,
            "filename": part_filename,
            "path": str(out_file),
            "start": format_time(start_t),
            "end": format_time(start_t + dur),
            "duration": format_time(p_info["duration"]),
            "size_mb": p_info["size_mb"]
        })

    return results
