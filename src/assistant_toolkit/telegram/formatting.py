from __future__ import annotations

import html
import re


MAX_MESSAGE_LEN = 3900


def h(value: object) -> str:
    return html.escape(str(value), quote=False)


_CODE_FENCE_RE = re.compile(r"```[ \t]*([A-Za-z0-9_+#.-]*)[ \t]*\r?\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_MARKDOWN_HEADING_RE = re.compile(r"^([ \t]{0,3})#{1,6}[ \t]+(.+?)\s*$")
_MARKDOWN_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*|__([^_\n]+)__")
_MARKDOWN_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)|(?<!_)_([^_\n]+)_(?!_)")


def rich(value: object) -> str:
    """Render common LLM Markdown into Telegram HTML."""
    text = str(value)
    if not text:
        return ""
    parts: list[str] = []
    idx = 0
    for match in _CODE_FENCE_RE.finditer(text):
        parts.append(rich_inline(text[idx : match.start()]))
        lang = match.group(1).strip().lower()
        code = h(match.group(2).rstrip("\n"))
        if lang:
            parts.append(f'<pre><code class="language-{h(lang)}">{code}</code></pre>')
        else:
            parts.append(f"<pre>{code}</pre>")
        idx = match.end()
    parts.append(rich_inline(text[idx:]))
    return "".join(parts)


def rich_inline(segment: str) -> str:
    parts: list[str] = []
    idx = 0
    for match in _INLINE_CODE_RE.finditer(segment):
        parts.append(_rich_plain(segment[idx : match.start()]))
        parts.append(f"<code>{h(match.group(1))}</code>")
        idx = match.end()
    parts.append(_rich_plain(segment[idx:]))
    return "".join(parts)


def _rich_plain(segment: str) -> str:
    lines: list[str] = []
    for chunk in segment.splitlines(keepends=True):
        body = chunk
        newline = ""
        if chunk.endswith("\r\n"):
            body = chunk[:-2]
            newline = "\r\n"
        elif chunk.endswith("\n"):
            body = chunk[:-1]
            newline = "\n"
        elif chunk.endswith("\r"):
            body = chunk[:-1]
            newline = "\r"

        heading = _MARKDOWN_HEADING_RE.match(body)
        if heading:
            text = re.sub(r"[ \t]+#+[ \t]*$", "", heading.group(2)).strip()
            lines.append(f"{h(heading.group(1))}<b>{_rich_markdown_inline(text)}</b>{newline}")
            continue

        lines.append(_rich_markdown_inline(body) + newline)
    return "".join(lines)


def _rich_markdown_inline(text: str) -> str:
    rendered = h(text)
    rendered = _MARKDOWN_BOLD_RE.sub(lambda match: f"<b>{match.group(1) or match.group(2)}</b>", rendered)
    rendered = _MARKDOWN_ITALIC_RE.sub(lambda match: f"<i>{match.group(1) or match.group(2)}</i>", rendered)
    return rendered


def split_message(text: str, *, limit: int = MAX_MESSAGE_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in text.splitlines():
        projected = current_len + len(line) + 1
        if current and projected > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line) + 1
        else:
            current.append(line)
            current_len = projected
    if current:
        chunks.append("\n".join(current))
    return chunks

