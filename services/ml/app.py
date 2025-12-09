import os
from typing import List

import numpy as np
import scipy.sparse as sp
import requests

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, ConfigDict
from config import load_config
from ml_core import OCSVMModel, OCSVMModelRaw


_cfg = load_config() if os.path.exists(os.environ.get("CONFIG_PATH", "/app/configs/ml.yaml")) else {}

TFIDF_CFG = _cfg.get("tfidf", {
    "max_features": 5000,
    "ngram_range": [1, 1],
    "min_df": 1,
    "max_df": 1.0,
    "lowercase": False,
    "token_pattern": r"(?u)\b\w+\b",
})
OCSVM_CFG = _cfg.get("ocsvm", {
    "kernel": "rbf",
    "gamma": "scale",
    "nu": 0.05,
})
MODEL_DIR = _cfg.get("model_dir", "/app/models")
MODEL_NAME_TXT = _cfg.get("model_name", "ocsvm_text.joblib")

app = FastAPI(title="ML Service (vectors-friendly)")

STORAGE_URL = os.environ.get("STORAGE_URL", "http://storage:8002")

# Оставлена ради совместимости, нодо будет снести потом
MODEL_TXT = OCSVMModel(TFIDF_CFG, OCSVM_CFG, MODEL_DIR, MODEL_NAME_TXT)

MODEL_VEC = OCSVMModelRaw(OCSVM_CFG, MODEL_DIR, "ocsvm_raw_vectors.joblib")


class SparseVector(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dim: int = Field(..., ge=1)
    indices: List[int]
    values: List[float]

    @field_validator("indices")
    @classmethod
    def _indices_int(cls, v):
        return [int(x) for x in v]

    @field_validator("values")
    @classmethod
    def _values_float(cls, v):
        vals = [float(x) for x in v]
        for x in vals:
            if not np.isfinite(x):
                raise ValueError("values contain non-finite numbers")
        return vals


class TrainVectorsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vectors: List[SparseVector]


class PredictVectorsRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vectors: List[SparseVector]


def to_csr(vectors: List[SparseVector]):
    if not vectors:
        raise HTTPException(400, "vectors is empty")
    dim = vectors[0].dim
    indptr = [0]
    indices = []
    data = []
    for i, v in enumerate(vectors):
        if v.dim != dim:
            raise HTTPException(400, f"all vectors must share the same dim (got {v.dim} vs {dim} at row {i})")
        if len(v.indices) != len(v.values):
            raise HTTPException(400, f"indices/values length mismatch at row {i}")
        for idx in v.indices:
            if idx < 0 or idx >= dim:
                raise HTTPException(400, f"index {idx} out of bounds [0,{dim}) at row {i}")
        indices.extend(v.indices)
        data.extend(v.values)
        indptr.append(indptr[-1] + len(v.indices))
    X = sp.csr_matrix(
        (np.array(data, dtype=float), np.array(indices, dtype=int), np.array(indptr, dtype=int)),
        shape=(len(vectors), dim)
    )
    return X


def _register_model(name: str, version: str, path: str, notes: str = ""):
    try:
        requests.post(
            f"{STORAGE_URL}/models",
            params={"name": name, "version": version, "path": path, "metric_aupr": 0.0, "notes": notes},
            timeout=5,
        )
    except Exception:
        pass



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/summary")
def summary():
    exists_txt = os.path.exists(MODEL_TXT.model_path)
    exists_vec = os.path.exists(MODEL_VEC.model_path)
    return {
        "text_model_path": MODEL_TXT.model_path,
        "text_exists": exists_txt,
        "vec_model_path": MODEL_VEC.model_path,
        "vec_exists": exists_vec,
    }


# ТЕКСТЫ (совместимость)
class TrainText(BaseModel):
    texts: List[str]


class PredictText(BaseModel):
    texts: List[str]


@app.post("/train")
def train_text(req: TrainText):
    if not req.texts:
        raise HTTPException(400, "texts is empty")
    stats = MODEL_TXT.fit(req.texts)
    path = MODEL_TXT.save()
    _register_model("ocsvm_tfidf", "v1", path, "trained on texts")
    return {"status": "trained", "path": path, "stats": stats}


@app.post("/predict")
def predict_text(req: PredictText):
    if not req.texts:
        raise HTTPException(400, "texts is empty")
    try:
        MODEL_TXT.load()
    except Exception:
        raise HTTPException(400, "model (text) not trained yet")
    labels, scores = MODEL_TXT.predict(req.texts)
    return {"labels": labels, "scores": scores}


# ВЕКТОРА
@app.post("/train_vectors")
async def train_vectors(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    if isinstance(body, list):
        payload = {"vectors": body}
    elif isinstance(body, dict) and "vectors" in body:
        payload = body
    else:
        raise HTTPException(400, "Body must be a list of vectors or an object with 'vectors' key")

    try:
        req = TrainVectorsRequest(**payload)
    except Exception as e:
        raise HTTPException(422, f"Invalid payload for vectors: {e}")

    X = to_csr(req.vectors)
    stats = MODEL_VEC.fit(X)
    path = MODEL_VEC.save()
    _register_model("ocsvm_vectors", "v1", path, "trained on sparse vectors")
    return {"status": "trained", "path": path, "stats": stats}


@app.post("/predict_vectors")
async def predict_vectors(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    if isinstance(body, list):
        payload = {"vectors": body}
    elif isinstance(body, dict) and "vectors" in body:
        payload = body
    else:
        raise HTTPException(400, "Body must be a list of vectors or an object with 'vectors' key")

    try:
        req = PredictVectorsRequest(**payload)
    except Exception as e:
        raise HTTPException(422, f"Invalid payload for vectors: {e}")

    try:
        MODEL_VEC.load()
    except Exception:
        raise HTTPException(400, "model (vectors) not trained yet")

    X = to_csr(req.vectors)
    labels, scores = MODEL_VEC.predict(X)
    return {"labels": labels, "scores": scores}

