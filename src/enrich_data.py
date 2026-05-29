import os
import json
import sys
import time
from datetime import datetime, timedelta, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class TokenManager:
    def __init__(self, tokens):
        self.tokens = [t for t in tokens if t]
        self.current_index = 0
        self.limits = {t: 5000 for t in self.tokens} # Default assumption

    def get_token(self):
        if not self.tokens: return None
        return self.tokens[self.current_index]

    def update_limit(self, token, remaining):
        self.limits[token] = int(remaining)
        if self.limits[token] < 10:
            self.rotate()

    def rotate(self):
        if len(self.tokens) > 1:
            self.current_index = (self.current_index + 1) % len(self.tokens)
            print(f"Switching to token {self.current_index + 1}/{len(self.tokens)}")

def load_config():
    with open('config/metrics.json', 'r') as f:
        return json.load(f)

def load_users():
    with open('data/users.json', 'r') as f:
        return json.load(f)

def load_enriched():
    if os.path.exists('data/users-enriched.json'):
        with open('data/users-enriched.json', 'r') as f:
            return {u['github_username'].lower(): u for u in json.load(f)}
    return {}

def save_enriched(enriched_list):
    with open('data/users-enriched.json', 'w') as f:
        json.dump(enriched_list, f, indent=2)
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    with open(f'data/{today}.json', 'w') as f:
        json.dump(enriched_list, f, indent=2)

GRAPHQL_FRAGMENT = """
fragment UserProfile on User {
  login name avatarUrl bio location company websiteUrl createdAt
  followers { totalCount }
  following { totalCount }
  repositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}, isFork: false) {
    nodes {
      name description url stargazerCount forkCount
      primaryLanguage { name }
      repositoryTopics(first: 5) { nodes { topic { name } } }
      pushedAt isArchived isFork
    }
    totalCount
  }
  contributionsCollection {
    totalCommitContributions totalPullRequestContributions
    totalIssueContributions totalPullRequestReviewContributions
    restrictedContributionsCount
    contributionCalendar { totalContributions }
  }
}
"""

def build_query(usernames):
    nodes = []
    for i, username in enumerate(usernames):
        nodes.append(f"user{i}: user(login: \"{username}\") {{ ...UserProfile }}")
    
    return f"""
    {GRAPHQL_FRAGMENT}
    query {{
      {chr(10).join(nodes)}
    }}
    """

