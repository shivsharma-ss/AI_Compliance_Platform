FROM python:3.9-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/.cache/huggingface \
    HF_HUB_CACHE=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary --extra-index-url https://download.pytorch.org/whl/cpu \
    numpy==1.25.2 \
    torch==2.2.2 \
    detoxify \
    fastapi \
    uvicorn && \
    pip check

# Pre-download model into the image to avoid Cloud Run cold-start downloads
RUN mkdir -p "${HF_HOME}" && python - <<'PY'
from detoxify import Detoxify
Detoxify('original')
PY
RUN \
    # verify cache exists at build time (helpful for troubleshooting)
    ls -la "${HF_HOME}" || true

# Copy app code
COPY . .

# Expose port
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
