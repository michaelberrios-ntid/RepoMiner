# tests/test_repo_miner.py

import os
import pandas as pd
import pytest
from datetime import datetime, timedelta
from src.repo_miner import fetch_commits

# --- Helpers for dummy GitHub API objects ---

class DummyAuthor:
    def __init__(self, name, email, date):
        self.name = name
        self.email = email
        self.date = date

class DummyCommitCommit:
    def __init__(self, author, message):
        self.author = author
        self.message = message

class DummyCommit:
    def __init__(self, sha, author, email, date, message):
        self.sha = sha
        self.commit = DummyCommitCommit(DummyAuthor(author, email, date), message)

class DummyUser:
    def __init__(self, login):
        self.login = login

class DummyIssue:
    def __init__(self, id_, number, title, user, state, created_at, closed_at, comments, is_pr=False):
        self.id = id_
        self.number = number
        self.title = title
        self.user = DummyUser(user)
        self.state = state
        self.created_at = created_at
        self.closed_at = closed_at
        self.comments = comments
        # attribute only on pull requests
        self.pull_request = DummyUser("pr") if is_pr else None

class DummyRepo:
    def __init__(self, commits, issues):
        self._commits = commits
        self._issues = issues

    def get_commits(self):
        return self._commits

    def get_issues(self, state="all"):
        # filter by state
        if state == "all":
            return self._issues
        return [i for i in self._issues if i.state == state]

class DummyGithub:
    def __init__(self, token):
        assert token == "fake-token"
        self._repo = None
        
    def get_repo(self, repo_name):
        # ignore repo_name; return repo set in test fixture
        return self._repo

@pytest.fixture(autouse=True)
def patch_env_and_github(monkeypatch):
    # Set fake token
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    # Patch Github class
    import src.repo_miner
    src.repo_miner.Github = DummyGithub

# Helper global placeholder
# gh_instance = DummyGithub("fake-token")

# --- Tests for fetch_commits ---
# An example test case
def test_fetch_commits_basic(monkeypatch):
    # Setup dummy commits
    now = datetime.now()
    commits = [
        DummyCommit("sha1", "Alice", "a@example.com", now, "Initial commit\nDetails"),
        DummyCommit("sha2", "Bob", "b@example.com", now - timedelta(days=1), "Bug fix")
    ]
    
    gh = DummyGithub("fake-token")
    gh._repo = DummyRepo(commits, [])
    # Patch repo_miner.Github to use our gh
    
    import src.repo_miner
    src.repo_miner.Github = lambda token: gh

    df = fetch_commits("any/repo")

    assert list(df.columns) == ["sha", "author", "email", "date", "message"]
    assert len(df) == 2
    assert df.iloc[0]["message"] == "Initial commit"

def test_fetch_commits_limit(monkeypatch):
    # # More commits than max_commits
    
    now = datetime.now()

    # Faking 3 commits
    commits = [
        DummyCommit("sha1", "Alice", "a@example.com", now, "Initial commit\nDetails"),
        DummyCommit("sha2", "Bob", "b@example.com", now - timedelta(days=1), "Bug fix"),
        DummyCommit("sha3", "Mikey", "m@example.com", now - timedelta(days=2), "Init")
    ]

    gh = DummyGithub("fake-token")
    gh._repo = DummyRepo(commits, [])
    # Patch repo_miner.Github to use our gh
    
    import src.repo_miner
    src.repo_miner.Github = lambda token: gh

    df = fetch_commits("any/repo", 2)

    assert len(df) == 2
    

def test_fetch_commits_empty(monkeypatch):
    # No commits in repo
    # TODO: Test that fetch_commits returns empty DataFrame when no commits exist.
    # Faking 0 commits
    commits = []

    gh = DummyGithub("fake-token")
    gh._repo = DummyRepo(commits, [])
    # Patch repo_miner.Github to use our gh
    
    import src.repo_miner
    src.repo_miner.Github = lambda token: gh

    df = fetch_commits("any/repo", 2)

    assert len(df) == 0