from __future__ import annotations

import json
import subprocess
import unittest

from assistant_toolkit.llm import (
    ClaudeCliConfigError,
    StructuredClaudeRunner,
    extract_json_payload,
    reported_usage_from_stdout,
    safe_claude_env,
)


class ClaudeCliTests(unittest.TestCase):
    def test_safe_env_removes_paid_api_vars(self) -> None:
        env = safe_claude_env(
            oauth_token="token",
            allow_paid_api=False,
            base_env={"ANTHROPIC_API_KEY": "paid", "PATH": "x"},
        )

        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual(env["CLAUDE_CODE_OAUTH_TOKEN"], "token")
        self.assertEqual(env["PATH"], "x")

    def test_safe_env_requires_oauth_when_paid_api_disabled(self) -> None:
        with self.assertRaises(ClaudeCliConfigError):
            safe_claude_env(oauth_token="", allow_paid_api=False, base_env={})

    def test_extract_payload_from_wrappers(self) -> None:
        direct = extract_json_payload('{"ok": true}', expected_keys=("ok",))
        wrapped = extract_json_payload(
            json.dumps({"result": json.dumps({"ok": True})}),
            expected_keys=("ok",),
        )
        structured_output = extract_json_payload(
            json.dumps({"structured_output": {"ok": True}, "result": ""}),
            expected_keys=("ok",),
        )
        fenced = extract_json_payload("```json\n{\"ok\": true}\n```", expected_keys=("ok",))

        self.assertEqual(direct["ok"], True)
        self.assertEqual(wrapped["ok"], True)
        self.assertEqual(structured_output["ok"], True)
        self.assertEqual(fenced["ok"], True)

    def test_reported_usage(self) -> None:
        usage = reported_usage_from_stdout(
            json.dumps(
                {
                    "usage": {
                        "input_tokens": 10,
                        "cache_creation_input_tokens": 5,
                        "cache_read_input_tokens": 3,
                        "output_tokens": 7,
                    },
                    "total_cost_usd": 0.01,
                    "duration_ms": 100,
                }
            )
        )

        self.assertEqual(usage["input_tokens"], 18)
        self.assertEqual(usage["output_tokens"], 7)
        self.assertEqual(usage["total_tokens"], 25)
        self.assertEqual(usage["estimated_usd"], 0.01)

    def test_structured_runner_builds_command_and_parses_payload(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_run_command(*args, **kwargs):
            calls.append({"cmd": args[0], **kwargs})
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=json.dumps({"result": json.dumps({"ok": True})}),
                stderr="",
            )

        runner = StructuredClaudeRunner(
            claude_bin="claude",
            oauth_token="token",
            timeout_seconds=5,
            run_command=fake_run_command,
        )
        result = runner.run(
            system_prompt="system",
            user_prompt="user",
            json_schema={"type": "object"},
            expected_keys=("ok",),
        )

        self.assertEqual(result.payload, {"ok": True})
        self.assertEqual(result.input_chars, len("systemuser"))
        self.assertEqual(len(calls), 1)
        self.assertIn("--json-schema", calls[0]["cmd"])
        self.assertEqual(calls[0]["input"], "user")
        self.assertEqual(calls[0]["encoding"], "utf-8")
        self.assertEqual(calls[0]["env"]["CLAUDE_CODE_OAUTH_TOKEN"], "token")

    def test_structured_runner_can_replace_system_prompt_and_limit_budget(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_run_command(*args, **kwargs):
            calls.append({"cmd": args[0], **kwargs})
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=json.dumps({"structured_output": {"ok": True}}),
                stderr="",
            )

        runner = StructuredClaudeRunner(
            claude_bin="claude",
            oauth_token="token",
            max_budget_usd=0.05,
            system_prompt_mode="replace",
            run_command=fake_run_command,
        )
        result = runner.run(
            system_prompt="system",
            user_prompt="user",
            json_schema={"type": "object"},
            expected_keys=("ok",),
        )

        cmd = calls[0]["cmd"]
        self.assertEqual(result.payload, {"ok": True})
        self.assertIn("--system-prompt", cmd)
        self.assertNotIn("--append-system-prompt", cmd)
        self.assertIn("--max-budget-usd", cmd)


if __name__ == "__main__":
    unittest.main()
