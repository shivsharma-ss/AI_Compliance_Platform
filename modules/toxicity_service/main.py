from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from detoxify import Detoxify
import logging

app = FastAPI(title="Toxicity Detection Service")

logger = logging.getLogger(__name__)

# Load model on startup (this might take a moment)
# using 'original' model for balance of speed/accuracy
model = None

@app.on_event("startup")
def load_model():
    """
    Load the Detoxify 'original' model into the module-level `model` variable.
    
    Attempts to instantiate Detoxify('original') and assign it to the global `model`. If loading fails, prints an error message and leaves `model` unchanged.
    """
    global model
    try:
        model = Detoxify('original')
    except Exception:
        logger.exception("Error loading model")

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

@app.get("/health")
def health_check():
    """
    Report service health and whether the toxicity model is loaded.
    
    Returns:
        dict: A mapping with keys:
            - "status": the string "ok".
            - "model_loaded": `True` if the global model is initialized, `False` otherwise.
    """
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/predict")
def predict_toxicity(request: AnalyzeRequest):
    """
    Analyze the provided text for toxicity and return a boolean flag plus per-label scores.
    
    Parameters:
        request (AnalyzeRequest): Payload containing the text to analyze (request.text).
    
    Returns:
        dict: A mapping with:
            - "is_toxic" (bool): True if the predicted "toxicity" score is greater than 0.7, False otherwise.
            - "scores" (dict): Per-label scores converted to Python floats.
    
    Raises:
        HTTPException: With status 503 if the model is not initialized; with status 500 for unexpected prediction errors.
    """
    if not model:
        raise HTTPException(status_code=503, detail="Model not initialized")
    
    try:
        results = model.predict(request.text)
        # Convert numpy types to float for JSON serialization
        sanitized_results = {k: float(v) for k, v in results.items()}

        # Simple heuristic: if toxicity > 0.7, flag it
        is_toxic = sanitized_results.get('toxicity', 0) > 0.7

        return {
            "is_toxic": is_toxic,
            "scores": sanitized_results
        }
    except Exception:
        logger.exception("Toxicity prediction failed")
        raise HTTPException(status_code=500, detail="Internal server error")
