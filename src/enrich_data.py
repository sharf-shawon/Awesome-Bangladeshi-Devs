import os
import json
import time
import yaml
from datetime import datetime, timedelta, timezone
import requests

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
    print(f"Rotating to token index {CURRENT_TOKEN_IDX}...")
    return True

# Optimized GraphQL Fragment
# Reduced repos to 10, removed daily calendar (fetching totals directly)
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
    totalCommitContributions
    totalIssueContributions
    totalPullRequestContributions
    totalPullRequestReviewContributions
  }
  recentContribs: contributionsCollection(from: $thirtyDaysAgo) {
    contributionCalendar { totalContributions }
  }
}
"""

def gql(query, variables=None):
    max_retries = len(TOKENS) if TOKENS else 1
    for _ in range(max_retries):
        try:
            r = requests.post(
                "https://api.github.com/graphql",
                headers=get_headers(),
                json={"query": query, "variables": variables or {}},
                timeout=60,
            )
            
            if r.status_code == 403 or r.status_code == 429:
                if rotate_token(): continue
                else: r.raise_for_status()

            r.raise_for_status()
            payload = r.json()
            
            if payload.get("errors"):
                if any("rate limit" in str(e).lower() for e in payload["errors"]):
                    if rotate_token(): continue
                raise RuntimeError(payload["errors"])
                
            return payload.get("data", {})
        except Exception as e:
            if rotate_token(): continue
            raise e
    return {}

def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default or []

def load_yaml(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
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

    # Optimized Score Calculation
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
        print("No GitHub tokens found.")
        return

    users = load_json(USERS_JSON)
    if not users: return

    enriched_data = load_json(ENRICHED_JSON, default={})
    if isinstance(enriched_data, list):
        enriched_data = {u["username"]: u for u in enriched_data}
        
    overrides = load_yaml(OVERRIDES_YML)
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    thirty_days_ago = (now - timedelta(days=30)).isoformat()
    
    to_enrich = []
    for user_entry in users:
        login = user_entry.get("github_username")
        if not login: continue
        existing = enriched_data.get(login)
        if existing:
            last_fetch = datetime.fromisoformat(existing["last_repo_fetched_at"].replace("Z", "+00:00"))
            if last_fetch > week_ago: continue
        to_enrich.append(login)

    print(f"Users to enrich: {len(to_enrich)}")
    
    batch_size = 30 # Increased batch size
    updated_count = 0
    
    for i in range(0, len(to_enrich), batch_size):
        batch = to_enrich[i : i + batch_size]
        query_parts = ["query($thirtyDaysAgo: DateTime!) {"]
        for idx, login in enumerate(batch):
            query_parts.append(f"  user{idx}: user(login: \"{login}\") {{ ...UserProfile }}")
        query_parts.append("  rateLimit { remaining }")
        query_parts.append("}")
        query_parts.append(USER_FRAGMENT)
        
        try:
            data = gql("\n".join(query_parts), {"thirtyDaysAgo": thirty_days_ago})
            if not data: continue

            for idx, login in enumerate(batch):
                user_raw = data.get(f"user{idx}")
                if user_raw:
                    enriched = process_user_data(user_raw)
                    if enriched:
                        user_overrides = overrides.get(login, {})
                        enriched.update(user_overrides)
                        enriched_data[login] = enriched
                        updated_count += 1
            
            # Rate limit logging
            if data.get("rateLimit"):
                print(f"Batch {i//batch_size + 1} done. RL Remaining: {data['rateLimit']['remaining']}")
            
            # Incremental save every 150 users
            if updated_count % 150 == 0:
                with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
                    json.dump(list(enriched_data.values()), f, ensure_ascii=False, indent=2)
            
            time.sleep(1)
        except Exception as e:
            print(f"Batch failed: {e}")
            time.sleep(2)

    # Integrity Check
    if len(enriched_data) < (len(users) * 0.9):
        print("CRITICAL: Significant data loss detected. Aborting.")
        exit(1)

    with open(ENRICHED_JSON, "w", encoding="utf-8") as f:
        json.dump(list(enriched_data.values()), f, ensure_ascii=False, indent=2)
        
    print(f"Updated {updated_count} users.")

if __name__ == "__main__":
    main()
