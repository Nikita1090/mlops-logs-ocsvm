import os, yaml

def load_config():
    path = os.environ.get("CONFIG_PATH", "/app/configs/storage.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def db_url():
    host = os.environ.get("DB_HOST", "db")
    port = os.environ.get("DB_PORT", "5432")
    user = os.environ.get("DB_USER")
    pwd  = os.environ.get("DB_PASSWORD")
    name = os.environ.get("DB_NAME")
    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{name}"

