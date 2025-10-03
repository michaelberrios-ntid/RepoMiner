#!/usr/bin/env python3
"""
repo_miner.py

A command-line tool to:
  1) Fetch and normalize commit data from GitHub

Sub-commands:
  - fetch-commits
"""

import os
import argparse
import pandas as pd
from github import Github, Auth
from github.Repository import Repository

# Helper function to get repository object
def get_repo(repo_name: str) -> Repository:
    # 1) Read GitHub token from environment
    gh_token = os.getenv("GITHUB_TOKEN")

    # 2) Initialize GitHub client and get the repo
    auth = Auth.Token(gh_token)
    gh = Github(auth=auth)
    repo = gh.get_repo(repo_name)

    return repo

def fetch_commits(repo_name: str, max_commits: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_commits` from the specified GitHub repository.
    Returns a DataFrame with columns: sha, author, email, date, message.
    """
    # 1) Read GitHub token from environment
    gh_token = os.getenv("GITHUB_TOKEN")

    # 2) Initialize GitHub client and get the repo
    gh = Github(gh_token)
    repo = gh.get_repo(repo_name)

    # repo = get_repo(repo_name)

    # 3) Fetch commit objects (paginated by PyGitHub)
    commits = repo.get_commits()

    # 4) Normalize each commit into a record dict
    commits_dict = []
    limit = max_commits or len(commits)

    for i, commit in enumerate(commits):
        if max_commits and i >= limit:
            break
        normalized = {
            "sha": commit.sha,
            "author": commit.commit.author.name,
            "email": commit.commit.author.email,
            "date": commit.commit.author.date.isoformat(),
            "message": commit.commit.message.split("\n")[0],
        }
        commits_dict.append(normalized)
    
    # 5) Build DataFrame from records
    dataFrame = pd.DataFrame(commits_dict)

    return dataFrame
    
def fetch_issues(repo_name: str, state: str = "all", max_issues: int = None) -> pd.DataFrame:
    """
    Fetch up to `max_issues` issues from a GitHub repository.

    Behavior:
    - Pull requests are excluded (only real issues are returned).
    - All datetime fields (`created_at`, `closed_at`) are normalized to ISO-8601 strings.
    - Adds a column `open_duration_days`:
        - If issue is closed: number of days between created_at and closed_at.
        - If issue is still open: None (becomes NaN in the DataFrame).

    Parameters
    ----------
    repo_name : str
        The repository in "owner/name" format.
    state : str, optional
        Filter issues by state ("all", "open", or "closed"), by default "all".
    max_issues : int, optional
        Maximum number of issues to fetch, by default None.

    Returns
    -------
    pd.DataFrame
        A DataFrame with columns:
        id, number, title, user, state, created_at, closed_at,
        comments, open_duration_days
    """

    # 1) Read GitHub token
    gh_token = os.getenv("GITHUB_TOKEN")

    # 2) Initialize client and get the repo
    gh = Github(gh_token)
    repo = gh.get_repo(repo_name)

    # repo = get_repo(repo_name)

    # 3) Fetch issues, filtered by state ('all', 'open', 'closed')
    issues = repo.get_issues(state=state)

    # 4) Normalize each issue (skip PRs)
    records = []
    for idx, issue in enumerate(issues):
        print(f"Processing #{idx} issue #{issue.number}")

        if max_issues and idx >= max_issues:
            break
        # Skip pull requests
        if issue.pull_request is not None:
            print("Skipped PR")
            continue

        # Append records
        # id, number, title, user, state, created_at, closed_at, open_duration_days, comments
        record = {
            "id": issue.id,
            "number": issue.number,
            "title": issue.title,
            "user": issue.user.login,
            "state": issue.state,
            "created_at": issue.created_at.isoformat(),
            "closed_at": issue.closed_at.isoformat() if issue.closed_at else None,
            "open_duration_days": (issue.closed_at - issue.created_at).days if issue.closed_at else None,
            "comments": issue.comments,
        }

        records.append(record)
        print(f"Added issue #{issue.number}")

    # 5) Build DataFrame
    return pd.DataFrame(records)

def main():
    """
    Parse command-line arguments and dispatch to sub-commands.
    """
    parser = argparse.ArgumentParser(
        prog="repo_miner",
        description="Fetch GitHub commits/issues and summarize them"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Sub-command: fetch-commits
    c1 = subparsers.add_parser("fetch-commits", help="Fetch commits and save to CSV")
    c1.add_argument("--repo", required=True, help="Repository in owner/repo format")
    c1.add_argument("--max",  type=int, dest="max_commits",
                    help="Max number of commits to fetch")
    c1.add_argument("--out",  required=True, help="Path to output commits CSV")

    # Sub-command: fetch-issues
    c2 = subparsers.add_parser("fetch-issues", help="Fetch issues and save to CSV")
    c2.add_argument("--repo",  required=True, help="Repository in owner/repo format")
    c2.add_argument("--state", choices=["all","open","closed"], default="all",
                    help="Filter issues by state")
    c2.add_argument("--max",   type=int, dest="max_issues",
                    help="Max number of issues to fetch")
    c2.add_argument("--out",   required=True, help="Path to output issues CSV")

    args = parser.parse_args()

    # Dispatch based on selected command
    if args.command == "fetch-commits":
        df = fetch_commits(args.repo, args.max_commits)
        df.to_csv(args.out, index=False)
        print(f"Saved {len(df)} commits to {args.out}")

    elif args.command == "fetch-issues":
        df = fetch_issues(args.repo, args.state, args.max_issues)
        df.to_csv(args.out, index=False)
        print(f"Saved {len(df)} issues to {args.out}")

if __name__ == "__main__":
    main()