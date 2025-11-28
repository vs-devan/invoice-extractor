"""
utils.py
--------
Shared utility functions used by parser, postproc, and main API.

Includes:
    - Numeric parsing
    - Text normalization
    - Logging helper
    - Common regex cleaning
"""

import re
import logging


# ------------------------------------------------------
# Logger Setup
# ------------------------------------------------------

def get_logger(name: str = "invoice_extractor"):
    """Create or retrieve a logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = get_logger()


# ------------------------------------------------------
# Number Parsing Helpers
# ------------------------------------------------------

def safe_float(text: str):
    """
    Converts text into float safely.
    Handles:
        - "1,234.50"
        - "₹ 180.00"
        - "(150.00)"
        - "- 200"
    Returns None if parse fails.
    """
    if text is None:
        return None

    s = str(text)
    s = s.replace(",", "").replace("₹", "").strip()

    # Handle negative in parentheses: (150.00)
    if re.match(r"^\(\s*\d+(\.\d+)?\s*\)$", s):
        s = "-" + s.replace("(", "").replace(")", "")

    # Keep only digits, dot, and minus
    s = re.sub(r"[^0-9.\-]", "", s)

    try:
        return float(s)
    except:
        return None


# ------------------------------------------------------
# Text Cleanup
# ------------------------------------------------------

def clean_text(text: str) -> str:
    """Trim whitespace and collapse multiple spaces."""
    if text is None:
        return ""
    t = str(text)
    t = t.replace("\n", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def normalize_text(text: str) -> str:
    """
    Lowercase, remove punctuation, collapse whitespace.
    Useful for fuzzy comparisons & dedup.
    """
    if not text:
        return ""
    t = clean_text(text).lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


# ------------------------------------------------------
# Regex Convenience Wrappers
# ------------------------------------------------------

def contains_total_keyword(text: str) -> bool:
    """Detects 'total', 'subtotal', 'grand total' in a safe fuzzy way."""
    if not text:
        return False
    return bool(re.search(r"(?i)(total|sub\s*total|grand\s*total)", text))


def contains_section_keyword(text: str) -> bool:
    """
    Detects typical hospital bill section headings used in sample PDFs.
    You can extend this list as needed.
    """
    if not text:
        return False

    sections = [
        "consultation",
        "room charges",
        "nursing care",
        "laboratory services",
        "radiology services",
        "surgery",
        "procedure",
        "investigation",
        "others",
    ]

    t = text.lower()
    return any(sec in t for sec in sections)
