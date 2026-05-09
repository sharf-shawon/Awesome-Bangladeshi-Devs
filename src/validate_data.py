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


def _norm_username(value):
    return (value or "").strip().lower().replace(".", "-")


def validate_duplicate_usernames(data_dir):
    users_path = data_dir / "users.json"
    automated_path = data_dir / "automated.json"

    users = []
    automated = []

    if users_path.exists():
        with open(users_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            users = payload if isinstance(payload, list) else []

    if automated_path.exists():
        with open(automated_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
            automated = payload.get("developers", []) if isinstance(payload, dict) else []

    all_ids = {}
    ok = True

    for entry in users:
        username = _norm_username(entry.get("github_username") or entry.get("login"))
        if not username:
            continue
        all_ids.setdefault(username, []).append("users.json")

    for entry in automated:
        username = _norm_username(entry.get("login") or entry.get("github_username"))
        if not username:
            continue
        all_ids.setdefault(username, []).append("automated.json")

    for username, sources in all_ids.items():
        if sources.count("users.json") > 1:
            print(f"Duplicate username in users.json: {username}")
            ok = False
        if sources.count("automated.json") > 1:
            print(f"Duplicate username in automated.json: {username}")
            ok = False

    return ok


def main():
    data_dir = Path(__file__).parent.parent / "data"
    files = ["users.json", "removed_users.json", "automated.json"]
    all_valid = True

    for fname in files:
        fpath = data_dir / fname
        if not validate_json_file(fpath):
            all_valid = False

    web_dir = data_dir / "web"
    if web_dir.exists():
        for fpath in web_dir.glob("*.json"):
            if not validate_json_file(fpath):
                all_valid = False

    if not validate_duplicate_usernames(data_dir):
        all_valid = False

    if not all_valid:
        exit(1)


if __name__ == "__main__":
    main()
