import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
import process_issue

def test_parse_issue():
    body = """
### GitHub Username
testuser

### Location
Dhaka

### Self Removal
- [x] I want to remove myself
"""
    fields = process_issue.parse_issue("Add developer", body)
    assert fields["github_username"] == "testuser"
    assert fields["location"] == "Dhaka"
    assert fields["self_removal"] == "true"

    # Fallback format
    body2 = "github_username: testuser2\nlocation: Dhaka"
    fields2 = process_issue.parse_issue("Add", body2)
    assert fields2["github_username"] == "testuser2"

def test_normalize_username():
    assert process_issue.normalize_username("Test.User") == "test-user"
    assert process_issue.normalize_username(None) == ""

@patch("requests.get")
def test_get_github_stats(mock_get):
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"name": "Test", "login": "test", "followers": 10, "public_repos": 5, "html_url": "url", "location": "Dhaka"}),
        MagicMock(status_code=200, json=lambda: [{"stargazers_count": 10}])
    ]
    stats = process_issue.get_github_stats("test")
    assert stats["followers"] == 10
    assert stats["recent_repo_stars_sum"] == 10

    # Test failure
    mock_get.side_effect = Exception("error")
    assert process_issue.get_github_stats("test") is None

@patch("process_issue.get_github_stats")
def test_add_developer(mock_stats):
    mock_stats.return_value = {
        "name": "Test", "followers": 10, "public_repos": 5, "recent_repo_stars_sum": 10, "profile_url": "url", "location": "Dhaka"
    }
    process_issue.users = []
    process_issue.removed_users = {}
    
    # Valid add
    fields = {"github_username": "test", "location": "Dhaka"}
    assert process_issue.add_developer(fields, "Add developer: test") is True
    assert len(process_issue.users) == 1

    # Missing username
    assert process_issue.add_developer({}, "Add developer") is False

    # Invalid location
    fields = {"github_username": "test2", "location": "Unknown"}
    assert process_issue.add_developer(fields, "Add developer") is False

    # Duplicate
    fields = {"github_username": "test", "location": "Dhaka"}
    assert process_issue.add_developer(fields, "Add developer") is False

@patch("process_issue.get_github_stats")
def test_add_developer_api_failure(mock_stats):
    mock_stats.return_value = None
    process_issue.users = []
    fields = {"github_username": "test", "location": "Dhaka"}
    assert process_issue.add_developer(fields, "Add developer: test") is True
    assert process_issue.users[0]["followers"] == 0

def test_add_developer_removed():
    process_issue.removed_users = {"test": {"reason": "test"}}
    fields = {"github_username": "test", "location": "Dhaka"}
    assert process_issue.add_developer(fields, "Add developer") is False

def test_remove_developer_self():
    process_issue.users = [{"github_username": "testuser"}]
    process_issue.removed_users = {}
    fields = {"github_username": "testuser", "self_removal": "true"}
    assert process_issue.remove_developer(fields, "testuser", "owner") is True
    assert len(process_issue.users) == 0
    assert "testuser" in process_issue.removed_users

def test_remove_developer_owner():
    process_issue.users = [{"github_username": "testuser"}]
    process_issue.removed_users = {}
    fields = {"github_username": "testuser", "reason": "Policy"}
    assert process_issue.remove_developer(fields, "owner", "owner") is True
    assert len(process_issue.users) == 0

def test_remove_developer_not_found():
    process_issue.users = []
    process_issue.removed_users = {}
    fields = {"github_username": "testuser", "self_removal": "true"}
    assert process_issue.remove_developer(fields, "testuser", "owner") is True
    assert "testuser" in process_issue.removed_users

def test_remove_developer_fail():
    # Missing username
    assert process_issue.remove_developer({}, "author", "owner") is False
    # Self removal not confirmed
    assert process_issue.remove_developer({"github_username": "u"}, "u", "owner") is False
    # Third party
    assert process_issue.remove_developer({"github_username": "u"}, "other", "owner") is False

@patch("process_issue.add_developer")
@patch("process_issue.remove_developer")
@patch("builtins.open")
def test_main(mock_open, mock_remove, mock_add):
    # Add
    with patch("sys.argv", ["script", "1", "Add developer", "body", "author", "owner"]):
        process_issue.main()
    assert mock_add.called

    # Remove
    with patch("sys.argv", ["script", "1", "Remove developer", "body", "author", "owner"]):
        process_issue.main()
    assert mock_remove.called

    # Invalid title
    with patch("sys.argv", ["script", "1", "Invalid", "body", "author", "owner"]):
        process_issue.main()

    # Changed save
    mock_add.return_value = True
    with patch("sys.argv", ["script", "1", "Add developer", "body", "author", "owner"]):
        process_issue.main()
    assert mock_open.called

    # Usage check
    with patch("sys.argv", ["script"]):
        process_issue.main()
