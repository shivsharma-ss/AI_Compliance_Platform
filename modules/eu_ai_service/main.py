from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import threading

app = FastAPI(title="EU AI Act Compliance Service")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model state: lazy-loaded on admin activation to avoid downloads at build/start time
classifier = None
model_loaded = False
_model_lock = threading.Lock()

# Simple fallback heuristic mapping keywords to candidate labels
KEYWORD_MAP = {
    "social": "social scoring or social credit system",
    "credit": "social scoring or social credit system",
    "facial": "facial recognition or biometric surveillance",
    "biometric": "facial recognition or biometric surveillance",
    "infrastructure": "critical infrastructure control",
    "education": "educational testing or grading",
    "exam": "educational testing or grading",
    "job": "employment screening or job application",
    "applicant": "employment screening or job application",
}

class AnalyzeRequest(BaseModel):
    text: str

# Define Risk Categories based on EU AI Act
CANDIDATE_LABELS = [
    "social scoring or social credit system", 
    "facial recognition or biometric surveillance", 
    "critical infrastructure control", 
    "educational testing or grading", 
    "employment screening or job application",
    "general assistance or information request"
]

RISK_MAPPING = {
    "social scoring or social credit system": "UNACCEPTABLE",
    "facial recognition or biometric surveillance": "UNACCEPTABLE",
    "critical infrastructure control": "HIGH",
    "educational testing or grading": "HIGH",
    "employment screening or job application": "HIGH",
    "general assistance or information request": "MINIMAL"
}

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model_loaded, "fallback": (not model_loaded)}


@app.post("/activate")
def activate_model():
    """
    Admin-triggered activation to download/load the transformer model.
    Safe to call multiple times; subsequent calls are no-ops once loaded.
    """
    global classifier, model_loaded

    if model_loaded and classifier is not None:
        return {"activated": True, "already_loaded": True}

    with _model_lock:
        if model_loaded and classifier is not None:
            return {"activated": True, "already_loaded": True}

        try:
            from transformers import pipeline  # local import to allow graceful fallback

            # This will download the model on first activation (respects TRANSFORMERS_CACHE)
            classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
            model_loaded = True
            logger.info("Model downloaded and loaded via /activate.")
            return {"activated": True, "downloaded": True}
        except Exception as e:
            logger.error(f"Failed to activate model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to activate model: {e}")

@app.post("/analyze_risk")
def analyze_risk(request: AnalyzeRequest):
    text = request.text or ""

    # If we have the transformer-based classifier, use it
    if model_loaded and classifier is not None:
        try:
            result = classifier(text, CANDIDATE_LABELS)
            top_label = result['labels'][0]
            score = float(result['scores'][0])
            risk_level = RISK_MAPPING.get(top_label, "UNKNOWN")
            if score < 0.6:
                risk_level = "MINIMAL"
                top_label = "uncertain (low confidence)"

            return {"risk_level": risk_level, "category": top_label, "confidence": score}
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # Fallback heuristic classifier
    lower = text.lower()
    matched_label = None
    for k, label in KEYWORD_MAP.items():
        if k in lower:
            matched_label = label
            break

    if not matched_label:
        matched_label = "general assistance or information request"
        confidence = 0.5
    else:
        confidence = 0.75

    risk_level = RISK_MAPPING.get(matched_label, "UNKNOWN")
    return {"risk_level": risk_level, "category": matched_label, "confidence": confidence}
