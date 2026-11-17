import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from trim_audio.notes_builder import OLLAMA_CHAT_URL, build_lecture_notes


class LectureNotesBuilderTests(unittest.TestCase):
    def test_sends_timestamped_transcript_to_local_ollama(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({
            "message": {"content": "## Core concept\n- A clear explanation."}
        }).encode("utf-8")

        transcription = {
            "segments": [
                {"start": 62.4, "end": 75.0, "text": "The lecturer defines bioelectronics."},
            ],
        }
        with patch("trim_audio.notes_builder.urlopen", return_value=response) as urlopen:
            notes = build_lecture_notes(transcription, model="qwen3:8b")

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, OLLAMA_CHAT_URL)
        self.assertEqual(payload["model"], "qwen3:8b")
        self.assertIn("[00:01:02]", payload["messages"][1]["content"])
        self.assertIn("Core concept", notes)

    def test_reports_when_local_ollama_is_unavailable(self):
        with patch(
            "trim_audio.notes_builder.urlopen",
            side_effect=URLError("connection refused"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Cannot reach local Ollama"):
                build_lecture_notes({
                    "segments": [{"start": 0.0, "end": 2.0, "text": "A test lecture."}],
                })


if __name__ == "__main__":
    unittest.main()
