import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
import generate_readme

def test_format_list_entry():
    dev = {
        "name": "Test User",
        "login": "testuser",
        "profile_url": "https://github.com/testuser",
        "location": "Dhaka, Bangladesh",
        "followers": 100,
        "public_repos": 10,
        "recent_repo_stars_sum": 50,
        "followers_growth": 5,
        "stars_growth": 2
    }
    # Test normal entry
    entry = generate_readme.format_list_entry(dev, 1, "directory")
    assert "1. [testuser](https://github.com/testuser?rank=directory) - Dhaka, Bangladesh, Test User, 100 followers, 10 public repos, 50 stars." in entry



    # Test rising followers
    entry = generate_readme.format_list_entry(dev, 1, "rising_followers")
    assert "100 followers (+5 this month)" in entry


def test_section():
    entries = ["1. A", "2. B"]
    sec = generate_readme.section("Top", entries)
    assert "### Top" in sec
    assert "1. A" in sec
    assert "2. B" in sec

def test_load_json(tmp_path):
    # Test valid JSON
    d = tmp_path / "test.json"
    d.write_text(json.dumps({"a": 1}))
    assert generate_readme.load_json(str(d)) == {"a": 1}

    # Test invalid JSON
    d.write_text("invalid")
    assert generate_readme.load_json(str(d)) == []

    # Test missing file
    assert generate_readme.load_json("missing.json") == []

def test_get_stats_data(tmp_path):
    with patch("generate_readme.DATA_DIR", str(tmp_path)):
        # Test no files
        assert generate_readme.get_stats_data() == ([], [], None)

        # Test with files
        f1 = tmp_path / "2026-04-22.json"
        f1.write_text(json.dumps({"developers": [{"login": "user1"}]}))
        f2 = tmp_path / "2026-04-21.json"
        f2.write_text(json.dumps({"developers": [{"login": "user2"}]}))
        
        latest, previous, date = generate_readme.get_stats_data()
        assert date == "2026-04-22"
        assert len(latest) == 1
        assert latest[0]["login"] == "user1"
        assert len(previous) == 1
        assert previous[0]["login"] == "user2"

def test_calculate_growth():
    latest = [{"login": "a", "followers": 10, "recent_repo_stars_sum": 5}]
    previous = [{"login": "a", "followers": 8, "recent_repo_stars_sum": 4}]
    enriched = generate_readme.calculate_growth(latest, previous)
    assert enriched[0]["followers_growth"] == 2
    assert enriched[0]["stars_growth"] == 1

@patch("generate_readme.get_stats_data")
@patch("generate_readme.load_json")
@patch("builtins.open")
def test_main_no_stats(mock_open, mock_load_json, mock_get_stats):
    mock_get_stats.return_value = ([], [], None)
    mock_load_json.side_effect = [{"top_n": 25}, [{"github_username": "user1"}], {}]
    
    generate_readme.main()
    mock_open.assert_called_with(generate_readme.README_PATH, "w", encoding="utf-8")

@patch("generate_readme.get_stats_data")
@patch("generate_readme.load_json")
@patch("builtins.open")
def test_main_with_stats(mock_open, mock_load_json, mock_get_stats):
    devs = [{
        "login": "user1", "name": "User 1", "profile_url": "url1", "location": "Loc1",
        "followers": 100, "public_repos": 10, "recent_repo_stars_sum": 50, "composite_score": 0.9,
        "followers_growth": 5, "stars_growth": 2
    }]
    mock_get_stats.return_value = (devs, devs, "2026-04-22")
    mock_load_json.side_effect = [{"top_n": 25}, [{"github_username": "user1"}], {}]
    
    generate_readme.main()
    mock_open.assert_called_with(generate_readme.README_PATH, "w", encoding="utf-8")

@patch("generate_readme.get_stats_data")
@patch("generate_readme.load_json")
@patch("builtins.open")
def test_main_merging(mock_open, mock_load_json, mock_get_stats):
    auto_devs = [{
        "login": "auto_user", "followers": 10, "public_repos": 10
    }]
    manual_devs = [
        {"github_username": "manual_user", "public_repos": 500},
        {"github_username": "auto_user", "public_repos": 10}
    ]
    mock_get_stats.return_value = (auto_devs, [], "2026-04-22")
    mock_load_json.side_effect = [{"top_n": 25}, manual_devs, {}]
    
    handle = mock_open.return_value.__enter__.return_value
    generate_readme.main()
    
    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    # manual_user should be in Top Repos list because it has 500 repos
    assert "manual_user" in written_content
    # auto_user should be there too
    assert "auto_user" in written_content
    
    # Check ranking in Top Repos section (using the header to avoid Table of Contents)
    repos_sec_idx = written_content.find("### 📁 Top 25 Developers by Public Repositories")
    manual_idx = written_content.find("manual_user", repos_sec_idx)
    auto_idx = written_content.find("auto_user", repos_sec_idx)
    assert manual_idx < auto_idx

def test_format_list_entry_sanitization():
    dev = {
        "name": "  Space User  ",
        "login": " spaceuser ",
        "location": " dhaka, bangladesh ",
        "followers": 10
    }
    entry = generate_readme.format_list_entry(dev, 1)
    # Check that whitespace is stripped and location is capitalized
    assert "[spaceuser]" in entry
    assert "Dhaka, bangladesh, Space User" in entry
    assert "github.com/spaceuser" in entry


def test_format_list_entry_name_lint_sanitization():
    dev = {
        "name": "</NameWithTags>",
        "login": "taguser",
        "location": "Bangladesh"
    }
    entry = generate_readme.format_list_entry(dev, 1)
    assert "[taguser]" in entry
    assert "Bangladesh, /NameWithTags" in entry



    assert "<" not in entry.split("]")[0]
    assert ">" not in entry.split("]")[0]


@patch("generate_readme.get_stats_data")
@patch("generate_readme.load_json")
@patch("builtins.open")
def test_main_removed_users(mock_open, mock_load_json, mock_get_stats):
    # Test that removed users are excluded from all lists
    # Note: the code uses .replace(".", "-") for normalization of removed users
    auto_devs = [{"login": "removed.user", "public_repos": 1000}, {"login": "active_user", "public_repos": 10}]
    manual_devs = [{"github_username": "removed.user"}, {"github_username": "active_user"}]
    removed_users = {"removed-user": {"reason": "test"}} 
    
    mock_get_stats.return_value = (auto_devs, [], "2026-05-03")
    mock_load_json.side_effect = [{"top_n": 25}, manual_devs, removed_users]
    
    handle = mock_open.return_value.__enter__.return_value
    generate_readme.main()
    
    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    assert "removed.user" not in written_content
    assert "active_user" in written_content

@patch("generate_readme.get_stats_data")
@patch("generate_readme.load_json")
@patch("builtins.open")
def test_main_top_n_config(mock_open, mock_load_json, mock_get_stats):
    # Test that top_n from config is respected
    devs = [{"login": f"user{i}", "public_repos": 100-i} for i in range(10)]
    mock_get_stats.return_value = (devs, [], "2026-05-03")
    mock_load_json.side_effect = [{"top_n": 3}, [], {}]
    
    handle = mock_open.return_value.__enter__.return_value
    generate_readme.main()
    
    written_content = "".join(call.args[0] for call in handle.write.call_args_list)
    # Only top 3 should be in a top list
    assert "1. [user0]" in written_content
    assert "2. [user1]" in written_content
    assert "3. [user2]" in written_content
    assert "4. [user3]" not in written_content.split("### 📁 Top 3 Developers by Public Repositories")[1].split("##")[0]




