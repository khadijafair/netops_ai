import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
MODEL = joblib.load(BASE / "models/random_forest.joblib")
FEATURES = json.loads(
    (BASE / "models/features.json").read_text()
)

app = FastAPI(title="NetOps-AI ML V2")

class Metrics(BaseModel):
    neighbor_count: int = Field(ge=0)
    missing_neighbors: int = Field(ge=0)
    ospf_route_count: int = Field(ge=0)
    interface_up: int = Field(ge=0)
    ping_success: int = Field(ge=0, le=1)
    ping_latency_ms: float = Field(ge=0)

@app.get("/health")
def health():
    return {"status": "ok", "model": "random_forest_v2"}

@app.post("/predict")
def predict(metrics: Metrics):
    values = metrics.model_dump()
    frame = pd.DataFrame(
        [[values[f] for f in FEATURES]],
        columns=FEATURES,
    )
    probability = float(MODEL.predict_proba(frame)[0][1])
    return {
        "anomaly": bool(probability >= 0.5),
        "fault_probability": round(probability, 4),
        "model": "random_forest_v2",
        "status": "experimental",
    }
