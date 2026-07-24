from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from assistant_toolkit.speech.service import (
    DisabledSpeechToText,
    OpenAISpeechToText,
    SpeechToText,
    WhisperCliSpeechToText,
    WhisperCppSpeechToText,
)


@dataclass(frozen=True)
class SpeechSettings:
    stt_provider: str = "disabled"
    openai_api_key: str = ""
    stt_openai_model: str = "gpt-4o-transcribe"
    stt_language: str = "ru"
    stt_prompt: str = ""
    stt_timeout_seconds: int = 180
    stt_whisper_bin: str = "whisper"
    stt_whisper_model: str = "small"
    stt_whisper_cpp_bin: str = "whisper-cli"
    stt_whisper_cpp_model: Path = Path("ggml-base.bin")
    ffmpeg_bin: str = "ffmpeg"


def build_speech_to_text(settings: SpeechSettings | Any) -> SpeechToText:
    provider = str(getattr(settings, "stt_provider", "disabled") or "disabled").strip().lower()
    if provider in ("", "disabled", "none", "off"):
        return DisabledSpeechToText()
    if provider == "openai":
        return OpenAISpeechToText(
            api_key=str(getattr(settings, "openai_api_key", "")),
            model=str(getattr(settings, "stt_openai_model", "gpt-4o-transcribe")),
            language=str(getattr(settings, "stt_language", "ru")),
            prompt=str(getattr(settings, "stt_prompt", "")),
            timeout_seconds=int(getattr(settings, "stt_timeout_seconds", 180)),
            ffmpeg_bin=str(getattr(settings, "ffmpeg_bin", "ffmpeg")),
        )
    if provider == "whisper_cli":
        return WhisperCliSpeechToText(
            whisper_bin=str(getattr(settings, "stt_whisper_bin", "whisper")),
            model=str(getattr(settings, "stt_whisper_model", "small")),
            language=str(getattr(settings, "stt_language", "ru")),
            timeout_seconds=int(getattr(settings, "stt_timeout_seconds", 180)),
        )
    if provider == "whisper_cpp":
        return WhisperCppSpeechToText(
            whisper_bin=str(getattr(settings, "stt_whisper_cpp_bin", "whisper-cli")),
            model_path=Path(getattr(settings, "stt_whisper_cpp_model", Path("ggml-base.bin"))),
            language=str(getattr(settings, "stt_language", "ru")),
            timeout_seconds=int(getattr(settings, "stt_timeout_seconds", 180)),
            ffmpeg_bin=str(getattr(settings, "ffmpeg_bin", "ffmpeg")),
        )
    raise RuntimeError(f"Unsupported STT_PROVIDER: {provider}")

