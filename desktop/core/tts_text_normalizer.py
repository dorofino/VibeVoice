"""Light text normalization for TTS input.

Applied before text is sent to the TTS model. Keep it fast and offline —
no LLM calls. The goal is to avoid obvious model trip-ups:
URLs, emails, hashes, ALL-CAPS acronyms shouted at the listener,
bare number clumps with no separators, common abbreviations, special
unicode (em-dash, smart quotes, bullets), and shell command syntax.
"""
import re
import unicodedata

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

# Shell long flag like --cached, --no-verify -> spoken word(s).
_SHELL_FLAG_RE = re.compile(r"(?<![\w-])--([a-zA-Z][a-zA-Z0-9-]*)")
# Shell short flag like -rf, -n.
_SHELL_SHORT_FLAG_RE = re.compile(r"(?<![\w-])-([a-zA-Z]{1,3})\b")
# File path-ish tokens (slashes, dots between words) → drop, the audio
# version is rarely useful.
_PATH_RE = re.compile(r"(?:[/\\][\w.-]+){2,}")

# Direct unicode-character substitutions. Anything the model handles
# poorly gets mapped to its closest ASCII equivalent. Em/en-dashes
# become a comma so the prosody includes a natural pause.
_CHAR_MAP = {
    # Dashes
    "\u2014": ", ",   # — em-dash
    "\u2013": ", ",   # – en-dash
    "\u2212": "-",    # − minus sign
    "\u2010": "-",    # ‐ hyphen
    "\u2011": "-",    # ‑ non-breaking hyphen
    # Smart quotes
    "\u201c": '"', "\u201d": '"',
    "\u2018": "'",  "\u2019": "'",
    "\u201a": ",",  "\u201e": '"',
    "\u00ab": '"',  "\u00bb": '"',
    # Ellipsis
    "\u2026": "...",
    # Bullets / list markers
    "\u2022": ".",   # •
    "\u2023": ".",   # ‣
    "\u25e6": ".",   # ◦
    "\u2043": "-",   # ⁃
    "\u00b7": ".",   # ·
    # Arrows -> read as "to"
    "\u2192": " to ", "\u2190": " from ",
    "\u21d2": " implies ", "\u21d0": " implied by ",
    # Math/symbol
    "\u00d7": " by ", "\u00f7": " divided by ",
    "\u00b1": " plus or minus ",
    "\u2260": " not equal to ",
    "\u2264": " less than or equal to ",
    "\u2265": " greater than or equal to ",
    "\u00b0": " degrees",
    # Currency
    "\u20ac": " euros ", "\u00a3": " pounds ", "\u00a5": " yen ",
    # Misc whitespace and invisible chars
    "\u00a0": " ",   # NBSP
    "\u2009": " ",   # thin space
    "\u200a": " ",   # hair space
    "\u202f": " ",   # narrow NBSP
    "\u200b": "",    # zero-width space (the silent killer)
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\ufeff": "",    # BOM
    "\u00ad": "",    # soft hyphen
}

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

    # Normalize unicode form (collapses combining sequences, fullwidth
    # variants, etc.) before character-level replacement.
    text = unicodedata.normalize("NFKC", text)

    # Replace special unicode chars (em-dash, smart quotes, bullets,
    # zero-width killers, math symbols) with TTS-friendly equivalents.
    for src, repl in _CHAR_MAP.items():
        if src in text:
            text = text.replace(src, repl)

    # Drop any remaining control characters that aren't \n or \t.
    text = "".join(
        ch for ch in text
        if ch in ("\n", "\t") or unicodedata.category(ch)[0] != "C"
    )

    # Strip fenced code blocks entirely and inline code to plain.
    text = _MARKDOWN_FENCE_RE.sub(" ", text)
    text = _INLINE_CODE_RE.sub(r"\1", text)

    # Markdown links: keep visible label, drop URL.
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)

    # Replace bare URLs and emails with a short spoken placeholder
    # instead of the literal string, which tends to trip the model.
    text = _URL_RE.sub("link", text)
    text = _EMAIL_RE.sub("email address", text)

    # File paths read poorly; replace with a short word.
    text = _PATH_RE.sub(" path ", text)

    # Long hex hashes → spoken placeholder.
    text = _HASH_RE.sub("hash", text)

    # Shell flags: --cached -> "cached", -rf -> "r f". Prevents the
    # model trying to vocalize the dash or freezing on dash sequences.
    text = _SHELL_FLAG_RE.sub(lambda m: " " + m.group(1).replace("-", " "), text)
    text = _SHELL_SHORT_FLAG_RE.sub(lambda m: " " + " ".join(m.group(1)), text)

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
