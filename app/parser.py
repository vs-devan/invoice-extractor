"""
parser.py
---------
This module converts OCR token outputs into structured line items:
    {
        "item_name": ...,
        "item_quantity": ...,
        "item_rate": ...,
        "item_amount": ...
    }
It uses line grouping + numeric alignment + rule-based filtering.
"""

from typing import List, Dict, Any
import re
import numpy as np


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def parse_numeric(text: str):
    """Convert text to float if numeric-looking."""
    t = text.replace(",", "").replace("₹", "").strip()
    t = re.sub(r"[^\d\.\-]", "", t)
    try:
        return float(t)
    except:
        return None


def is_section_header(text: str) -> bool:
    """Detects common hospital section headings."""
    sections = [
        "consultation",
        "room charges",
        "nursing care",
        "laboratory services",
        "radiology services",
        "surgery",
        "procedure charges",
        "investigation charges",
        "others"
    ]
    t = text.lower().strip()
    return any(h in t for h in sections)


def is_total_line(text: str) -> bool:
    """Detects totals/subtotals/grand totals."""
    return bool(re.search(r"(?i)(total|sub\s*total|grand\s*total)", text))


# -------------------------------------------------------------------
# Line grouping from OCR tokens
# -------------------------------------------------------------------

def group_tokens_into_lines(tokens: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Groups tokens by line_id, as provided by OCR.
    Returns a list of lists of tokens belonging to the same line.
    """
    lines_map = {}
    for tok in tokens:
        line_id = tok["line_id"]
        if line_id not in lines_map:
            lines_map[line_id] = []
        lines_map[line_id].append(tok)

    # Sort tokens inside lines by x-coordinate
    lines = []
    for line in lines_map.values():
        line_sorted = sorted(line, key=lambda t: t["bbox"][0])
        lines.append(line_sorted)

    # Sort overall lines by y-coordinate
    lines = sorted(lines, key=lambda line: min(t["bbox"][1] for t in line))
    return lines


# -------------------------------------------------------------------
# Column boundary inference (simple and dataset-friendly)
# -------------------------------------------------------------------

def infer_column_boundaries(lines: List[List[Dict[str, Any]]]) -> List[int]:
    """
    Infer column breakpoints using numeric token alignment:
    - Rightmost alignment ≈ item_amount column
    - Next numeric column ≈ rate
    - Left numeric ≈ quantity
    Returns list of sorted x positions (column boundaries).
    """
    numeric_positions = []

    for line in lines:
        xs = []
        for tok in line:
            if parse_numeric(tok["text"]) is not None:
                xs.append(tok["bbox"][0])
        if xs:
            numeric_positions.append(xs)

    if not numeric_positions:
        return []

    # Flatten all numeric token x positions
    all_xs = np.array([x for line in numeric_positions for x in line])

    # Use k-means logic via quantiles → 3 numeric columns expected
    # (Qty / Rate / Amount)
    try:
        q1 = np.quantile(all_xs, 0.33)
        q2 = np.quantile(all_xs, 0.66)
        return [q1, q2]
    except:
        return []


# -------------------------------------------------------------------
# Row parsing
# -------------------------------------------------------------------

def extract_from_line(line: List[Dict[str, Any]], col_boundaries: List[int]) -> Dict[str, Any]:
    """
    Given a line of tokens and inferred column boundaries,
    extract (name, qty, rate, amount).
    """

    words = [tok["text"] for tok in line]
    full_text = " ".join(words).strip()

    # If no numeric value at all → not an item
    numeric_vals = [parse_numeric(w) for w in words]
    numeric_clean = [n for n in numeric_vals if n is not None]
    if not numeric_clean:
        return None

    # Assign columns based on X positions:
    qty_val, rate_val, amt_val = None, None, None
    name_tokens = []

    for tok in line:
        txt = tok["text"]
        num = parse_numeric(txt)
        x = tok["bbox"][0]

        if num is None:
            name_tokens.append(txt)
        else:
            # Decide whether token falls in qty, rate, or amount column
            if not col_boundaries:
                # Fallback: last numeric value is amount
                amt_val = num
            else:
                if x < col_boundaries[0]:
                    qty_val = num
                elif x < col_boundaries[1]:
                    rate_val = num
                else:
                    amt_val = num

    # If no amount detected, fallback to last numeric
    if amt_val is None and numeric_clean:
        amt_val = numeric_clean[-1]

    # Normalize name
    item_name = " ".join(name_tokens).strip()

    if len(item_name) < 2:
        return None

    return {
        "item_name": item_name,
        "item_quantity": round(float(qty_val), 2) if qty_val is not None else None,
        "item_rate": round(float(rate_val), 2) if rate_val is not None else None,
        "item_amount": round(float(amt_val), 2) if amt_val is not None else None
    }


# -------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------

def extract_line_items(tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Main entry point:
    - Groups tokens into lines
    - Infers columns
    - Parses each line into an item
    - Removes section headers & totals
    """
    lines = group_tokens_into_lines(tokens)

    # Infer columns
    col_boundaries = infer_column_boundaries(lines)

    extracted = []

    for line in lines:
        words = [tok["text"] for tok in line]
        full_line = " ".join(words).strip()

        # Skip section headers
        if is_section_header(full_line):
            continue

        # Skip totals/subtotals
        if is_total_line(full_line):
            continue

        item = extract_from_line(line, col_boundaries)
        if item is None:
            continue

        # Must have amount to be valid
        if item["item_amount"] is None:
            continue

        extracted.append(item)

    return extracted