def fetch_batch(usernames, token_manager, session):
    query = build_query(usernames)
    
    # Try all tokens if necessary
    for _ in range(len(token_manager.tokens)):
        token = token_manager.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = session.post("https://api.github.com/graphql", json={"query": query}, headers=headers, timeout=45)
            
            # Update rate limit info
            remaining = resp.headers.get('X-RateLimit-Remaining')
            if remaining:
                token_manager.update_limit(token, remaining)

            if resp.status_code == 200:
                data = resp.json().get('data', {})
                if data: return data
            elif resp.status_code in [403, 429]:
                print(f"Token {token[:8]}... rate limited, rotating...")
                token_manager.rotate()
                continue
            else:
                print(f"Error fetching batch: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            print(f"Request failed: {str(e)}")
            
    return None

def fetch_with_recursion(batch, token_manager, session):
    data = fetch_batch(batch, token_manager, session)
    if data: return data
    
    if len(batch) > 1:
        print(f"Batch of {len(batch)} failed, splitting into half...")
        mid = len(batch) // 2
        d1 = fetch_with_recursion(batch[:mid], token_manager, session)
        d2 = fetch_with_recursion(batch[mid:], token_manager, session)
        
        combined = {}
        if d1: combined.update(d1)
        if d2: combined.update(d2)
        return combined
    return None

def compute_activity_score(user, config, stats_min_max):
    weights = config['scoring_weights']
    metrics = {
        'contributions': user.get('contributions_last_90d', 0),
        'followers': user.get('followers', 0),
        'pull_requests': user.get('prs_last_90d', 0),
        'stars': user.get('total_stars', 0),
        'public_repos': user.get('public_repos', 0),
        'commits': user.get('commits_last_90d', 0),
        'issues': user.get('issues_last_90d', 0),
        'reviews': user.get('reviews_last_90d', 0)
    }
    
    score = 0
    for key, weight in weights.items():
        val = metrics.get(key, 0)
        min_val = stats_min_max[key]['min']
        max_val = stats_min_max[key]['max']
        if max_val > min_val:
            normalized = (val - min_val) / (max_val - min_val)
        else:
            normalized = 0
        score += normalized * weight
    return round(score * 100, 2)

def main():
    force = '--force' in sys.argv
    raw_tokens = os.getenv('GH_TOKENS', '').split(',')
    if not any(raw_tokens):
        raw_tokens = [os.getenv('GITHUB_TOKEN')]
    
    token_manager = TokenManager(raw_tokens)
    
    # Setup resilient session
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    config = load_config()
    users = load_users()
    enriched_map = load_enriched()
    
    to_enrich = []
    now = datetime.now(timezone.utc)
    
    all_users_to_check = {}
    for user in users:
        all_users_to_check[user['github_username'].lower()] = user['github_username']
    for user in enriched_map.values():
        all_users_to_check[user['github_username'].lower()] = user['github_username']
    
    for username_lower, username in all_users_to_check.items():
        if username_lower in enriched_map and not force:
            user_record = enriched_map[username_lower]
            enriched_at_str = user_record.get('enriched_at') or user_record.get('last_repo_fetched_at')
            if enriched_at_str:
                enriched_at = datetime.fromisoformat(enriched_at_str)
                if now - enriched_at < timedelta(hours=24):
                    continue
        to_enrich.append(username)
        
    print(f"Enriching {len(to_enrich)} users...")
    
    batch_size = 10 # Reduced for stability
    for i in range(0, len(to_enrich), batch_size):
        batch = to_enrich[i:i+batch_size]
        data = fetch_with_recursion(batch, token_manager, session)
        
        if not data:
            print(f"Failed to fetch batch starting with {batch[0]}, skipping...")
            continue
            
        for key, raw_user in data.items():
            if not raw_user: continue
            
            login = raw_user['login']
            repos = [r for r in raw_user['repositories']['nodes'] if r]
            total_stars = sum(r.get('stargazerCount', 0) for r in repos)
            
            langs = set()
            for r in repos:
                if r.get('primaryLanguage'):
                    langs.add(r['primaryLanguage']['name'])
            
            contribs = raw_user.get('contributionsCollection') or {}
            
            enriched_user = {
                "github_username": login,
                "name": raw_user.get('name') or login,
                "profile_url": f"https://github.com/{login}",
                "location": raw_user.get('location') or "",
                "avatar_url": raw_user.get('avatarUrl'),
                "bio": raw_user.get('bio') or "",
                "company": raw_user.get('company') or "",
                "website_url": raw_user.get('websiteUrl') or "",
                "followers": raw_user['followers']['totalCount'],
                "following": raw_user['following']['totalCount'],
                "public_repos": raw_user['repositories']['totalCount'],
                "total_stars": total_stars,
                "top_repos": [
                    {
                        "name": r.get('name'),
                        "description": r.get('description') or "",
                        "url": r.get('url'),
                        "stars": r.get('stargazerCount', 0),
                        "forks": r.get('forkCount', 0),
                        "language": r['primaryLanguage']['name'] if r.get('primaryLanguage') else None,
                        "topics": [t['topic']['name'] for t in r['repositoryTopics']['nodes'] if t and t.get('topic')],
                        "pushed_at": r.get('pushedAt')
                    } for r in repos
                ],
                "top_language": list(langs)[0] if langs else None,
                "all_languages": list(langs),
                "contributions_last_90d": contribs.get('contributionCalendar', {}).get('totalContributions', 0),
                "prs_last_90d": contribs.get('totalPullRequestContributions', 0),
                "issues_last_90d": contribs.get('totalIssueContributions', 0),
                "reviews_last_90d": contribs.get('totalPullRequestReviewContributions', 0),
                "commits_last_90d": contribs.get('totalCommitContributions', 0),
                "enriched_at": now.isoformat()
            }
            enriched_map[login.lower()] = enriched_user

    if not enriched_map:
        print("No users to enrich.")
        return

    key_map = {
        'contributions': 'contributions_last_90d',
        'followers': 'followers',
        'pull_requests': 'prs_last_90d',
        'stars': 'total_stars',
        'public_repos': 'public_repos',
        'commits': 'commits_last_90d',
        'issues': 'issues_last_90d',
        'reviews': 'reviews_last_90d'
    }

    stats_min_max = {}
    for config_key, data_key in key_map.items():
        vals = [u.get(data_key, 0) for u in enriched_map.values()]
        stats_min_max[config_key] = {
            'min': min(vals) if vals else 0,
            'max': max(vals) if vals else 0
        }

    enriched_list = []
    for user in enriched_map.values():
        user['activity_score'] = compute_activity_score(user, config, stats_min_max)
        enriched_list.append(user)
        
    enriched_list.sort(key=lambda x: x['activity_score'], reverse=True)
    save_enriched(enriched_list)
    print(f"Successfully enriched {len(enriched_list)} users.")

if __name__ == "__main__":
    main()
