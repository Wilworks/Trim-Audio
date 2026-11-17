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
                lecture_notes=(
                    "## Core concepts\n"
                    "- Ohm's law: **V = I × R** (& measured in ohms).\n\n"
                    "### Equation\n$$\nV = I \\times R\n$$"
                ),
                notes_model="qwen3:8b",
            )
            pdf_data = output_path.read_bytes()

        self.assertTrue(pdf_data.startswith(b"%PDF-"))
        self.assertIn(b"/Title (Bioelectronics Lecture 4)", pdf_data)
        self.assertIn(b"/Author (Wilfred Ayine)", pdf_data)
        self.assertIn(b"/Count 2", pdf_data)

    def test_interactive_menu_offers_transcription(self):
        with (
            patch("trim_audio.cli.select") as menu,
            patch(
                "builtins.input",
                side_effect=["'lecture.mov'", "", "mps", "Dr. Jane Doe", "", "", ""],
            ),
            patch("trim_audio.cli.Path.is_file", return_value=True),
            patch("trim_audio.cli.cmd_transcribe") as transcribe,
        ):
            menu.return_value.ask.return_value = "transcribe"
            interactive_menu()

        args = transcribe.call_args.args[0]
        self.assertEqual(menu.call_args.kwargs["choices"][0].value, "transcribe")
        self.assertEqual(args.input, "lecture.mov")
        self.assertIsNone(args.output)
        self.assertEqual(args.lecturer, "Dr. Jane Doe")
        self.assertEqual(args.author, "Wilfred Ayine")
        self.assertEqual(args.device, "mps")
        self.assertEqual(args.notes_model, "qwen3:8b")
        self.assertTrue(args.build_notes)

    def test_interactive_menu_offers_existing_transcript_notes(self):
        with (
            patch("trim_audio.cli.select") as menu,
            patch("builtins.input", side_effect=["lecture.txt", "", "", "", "", ""]),
            patch("trim_audio.cli.cmd_build_notes") as build_notes,
        ):
            menu.return_value.ask.return_value = "notes"
            interactive_menu()

        self.assertIn("notes", [choice.value for choice in menu.call_args.kwargs["choices"]])
        args = build_notes.call_args.args[0]
        self.assertEqual(args.input, "lecture.txt")
        self.assertEqual(args.notes_model, "qwen3:8b")

    def test_interactive_transcription_can_skip_notes(self):
        with (
            patch("trim_audio.cli.select") as menu,
            patch("builtins.input", side_effect=["lecture.mov", "", "cpu", "", "", "n"]),
            patch("trim_audio.cli.Path.is_file", return_value=True),
            patch("trim_audio.cli.cmd_transcribe") as transcribe,
        ):
            menu.return_value.ask.return_value = "transcribe"
            interactive_menu()

        args = transcribe.call_args.args[0]
        self.assertFalse(args.build_notes)

    def test_interactive_menu_handles_ctrl_c_during_prompt(self):
        with (
            patch("trim_audio.cli.select") as menu,
            patch("builtins.input", side_effect=KeyboardInterrupt),
            patch("trim_audio.cli.cmd_transcribe") as transcribe,
        ):
            menu.return_value.ask.return_value = "transcribe"
            interactive_menu()

        transcribe.assert_not_called()

    def test_interactive_transcription_rejects_directory_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("trim_audio.cli.select") as menu,
                patch("builtins.input", side_effect=[temp_dir]),
                patch("trim_audio.cli.cmd_transcribe") as transcribe,
            ):
                menu.return_value.ask.return_value = "transcribe"
                interactive_menu()

        transcribe.assert_not_called()

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
