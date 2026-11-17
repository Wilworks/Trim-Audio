"""Clean, searchable PDF export for speech transcripts."""

from datetime import datetime
from html import escape
from pathlib import Path
import re

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

REPOSITORY_URL = "https://github.com/Wilworks/Trim-Audio"
DEFAULT_LECTURER = "Dr. Cletus Fiifi Adams"
DEFAULT_AUTHOR = "Wilfred Ayine"


def _register_fonts() -> tuple[str, str]:
    fonts_dir = Path(reportlab.__file__).parent / "fonts"
    regular_name = "TranscriptVera"
    bold_name = "TranscriptVera-Bold"
    pdfmetrics.registerFont(TTFont(regular_name, str(fonts_dir / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont(bold_name, str(fonts_dir / "VeraBd.ttf")))
    return regular_name, bold_name


def _format_timestamp(seconds: float) -> str:
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def _format_note_text(text: str) -> str:
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)


def _lecture_note_story(notes: str, regular_font: str, bold_font: str) -> list:
    styles = getSampleStyleSheet()
    heading_styles = {
        1: ParagraphStyle(
            "NotesHeading1",
            parent=styles["Heading1"],
            fontName=bold_font,
            fontSize=17,
            leading=22,
            textColor=colors.HexColor("#18324B"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        2: ParagraphStyle(
            "NotesHeading2",
            parent=styles["Heading2"],
            fontName=bold_font,
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#287C82"),
            spaceBefore=9,
            spaceAfter=4,
        ),
        3: ParagraphStyle(
            "NotesHeading3",
            parent=styles["Heading3"],
            fontName=bold_font,
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#18324B"),
            spaceBefore=7,
            spaceAfter=3,
        ),
    }
    body_style = ParagraphStyle(
        "NotesBody",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#202A34"),
        spaceAfter=5,
    )
    quote_style = ParagraphStyle(
        "NotesQuote",
        parent=body_style,
        leftIndent=8 * mm,
        textColor=colors.HexColor("#566575"),
    )

    story = []
    in_code_block = False
    for raw_line in notes.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if not line or line in {"---", "***", "___"}:
            continue
        if in_code_block:
            story.append(Paragraph(_format_note_text(line), body_style))
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            heading_text = heading.group(2).strip()
            if heading_text.casefold() not in {"lecture notes", "comprehensive lecture notes"}:
                story.append(
                    Paragraph(_format_note_text(heading_text), heading_styles[len(heading.group(1))])
                )
            continue

        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if bullet:
            story.append(
                Paragraph(_format_note_text(bullet.group(1)), body_style, bulletText="•")
            )
            continue

        numbered_item = re.match(r"^(\d+)[.)]\s+(.+)$", line)
        if numbered_item:
            story.append(
                Paragraph(
                    _format_note_text(numbered_item.group(2)),
                    body_style,
                    bulletText=f"{numbered_item.group(1)}.",
                )
            )
            continue

        if line.startswith(">"):
            story.append(Paragraph(_format_note_text(line[1:].strip()), quote_style))
        else:
            story.append(Paragraph(_format_note_text(line), body_style))
    return story


def create_transcript_pdf(
    transcription: dict,
    output_path: str | Path,
    lecturer: str = DEFAULT_LECTURER,
    author: str = DEFAULT_AUTHOR,
    lecture_notes: str | None = None,
    notes_model: str | None = None,
) -> Path:
    """Write a searchable transcript PDF, optionally followed by lecture notes."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_name = transcription.get("filename") or Path(transcription.get("path", "Transcript")).name
    title = Path(source_name).stem
    regular_font, bold_font = _register_fonts()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TranscriptTitle",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=22,
        leading=28,
        textColor=colors.HexColor("#18324B"),
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "TranscriptMeta",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#566575"),
        spaceAfter=2,
    )
    body_style = ParagraphStyle(
        "TranscriptBody",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#202A34"),
        spaceAfter=8,
    )

    duration = transcription.get("duration")
    duration_text = f"{_format_timestamp(duration)} duration" if duration is not None else None
    details = [
        f"Lecturer: {escape(lecturer)}",
        f"Prepared by: {escape(author)}",
        f"Source: {escape(source_name)}",
        f"Generated: {datetime.now().strftime('%B %d, %Y').replace(' 0', ' ')}",
    ]
    if duration_text:
        details.append(escape(duration_text))
    details.append(f"{transcription.get('word_count', 0):,} words")

    story = [
        Paragraph(escape(title), title_style),
        Paragraph("LECTURE TRANSCRIPT", meta_style),
        Spacer(1, 4 * mm),
        Paragraph(" &nbsp;·&nbsp; ".join(details), meta_style),
        Paragraph(
            f'<link href="{REPOSITORY_URL}" color="#287C82">github.com/Wilworks/Trim-Audio</link>',
            meta_style,
        ),
        Spacer(1, 4 * mm),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#D7E0E7")),
        Spacer(1, 5 * mm),
    ]

    segments = transcription.get("segments") or []
    if segments:
        for segment in segments:
            timestamp = _format_timestamp(segment.get("start", 0))
            text = escape(str(segment.get("text", "")).strip()).replace("\n", "<br/>")
            if text:
                story.append(
                    Paragraph(
                        f'<font color="#287C82"><b>{timestamp}</b></font>&nbsp;&nbsp;{text}',
                        body_style,
                    )
                )
    else:
        full_text = str(transcription.get("full_text", "")).strip()
        story.append(Paragraph(escape(full_text) if full_text else "[No speech detected]", body_style))

    if lecture_notes:
        notes_heading_style = ParagraphStyle(
            "LectureNotesTitle",
            parent=title_style,
            fontSize=20,
            leading=26,
            spaceAfter=6,
        )
        notes_meta_style = ParagraphStyle(
            "LectureNotesMeta",
            parent=meta_style,
            spaceAfter=8,
        )
        story.extend([
            PageBreak(),
            Paragraph("LECTURE NOTES", notes_heading_style),
            Paragraph(
                f"Comprehensive review notes · Prepared by {escape(author)}"
                + (f" · Generated locally with {escape(notes_model)}" if notes_model else ""),
                notes_meta_style,
            ),
            HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#D7E0E7")),
            Spacer(1, 4 * mm),
            *_lecture_note_story(lecture_notes, regular_font, bold_font),
        ])

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(colors.HexColor("#566575"))
        canvas.drawString(18 * mm, 10 * mm, f"Prepared by {author}")
        page_label = f"{doc.page}"
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, page_label)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=title,
        author=author,
        subject=f"Speech transcript and lecture notes for {source_name}",
    )
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return output_path
