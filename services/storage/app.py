from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from db import engine
import os, json

app = FastAPI(title="Storage Service")

@app.on_event("startup")
def startup():
    with engine.begin() as conn:
        script_path = os.path.join(os.path.dirname(__file__), "alembic_init.sql")
        with open(script_path, "r", encoding="utf-8") as f:
            conn.execute(text(f.read()))

@app.get("/health")
def health():
    return {"status": "ok"}


class VecIn(BaseModel):
    line_id: int
    alert_tag: str
    is_alert: bool
    template_id: int
    dim: int
    indices: list[int]
    values: list[float]

@app.post("/bgl/vectors")
def insert_vec(v: VecIn):
    with engine.begin() as conn:
        res = conn.execute(
            text("""INSERT INTO bgl_vectors (line_id, alert_tag, is_alert, template_id, dim, indices, values)
                    VALUES (:lid, :tag, :ia, :tid, :dim, :inds, :vals) RETURNING id"""),
            {
                "lid": v.line_id, "tag": v.alert_tag, "ia": v.is_alert,
                "tid": v.template_id, "dim": v.dim,
                "inds": json.dumps(v.indices, ensure_ascii=False),
                "vals": json.dumps(v.values)
            }
        )
        return {"id": res.scalar_one()}

@app.post("/bgl/vectors/bulk")
def insert_vec_bulk(items: list[VecIn]):
    if not items:
        return {"inserted": 0}
    rows = [{
        "lid": it.line_id, "tag": it.alert_tag, "ia": it.is_alert,
        "tid": it.template_id, "dim": it.dim,
        "inds": json.dumps(it.indices, ensure_ascii=False),
        "vals": json.dumps(it.values)
    } for it in items]
    with engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO bgl_vectors (line_id, alert_tag, is_alert, template_id, dim, indices, values)
                    VALUES (:lid, :tag, :ia, :tid, :dim, :inds, :vals)"""),
            rows
        )
    return {"inserted": len(items)}

@app.get("/bgl/vectors")
def list_vecs(limit: int = 1000, offset: int = 0, only_non_alert: bool = False):
    with engine.begin() as conn:
        if only_non_alert:
            sql = "SELECT * FROM bgl_vectors WHERE is_alert=false ORDER BY id DESC LIMIT :lim OFFSET :off"
        else:
            sql = "SELECT * FROM bgl_vectors ORDER BY id DESC LIMIT :lim OFFSET :off"
        rows = conn.execute(text(sql), {"lim": limit, "off": offset}).mappings().all()
        out = []
        for r in rows:
            d = dict(r)
            d["indices"] = json.loads(d["indices"]) if d.get("indices") else []
            d["values"]  = json.loads(d["values"]) if d.get("values") else []
            out.append(d)
        return out


@app.post("/models")
def create_model(name: str, version: str, path: str, metric_aupr: float = 0.0, notes: str = ""):
    with engine.begin() as conn:
        res = conn.execute(
            text("INSERT INTO models (name,version,path,metric_aupr,notes) VALUES (:n,:v,:p,:m,:no) RETURNING id"),
            {"n": name, "v": version, "p": path, "m": metric_aupr, "no": notes}
        )
        return {"id": res.scalar_one()}

@app.get("/models")
def list_models():
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT * FROM models ORDER BY id DESC")).mappings().all()
        return [dict(r) for r in rows]

