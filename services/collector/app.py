from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
from config import load_config
import itertools

cfg = load_config()
app = FastAPI(title="Collector Service (BGL)")

DATASET_PATH = cfg["dataset_path"]
ENCODING = cfg.get("encoding", "utf-8")
DEFAULT_BATCH = int(cfg.get("batch_size", 1000))

class LogLine(BaseModel):
    line_id: int
    raw: str
    alert_tag: str
    is_alert: bool
    message: str

class BatchResponse(BaseModel):
    start: int
    end: int
    total: int | None
    data: List[LogLine]

@app.get("/health")
def health():
    return {"status": "ok", "dataset_path": DATASET_PATH}

def parse_bgl_line(idx: int, line: str) -> LogLine:
    s = line.rstrip("\n")
    if not s:
        return LogLine(line_id=idx, raw="", alert_tag="-", is_alert=False, message="")
    parts = s.split(maxsplit=1)
    first = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    is_alert = (first != "-")
    return LogLine(line_id=idx, raw=s, alert_tag=first, is_alert=is_alert, message=rest)

def iter_slice(path: str, start: int, stop: int):
    with open(path, "r", encoding=ENCODING, errors="replace") as f:
        for idx, line in itertools.islice(enumerate(f), start, stop):
            yield idx, line

@app.get("/collect", response_model=BatchResponse)
def collect_batch(offset: int = Query(0, ge=0), limit: int = Query(DEFAULT_BATCH, gt=0)):
    start = offset
    end = offset + limit
    items: list[LogLine] = []
    for idx, line in iter_slice(DATASET_PATH, start, end):
        items.append(parse_bgl_line(idx, line))
    return BatchResponse(start=start, end=start+len(items), total=None, data=items)

