import os
import json
import glob
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
README_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")

AWESOME_BADGE = "[![Awesome](https://awesome.re/badge.svg)](https://awesome.re)"
VISITOR_BADGE = "![Views Count](https://komarev.com/ghpvc/?username=sharf-shawon-abd&label=Views&color=blue&style=flat-square)"
BUILD_STATUS = "[![Pipeline Status](https://github.com/sharf-shawon/Awesome-Bangladeshi-Devs/actions/workflows/pipeline.yml/badge.svg)](https://github.com/sharf-shawon/Awesome-Bangladeshi-Devs/actions/workflows/pipeline.yml)"
STATS_STATUS = "[![Stats Collection Status](https://github.com/sharf-shawon/Awesome-Bangladeshi-Devs/actions/workflows/collect-stats.yml/badge.svg)](https://github.com/sharf-shawon/Awesome-Bangladeshi-Devs/actions/workflows/collect-stats.yml)"
LAST_COMMIT = "![Last Commit](https://img.shields.io/github/last-commit/sharf-shawon/Awesome-Bangladeshi-Devs)"
LICENSE_BADGE = "![License](https://img.shields.io/github/license/sharf-shawon/Awesome-Bangladeshi-Devs)"

GOAL = (
    "## Goal & Use Case\n\n"
    "<details>\n"
    "<summary>Expand to learn more</summary>\n\n"
    "This repository is a **data-driven directory** of the Bangladeshi developer community on GitHub. "
    "We aim to highlight impactful contributors, discover rising talent, and provide a platform for developers to showcase their work. "
    "It serves as a resource for finding collaborators, mentors, and exploring the local open-source ecosystem.\n"
    "</details>"
)

HOW_TO_JOIN = (
    "## How to Join\n\n"
    "1. Open an Issue: [Add Developer](https://github.com/sharf-shawon/Awesome-Bangladeshi-Devs/issues/new?template=add_developer.yml)\n"
    "2. Submit: Fill in your username and location.\n"
    "3. Done: Our automation handles the rest!"
)

HOW_IT_WORKS = (
    "## How it Works\n\n"
    "<details>\n"
    "<summary>Expand for ranking details</summary>\n\n"
    "Profiles are ranked using a **weighted composite score** based on the last 90 days of GitHub activity:\n\n"
    "- 35% Contributions: Total activity (commits, PRs, issues, etc.).\n"
    "- 20% Followers: Impact and reach.\n"
    "- 10% Pull Requests: Active collaboration.\n"
    "- 10% Stars: Community recognition.\n"
    "- 10% Public Repos: Portfolio size.\n"
    "- 15% Others: Reviews (5%), Issues (5%), and Commits (5%).\n"
    "</details>"
)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def get_stats_data():
    """Returns (latest_stats, previous_stats, latest_date)"""
    # Prefer automated.json as per instructions
    automated_path = os.path.join(DATA_DIR, "automated.json")
    if os.path.exists(automated_path):
        latest_data = load_json(automated_path)
        latest_date = latest_data.get("run_date")
        latest_devs = latest_data.get("developers", []) if isinstance(latest_data, dict) else []
        
        # Look for the previous dated file for growth calculation
        files = sorted(glob.glob(os.path.join(DATA_DIR, "????-??-??.json")), reverse=True)
        previous_devs = []
        if files:
            prev_data = load_json(files[0])
            previous_devs = prev_data.get("developers", []) if isinstance(prev_data, dict) else []
        return latest_devs, previous_devs, latest_date

    files = sorted(glob.glob(os.path.join(DATA_DIR, "????-??-??.json")), reverse=True)
    if not files:
        return [], [], None
    
    latest_file = files[0]
    latest_date = os.path.basename(latest_file).replace(".json", "")
    latest_data = load_json(latest_file)
    latest_devs = latest_data.get("developers", []) if isinstance(latest_data, dict) else []
    
    previous_devs = []
    if len(files) > 1:
        prev_data = load_json(files[1])
        previous_devs = prev_data.get("developers", []) if isinstance(prev_data, dict) else []
        
    return latest_devs, previous_devs, latest_date

def calculate_growth(latest_devs, previous_devs):
    prev_map = {d["login"].lower(): d for d in previous_devs}
    enriched = []
    for dev in latest_devs:
        login_lower = dev["login"].lower()
        prev = prev_map.get(login_lower, {})
        
        # Calculate growth if previous data exists
        dev["followers_growth"] = dev.get("followers", 0) - prev.get("followers", dev.get("followers", 0))
        dev["stars_growth"] = dev.get("recent_repo_stars_sum", 0) - prev.get("recent_repo_stars_sum", dev.get("recent_repo_stars_sum", 0))
        enriched.append(dev)
    return enriched

