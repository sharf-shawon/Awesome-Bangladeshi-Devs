import json
import os
from pathlib import Path

def validate_json_file(path):
    if not os.path.exists(path):
        print(f"{path}: skipped (does not exist).")
        return True
    try:
        with open(path, "r", encoding="utf-8") as f:
            json.load(f)
        print(f"{path}: valid JSON.")
        return True
    except Exception as e:
        print(f"{path}: INVALID JSON: {e}")
        return False

def main():
    data_dir = Path(__file__).parent.parent / "data"
    files = ["users.json", "removed_users.json"]
    all_valid = True
    for fname in files:
        fpath = data_dir / fname
        if not validate_json_file(fpath):
            all_valid = False
    if not all_valid:
        exit(1)

if __name__ == "__main__":
    main()
