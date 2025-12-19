from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
import logging
import threading

app = FastAPI(title="Presidio PII Service")

# Lazy-initialized engines to avoid model downloads at build/start time
analyzer = None
anonymizer = None
_engine_lock = threading.Lock()
logger = logging.getLogger(__name__)

# Configuration reused for activation
NLP_CONFIG = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
}
MODEL_NAME = "en_core_web_sm"

class AnalyzeRequest(BaseModel):
    text: str
    language: str = "en"

def _ensure_engines_loaded():
    """
    Idempotent initializer that loads spaCy model and Presidio engines.
    Model is baked into the image, so no network access is required here.
    """
    global analyzer, anonymizer
    if analyzer is not None and anonymizer is not None:
        return True

    with _engine_lock:
        if analyzer is not None and anonymizer is not None:
            return True
        try:
            provider = NlpEngineProvider(nlp_configuration=NLP_CONFIG)
            nlp_engine = provider.create_engine()
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            anonymizer = AnonymizerEngine()
            logger.info("Presidio engines initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Presidio engines: {e}")
            return False


@app.on_event("startup")
def startup_load():
    _ensure_engines_loaded()


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health_check():
    return {"status": "ok", "activated": analyzer is not None}


@app.post("/activate")
def activate():
    """
    Admin-triggered activation that initializes Presidio engines.
    Safe to call multiple times; no network downloads are performed because the model is baked into the image.
    """
    if analyzer is not None and anonymizer is not None:
        return {"activated": True, "already_loaded": True}

    if _ensure_engines_loaded():
        return {"activated": True, "downloaded": False}

    raise HTTPException(status_code=500, detail="Failed to initialize Presidio engines")

@app.post("/analyze")
def analyze_text(request: AnalyzeRequest):
    if analyzer is None or anonymizer is None:
        raise HTTPException(status_code=503, detail="Module not activated. Please call /activate to download and load the model.")

    try:
        # Analyze
        results = analyzer.analyze(text=request.text, language=request.language)
        
        # Format results
        entities = []
        for res in results:
            entities.append({
                "type": res.entity_type,
                "start": res.start,
                "end": res.end,
                "score": res.score
            })
            
        return {
            "found_pii": len(entities) > 0,
            "entities": entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
