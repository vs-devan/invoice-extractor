from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging

from app.utils import download_file, detect_page_type
from app.ocr import load_document, extract_tokens
from app.parser import group_rows, parse_rows_into_items
from app.postproc import filter_items_strict


# ----------------------------------------------------
# FASTAPI Initialization
# ----------------------------------------------------
app = FastAPI(title="Bajaj Bill Extraction API")

logger = logging.getLogger("uvicorn")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------
# HEALTH CHECK (Optional)
# ----------------------------------------------------
@app.get("/")
def health_check():
    return {"status": "running", "message": "HackRx Bill Extraction API"}


# ----------------------------------------------------
# REQUIRED ENDPOINT
# POST /extract-bill-data
# ----------------------------------------------------
@app.post("/extract-bill-data")
def extract_bill_data(request: dict):
    """
    Main pipeline:
    1. Download document from URL
    2. Load pages
    3. OCR each page
    4. Determine page type
    5. Extract rows → items (ONLY Pharmacy pages)
    6. Strict postprocessing
    7. Return HackRx-compliant JSON
    """

    try:
        # ------------------------------------------------
        # 1. Validate & download the document
        # ------------------------------------------------
        if "document" not in request:
            return {
                "is_success": False,
                "message": "Missing 'document' field in request"
            }

        url = request["document"]
        logger.info(f"Downloading document: {url}")

        local_path = download_file(url)
        logger.info(f"Document saved at: {local_path}")

        # ------------------------------------------------
        # 2. Load PDF pages
        # ------------------------------------------------
        pages = load_document(local_path)
        logger.info(f"Loaded {len(pages)} pages")

        pagewise_output = []
        total_items = 0

        # ------------------------------------------------
        # 3. Process each page
        # ------------------------------------------------
        for idx, page in enumerate(pages, start=1):
            logger.info(f"Processing page {idx}...")

            # 3.1 OCR extraction
            tokens = extract_tokens(page)
            logger.info(f"Extracted {len(tokens)} tokens from page {idx}")

            # 3.2 Page-type detection
            page_type = detect_page_type(tokens)
            logger.info(f"Page {idx} classified as: {page_type}")

            # 3.3 Group OCR tokens into line rows
            rows = group_rows(tokens)

            # 3.4 Extract items ONLY for Pharmacy pages
            if page_type == "Pharmacy":
                raw_items = parse_rows_into_items(rows, page.width)
                cleaned = filter_items_strict(raw_items)
                logger.info(f"Page {idx}: {len(cleaned)} cleaned pharmacy items")
            else:
                cleaned = []

            total_items += len(cleaned)

            pagewise_output.append({
                "page_no": str(idx),
                "page_type": page_type,
                "bill_items": cleaned
            })

        # ------------------------------------------------
        # 4. Final HackRx-compliant response
        # ------------------------------------------------
        return {
            "is_success": True,
            "token_usage": {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0
            },
            "data": {
                "pagewise_line_items": pagewise_output,
                "total_item_count": total_items
            }
        }

    except Exception as e:
        logger.error("Error during processing:")
        logger.error(traceback.format_exc())

        # HackRx-required error schema
        return {
            "is_success": False,
            "message": "Failed to process document. Internal server error occurred"
        }
