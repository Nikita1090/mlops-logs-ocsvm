from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List
import os, json, itertools, subprocess
from config import load_config


cfg = load_config()
app = FastAPI(title="Collector C++ (Templates + TF-IDF)")


DATASET_PATH = cfg["dataset_path"]
ENCODING     = cfg.get("encoding", "utf-8")
OUT_DIR      = cfg.get("out_dir", "/app/out")
BATCH_SIZE   = int(cfg.get("batch_size", 1000))


BIN_PATH = "/app/bin/bgl_template_miner"
META_PATH = os.path.join(OUT_DIR, "meta.json")
TPL_PATH  = os.path.join(OUT_DIR, "templates.json")
VEC_PATH  = os.path.join(OUT_DIR, "vectors.jsonl")


class VectorItem(BaseModel):
    line_id: int
    alert_tag: str
    is_alert: bool
    template_id: int
    dim: int
    indices: List[int]
    values: List[float]

class BatchVectors(BaseModel):
    start: int
    end: int
    total: int | None
    data: List[VectorItem]


def ensure_built():
    """
    Гарантируем, что артефакты (templates.json, meta.json, vectors.jsonl) собраны.
    Если их нет — запускаем: /app/bin/bgl_template_miner <in_log> <encoding> <out_dir>
    """
    if not (os.path.exists(VEC_PATH) and os.path.exists(META_PATH) and os.path.exists(TPL_PATH)):
        os.makedirs(OUT_DIR, exist_ok=True)
        cmd = [BIN_PATH, DATASET_PATH, ENCODING, OUT_DIR]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(status_code=500, detail=f"C++ builder failed: {e}")

def read_meta():
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def iter_slice(path: str, start: int, stop: int):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for idx, line in itertools.islice(enumerate(f), start, stop):
            yield idx, line


@app.get("/health")
def health():
    built = os.path.exists(VEC_PATH) and os.path.exists(META_PATH) and os.path.exists(TPL_PATH)
    meta = {}
    if built:
        try:
            meta = read_meta()
        except Exception:
            meta = {}
    return {
        "status": "ok",
        "built": built,
        "dataset_path": DATASET_PATH,
        "meta": meta
    }

@app.post("/build")
def build():
    ensure_built()
    h = health()
    return {"status": "built", "meta": h.get("meta", {}), "dataset_path": h.get("dataset_path")}

@app.get("/collect_vectors", response_model=BatchVectors)
def collect_vectors(offset: int = Query(0, ge=0), limit: int = Query(BATCH_SIZE, gt=0)):
    """
    Возвращает батч векторизованных событий
    При первом вызове соберёт артефакты
    """
    ensure_built()
    items: list[VectorItem] = []

    for _, line in iter_slice(VEC_PATH, offset, offset + limit):
        line = line.rstrip("\r\n")
        if not line:
            continue
        obj = json.loads(line)
        items.append(VectorItem(**obj))

    total = None
    try:
        total = read_meta().get("num_docs")
    except Exception:
        total = None

    return BatchVectors(
        start=offset,
        end=offset + len(items),
        total=total,
        data=items
    )

