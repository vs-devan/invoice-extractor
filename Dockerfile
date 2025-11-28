# ---------------------------------------------------------
# Base Python Image
# ---------------------------------------------------------
FROM python:3.9-slim

# ---------------------------------------------------------
# Install System Dependencies
# ---------------------------------------------------------
# poppler-utils -> required for pdf2image
# tesseract-ocr -> OCR engine
# tesseract-ocr-eng -> English OCR model
# libgl1 -> needed by pillow on some systems
# ---------------------------------------------------------
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libgl1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV OMP_THREAD_LIMIT=1

# ---------------------------------------------------------
# Set Work Directory
# ---------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------
# Copy Requirements & Install
# ---------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------
# Copy Application Code
# ---------------------------------------------------------
COPY app ./app

# ---------------------------------------------------------
# Expose FastAPI Port
# ---------------------------------------------------------
EXPOSE 8000

# ---------------------------------------------------------
# Create Non-Root User (Best Practice)
# ---------------------------------------------------------
RUN useradd -m appuser
USER appuser

# ---------------------------------------------------------
# Start FastAPI Server
# ---------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
