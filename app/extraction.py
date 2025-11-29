"""
STEP B: Information Extraction Module

Takes the clean OCR text output from Step A and generates structured JSON.
This module focuses on:
1. Parsing clean text into line items
2. Extracting item name, quantity, rate, amount
3. Validating and structuring the output
"""

import re
from datetime import datetime

# ----------------------------------------
# Numeric helper
# ----------------------------------------
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


# ----------------------------------------
# GUARD AGAINST INTERPRETATION ERRORS
# Detect non-monetary fields that should NOT be extracted
# ----------------------------------------

def is_date_like(text: str) -> bool:
    """
    Detect if text looks like a date.
    Prevents Invoice Date/Time from being extracted as amounts.
    
    Examples:
    - "2025-11-29" → True
    - "29/11/2025" → True
    - "11-29-2025" → True
    - "29.11.2025" → True
    - "2025" → True (year alone)
    - "50" → False (not obviously a date)
    """
    text = text.strip()
    
    # Check for date patterns
    date_patterns = [
        r'^\d{4}-\d{2}-\d{2}',      # YYYY-MM-DD
        r'^\d{2}/\d{2}/\d{4}',      # DD/MM/YYYY or MM/DD/YYYY
        r'^\d{1,2}-\d{1,2}-\d{4}',  # D-M-YYYY
        r'^\d{1,2}\.\d{1,2}\.\d{4}',# D.M.YYYY
        r'^\d{4}$',                  # YYYY alone (year)
    ]
    
    for pattern in date_patterns:
        if re.match(pattern, text):
            return True
    
    return False


def is_invoice_identifier(text: str) -> bool:
    """
    Detect if text looks like an invoice number, invoice ID, or similar identifier.
    Prevents Invoice Number fields from being extracted as amounts.
    
    Examples:
    - "INV123456" → True
    - "INV-2025-001" → True
    - "Invoice #123" → True
    - "ID:XYZ789" → True
    - "REF12345" → True
    - "50" → False (just a number)
    """
    text = text.upper().strip()
    
    # Explicit invoice identifier keywords
    invoice_keywords = [
        "INV",
        "INVOICE",
        "REF",
        "REFERENCE",
        "ID",
        "NUMBER",
        "#",
        "BILL",
        "BILL#",
        "ORDER",
        "ORD",
        "DOC",
    ]
    
    for keyword in invoice_keywords:
        if keyword in text:
            return True
    
    # Pattern: starts with letters followed by numbers (e.g., INV123456)
    if re.match(r'^[A-Z]+[-_]?[\d]+', text):
        return True
    
    return False


def is_time_like(text: str) -> bool:
    """
    Detect if text looks like a time value.
    Prevents Invoice Time from being extracted as amounts.
    
    Examples:
    - "14:30:00" → True
    - "14:30" → True
    - "2:30 PM" → True
    - "02:30" → True
    - "50" → False (just a number)
    """
    text = text.strip()
    
    # Check for time patterns
    time_patterns = [
        r'^\d{1,2}:\d{2}:\d{2}',     # HH:MM:SS
        r'^\d{1,2}:\d{2}',            # HH:MM
        r'^\d{1,2}:\d{2}\s*(AM|PM)',  # HH:MM AM/PM
    ]
    
    for pattern in time_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    return False


def is_monetary_value(value: float, context_text: str = "") -> bool:
    """
    Determine if a numeric value is likely a monetary amount (not a date/ID/time).
    
    Guards against:
    - Year values (1900-2100) being treated as amounts
    - Small integers that look like dates (01-31)
    - Invoice numbers
    - Quantity-like values in wrong context
    
    Args:
        value: The numeric value to check
        context_text: Surrounding text for context
    
    Returns:
        True if value is likely monetary, False if suspicious
    """
    
    # Range check: typical monetary amounts are more realistic
    # (dates are often 1-31, 1-12, or 1900-2100)
    if value < 0.01:
        return False  # Too small to be meaningful
    
    # Check if value looks like a year (1900-2100)
    if 1900 <= value <= 2100:
        # If context mentions "date", "year", "invoice", or "20XX" pattern
        if any(keyword in context_text.lower() for keyword in 
               ["date", "year", "invoice", "20", "19"]):
            return False
    
    # Check if value looks like a day/month (1-31, or 1-12)
    if 1 <= value <= 31:
        # Only accept if it's clearly in a monetary context
        if not any(keyword in context_text.lower() for keyword in 
                   ["quantity", "qty", "amount", "rate", "price", "cost", "total"]):
            return False
    
    # Values in range 1900-2100 are suspicious (might be years)
    if 1900 <= value <= 2100:
        return False
    
    return True


def should_skip_line(line_text: str, item_name: str) -> bool:
    """
    Determine if a line should be skipped entirely based on content patterns.
    
    Skips:
    - Header/footer lines
    - Date/time related lines
    - Invoice metadata lines
    - Section headers
    
    Args:
        line_text: The full text of the line
        item_name: The extracted item name from the line
    
    Returns:
        True if line should be skipped, False if it might be valid
    """
    
    line_lower = line_text.lower()
    
    # Skip common header/footer keywords
    skip_keywords = [
        "invoice", "date", "time", "number", "patient", "doctor",
        "hospital", "reference", "page", "total", "amount", "due",
        "paid", "balance", "gst", "tax", "discount", "subtotal",
        "bill", "ref", "id:", "inv", "document"
    ]
    
    for keyword in skip_keywords:
        if keyword in line_lower:
            return True
    
    # Skip if item name contains only numbers/dates
    if re.match(r'^[\d\-/:\.]+$', item_name):
        return True
    
    return False


