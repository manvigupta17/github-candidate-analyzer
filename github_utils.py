"""
github_utils.py — All GitHub API calls
"""

import requests
import os
import base64
from dotenv import load_dotenv

load_dotenv()

GITHUB_API   = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
headers      = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def _get(path: str, params: dict = None):
    try:
        r = requests.get(f"{GITHUB_API}{path}", headers=headers, params=params, timeout=15)
        if r.status_code in (404, 409):
            return None
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _paginate(path: str, max_pages: int = 5) -> list:
    results = []
    for page in range(1, max_pages + 1):
        data = _get(path, params={"per_page": 100, "page": page})
        if not data:
            break
        results.extend(data)
        if len(data) < 100:
            break
    return results


# ── Core ─────────────────────────────────────────────────────────────────────

def get_user_profile(username: str):
    return _get(f"/users/{username}")

def get_user_repos(username: str) -> list:
    all_repos = _paginate(f"/users/{username}/repos", max_pages=5)
    return [r for r in all_repos if not r.get("fork")]

def get_repo_commits(username: str, repo_name: str) -> list:
    data = _get(f"/repos/{username}/{repo_name}/commits", params={"per_page": 100})
    return data if isinstance(data, list) else []

def get_repo_tree(username: str, repo_name: str) -> list:
    repo = _get(f"/repos/{username}/{repo_name}")
    if not repo:
        return []
    branch = repo.get("default_branch", "main")
    tree_data = _get(f"/repos/{username}/{repo_name}/git/trees/{branch}", params={"recursive": "1"})
    return tree_data.get("tree", []) if tree_data else []

def get_repo_languages(username: str, repo_name: str) -> dict:
    return _get(f"/repos/{username}/{repo_name}/languages") or {}

def get_repo_releases(username: str, repo_name: str) -> list:
    data = _get(f"/repos/{username}/{repo_name}/releases", params={"per_page": 10})
    return data if isinstance(data, list) else []

def get_repo_contributors(username: str, repo_name: str) -> list:
    data = _get(f"/repos/{username}/{repo_name}/contributors", params={"per_page": 20})
    return data if isinstance(data, list) else []

def get_repo_issues(username: str, repo_name: str, state: str = "all") -> list:
    data = _get(f"/repos/{username}/{repo_name}/issues", params={"per_page": 50, "state": state})
    return data if isinstance(data, list) else []

def get_repo_pulls(username: str, repo_name: str, state: str = "all") -> list:
    data = _get(f"/repos/{username}/{repo_name}/pulls", params={"per_page": 50, "state": state})
    return data if isinstance(data, list) else []

def get_user_events(username: str) -> list:
    data = _get(f"/users/{username}/events/public", params={"per_page": 100})
    return data if isinstance(data, list) else []

def get_code_sample(username: str, repo_name: str, path: str):
    data = _get(f"/repos/{username}/{repo_name}/contents/{path}")
    if not data or not isinstance(data, dict):
        return None
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")[:5000]
        except Exception:
            return None
    return None

def get_repo_readme(username: str, repo_name: str) -> str:
    data = _get(f"/repos/{username}/{repo_name}/readme")
    if not data or not isinstance(data, dict):
        return ""
    if data.get("encoding") == "base64":
        try:
            return base64.b64decode(data["content"]).decode("utf-8", errors="ignore")[:2000]
        except Exception:
            return ""
    return ""
