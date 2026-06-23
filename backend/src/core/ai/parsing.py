import re

_FENCE_OPEN = re.compile(r"^```(?:json)?\s*", re.IGNORECASE)
_FENCE_CLOSE = re.compile(r"```\s*$")

_DEPRECATED_RE = re.compile(r"`([a-zA-Z_]+)`\s+is\s+deprecated", re.IGNORECASE)


def extract_json(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        s = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", s)).strip()
    first = s.find("{")
    last = s.rfind("}")
    if first != -1 and last != -1 and last > first:
        s = s[first : last + 1]
    return s


def detect_deprecated_param(error_body: str) -> str | None:
    match = _DEPRECATED_RE.search(error_body)
    return match.group(1) if match else None
