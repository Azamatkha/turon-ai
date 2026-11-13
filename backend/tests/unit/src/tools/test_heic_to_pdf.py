"""iPhone rasm formatlari (HEIC/HEIF, AVIF, PNG skrinshot, GIF) PDF'ga o'giriladi."""

import io

from PIL import Image
import pymupdf
import pytest

from src.tools.pdf_convert import IMAGE_EXTS, images_to_pdf


def _image_bytes(fmt: str, mode: str = "RGB") -> bytes:
    out = io.BytesIO()
    Image.new(mode, (40, 30), (200, 30, 30) if mode == "RGB" else 1).save(out, fmt)
    return out.getvalue()


def test_iphone_extensions_supported() -> None:
    assert {"heic", "heif", "hif", "avif", "gif", "jpg", "png"} <= IMAGE_EXTS


@pytest.mark.parametrize(("fmt", "mode"), [("HEIF", "RGB"), ("AVIF", "RGB"), ("GIF", "P"), ("PNG", "RGB")])
def test_image_becomes_pdf_page(fmt: str, mode: str) -> None:
    pdf = images_to_pdf([_image_bytes(fmt, mode)])
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        assert doc.page_count == 1
        # Keng rasm — albom sahifa
        assert doc[0].rect.width > doc[0].rect.height
        assert doc[0].get_images()
    finally:
        doc.close()


def test_mixed_iphone_images_one_pdf() -> None:
    pdf = images_to_pdf([_image_bytes("HEIF"), _image_bytes("JPEG"), _image_bytes("AVIF")])
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    try:
        assert doc.page_count == 3
    finally:
        doc.close()
