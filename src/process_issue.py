import os
import sys
import json
import re
from pathlib import Path
import requests

DATA_PATH = Path(__file__).parent.parent / "data" / "users.json"
REMOVED_DATA_PATH = Path(__file__).parent.parent / "data" / "removed_users.json"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "metrics.json"

TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": os.getenv("GITHUB_APP_NAME", "bd-github-collector")
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Helper to load config
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)
location_aliases = set([l.lower() for l in config.get("location_aliases", [])])

# Load current users
if DATA_PATH.exists():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        users = json.load(f)
else:
    users = []

# Load removed users
if REMOVED_DATA_PATH.exists():
    with open(REMOVED_DATA_PATH, "r", encoding="utf-8") as f:
        removed_users = json.load(f)
else:
    removed_users = {}

def get_github_stats(username):
    try:
        # Get basic user info
        u_resp = requests.get(f"https://api.github.com/users/{username}", headers=HEADERS, timeout=10)
        u_resp.raise_for_status()
        user_data = u_resp.json()
        
        # Get repos for stars
        r_resp = requests.get(f"https://api.github.com/users/{username}/repos", 
                              headers=HEADERS, params={"per_page": 100, "sort": "updated"}, timeout=10)
        r_resp.raise_for_status()
        repos = r_resp.json()
        stars_sum = sum(r.get("stargazers_count", 0) for r in repos)
        
        return {
            "name": user_data.get("name") or user_data.get("login"),
            "followers": user_data.get("followers", 0),
            "public_repos": user_data.get("public_repos", 0),
            "recent_repo_stars_sum": stars_sum,
            "profile_url": user_data.get("html_url"),
            "location": user_data.get("location") or "Bangladesh"
        }
    except Exception as e:
        print(f"ERROR fetching stats for {username}: {e}")
        return None

def parse_issue(title, body):
    # Extract fields from issue body using regex for YAML/Markdown headers
    fields = {}
    current_key = None
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # Check for header-style keys (e.g. ### GitHub Username)
        if line.startswith("### "):
            # Normalize key: lower, replace spaces and hyphens with underscores
            current_key = line[4:].strip().lower().replace(" ", "_").replace("-", "_")
        elif current_key:
            # Handle checkbox lines like "- [x] I have read..."
            if line.startswith("- [") and "]" in line:
                is_checked = "[x]" in line.lower()
                if "self_removal" in current_key:
                    fields["self_removal"] = "true" if is_checked else "false"
                else:
                    fields[current_key] = "true" if is_checked else "false"
            elif current_key not in fields:
                fields[current_key] = line
            else:
                fields[current_key] += "\n" + line
    
    # Fallback to old format if no fields found via headers
    if not fields:
        for line in body.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                normalized_k = k.strip().lower().replace(" ", "_").replace("-", "_")
                fields[normalized_k] = v.strip()
    return fields

def normalize_username(username):
    if not username:
        return ""
    # GitHub handles dots and hyphens interchangeably in some contexts, 
    # and users often confuse them. Normalizing to hyphens for comparison.
    return username.lower().replace(".", "-").strip()

def is_duplicate(username):
    norm_username = normalize_username(username)
    return any(normalize_username(u.get("github_username", "")) == norm_username for u in users)

def is_removed(username):
    norm_username = normalize_username(username)
    return norm_username in removed_users

