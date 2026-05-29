import json
import pytest
from src.validate_data import validate_data
import os

def test_validate_data_success(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_file = data_dir / "users.json"
    
    users = [
        {
            "github_username": "user1",
            "profile_url": "https://github.com/user1"
        }
    ]
    users_file.write_text(json.dumps(users))
    
    # Change current working directory to tmp_path for the test
    monkeypatch.chdir(tmp_path)
    
    # Mock sys.exit to check if it's called with 0
    with pytest.raises(SystemExit) as e:
        validate_data()
    assert e.value.code == 0

def test_validate_data_duplicate(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_file = data_dir / "users.json"
    
    users = [
        {"github_username": "user1", "profile_url": "https://github.com/user1"},
        {"github_username": "user1", "profile_url": "https://github.com/user1"}
    ]
    users_file.write_text(json.dumps(users))
    
    monkeypatch.chdir(tmp_path)
    
    with pytest.raises(SystemExit) as e:
        validate_data()
    assert e.value.code == 1

def test_validate_data_url_mismatch(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    users_file = data_dir / "users.json"
    
    users = [
        {"github_username": "user1", "profile_url": "https://github.com/wrong"}
    ]
    users_file.write_text(json.dumps(users))
    
    monkeypatch.chdir(tmp_path)
    
    with pytest.raises(SystemExit) as e:
        validate_data()
    assert e.value.code == 1
