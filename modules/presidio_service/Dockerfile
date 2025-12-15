FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn presidio-analyzer presidio-anonymizer spacy

# Download Spacy model (Small)
RUN python -m spacy download en_core_web_sm

# Copy app code
COPY . .

# Expose port
EXPOSE 8000

# Command to run (overridden by docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
