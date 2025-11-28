import os
import re
import requests
import tempfile

# --------------------------------------------
# Download document from a URL → local temp file
# --------------------------------------------
def download_file(url: str, suffix=".pdf"):
    """
    Downloads document from URL and saves it to a temporary local file.
    Supports PDF, PNG, JPG.
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        # Detect content type
        ct = resp.headers.get("Content-Type", "").lower()

        if "pdf" in ct:
            suffix = ".pdf"
        elif "png" in ct:
            suffix = ".png"
        elif "jpg" in ct or "jpeg" in ct:
            suffix = ".jpg"
        else:
            # fallback
            suffix = suffix

        f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        f.write(resp.content)
        f.close()
        return f.name

    except Exception as e:
        raise RuntimeError(f"Failed to download file: {str(e)}")


# --------------------------------------------
# Page-type detection logic
# --------------------------------------------
def detect_page_type(tokens):
    """
    Determines the page type based on token content.
    Types:
        - Pharmacy
        - Final Bill
        - Bill Detail
    """
    text = " ".join(t["text"].lower() for t in tokens)

    # Strong markers of pharmacy pages
    pharmacy_markers = [
        "tab", "tablet", "cap", "capsule",
        "syrup", "syp", "inj", "injection",
        "ointment", "cream", "ml", "mg"
    ]

    # Markers of final summary
    final_bill_markers = [
        "final bill",
        "summary",
        "consolidated",
        "settlement",
        "net payable",
        "gross amount",
        "net amount"
    ]

    if any(w in text for w in pharmacy_markers):
        return "Pharmacy"
    if any(w in text for w in final_bill_markers):
        return "Final Bill"

    # Default to bill detail
    return "Bill Detail"


# --------------------------------------------
# Numeric helpers
# --------------------------------------------
def is_float(x):
    try:
        float(x)
        return True
    except:
        return False


def to_float(x):
    try:
        return float(x)
    except:
        return None


# --------------------------------------------
# Text cleaning helpers
# --------------------------------------------
def clean_text(t):
    if not t:
        return ""
    t = t.strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^0-9A-Za-z()%\-./ ]", "", t)
    return t


def normalize_name(name):
    name = str(name).strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^0-9A-Za-z()\-./ ]", "", name)
    return name


# --------------------------------------------
# Bounding box helpers (optional but safe)
# --------------------------------------------
def bbox_center(token):
    return token["x"] + token["w"] / 2, token["y"] + token["h"] / 2


# --------------------------------------------
# Debug helper (optional)
# --------------------------------------------
def print_tokens(tokens):
    for t in tokens:
        print(f"{t['text']:20s}  x={t['x']:<4d} y={t['y']:<4d} line={t['line_num']}")
