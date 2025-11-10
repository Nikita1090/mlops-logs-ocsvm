FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py db.py models.py alembic_init.sql config.py ./
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]

