from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import requests, os, time
from jinja2 import Template
from config import load_config

cfg = load_config()
app = FastAPI(title="Web Master (vectors)")

COLLECTOR_URL = cfg["services"]["collector"]
STORAGE_URL   = cfg["services"]["storage"]
ML_URL        = cfg["services"]["ml"]
REPORT_DIR    = cfg["report_dir"]
os.makedirs(REPORT_DIR, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/scenario/collect_templates")
def collect_templates():
    r = requests.post(f"{COLLECTOR_URL}/build", timeout=7200)
    r.raise_for_status()

    h = requests.get(f"{COLLECTOR_URL}/health", timeout=60).json()
    meta = h.get("meta", {})
    built = h.get("built", False)
    return {
        "status": "built" if built else "unknown",
        "collector_meta": meta,
        "collector_dataset": h.get("dataset_path"),
    }

@app.post("/scenario/collect_vectors_batch")
def collect_vectors_batch(offset: int = 0, limit: int = 2000):

    r = requests.get(f"{COLLECTOR_URL}/collect_vectors",
                     params={"offset": offset, "limit": limit},
                     timeout=7200)
    r.raise_for_status()
    payload = r.json()
    vectors = payload.get("data", [])
    fetched = len(vectors)

    if fetched == 0:
        return {"inserted": 0, "fetched": 0, "offset": offset, "limit": limit}


    rb = requests.post(f"{STORAGE_URL}/bgl/vectors/bulk", json=vectors, timeout=7200)
    rb.raise_for_status()
    inserted = rb.json().get("inserted", 0)

    return {
        "inserted": inserted,
        "fetched": fetched,
        "offset": offset,
        "limit": limit
    }

@app.post("/scenario/train_model_vectors")
def train_model_vectors(n: int = 50000):
    rows = requests.get(f"{STORAGE_URL}/bgl/vectors",
                        params={"limit": n, "offset": 0, "only_non_alert": True},
                        timeout=7200).json()
    if not rows:
        raise HTTPException(400, "Нет non-alert векторов для обучения")

    vectors = [{"dim": r["dim"], "indices": r["indices"], "values": r["values"]} for r in rows]
    r = requests.post(f"{ML_URL}/train_vectors", json={"vectors": vectors}, timeout=7200)
    r.raise_for_status()
    return r.json()


@app.post("/scenario/infer_last_vectors")
def infer_last_vectors(n: int = 1000):
    rows = requests.get(f"{STORAGE_URL}/bgl/vectors",
                        params={"limit": n, "offset": 0, "only_non_alert": False},
                        timeout=7200).json()
    if not rows:
        raise HTTPException(400, "Нет векторов для инференса")

    vectors = [{"dim": r["dim"], "indices": r["indices"], "values": r["values"]} for r in rows]
    r = requests.post(f"{ML_URL}/predict_vectors", json={"vectors": vectors}, timeout=7200)
    r.raise_for_status()
    return {"prediction": r.json(), "requested": n, "received": len(rows)}


@app.get("/scenario/report", response_class=FileResponse)
def report():
    models = requests.get(f"{STORAGE_URL}/models", timeout=30).json()
    summary = requests.get(f"{ML_URL}/summary", timeout=30).json()
    template_str = """
    <html>
    <head><meta charset="utf-8"><title>OCSVM Report (BGL, vectors)</title></head>
    <body>
      <h1>Отчёт: One-Class SVM на векторизованных шаблонах</h1>
      <h2>Состояние моделей</h2>
      <ul>
        <li>Text model: {{ text_model_path }} (exists={{ text_exists }})</li>
        <li>Vector model: {{ vec_model_path }} (exists={{ vec_exists }})</li>
      </ul>
      <h2>Зарегистрированные модели</h2>
      <ul>
      {% for m in models %}
        <li>{{ m.id }} | {{ m.name }} | {{ m.version }} | {{ m.path }} | AUPR={{ m.metric_aupr }}</li>
      {% endfor %}
      </ul>
      <p>Генерация: {{ ts }}</p>
      <p>Примечание: шаблоны и IDF собирает C++-сборщик; обучение и инференс работают на разрежённых векторах.</p>
    </body>
    </html>
    """
    html = Template(template_str).render(
        text_model_path=summary.get("text_model_path"),
        text_exists=summary.get("text_exists"),
        vec_model_path=summary.get("vec_model_path"),
        vec_exists=summary.get("vec_exists"),
        models=models,
        ts=time.ctime()
    )
    out_path = os.path.join(REPORT_DIR, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return FileResponse(out_path, media_type="text/html", filename="report.html")

