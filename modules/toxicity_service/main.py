from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from detoxify import Detoxify

app = FastAPI(title="Toxicity Detection Service")

# Load model on startup (this might take a moment)
# using 'original' model for balance of speed/accuracy
model = None

@app.on_event("startup")
def load_model():
    global model
    try:
        model = Detoxify('original')
    except Exception as e:
        print(f"Error loading model: {e}")

class AnalyzeRequest(BaseModel):
    text: str

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/predict")
def predict_toxicity(request: AnalyzeRequest):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
