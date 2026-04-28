import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open as stdlib_mock_open, call
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
import collect_stats

def test_gh_get():
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"a": 1}
        assert collect_stats.gh_get("url") == {"a": 1}

        # Test rate limit
        mock_get.return_value.status_code = 403
        mock_get.return_value.text = "rate limit"
        with pytest.raises(RuntimeError):
            collect_stats.gh_get("url")

def test_gql():
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"data": {"a": 1}}
        assert collect_stats.gql("query") == {"a": 1}

        # Test errors
        mock_post.return_value.json.return_value = {"errors": "error"}
        with pytest.raises(RuntimeError):
            collect_stats.gql("query")

def test_load_config():
    with patch("builtins.open") as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"test": 1})
        assert collect_stats.load_config() == {"test": 1}

@patch("collect_stats.gh_get")
def test_search_candidates(mock_get):
    mock_get.return_value = {"items": [{"login": "user1"}], "total_count": 1}
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False
        candidates = collect_stats.search_candidates(["Loc1"])
        assert "user1" in candidates

@patch("collect_stats.gh_get")
def test_search_candidates_removed(mock_get):
    mock_get.return_value = {"items": [{"login": "user1"}], "total_count": 1}
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"user1": {}})
            candidates = collect_stats.search_candidates(["Loc1"])
            assert "user1" not in candidates

@patch("collect_stats.gh_get")
def test_search_candidates_paginates(mock_get):
    """search_candidates must paginate until all results are fetched."""
    page1 = [{"login": f"u{i}"} for i in range(100)]
    page2 = [{"login": f"u{i}"} for i in range(100, 120)]
    mock_get.side_effect = [
        {"items": page1, "total_count": 120},
        {"items": page2, "total_count": 120},
    ]
    with patch("os.path.exists", return_value=False):
        candidates = collect_stats.search_candidates(["Bangladesh"], per_query=100)
    assert len(candidates) == 120
    assert mock_get.call_count == 2

@patch("collect_stats.gh_get")
def test_search_candidates_stops_at_api_cap(mock_get):
    """search_candidates must stop after 1000 results (GitHub Search API cap)."""
    # Each page has 100 unique logins so deduplication does not obscure the count
    pages = [
        {"items": [{"login": f"u{p * 100 + i}"} for i in range(100)], "total_count": 5000}
        for p in range(11)  # provide 11 pages; only first 10 should be fetched
    ]
    mock_get.side_effect = pages
    with patch("os.path.exists", return_value=False):
        candidates = collect_stats.search_candidates(["Bangladesh"], per_query=100)
    assert len(candidates) == 1000
    assert mock_get.call_count == 10

@patch("collect_stats.gh_get")
def test_search_candidates_stops_on_partial_page(mock_get):
    """search_candidates stops when fewer items than per_page are returned."""
    mock_get.return_value = {
        "items": [{"login": "user1"}, {"login": "user2"}],
        "total_count": 2,
    }
    with patch("os.path.exists", return_value=False):
        candidates = collect_stats.search_candidates(["Bangladesh"], per_query=100)
    assert set(candidates) == {"user1", "user2"}
    assert mock_get.call_count == 1

@patch("collect_stats.gh_get")
def test_search_candidates_empty_page(mock_get):
    """search_candidates stops immediately on an empty first page."""
    mock_get.return_value = {"items": [], "total_count": 0}
    with patch("os.path.exists", return_value=False):
        candidates = collect_stats.search_candidates(["Bangladesh"])
    assert candidates == []

@patch("collect_stats.gh_get")
def test_get_user(mock_get):
    mock_get.return_value = {"login": "user1"}
    assert collect_stats.get_user("user1") == {"login": "user1"}

@patch("collect_stats.gh_get")
def test_get_repo_star_sum(mock_get):
    mock_get.return_value = [{"stargazers_count": 10}, {"stargazers_count": 20}]
    stars, count = collect_stats.get_repo_star_sum("user1")
    assert stars == 30
    assert count == 2

@patch("collect_stats.gh_get")
def test_get_repo_stats(mock_get):
    mock_get.return_value = [
        {"stargazers_count": 10, "language": "Python"},
        {"stargazers_count": 20, "language": "Python"},
        {"stargazers_count": 5, "language": "JavaScript"},
        {"stargazers_count": 0, "language": None},
    ]
    stars, count, langs = collect_stats.get_repo_stats("user1")
    assert stars == 35
    assert count == 4
    assert langs == ["Python", "JavaScript"]

