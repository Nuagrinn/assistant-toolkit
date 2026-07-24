# Modules

Date: 2026-07-24

## `assistant_toolkit.speech`

Extracted from LearnKeeper's `app/features/speech`.

Provides:

- `SpeechToText` protocol;
- `DisabledSpeechToText`;
- `OpenAISpeechToText`;
- `WhisperCliSpeechToText`;
- `WhisperCppSpeechToText`;
- `SpeechSettings`;
- `build_speech_to_text`.

The factory accepts either `SpeechSettings` or any object with matching
attributes. This keeps existing bots free to keep their own settings dataclass.

## `assistant_toolkit.llm`

Extracted and generalized from LearnKeeper Claude agents.

Provides:

- paid Anthropic API env stripping;
- `CLAUDE_CODE_OAUTH_TOKEN` enforcement when `allow_paid_api=False`;
- stable empty sandbox cwd;
- `DISALLOWED_AGENT_TOOLS`;
- `StructuredClaudeRunner` for `--json-schema` calls;
- payload unwrapping from direct JSON, Claude wrapper JSON, content arrays and
  fenced JSON;
- Claude CLI usage extraction.

Bots should keep prompts and payload-specific validation in their own code.

## `assistant_toolkit.config`

Small `.env` and primitive parsing helpers:

- `load_env_file`;
- `resolve_path`;
- `parse_bool`;
- `parse_int`;
- `parse_float`;
- `parse_hhmm`.

This is intentionally not a full settings framework.

## `assistant_toolkit.db`

SQLite helper copied from the working LearnKeeper shape, but with configurable
migration directory:

- `Database.connect`;
- `Database.session`;
- `Database.migrate`;
- `Database.applied_migrations`.

Each bot owns its own migrations and schema.

## `assistant_toolkit.telegram`

Formatting helpers that do not depend on `python-telegram-bot`:

- `h`;
- `rich`;
- `rich_inline`;
- `split_message`.

Concrete keyboards, callback data and texts stay in each bot.

