FROM python:3.12-slim

WORKDIR /app

# System deps for lxml / Pillow / pytesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# emergentintegrations is a private package; strip it for public/docker builds (matches CI)
RUN grep -v "emergentintegrations" requirements.txt > /tmp/req.txt \
    && pip install --no-cache-dir -r /tmp/req.txt

COPY . .

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
