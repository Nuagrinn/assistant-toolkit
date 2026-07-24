from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Tools Claude Code could use to explore the filesystem or run code. We deny them
# so structured calls stay single-shot and predictable. StructuredOutput is not
# listed because --json-schema needs it.
DISALLOWED_AGENT_TOOLS = (
    "Bash,Read,Edit,Write,Glob,Grep,WebFetch,WebSearch,"
    "Task,NotebookEdit,TodoWrite,BashOutput,KillShell"
)

PAID_API_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_BASE_URL",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
)

RunCommand = Callable[..., subprocess.CompletedProcess[str]]
_SANDBOX_CWD: Path | None = None


class ClaudeCliError(RuntimeError):
    pass


class ClaudeCliConfigError(ClaudeCliError):
    pass


class ClaudeCliExecutionError(ClaudeCliError):
    pass


class ClaudeCliPayloadError(ClaudeCliError):
    pass


@dataclass(frozen=True)
class StructuredClaudeResult:
    payload: dict[str, Any]
    stdout: str
    stderr: str
    returncode: int
    duration_seconds: float
    input_chars: int
    output_chars: int
    reported_usage: dict[str, Any]


def sandbox_cwd(prefix: str = "assistant-toolkit-agent-cwd-") -> str:
    """Return a stable empty directory for constrained Claude CLI calls."""
    global _SANDBOX_CWD
    if _SANDBOX_CWD is None or not _SANDBOX_CWD.is_dir():
        _SANDBOX_CWD = Path(tempfile.mkdtemp(prefix=prefix))
    return str(_SANDBOX_CWD)