def add_developer(fields, title):
    username = fields.get("github_username") or fields.get("username")
    location_input = fields.get("location", "").lower()
    
    # Extract name from title if it follows "Add developer: [Username]"
    # (Backward compatibility with old issues)
    name_from_title = None
    if ":" in title:
        name_from_title = title.split(":", 1)[1].strip()
    
    if not username:
        if name_from_title and "developer" not in name_from_title.lower():
            username = name_from_title
            print(f"Falling back to title for username: {username}")
        else:
            print("Missing required fields (username).")
            return False

    if is_removed(username):
        reason = removed_users[normalize_username(username)].get("reason", "No reason provided")
        print(f"REMOVAL_ALERT: User {username} cannot be added because they were previously removed. Reason: {reason}")
        return False

    # Construct profile URL
    profile_url = fields.get("profile_url") or fields.get("github_profile_url") or f"https://github.com/{username}"

    # Check if any allowed location alias is present in the input location string
    location_valid = any(alias.lower() in location_input for alias in location_aliases)
    
    if not location_valid:
        print(f"Location '{location_input}' not allowed. Must contain one of: {', '.join(location_aliases)}")
        return False
    if is_duplicate(username):
        print(f"Duplicate entry for {username}.")
        return False
    
    # Fetch real-time stats
    print(f"Fetching real-time stats for {username}...")
    stats = get_github_stats(username)
    if stats:
        dev_entry = {
            "name": stats["name"],
            "github_username": username,
            "profile_url": stats["profile_url"],
            "location": stats["location"],
            "followers": stats["followers"],
            "public_repos": stats["public_repos"],
            "recent_repo_stars_sum": stats["recent_repo_stars_sum"]
        }
        print(f"Fetched stats: {stats['followers']} followers, {stats['public_repos']} repos, {stats['recent_repo_stars_sum']} stars.")
    else:
        # Fallback if API fails
        print("Fallback to manual info due to API failure.")
        dev_entry = {
            "name": name_from_title or username,
            "github_username": username,
            "profile_url": profile_url or f"https://github.com/{username}",
            "location": fields.get("location") or "Bangladesh",
            "followers": 0,
            "public_repos": 0,
            "recent_repo_stars_sum": 0
        }
    
    users.append(dev_entry)
    return True

def remove_developer(fields, issue_author, repo_owner):
    username = fields.get("github_username") or fields.get("username")
    reason = fields.get("reason_for_removal") or fields.get("reason") or "Manual removal"
    
    if not username:
        print(f"DEBUG: Fields found: {list(fields.keys())}")
        print("Missing username for removal.")
        return False
    
    # Normalize for comparison
    norm_username = normalize_username(username)
    norm_author = normalize_username(issue_author)
    norm_owner = normalize_username(repo_owner)
    
    # Self-removal: issue author matches username
    is_self = norm_username == norm_author
    is_owner = norm_author == norm_owner
    confirmed = fields.get("self_removal") == "true"
    
    print(f"DEBUG: norm_username={norm_username}, norm_author={norm_author}, is_self={is_self}, is_owner={is_owner}, confirmed={confirmed}")
    
    if (is_self and confirmed) or is_owner:
        initial_count = len(users)
        # Find the user data before removing
        removed_user_data = next((u for u in users if normalize_username(u.get("github_username", "")) == norm_username), None)
        
        users[:] = [u for u in users if normalize_username(u.get("github_username", "")) != norm_username]
        
        if len(users) < initial_count:
            # Save to removed_users.json
            removed_users[norm_username] = {
                "github_username": username,
                "reason": reason,
                "removed_by": issue_author,
                "is_self": is_self
            }
            print(f"Removed {username} from the list. Reason: {reason}")
            return True
        else:
            # Even if not in users.json, we might want to mark it as removed to prevent automated addition
            removed_users[norm_username] = {
                "github_username": username,
                "reason": reason,
                "removed_by": issue_author,
                "is_self": is_self
            }
            print(f"User {username} marked as removed (was not in the active list).")
            return True
    elif is_self and not confirmed:
        print("Self-removal requested but confirmation checkbox not checked.")
        return False
    
    # Third-party removal: require manual review
    print(f"MANUAL_REVIEW: Third-party removal (Author: {issue_author}, Target: {username}).")
    return False

def main():
    if len(sys.argv) < 5:
        print("Usage: python src/process_issue.py <number> <title> <body> <author> [repo_owner]")
        return
    issue_number, title, body, issue_author = sys.argv[1:5]
    repo_owner = sys.argv[5] if len(sys.argv) > 5 else ""
    
    title_lower = title.lower()
    is_add = "add developer" in title_lower
    is_remove = "remove developer" in title_lower
    
    fields = parse_issue(title, body)
    changed = False
    if is_add:
        changed = add_developer(fields, title)
    elif is_remove:
        changed = remove_developer(fields, issue_author, repo_owner)
    else:
        print(f"Issue title '{title}' doesn't specify 'Add developer' or 'Remove developer'.")
    
    if changed:
        # Save users.json
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        # Save removed_users.json
        with open(REMOVED_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(removed_users, f, ensure_ascii=False, indent=2)
            
        print("users.json and removed_users.json updated.")
    else:
        print("No changes made.")

if __name__ == "__main__":
    main()
