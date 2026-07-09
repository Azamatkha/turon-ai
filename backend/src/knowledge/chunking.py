"""Very small text chunker.

Splits on blank lines (paragraphs) and packs paragraphs into chunks of at most
`max_chars`, splitting any single oversized paragraph. Good enough for Stage 1;
a smarter, token-aware splitter can replace it later.
"""


def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
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
            # Paragraph itself is too long — hard-split it with overlap.
            if current:
                chunks.append(current)
                current = ""
            step = max(1, max_chars - overlap)
            for i in range(0, len(para), step):
                chunks.append(para[i : i + max_chars])

    if current:
        chunks.append(current)
    return chunks
