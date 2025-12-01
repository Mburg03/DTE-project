import os, json

def _ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def load_processed(path: str):
    seen = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    seen.add(obj.get("key"))
                except Exception:
                    pass
    return seen

def append_processed(path: str, keys: list):
    if not keys: return
    _ensure_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        for k in keys:
            f.write(json.dumps({"key": k}) + "\n")
