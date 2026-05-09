import json
import os

from collect_stats import AUTOMATED_PATH, build_site_outputs, load_config


def main():
    if not os.path.exists(AUTOMATED_PATH):
        raise FileNotFoundError(f"Missing automated data file: {AUTOMATED_PATH}")

    with open(AUTOMATED_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    cfg = load_config()
    build_site_outputs(payload, cfg)
    print("site bundle generated")


if __name__ == "__main__":
    main()
