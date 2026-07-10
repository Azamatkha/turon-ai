"""Small text chunker.

Splits on blank lines (paragraphs) and packs paragraphs into chunks of at most
`max_chars`. If a single paragraph is too long, it is split on sentence
boundaries, and only as a last resort on word boundaries — never mid-word.
"""

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(paragraph) if s.strip()]


def _split_by_words(text: str, max_chars: int) -> list[str]:
    """Oxirgi chora: so'zlarni chegara qilib bo'lamiz (hech qachon so'z ichidan
    kesmaymiz)."""
    words = text.split(" ")
    chunks: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            chunks.append(current)
            current = ""
        current = f"{current} {word}" if current else word
    if current:
        chunks.append(current)
    return chunks


def _pack_units(units: list[str], max_chars: int, joiner: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + len(joiner) + len(unit) > max_chars:
            chunks.append(current)
            current = ""
        if len(unit) <= max_chars:
            current = f"{current}{joiner}{unit}" if current else unit
        else:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_by_words(unit, max_chars))
    if current:
        chunks.append(current)
    return chunks


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current)
            current = ""

        if len(para) <= max_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            # Paragraf o'zi juda uzun — avval gaplarga, kerak bo'lsa so'zlarga
            # bo'lamiz. Xarakter bo'yicha qattiq kesish (so'z o'rtasidan) YO'Q.
            if current:
                chunks.append(current)
                current = ""
            sentences = _split_sentences(para)
            if len(sentences) > 1:
                chunks.extend(_pack_units(sentences, max_chars, " "))
            else:
                chunks.extend(_split_by_words(para, max_chars))

    if current:
        chunks.append(current)
    return chunks
