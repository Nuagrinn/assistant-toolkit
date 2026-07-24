from __future__ import annotations

from pathlib import Path


def load_env_file(path: Path) -> dict[str, str]:
    """Load a simple KEY=VALUE env file without overriding process env."""
    path = Path(path)
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_path(value: str | Path | None, *, default: Path, base_dir: Path | None = None) -> Path:
    """Resolve a possibly relative path against base_dir.

    Empty values return default. If base_dir is omitted, relative values are
    resolved against the current process working directory by pathlib.
    """
    if value is None or str(value).strip() == "":
        return Path(default)
    path = Path(value)
    if not path.is_absolute() and base_dir is not None:
        path = Path(base_dir) / path
    return path


def parse_bool(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if not text:
        return default
    if text in ("1", "true", "yes", "on", "y"):
        return True
    if text in ("0", "false", "no", "off", "n"):
        return False
    return default


def parse_int(
    value: object,
    *,
    default: int = 0,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    try:
        parsed = int(float(str(value).strip().replace(",", "").replace("_", "")))
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None:
        parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed


def parse_float(
    value: object,
    *,
    default: float = 0.0,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    try:
        parsed = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        parsed = default
    if min_value is not None:
        parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed


def parse_hhmm(value: object, *, default: tuple[int, int]) -> tuple[int, int]:
    try:
        raw_hour, raw_minute = str(value).strip().split(":", 1)
        hour = int(raw_hour)
        minute = int(raw_minute)
    except (ValueError, TypeError):
        return default
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return default
    return hour, minute

