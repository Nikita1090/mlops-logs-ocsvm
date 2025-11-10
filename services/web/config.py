import os, yaml

def load_config():
    path = os.environ.get("CONFIG_PATH", "/app/configs/web.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

