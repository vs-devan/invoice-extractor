"""
main.py
-------
Final integrated FastAPI application with:
- Document download
- PDF/image loading
- OCR (tesseract)
- Parsing into line items
- Postprocessing (dedup, subtotal removal, reconciliation)
- Logging

Endpoint:
POST /extract-bill-data
"""

import traceback
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any

# Internal modules
from app.utils import logger
from app.ocr import download_document, load_document_as_images, run_ocr_page
from app.parser import extract_line_items
from app.postproc import postprocess_items


# ---------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------
app = FastAPI(
    title="Bill Extraction API",
    version="1.0",
    description="Extracts structured line items and totals from invoices."
)


# ---------------------------------------------------------------------
# Request Model
# ---------------------------------------------------------------------
class DocRequest(BaseModel):
    document: str



# ---------------------------------------------------------------------
# Main Endpoint
# ---------------------------------------------------------------------

@app.post("/extract-bill-data")
async def extract_bill_data(req: DocRequest) -> Dict[str, Any]:
    """
    Main API endpoint required by the problem statement.
    Processes the bill and returns extracted line-items + totals.
    """
    try:
        logger.info("Received request for document extraction")
        logger.info(f"Downloading document from URL: {req.document}")

        # 1. Download file
        local_path = download_document(req.document)
        logger.info(f"Document downloaded to: {local_path}")

        # 2. Convert to images
        pages = load_document_as_images(local_path)
        logger.info(f"Loaded {len(pages)} page(s) from the file")

        pagewise_output = []
        all_raw_items = []

        # 3. OCR + Parse Pages
        for idx, page_img in enumerate(pages, start=1):
            logger.info(f"Processing page {idx}...")

            # OCR tokens
            tokens = run_ocr_page(page_img)
            logger.info(f"OCR produced {len(tokens)} tokens on page {idx}")

            # Parse tokens → raw line items
            items = extract_line_items(tokens)
            logger.info(f"Extracted {len(items)} raw items on page {idx}")

            # Store page-level items before postprocessing
            if len(items) > 0:
                pagewise_output.append({
                    "page_no": str(idx),
                    "bill_items": items
                })

            # Keep accumulating for global reconciliation
            all_raw_items.extend(items)

        logger.info(f"Total raw extracted items across all pages: {len(all_raw_items)}")

        # 4. Postprocessing (dedup, subtotal removal, reconciliation)
        processed = postprocess_items(all_raw_items)
        logger.info(f"Postprocessed {processed['total_item_count']} final items")
        logger.info(f"Reconciled amount = {processed['reconciled_amount']}")

        # Attach cleaned items back into per-page structure
        # (flat split across pages in order)
        flat = processed["items"]
        for page in pagewise_output:
            count = len(page["bill_items"])
            page["bill_items"] = flat[:count]
            flat = flat[count:]

        # 5. Final response
        logger.info("Returning successful response")

        return {
            "is_success": True,
            "data": {
                "pagewise_line_items": pagewise_output,
                "total_item_count": processed["total_item_count"],
                "reconciled_amount": processed["reconciled_amount"]
            }
        }

    except Exception as e:
        logger.error("Exception while processing the document")
        logger.error(traceback.format_exc())

        return {
            "is_success": False,
            "error": str(e)
        }
