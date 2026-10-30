import os
import json
import re
import sys
import yaml
import requests

def load_config():
    with open('config/metrics.json', 'r') as f:
        return json.load(f)

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []

def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

CHECKBOX_RE = re.compile(r'^- \[( |x|X)\]\s*(.*)$')

def parse_issue_body(body):
    # parse Markdown issue form bodies before falling back to YAML
    if '###' in body:
        return _parse_markdown_sections(body)
    try:
        parsed = yaml.safe_load(body)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}

def _parse_markdown_sections(body):
    result = {}
    for section in re.split(r'^###\s+', body, flags=re.MULTILINE)[1:]:
        lines = section.strip().splitlines()
        if not lines:
            continue
        # Normalize issue form labels to snake_case form IDs
        key = re.sub(r'[\s-]+', '_', lines[0].strip().lower())
        values = [line.strip() for line in lines[1:] if line.strip()]
        checkbox_matches = [CHECKBOX_RE.match(value) for value in values]
        if values and all(checkbox_matches):
            result[key] = {
                match.group(2).strip(): match.group(1).lower() == 'x'
                for match in checkbox_matches
            }
        else:
            result[key] = '\n'.join(values)
    return result

def main():
    issue_number = os.getenv('ISSUE_NUMBER')
    issue_title = os.getenv('ISSUE_TITLE')
    issue_body = os.getenv('ISSUE_BODY')
    labels = os.getenv('ISSUE_LABELS', '').split(',')
    github_token = os.getenv('GITHUB_TOKEN')

    if not issue_body:
        print("Error: ISSUE_BODY not set")
        sys.exit(1)

    config = load_config()
    users = load_data('data/users.json')
    removed_users = load_data('data/removed_users.json')
    
    parsed_body = parse_issue_body(issue_body)
    
    if 'add-developer' in labels:
        username = parsed_body.get('github_username', '').strip()
        location = parsed_body.get('location', '').lower()
        
        if not username:
            print("PROFILE_NOT_FOUND")
            sys.exit(0)
            
        # Check if blocked
        if any(u.get('github_username', '').lower() == username.lower() for u in removed_users):
            print("BLOCKED")
            sys.exit(0)
            
        # Check if duplicate
        if any(u.get('github_username', '').lower() == username.lower() for u in users):
            print("DUPLICATE")
            sys.exit(0)
            
        # Validate location
        location_aliases = config.get('location_aliases', [])
        if not any(alias in location for alias in location_aliases):
            print("INVALID_LOCATION")
            sys.exit(0)
            
        # Fetch profile
        headers = {'Authorization': f'token {github_token}'} if github_token else {}
        resp = requests.get(f"https://api.github.com/users/{username}", headers=headers)
        
        if resp.status_code != 200:
            print("PROFILE_NOT_FOUND")
            sys.exit(0)
            
        user_data = resp.json()
        new_user = {
            "github_username": user_data['login'],
            "name": user_data.get('name') or user_data['login'],
            "profile_url": f"https://github.com/{user_data['login']}",
            "location": user_data.get('location') or "",
            "followers": user_data.get('followers', 0),
            "public_repos": user_data.get('public_repos', 0)
        }
        
        users.append(new_user)
        users.sort(key=lambda x: x['github_username'].lower())
        save_data('data/users.json', users)
        print("ADDED")
        sys.exit(0)
        
    elif 'remove-developer' in labels:
        # ...
        username = parsed_body.get('github_username', '').strip()
        self_removal_raw = parsed_body.get('self_removal')
        if isinstance(self_removal_raw, dict):
            self_removal = any(self_removal_raw.values())
        else:
            self_removal = bool(self_removal_raw)
        
        user_to_remove = next((u for u in users if u['github_username'].lower() == username.lower()), None)
        
        if not user_to_remove:
            print("NOT_FOUND")
            sys.exit(0)
            
        if self_removal:
            users = [u for u in users if u['github_username'].lower() != username.lower()]
            removed_users.append({
                "github_username": user_to_remove['github_username'],
                "reason": "self_removal"
            })
            save_data('data/users.json', users)
            save_data('data/removed_users.json', removed_users)
            print("REMOVED")
            sys.exit(0)
        else:
            print("MANUAL_REVIEW")
            sys.exit(0)
            
    else:
        print("NO_ACTION")
        sys.exit(0)

if __name__ == "__main__":
    main()
