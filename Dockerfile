# Stage 1: Builder - Optimized for CPU-only dependencies
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
# RUN pip install --upgrade pip && \
#     pip install --no-cache-dir \
#     --extra-index-url https://download.pytorch.org/whl/cpu \
#     -r requirements.txt

RUN pip install --upgrade pip && \
    pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    fastapi \
    uvicorn \
    gunicorn \
    -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    nginx \
    supervisor \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy from builder stage (using the same name)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application files
COPY . .

# Configure services
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Create required directories
RUN mkdir -p \
    /app/static \
    /app/models \
    /var/log/nginx \
    /var/log/supervisor \
    /var/run/supervisor

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    DOCTR_CACHE_DIR=/app/models \
    EASYOCR_MODULE_PATH=/app/models/easyocr \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata \
    STATIC_FILES_DIR=/app/static

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]