# 🏥 Bill Extraction API  
**Automated Line-Item Extraction & Reconciliation for Health Insurance Invoices**

This project implements an end-to-end solution for extracting **line items**, **item quantities**, **rates**, **amounts**, and **reconciled totals** from medical bills, pharmacy invoices, and hospital charge sheets. It is built according to the requirements of the Bajaj HackRx Datathon.

---

## 📌 Problem Statement

Medical insurance claim bills often come as large multi-page PDFs or scanned images.  
Each bill may contain multiple tables and section headers (Consultation, Pharmacy, Investigations, Radiology, OT Charges, etc.).

### The task:
- Extract **every valid line item** from the bill.
- Avoid **missing items** and **avoid double-counting**.
- Identify & ignore **section headers** and **subtotals**.
- Compute:
  - `pagewise_line_items`
  - `total_item_count`
  - `reconciled_amount`

The extracted total should be as close as possible to the true bill amount.

---

## 🚀 Solution Overview

This project provides a **FastAPI-based inference server** that performs:

### 1️⃣ Document Loading  
Supports:
- Remote URLs  
- PDF or image files  
- Multi-page extraction  

### 2️⃣ OCR (Optical Character Recognition)  
Uses **Tesseract** to extract:
- Word tokens  
- Bounding boxes  
- Line grouping metadata  
- Confidence scores  

### 3️⃣ Parsing & Table Reconstruction  
A custom logic reconstructs invoice rows via:
- Token → line grouping  
- Column boundary inference  
- Extraction of:
  - Item Name  
  - Quantity  
  - Rate  
  - Amount (rightmost numeric value)  

### 4️⃣ Post-processing  
Ensures high-accuracy extraction:
- Removes **subtotals** & **section headers**  
- Deduplicates rows using **fuzzy matching**  
- Normalizes numbers  
- Computes:
  - `total_item_count`  
  - `reconciled_amount`  

### 5️⃣ Standardized API Output  
JSON response exactly as required:

```json
{
  "is_success": true,
  "data": {
    "pagewise_line_items": [...],
    "total_item_count": 30,
    "reconciled_amount": 21800.0
  }
}
