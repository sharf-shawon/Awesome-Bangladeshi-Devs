import os
import re
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
README_PATH = os.path.join(ROOT, "README.md")


def gh_get(url, params=None):
    r = requests.get(url, headers=BASE_HEADERS, params=params, timeout=30)
    if r.status_code == 403 and "rate limit" in r.text.lower():
        raise RuntimeError("GitHub API rate limit hit")
    r.raise_for_status()
    time.sleep(0.2)
    return r.json()


def gql(query, variables=None):
    r = requests.post(
        "https://api.github.com/graphql",
        headers=BASE_HEADERS,
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    time.sleep(0.2)
    return payload["data"]


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def search_candidates(locations, per_query=100):
    removed_path = os.path.join(DATA_DIR, "removed_users.json")
    removed_logins = set()
    if os.path.exists(removed_path):
        with open(removed_path, "r", encoding="utf-8") as f:
            removed_logins = set(json.load(f).keys())

    seen = {}
    for loc in locations:
        q = f"location:{quote(loc)} followers:>=1"
        page = 1
        fetched = 0
        page_size = min(per_query, 100)
        while True:
            data = gh_get(
                "https://api.github.com/search/users",
                {"q": q, "per_page": page_size, "page": page},
            )
            items = data.get("items", [])
            if not items:
                break
            for item in items:
                login = item["login"]
                norm_login = login.lower().replace(".", "-").strip()
                if norm_login not in removed_logins:
                    seen[login] = item
                else:
                    print(f"Skipping removed user: {login}")
            fetched += len(items)
            # GitHub Search API caps at 1000 results; stop when all fetched
            total = min(data.get("total_count", 0), 1000)
            if fetched >= total or len(items) < page_size:
                break
            page += 1
    return list(seen.keys())


def get_user(login):
    return gh_get(f"https://api.github.com/users/{login}")


def get_repo_star_sum(login, max_repos=100):
    repos = gh_get(f"https://api.github.com/users/{login}/repos", {"per_page": min(max_repos, 100), "sort": "updated"})
    return sum(r.get("stargazers_count", 0) for r in repos), len(repos)


def get_repo_stats(login, max_repos=100):
    """Fetch repos and return star sum, repo count, and top languages in one API call."""
    repos = gh_get(
        f"https://api.github.com/users/{login}/repos",
        {"per_page": min(max_repos, 100), "sort": "updated"},
    )
    stars_sum = sum(r.get("stargazers_count", 0) for r in repos)
    repo_count = len(repos)
    lang_counts = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_languages = [
        lang
        for lang, _ in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    return stars_sum, repo_count, top_languages


def load_users_from_json(users_path):
    """Return a list of GitHub login names from a users.json file."""
    if not os.path.exists(users_path):
        return []
    with open(users_path, "r", encoding="utf-8") as f:
        users = json.load(f)
    if not isinstance(users, list):
        return []
    logins = []
    for u in users:
        login = u.get("github_username") or u.get("login")
        if login:
            logins.append(login)
    return logins


def load_logins_from_readme(readme_path):
    """Extract GitHub profile usernames from markdown links in the README.

    Matches URLs of the form:
        https://github.com/USERNAME
        https://github.com/USERNAME?rank=TYPE

    Multi-segment paths (org/repo URLs, action badges, issue templates) are
    intentionally excluded because they contain a '/' after the username.
    """
    if not os.path.exists(readme_path):
        return []
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Inside a markdown link paren: only single-path-segment github.com URLs
    pattern = r'\(https://github\.com/([A-Za-z0-9][A-Za-z0-9._-]*)(?:\?[^)#\s]*)?\)'
    logins = list(dict.fromkeys(re.findall(pattern, content)))
    return logins


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

    # Collect candidates from GitHub location search (paginated)
    search_logins = search_candidates(locations, per_query=cfg.get("per_query", 100))

    # Load all manually-registered users from users.json
    users_path = os.path.join(DATA_DIR, "users.json")
    registered_logins = load_users_from_json(users_path)

    # Load all developers currently listed in the README
    readme_logins = load_logins_from_readme(README_PATH)

    # Load removed users to skip them
    removed_path = os.path.join(DATA_DIR, "removed_users.json")
    removed_logins = set()
    if os.path.exists(removed_path):
        with open(removed_path, "r", encoding="utf-8") as f:
            removed_logins = set(json.load(f).keys())

    # Merge all logins deduplicating case-insensitively; search candidates first
    seen_lower = set()
    all_logins = []
    for login in search_logins + registered_logins + readme_logins:
        norm = login.lower().replace(".", "-").strip()
        if norm not in seen_lower and norm not in removed_logins:
            seen_lower.add(norm)
            all_logins.append(login)

    rows = []
    for login in all_logins:
        try:
            user = get_user(login)
            stars_sum, repo_count_seen, top_languages = get_repo_stats(login)
            contribs = get_contribs(login, start, now)
            rows.append({
                "login": login,
                "name": user.get("name"),
                "avatar_url": user.get("avatar_url"),
                "profile_url": user.get("html_url"),
                "bio": user.get("bio"),
                "company": user.get("company"),
                "blog": user.get("blog"),
                "twitter_username": user.get("twitter_username"),
                "email": user.get("email"),
                "location": user.get("location"),
                "hireable": user.get("hireable"),
                "followers": user.get("followers", 0),
                "following": user.get("following", 0),
                "public_repos": user.get("public_repos", 0),
                "public_gists": user.get("public_gists", 0),
                "repo_scan_count": repo_count_seen,
                "recent_repo_stars_sum": stars_sum,
                "top_languages": top_languages,
                "account_created_at": user.get("created_at"),
                "account_updated_at": user.get("updated_at"),
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

    # Assign ranks to ALL developers so historic data is fully usable
    for i, r in enumerate(scored, start=1):
        r["rank"] = i

    payload = {
        "run_date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "lookback_days": lookback_days,
        "top_n": top_n,
        "search_candidate_count": len(search_logins),
        "registered_user_count": len(registered_logins),
        "readme_user_count": len(readme_logins),
        "candidate_count": len(all_logins),
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