def format_list_entry(dev, index, rank_type=None):
    login = dev.get("login") or dev.get("github_username") or ""
    name = dev.get("name") or login or "Unknown"
    url = dev.get("profile_url") or f"https://github.com/{login}"
    
    location = (dev.get("location") or "Bangladesh").strip().rstrip(",")
    followers = dev.get("followers", 0)
    repos = dev.get("public_repos", 0)
    stars = dev.get("recent_repo_stars_sum", 0)
    
    growth_str = ""
    if rank_type == "rising_followers" and dev.get("followers_growth", 0) > 0:
        growth_str = f" (+{dev['followers_growth']} this month)"
    elif rank_type == "rising_stars" and dev.get("stars_growth", 0) > 0:
        growth_str = f" (+{dev['stars_growth']} stars this month)"
    
    return f"{index}. [{name}]({url}) - {location}, {followers} followers{growth_str}, {repos} public repos, {stars} stars."

def section(title, entries, level=3):
    prefix = "#" * level
    return f"{prefix} {title}\n\n" + "\n".join(entries)

def main():
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "metrics.json")
    cfg = load_json(config_path)
    if not isinstance(cfg, dict): cfg = {}
    top_n = cfg.get("top_n", 25)

    latest_devs, previous_devs, latest_date = get_stats_data()
    user_devs = load_json(os.path.join(DATA_DIR, "users.json"))
    if not isinstance(user_devs, list): user_devs = []

    # Filter out removed users from all sources
    removed_data = load_json(os.path.join(DATA_DIR, "removed_users.json"))
    removed_logins = set(removed_data.keys()) if isinstance(removed_data, dict) else set()

    latest_devs = [d for d in latest_devs if d["login"].lower().replace(".", "-").strip() not in removed_logins]
    previous_devs = [d for d in previous_devs if d["login"].lower().replace(".", "-").strip() not in removed_logins]
    user_devs = [d for d in user_devs if d.get("github_username", "").lower().replace(".", "-").strip() not in removed_logins]

    if not latest_devs:
        # Fallback
        all_devs_sorted = sorted(user_devs, key=lambda d: (d.get("name") or d.get("github_username", "")).lower())
        directory_entries = [format_list_entry(d, i+1, "fallback") for i, d in enumerate(all_devs_sorted)]
        content = [
            "## Directory of Awesome Bangladeshi Developers\n\n",
            "*This directory is curated from manual submissions.*\n\n",
            "\n".join(directory_entries)
        ]
        has_stats = False
    else:
        has_stats = True
        enriched_devs = calculate_growth(latest_devs, previous_devs)
        
        # 1. GOATS Subsections
        top_score = sorted(enriched_devs, key=lambda d: d.get("composite_score", 0), reverse=True)[:top_n]
        top_followers = sorted(enriched_devs, key=lambda d: d.get("followers", 0), reverse=True)[:top_n]
        top_stars = sorted(enriched_devs, key=lambda d: d.get("recent_repo_stars_sum", 0), reverse=True)[:top_n]
        top_repos = sorted(enriched_devs, key=lambda d: d.get("public_repos", 0), reverse=True)[:top_n]

        # 2. Rising Stars Subsections
        rising_followers = sorted(enriched_devs, key=lambda d: d.get("followers_growth", 0), reverse=True)[:20]
        rising_stars = sorted(enriched_devs, key=lambda d: d.get("stars_growth", 0), reverse=True)[:20]
        
        # Deduplication for Awesome compliance (each link must appear only once)
        used_links = set()

        def format_unique_entry(dev, rank_type=None):
            url = dev.get("profile_url") or f"https://github.com/{dev.get('login', dev.get('github_username', ''))}"
            if url.lower() in used_links:
                return None
            used_links.add(url.lower())
            return dev

        top_score_devs = [d for d in [format_unique_entry(d, "score") for d in top_score] if d]
        top_followers_devs = [d for d in [format_unique_entry(d, "followers") for d in top_followers] if d]
        top_stars_devs = [d for d in [format_unique_entry(d, "stars") for d in top_stars] if d]
        top_repos_devs = [d for d in [format_unique_entry(d, "repos") for d in top_repos] if d]
        
        goats_content = [
            section(f"Top {top_n} Bangladeshi Developers by Overall Score", 
                    ["*The most active and impactful developers based on a weighted composite of contributions, followers, stars, and activity.*", "", 
                     *[format_list_entry(d, i+1, "score") for i, d in enumerate(top_score_devs)]]),
            "",
            section(f"Top {top_n} Bangladeshi Developers by Followers", 
                    ["*Developers with the most significant reach and community following in the Bangladeshi tech ecosystem.*", "", 
                     *[format_list_entry(d, i+1, "followers") for i, d in enumerate(top_followers_devs)]]),
            "",
            section(f"Top {top_n} Bangladeshi Developers by Stars", 
                    ["*Creators of the most popular and recognized open-source projects, measured by recent repository stars.*", "", 
                     *[format_list_entry(d, i+1, "stars") for i, d in enumerate(top_stars_devs)]]),
            "",
            section(f"Top {top_n} Bangladeshi Developers by Public Repos", 
                    ["*The most prolific contributors with a vast portfolio of public repositories and open-source projects.*", "", 
                     *[format_list_entry(d, i+1, "repos") for i, d in enumerate(top_repos_devs)]])
        ]

        rising_followers_devs = [d for d in [format_unique_entry(d, "rising_followers") for d in rising_followers] if d]
        rising_stars_devs = [d for d in [format_unique_entry(d, "rising_stars") for d in rising_stars] if d]

        rising_content = [
            section("Trending: Most Followers Gained This Month", 
                    ["*Rising talent experiencing the fastest growth in community following and recognition.*", "", 
                     *[format_list_entry(d, i+1, "rising_followers") for i, d in enumerate(rising_followers_devs)]]),
            "",
            section("Trending: Most Stars Gained This Month", 
                    ["*Projects and developers gaining the most community appreciation and traction recently.*", "", 
                     *[format_list_entry(d, i+1, "rising_stars") for i, d in enumerate(rising_stars_devs)]])
        ]

        # 3. Directory
        stats_map = {d["login"].lower(): d for d in enriched_devs}
        directory_candidates = []
        for dev in user_devs:
            login = dev.get("github_username", "").lower()
            if not login: continue
            full_dev = stats_map.get(login, dev)
            if "login" not in full_dev: full_dev["login"] = login
            if "profile_url" not in full_dev: full_dev["profile_url"] = f"https://github.com/{login}"
            directory_candidates.append(full_dev)
            
        directory_candidates.sort(key=lambda d: (d.get("name") or d.get("login", "")).lower())
        directory_devs = [d for d in [format_unique_entry(d, "directory") for d in directory_candidates] if d]
        directory_entries = [format_list_entry(d, i+1, "directory") for i, d in enumerate(directory_devs)]

        content = [
            "## GOATS: Top Bangladeshi Developers\n\n",
            "\n".join(goats_content),
            "",
            "## Rising Stars: Trending Developers\n\n",
            "\n".join(rising_content),
            "",
            "## Directory of Awesome Bangladeshi Developers\n\n",
            "*This directory features developers who are part of our community but not currently in the top rankings.*\n\n",
            "\n".join(directory_entries)
        ]

    # Build README
    lines = [
        f"# Awesome Bangladeshi Developers {AWESOME_BADGE}",
        "Discover the top Bangladeshi open-source contributors, GitHub leaders, and rising software talent.",
        "",
        f"{BUILD_STATUS} {STATS_STATUS} {VISITOR_BADGE} {LAST_COMMIT} {LICENSE_BADGE}",
        "",
        "A curated, data-driven directory of the most impactful and active Bangladeshi developers on GitHub.",
        "",
        "## Contents",
        ""
    ]
    
    if has_stats:
        lines += [
            "- [Goal & Use Case](#goal--use-case)",
            "- [How to Join](#how-to-join)",
            "- [How it Works](#how-it-works)",
            "- [GOATS: Top Bangladeshi Developers](#goats-top-bangladeshi-developers)",
            f"  - [Top {top_n} Bangladeshi Developers by Overall Score](#top-{top_n}-bangladeshi-developers-by-overall-score)",
            f"  - [Top {top_n} Bangladeshi Developers by Followers](#top-{top_n}-bangladeshi-developers-by-followers)",
            f"  - [Top {top_n} Bangladeshi Developers by Stars](#top-{top_n}-bangladeshi-developers-by-stars)",
            f"  - [Top {top_n} Bangladeshi Developers by Public Repos](#top-{top_n}-bangladeshi-developers-by-public-repos)",
            "- [Rising Stars: Trending Developers](#rising-stars-trending-developers)",
            "  - [Trending: Most Followers Gained This Month](#trending-most-followers-gained-this-month)",
            "  - [Trending: Most Stars Gained This Month](#trending-most-stars-gained-this-month)",
            "- [Directory of Awesome Bangladeshi Developers](#directory-of-awesome-bangladeshi-developers)"
        ]
    else:
        lines += [
            "- [Goal & Use Case](#goal--use-case)",
            "- [How to Join](#how-to-join)",
            "- [How it Works](#how-it-works)",
            "- [Directory of Awesome Bangladeshi Developers](#directory-of-awesome-bangladeshi-developers)"
        ]

    lines += [
        "",
        "",
        GOAL,
        "",
        HOW_TO_JOIN,
        "",
        HOW_IT_WORKS,
        "",
        ""
    ]
    
    lines.extend(content)
    lines += [
        "",
        "## Contributing",
        "",
        f"Contributions welcome! Read our [contribution guidelines](contributing.md) to learn how to add yourself.\n\n Stats last updated: {latest_date or 'N/A'}."
    ]
    
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
