"""Text preprocessing for TTS.

Raw LLM output contains markdown, HTML, symbols, and abbreviations that TTS
engines mispronounce ("**" read as "asterisk asterisk", "$42" read as "dollar
forty two"). This pipeline cleans text into a spoken-language form before it
reaches the synthesiser.

Pure standard library (re only) — no external dependencies, fully unit-testable
in isolation.
"""

import re

# ── Markdown stripping (order matters: code blocks before inline) ─────────────
_MARKDOWN_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"```.*?```", re.DOTALL), " "),        # fenced code blocks
    (re.compile(r"`([^`]*)`"), r"\1"),                 # inline code
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),     # [text](url) -> text
    (re.compile(r"\*\*([^*]+)\*\*"), r"\1"),           # **bold**
    (re.compile(r"\*([^*]+)\*"), r"\1"),               # *italic*
    (re.compile(r"__([^_]+)__"), r"\1"),               # __bold__
    (re.compile(r"~~([^~]+)~~"), r"\1"),               # ~~strikethrough~~
    (re.compile(r"^#{1,6}\s*", re.MULTILINE), ""),     # # headers
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),   # - bullet points
    (re.compile(r"^\s*>\s?", re.MULTILINE), ""),       # > blockquotes
]

_HTML_TAG = re.compile(r"<[^>]+>")

# ── Abbreviation expansion (only unambiguous ones — "St." is skipped because
#    it means both Street and Saint) ────────────────────────────────────────
_ABBREVIATIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bDr\.", re.IGNORECASE), "Doctor"),
    (re.compile(r"\bMr\."), "Mister"),
    (re.compile(r"\bMrs\."), "Missus"),
    (re.compile(r"\bMs\."), "Miss"),
    (re.compile(r"\bProf\.", re.IGNORECASE), "Professor"),
    (re.compile(r"\bAve\.", re.IGNORECASE), "Avenue"),
    (re.compile(r"\bRd\.", re.IGNORECASE), "Road"),
    (re.compile(r"\bDept\.", re.IGNORECASE), "Department"),
    (re.compile(r"\bappt\.", re.IGNORECASE), "appointment"),
    (re.compile(r"\bapprox\.", re.IGNORECASE), "approximately"),
    (re.compile(r"\betc\.", re.IGNORECASE), "et cetera"),
    (re.compile(r"\bvs\.", re.IGNORECASE), "versus"),
    (re.compile(r"\be\.g\.", re.IGNORECASE), "for example"),
    (re.compile(r"\bi\.e\.", re.IGNORECASE), "that is"),
]

# ── Symbol expansion ─────────────────────────────────────────────────────────
_SYMBOL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)"), r"\1 dollars"),   # $42 -> 42 dollars
    (re.compile(r"(\d[\d,]*(?:\.\d+)?)\s?%"), r"\1 percent"),    # 50% -> 50 percent
    (re.compile(r"#(\d)"), r"number \1"),                       # #5 -> number 5
    (re.compile(r"\s&\s"), " and "),                            # & -> and
    (re.compile(r"\s@\s"), " at "),                             # @ -> at
]

# ── Whitespace / punctuation cleanup ─────────────────────────────────────────
_MISSING_SPACE = re.compile(r"([,.!?;:])([A-Za-z])")   # "hello.World" -> "hello. World"
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.!?;:])")     # "hello ." -> "hello."
_MULTISPACE = re.compile(r"\s+")


def process(text: str) -> str:
    """Clean raw text into a spoken-language form suitable for TTS."""
    if not text or not text.strip():
        return ""

    result = text
    for pattern, repl in _MARKDOWN_PATTERNS:
        result = pattern.sub(repl, result)

    result = _HTML_TAG.sub(" ", result)

    for pattern, repl in _ABBREVIATIONS:
        result = pattern.sub(repl, result)

    for pattern, repl in _SYMBOL_PATTERNS:
        result = pattern.sub(repl, result)

    result = _MISSING_SPACE.sub(r"\1 \2", result)
    result = _SPACE_BEFORE_PUNCT.sub(r"\1", result)
    result = _MULTISPACE.sub(" ", result)

    return result.strip()
