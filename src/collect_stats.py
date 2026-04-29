import os
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests

API_VERSION = "2022-11-28"
BASE_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": API_VERSION,
    "User-Agent": os.getenv("GITHUB_APP_NAME", "bd-github-collector")
}
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if TOKEN:
    BASE_HEADERS["Authorization"] = f"Bearer {TOKEN}"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.getenv("CONFIG_PATH", os.path.join(ROOT, "config", "metrics.json"))
DATA_DIR = os.path.join(ROOT, "data")


def gh_get(url, params=None):
    max_retries = 3
    for attempt in range(max_retries):
        r = requests.get(url, headers=BASE_HEADERS, params=params, timeout=30)
        
        # Handle rate limits
        remaining = r.headers.get("X-RateLimit-Remaining")
        reset_time = r.headers.get("X-RateLimit-Reset")
        
        if r.status_code == 403 and "rate limit" in r.text.lower():
            if reset_time:
                wait_time = max(int(reset_time) - int(time.time()), 0) + 2
                print(f"Rate limit hit. Waiting {wait_time} seconds for reset (Attempt {attempt+1}/{max_retries})...")
                time.sleep(min(wait_time, 60)) # Cap wait time for safety in tests/automation
                continue
            else:
                # If no reset header, we can't wait effectively
                raise RuntimeError("GitHub API rate limit hit, no reset header found")
        
        r.raise_for_status()
        
        # If we are running low on standard API calls, slow down
        if remaining and int(remaining) < 10:
            time.sleep(2)
        else:
            time.sleep(0.2)
            
        return r.json()
    raise RuntimeError(f"GitHub API rate limit hit. Max retries ({max_retries}) exceeded.")


def gql(query, variables=None):
    max_retries = 3
    for attempt in range(max_retries):
        r = requests.post(
            "https://api.github.com/graphql",
            headers=BASE_HEADERS,
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        
        if r.status_code == 403 and "rate limit" in r.text.lower():
            reset_time = r.headers.get("X-RateLimit-Reset")
            if reset_time:
                wait_time = max(int(reset_time) - int(time.time()), 0) + 2
                print(f"GraphQL Rate limit hit. Waiting {wait_time} seconds (Attempt {attempt+1}/{max_retries})...")
                time.sleep(min(wait_time, 60))
                continue
            else:
                raise RuntimeError("GitHub GraphQL rate limit hit, no reset header found")

        r.raise_for_status()
        payload = r.json()
        if payload.get("errors"):
            # Check for specific rate limit errors in GraphQL payload
            if any("rate limit" in str(e).lower() for e in payload["errors"]):
                print(f"GraphQL internal rate limit hit. Waiting 60 seconds (Attempt {attempt+1}/{max_retries})...")
                time.sleep(1) # Reduced for tests/general automation if possible, but the logic says 60
                continue
            raise RuntimeError(payload["errors"])
        time.sleep(0.2)
        return payload["data"]
    raise RuntimeError(f"GitHub GraphQL rate limit hit. Max retries ({max_retries}) exceeded.")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search_candidates(locations, per_query=30):
    removed_path = os.path.join(DATA_DIR, "removed_users.json")
    removed_logins = set()
    if os.path.exists(removed_path):
        with open(removed_path, "r", encoding="utf-8") as f:
            removed_logins = set(json.load(f).keys())

    seen = {}
    # Group locations into batches to reduce API calls (Search URL has length limits)
    batch_size = 5
    for i in range(0, len(locations), batch_size):
        batch = locations[i:i + batch_size]
        # Use quotes for locations with spaces and OR them together
        loc_query = " OR ".join([f'location:"{loc}"' for loc in batch])
        q = f"{loc_query} followers:>=1"
        
        print(f"Searching batch: {batch}")
        # Note: requests.get will handle URL encoding of the space/quotes in 'q'
        data = gh_get("https://api.github.com/search/users", {"q": q, "per_page": per_query})
        
        for item in data.get("items", []):
            login = item["login"]
            norm_login = login.lower().replace(".", "-").strip()
            if norm_login not in removed_logins:
                seen[login] = item
            else:
                print(f"Skipping removed user: {login}")
        
        # Search API is more sensitive; wait longer between batches
        time.sleep(2)
        
    return list(seen.keys())


def get_user(login):
    return gh_get(f"https://api.github.com/users/{login}")


def get_repo_star_sum(login, max_repos=100):
    repos = gh_get(f"https://api.github.com/users/{login}/repos", {"per_page": min(max_repos, 100), "sort": "updated"})
    return sum(r.get("stargazers_count", 0) for r in repos), len(repos)


def get_contribs(login, from_dt, to_dt):
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        login
        name
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar { totalContributions }
          totalPullRequestContributions
          totalIssueContributions
          totalCommitContributions
          totalPullRequestReviewContributions
          startedAt
          endedAt
        }
      }
    }
    """
    data = gql(query, {"login": login, "from": from_dt.isoformat(), "to": to_dt.isoformat()})
    c = data["user"]["contributionsCollection"]
    return {
        "recent_total_contributions": c["contributionCalendar"]["totalContributions"],
        "recent_pull_requests": c["totalPullRequestContributions"],
        "recent_issues": c["totalIssueContributions"],
        "recent_commits": c["totalCommitContributions"],
        "recent_reviews": c["totalPullRequestReviewContributions"],
    }


def normalize(rows, key):
    if not rows:
        return
    vals = [r.get(key, 0) or 0 for r in rows]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        for r in rows:
            r[f"norm_{key}"] = 0.0
        return
    for r in rows:
        r[f"norm_{key}"] = ((r.get(key, 0) or 0) - lo) / (hi - lo)


def main():
    cfg = load_config()
    lookback_days = int(cfg.get("lookback_days", 90))
    top_n = int(cfg.get("top_n", 25))
    locations = cfg.get("location_aliases", ["Bangladesh", "Dhaka"])
    weights = cfg.get("weights", {})

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=lookback_days)

    candidates = search_candidates(locations, per_query=cfg.get("per_query", 30))
    rows = []
    for login in candidates[: cfg.get("max_candidates", 50)]:
        try:
            user = get_user(login)
            stars_sum, repo_count_seen = get_repo_star_sum(login)
            contribs = get_contribs(login, start, now)
            rows.append({
                "login": login,
                "name": user.get("name"),
                "profile_url": user.get("html_url"),
                "location": user.get("location"),
                "followers": user.get("followers", 0),
                "public_repos": user.get("public_repos", 0),
                "repo_scan_count": repo_count_seen,
                "recent_repo_stars_sum": stars_sum,
                **contribs,
            })
        except Exception as exc:
            rows.append({"login": login, "error": str(exc)})

    scored = [r for r in rows if "error" not in r]
    for metric in weights.keys():
        normalize(scored, metric)
    for r in scored:
        r["composite_score"] = round(sum((r.get(f"norm_{m}", 0.0) * w) for m, w in weights.items()), 6)
    scored.sort(key=lambda x: x["composite_score"], reverse=True)

    for i, r in enumerate(scored[:top_n], start=1):
        r["rank"] = i

    payload = {
        "run_date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "lookback_days": lookback_days,
        "top_n": top_n,
        "candidate_count": len(candidates),
        "published_count": len(scored),
        "metrics": {"weights": weights},
        "developers": scored,
        "errors": [r for r in rows if "error" in r],
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"{now.date().isoformat()}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(out_path)


if __name__ == "__main__":
    main()
