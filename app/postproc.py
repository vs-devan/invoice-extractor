"""
postproc.py
------------
Post-processing on extracted line items:
    - Clean & normalize rows
    - Remove duplicates
    - Remove subtotal-like rows
    - Compute reconciled total
"""

from typing import List, Dict, Any
import re
from rapidfuzz import fuzz


# -------------------------------------------------------
# Text Normalization Helper
# -------------------------------------------------------

def normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


# -------------------------------------------------------
# Detect if a row is likely a subtotal line
# -------------------------------------------------------

def is_subtotal_row(item: Dict[str, Any]) -> bool:
    """
    Heuristic: rows with no quantity/rate but have an amount
    and name looks generic (CONSULTATION, LAB SERVICES)
    """
    name = item["item_name"].lower()

    if "total" in name:
        return True

    # Subtotal-like patterns
    subtotal_keywords = [
        "consultation", "room charges", "nursing care",
        "laboratory services", "radiology services",
        "surgery", "procedure charges", "investigation charges",
        "others"
    ]

    if any(k in name for k in subtotal_keywords):
        # Case: subtotal row has amount but no qty/rate
        if not item["item_quantity"] and not item["item_rate"]:
            return True

    return False


# -------------------------------------------------------
# Deduplication
# -------------------------------------------------------

def deduplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicates based on fuzzy matching of names + amounts.
    """

    unique_items = []
    seen = []

    for itm in items:
        name_norm = normalize_name(itm["item_name"])
        amount = itm["item_amount"]

        is_dup = False

        for (prev_name, prev_amt) in seen:
            # If names extremely similar and amounts match → duplicate
            if fuzz.token_sort_ratio(name_norm, prev_name) >= 92 and abs(prev_amt - amount) < 0.001:
                is_dup = True
                break

        if not is_dup:
            unique_items.append(itm)
            seen.append((name_norm, amount))

    return unique_items


# -------------------------------------------------------
# Clean None fields
# -------------------------------------------------------

def clean_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove empty fields & standardize amount/qty/rate.
    """
    cleaned = []
    for itm in items:
        cleaned.append({
            "item_name": itm["item_name"],
            "item_amount": float(itm["item_amount"]) if itm["item_amount"] else None,
            "item_rate": float(itm["item_rate"]) if itm["item_rate"] else None,
            "item_quantity": float(itm["item_quantity"]) if itm["item_quantity"] else None
        })
    return cleaned


# -------------------------------------------------------
# Optional confidence scoring
# -------------------------------------------------------

def compute_confidence(item: Dict[str, Any]) -> float:
    """
    Simple rule-based confidence score (0–1).
    You can extend this later using OCR confidences in parser.
    """
    score = 1.0

    # Missing fields reduce confidence slightly
    if item["item_quantity"] is None:
        score -= 0.1
    if item["item_rate"] is None:
        score -= 0.1

    return max(0.0, min(1.0, score))


# -------------------------------------------------------
# Main Post-Processing Function
# -------------------------------------------------------

def postprocess_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Full pipeline:
        - Remove subtotal-like rows
        - Deduplicate
        - Clean
        - Add confidence
        - Compute reconciled amount
    """

    # 1. Drop subtotal / section header rows
    filtered = []
    for itm in items:
        if not is_subtotal_row(itm):
            filtered.append(itm)

    # 2. Deduplicate
    deduped = deduplicate_items(filtered)

    # 3. Clean
    cleaned = clean_items(deduped)

    # 4. Add confidence
    for itm in cleaned:
        itm["confidence"] = compute_confidence(itm)

    # 5. Compute reconciled total
    total_amount = sum(it["item_amount"] for it in cleaned if it["item_amount"] is not None)
    total_amount = round(total_amount, 2)

    return {
        "items": cleaned,
        "reconciled_amount": total_amount,
        "total_item_count": len(cleaned)
    }
