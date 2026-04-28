import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open as stdlib_mock_open
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
    mock_get.return_value = {"items": [{"login": "user1"}]}
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = False
        candidates = collect_stats.search_candidates(["Loc1"])
        assert "user1" in candidates

@patch("collect_stats.gh_get")
def test_search_candidates_removed(mock_get):
    mock_get.return_value = {"items": [{"login": "user1"}]}
    with patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps({"user1": {}})
            candidates = collect_stats.search_candidates(["Loc1"])
            assert "user1" not in candidates

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
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main(mock_open, mock_mkdir, mock_exists, mock_contribs, mock_repo_stats,
              mock_user, mock_load_users, mock_candidates, mock_config):
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = ["user2"]
    mock_user.side_effect = lambda login: _full_user_response(login)
    mock_repo_stats.return_value = (20, 5, ["Python", "JavaScript"])
    mock_contribs.return_value = _full_contribs()
    mock_exists.return_value = False  # no removed_users.json

    collect_stats.main()

    assert mock_open.called
    written = "".join(call.args[0] for call in mock_open().write.call_args_list)
    payload = json.loads(written)

    # Both search candidate and registered user should appear
    logins = [d["login"] for d in payload["developers"]]
    assert "user1" in logins
    assert "user2" in logins

    # All developers should have a rank
    for dev in payload["developers"]:
        assert "rank" in dev

    # Payload metadata
    assert payload["search_candidate_count"] == 1
    assert payload["registered_user_count"] == 1
    assert payload["candidate_count"] == 2

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
@patch("collect_stats.get_user")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_error(mock_open, mock_mkdir, mock_exists, mock_user,
                    mock_load_users, mock_candidates, mock_config):
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = []
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
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_deduplicates_users(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                  mock_repo_stats, mock_user, mock_load_users,
                                  mock_candidates, mock_config):
    """Users in both search results and users.json should only appear once."""
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = ["user1"]  # same login as search result
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
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_removed_users_excluded(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                      mock_repo_stats, mock_user, mock_load_users,
                                      mock_candidates, mock_config):
    """Removed users must not appear in the output even if present in users.json."""
    mock_config.return_value = _base_config()
    mock_candidates.return_value = ["user1"]
    mock_load_users.return_value = ["removed-dev"]
    mock_user.side_effect = lambda login: _full_user_response(login)
    mock_repo_stats.return_value = (10, 3, [])
    mock_contribs.return_value = _full_contribs()

    # Make os.path.exists return True only for the removed_users.json path
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
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_stats")
@patch("collect_stats.get_contribs")
@patch("os.path.exists")
@patch("os.makedirs")
@patch("builtins.open", new_callable=stdlib_mock_open)
def test_main_all_developers_ranked(mock_open, mock_mkdir, mock_exists, mock_contribs,
                                     mock_repo_stats, mock_user, mock_load_users,
                                     mock_candidates, mock_config):
    """All successful developers must have a rank (not just top_n)."""
    mock_config.return_value = {
        "lookback_days": 90, "top_n": 1, "location_aliases": ["Loc1"],
        "weights": {"followers": 1.0},
    }
    mock_candidates.return_value = ["user1", "user2", "user3"]
    mock_load_users.return_value = []
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

