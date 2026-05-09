import os
import sys
import json
import time
import yaml
from datetime import datetime, timedelta, timezone
import requests

# Enable unbuffered output for GitHub Actions
sys.stdout.reconfigure(line_buffering=True)

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

# Constants
API_VERSION = "2022-11-28"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
USERS_JSON = os.path.join(DATA_DIR, "users.json")
ENRICHED_JSON = os.path.join(DATA_DIR, "users-enriched.json")
OVERRIDES_YML = os.path.join(DATA_DIR, "overrides.yml")

# Token Management
TOKENS = [t.strip() for t in (os.getenv("GH_TOKENS") or os.getenv("GH_TOKEN") or "").split(",") if t.strip()]
CURRENT_TOKEN_IDX = 0

log(f"Initialized with {len(TOKENS)} tokens.")

def get_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "bd-github-enricher"
    }
    if TOKENS:
        headers["Authorization"] = f"Bearer {TOKENS[CURRENT_TOKEN_IDX]}"
    return headers

def rotate_token():
    global CURRENT_TOKEN_IDX
    if not TOKENS or len(TOKENS) <= 1:
        return False
    CURRENT_TOKEN_IDX = (CURRENT_TOKEN_IDX + 1) % len(TOKENS)
    log(f"Rotating to token index {CURRENT_TOKEN_IDX}...")
    return True

# Optimized GraphQL Fragment
USER_FRAGMENT = """
fragment UserProfile on User {
  login
  name
  avatarUrl
  bio
  location
  company
  websiteUrl
  createdAt
  followers { totalCount }
  following { totalCount }
  repositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}, isFork: false) {
    nodes {
      name
      description
      url
      stargazerCount
      forkCount
      primaryLanguage { name }
      repositoryTopics(first: 5) {
        nodes { topic { name } }
      }
      createdAt
      pushedAt
      isArchived
      isFork
      homepageUrl
      licenseInfo { name }
    }
    totalCount
  }
  yearlyContribs: contributionsCollection {
    contributionCalendar { totalContributions }
  }
  recentContribs: contributionsCollection(from: $thirtyDaysAgo) {
    contributionCalendar { totalContributions }
  }
}
"""

def gql(query, variables=None):
    max_retries = len(TOKENS) if TOKENS else 1
    for attempt in range(max_retries):
        try:
            r = requests.post(
                "https://api.github.com/graphql",
                headers=get_headers(),
                json={"query": query, "variables": variables or {}},
                timeout=60,
            )
            
            if r.status_code == 403 or r.status_code == 429:
                log(f"Rate limit or forbidden (HTTP {r.status_code}).")
                if rotate_token(): continue
                else: r.raise_for_status()

            r.raise_for_status()
            payload = r.json()
            
            if payload.get("errors"):
                errors_str = str(payload["errors"])
                if "rate limit" in errors_str.lower():
                    log("GraphQL internal rate limit hit.")
                    if rotate_token(): continue
                log(f"GraphQL Errors encountered: {errors_str[:200]}...")
                # We return the data even if there are errors for some users in the batch
            
            return payload.get("data") or {}
        except Exception as e:
            log(f"Request error (Attempt {attempt+1}): {e}")
            if rotate_token(): continue
            raise e
    return {}

def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading {path}: {e}")
    return default or []

def load_yaml(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            log(f"Error loading {path}: {e}")
    return {}

def process_user_data(user):
    if not user: return None
        
    repos_nodes = user.get("repositories", {}).get("nodes", [])
    repos = []
    for repo in repos_nodes:
        if not repo: continue
        repos.append({
            "name": repo["name"],
            "description": repo["description"],
            "url": repo["url"],
            "stargazerCount": repo["stargazerCount"],
            "forkCount": repo["forkCount"],
            "primaryLanguage": repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else None,
            "topics": [t["topic"]["name"] for t in repo["repositoryTopics"]["nodes"]],
            "createdAt": repo["createdAt"],
            "pushedAt": repo["pushedAt"],
            "isArchived": repo["isArchived"],
            "isFork": repo["isFork"],
            "homepageUrl": repo["homepageUrl"],
            "license": repo["licenseInfo"]["name"] if repo["licenseInfo"] else None
        })

    langs = {}
    for r in repos:
        if r["primaryLanguage"]:
            langs[r["primaryLanguage"]] = langs.get(r["primaryLanguage"], 0) + 1
    top_langs = sorted(langs.items(), key=lambda x: x[1], reverse=True)[:5]

    topics = {}
    for r in repos:
        for t in r["topics"]:
            topics[t] = topics.get(t, 0) + 1
    top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]

    yearly = user.get("yearlyContribs", {})
    recent = user.get("recentContribs", {})
    total_y = yearly.get("contributionCalendar", {}).get("totalContributions", 0)
    total_r = recent.get("contributionCalendar", {}).get("totalContributions", 0)
    
    score = (total_y * 0.1) + (total_r * 0.9)

    return {
        "username": user["login"],
        "name": user["name"] or user["login"],
        "avatar_url": user["avatarUrl"],
        "bio": user["bio"],
        "location": user["location"],
        "company": user["company"],
        "blog": user["websiteUrl"],
        "created_at": user["createdAt"],
        "followers": user["followers"]["totalCount"],
        "following": user["following"]["totalCount"],
        "public_repos": user.get("repositories", {}).get("totalCount", len(repos)),
        "last_active": repos[0]["pushedAt"] if repos else None,
        "activity_score": round(score, 2),
        "top_languages": [l[0] for l in top_langs],
        "top_topics": [t[0] for t in top_topics],
        "featured_repos": repos,
        "last_repo_fetched_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0"
    }