# ----------------------------------------
# STEP B: Extract structured items from clean OCR text
# ----------------------------------------
def extract_items_from_ocr_text(text_lines, page_width):
    """
    Step B: Information Extraction
    
    Takes clean OCR text (Step A output) and extracts structured item data.
    
    GUARDS AGAINST INTERPRETATION ERRORS:
    - Date fields (Invoice Date, Time) won't be extracted as amounts
    - Invoice numbers and IDs are excluded
    - Non-monetary identifiers are filtered
    - Clear constraints distinguish currency from identifiers
    
    Args:
        text_lines: List of line dicts from Step A, each with "text" and "tokens"
        page_width: Width of the page for column boundary inference
    
    Returns:
        List of structured item dicts with: item_name, item_quantity, item_rate, item_amount
    """
    
    items = []
    
    # Define column zones based on page width
    col_name_max_x = page_width * 0.55   # item name is typically left half
    col_numeric_min_x = page_width * 0.40  # numeric columns start around 40%
    
    # Safety thresholds for numeric values
    max_item_amount = 200000
    max_item_rate = 50000
    max_item_qty = 500
    min_item_amount = 0.01  # Minimum meaningful monetary amount
    min_item_rate = 0.01
    min_item_qty = 0.01
    
    for line_dict in text_lines:
        tokens = line_dict.get("tokens", [])
        text = line_dict.get("text", "").strip()
        
        if not text:
            continue
        
        # ========== GUARD: Skip lines that are metadata/headers ==========
        # Early exit for obvious non-item lines
        name_tokens = [t for t in tokens if t["x"] < col_name_max_x and not is_float(t["text"])]
        if name_tokens:
            temp_name = " ".join(t["text"] for t in name_tokens).strip()
            if should_skip_line(text, temp_name):
                continue
        
        # ----------------------------
        # 1. Split tokens into name-side and numeric-side
        # ----------------------------
        name_tokens = [t for t in tokens if t["x"] < col_name_max_x and not is_float(t["text"])]
        numeric_tokens = [t for t in tokens if t["x"] > col_numeric_min_x and is_float(t["text"])]
        
        # Skip lines without meaningful item name
        if len(name_tokens) == 0:
            continue
        
        # Construct item name from left-side text
        item_name = " ".join(t["text"] for t in name_tokens).strip()
        
        # ========== GUARD: Check if item name is suspicious ==========
        if is_date_like(item_name) or is_time_like(item_name) or is_invoice_identifier(item_name):
            continue
        
        # ----------------------------------------
        # 2. Extract numeric columns: qty, rate, amount
        # ----------------------------------------
        nums = [to_float(t["text"]) for t in numeric_tokens]
        nums = [x for x in nums if x is not None]
        
        if len(nums) == 0:
            continue
        
        # ========== GUARD: Filter out suspicious numeric values ==========
        # Remove dates (4-digit years, day/month patterns), invoice numbers, etc.
        filtered_nums = []
        for num in nums:
            # Check if this number looks like a date or identifier
            if is_date_like(str(int(num))) or is_time_like(str(int(num))):
                continue  # Skip dates/times
            
            # Check if it's a monetary value in context
            if not is_monetary_value(num, item_name + " " + text):
                continue  # Skip non-monetary values
            
            filtered_nums.append(num)
        
        # If all numbers were filtered out, skip this line
        if len(filtered_nums) == 0:
            continue
        
        # Sort values small → large to guess qty, rate, amount
        nums_sorted = sorted(filtered_nums)
        
        qty = rate = amount = None
        
        # Heuristic mapping:
        # Usually: Quantity < Rate < Amount/NetAmount
        if len(nums_sorted) >= 3:
            qty, rate, amount = nums_sorted[-3:]
        elif len(nums_sorted) == 2:
            qty, rate = nums_sorted
            amount = qty * rate
        else:
            continue
        
        # ----------------------------------------
        # 3. Strict numeric validation
        # ----------------------------------------
        # Check minimum thresholds (guard against small junk values)
        if not (min_item_qty < qty <= max_item_qty):
            continue
        if not (min_item_rate < rate <= max_item_rate):
            continue
        if not (min_item_amount < amount <= max_item_amount):
            continue
        
        # Consistency rule: amount ≈ qty * rate (±15% tolerance)
        if abs(amount - qty * rate) > max(5, amount * 0.15):
            continue
        
        # ========== GUARD: Final sanity check ==========
        # Ensure values are realistic for pharmacy items
        # Quantity should be > 0
        if qty <= 0:
            continue
        
        # Rate should be > 0
        if rate <= 0:
            continue
        
        # Amount should be > 0
        if amount <= 0:
            continue
        
        # Amount should be reasonable (not too small for pharmacy items)
        if amount < 0.5:
            continue
        
        # ----------------------------------------
        # 4. Create structured item
        # ----------------------------------------
        item = {
            "item_name": item_name,
            "item_quantity": round(qty, 2),
            "item_rate": round(rate, 2),
            "item_amount": round(amount, 2)
        }
        items.append(item)
    
    return items


# ----------------------------------------
# Alternative: Direct text parsing (for future LLM integration)
# ----------------------------------------
def extract_items_from_text_direct(raw_text):
    """
    Alternative extraction method using direct text parsing.
    Useful if you want to integrate with an LLM or NLP model later.
    
    For now, returns empty list as placeholder for future enhancement.
    """
    # TODO: Integrate with Claude/GPT for semantic extraction
    # Can pass raw_text to LLM and get structured JSON
    return []
