# RepoMiner
SWEN-746 · Small data-collection pipeline project.

## Python 3 Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ensure github_token is set in Environment
```bash
export GITHUB_TOKEN=your_github_token_here
```

## Run repo_miner with github_token as environment variable
```bash
python -m src.repo_miner fetch-commits --repo octocat/Hello-World --max 100 --out octocat-hello-world-commits.csv
```

## Running Tests
```bash
pytest
``` 

## Deactivate Virtual Environment
```bash
deactivate
``` 