import re
import math

# -------------------------------------------------
# Normalize item name (clean whitespace, hyphens, etc.)
# -------------------------------------------------
def normalize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", " ", name)             # collapse multiple spaces
    name = re.sub(r"[^0-9A-Za-z()\-./ ]", "", name)  # remove weird OCR chars
    return name


# -------------------------------------------------
# Check final arithmetic validity
# -------------------------------------------------
def valid_item_entry(item):
    qty = item["item_quantity"]
    rate = item["item_rate"]
    amount = item["item_amount"]

    # basic sanity
    if qty <= 0 or qty > 500:
        return False
    if rate <= 0 or rate > 50000:
        return False
    if amount <= 0 or amount > 200000:
        return False

    # amount ≈ qty * rate check (allow small tolerance)
    if abs(amount - qty * rate) > max(5, 0.12 * amount):
        return False

    return True


# -------------------------------------------------
# Remove duplicates using a smart signature
# -------------------------------------------------
def dedupe_items(items):
    unique = []
    seen = set()

    for it in items:
        key = (
            normalize_name(it["item_name"]).lower(),
            round(it["item_quantity"], 2),
            round(it["item_rate"], 2),
            round(it["item_amount"], 2)
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(it)

    return unique


# -------------------------------------------------
# Merge items that belong to same description with multi-line names
# e.g.
#   "AMOXYCILLIN 500MG"
#   "CAPSULE"
# becomes
#   "AMOXYCILLIN 500MG CAPSULE"
# -------------------------------------------------
def merge_multiline_descriptions(items):
    merged = []

    for it in items:
        name = normalize_name(it["item_name"])
        # if shorter sub-name → merge with previous
        if len(name.split()) <= 2 and merged:
            merged[-1]["item_name"] += " " + name
        else:
            it["item_name"] = name
            merged.append(it)

    return merged


# -------------------------------------------------
# Final strict filtering pipeline
# -------------------------------------------------
def filter_items_strict(items):
    """
    Combines all strict checks to return only real, high-confidence items.
    """

    clean = []

    for it in items:
        # normalize name first
        it["item_name"] = normalize_name(it["item_name"])

        # reject garbage names like single characters
        if len(it["item_name"]) < 3:
            continue

        # reject numeric-only names
        if re.fullmatch(r"[0-9.]+", it["item_name"]):
            continue

        # reject rows with "total", "gst", etc.
        lower = it["item_name"].lower()
        if any(word in lower for word in ["total", "gst", "amount", "bill", "round"]):
            continue

        # strict final numeric validation
        if not valid_item_entry(it):
            continue

        clean.append(it)

    # merge multi-line item descriptions
    clean = merge_multiline_descriptions(clean)

    # final dedupe
    clean = dedupe_items(clean)

    return clean
