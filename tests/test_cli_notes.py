import tempfile
import unittest
from argparse import Namespace
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

from trim_audio.cli import cmd_build_notes


class BuildNotesCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.input_path = Path(self.temp_dir.name) / "TRANSCRIPT_COMBINED.txt"
        self.input_path.write_text(
            "# MASTER AUDIO TRANSCRIPTION CONSOLIDATED REPORT\n"
            "# Generated on: 2026-11-17 10:00:00\n"
            "# Total audio clips: 1\n\n"
            "========================================================================\n"
            "  TRANSCRIPT: Lecture 4.mov\n"
            "  File: Lecture 4.mov | Duration: 12.0s | Words: 4\n"
            "========================================================================\n\n"
            "Voltage equals current multiplied by resistance.\n",
            encoding="utf-8",
        )
        self.args = Namespace(
            input=self.input_path,
            output=None,
            lecturer="Dr. Cletus Fiifi Adams",
            author="Wilfred Ayine",
            notes_model="qwen3:8b",
        )

    def test_builds_two_part_pdf_from_existing_master_transcript(self):
        with (
            patch(
                "trim_audio.cli.build_lecture_notes",
                return_value="## Ohm's law\n- V equals I times R.",
            ) as build_notes,
            patch("trim_audio.cli.create_transcript_pdf", return_value=Path("notes.pdf")) as create_pdf,
            patch("trim_audio.cli.console.status", return_value=nullcontext()),
        ):
            cmd_build_notes(self.args)

        transcription = build_notes.call_args.args[0]
        self.assertEqual(build_notes.call_args.kwargs["model"], "qwen3:8b")
        self.assertEqual(transcription["filename"], "TRANSCRIPT_COMBINED.txt")
        self.assertIn("## Lecture 4.mov", transcription["full_text"])
        self.assertNotIn("MASTER AUDIO TRANSCRIPTION", transcription["full_text"])
        self.assertEqual(create_pdf.call_args.args[0], transcription)
        self.assertEqual(create_pdf.call_args.kwargs["lecture_notes"], "## Ohm's law\n- V equals I times R.")
        self.assertEqual(create_pdf.call_args.kwargs["author"], "Wilfred Ayine")
        self.assertEqual(create_pdf.call_args.args[1], self.input_path.with_name("TRANSCRIPT_COMBINED_notes.pdf"))

    def test_empty_transcript_does_not_call_local_model(self):
        self.input_path.write_text("", encoding="utf-8")
        with patch("trim_audio.cli.build_lecture_notes") as build_notes:
            cmd_build_notes(self.args)

        build_notes.assert_not_called()


if __name__ == "__main__":
    unittest.main()
