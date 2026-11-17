import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

from trim_audio.cli import DEFAULT_DEVICE, _prompt_timecode, cmd_range, interactive_menu
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
            patch("trim_audio.cli.Prompt.ask", return_value="1") as prompt,
            patch("builtins.input", side_effect=["'lecture.mov'", "", "mps"]),
            patch("trim_audio.cli.cmd_transcribe") as transcribe,
        ):
            interactive_menu()

        args = transcribe.call_args.args[0]
        self.assertIn("q", prompt.call_args.kwargs["choices"])
        self.assertEqual(args.input, "lecture.mov")
        self.assertIsNone(args.output)
        self.assertEqual(args.lecturer, "Dr. Cletus Fiifi Adams")
        self.assertEqual(args.device, "mps")

    def test_blank_interactive_timecode_is_reprompted(self):
        with patch("builtins.input", side_effect=["", "00:00:05"]):
            self.assertEqual(_prompt_timecode("End time: "), "00:00:05")

    def test_blank_range_timecode_does_not_raise_or_trim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "audio.mp3"
            input_path.touch()
            with patch("trim_audio.cli.trim_segment") as trim:
                cmd_range(Namespace(input=input_path, start="00:00:01", end=""))

        trim.assert_not_called()


if __name__ == "__main__":
    unittest.main()
