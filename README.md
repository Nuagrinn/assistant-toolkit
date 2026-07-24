# Assistant Toolkit

Shared Python helpers for personal assistant Telegram bots.

The first version extracts infrastructure that already worked in LearnKeeper:

- speech-to-text providers for Telegram voice messages;
- safe Claude CLI structured JSON calls;
- small `.env` parsing helpers;
- SQLite migration/session helper;
- Telegram HTML formatting helpers.

Domain logic stays outside this package. LearnKeeper topics/quizzes and reminder
events should live in their own bots.

## Install locally

```powershell
python -m pip install -e .
```

Or from another project:

```text
assistant-toolkit @ git+https://github.com/Nuagrinn/assistant-toolkit.git
```

## Modules

| Module | Purpose |
|---|---|
| `assistant_toolkit.speech` | OpenAI / whisper CLI / whisper.cpp STT adapters |
| `assistant_toolkit.llm` | Claude CLI safe env, sandbox cwd and JSON-schema runner |
| `assistant_toolkit.config` | `.env`, bool/int/float/path/time helpers |
| `assistant_toolkit.db` | SQLite connection, transactions and SQL migrations |
| `assistant_toolkit.telegram` | HTML escaping, Markdown-lite rendering, message splitting |

## Safety defaults

`assistant_toolkit.llm.safe_claude_env()` removes paid Anthropic API environment
variables unless `allow_paid_api=True`. With the default `allow_paid_api=False`,
`CLAUDE_CODE_OAUTH_TOKEN` is required so Claude Code uses subscription auth.

The structured Claude runner uses an empty sandbox cwd by default and disables
file/shell/web tools while keeping `StructuredOutput` available for
`--json-schema`.

## Development

```powershell
python -m unittest discover -s tests
```

## Documentation

- [docs/modules.md](docs/modules.md)
- [docs/worklog/2026-07-24-initial-extraction.md](docs/worklog/2026-07-24-initial-extraction.md)

