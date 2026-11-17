"""Clean, searchable PDF export for speech transcripts."""

from datetime import datetime
from html import escape
from pathlib import Path

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

REPOSITORY_URL = "https://github.com/Wilworks/Trim-Audio"
DEFAULT_LECTURER = "Dr. Cletus Fiifi Adams"


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


def create_transcript_pdf(
    transcription: dict,
    output_path: str | Path,
    lecturer: str = DEFAULT_LECTURER,
) -> Path:
    """Write a searchable transcript PDF with source and lecturer details."""
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

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(colors.HexColor("#566575"))
        canvas.drawString(18 * mm, 10 * mm, "Automatically generated transcript")
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
        author=lecturer,
        subject=f"Speech transcript of {source_name}",
    )
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return output_path
