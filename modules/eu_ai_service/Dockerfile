FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Using transformers for classification with pinned CPU-only torch
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn==0.34.0 \
    transformers==4.48.2 \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu

# Create directory for model cache
RUN mkdir -p /app/model_cache
ENV TRANSFORMERS_CACHE=/app/model_cache

COPY . .

# Download model during build to bake it into image
# Baking a smaller distilled model to reduce image size.
RUN python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='valhalla/distilbart-mnli-12-1')"

EXPOSE 8000

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
