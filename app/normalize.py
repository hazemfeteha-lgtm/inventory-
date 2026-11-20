"""Arabic text normalization helpers used by search and importing."""
from __future__ import annotations

import re
import unicodedata

# Unify Arabic letter variants so that "أ/إ/آ" and "ة/ه" compare equal.
_LETTER_MAP = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ؤ": "و",
        "ئ": "ي",
        "ة": "ه",
        "ى": "ي",
        "ـ": "",  # tatweel
    }
)
_MARKS = re.compile(r"[\u064b-\u0652\u0670\u0640]")  # harakat + tatweel


def norm(value: object) -> str:
    """Normalize text for display-independent comparison / searching."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = _MARKS.sub("", text).translate(_LETTER_MAP)
    return re.sub(r"\s+", " ", text).strip().lower()


def norm_key(value: object) -> str:
    """Compact normalized key: only alphanumeric characters remain."""
    return "".join(ch for ch in norm(value) if ch.isalnum())


def numeric(value: object, default: int = 1) -> int:
    """Read the first integer in a value, returning default when absent."""
    if value is None:
        return default
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else default


def clean_serial(value: object) -> str:
    """Return a trimmed serial/identifier string, or '' for blank cells."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"none", "nan", "-"} else text
