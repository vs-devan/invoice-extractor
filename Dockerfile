# -----------------------------
# Base image
# -----------------------------
FROM python:3.10-slim

# -----------------------------
# Install system dependencies
# -----------------------------
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Working directory inside container
# -----------------------------
WORKDIR /app

# -----------------------------
# Copy requirements first (for caching)
# -----------------------------
COPY requirements.txt .

# -----------------------------
# Install Python dependencies
# -----------------------------
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy the entire project
# -----------------------------
COPY . .

# -----------------------------
# Expose API port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Start FastAPI (correct module path!)
# -----------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
