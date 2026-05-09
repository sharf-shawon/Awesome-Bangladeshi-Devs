import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
ENRICHED_JSON = os.path.join(DATA_DIR, "users-enriched.json")
SEARCH_INDEX_JSON = os.path.join(DATA_DIR, "search-index.json")

def main():
    if not os.path.exists(ENRICHED_JSON):
        print(f"Enriched data not found at {ENRICHED_JSON}")
        return

    with open(ENRICHED_JSON, "r", encoding="utf-8") as f:
        users = json.load(f)

    search_index = []
    for user in users:
        # Extract only necessary fields for search to keep the index light
        entry = {
            "id": user["username"],
            "name": user["name"],
            "bio": user["bio"],
            "langs": user["top_languages"],
            "topics": user["top_topics"],
            "r_names": [r["name"] for r in user.get("featured_repos", [])],
            "r_desc": [r["description"] for r in user.get("featured_repos", []) if r.get("description")],
            "score": user["activity_score"],
            "followers": user["followers"]
        }
        # Add aliases if they exist in user object (from overrides)
        if "aliases" in user:
            entry["aliases"] = user["aliases"]
            
        search_index.append(entry)

    with open(SEARCH_INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, indent=2)

    print(f"Successfully built search index with {len(search_index)} users.")

if __name__ == "__main__":
    main()
