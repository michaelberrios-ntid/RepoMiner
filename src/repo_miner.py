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

def merge_and_summarize(commits_df: pd.DataFrame, issues_df: pd.DataFrame) -> None:
    """
    Takes two DataFrames (commits and issues) and prints:
      - Top 5 committers by commit count
      - Issue close rate (closed/total)
      - Average open duration for closed issues (in days)
    """
    # Copy to avoid modifying original data
    commits = commits_df.copy()
    issues  = issues_df.copy()

    # 1) Normalize date/time columns to pandas datetime
    commits['date']      = pd.to_datetime(commits['date'], errors='coerce')
    issues['created_at'] = pd.to_datetime(issues['created_at'], errors='coerce')
    issues['closed_at']  = pd.to_datetime(issues['closed_at'], errors='coerce')

    # 2) Top 5 committers
    top_committers = commits['author'].value_counts().head() # Series of top 5 committers by default

    # 3) Calculate issue close rate
    """
    Since an issue is considered an entry in the 'issues' list, 'created_at' is implied. 
    So, we filter by where 'closed_at' is not null to get the count of closed issues, and 
    where 'closed_at' is null to get the count of open issues.
    """
    issues_close_df = issues.groupby('user')['closed_at'].agg([
        ('open_issues', lambda s: s.isna().sum()),
        ('closed_issues', lambda s: s.notnull().sum()),
        ('total_issues', lambda s: s.size)
    ])

    """
    Add a 'close_rate' column to the DataFrame, calculated as the ratio of closed issues
    to total issues for each user. If a user has no issues, the close rate is set to 0.
    """
    issues_close_df['close_rate'] = issues_close_df['closed_issues'] / issues_close_df['total_issues']

    # 4) Compute average open duration (days) for closed issues
    """
    Now we calculate the average open duration for closed issues.
    We filter the original issues DataFrame to include only closed issues, then group by user
    and calculate the mean of the 'open_duration_days' column.
    Finally, we merge this information into the issues_close_df DataFrame.
    """
    closed_issues = issues[issues['closed_at'].notnull()].copy()
    closed_issues['open_duration_days'] = (closed_issues['closed_at'] - closed_issues['created_at']).dt.days
    avg_duration_per_user = closed_issues.groupby('user')['open_duration_days'].mean()
    issues_close_df['average_open_duration_days'] = avg_duration_per_user

    # issues['open_duration_days'] = (issues['closed_at'] - issues['created_at']).dt.days
    # issues_close_df['average_open_duration_days'] = issues.groupby('user')['open_duration_days'].mean()

    print(issues_close_df)
    # print(issues)

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

    # Sub-command: summarize
    c3 = subparsers.add_parser("summarize", help="Summarize commits and issues")
    c3.add_argument("--commits", required=True, help="Path to commits CSV file")
    c3.add_argument("--issues",  required=True, help="Path to issues CSV file")

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

    elif args.command == "summarize":
        # Read CSVs into DataFrames
        commits_df = pd.read_csv(args.commits)
        issues_df  = pd.read_csv(args.issues)

        # Generate and print the summary
        merge_and_summarize(commits_df, issues_df)

if __name__ == "__main__":
    main()