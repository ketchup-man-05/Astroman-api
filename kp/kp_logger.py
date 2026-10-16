"""kp_logger.py - one JSON file per reading. Never lets logging break a reading."""
import os, json
from datetime import datetime, timezone

LOG_DIR = "logs"

def log_reading(record):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        num = record.get("inputs", {}).get("horary_number", "X")
        path = os.path.join(LOG_DIR, f"{ts}_{num}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, default=str)
        return path
    except Exception as e:
        print(f"[kp_logger] warning: could not write log: {e}")
        return None