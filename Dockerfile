# -----------------------------
# Base image (lightweight Ubuntu)
# -----------------------------
FROM python:3.9-slim

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
# Set working directory
# -----------------------------
WORKDIR /app

# -----------------------------
# Copy requirements
# -----------------------------
COPY requirements.txt .

# -----------------------------
# Install Python dependencies
# -----------------------------
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy the application
# -----------------------------
COPY . .

# -----------------------------
# Expose port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Start the FastAPI server
# -----------------------------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
