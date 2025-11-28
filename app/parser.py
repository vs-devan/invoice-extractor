import re

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
# Group OCR tokens into rows based on line number
# ----------------------------------------
def group_rows(tokens):
    """
    Groups OCR tokens into line rows based on Tesseract line_num.
    Each row is sorted left-to-right.
    """
    rows = {}
    for t in tokens:
        ln = t["line_num"]
        rows.setdefault(ln, []).append(t)

    # Sort tokens left → right inside each row
    for ln in rows:
        rows[ln] = sorted(rows[ln], key=lambda t: t["x"])

    # Return rows sorted by line number
    return [rows[k] for k in sorted(rows.keys())]


# ----------------------------------------
# Column-based parsing logic tuned for medical/pharmacy bills
# ----------------------------------------
def parse_rows_into_items(rows, page_width):
    """
    Parses bill rows into structured item entries:
    item_name, quantity, rate, amount
    
    This parser is fine-tuned for Sample Document 1/2/3
    following the column structure.

    LEFT COLUMN = item description (string)
    RIGHT COLUMNS = numeric columns for qty / rate / amount
    """

    items = []

    # Define column zones (empirical from your documents)
    col_name_max_x = page_width * 0.55   # everything left of this is item-name space
    col_numeric_min_x = page_width * 0.40  # numeric columns are usually to the right
    max_item_amount = 200000    # safety threshold to remove OCR errors
    max_item_rate = 50000
    max_item_qty = 500

    for row in rows:
        # ----------------------------
        # 1. Split tokens into name-side and numeric-side
        # ----------------------------
        name_tokens = [t for t in row if t["x"] < col_name_max_x and not is_float(t["text"])]
        numeric_tokens = [t for t in row if t["x"] > col_numeric_min_x and is_float(t["text"])]

        # Ignore rows that clearly do not represent items (headers, blank)
        if len(name_tokens) == 0:
            continue

        # Construct item name by joining left-side text
        item_name = " ".join(t["text"] for t in name_tokens).strip()

        # ----------------------------------------
        # 2. Extract numeric columns: qty, rate, amount
        # ----------------------------------------
        nums = [to_float(t["text"]) for t in numeric_tokens]
        nums = [x for x in nums if x is not None]

        if len(nums) == 0:
            # Could be name-only line
            continue

        # Sort values small → large to guess qty, rate, amount
        nums_sorted = sorted(nums)

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
        # 3. Strict numeric rules
        # ----------------------------------------
        if not (0 < qty <= max_item_qty):
            continue
        if not (0 < rate <= max_item_rate):
            continue
        if not (0 < amount <= max_item_amount):
            continue

        # Consistency rule: amount ≈ qty * rate (±10%)
        if abs(amount - qty * rate) > max(5, amount * 0.15):
            continue

        # ----------------------------------------
        # 4. Avoid duplicate junk like "0.00 0.00"
        # ----------------------------------------
        if amount == 0 or rate == 0:
            continue

        # ----------------------------------------
        # 5. Add item
        # ----------------------------------------
        item = {
            "item_name": item_name,
            "item_quantity": round(qty, 2),
            "item_rate": round(rate, 2),
            "item_amount": round(amount, 2)
        }
        items.append(item)

    return items