@patch("collect_stats.gh_get")
def test_get_repo_stats_no_repos(mock_get):
    mock_get.return_value = []
    stars, count, langs = collect_stats.get_repo_stats("user1")
    assert stars == 0
    assert count == 0
    assert langs == []

@patch("collect_stats.gql")
def test_get_contribs(mock_gql):
    mock_gql.return_value = {
        "user": {
            "contributionsCollection": {
                "contributionCalendar": {"totalContributions": 100},
                "totalPullRequestContributions": 10,
                "totalIssueContributions": 5,
                "totalCommitContributions": 80,
                "totalPullRequestReviewContributions": 5,
                "startedAt": "2026-01-01T00:00:00Z",
                "endedAt": "2026-04-01T00:00:00Z"
            }
        }
    }
    contribs = collect_stats.get_contribs("user1", datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert contribs["recent_total_contributions"] == 100

def test_normalize():
    rows = [{"val": 10}, {"val": 20}, {"val": 0}]
    collect_stats.normalize(rows, "val")
    assert rows[0]["norm_val"] == 0.5
    assert rows[1]["norm_val"] == 1.0
    assert rows[2]["norm_val"] == 0.0

    # Test all same
    rows2 = [{"val": 10}, {"val": 10}]
    collect_stats.normalize(rows2, "val")
    assert rows2[0]["norm_val"] == 0.0


# --- load_users_from_json ---

def test_load_users_from_json_not_found(tmp_path):
    result = collect_stats.load_users_from_json(str(tmp_path / "missing.json"))
    assert result == []

def test_load_users_from_json_empty(tmp_path):
    p = tmp_path / "users.json"
    p.write_text("[]", encoding="utf-8")
    assert collect_stats.load_users_from_json(str(p)) == []

def test_load_users_from_json_github_username_field(tmp_path):
    users = [
        {"github_username": "Alice", "name": "Alice A"},
        {"github_username": "Bob"},
    ]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    result = collect_stats.load_users_from_json(str(p))
    assert result == ["Alice", "Bob"]

def test_load_users_from_json_login_field(tmp_path):
    users = [{"login": "charlie"}]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    result = collect_stats.load_users_from_json(str(p))
    assert result == ["charlie"]

def test_load_users_from_json_skips_entries_without_login(tmp_path):
    users = [{"name": "No Login"}, {"github_username": "dave"}]
    p = tmp_path / "users.json"
    p.write_text(json.dumps(users), encoding="utf-8")
    result = collect_stats.load_users_from_json(str(p))
    assert result == ["dave"]

def test_load_users_from_json_non_list(tmp_path):
    p = tmp_path / "users.json"
    p.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    assert collect_stats.load_users_from_json(str(p)) == []


# --- load_logins_from_readme ---

def test_load_logins_from_readme_not_found(tmp_path):
    result = collect_stats.load_logins_from_readme(str(tmp_path / "README.md"))
    assert result == []

def test_load_logins_from_readme_extracts_profile_links(tmp_path):
    content = (
        "# README\n\n"
        "1. [Alice](https://github.com/alice?rank=score) - Location.\n"
        "2. [Bob Dev](https://github.com/bob-dev?rank=followers) - Location.\n"
        "3. [Charlie](https://github.com/charlie) - No rank param.\n"
    )
    p = tmp_path / "README.md"
    p.write_text(content, encoding="utf-8")
    result = collect_stats.load_logins_from_readme(str(p))
    assert "alice" in result
    assert "bob-dev" in result
    assert "charlie" in result

def test_load_logins_from_readme_ignores_multi_segment_repo_links(tmp_path):
    content = (
        "[![Badge](https://github.com/owner/repo/actions/badge.svg)]"
        "(https://github.com/owner/repo/actions/badge.svg)\n"
        "[Issues](https://github.com/owner/repo/issues/new?template=foo.yml)\n"
    )
    p = tmp_path / "README.md"
    p.write_text(content, encoding="utf-8")
    result = collect_stats.load_logins_from_readme(str(p))
    # Multi-segment paths must not appear in results
    assert "owner" not in result
    assert "owner/repo" not in result

def test_load_logins_from_readme_deduplicates(tmp_path):
    content = (
        "[Alice](https://github.com/alice?rank=score)\n"
        "[Alice Again](https://github.com/alice?rank=followers)\n"
    )
    p = tmp_path / "README.md"
    p.write_text(content, encoding="utf-8")
    result = collect_stats.load_logins_from_readme(str(p))
    assert result.count("alice") == 1

def test_load_logins_from_readme_empty_file(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("", encoding="utf-8")
    assert collect_stats.load_logins_from_readme(str(p)) == []

def test_load_logins_from_readme_preserves_case(tmp_path):
    """Usernames are case-sensitive on GitHub; preserve original casing."""
    content = "[Dev](https://github.com/MyDev?rank=score)\n"
    p = tmp_path / "README.md"
    p.write_text(content, encoding="utf-8")
    result = collect_stats.load_logins_from_readme(str(p))
    assert "MyDev" in result

def test_load_logins_from_readme_mixed_content(tmp_path):
    """Real-world README snippet: profile links interleaved with badge/action URLs."""
    content = (
        "[![Pipeline](https://github.com/org/repo/actions/pipeline.yml/badge.svg)]"
        "(https://github.com/org/repo/actions/pipeline.yml)\n"
        "1. [Dev One](https://github.com/devone?rank=score) - Dhaka.\n"
        "2. [Dev Two](https://github.com/devtwo?rank=followers) - Bangladesh.\n"
        "[Remove](https://github.com/org/repo/issues/new?template=remove.yml)\n"
    )
    p = tmp_path / "README.md"
    p.write_text(content, encoding="utf-8")
    result = collect_stats.load_logins_from_readme(str(p))
    assert "devone" in result
    assert "devtwo" in result
    assert "org" not in result


# --- main() tests ---

def _base_config():
    return {
        "lookback_days": 90,
        "top_n": 5,
        "location_aliases": ["Loc1"],
        "weights": {"followers": 1.0},
    }

def _full_user_response(login="user1"):
    return {
        "login": login,
        "name": "User One",
        "avatar_url": "https://avatars.githubusercontent.com/u/1",
        "html_url": f"https://github.com/{login}",
        "bio": "Dev",
        "company": "ACME",
        "blog": "https://example.com",
        "twitter_username": "user1",
        "email": "user1@example.com",
        "location": "Dhaka, Bangladesh",
        "hireable": True,
        "followers": 10,
        "following": 5,
        "public_repos": 8,
        "public_gists": 2,
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2026-04-01T00:00:00Z",
    }

def _full_contribs():
    return {
        "recent_total_contributions": 50,
        "recent_pull_requests": 5,
        "recent_issues": 2,
        "recent_commits": 40,
        "recent_reviews": 3,
    }


@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.load_users_from_json")
@patch("collect_stats.load_logins_from_readme")
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main(mock_open, mock_mkdir, mock_exists, mock_contribs, mock_repo_stats,
              mock_user, mock_load_readme, mock_load_users, mock_candidates, mock_config):
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = ["user2"]
    mock_load_readme.return_value = ["user3"]
    mock_user.side_effect = lambda login: _full_user_response(login)
    mock_repo_stats.return_value = (20, 5, ["Python", "JavaScript"])
    mock_contribs.return_value = _full_contribs()
    mock_exists.return_value = False  # no removed_users.json

    collect_stats.main()

    assert mock_open.called
    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)

    # All three sources should appear
    logins = [d["login"] for d in payload["developers"]]
    assert "user1" in logins
    assert "user2" in logins
    assert "user3" in logins

    # All developers should have a rank
    for dev in payload["developers"]:
        assert "rank" in dev

    # Payload metadata
    assert payload["search_candidate_count"] == 1
    assert payload["registered_user_count"] == 1
    assert payload["readme_user_count"] == 1
    assert payload["candidate_count"] == 3

    # Rich fields collected
    dev = next(d for d in payload["developers"] if d["login"] == "user1")
    assert dev["top_languages"] == ["Python", "JavaScript"]
    assert dev["bio"] == "Dev"
    assert dev["company"] == "ACME"
    assert dev["twitter_username"] == "user1"
    assert dev["account_created_at"] == "2020-01-01T00:00:00Z"


@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.load_users_from_json")
@patch("collect_stats.load_logins_from_readme")
@patch("collect_stats.get_user")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_error(mock_open, mock_mkdir, mock_exists, mock_user,
                    mock_load_readme, mock_load_users, mock_candidates, mock_config):
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = []
    mock_load_readme.return_value = []
    mock_user.side_effect = Exception("api error")
    mock_exists.return_value = False

    collect_stats.main()

    assert mock_open.called
    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)
    assert len(payload["errors"]) == 1
    assert payload["errors"][0]["login"] == "user1"
    assert "api error" in payload["errors"][0]["error"]


