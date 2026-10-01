"""
Automated Speech Recognition (ASR) Engine
Powered by Faster-Whisper / Whisper with int8 quantization support
"""

import os
import json
import time
from pathlib import Path

def transcribe_audio_file(audio_path: str | Path, model_name: str = "tiny.en", device: str = "cpu") -> dict:
    """Transcribes an audio file using Faster-Whisper ASR engine."""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file for transcription not found: {audio_path}")

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_name, device=device, compute_type="int8")
        segments, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
        
        segment_list = []
        full_text_chunks = []

        for s in segments:
            txt = s.text.strip()
            if txt:
                segment_list.append({
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "text": txt
                })
                full_text_chunks.append(txt)

        full_text = " ".join(full_text_chunks)

        return {
            "filename": audio_path.name,
            "path": str(audio_path),
            "duration": round(info.duration, 2),
            "language": info.language,
            "word_count": len(full_text.split()),
            "segments": segment_list,
            "full_text": full_text
        }

    except Exception as e:
        # Fallback to standard openai-whisper if faster-whisper hits compatibility issue
        import whisper
        model = whisper.load_model("tiny")
        res = model.transcribe(str(audio_path))
        
        return {
            "filename": audio_path.name,
            "path": str(audio_path),
            "duration": 0.0,
            "language": "en",
            "word_count": len(res["text"].split()),
            "segments": res.get("segments", []),
            "full_text": res["text"].strip()
        }

def batch_transcribe_files(audio_paths: list[str | Path], output_master_txt: str | Path, model_name: str = "tiny.en") -> dict:
    """Batch transcribes multiple audio files and consolidates into one master transcript file."""
    output_master_txt = Path(output_master_txt)
    output_master_txt.parent.mkdir(parents=True, exist_ok=True)

    combined_transcripts = []
    summary_data = []

    for path in audio_paths:
        p = Path(path)
        res = transcribe_audio_file(p, model_name=model_name)
        
        header = f"========================================================================\n" \
                 f"  TRANSCRIPT: {p.name}\n" \
                 f"  File: {p.name} | Duration: {res['duration']}s | Words: {res['word_count']}\n" \
                 f"========================================================================\n\n"
        
        body = res['full_text'] if res['full_text'] else "[No speech detected]"
        combined_transcripts.append(f"{header}{body}\n\n")
        summary_data.append(res)

    master_content = f"# MASTER AUDIO TRANSCRIPTION CONSOLIDATED REPORT\n" \
                     f"# Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n" \
                     f"# Total audio clips: {len(audio_paths)}\n\n" + "".join(combined_transcripts)

    output_master_txt.write_text(master_content, encoding="utf-8")
    
    return {
        "output_path": str(output_master_txt),
        "total_files": len(audio_paths),
        "total_words": sum(r["word_count"] for r in summary_data),
        "details": summary_data
    }
