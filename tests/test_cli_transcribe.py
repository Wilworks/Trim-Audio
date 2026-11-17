import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

from trim_audio.cli import cmd_transcribe
from trim_audio.notes_builder import DEFAULT_NOTES_MODEL
from trim_audio.pdf_export import DEFAULT_AUTHOR


class TranscribeCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.input_path = Path(self.temp_dir.name) / "lecture.mov"
        self.input_path.touch()
        self.transcription = {"word_count": 1, "segments": []}
        self.args = Namespace(
            input=self.input_path,
            output=None,
            lecturer="Dr. Cletus Fiifi Adams",
            model="tiny.en",
            device="cpu",
            notes_model=DEFAULT_NOTES_MODEL,
            build_notes=True,
        )

    def test_builds_local_notes_before_creating_pdf(self):
        with (
            patch("trim_audio.cli.transcribe_audio_file", return_value=self.transcription),
            patch("trim_audio.cli.build_lecture_notes", return_value="## Lecture notes") as build_notes,
            patch("trim_audio.cli.create_transcript_pdf", return_value=Path("lecture.pdf")) as create_pdf,
            patch("trim_audio.cli.console.status", return_value=nullcontext()),
        ):
            cmd_transcribe(self.args)

        build_notes.assert_called_once()
        self.assertEqual(build_notes.call_args.args[0], self.transcription)
        self.assertEqual(build_notes.call_args.kwargs["model"], DEFAULT_NOTES_MODEL)
        self.assertTrue(callable(build_notes.call_args.kwargs["progress_callback"]))
        self.assertEqual(create_pdf.call_args.kwargs["author"], DEFAULT_AUTHOR)
        self.assertEqual(create_pdf.call_args.kwargs["lecture_notes"], "## Lecture notes")
        self.assertEqual(create_pdf.call_args.kwargs["notes_model"], DEFAULT_NOTES_MODEL)

    def test_no_notes_option_skips_local_model(self):
        self.args.build_notes = False
        with (
            patch("trim_audio.cli.transcribe_audio_file", return_value=self.transcription),
            patch("trim_audio.cli.build_lecture_notes") as build_notes,
            patch("trim_audio.cli.create_transcript_pdf", return_value=Path("lecture.pdf")) as create_pdf,
        ):
            cmd_transcribe(self.args)

        build_notes.assert_not_called()
        self.assertIsNone(create_pdf.call_args.kwargs["lecture_notes"])
        self.assertIsNone(create_pdf.call_args.kwargs["notes_model"])

    def test_local_model_failure_does_not_create_pdf(self):
        with (
            patch("trim_audio.cli.transcribe_audio_file", return_value=self.transcription),
            patch("trim_audio.cli.build_lecture_notes", side_effect=RuntimeError("model unavailable")),
            patch("trim_audio.cli.create_transcript_pdf") as create_pdf,
            patch("trim_audio.cli.console.status", return_value=nullcontext()),
        ):
            cmd_transcribe(self.args)

        create_pdf.assert_not_called()

    def test_directory_input_is_rejected_before_transcription(self):
        input_directory = Path(self.temp_dir.name) / "media-folder"
        input_directory.mkdir()
        self.args.input = input_directory
        with patch("trim_audio.cli.transcribe_audio_file") as transcribe:
            cmd_transcribe(self.args)

        transcribe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
