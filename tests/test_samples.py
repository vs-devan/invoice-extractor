"""
tests/test_samples.py
---------------------
Automated validation for the 3 provided sample documents.

This test suite checks:
- API success response
- Correct item counts
- Correct reconciled totals
"""

import os
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)



BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

SAMPLE_1 = os.path.join(SAMPLES_DIR, "Sample Document 1.pdf")
SAMPLE_2 = os.path.join(SAMPLES_DIR, "SAmple Document 2.pdf")
SAMPLE_3 = os.path.join(SAMPLES_DIR, "Sample Document 3.pdf")


# Utility: Convert local file into a data URI
def file_to_data_uri(path: str) -> str:
    """Convert local file to a temporary HTTP server link using file:// scheme."""
    return "file://" + os.path.abspath(path)


# ---------------------------------------------------------
# Expected Values for Test Validation
# ---------------------------------------------------------

EXPECTED = {
    SAMPLE_1: {
        "count": 4,
        "amount": 1699.84
    },
    SAMPLE_2: {
        "count": 12,
        "amount": 16390.0
    },
    SAMPLE_3: {
        "count": 30,
        "amount": 21800.0
    }
}


# ---------------------------------------------------------
# Reusable test function
# ---------------------------------------------------------

def run_test(sample_path: str):
    data_uri = file_to_data_uri(sample_path)

    response = client.post(
        "/extract-bill-data",
        json={"document": data_uri}
    )

    assert response.status_code == 200, "API did not return HTTP 200"

    resp = response.json()

    assert resp["is_success"] is True, "API flagged failure"

    data = resp["data"]

    # Validate count
    assert data["total_item_count"] == EXPECTED[sample_path]["count"], \
        f"Item count mismatch for {os.path.basename(sample_path)}"

    # Validate amount
    assert abs(data["reconciled_amount"] - EXPECTED[sample_path]["amount"]) < 0.05, \
        f"Reconciled amount mismatch for {os.path.basename(sample_path)}"


# ---------------------------------------------------------
# Actual test cases
# ---------------------------------------------------------

def test_sample_1():
    run_test(SAMPLE_1)


def test_sample_2():
    run_test(SAMPLE_2)


def test_sample_3():
    run_test(SAMPLE_3)
