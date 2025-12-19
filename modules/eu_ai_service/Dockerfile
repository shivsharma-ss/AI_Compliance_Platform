FROM python:3.9-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/app/model_cache \
    HF_HOME=/app/model_cache \
    HF_HUB_CACHE=/app/model_cache \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (CPU-only torch to keep image smaller)
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    fastapi uvicorn transformers torch==2.2.2

# Create directory for model cache
RUN mkdir -p /app/model_cache

COPY . .

# Avoid model downloads at build time (enable explicitly if you want to bake the model into the image)
ARG DOWNLOAD_MODELS=0
RUN if [ "$DOWNLOAD_MODELS" = "1" ]; then python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='facebook/bart-large-mnli')"; fi

EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
