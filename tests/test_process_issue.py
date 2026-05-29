import os
import json
import pytest
import yaml
from src.process_issue import main
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
