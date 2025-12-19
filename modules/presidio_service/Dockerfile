FROM python:3.9-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PREFER_BINARY=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies (prefer binary wheels to avoid long source builds)
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary \
    numpy==1.25.2 \

    fastapi \
    uvicorn \
    presidio-analyzer \
    presidio-anonymizer \
    spacy==3.6.1 && \
    pip check

# Download spaCy English model at build time so the service is ready immediately
RUN python -m spacy download en_core_web_sm && \
    # sanity check to surface version mismatches during build
    python -c "import numpy, spacy, presidio_analyzer; print('numpy', numpy.__version__)" || true

# Copy app code
COPY . .

# Expose port
EXPOSE 8080

# Command to run (overridden by docker-compose)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
