import json
import sys
import os

def validate_data():
    file_path = 'data/users.json'
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        sys.exit(1)
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse {file_path}: {e}")
        sys.exit(1)
        
    if not isinstance(users, list):
        print(f"Error: {file_path} must be a JSON array.")
        sys.exit(1)
        
    usernames = set()
    errors = []
    
    for i, user in enumerate(users):
        username = user.get('github_username')
        
        # Requirement: github_username is required and non-empty
        if not username:
            errors.append(f"Entry {i}: Missing or empty 'github_username'")
            continue
            
        # Requirement: no duplicates by username
        if username.lower() in usernames:
            errors.append(f"Entry {i}: Duplicate username '{username}'")
        usernames.add(username.lower())
        
        # Requirement: profile_url matches https://github.com/{username} (case-insensitive)
        expected_url = f"https://github.com/{username}"
        actual_url = user.get('profile_url', '')
        if actual_url.lower() != expected_url.lower():
            errors.append(f"Entry {i} ({username}): URL mismatch. Expected {expected_url}, got {actual_url}")
            
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)
        
    print(f"Successfully validated {len(users)} users.")
    sys.exit(0)

if __name__ == "__main__":
    validate_data()
