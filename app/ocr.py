import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path

# -------------------------------
# Preprocessing for medical bills
# -------------------------------
def preprocess_image(image):
    """
    Preprocesses scanned medical bills for robust OCR.
    Tuned for Sample Document 1/2/3 patterns.
    """

    # Convert PIL -> OpenCV BGR
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Remove noise
    denoised = cv2.fastNlMeansDenoising(gray, h=15)

    # Sharpen text slightly
    kernel_sharp = np.array([[0, -1, 0],
                             [-1, 5,-1],
                             [0, -1, 0]])
    sharp = cv2.filter2D(denoised, -1, kernel_sharp)

    # Adaptive threshold tuned for bills
    thresh = cv2.adaptiveThreshold(
        sharp, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=12
    )

    # Light dilation to connect column text
    kernel = np.ones((1, 2), np.uint8)
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    return dilated


# -------------------------------
# PDF Loader
# -------------------------------
def load_document(path):
    """
    Loads PDF as list of images at optimal DPI for numeric extraction.
    300 DPI => much better accuracy for Rate/Qty/Amount.
    """
    pages = convert_from_path(path, dpi=200, thread_count=1)
    return pages


# -------------------------------
# OCR Token Extraction
# -------------------------------
def extract_tokens(image):
    """
    Extracts OCR tokens with bounding boxes.
    Uses PSM 6 → assume block of text (best for line-item tables).
    OEM LSTM → best accuracy for medicine names + numbers.
    """

    processed = preprocess_image(image)

    # OCR config tuned for tables
    config = (
        "--psm 6 "          # uniform block/table of text
        "--oem 3 "          # LSTM neural OCR engine
        "-c tessedit_char_blacklist={}[]()/\\|"  # remove table symbols
        "-c preserve_interword_spaces=1" \
        "omp_num_threads=1"
    )

    data = pytesseract.image_to_data(
        processed,
        output_type=pytesseract.Output.DICT,
        config=config
    )

    tokens = []
    n = len(data["text"])

    for i in range(n):
        text = data["text"][i].strip()
        if not text:
            continue

        # Remove pure noise
        if len(text) == 1 and not text.isalnum():
            continue

        tokens.append({
            "text": text,
            "x": data["left"][i],
            "y": data["top"][i],
            "w": data["width"][i],
            "h": data["height"][i],
            "line_num": data["line_num"][i],
            "conf": int(data["conf"][i])
        })

    # Remove very low-confidence tokens (noise)
    tokens = [t for t in tokens if t["conf"] > 30]

    return tokens


# -------------------------------
# STEP A: Clean OCR Text Output
# -------------------------------
def extract_clean_text(image):
    """
    Step A: Initial Processing - Extract clean, reliable text from image.
    
    This is the first step of the two-step approach:
    1. Get clean text output from OCR
    2. Use this text for structured extraction
    
    Returns:
    - raw_text: Full OCR text output
    - tokens: Detailed token data with positions for column-based parsing
    - text_lines: Text organized by line for easier processing
    """
    
    # Extract detailed tokens
    tokens = extract_tokens(image)
    
    # Build raw OCR text
    raw_text = " ".join(t["text"] for t in tokens)
    
    # Group text by line for structured reading
    lines_dict = {}
    for t in tokens:
        ln = t["line_num"]
        if ln not in lines_dict:
            lines_dict[ln] = []
        lines_dict[ln].append(t)
    
    # Sort tokens within each line left-to-right
    text_lines = []
    for ln in sorted(lines_dict.keys()):
        line_tokens = sorted(lines_dict[ln], key=lambda t: t["x"])
        line_text = " ".join(t["text"] for t in line_tokens)
        text_lines.append({
            "line_num": ln,
            "text": line_text,
            "tokens": line_tokens
        })
    
    return {
        "raw_text": raw_text,
        "tokens": tokens,
        "text_lines": text_lines
    }
