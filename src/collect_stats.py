import glob
import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from html import escape

import requests

API_VERSION = "2022-11-28"
BASE_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": API_VERSION,
    "User-Agent": os.getenv("GITHUB_APP_NAME", "bd-github-collector"),
}
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
if TOKEN:
    BASE_HEADERS["Authorization"] = f"Bearer {TOKEN}"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.getenv("CONFIG_PATH", os.path.join(ROOT, "config", "metrics.json"))
DATA_DIR = os.path.join(ROOT, "data")
WEB_DIR = os.path.join(DATA_DIR, "web")
AUTOMATED_PATH = os.path.join(DATA_DIR, "automated.json")
USERS_PATH = os.path.join(DATA_DIR, "users.json")
REMOVED_PATH = os.path.join(DATA_DIR, "removed_users.json")
CACHE_PATH = os.path.join(DATA_DIR, "api_cache.json")
DEVELOPERS_DIR = os.path.join(ROOT, "developers")
SITEMAP_PATH = os.path.join(ROOT, "sitemap.xml")
ROBOTS_PATH = os.path.join(ROOT, "robots.txt")

API_STATS = {
    "rest_calls": 0,
    "graphql_calls": 0,
    "remaining_min": None,
    "used": 0,
    "degraded": False,
}


def _load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, TypeError):
        return default


def _write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _normalize_login(login):
    return (login or "").strip().lower().replace(".", "-")


def _parse_iso(dt_str):
    if not dt_str:
        return None
    normalized = dt_str.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _update_rate_stats(headers):
    remaining = headers.get("X-RateLimit-Remaining")
    used = headers.get("X-RateLimit-Used")
    try:
        if remaining is not None:
            rem_int = int(remaining)
            prev = API_STATS["remaining_min"]
            API_STATS["remaining_min"] = rem_int if prev is None else min(prev, rem_int)
    except (TypeError, ValueError):
        pass
    try:
        if used is not None:
            API_STATS["used"] = max(API_STATS["used"], int(used))
    except (TypeError, ValueError):
        pass


def _should_degrade(cfg):
    threshold = int(cfg.get("api_min_remaining_threshold", 20))
    rem = API_STATS.get("remaining_min")
    return rem is not None and rem <= threshold


