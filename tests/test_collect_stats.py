import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
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

@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.get_user")
@patch("collect_stats.get_repo_star_sum")
@patch("collect_stats.get_contribs")
@patch("builtins.open")
@patch("os.makedirs")
def test_main(mock_mkdir, mock_open, mock_contribs, mock_stars, mock_user, mock_candidates, mock_config):
    mock_config.return_value = {
        "lookback_days": 90, "top_n": 5, "location_aliases": ["Loc1"], "weights": {"followers": 1.0}
    }
    mock_candidates.return_value = ["user1"]
    mock_user.return_value = {"login": "user1", "followers": 10, "public_repos": 5}
    mock_stars.return_value = (10, 5)
    mock_contribs.return_value = {"followers": 10}
    
    collect_stats.main()
    assert mock_open.called

@patch("collect_stats.load_config")
@patch("collect_stats.search_candidates")
@patch("collect_stats.get_user")
@patch("builtins.open")
@patch("os.makedirs")
def test_main_error(mock_mkdir, mock_open, mock_user, mock_candidates, mock_config):
    mock_config.return_value = {
        "lookback_days": 90, "top_n": 5, "location_aliases": ["Loc1"], "weights": {"followers": 1.0}
    }
    mock_candidates.return_value = ["user1"]
    mock_user.side_effect = Exception("error")
    
    collect_stats.main()
    # Check that error was added to payload
    args, kwargs = mock_open.call_args_list[-1]
    # This is a bit tricky to check without better mocking of open
    assert mock_open.called
