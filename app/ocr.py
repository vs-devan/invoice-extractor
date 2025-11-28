"""
ocr.py
-------
This module handles:
1. PDF → image conversion
2. OCR extraction (Tesseract by default)
3. Normalized structured OCR output
"""

import tempfile
import re
import requests
from typing import Dict, List, Any

from pdf2image import convert_from_path
from PIL import Image
import pytesseract


# ----------------------------------------------------------
# 1. Download Utility
# ----------------------------------------------------------

def download_document(url: str) -> str:
    """Download a PDF/Image from a public URL into a temp file."""
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise Exception(f"Failed to download document: {response.status_code}")

    # Heuristics: decide extension
    if ".pdf" in url.lower():
        suffix = ".pdf"
    else:
        suffix = ".png"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(response.content)
    tmp.flush()
    tmp.close()
    return tmp.name


# ----------------------------------------------------------
# 2. PDF → Image Conversion
# ----------------------------------------------------------

def load_document_as_images(path: str) -> List[Image.Image]:
    """
    Turns a PDF or image into a list of PIL image pages.
    """
    if path.lower().endswith(".pdf"):
        return convert_from_path(path, dpi=300)
    else:
        return [Image.open(path)]


# ----------------------------------------------------------
# 3. OCR Wrapper (Tesseract)
# ----------------------------------------------------------

def run_tesseract_ocr(image: Image.Image) -> Dict[str, List[Any]]:
    """
    Invokes Tesseract and returns token-level OCR output.
    """
    return pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT
    )


# ----------------------------------------------------------
# 4. OCR Normalization
# ----------------------------------------------------------

def clean_text(text: str) -> str:
    return text.replace("\n", " ").strip()


def normalize_ocr_output(ocr: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
    """
    Takes Tesseract raw output and produces a clean
    list of tokens with:
        - text
        - bbox (x1, y1, x2, y2)
        - confidence
        - line_id (for grouping)
    """
    tokens = []
    n = len(ocr["text"])

    for i in range(n):
        conf = int(ocr["conf"][i])
        if conf < 0:
            continue

        text = clean_text(ocr['text'][i])
        if not text:
            continue

        x, y = ocr['left'][i], ocr['top'][i]
        w, h = ocr['width'][i], ocr['height'][i]
        bbox = (x, y, x + w, y + h)

        line_id = (
            ocr["page_num"][i],
            ocr["block_num"][i],
            ocr["par_num"][i],
            ocr["line_num"][i],
        )

        tokens.append({
            "text": text,
            "bbox": bbox,
            "conf": conf,
            "line_id": line_id
        })

    return tokens


# ----------------------------------------------------------
# 5. Unified "OCR for one page" function
# ----------------------------------------------------------

def run_ocr_page(image: Image.Image) -> List[Dict[str, Any]]:
    """
    Main OCR function used by main.py:
    Returns normalized tokens for a page.
    """
    raw = run_tesseract_ocr(image)
    tokens = normalize_ocr_output(raw)
    return tokens
