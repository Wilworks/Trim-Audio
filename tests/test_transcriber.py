import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from trim_audio.transcriber import transcribe_audio_file


class TranscriberDeviceTests(unittest.TestCase):
    def test_mps_uses_float16_and_transcribes_with_requested_device(self):
        model = Mock()
        model.transcribe.return_value = (
            [SimpleNamespace(start=0.0, end=1.0, text=" Speech from video. ")],
            SimpleNamespace(duration=1.0, language="en"),
        )
        whisper_module = SimpleNamespace(WhisperModel=Mock(return_value=model))

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "lecture.mov"
            audio_path.touch()
            with patch.dict("sys.modules", {"faster_whisper": whisper_module}):
                result = transcribe_audio_file(audio_path, device="mps")

        whisper_module.WhisperModel.assert_called_once_with(
            "tiny.en",
            device="mps",
            compute_type="float16",
        )
        self.assertEqual(result["full_text"], "Speech from video.")

    def test_mps_failure_is_not_silently_retried_on_cpu(self):
        whisper_model = Mock(side_effect=RuntimeError("MPS unavailable"))
        whisper_module = SimpleNamespace(WhisperModel=whisper_model)
        fallback_module = SimpleNamespace(load_model=Mock())

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "lecture.mov"
            audio_path.touch()
            with patch.dict(
                "sys.modules",
                {"faster_whisper": whisper_module, "whisper": fallback_module},
            ):
                with self.assertRaisesRegex(RuntimeError, "MPS unavailable"):
                    transcribe_audio_file(audio_path, device="mps")

        fallback_module.load_model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
