import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import process_issue
import bulk_add_developers


# ---------------------------------------------------------------------------
# extract_username
# ---------------------------------------------------------------------------

def test_extract_username_plain():
    assert bulk_add_developers.extract_username("johndoe") == "johndoe"

def test_extract_username_profile_url():
    assert bulk_add_developers.extract_username("https://github.com/johndoe") == "johndoe"

def test_extract_username_profile_url_trailing_slash():
    assert bulk_add_developers.extract_username("https://github.com/johndoe/") == "johndoe"

def test_extract_username_repo_url():
    assert bulk_add_developers.extract_username("https://github.com/johndoe/some-repo") == "johndoe"

def test_extract_username_http():
    assert bulk_add_developers.extract_username("http://github.com/johndoe") == "johndoe"

def test_extract_username_empty():
    assert bulk_add_developers.extract_username("") == ""
    assert bulk_add_developers.extract_username("   ") == ""


# ---------------------------------------------------------------------------
# parse_input
# ---------------------------------------------------------------------------

def test_parse_input_newline_separated():
    raw = "user1\nuser2\nuser3"
    result = bulk_add_developers.parse_input(raw)
    assert result == ["user1", "user2", "user3"]

def test_parse_input_comma_separated():
    raw = "user1, user2, user3"
    result = bulk_add_developers.parse_input(raw)
    assert result == ["user1", "user2", "user3"]

def test_parse_input_mixed_separators():
    raw = "user1\nhttps://github.com/user2, user3\nuser1"  # user1 duplicate
    result = bulk_add_developers.parse_input(raw)
    assert result == ["user1", "user2", "user3"]

def test_parse_input_urls_and_usernames():
    raw = "https://github.com/alice\nbob\nhttps://github.com/charlie/repo"
    result = bulk_add_developers.parse_input(raw)
    assert result == ["alice", "bob", "charlie"]

def test_parse_input_empty_lines_ignored():
    raw = "user1\n\n  \nuser2"
    result = bulk_add_developers.parse_input(raw)
    assert result == ["user1", "user2"]

def test_parse_input_deduplication_case_insensitive():
    raw = "User1\nuser1\nUSER1"
    result = bulk_add_developers.parse_input(raw)
    assert len(result) == 1
    assert result[0] == "User1"  # first occurrence is preserved


# ---------------------------------------------------------------------------
# bulk_add
# ---------------------------------------------------------------------------

@patch("process_issue.get_github_stats")
def test_bulk_add_success(mock_stats):
    mock_stats.return_value = {
        "name": "Alice",
        "followers": 100,
        "public_repos": 20,
        "recent_repo_stars_sum": 50,
        "profile_url": "https://github.com/alice",
        "location": "Dhaka",
    }
    process_issue.users = []
    process_issue.removed_users = {}

    summary = bulk_add_developers.bulk_add("alice")

    assert "alice" in summary["added"]
    assert summary["skipped"] == []
    assert summary["failed"] == []
    assert len(process_issue.users) == 1


@patch("process_issue.get_github_stats")
def test_bulk_add_multiple(mock_stats):
    mock_stats.return_value = {
        "name": "Test",
        "followers": 5,
        "public_repos": 3,
        "recent_repo_stars_sum": 1,
        "profile_url": "https://github.com/test",
        "location": "Bangladesh",
    }
    process_issue.users = []
    process_issue.removed_users = {}

    summary = bulk_add_developers.bulk_add("user1\nuser2\nuser3")

    assert len(summary["added"]) == 3
    assert summary["skipped"] == []
    assert summary["failed"] == []


@patch("process_issue.get_github_stats")
def test_bulk_add_skips_duplicates(mock_stats):
    mock_stats.return_value = {
        "name": "Test",
        "followers": 5,
        "public_repos": 3,
        "recent_repo_stars_sum": 1,
        "profile_url": "https://github.com/test",
        "location": "Bangladesh",
    }
    process_issue.users = [{"github_username": "existing"}]
    process_issue.removed_users = {}

    summary = bulk_add_developers.bulk_add("existing")

    assert summary["added"] == []
    assert "existing" in summary["skipped"]


@patch("process_issue.get_github_stats")
def test_bulk_add_fails_removed_user(mock_stats):
    mock_stats.return_value = None
    process_issue.users = []
    process_issue.removed_users = {"removed-user": {"reason": "spam"}}

    summary = bulk_add_developers.bulk_add("removed-user")

    assert summary["added"] == []
    assert len(summary["failed"]) == 1
    assert summary["failed"][0][0] == "removed-user"


def test_bulk_add_empty_input():
    process_issue.users = []
    process_issue.removed_users = {}

    summary = bulk_add_developers.bulk_add("")
    assert summary["added"] == []
    assert summary["skipped"] == []
    assert summary["failed"] == []


@patch("process_issue.get_github_stats")
def test_bulk_add_accepts_urls(mock_stats):
    mock_stats.return_value = {
        "name": "Bob",
        "followers": 10,
        "public_repos": 5,
        "recent_repo_stars_sum": 2,
        "profile_url": "https://github.com/bob",
        "location": "Bangladesh",
    }
    process_issue.users = []
    process_issue.removed_users = {}

    summary = bulk_add_developers.bulk_add(
        "https://github.com/bob\nhttps://github.com/bob/some-repo"
    )
    # Both URLs resolve to same username "bob"; only one entry should be added
    assert summary["added"] == ["bob"]
    assert len(process_issue.users) == 1


# ---------------------------------------------------------------------------
# save_and_report
# ---------------------------------------------------------------------------

@patch("builtins.open", new_callable=mock_open)
def test_save_and_report_with_changes(mock_file, capsys):
    process_issue.users = [{"github_username": "alice"}]
    process_issue.removed_users = {}

    summary = {"added": ["alice"], "skipped": [], "failed": []}
    bulk_add_developers.save_and_report(summary)

    captured = capsys.readouterr()
    assert "users.json and removed_users.json updated" in captured.out
    assert "Added" in captured.out
    assert mock_file.called


def test_save_and_report_no_changes(capsys):
    summary = {"added": [], "skipped": ["x"], "failed": []}
    bulk_add_developers.save_and_report(summary)

    captured = capsys.readouterr()
    assert "No new developers" in captured.out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

@patch("bulk_add_developers.bulk_add")
@patch("bulk_add_developers.save_and_report")
def test_main_with_arg(mock_save, mock_bulk):
    mock_bulk.return_value = {"added": [], "skipped": [], "failed": []}
    with patch("sys.argv", ["script", "user1\nuser2"]):
        bulk_add_developers.main()
    mock_bulk.assert_called_once_with("user1\nuser2")
    mock_save.assert_called_once()


def test_main_no_args(capsys):
    with patch("sys.argv", ["script"]):
        bulk_add_developers.main()
    captured = capsys.readouterr()
    assert "Usage:" in captured.out