@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.load_users_from_json")
@patch("collect_stats.load_logins_from_readme")
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_deduplicates_users(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                  mock_repo_stats, mock_user, mock_load_readme,
                                  mock_load_users, mock_candidates, mock_config):
    """Users appearing in multiple sources should only be processed once."""
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = ["user1"]   # same as search
    mock_load_readme.return_value = ["user1"]  # same again
    mock_user.side_effect = lambda login: _full_user_response(login)
    mock_repo_stats.return_value = (10, 3, ["Go"])
    mock_contribs.return_value = _full_contribs()
    mock_exists.return_value = False

    collect_stats.main()

    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)
    logins = [d["login"] for d in payload["developers"]]
    assert logins.count("user1") == 1
    assert payload["candidate_count"] == 1


@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.load_users_from_json")
@patch("collect_stats.load_logins_from_readme")
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_readme_only_user_included(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                         mock_repo_stats, mock_user, mock_load_readme,
                                         mock_load_users, mock_candidates, mock_config):
    """A user present only in the README (not in users.json or search) must be scanned."""
    mock_config.return_value = _base_config()
    mock_candidates.return_value = []
    mock_load_users.return_value = []
    mock_load_readme.return_value = ["readme-only-dev"]
    mock_user.side_effect = lambda login: _full_user_response(login)
    mock_repo_stats.return_value = (5, 2, ["Python"])
    mock_contribs.return_value = _full_contribs()
    mock_exists.return_value = False

    collect_stats.main()

    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)
    logins = [d["login"] for d in payload["developers"]]
    assert "readme-only-dev" in logins
    assert payload["readme_user_count"] == 1


