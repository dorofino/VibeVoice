"""Light text normalization for TTS input.

Applied before text is sent to the TTS model. Keep it fast and offline —
no LLM calls. The goal is to avoid obvious model trip-ups:
URLs, emails, hashes, ALL-CAPS acronyms shouted at the listener,
bare number clumps with no separators, common abbreviations, etc.
"""
import re

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_HASH_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
_MULTI_PUNCT_RE = re.compile(r"([!?.,;:])\1+")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "]+",
    flags=re.UNICODE,
)
_MARKDOWN_FENCE_RE = re.compile(r"```[\s\S]*?```")
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Common abbreviations → spoken form.
_ABBREV = {
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "et cetera",
    "vs.": "versus",
    "Mr.": "Mister",
    "Mrs.": "Missus",
    "Ms.": "Miss",
    "Dr.": "Doctor",
    "St.": "Saint",
    "Jr.": "Junior",
    "Sr.": "Senior",
    "approx.": "approximately",
}


def normalize_for_tts(text: str) -> str:
    """Return a TTS-friendly version of text. Conservative — only fixes
    patterns the model is known to stumble on."""
    if not text:
        return text

    # Strip fenced code blocks entirely and inline code to plain.
    text = _MARKDOWN_FENCE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)

    # Markdown links: keep visible label, drop URL.
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)

    # Replace bare URLs and emails with a short spoken placeholder
    # instead of the literal string, which tends to trip the model.
    text = _URL_RE.sub("link", text)
    text = _EMAIL_RE.sub("email address", text)

    # Long hex hashes → spoken placeholder.
    text = _HASH_RE.sub("hash", text)

    # Emoji out.
    text = _EMOJI_RE.sub("", text)

    # Abbreviations.
    for abbr, repl in _ABBREV.items():
        text = text.replace(abbr, repl)

    # Collapse shouting: if a word is ALL CAPS and >3 chars, lowercase
    # everything but the first letter so the model reads it as a word,
    # not an acronym. Skip if it's probably an acronym (<=4 chars).
    def _decap(match: re.Match) -> str:
        w = match.group(0)
        if len(w) <= 4:
            return w
        return w[0] + w[1:].lower()

    text = re.sub(r"\b[A-Z]{4,}\b", _decap, text)

    # Collapse repeated punctuation: "!!!" -> "!", "..." kept but "...." -> "..."
    # Only collapse runs longer than 3 for ellipsis, otherwise to single char.
    def _collapse(match: re.Match) -> str:
        ch = match.group(1)
        if ch == "." and len(match.group(0)) >= 3:
            return "..."
        return ch

    text = _MULTI_PUNCT_RE.sub(_collapse, text)

    # Normalize whitespace.
    text = _WHITESPACE_RE.sub(" ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
