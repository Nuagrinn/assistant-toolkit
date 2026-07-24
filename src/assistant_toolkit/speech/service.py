from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol


log = logging.getLogger(__name__)
OPENAI_MAX_BYTES = 25 * 1024 * 1024


class SpeechToTextError(RuntimeError):
    pass


class SpeechToText(Protocol):
    provider: str
    model: str

    def transcribe(self, path: Path) -> str:
        ...


class DisabledSpeechToText:
    provider = "disabled"
    model = "none"

    def transcribe(self, path: Path) -> str:
        raise SpeechToTextError(
            "Speech-to-text is disabled. Set STT_PROVIDER=whisper_cpp, "
            "STT_PROVIDER=whisper_cli or STT_PROVIDER=openai."
        )


class OpenAISpeechToText:
    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-transcribe",
        language: str = "ru",
        prompt: str = "",
        timeout_seconds: int = 120,
        ffmpeg_bin: str = "ffmpeg",
    ):
        self.api_key = api_key.strip()
        self.model = model.strip() or "gpt-4o-transcribe"
        self.language = language.strip() or "ru"
        self.prompt = prompt.strip()
        self.timeout_seconds = timeout_seconds
        self.ffmpeg_bin = ffmpeg_bin.strip() or "ffmpeg"

    def transcribe(self, path: Path) -> str:
        if not self.api_key:
            raise SpeechToTextError("OPENAI_API_KEY is required for STT_PROVIDER=openai.")
        if path.stat().st_size > OPENAI_MAX_BYTES:
            size_mb = path.stat().st_size // (1024 * 1024)
            raise SpeechToTextError(f"Audio file is {size_mb} MB, above OpenAI's 25 MB limit.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise SpeechToTextError(
                "Package `openai` is not installed. Install assistant-toolkit[openai] "
                "or use a local STT provider."
            ) from exc

        mp3_path = _convert_to_mp3(path, ffmpeg_bin=self.ffmpeg_bin)
        try:
            client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
            with mp3_path.open("rb") as file:
                response = client.audio.transcriptions.create(
                    model=self.model,
                    file=(mp3_path.name, file.read()),
                    language=self.language,
                    prompt=self.prompt or None,
                )
            text = (response.text or "").strip()
        finally:
            _safe_unlink(mp3_path)

        if not text:
            raise SpeechToTextError("Speech-to-text returned an empty transcript.")
        return text


class WhisperCliSpeechToText:
    provider = "whisper_cli"

    def __init__(
        self,
        *,
        whisper_bin: str = "whisper",
        model: str = "small",
        language: str = "ru",
        timeout_seconds: int = 180,
        run_command=subprocess.run,
    ):
        self.whisper_bin = whisper_bin.strip() or "whisper"
        self.model = model.strip()
        self.language = language.strip() or "ru"
        self.timeout_seconds = timeout_seconds
        self.run_command = run_command

    def transcribe(self, path: Path) -> str:
        with tempfile.TemporaryDirectory(prefix="assistant-toolkit-stt-") as tmp:
            output_dir = Path(tmp)
            command = [
                self.whisper_bin,
                str(path),
                "--language",
                self.language,
                "--output_format",
                "txt",
                "--output_dir",
                str(output_dir),
            ]
            if self.model:
                command.extend(["--model", self.model])

            log.info("Whisper CLI STT started model=%s input=%s", self.model or "default", path)
            try:
                completed = self.run_command(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except FileNotFoundError as exc:
                raise SpeechToTextError(f"Whisper CLI executable not found: {self.whisper_bin}.") from exc
            except subprocess.TimeoutExpired as exc:
                raise SpeechToTextError("Local whisper STT timed out.") from exc
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                if stderr:
                    log.warning("Whisper CLI failed: %s", stderr[-1000:])
                raise SpeechToTextError("Local whisper failed to transcribe audio.") from exc

            text = _read_whisper_output(output_dir, fallback=completed.stdout)
            if not text:
                raise SpeechToTextError("Speech-to-text returned an empty transcript.")
            log.info("Whisper CLI STT finished chars=%s", len(text))
            return text


class WhisperCppSpeechToText:
    provider = "whisper_cpp"

    def __init__(
        self,
        *,
        whisper_bin: str,
        model_path: Path,
        language: str = "ru",
        timeout_seconds: int = 180,
        ffmpeg_bin: str = "ffmpeg",
        run_command=subprocess.run,
    ):
        self.whisper_bin = str(whisper_bin).strip()
        self.model_path = Path(model_path)
        self.model = self.model_path.name
        self.language = language.strip() or "ru"
        self.timeout_seconds = timeout_seconds
        self.ffmpeg_bin = ffmpeg_bin.strip() or "ffmpeg"
        self.run_command = run_command

    def transcribe(self, path: Path) -> str:
        if not self.model_path.exists():
            raise SpeechToTextError(f"whisper.cpp model not found: {self.model_path}.")

        with tempfile.TemporaryDirectory(prefix="assistant-toolkit-whisper-cpp-") as tmp:
            work_dir = Path(tmp)
            wav_path = _convert_to_wav(path, output_dir=work_dir, ffmpeg_bin=self.ffmpeg_bin)
            output_base = work_dir / "transcript"
            command = [
                self.whisper_bin,
                "-m",
                str(self.model_path),
                "-f",
                str(wav_path),
                "-l",
                self.language,
                "-otxt",
                "-of",
                str(output_base),
            ]

            log.info("whisper.cpp STT started model=%s input=%s wav=%s", self.model_path, path, wav_path)
            try:
                completed = self.run_command(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except FileNotFoundError as exc:
                raise SpeechToTextError(f"whisper.cpp executable not found: {self.whisper_bin}.") from exc
            except subprocess.TimeoutExpired as exc:
                raise SpeechToTextError("Local whisper.cpp STT timed out.") from exc
            except subprocess.CalledProcessError as exc:
                stderr = (exc.stderr or "").strip()
                if stderr:
                    log.warning("whisper.cpp failed: %s", stderr[-1000:])
                raise SpeechToTextError("whisper.cpp failed to transcribe audio.") from exc

            text = _read_whisper_output(work_dir, fallback=completed.stdout)
            if not text:
                raise SpeechToTextError("Speech-to-text returned an empty transcript.")
            log.info("whisper.cpp STT finished chars=%s", len(text))
            return text


def _convert_to_mp3(src: Path, *, ffmpeg_bin: str) -> Path:
    dst = src.with_suffix(".mp3")
    try:
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise SpeechToTextError("ffmpeg is required to convert audio to mp3.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "ignore") if exc.stderr else ""
        if stderr:
            log.warning("ffmpeg failed: %s", stderr[-1000:])
        raise SpeechToTextError("Failed to convert audio to mp3.") from exc
    return dst


def _convert_to_wav(src: Path, *, output_dir: Path, ffmpeg_bin: str) -> Path:
    dst = output_dir / f"{src.stem}.wav"
    try:
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise SpeechToTextError("ffmpeg is required to prepare audio for whisper.cpp.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", "ignore") if exc.stderr else ""
        if stderr:
            log.warning("ffmpeg failed: %s", stderr[-1000:])
        raise SpeechToTextError("Failed to prepare audio for whisper.cpp.") from exc
    return dst


def _read_whisper_output(output_dir: Path, *, fallback: str) -> str:
    txt_files = sorted(output_dir.glob("*.txt"))
    if txt_files:
        return clean_transcript(txt_files[0].read_text(encoding="utf-8"))
    return clean_transcript(fallback)


def clean_transcript(value: str) -> str:
    return " ".join(value.strip().split())


def _safe_unlink(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass

