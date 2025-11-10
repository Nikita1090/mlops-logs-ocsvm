from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from db import engine
import os

app = FastAPI(title="Storage Service")

@app.on_event("startup")
def startup():
    with engine.begin() as conn:
        script_path = os.path.join(os.path.dirname(__file__), "alembic_init.sql")
        with open(script_path, "r", encoding="utf-8") as f:
            conn.execute(text(f.read()))

class BGLLogIn(BaseModel):
    line_id: int
    alert_tag: str
    is_alert: bool
    raw: str
    message: str

@app.get("/health")
def health():
    return {"status": "ok"}

# --- BGL CRUD ---

@app.post("/bgl/logs")
def create_bgl_log(item: BGLLogIn):
    with engine.begin() as conn:
        res = conn.execute(
            text("""INSERT INTO bgl_logs (line_id, alert_tag, is_alert, raw, message)
                    VALUES (:lid, :tag, :ia, :raw, :msg) RETURNING id"""),
            {"lid": item.line_id, "tag": item.alert_tag, "ia": item.is_alert,
             "raw": item.raw, "msg": item.message}
        )
        return {"id": res.scalar_one()}

@app.post("/bgl/logs/bulk")
def create_bgl_bulk(items: list[BGLLogIn]):
    if not items:
        return {"inserted": 0}
    with engine.begin() as conn:
        params = [
            {"lid": it.line_id, "tag": it.alert_tag, "ia": it.is_alert,
             "raw": it.raw, "msg": it.message}
            for it in items
        ]
        conn.execute(
            text("""INSERT INTO bgl_logs (line_id, alert_tag, is_alert, raw, message)
                    VALUES (:lid, :tag, :ia, :raw, :msg)"""),
            params
        )
        return {"inserted": len(items)}

@app.get("/bgl/logs/{bid}")
def get_bgl_log(bid: int):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM bgl_logs WHERE id=:id"), {"id": bid}).mappings().first()
        if not row:
            raise HTTPException(404, "Not found")
        return dict(row)

@app.get("/bgl/logs")
def list_bgl_logs(limit: int = 100, offset: int = 0, only_non_alert: bool = False):
    with engine.begin() as conn:
        if only_non_alert:
            sql = "SELECT * FROM bgl_logs WHERE is_alert=false ORDER BY id LIMIT :lim OFFSET :off"
        else:
            sql = "SELECT * FROM bgl_logs ORDER BY id LIMIT :lim OFFSET :off"
        rows = conn.execute(text(sql), {"lim": limit, "off": offset}).mappings().all()
        return [dict(r) for r in rows]

# --- Модели (оставляем как было) ---

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