def safe_claude_env(
    *,
    oauth_token: str = "",
    allow_paid_api: bool = False,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(base_env if base_env is not None else os.environ)
    if not allow_paid_api:
        for name in PAID_API_ENV_VARS:
            env.pop(name, None)
        if not oauth_token:
            raise ClaudeCliConfigError(
                "CLAUDE_CODE_OAUTH_TOKEN is required when allow_paid_api=False"
            )
    if oauth_token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
    return env


class StructuredClaudeRunner:
    """Run Claude CLI once and parse a JSON-schema response payload."""

    def __init__(
        self,
        *,
        claude_bin: str = "claude",
        oauth_token: str = "",
        model: str = "",
        timeout_seconds: int = 120,
        allow_paid_api: bool = False,
        max_budget_usd: float = 0,
        system_prompt_mode: str = "append",
        cwd: str | Path | None = None,
        disallowed_tools: str = DISALLOWED_AGENT_TOOLS,
        run_command: RunCommand | None = None,
    ):
        self.claude_bin = claude_bin
        self.oauth_token = oauth_token
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.allow_paid_api = allow_paid_api
        self.max_budget_usd = max(0, float(max_budget_usd or 0))
        self.system_prompt_mode = system_prompt_mode.strip().lower() or "append"
        self.cwd = Path(cwd) if cwd else None
        self.disallowed_tools = disallowed_tools
        self.run_command = run_command or subprocess.run

    def run(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
        expected_keys: tuple[str, ...] = (),
    ) -> StructuredClaudeResult:
        cmd = [
            self.claude_bin,
            "--print",
            "--system-prompt" if self.system_prompt_mode in {"replace", "system"} else "--append-system-prompt",
            system_prompt,
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(json_schema, ensure_ascii=False),
            "--no-session-persistence",
            "--disallowedTools",
            self.disallowed_tools,
        ]
        if self.model:
            cmd.extend(["--model", self.model])
        if self.max_budget_usd > 0:
            cmd.extend(["--max-budget-usd", f"{self.max_budget_usd:g}"])

        started = time.perf_counter()
        input_chars = len(system_prompt) + len(user_prompt)
        try:
            proc = self.run_command(
                cmd,
                input=user_prompt,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=self.timeout_seconds,
                cwd=str(self.cwd) if self.cwd else sandbox_cwd(),
                env=safe_claude_env(
                    oauth_token=self.oauth_token,
                    allow_paid_api=self.allow_paid_api,
                ),
            )
        except FileNotFoundError as exc:
            raise ClaudeCliExecutionError(f"Claude CLI not found: {self.claude_bin}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ClaudeCliExecutionError(
                f"Claude CLI timed out after {self.timeout_seconds} seconds: "
                f"{output_preview(timeout_output(exc))}"
            ) from exc

        duration = time.perf_counter() - started
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        reported_usage = reported_usage_from_stdout(stdout)

        if proc.returncode != 0:
            detail = output_preview(stderr or stdout)
            raise ClaudeCliExecutionError(
                "Claude CLI failed"
                + (f" with returncode {proc.returncode}" if proc.returncode is not None else "")
                + (f": {detail}" if detail else "")
            )

        payload = extract_json_payload(stdout, expected_keys=expected_keys)
        return StructuredClaudeResult(
            payload=payload,
            stdout=stdout,
            stderr=stderr,
            returncode=proc.returncode,
            duration_seconds=duration,
            input_chars=input_chars,
            output_chars=len(stdout),
            reported_usage=reported_usage,
        )


def extract_json_payload(stdout: str, *, expected_keys: tuple[str, ...] = ()) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        raise ClaudeCliPayloadError("Claude CLI returned empty output")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raw = json.loads(json_object_slice(text))
    return coerce_json_payload(raw, expected_keys=expected_keys)


def coerce_json_payload(value: Any, *, expected_keys: tuple[str, ...] = ()) -> dict[str, Any]:
    if isinstance(value, dict):
        for key in ("structured_output",):
            nested = value.get(key)
            if isinstance(nested, dict):
                return coerce_json_payload(nested, expected_keys=expected_keys)
    if isinstance(value, dict) and _matches_expected(value, expected_keys):
        return value
    if isinstance(value, dict):
        for key in ("result", "content", "message", "text"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                raise_if_denied_structured_output(nested)
                return extract_json_payload(nested, expected_keys=expected_keys)
            if isinstance(nested, dict):
                return coerce_json_payload(nested, expected_keys=expected_keys)
            if isinstance(nested, list):
                joined = "\n".join(
                    str(item.get("text") or "")
                    for item in nested
                    if isinstance(item, dict)
                ).strip()
                if joined:
                    return extract_json_payload(joined, expected_keys=expected_keys)
    if isinstance(value, dict) and not expected_keys:
        return value
    raise ClaudeCliPayloadError(
        "Claude CLI JSON output does not contain expected payload"
        + (f": {', '.join(expected_keys)}" if expected_keys else "")
    )


def _matches_expected(payload: dict[str, Any], expected_keys: tuple[str, ...]) -> bool:
    return all(key in payload for key in expected_keys) if expected_keys else True


def raise_if_denied_structured_output(text: str) -> None:
    normalized = text.lower()
    if "structuredoutput" in normalized and (
        "denied" in normalized or "plan mode" in normalized or "permission" in normalized
    ):
        raise ClaudeCliPayloadError(
            "Claude CLI could not return structured JSON because StructuredOutput was denied"
        )


def reported_usage_from_stdout(stdout: str | None) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(raw, dict):
        return {}

    usage = raw.get("usage")
    if not isinstance(usage, dict):
        usage = {}
    direct_input_tokens = optional_int(usage.get("input_tokens")) or 0
    cache_creation_tokens = optional_int(usage.get("cache_creation_input_tokens")) or 0
    cache_read_tokens = optional_int(usage.get("cache_read_input_tokens")) or 0
    output_tokens = optional_int(usage.get("output_tokens")) or 0
    input_tokens = direct_input_tokens + cache_creation_tokens + cache_read_tokens
    total_tokens = input_tokens + output_tokens
    total_cost_usd = optional_float(raw.get("total_cost_usd"))

    if total_tokens <= 0 and total_cost_usd is None:
        return {}

    metadata = {
        "claude_total_cost_usd": total_cost_usd,
        "claude_input_tokens": direct_input_tokens,
        "claude_cache_creation_input_tokens": cache_creation_tokens,
        "claude_cache_read_input_tokens": cache_read_tokens,
        "claude_output_tokens": output_tokens,
        "claude_duration_ms": optional_int(raw.get("duration_ms")),
        "claude_duration_api_ms": optional_int(raw.get("duration_api_ms")),
        "claude_service_tier": usage.get("service_tier") if usage else None,
    }
    return {
        "usage_source": "claude_cli_reported",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_usd": total_cost_usd,
        "metadata": {key: value for key, value in metadata.items() if value is not None},
    }


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(0, float(value))
    except (TypeError, ValueError):
        return None


def json_object_slice(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?", "", clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r"```$", "", clean).strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ClaudeCliPayloadError("Could not find JSON object in Claude CLI output")
    return clean[start : end + 1]


def timeout_output(exc: subprocess.TimeoutExpired) -> str:
    parts: list[str] = []
    for value in (exc.stdout, exc.stderr):
        if isinstance(value, bytes):
            parts.append(value.decode(errors="ignore"))
        elif value:
            parts.append(str(value))
    return "".join(parts)


def output_preview(value: str | None, *, limit: int = 800) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
