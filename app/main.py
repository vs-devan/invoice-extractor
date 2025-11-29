from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import traceback
import logging

from app.utils import download_file, detect_page_type
from app.ocr import load_document, extract_tokens, extract_clean_text
from app.extraction import extract_items_from_ocr_text
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
    TWO-STEP PIPELINE:
    
    STEP A: Initial Processing (OCR)
    - Load document
    - Extract clean, reliable OCR text from image
    - Get raw text output and organized text lines
    
    STEP B: Information Extraction (JSON Generation)
    - Parse clean OCR text into structured line items
    - Extract item name, quantity, rate, amount
    - Apply strict validation and filtering
    - Return HackRx-compliant JSON
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
        # 3. Process each page with TWO-STEP approach
        # ------------------------------------------------
        for idx, page in enumerate(pages, start=1):
            logger.info(f"Processing page {idx}...")

            # ========== STEP A: Initial OCR Processing ==========
            logger.info(f"[STEP A] Extracting clean OCR text from page {idx}...")
            ocr_data = extract_clean_text(page)
            
            raw_text = ocr_data["raw_text"]
            text_lines = ocr_data["text_lines"]
            
            logger.info(f"[STEP A] Extracted {len(text_lines)} text lines")
            logger.debug(f"[STEP A] Raw OCR text (first 200 chars): {raw_text[:200]}")

            # 3.2 Page-type detection
            page_type = detect_page_type(ocr_data["tokens"])
            logger.info(f"Page {idx} classified as: {page_type}")

            # ========== STEP B: Information Extraction ==========
            # Only extract items for Pharmacy pages
            if page_type == "Pharmacy":
                logger.info(f"[STEP B] Extracting structured items from clean OCR text...")
                
                # Parse clean text into structured items
                raw_items = extract_items_from_ocr_text(text_lines, page.width)
                logger.info(f"[STEP B] Extracted {len(raw_items)} raw items")
                
                # Apply strict filtering and validation
                cleaned = filter_items_strict(raw_items)
                logger.info(f"[STEP B] After filtering: {len(cleaned)} valid items")
                
                # Log sample items for debugging
                if cleaned:
                    logger.debug(f"[STEP B] Sample item: {cleaned[0]}")
            else:
                logger.info(f"[STEP B] Skipping item extraction (not a Pharmacy page)")
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
        logger.info(f"Pipeline complete. Total items extracted: {total_items}")
        
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
