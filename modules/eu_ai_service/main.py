from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
import logging

app = FastAPI(title="EU AI Act Compliance Service")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize model
# Zero-shot classification is powerful for this "open ended" categorization
try:
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    classifier = None

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
    """
    Report service health and whether the classification model is loaded.
    
    Returns:
        dict: {
            "status": "ok",           # str: indicates service is responsive
            "model_loaded": bool      # True if the classifier is initialized, False otherwise
        }
    """
    return {"status": "ok", "model_loaded": classifier is not None}

@app.post("/analyze_risk")
def analyze_risk(request: AnalyzeRequest):
    """
    Analyze the input text and assign an EU AI Act risk level and category.
    
    Parameters:
        request (AnalyzeRequest): Request object containing the `text` to classify.
    
    Returns:
        dict: A mapping with keys:
            - "risk_level": mapped risk level string (e.g., "UNACCEPTABLE", "HIGH", "MINIMAL", or "UNKNOWN"),
            - "category": top predicted category or "uncertain (low confidence)" if confidence is low,
            - "confidence": numeric confidence score for the top prediction.
    
    Raises:
        HTTPException: with status 503 if the classification model is not loaded.
        HTTPException: with status 500 if a prediction error occurs.
    """
    if not classifier:
        raise HTTPException(status_code=503, detail="Model not ready")
        
    try:
        # Perform classification
        result = classifier(request.text, CANDIDATE_LABELS)
        
        # Get top prediction
        top_label = result['labels'][0]
        score = result['scores'][0]
        
        # Determine Risk Level
        risk_level = RISK_MAPPING.get(top_label, "UNKNOWN")
        
        # Threshold check (only flag if confident)
        if score < 0.6:
            risk_level = "MINIMAL"
            top_label = "uncertain (low confidence)"

        return {
            "risk_level": risk_level,
            "category": top_label,
            "confidence": score
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))