@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.load_users_from_json")
@patch("collect_stats.load_logins_from_readme")
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_removed_users_excluded(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                      mock_repo_stats, mock_user, mock_load_readme,
                                      mock_load_users, mock_candidates, mock_config):
    """Removed users must not appear in the output from any source."""
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = ["removed-dev"]
    mock_load_readme.return_value = ["removed-dev"]
    mock_user.side_effect = lambda login: _full_user_response(login)
    mock_repo_stats.return_value = (10, 3, [])
    mock_contribs.return_value = _full_contribs()

    def exists_side_effect(path):
        return os.path.basename(path) == "removed_users.json"

    mock_exists.side_effect = exists_side_effect

    removed_json = json.dumps({"removed-dev": {}})
    mock_open.return_value.__enter__.return_value.read.return_value = removed_json

    collect_stats.main()

    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)
    logins = [d["login"] for d in payload.get("developers", [])]
    assert "removed-dev" not in logins


@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.load_users_from_json")
@patch("collect_stats.load_logins_from_readme")
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_all_developers_ranked(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                     mock_repo_stats, mock_user, mock_load_readme,
                                     mock_load_users, mock_candidates, mock_config):
    """All successful developers must have a rank (not just top_n)."""
    mock_config.return_value = {
        "lookback_days": 90, "top_n": 1, "location_aliases": ["Loc1"],
        "weights": {"followers": 1.0},
    }
    mock_candidates.return_value = ["user1", "user2", "user3"]
    mock_load_users.return_value = []
    mock_load_readme.return_value = []
    follower_map = {"user1": 10, "user2": 20, "user3": 30}
    mock_user.side_effect = lambda login: {**_full_user_response(login), "followers": follower_map[login]}
    mock_repo_stats.return_value = (0, 0, [])
    mock_contribs.return_value = _full_contribs()
    mock_exists.return_value = False

    collect_stats.main()

    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)
    ranks = [d["rank"] for d in payload["developers"]]
    # All 3 developers should have a rank (top_n=1 should not cap the ranks)
    assert len(ranks) == 3
    assert sorted(ranks) == [1, 2, 3]


