import json
import os

def build_index():
    enriched_path = 'data/users-enriched.json'
    index_path = 'data/search-index.json'
    
    if not os.path.exists(enriched_path):
        print(f"Error: {enriched_path} not found.")
        return
        
    with open(enriched_path, 'r') as f:
        users = json.load(f)
        
    search_index = []
    for user in users:
        # Normalize fields
        username = user.get('github_username') or user.get('username')
        name = user.get('name') or username
        bio = user.get('bio', '')
        
        # Handle repos and stars
        repos = user.get('top_repos') or user.get('featured_repos') or []
        total_stars = user.get('total_stars')
        if total_stars is None:
            total_stars = sum((r.get('stars') or r.get('stargazerCount') or 0) for r in repos)
            
        # Handle languages
        all_langs = user.get('all_languages') or user.get('top_languages') or []
        top_lang = user.get('top_language')
        if not top_lang and all_langs:
            top_lang = all_langs[0]
            
        topics = set()
        for repo in repos:
            for topic in repo.get('topics', []):
                topics.add(topic)
                
        search_index.append({
            "u": username,
            "n": name,
            "b": bio,
            "l": top_lang or '',
            "al": all_langs,
            "t": list(topics),
            "s": user.get('activity_score', 0),
            "f": user.get('followers', 0),
            "r": user.get('public_repos', 0)
        })
        
    with open(index_path, 'w') as f:
        json.dump(search_index, f, separators=(',', ':'))
        
    print(f"Successfully built search index with {len(search_index)} users.")
    print(f"Index size: {os.path.getsize(index_path) / 1024:.2f} KB")

if __name__ == "__main__":
    build_index()
