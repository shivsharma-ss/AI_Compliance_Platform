from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider

app = FastAPI(title="Presidio PII Service")

# Initialize engines
# Load NlpEngine
provider = NlpEngineProvider(nlp_configuration={
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
})
nlp_engine = provider.create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
anonymizer = AnonymizerEngine()

class AnalyzeRequest(BaseModel):
    text: str
    language: str = "en"

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
def analyze_text(request: AnalyzeRequest):
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
