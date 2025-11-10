import os
import subprocess
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from config import load_config
from tfidf_vec import TFIDFStore, load_templates_csv

cfg = load_config()
app = FastAPI(title="Collector CPP + TFIDF")

LOG_DIR = cfg.get("log_dir", "/app/data/BGL")
OUT_DIR = cfg.get("out_dir", "/app/data/BGL/out")
DATASET_FILE = cfg.get("dataset_file", "/app/data/BGL/BGL.log")
ENCODING = cfg.get("encoding", "utf-8")
TFIDF_PARAMS = cfg.get("tfidf", {})

BIN_PATH = "/app/aggregator"

class VectorRow(BaseModel):
    templ_id: int
    template: str
    vector: List[float]

class VectorBatch(BaseModel):
    start: int
    end: int
    total: int
    dim: int
    rows: List[VectorRow]

@app.get("/health")
def health():
    return {"status": "ok", "log_dir": LOG_DIR, "out_dir": OUT_DIR}

@app.post("/collect_templates")
def collect_templates():
    os.makedirs(OUT_DIR, exist_ok=True)
    # агрегатор читает *.log из LOG_DIR
    try:
        r = subprocess.run([BIN_PATH, LOG_DIR, OUT_DIR], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"aggregator error: {e.stderr}")
    dict_path = os.path.join(OUT_DIR, "dict_templ.csv")
    if not os.path.exists(dict_path):
        raise HTTPException(500, "dict_templ.csv not found after aggregation")
    df = load_templates_csv(dict_path)
    return {"templates": len(df), "dict_path": dict_path}

@app.get("/collect_vectors", response_model=VectorBatch)
def collect_vectors(offset: int = Query(0, ge=0), limit: int = Query(1000, gt=0)):
    dict_path = os.path.join(OUT_DIR, "dict_templ.csv")
    if not os.path.exists(dict_path):
        raise HTTPException(400, "Run /collect_templates first")
    df = load_templates_csv(dict_path)
    total = len(df)

    store = TFIDFStore(OUT_DIR, TFIDF_PARAMS)
    status = store.fit_or_load(df["template"].tolist())

    start = min(offset, total)
    end = min(offset + limit, total)
    sl = df.iloc[start:end]

    X = store.transform(sl["template"].tolist())
    dim = X.shape[1]
    rows: List[VectorRow] = []
    # преобразуем в плотный (для простоты передачи) — ок для батчей
    for templ_id, templ, row in zip(sl["id"].tolist(), sl["template"].tolist(), X.toarray()):
        rows.append(VectorRow(templ_id=templ_id, template=templ, vector=row.astype(float).tolist()))
    return VectorBatch(start=start, end=end, total=total, dim=dim, rows=rows)

