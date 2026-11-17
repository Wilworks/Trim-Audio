import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trim_audio.cli import DEFAULT_DEVICE, interactive_menu
from trim_audio.pdf_export import create_transcript_pdf


class TranscriptPdfTests(unittest.TestCase):
    def test_creates_pdf_with_video_title_and_lecturer_metadata(self):
        transcription = {
            "filename": "Bioelectronics Lecture 4.mov",
            "duration": 83.0,
            "word_count": 4,
            "segments": [{"start": 2.5, "text": "Welcome to the lecture."}],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = create_transcript_pdf(
                transcription,
                Path(temp_dir) / "lecture.pdf",
            )
            pdf_data = output_path.read_bytes()

        self.assertTrue(pdf_data.startswith(b"%PDF-"))
        self.assertIn(b"/Title (Bioelectronics Lecture 4)", pdf_data)
        self.assertIn(b"/Author (Dr. Cletus Fiifi Adams)", pdf_data)

    def test_interactive_menu_offers_transcription(self):
        with (
            patch("builtins.input", side_effect=["1", "'lecture.mov'", "", "mps"]),
            patch("trim_audio.cli.cmd_transcribe") as transcribe,
        ):
            interactive_menu()

        args = transcribe.call_args.args[0]
        self.assertEqual(args.input, "lecture.mov")
        self.assertIsNone(args.output)
        self.assertEqual(args.lecturer, "Dr. Cletus Fiifi Adams")
        self.assertEqual(args.device, "mps")


if __name__ == "__main__":
    unittest.main()
