import os
import json
import pytest
import yaml
from src.process_issue import main, parse_issue_body
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "users.json").write_text("[]")
    (data_dir / "removed_users.json").write_text("[]")
    
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "metrics.json").write_text(json.dumps({
        "location_aliases": ["dhaka", "bangladesh"]
    }))
    
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    return tmp_path

def test_add_developer_success(mock_env, capsys):
    issue_body = """
github_username: testuser
location: Dhaka, Bangladesh
"""
    with patch.dict(os.environ, {
        "ISSUE_BODY": issue_body,
        "ISSUE_LABELS": "add-developer",
        "ISSUE_TITLE": "[ADD] @testuser"
    }), patch("requests.get") as mock_get:
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "login": "testuser",
            "name": "Test User",
            "location": "Dhaka",
            "followers": 10,
            "public_repos": 5
        }
        
        with pytest.raises(SystemExit):
            main()
            
        captured = capsys.readouterr()
        assert "ADDED" in captured.out
        
        users = json.loads((mock_env / "data/users.json").read_text())
        assert len(users) == 1
        assert users[0]['github_username'] == "testuser"

def test_add_developer_invalid_location(mock_env, capsys):
    issue_body = "github_username: testuser\nlocation: Mars"
    with patch.dict(os.environ, {
        "ISSUE_BODY": issue_body,
        "ISSUE_LABELS": "add-developer"
    }):
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "INVALID_LOCATION" in captured.out


# Real body submitted by GitHub's issue forms (markdown sections), as filed
# in issue #59, which yaml.safe_load() cannot parse.
GITHUB_FORM_ADD_BODY = """### GitHub Username

AbdulOhab

### Location

Dhaka, Bangladesh

### Confirmation

- [x] I confirm this developer is from Bangladesh or has strong ties to Bangladesh
- [x] I have read the contributing guidelines
"""

GITHUB_FORM_REMOVE_CHECKED = """### GitHub Username

AbdulOhab

### Reason for removal

No longer active

### Self-removal

- [X] I am removing my own profile
"""

GITHUB_FORM_REMOVE_UNCHECKED = """### GitHub Username

AbdulOhab

### Reason for removal

No longer active

### Self-removal

- [ ] I am removing my own profile
"""

SEED_USER = {
    "github_username": "AbdulOhab",
    "name": "Abdul Ohab",
    "profile_url": "https://github.com/AbdulOhab",
    "location": "Dhaka",
    "followers": 9,
    "public_repos": 29
}

GITHUB_API_USER = {
    "login": "AbdulOhab",
    "name": "Abdul Ohab",
    "location": "Dhaka",
    "followers": 9,
    "public_repos": 29
}


def test_parse_issue_body_handles_github_form_markdown():
    parsed = parse_issue_body(GITHUB_FORM_ADD_BODY)
    assert parsed.get('github_username') == 'AbdulOhab'
    assert parsed.get('location') == 'Dhaka, Bangladesh'
    assert parsed.get('confirmation') == {
        'I confirm this developer is from Bangladesh or has strong ties to Bangladesh': True,
        'I have read the contributing guidelines': True,
    }


def test_parse_issue_body_still_supports_plain_yaml():
    parsed = parse_issue_body("github_username: testuser\nlocation: Dhaka\n")
    assert parsed.get('github_username') == 'testuser'
    assert parsed.get('location') == 'Dhaka'


def test_parse_issue_body_returns_empty_on_garbage():
    assert parse_issue_body("just some random text\nwithout any structure") == {}


def test_add_developer_from_github_form_body(mock_env, capsys):
    with patch.dict(os.environ, {
        "ISSUE_BODY": GITHUB_FORM_ADD_BODY,
        "ISSUE_LABELS": "add-developer",
        "ISSUE_TITLE": "[ADD] @AbdulOhab"
    }), patch("requests.get") as mock_get:

        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = GITHUB_API_USER

        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "ADDED" in captured.out

        users = json.loads((mock_env / "data/users.json").read_text())
        assert len(users) == 1
        assert users[0]['github_username'] == "AbdulOhab"


def test_remove_developer_self_removal_checked(mock_env, capsys):
    (mock_env / "data/users.json").write_text(json.dumps([SEED_USER]))
    with patch.dict(os.environ, {
        "ISSUE_BODY": GITHUB_FORM_REMOVE_CHECKED,
        "ISSUE_LABELS": "remove-developer",
        "ISSUE_TITLE": "[REMOVE] @AbdulOhab"
    }):
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "REMOVED" in captured.out

        assert json.loads((mock_env / "data/users.json").read_text()) == []
        removed = json.loads((mock_env / "data/removed_users.json").read_text())
        assert removed[0]["github_username"] == "AbdulOhab"
        assert removed[0]["reason"] == "self_removal"


def test_remove_developer_self_removal_unchecked_needs_review(mock_env, capsys):
    (mock_env / "data/users.json").write_text(json.dumps([SEED_USER]))
    with patch.dict(os.environ, {
        "ISSUE_BODY": GITHUB_FORM_REMOVE_UNCHECKED,
        "ISSUE_LABELS": "remove-developer",
        "ISSUE_TITLE": "[REMOVE] @AbdulOhab"
    }):
        with pytest.raises(SystemExit):
            main()
        captured = capsys.readouterr()
        assert "MANUAL_REVIEW" in captured.out

        users = json.loads((mock_env / "data/users.json").read_text())
        assert len(users) == 1
