"""
AI Transcript Summarizer & Action Items Extractor
Intelligent text processing for large ASR transcripts
"""

import os
import re
import math
from collections import Counter
from pathlib import Path

def extract_keywords_tfidf(text: str, top_n: int = 15) -> list[str]:
    """Extracts top meaningful key terms from text, filtering out common stop words."""
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    stop_words = {
        'the', 'and', 'that', 'have', 'for', 'not', 'with', 'you', 'this', 'but',
        'his', 'from', 'they', 'say', 'her', 'she', 'or', 'an', 'will', 'my', 'one',
        'all', 'would', 'there', 'their', 'what', 'so', 'up', 'out', 'if', 'about',
        'who', 'get', 'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time',
        'no', 'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your', 'good',
        'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only',
        'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use', 'two', 'how',
        'our', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any',
        'these', 'give', 'day', 'most', 'us', 'are', 'was', 'were', 'been', 'being'
    }
    filtered = [w for w in words if w not in stop_words]
    counts = Counter(filtered)
    return [item[0].capitalize() for item in counts.most_common(top_n)]

def summarize_transcript(transcript_text: str, title: str = "Audio Transcript Summary") -> dict:
    """Processes large multi-part transcript text and generates a structured Markdown summary report."""
    # Split text into sections if delimited by headers
    sections = []
    current_section = {"header": "General Content", "text": []}
    
    for line in transcript_text.splitlines():
        if line.startswith("===") or line.startswith("# MASTER") or line.startswith("# TRANSCRIPT"):
            continue
        if "TRANSCRIPT:" in line or line.startswith("## "):
            if current_section["text"]:
                sections.append({
                    "header": current_section["header"],
                    "content": "\n".join(current_section["text"]).strip()
                })
            current_section = {"header": line.replace("TRANSCRIPT:", "").replace("#", "").strip(), "text": []}
        else:
            if line.strip():
                current_section["text"].append(line.strip())

    if current_section["text"]:
        sections.append({
            "header": current_section["header"],
            "content": "\n".join(current_section["text"]).strip()
        })

    # Global keywords
    keywords = extract_keywords_tfidf(transcript_text, top_n=12)

    # Generate section breakdowns
    section_summaries = []
    action_items = []
    key_quotes = []

    for idx, sec in enumerate(sections):
        content = sec["content"]
        sentences = re.split(r'(?<=[.!?]) +', content)
        
        # Pick representative sentences for summary
        summary_sentences = [s for s in sentences if len(s.split()) >= 8][:3]
        sec_summary = " ".join(summary_sentences) if summary_sentences else content[:300] + "..."

        # Look for potential action items or key takeaways (patterns with 'need', 'should', 'important', 'advice')
        for s in sentences:
            s_lower = s.lower()
            if any(k in s_lower for k in ['advice', 'important', 'should', 'need to', 'must', 'key', 'recommend']):
                if 10 <= len(s.split()) <= 35 and len(action_items) < 8:
                    action_items.append(s.strip())
            if any(k in s_lower for k in ['i think', 'believe', 'remember', 'future', 'technology']):
                if 12 <= len(s.split()) <= 30 and len(key_quotes) < 5:
                    key_quotes.append(f'"{s.strip()}"')

        section_summaries.append({
            "part_number": idx + 1,
            "title": sec["header"],
            "word_count": len(content.split()),
            "summary": sec_summary
        })

    # Construct clean markdown report
    md = f"# 🧠 Executive AI Summary: {title}\n\n"
    md += f"**Total Words Analyzed**: {len(transcript_text.split()):,} words | **Sections**: {len(sections)}\n\n"
    md += "---\n\n"

    md += "## 🎯 Key Topics & Discussion Themes\n"
    for kw in keywords:
        md += f"- `{kw}`\n"
    md += "\n---\n\n"

    md += "## 💡 Key Takeaways & Advice\n"
    for item in action_items[:6]:
        md += f"- **Takeaway**: {item}\n"
    md += "\n---\n\n"

    if key_quotes:
        md += "## 💬 Notable Quotes & Insights\n"
        for q in key_quotes[:4]:
            md += f"- {q}\n"
        md += "\n---\n\n"

    md += "## 📝 Section-by-Section Executive Breakdown\n\n"
    for s in section_summaries:
        md += f"### 📌 Part {s['part_number']}: {s['title']}\n"
        md += f"**Length**: {s['word_count']:,} words\n\n"
        md += f"> {s['summary']}\n\n"

    return {
        "title": title,
        "total_words": len(transcript_text.split()),
        "keywords": keywords,
        "action_items": action_items,
        "key_quotes": key_quotes,
        "section_summaries": section_summaries,
        "markdown_report": md
    }

def summarize_file(input_file: str | Path, output_file: str | Path = None) -> Path:
    """Summarizes a transcript text file and exports the executive summary to Markdown."""
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Transcript file not found: {input_path}")

    text = input_path.read_text(encoding="utf-8")
    title = input_path.stem.replace("_", " ").title()

    res = summarize_transcript(text, title=title)

    if output_file is None:
        output_path = input_path.parent / f"{input_path.stem}_SUMMARY.md"
    else:
        output_path = Path(output_file)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(res["markdown_report"], encoding="utf-8")

    return output_path
