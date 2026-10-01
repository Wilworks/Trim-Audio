# ✂️ AudioTrimmer Pro & ASR Pipeline

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![FFmpeg](https://img.shields.io/badge/Engine-FFmpeg-green.svg)](https://ffmpeg.org)
[![ASR](https://img.shields.io/badge/Speech%20Recognition-Faster--Whisper-magenta.svg)](https://github.com/SYSTRAN/faster-whisper)

A high-precision, open-source Command Line Tool (CLI) designed for **lossless audio trimming, segmenting, and automated speech-to-text transcription**. Built to process long recordings (conference talks, lectures, audiobooks, podcasts) into manageable chunks for reading and study.

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
- 🎙️ **Built-in ASR Transcriber**: Integrates `Faster-Whisper` (int8 quantized CPU execution) to convert trimmed audio chunks into clean text transcripts.
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

### 5. Interactive Mode
```bash
trim-audio
```

---

## 📲 LinkedIn Post Template (Copy & Share!)

> **Building tools to solve my own learning workflows 🚀**
> 
> I recently had several long audio recordings (over 4 hours of conference sessions) that I needed to review and study. Instead of manually listening through or fighting with bloated online tools, I built **AudioTrimmer Pro** — an open-source CLI tool that:
> 
> ✂️ Slices massive audio recordings into equal parts losslessly in seconds via FFmpeg  
> 🎙️ Automatically transcribes every audio segment using quantized Faster-Whisper  
> 📄 Compiles everything into a single structured master text transcript for easy reading  
> 
> Decided to drop the code completely free and open-source on GitHub for anyone who needs fast audio segmentation and transcription:
> 
> 🔗 **GitHub Repository**: https://github.com/Wilworks/Trim-Audio
> 
> #Python #OpenSource #AI #Whisper #FFmpeg #SoftwareEngineering #BuildInPublic

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.