def main():
    if not TOKENS:
        log("CRITICAL: No GitHub tokens found. Exiting.")
        return

    log("Loading users...")
    users_raw = load_json(USERS_JSON)
    if not users_raw:
        log("No users found in users.json. Exiting.")
        return
    log(f"Loaded {len(users_raw)} users from users.json.")

    log("Loading enriched data...")
    enriched_data = load_json(ENRICHED_JSON, default={})
    if isinstance(enriched_data, list):
        enriched_data = {u["username"]: u for u in enriched_data}
    log(f"Loaded {len(enriched_data)} existing enriched profiles.")
        
    overrides = load_yaml(OVERRIDES_YML)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    
    log("Filtering users for enrichment...")
    to_enrich = []
    for user_entry in users_raw:
        login = user_entry.get("github_username")
        if not login: continue
        existing = enriched_data.get(login)
        if existing:
            try:
                last_fetch = datetime.fromisoformat(existing["last_repo_fetched_at"].replace("Z", "+00:00"))
                if last_fetch > week_ago: continue
            except: pass
        to_enrich.append(login)

    log(f"Total users needing enrichment: {len(to_enrich)}")
    if not to_enrich:
        log("All users are up to date. Exiting.")
        return
    
    batch_size = 30
    updated_count = 0
    total_batches = (len(to_enrich) + batch_size - 1) // batch_size
    
    for i in range(0, len(to_enrich), batch_size):
        batch_idx = i // batch_size + 1
        batch = to_enrich[i : i + batch_size]
        log(f"Processing batch {batch_idx}/{total_batches} ({len(batch)} users)...")
        
        query_parts = ["query($thirtyDaysAgo: DateTime!) {"]
        for idx, login in enumerate(batch):
            query_parts.append(f"  user{idx}: user(login: \"{login}\") {{ ...UserProfile }}")
        query_parts.append("  rateLimit { remaining }")
        query_parts.append("}")
        query_parts.append(USER_FRAGMENT)
        
        try:
            data = gql("\n".join(query_parts), {"thirtyDaysAgo": thirty_days_ago})
            
            users_processed_in_batch = 0
            for idx, login in enumerate(batch):
                user_raw = data.get(f"user{idx}")
                if user_raw:
                    enriched = process_user_data(user_raw)
                    if enriched:
                        user_overrides = overrides.get(login, {})
                        enriched.update(user_overrides)
                        enriched_data[login] = enriched
                        updated_count += 1
                        users_processed_in_batch += 1
            
            log(f"Batch {batch_idx} complete: {users_processed_in_batch}/{len(batch)} users enriched.")
            
            if data.get("rateLimit"):
                log(f"Rate Limit Remaining: {data['rateLimit']['remaining']}")
            
            if updated_count % 300 == 0:
                log(f"Saving progress... ({len(enriched_data)} users total)")
                with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
                    json.dump(list(enriched_data.values()), f, ensure_ascii=False, indent=2)
            
            time.sleep(1)
        except Exception as e:
            log(f"Batch {batch_idx} failed: {e}")
            time.sleep(5)

    log("Final integrity check...")
    if len(enriched_data) < (len(users_raw) * 0.9):
        log("CRITICAL: Final user count is below 90% threshold. Aborting save to prevent data loss.")
        exit(1)

    log(f"Saving final data to {ENRICHED_JSON}...")
    with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
        json.dump(list(enriched_data.values()), f, ensure_ascii=False, indent=2)
        
    log(f"Success! Enriched {updated_count} users. Total profiles: {len(enriched_data)}")

if __name__ == "__main__":
    main()
