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
# Check final arithmetic validity with monetary guards
# -------------------------------------------------
def valid_item_entry(item):
    """
    Validate item with strict checks against interpretation errors.
    Guards against date/time/ID fields being misclassified as items.
    """
    qty = item["item_quantity"]
    rate = item["item_rate"]
    amount = item["item_amount"]
    name = item["item_name"].lower()

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

    # ========== GUARD: Reject date-like patterns in item name ==========
    # Prevent Invoice Date, Invoice Time, etc. from being items
    date_patterns = [
        r'\b20\d{2}\b',              # Year: 2020, 2021, etc.
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}',  # Date: 01/02/2021
        r'\b\d{1,2}:\d{2}:\d{2}\b',  # Time: 14:30:00
        r'\b\d{1,2}:\d{2}\b',        # Time: 14:30
        r'\binvoice\s*date\b',
        r'\binvoice\s*time\b',
        r'\binvoice\s*#',
        r'\binvoice\s*id\b',
        r'\breference\s*#',
        r'\bdocument\s*#',
    ]
    
    for pattern in date_patterns:
        if re.search(pattern, name):
            return False
    
    # ========== GUARD: Reject suspicious numeric names ==========
    # Names that are purely numbers are usually dates/IDs, not items
    if re.match(r'^[\d\-/:\.]+$', item["item_name"]):
        return False
    
    # ========== GUARD: Ensure name has meaningful text ==========
    # Filter out names with only digits and one special char (like "2021" or "123")
    if len(re.sub(r'[^A-Za-z]', '', item["item_name"])) < 2:
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
    
    GUARDS AGAINST INTERPRETATION ERRORS:
    - Date fields (Invoice Date, Invoice Time) filtered
    - Invoice numbers and identifiers excluded
    - Non-monetary values rejected
    - Clear distinction between identifiers and transactional values
    """

    clean = []

    for it in items:
        # normalize name first
        it["item_name"] = normalize_name(it["item_name"])

        # ========== GUARD: Reject date/time/id patterns ==========
        name_lower = it["item_name"].lower()
        
        # Reject obvious metadata fields
        metadata_keywords = [
            "invoice", "date", "time", "ref", "id", "number", "doc",
            "bill", "patient", "doctor", "hospital", "address",
            "contact", "phone", "email"
        ]
        
        if any(keyword in name_lower for keyword in metadata_keywords):
            continue
        
        # Reject names that are purely numeric/date patterns
        if re.match(r'^[\d\-/:\.]+$', it["item_name"]):
            continue
        
        # Reject if name looks like a year/date
        if re.search(r'\b(19|20)\d{2}\b', it["item_name"]):
            continue
        
        # Reject if name contains time patterns
        if re.search(r'\d{1,2}:\d{2}', it["item_name"]):
            continue

        # reject garbage names like single characters
        if len(it["item_name"]) < 3:
            continue

        # reject numeric-only names
        if re.fullmatch(r"[0-9.]+", it["item_name"]):
            continue

        # reject rows with known non-item keywords
        keywords_to_reject = ["total", "gst", "amount", "bill", "round", "subtotal", 
                             "tax", "discount", "paid", "due", "balance", "summary",
                             "page", "statement"]
        if any(word in name_lower for word in keywords_to_reject):
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
