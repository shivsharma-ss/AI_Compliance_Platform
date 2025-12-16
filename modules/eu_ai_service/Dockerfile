FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Using transformers for classification
RUN pip install --no-cache-dir fastapi uvicorn transformers torch

# Create directory for model cache
RUN mkdir -p /app/model_cache
ENV TRANSFORMERS_CACHE=/app/model_cache

COPY . .

# Download model during build to bake it into image
# Using a small zero-shot model or similar. For MVP, we might rely on dynamic download or bake it.
# Baking a small model:
RUN python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='facebook/bart-large-mnli')"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
