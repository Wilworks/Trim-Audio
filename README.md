# ✂️ AudioTrimmer Pro & ASR Pipeline

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/Engine-FFmpeg-green.svg)](https://ffmpeg.org)
[![ASR](https://img.shields.io/badge/Speech%20Recognition-Faster--Whisper-magenta.svg)](https://github.com/SYSTRAN/faster-whisper)

A clean, open-source CLI for **transcribing speech from audio and video into searchable PDFs**, with audio trimming, segmentation, and transcript summaries.

```text
  █████╗ ██╗   ██╗██████╗ ██╗██╗███╗   ██╗████████╗██████╗ ██╗███╗   ██╗██████╗ 
 ██╔══██╗██║   ██║██╔══██╗██║██║████╗  ██║╚══██╔══╝██╔══██╗██║████╗  ██║██╔══██╗
 ███████║██║   ██║██║  ██║██║██║██╔██╗ ██║   ██║   ██████╔╝██║██╔██╗ ██║██████╔╝
 ██╔══██║██║   ██║██║  ██║██║██║██║╚██╗██║   ██║   ██╔══██╗██║██║╚██╗██║██╔══██╗
 ██║  ██║╚██████╔╝██████╔╝██║██║██║ ╚████║   ██║   ██║  ██║██║██║ ╚████║██████╔╝
 ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═════╝ 
```

---

## ✨ Key Features

- ⚡ **Lossless Stream-Copy Trimming**: Slices multi-hour audio files (`.m4a`, `.mp3`, `.wav`, `.aac`, `.flac`, `.ogg`) in seconds without re-encoding quality degradation.
- ✂️ **Multi-Mode Segmentation**:
  - **Equal Part Splitter**: Slices 1 audio file into $N$ equal parts automatically.
  - **Custom Timestamp Range**: Cut exact timecodes (`hh:mm:ss.ms` or seconds).
- 🎙️ **Built-in ASR Transcriber**: Uses `Faster-Whisper` with int8 CPU or FP16 Apple Silicon MPS execution.
- 📄 **Speech-to-PDF Export**: Transcribes audio or video speech into a clean, timestamped, searchable PDF.
- 📊 **Consolidated Reporting**: Automatically aggregates multi-clip transcripts into a single master `.txt` / `.md` file with word counts and timecodes.
- 🧠 **AI Transcript Summarizer**: Automatically parses massive (20,000+ word) transcripts into structured executive summaries, key advice takeaways, notable quotes, and section breakdowns.
- 🎨 **Rich Terminal Telemetry**: Beautiful CLI interface powered by `rich` with glowing hero banners, live progress bars, and diagnostic summary tables.

---

## 🚀 Quick Start & Installation

### 1. Clone Repository
```bash
git clone https://github.com/Wilworks/Trim-Audio.git
cd Trim-Audio
```

### 2. Install Package Locally
```bash
pip install -e .
```

Now you can run the `trim-audio` or `trimmer` command from anywhere in your terminal!

---

## 🛠️ Usage Examples

### 1. Split an Audio File into 2 Equal Parts
```bash
trim-audio split --input "my_recording.m4a" --parts 2 --output "./trimmed_output"
```

### 2. Split and Automatically Transcribe to Text
```bash
trim-audio split -i "lecture.mp3" -p 2 -o "./output" --transcribe
```

### 3. Trim a Specific Timestamp Range (e.g. 5m to 15m 30s)
```bash
trim-audio range -i "podcast.m4a" -s 00:05:00 -e 00:15:30 -o "./output"
```

### 4. Generate AI Executive Summary from Transcript
```bash
trim-audio summarize -i "TRANSCRIPT.txt" -o "SUMMARY.md"
```

### 5. Transcribe Speech from a Video to a PDF
```bash
trim-audio transcribe -i "Bioelectronics Lecture 4.mov" --device mps
```

The PDF is saved beside the source video as `Bioelectronics Lecture 4_transcript.pdf`.
It contains two parts: the original timestamped transcript, followed by organized,
comprehensive lecture notes. The notes are generated locally with Ollama's `qwen3:8b`
model; transcript text is sent only to the local Ollama service. Ollama must be running
with the model installed (`ollama pull qwen3:8b` if needed). The PDF title comes from
the video filename and includes lecturer Dr. Cletus Fiifi Adams, prepared by Wilfred
Ayine, and a clickable link to this repository. Use `--notes-model` to select another
local Ollama model, `--no-notes` for a transcript-only PDF, or `--author` to change
the prepared-by name. MPS is the default transcription device on Apple Silicon; use
`--device cpu` or `--device mps` to select it explicitly.

### 6. Interactive Mode
```bash
trim-audio
```
Use the arrow keys to select a workflow and press Enter.

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.
