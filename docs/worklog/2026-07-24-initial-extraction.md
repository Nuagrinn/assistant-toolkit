# Worklog: initial extraction

Date: 2026-07-24

## Goal

Create a separate reusable package for shared personal Telegram bot
infrastructure before implementing the reminder bot.

Repository: `https://github.com/Nuagrinn/assistant-toolkit.git`

## Extracted from LearnKeeper

- Speech-to-text providers:
  - disabled;
  - OpenAI transcription;
  - whisper CLI;
  - whisper.cpp.
- Claude CLI constraints:
  - paid API env stripping;
  - OAuth token requirement for subscription auth;
  - empty sandbox cwd;
  - disallowed tool list that keeps `StructuredOutput` available.
- Structured Claude JSON helper:
  - command construction;
  - JSON schema call;
  - wrapper/fenced JSON payload extraction;
  - Claude CLI usage metadata parsing.
- SQLite migration/session helper.
- Basic `.env` parsing helpers.
- Telegram HTML formatting helpers.

## Deliberately not extracted

- LearnKeeper quiz/review/topic domain logic.
- LearnKeeper LLM usage storage.
- Telegram keyboards and callback handlers.
- Any reminder-bot domain model.
- Any secrets or deployment credentials.

## Package name

Distribution: `assistant-toolkit`

Import package: `assistant_toolkit`

## Next integration step

After this package is pushed:

1. Update LearnKeeper imports gradually.
2. Keep LearnKeeper tests green after each small replacement.
3. Start reminder-bot using `assistant_toolkit` from day one.

## Validation

- Installed locally with `python -m pip install -e .` using Python 3.12.
- Ran `python -m unittest discover -s tests`: 16 tests passed.
- Ran `python -m compileall -q src tests`: no syntax errors.
