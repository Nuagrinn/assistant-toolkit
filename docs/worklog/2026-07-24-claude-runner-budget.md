# Worklog: Claude runner budget controls

Date: 2026-07-24

## What changed

- `StructuredClaudeRunner` can now use `--system-prompt` instead of
  `--append-system-prompt` via `system_prompt_mode="replace"`.
- `StructuredClaudeRunner` supports `max_budget_usd`, passed to Claude Code CLI
  as `--max-budget-usd`.
- Claude Code JSON wrapper parsing now prefers `structured_output` when present.
- Claude subprocess calls now force `encoding="utf-8"` so Russian prompts are
  not corrupted on Windows.

## Reason

Reminder parsing is a small structured task. It should not inherit the full
default Claude Code system context or run without a per-call budget guard.
