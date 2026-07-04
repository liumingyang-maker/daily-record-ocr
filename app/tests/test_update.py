"""Tests for update service."""

import pytest
from unittest.mock import patch, MagicMock
from app.application.update_service import run_git, get_local_info, check_update


def test_run_git_returns_tuple():
    code, output = run_git(["--version"])
    assert code == 0
    assert "git version" in output


def test_get_local_info():
    info = get_local_info()
    assert "hash" in info
    assert "branch" in info
    assert "commit_count" in info


@patch("app.application.update_service.run_git")
def test_check_update_up_to_date(mock_run_git):
    mock_run_git.side_effect = [
        # get_local_info (5 calls)
        (0, "abc1234"),                    # rev-parse --short HEAD
        (0, "abc1234full"),                # rev-parse HEAD
        (0, "2026-07-03 12:00:00 +0800"), # log -1 --format=%ci
        (0, "master"),                     # branch --show-current
        (0, "35"),                         # rev-list --count HEAD
        # get_remote_info (3 calls)
        (0, ""),                           # fetch origin
        (0, "abc1234"),                    # rev-parse --short origin/main
        (0, "2026-07-03 12:00:00 +0800"), # log -1 origin/main
        # check_update comparison (2 calls)
        (0, "0"),                          # rev-list --count HEAD..origin/main
        (0, "0"),                          # rev-list --count HEAD..origin/master (fallback)
    ]
    result = check_update()
    assert result["status"] == "up_to_date"


@patch("app.application.update_service.run_git")
def test_check_update_available(mock_run_git):
    mock_run_git.side_effect = [
        (0, "abc1234"),   # local hash
        (0, "abc1234full"),
        (0, "2026-07-03 12:00:00"),
        (0, "master"),
        (0, "35"),
        (0, ""),          # fetch
        (0, "def5678"),   # remote hash
        (0, "2026-07-03 15:00:00"),
        (0, "3"),         # behind
        (0, "def5678 feat: new feature\nabc1234 fix: bug fix\n"),  # log
    ]
    result = check_update()
    assert result["status"] == "update_available"
    assert result["behind"] == 3
    assert len(result["new_commits"]) == 2


@patch("app.application.update_service.run_git")
def test_check_update_error(mock_run_git):
    mock_run_git.side_effect = [
        (0, "abc1234"),
        (0, "abc1234full"),
        (0, "2026-07-03 12:00:00"),
        (0, "master"),
        (0, "35"),
        (1, "Network error"),  # fetch fails
    ]
    result = check_update()
    assert result["status"] == "error"
