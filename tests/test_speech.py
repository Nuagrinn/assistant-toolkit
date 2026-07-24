from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from assistant_toolkit.speech import (
    DisabledSpeechToText,
    SpeechSettings,
    SpeechToTextError,
    WhisperCliSpeechToText,
    build_speech_to_text,
)
from assistant_toolkit.speech.service import clean_transcript


class SpeechTests(unittest.TestCase):
    def test_disabled_provider_raises(self) -> None:
        with self.assertRaises(SpeechToTextError):
            DisabledSpeechToText().transcribe(Path("voice.oga"))

    def test_factory_selects_disabled(self) -> None:
        stt = build_speech_to_text(SpeechSettings(stt_provider="off"))
        self.assertIsInstance(stt, DisabledSpeechToText)

    def test_clean_transcript(self) -> None:
        self.assertEqual(clean_transcript(" hello\n  world "), "hello world")

    def test_whisper_cli_reads_txt_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "voice.oga"
            audio.write_bytes(b"audio")

            def fake_run_command(command, **kwargs):
                output_dir = Path(command[command.index("--output_dir") + 1])
                (output_dir / "voice.txt").write_text(" привет\nмир ", encoding="utf-8")
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            stt = WhisperCliSpeechToText(run_command=fake_run_command)
            self.assertEqual(stt.transcribe(audio), "привет мир")


if __name__ == "__main__":
    unittest.main()