def gh_get(url, params=None, cache=None, cache_key=None):
    max_retries = 3
    request_headers = dict(BASE_HEADERS)

    cache_entry = None
    if cache is not None and cache_key:
        cache_entry = cache.get(cache_key)
        if cache_entry:
            etag = cache_entry.get("etag")
            last_modified = cache_entry.get("last_modified")
            if etag:
                request_headers["If-None-Match"] = etag
            if last_modified:
                request_headers["If-Modified-Since"] = last_modified

    for attempt in range(max_retries):
        API_STATS["rest_calls"] += 1
        r = requests.get(url, headers=request_headers, params=params, timeout=30)
        _update_rate_stats(r.headers)

        if r.status_code == 304 and cache_entry:
            return cache_entry.get("body", {})

        remaining = r.headers.get("X-RateLimit-Remaining")
        reset_time = r.headers.get("X-RateLimit-Reset")

        if r.status_code == 403 and "rate limit" in r.text.lower():
            if reset_time:
                wait_time = max(int(reset_time) - int(time.time()), 0) + 2
                print(f"Rate limit hit. Waiting {wait_time} seconds for reset (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(min(wait_time, 60))
                continue
            raise RuntimeError("GitHub API rate limit hit, no reset header found")

        r.raise_for_status()
        payload = r.json()

        if cache is not None and cache_key:
            cache[cache_key] = {
                "etag": r.headers.get("ETag"),
                "last_modified": r.headers.get("Last-Modified"),
                "body": payload,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }

        if remaining and remaining.isdigit() and int(remaining) < 10:
            time.sleep(2)
        else:
            time.sleep(0.2)

        return payload

    raise RuntimeError(f"GitHub API rate limit hit. Max retries ({max_retries}) exceeded.")


def gql(query, variables=None):
    max_retries = 3
    for attempt in range(max_retries):
        API_STATS["graphql_calls"] += 1
        r = requests.post(
            "https://api.github.com/graphql",
            headers=BASE_HEADERS,
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        _update_rate_stats(r.headers)

        if r.status_code == 403 and "rate limit" in r.text.lower():
            reset_time = r.headers.get("X-RateLimit-Reset")
            if reset_time:
                wait_time = max(int(reset_time) - int(time.time()), 0) + 2
                print(f"GraphQL Rate limit hit. Waiting {wait_time} seconds (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(min(wait_time, 60))
                continue
            raise RuntimeError("GitHub GraphQL rate limit hit, no reset header found")

        r.raise_for_status()
        payload = r.json()
        if payload.get("errors"):
            if any("rate limit" in str(e).lower() for e in payload["errors"]):
                print(f"GraphQL internal rate limit hit. Waiting 60 seconds (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(1)
                continue
            raise RuntimeError(payload["errors"])

        time.sleep(0.2)
        return payload["data"]

    raise RuntimeError(f"GitHub GraphQL rate limit hit. Max retries ({max_retries}) exceeded.")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_site_url():
    cfg_path = os.path.join(ROOT, "_config.yml")
    if not os.path.exists(cfg_path):
        return ""
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("url:"):
                    return line.split(":", 1)[1].strip().strip('"').strip("'")
    except OSError:
        return ""
    return ""


def search_candidates(locations, per_query=30, cache=None):
    removed_logins = set(_load_json(REMOVED_PATH, {}).keys())
    seen = {}
    for loc in locations:
        q = f'location:"{loc}" followers:>=1'
        print(f"Searching location: {loc}")
        try:
            data = gh_get(
                "https://api.github.com/search/users",
                {"q": q, "per_page": per_query},
                cache=cache,
                cache_key=f"search:{q}:{per_query}",
            )
            for item in data.get("items", []):
                login = item["login"]
                norm_login = _normalize_login(login)
                if norm_login not in removed_logins:
                    seen[login] = item
        except Exception as e:
            print(f"Error searching location {loc}: {e}")
        time.sleep(1)
    return list(seen.keys())


def get_user(login, cache=None):
    return gh_get(
        f"https://api.github.com/users/{login}",
        cache=cache,
        cache_key=f"user:{_normalize_login(login)}",
    )


def get_user_repos(login, max_repos=100, cache=None):
    repos = gh_get(
        f"https://api.github.com/users/{login}/repos",
        {"per_page": min(max_repos, 100), "sort": "updated"},
        cache=cache,
        cache_key=f"repos:{_normalize_login(login)}:{min(max_repos, 100)}",
    )
    return repos if isinstance(repos, list) else []


def get_repo_star_sum(login, max_repos=100):
    repos = gh_get(
        f"https://api.github.com/users/{login}/repos",
        {"per_page": min(max_repos, 100), "sort": "updated"},
    )
    repos = repos if isinstance(repos, list) else []
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


def _clean_text(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def _tokenize(*parts):
    text = " ".join(_clean_text(p).lower() for p in parts if p)
    # Keep token chars commonly found in developer terms (c++, c#, node.js, ci-cd) and
    # drop 1-char tokens to reduce noisy matches in the client-side search index.
    return sorted({t for t in re.split(r"[^a-z0-9+#.\-]+", text) if len(t) > 1})

def summarize_repositories(repos, cfg):
    repos = repos if isinstance(repos, list) else []
    top_repo_count = int(cfg.get("top_repos_per_user", 8))

    repo_summaries = []
    language_counter = {}
    topic_counter = {}
    stars_sum = 0
    forks_sum = 0
    latest_repo_activity = None

    for repo in repos:
        language = _clean_text(repo.get("language") or "")
        topics = repo.get("topics") if isinstance(repo.get("topics"), list) else []
        topics = [_clean_text(t).lower() for t in topics if _clean_text(t)]

        repo_summary = {
            "name": repo.get("name"),
            "full_name": repo.get("full_name"),
            "url": repo.get("html_url"),
            "description": _clean_text(repo.get("description") or ""),
            "language": language,
            "stargazers_count": int(repo.get("stargazers_count", 0) or 0),
            "forks_count": int(repo.get("forks_count", 0) or 0),
            "created_at": repo.get("created_at"),
            "updated_at": repo.get("updated_at"),
            "pushed_at": repo.get("pushed_at"),
            "archived": bool(repo.get("archived", False)),
            "is_fork": bool(repo.get("fork", False)),
            "topics": topics,
        }
        repo_summaries.append(repo_summary)

        stars_sum += repo_summary["stargazers_count"]
        forks_sum += repo_summary["forks_count"]

        if language:
            language_counter[language] = language_counter.get(language, 0) + 1
        for topic in topics:
            topic_counter[topic] = topic_counter.get(topic, 0) + 1

        pushed_at = _parse_iso(repo_summary.get("pushed_at"))
        if pushed_at and (latest_repo_activity is None or pushed_at > latest_repo_activity):
            latest_repo_activity = pushed_at

    sorted_repos = sorted(
        repo_summaries,
        key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0), r.get("updated_at") or ""),
        reverse=True,
    )

    primary_languages = [
        k for k, _ in sorted(language_counter.items(), key=lambda i: (i[1], i[0].lower()), reverse=True)[:5]
    ]
    expertise_tags = [
        k for k, _ in sorted(topic_counter.items(), key=lambda i: (i[1], i[0]), reverse=True)[:10]
    ]
    skills = sorted({_clean_text(s) for s in (primary_languages + expertise_tags) if _clean_text(s)})

    total_languages = sum(language_counter.values())
    language_mix = (
        {
            lang: round((count / total_languages), 4)
            for lang, count in sorted(language_counter.items(), key=lambda i: i[1], reverse=True)
        }
        if total_languages
        else {}
    )

    return {
        "repo_scan_count": len(repo_summaries),
        "recent_repo_stars_sum": stars_sum,
        "repo_forks_sum": forks_sum,
        "top_repositories": sorted_repos[:top_repo_count],
        "language_mix": language_mix,
        "languages": sorted(language_counter.keys()),
        "primary_languages": primary_languages,
        "expertise_tags": expertise_tags,
        "skills": skills,
        "last_repo_activity_at": latest_repo_activity.isoformat().replace("+00:00", "Z") if latest_repo_activity else None,
    }


def _choose_last_active(user, repo_summary):
    times = [_parse_iso(user.get("updated_at")), _parse_iso(repo_summary.get("last_repo_activity_at"))]
    valid = [t for t in times if t is not None]
    if not valid:
        return None
    return max(valid).isoformat().replace("+00:00", "Z")


def _load_previous_automated():
    prev = _load_json(AUTOMATED_PATH, {})
    if not isinstance(prev, dict):
        return {}
    return prev


def _should_refresh_developer(login, previous_map, now, cfg, full_refresh=False):
    if full_refresh:
        return True
    prev = previous_map.get(_normalize_login(login))
    if not prev:
        return True
    ttl_hours = int(cfg.get("incremental_ttl_hours", 24))
    stamp = _parse_iso(prev.get("last_collected_at") or prev.get("fetched_at") or prev.get("last_active_at"))
    if stamp is None:
        return True
    return now - stamp > timedelta(hours=ttl_hours)


def _merge_candidates(search_logins, manual_logins, max_candidates):
    seen = set()
    merged = []
    for login in list(manual_logins) + list(search_logins):
        if not login:
            continue
        norm = _normalize_login(login)
        if norm in seen:
            continue
        seen.add(norm)
        merged.append(login)
        if len(merged) >= max_candidates:
            break
    return merged


def _compute_growth(current_devs, previous_devs):
    prev_map = {_normalize_login(d.get("login")): d for d in previous_devs}
    for dev in current_devs:
        prev = prev_map.get(_normalize_login(dev.get("login")), {})
        dev["followers_growth"] = int(dev.get("followers", 0) or 0) - int(prev.get("followers", dev.get("followers", 0)) or 0)
        dev["stars_growth"] = int(dev.get("recent_repo_stars_sum", 0) or 0) - int(prev.get("recent_repo_stars_sum", dev.get("recent_repo_stars_sum", 0)) or 0)


def _load_activity_timeline(limit=30):
    timeline = []
    files = sorted(glob.glob(os.path.join(DATA_DIR, "????-??-??.json")), reverse=True)[:limit]
    for path in reversed(files):
        payload = _load_json(path, {})
        if not isinstance(payload, dict):
            continue
        devs = payload.get("developers", []) or []
        if not devs:
            continue
        total_contribs = sum(int(d.get("recent_total_contributions", 0) or 0) for d in devs)
        avg_score = sum(float(d.get("composite_score", 0) or 0) for d in devs) / len(devs)
        timeline.append(
            {
                "date": payload.get("run_date") or os.path.basename(path).replace(".json", ""),
                "developers": len(devs),
                "total_contributions": total_contribs,
                "average_score": round(avg_score, 6),
            }
        )
    return timeline


def _build_aggregates(scored, previous_devs, timeline):
    language_stats = {}
    location_stats = {}
    prev_repo_stars = {}

    for dev in previous_devs:
        for repo in dev.get("top_repositories", []) or []:
            full_name = repo.get("full_name") or repo.get("name")
            if full_name:
                prev_repo_stars[full_name.lower()] = int(repo.get("stargazers_count", 0) or 0)

    rising_repos = []
    for dev in scored:
        location = _clean_text(dev.get("location") or "Unknown")
        location_stats[location] = location_stats.get(location, 0) + 1

        for lang in dev.get("primary_languages", []) or []:
            block = language_stats.setdefault(lang, {"developers": 0, "stars": 0})
            block["developers"] += 1
            block["stars"] += int(dev.get("recent_repo_stars_sum", 0) or 0)

        for repo in dev.get("top_repositories", []) or []:
            full_name = repo.get("full_name") or repo.get("name")
            if not full_name:
                continue
            old = prev_repo_stars.get(full_name.lower(), 0)
            current = int(repo.get("stargazers_count", 0) or 0)
            growth = current - old
            if growth > 0:
                rising_repos.append(
                    {
                        "repository": full_name,
                        "url": repo.get("url"),
                        "owner": dev.get("login"),
                        "stars_growth": growth,
                        "stars": current,
                    }
                )

    language_leaderboard = [
        {"language": lang, **stats}
        for lang, stats in sorted(
            language_stats.items(), key=lambda i: (i[1]["developers"], i[1]["stars"], i[0].lower()), reverse=True
        )
    ]
    location_leaderboard = [
        {"location": loc, "developers": count}
        for loc, count in sorted(location_stats.items(), key=lambda i: (i[1], i[0].lower()), reverse=True)
    ]
    rising_repos.sort(key=lambda r: (r["stars_growth"], r["stars"]), reverse=True)

    return {
        "language_leaderboard": language_leaderboard[:30],
        "location_leaderboard": location_leaderboard[:30],
        "rising_repositories": rising_repos[:50],
        "activity_timeline": timeline,
    }


def _developer_card(dev):
    return {
        "login": dev.get("login"),
        "name": dev.get("name"),
        "profile_url": dev.get("profile_url"),
        "location": dev.get("location"),
        "followers": dev.get("followers", 0),
        "public_repos": dev.get("public_repos", 0),
        "recent_repo_stars_sum": dev.get("recent_repo_stars_sum", 0),
        "repo_forks_sum": dev.get("repo_forks_sum", 0),
        "activity_score": dev.get("activity_score", 0),
        "last_active_at": dev.get("last_active_at"),
        "skills": dev.get("skills", []),
        "languages": dev.get("languages", []),
        "primary_languages": dev.get("primary_languages", []),
        "expertise_tags": dev.get("expertise_tags", []),
        "top_repositories": dev.get("top_repositories", [])[:5],
    }

def _developer_page_html(dev, base_url):
    login = dev.get("login") or "unknown"
    name = dev.get("name") or login
    canonical = f"{base_url.rstrip('/')}/developers/{login}/" if base_url else f"/developers/{login}/"
    description = f"{name} ({login}) from {dev.get('location') or 'Bangladesh'} – GitHub activity and repository highlights."

    repo_items = []
    for repo in dev.get("top_repositories", [])[:12]:
        repo_name = escape(repo.get("name") or "repository")
        repo_url = escape(repo.get("url") or "#")
        repo_desc = escape(repo.get("description") or "")
        language = escape(repo.get("language") or "Unknown")
        stars = int(repo.get("stargazers_count", 0) or 0)
        forks = int(repo.get("forks_count", 0) or 0)
        repo_items.append(f"<li><a href=\"{repo_url}\" rel=\"noopener\">{repo_name}</a> - {repo_desc} <small>({language} · ⭐ {stars} · 🍴 {forks})</small></li>")

    json_ld = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": name,
        "alternateName": login,
        "url": dev.get("profile_url") or f"https://github.com/{login}",
        "sameAs": [dev.get("profile_url") or f"https://github.com/{login}"],
        "homeLocation": dev.get("location") or "Bangladesh",
        "knowsAbout": (dev.get("skills", []) + dev.get("expertise_tags", []))[:30],
    }

    skills = ", ".join(escape(s) for s in dev.get("skills", [])) or "Not available"
    languages = ", ".join(escape(s) for s in dev.get("languages", [])) or "Not available"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(name)} ({escape(login)}) | Awesome Bangladeshi Developers</title>
  <meta name=\"description\" content=\"{escape(description)}\" />
  <link rel=\"canonical\" href=\"{escape(canonical)}\" />
  <meta property=\"og:type\" content=\"profile\" />
  <meta property=\"og:title\" content=\"{escape(name)} ({escape(login)})\" />
  <meta property=\"og:description\" content=\"{escape(description)}\" />
  <meta property=\"og:url\" content=\"{escape(canonical)}\" />
  <meta name=\"twitter:card\" content=\"summary\" />
  <script type=\"application/ld+json\">{json.dumps(json_ld, ensure_ascii=False)}</script>
</head>
<body>
  <main>
    <p><a href=\"/\">← Back to directory</a></p>
    <h1>{escape(name)} <small>({escape(login)})</small></h1>
    <p><a href=\"{escape(dev.get('profile_url') or f'https://github.com/{login}') }\" rel=\"noopener\">GitHub profile</a></p>
    <p><strong>Location:</strong> {escape(dev.get('location') or 'Unknown')}</p>
    <p><strong>Followers:</strong> {int(dev.get('followers', 0) or 0)} | <strong>Public repos:</strong> {int(dev.get('public_repos', 0) or 0)} | <strong>Total stars:</strong> {int(dev.get('recent_repo_stars_sum', 0) or 0)}</p>
    <p><strong>Activity score:</strong> {float(dev.get('activity_score', 0) or 0):.4f} | <strong>Last active:</strong> {escape(dev.get('last_active_at') or 'N/A')}</p>
    <p><strong>Languages:</strong> {languages}</p>
    <p><strong>Skills & expertise:</strong> {skills}</p>
    <h2>Highlighted repositories</h2>
    <ul>{''.join(repo_items) if repo_items else '<li>No repository summaries available.</li>'}</ul>
  </main>
</body>
</html>
"""


def _hub_page_html(title, items, item_key, value_key):
    lis = []
    for it in items:
        label = escape(str(it.get(item_key, "Unknown")))
        value = escape(str(it.get(value_key, 0)))
        lis.append(f"<li><strong>{label}</strong>: {value}</li>")
    return f"""<!doctype html>
<html lang=\"en\">
<head><meta charset=\"utf-8\" /><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" /><title>{escape(title)}</title></head>
<body><main><p><a href=\"/\">← Back to home</a></p><h1>{escape(title)}</h1><ul>{''.join(lis) if lis else '<li>No data available.</li>'}</ul></main></body>
</html>
"""


def generate_developer_pages(developers, base_url=""):
    os.makedirs(DEVELOPERS_DIR, exist_ok=True)
    page_urls = [f"{base_url.rstrip('/')}/" if base_url else "/"]

    for dev in developers:
        login = dev.get("login")
        if not login:
            continue
        out_dir = os.path.join(DEVELOPERS_DIR, login)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(_developer_page_html(dev, base_url))
        page_urls.append(f"{base_url.rstrip('/')}/developers/{login}/" if base_url else f"/developers/{login}/")

    languages = {}
    locations = {}
    for dev in developers:
        for lang in dev.get("primary_languages", []) or []:
            languages[lang] = languages.get(lang, 0) + 1
        loc = _clean_text(dev.get("location") or "Unknown")
        locations[loc] = locations.get(loc, 0) + 1

    language_dir = os.path.join(ROOT, "languages")
    location_dir = os.path.join(ROOT, "locations")
    os.makedirs(language_dir, exist_ok=True)
    os.makedirs(location_dir, exist_ok=True)

    language_items = [{"language": k, "developers": v} for k, v in sorted(languages.items(), key=lambda i: (i[1], i[0].lower()), reverse=True)]
    location_items = [{"location": k, "developers": v} for k, v in sorted(locations.items(), key=lambda i: (i[1], i[0].lower()), reverse=True)]

    with open(os.path.join(language_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(_hub_page_html("Language Leaderboard", language_items[:200], "language", "developers"))
    with open(os.path.join(location_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(_hub_page_html("Location Leaderboard", location_items[:200], "location", "developers"))

    page_urls.extend([
        f"{base_url.rstrip('/')}/languages/" if base_url else "/languages/",
        f"{base_url.rstrip('/')}/locations/" if base_url else "/locations/",
    ])

    lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?>", "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
    for url in page_urls:
        lines.append(f"  <url><loc>{escape(url)}</loc></url>")
    lines.append("</urlset>")
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    robots_lines = ["User-agent: *", "Allow: /", f"Sitemap: {base_url.rstrip('/') + '/sitemap.xml' if base_url else '/sitemap.xml'}"]
    with open(ROBOTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(robots_lines) + "\n")


def build_site_outputs(payload, cfg):
    os.makedirs(WEB_DIR, exist_ok=True)
    developers = payload.get("developers", []) or []
    page_size = int(cfg.get("web_page_size", 100))

    sorted_directory = sorted(developers, key=lambda d: ((d.get("login") or "").lower(), d.get("followers", 0)))
    pages = []
    page_files = []

    for i in range(0, len(sorted_directory), page_size):
        chunk = [_developer_card(dev) for dev in sorted_directory[i : i + page_size]]
        page_idx = i // page_size + 1
        name = f"directory-page-{page_idx}.json"
        page_files.append(name)
        pages.append({"page": page_idx, "count": len(chunk), "file": name})
        _write_json(os.path.join(WEB_DIR, name), {"page": page_idx, "developers": chunk})

    search_items = []
    for dev in developers:
        repos = dev.get("top_repositories", []) or []
        repo_names = [r.get("name") for r in repos if r.get("name")]
        repo_desc = [r.get("description") for r in repos if r.get("description")]
        search_items.append(
            {
                "id": dev.get("login"),
                "tokens": _tokenize(
                    dev.get("login"),
                    dev.get("name"),
                    dev.get("location"),
                    " ".join(dev.get("skills", [])),
                    " ".join(dev.get("languages", [])),
                    " ".join(dev.get("expertise_tags", [])),
                    " ".join(repo_names),
                    " ".join(repo_desc),
                ),
                "location": dev.get("location"),
                "followers": dev.get("followers", 0),
                "stars": dev.get("recent_repo_stars_sum", 0),
                "forks": dev.get("repo_forks_sum", 0),
                "activity_score": dev.get("activity_score", 0),
                "last_active_at": dev.get("last_active_at"),
                "skills": dev.get("skills", []),
                "languages": dev.get("languages", []),
                "expertise_tags": dev.get("expertise_tags", []),
            }
        )
    _write_json(os.path.join(WEB_DIR, "search-index.json"), {"items": search_items})

    sort_specs = {
        "followers": lambda d: d.get("followers", 0),
        "stars": lambda d: d.get("recent_repo_stars_sum", 0),
        "forks": lambda d: d.get("repo_forks_sum", 0),
        "updated": lambda d: d.get("last_active_at") or "",
        "activity": lambda d: d.get("activity_score", 0),
    }
    _write_json(os.path.join(WEB_DIR, "sorted-indexes.json"), {k: [d.get("login") for d in sorted(developers, key=fn, reverse=True)] for k, fn in sort_specs.items()})

    charts = {
        "timeline": payload.get("aggregates", {}).get("activity_timeline", []),
        "languages": payload.get("aggregates", {}).get("language_leaderboard", [])[:15],
        "locations": payload.get("aggregates", {}).get("location_leaderboard", [])[:15],
        "rising_repositories": payload.get("aggregates", {}).get("rising_repositories", [])[:15],
        "rising_developers": [{"login": d.get("login"), "followers_growth": d.get("followers_growth", 0), "stars_growth": d.get("stars_growth", 0)} for d in sorted(developers, key=lambda d: (d.get("followers_growth", 0), d.get("stars_growth", 0)), reverse=True)[:25]],
    }
    _write_json(os.path.join(WEB_DIR, "charts.json"), charts)

    summary = {
        "generated_at": payload.get("generated_at"),
        "run_date": payload.get("run_date"),
        "total_developers": len(developers),
        "top_followers": [d.get("login") for d in sorted(developers, key=lambda d: d.get("followers", 0), reverse=True)[:20]],
        "top_activity": [d.get("login") for d in sorted(developers, key=lambda d: d.get("activity_score", 0), reverse=True)[:20]],
        "top_stars": [d.get("login") for d in sorted(developers, key=lambda d: d.get("recent_repo_stars_sum", 0), reverse=True)[:20]],
        "language_leaderboard": payload.get("aggregates", {}).get("language_leaderboard", [])[:25],
        "location_leaderboard": payload.get("aggregates", {}).get("location_leaderboard", [])[:25],
    }
    _write_json(os.path.join(WEB_DIR, "stats-summary.json"), summary)

    version_source = {"generated_at": payload.get("generated_at"), "run_date": payload.get("run_date"), "developer_count": len(developers), "pages": page_files}
    # 16 hex chars keeps URLs short while being stable enough for static-bundle cache busting.
    version_hash = hashlib.sha256(json.dumps(version_source, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    manifest = {
        "version": version_hash,
        "generated_at": payload.get("generated_at"),
        "run_date": payload.get("run_date"),
        "pages": pages,
        "page_size": page_size,
        "directory_index": page_files,
        "search_index": "search-index.json",
        "sorted_indexes": "sorted-indexes.json",
        "stats_summary": "stats-summary.json",
        "charts": "charts.json",
    }
    _write_json(os.path.join(WEB_DIR, "manifest.json"), manifest)

    generate_developer_pages(developers, load_site_url())


def main():
    cfg = load_config()
    lookback_days = int(cfg.get("lookback_days", 90))
    top_n = int(cfg.get("top_n", 25))
    locations = cfg.get("location_aliases", ["Bangladesh", "Dhaka"])
    weights = cfg.get("weights", {})

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=lookback_days)

    previous_payload = _load_previous_automated()
    previous_devs = previous_payload.get("developers", []) if isinstance(previous_payload, dict) else []
    previous_map = {_normalize_login(d.get("login")): d for d in previous_devs if d.get("login")}

    full_refresh_interval_days = int(cfg.get("full_refresh_interval_days", 7))
    prev_generated_at = _parse_iso(previous_payload.get("generated_at")) if isinstance(previous_payload, dict) else None
    full_refresh = not prev_generated_at or (now - prev_generated_at > timedelta(days=full_refresh_interval_days))

    cache = _load_json(CACHE_PATH, {})
    if not isinstance(cache, dict):
        cache = {}

    manual_users = _load_json(USERS_PATH, [])
    if not isinstance(manual_users, list):
        manual_users = []
    manual_logins = [u.get("github_username") for u in manual_users if u.get("github_username")]

    candidates_from_search = search_candidates(locations, per_query=cfg.get("per_query", 30), cache=cache)
    candidates = _merge_candidates(candidates_from_search, manual_logins, int(cfg.get("max_candidates", 100)))
    removed_logins = set(_load_json(REMOVED_PATH, {}).keys())

    rows = []
    repo_scan_cap = int(cfg.get("repos_per_user_scan", 100))

    for login in candidates:
        norm_login = _normalize_login(login)
        if norm_login in removed_logins:
            continue

        if _should_degrade(cfg):
            API_STATS["degraded"] = True

        can_reuse = (not API_STATS["degraded"]) and (not _should_refresh_developer(login, previous_map, now, cfg, full_refresh=full_refresh))
        if can_reuse:
            reused = dict(previous_map[norm_login])
            reused["reused_from_previous"] = True
            rows.append(reused)
            continue

        try:
            user = get_user(login, cache=cache)
            if API_STATS["degraded"]:
                repos = (previous_map.get(norm_login, {}) or {}).get("top_repositories", [])
                repo_summary = summarize_repositories(repos, cfg)
                prev = previous_map.get(norm_login, {})
                contribs = {
                    "recent_total_contributions": int(prev.get("recent_total_contributions", 0) or 0),
                    "recent_pull_requests": int(prev.get("recent_pull_requests", 0) or 0),
                    "recent_issues": int(prev.get("recent_issues", 0) or 0),
                    "recent_commits": int(prev.get("recent_commits", 0) or 0),
                    "recent_reviews": int(prev.get("recent_reviews", 0) or 0),
                }
            else:
                repos = get_user_repos(login, max_repos=repo_scan_cap, cache=cache)
                repo_summary = summarize_repositories(repos, cfg)
                contribs = get_contribs(login, start, now)

            last_active_at = _choose_last_active(user, repo_summary)
            rows.append({
                "login": login,
                "name": user.get("name"),
                "profile_url": user.get("html_url"),
                "location": user.get("location"),
                "followers": int(user.get("followers", 0) or 0),
                "public_repos": int(user.get("public_repos", 0) or 0),
                "updated_at": user.get("updated_at"),
                **repo_summary,
                **contribs,
                "last_active_at": last_active_at,
                "last_collected_at": now.isoformat().replace("+00:00", "Z"),
            })
        except Exception as exc:
            rows.append({"login": login, "error": str(exc)})

    scored = [r for r in rows if "error" not in r]
    _compute_growth(scored, previous_devs)

    for metric in weights.keys():
        normalize(scored, metric)

    for r in scored:
        score = sum((r.get(f"norm_{m}", 0.0) * w) for m, w in weights.items())
        r["composite_score"] = round(score, 6)
        r["activity_score"] = r["composite_score"]
        r.setdefault("skills", [])
        r.setdefault("languages", [])
        r.setdefault("expertise_tags", [])
        r.setdefault("primary_languages", [])

    scored.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, r in enumerate(scored[:top_n], start=1):
        r["rank"] = i

    timeline = _load_activity_timeline(limit=int(cfg.get("activity_timeline_days", 30)))
    aggregates = _build_aggregates(scored, previous_devs, timeline)

    payload = {
        "run_date": now.date().isoformat(),
        "generated_at": now.isoformat(),
        "lookback_days": lookback_days,
        "top_n": top_n,
        "candidate_count": len(candidates),
        "published_count": len(scored),
        "metrics": {"weights": weights},
        "api_budget": dict(API_STATS),
        "full_refresh": full_refresh,
        "developers": scored,
        "aggregates": aggregates,
        "errors": [r for r in rows if "error" in r],
    }

    _write_json(os.path.join(DATA_DIR, f"{now.date().isoformat()}.json"), payload)
    _write_json(AUTOMATED_PATH, payload)
    _write_json(CACHE_PATH, cache)
    build_site_outputs(payload, cfg)

    print(os.path.join(DATA_DIR, f"{now.date().isoformat()}.json"))


if __name__ == "__main__":
    main()
