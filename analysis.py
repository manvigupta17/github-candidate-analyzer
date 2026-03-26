"""
analysis.py — Full GitHub analysis engine
"""

import os
from collections import Counter
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import httpx

load_dotenv()

AI_API_KEY  = os.getenv("AI_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()   # groq | gemini | anthropic

_CONVENTIONAL = ("feat","fix","docs","style","refactor","test","chore","perf","ci","build","revert")
_VAGUE        = {"update","fix","wip","test","changes","misc","edit","work","stuff","minor","tweak","patch","commit","save"}
_CODE_EXTS    = {".py",".js",".ts",".go",".java",".cpp",".c",".rs",".rb",".php",".kt",".swift",".cs",".jsx",".tsx",".vue"}
_TEST_DIRS    = {"test","tests","spec","specs","__tests__","testing"}
_CI_SIGNALS   = {".travis.yml","jenkinsfile",".gitlab-ci.yml","azure-pipelines.yml"}
_QUALITY_FILES= {".eslintrc",".eslintrc.js",".prettierrc","pyproject.toml",".flake8","setup.cfg",".editorconfig",".rubocop.yml"}
_DOCKER_FILES = {"dockerfile","docker-compose.yml","docker-compose.yaml"}


def _now():
    return datetime.now(timezone.utc)

def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _days_since(dt):
    if not dt:
        return None
    return (_now() - dt).days


# ─────────────────────────────────────────────────────────────────────────────
# MASTER ANALYSIS FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def full_analysis(username: str) -> dict:
    from github_utils import (
        get_user_profile, get_user_repos, get_repo_commits,
        get_repo_tree, get_repo_languages, get_repo_releases,
        get_repo_contributors, get_repo_issues, get_repo_pulls,
        get_user_events, get_code_sample, get_repo_readme
    )

    profile = get_user_profile(username)
    if not profile:
        raise ValueError(f"GitHub user '{username}' not found.")

    repos = get_user_repos(username)

    # ── per-repo deep data ────────────────────────────────────
    repo_details = []
    for repo in repos[:25]:
        rname = repo["name"]
        commits      = get_repo_commits(username, rname)
        languages    = get_repo_languages(username, rname)
        contributors = get_repo_contributors(username, rname)
        releases     = get_repo_releases(username, rname)
        issues       = get_repo_issues(username, rname)
        pulls        = get_repo_pulls(username, rname)
        tree         = get_repo_tree(username, rname)
        readme       = get_repo_readme(username, rname)

        # code samples (up to 3 per repo)
        code_samples = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            ext  = ("." + path.split(".")[-1]) if "." in path else ""
            if ext in _CODE_EXTS and len(code_samples) < 3:
                content = get_code_sample(username, rname, path)
                if content:
                    code_samples.append({"filename": path, "content": content[:2500]})

        repo_details.append({
            "meta":         repo,
            "commits":      commits,
            "languages":    languages,
            "contributors": contributors,
            "releases":     releases,
            "issues":       issues,
            "pulls":        pulls,
            "tree":         tree,
            "readme":       readme,
            "code_samples": code_samples,
        })

    events = get_user_events(username)

    # ── compute all metrics ───────────────────────────────────
    profile_m    = _profile_metrics(profile)
    repo_m       = _repo_metrics(repo_details)
    commit_m     = _commit_metrics(repo_details)
    code_m       = _code_metrics(repo_details)
    activity_m   = _activity_metrics(repo_details, events)
    lang_m       = _language_metrics(repo_details)
    collab_m     = _collaboration_metrics(repo_details)
    repo_cards   = _repo_cards(repo_details)
    score        = _compute_score(repo_m, commit_m, code_m, activity_m, collab_m)
    summary      = _generate_summary(username, profile, repo_m, commit_m,
                                      code_m, activity_m, lang_m, collab_m,
                                      repo_cards, score)

    return {
        "username":              username,
        "profile":               profile_m,
        "repository_metrics":    repo_m,
        "commit_metrics":        commit_m,
        "code_quality":          code_m,
        "activity":              activity_m,
        "languages":             lang_m,
        "collaboration":         collab_m,
        "top_repositories":      repo_cards[:10],
        "scoring":               score,
        "summary":               summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────────────────────────────────────────

def _profile_metrics(user: dict) -> dict:
    created = _parse_dt(user.get("created_at"))
    return {
        "username":        user.get("login"),
        "name":            user.get("name"),
        "bio":             user.get("bio"),
        "location":        user.get("location"),
        "company":         user.get("company"),
        "blog":            user.get("blog"),
        "email":           user.get("email"),
        "twitter":         user.get("twitter_username"),
        "avatar_url":      user.get("avatar_url"),
        "profile_url":     user.get("html_url"),
        "public_repos":    user.get("public_repos", 0),
        "public_gists":    user.get("public_gists", 0),
        "followers":       user.get("followers", 0),
        "following":       user.get("following", 0),
        "hireable":        user.get("hireable"),
        "account_created": user.get("created_at"),
        "account_age_years": round((_now() - created).days / 365, 1) if created else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# REPOSITORY METRICS
# ─────────────────────────────────────────────────────────────────────────────

def _repo_metrics(repos: list) -> dict:
    if not repos:
        return {"total_repositories": 0, "no_public_repos": True,
                "note": "No public repositories found."}

    total_stars   = sum(r["meta"].get("stargazers_count", 0) for r in repos)
    total_forks   = sum(r["meta"].get("forks_count",      0) for r in repos)
    total_watchers= sum(r["meta"].get("watchers_count",   0) for r in repos)
    total_issues  = sum(r["meta"].get("open_issues_count",0) for r in repos)
    sizes         = [r["meta"].get("size", 0) for r in repos]
    topics        = []
    for r in repos:
        topics.extend(r["meta"].get("topics", []))

    lang_counter = Counter()
    for r in repos:
        lang = r["meta"].get("language")
        if lang:
            lang_counter[lang] += 1

    licenses = Counter(
        r["meta"].get("license", {}).get("spdx_id")
        for r in repos if r["meta"].get("license")
    )

    most_starred = max(repos, key=lambda r: r["meta"].get("stargazers_count", 0))
    largest      = max(repos, key=lambda r: r["meta"].get("size", 0))

    return {
        "total_repositories":   len(repos),
        "no_public_repos":      False,
        "total_stars":          total_stars,
        "total_forks":          total_forks,
        "total_watchers":       total_watchers,
        "total_open_issues":    total_issues,
        "avg_repo_size_kb":     round(sum(sizes) / len(sizes), 1) if sizes else 0,
        "top_languages_by_repo_count": lang_counter.most_common(5),
        "most_starred_repo":    most_starred["meta"].get("name"),
        "largest_repo":         largest["meta"].get("name"),
        "top_topics":           [t for t, _ in Counter(topics).most_common(10)],
        "licenses_used":        dict(licenses),
        "archived_repos":       sum(1 for r in repos if r["meta"].get("archived")),
        "repos_with_description": sum(1 for r in repos if r["meta"].get("description")),
        "repos_with_homepage":  sum(1 for r in repos if r["meta"].get("homepage")),
        "repos_with_topics":    sum(1 for r in repos if r["meta"].get("topics")),
        "total_releases":       sum(len(r.get("releases", [])) for r in repos),
    }


# ─────────────────────────────────────────────────────────────────────────────
# COMMIT METRICS
# ─────────────────────────────────────────────────────────────────────────────

def _commit_metrics(repos: list) -> dict:
    all_commits  = []
    all_messages = []
    repo_counts  = {}

    for r in repos:
        rname = r["meta"].get("name")
        count = len(r["commits"])
        repo_counts[rname] = count
        for c in r["commits"]:
            msg = ((c.get("commit") or {}).get("message") or "").strip()
            dt  = _parse_dt(((c.get("commit") or {}).get("author") or {}).get("date"))
            all_commits.append((dt, msg))
            if msg:
                all_messages.append(msg)

    if not all_commits:
        return {"total_commits": 0, "no_data": True}

    dates = [d for d, _ in all_commits if d]
    dates.sort()
    first, latest = dates[0], dates[-1]
    span_days = (latest - first).days or 1

    monthly: Counter = Counter()
    for d in dates:
        monthly[f"{d.year}-{d.month:02d}"] += 1
    avg_per_month = round(len(dates) / max(len(monthly), 1), 1)

    cutoff_30  = _now() - timedelta(days=30)
    cutoff_90  = _now() - timedelta(days=90)
    cutoff_180 = _now() - timedelta(days=180)
    last_30  = sum(1 for d in dates if d >= cutoff_30)
    last_90  = sum(1 for d in dates if d >= cutoff_90)
    prev_90  = sum(1 for d in dates if cutoff_180 <= d < cutoff_90)

    if   last_90 > prev_90 * 1.2: trend = "INCREASING"
    elif last_90 < prev_90 * 0.8: trend = "DECLINING"
    else:                          trend = "STABLE"

    dow     = Counter(d.strftime("%A") for d in dates)
    hours   = Counter(d.hour for d in dates)
    weekend = dow.get("Saturday", 0) + dow.get("Sunday", 0)

    total_m      = len(all_messages) or 1
    conventional = sum(1 for m in all_messages
                       if m.split(":")[0].split("(")[0].lower().strip() in _CONVENTIONAL)
    vague        = sum(1 for m in all_messages
                       if m.lower().split("\n")[0].strip() in _VAGUE or len(m) < 8)
    avg_len      = round(sum(len(m) for m in all_messages) / total_m, 1)

    most_active = max(repo_counts, key=repo_counts.get) if repo_counts else None

    return {
        "total_commits":              len(dates),
        "first_commit_date":          first.date().isoformat(),
        "latest_commit_date":         latest.date().isoformat(),
        "active_span_days":           span_days,
        "avg_commits_per_month":      avg_per_month,
        "commits_last_30_days":       last_30,
        "commits_last_90_days":       last_90,
        "activity_trend":             trend,
        "most_active_repo":           most_active,
        "repo_commit_counts":         dict(sorted(repo_counts.items(), key=lambda x: -x[1])[:10]),
        "busiest_day_of_week":        max(dow, key=dow.get) if dow else None,
        "busiest_hour_utc":           max(hours, key=hours.get) if hours else None,
        "weekend_commit_pct":         round(weekend / len(dates) * 100, 1),
        "average_commits_per_repo":   len(dates) // max(len(repos), 1),
        "commit_message_quality": {
            "conventional_commits_pct": round(conventional / total_m * 100, 1),
            "vague_messages_pct":       round(vague        / total_m * 100, 1),
            "avg_message_length_chars": avg_len,
            "quality_rating": (
                "EXCELLENT" if conventional/total_m > 0.6 and vague/total_m < 0.1 else
                "GOOD"      if conventional/total_m > 0.3 and vague/total_m < 0.25 else
                "FAIR"      if vague/total_m < 0.4 else "POOR"
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# CODE QUALITY
# ─────────────────────────────────────────────────────────────────────────────

def _code_metrics(repos: list) -> dict:
    if not repos:
        return {"score": 0, "no_data": True}

    total_files = 0
    file_counter = Counter()
    has_tests = has_ci = has_readme = has_docker = has_quality = 0
    total_test_files = total_functions = 0
    readme_qualities = []

    for r in repos:
        tree      = r.get("tree", [])
        repo_paths= set()

        for item in tree:
            if item.get("type") == "blob":
                total_files += 1
                path = item.get("path", "")
                repo_paths.add(path.lower())
                if "." in path:
                    file_counter[path.split(".")[-1].lower()] += 1

        path_str = " ".join(repo_paths)

        # tests
        tf = sum(1 for p in repo_paths if "test" in p.split("/")[-1] or
                 p.split("/")[0] in _TEST_DIRS)
        total_test_files += tf
        if tf > 0: has_tests += 1

        # CI/CD
        if (any(ci in repo_paths for ci in _CI_SIGNALS) or
                ".github/workflows" in path_str or "circleci" in path_str):
            has_ci += 1

        # README
        has_r = any(p in repo_paths for p in ("readme.md","readme.rst","readme.txt","readme"))
        if has_r:
            has_readme += 1
            readme_txt = r.get("readme", "")
            rq = 0
            if len(readme_txt) > 500:  rq += 2
            if len(readme_txt) > 1500: rq += 2
            if "##" in readme_txt:     rq += 2
            if "install" in readme_txt.lower(): rq += 1
            if "usage"   in readme_txt.lower(): rq += 1
            if "badge"   in readme_txt.lower() or "![" in readme_txt: rq += 1
            if "contribut" in readme_txt.lower(): rq += 1
            readme_qualities.append(min(rq, 10))

        # Docker
        if any(d in repo_paths for d in _DOCKER_FILES): has_docker += 1

        # Quality configs
        if any(q in repo_paths for q in _QUALITY_FILES): has_quality += 1

        # Estimate function count from code samples
        for s in r.get("code_samples", []):
            content = s.get("content", "")
            total_functions += content.count("def ") + content.count("function ") + content.count("func ")

    n = len(repos) or 1

    return {
        "total_files":                  total_files,
        "total_test_files":             total_test_files,
        "estimated_functions_sampled":  total_functions,
        "file_type_distribution":       file_counter.most_common(15),
        "repos_with_readme_pct":        round(has_readme  / n * 100, 1),
        "repos_with_tests_pct":         round(has_tests   / n * 100, 1),
        "repos_with_ci_cd_pct":         round(has_ci      / n * 100, 1),
        "repos_with_docker_pct":        round(has_docker  / n * 100, 1),
        "repos_with_quality_cfg_pct":   round(has_quality / n * 100, 1),
        "avg_readme_quality_score":     round(sum(readme_qualities)/len(readme_qualities), 1) if readme_qualities else 0,
        "test_to_total_file_ratio":     round(total_test_files / max(total_files, 1), 3),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVITY & RECENT EVENTS
# ─────────────────────────────────────────────────────────────────────────────

def _activity_metrics(repos: list, events: list) -> dict:
    push_dates = []
    for r in repos:
        pushed = _parse_dt(r["meta"].get("pushed_at"))
        if pushed:
            push_dates.append(pushed)
    push_dates.sort(reverse=True)
    last_push     = push_dates[0] if push_dates else None
    days_since    = _days_since(last_push)

    if days_since is not None:
        level = ("VERY_ACTIVE" if days_since < 14 else
                 "ACTIVE"      if days_since < 60 else
                 "MODERATE"    if days_since < 180 else
                 "INACTIVE"    if days_since < 365 else "DORMANT")
    else:
        level = "UNKNOWN"

    # recent events breakdown
    event_types = Counter(e.get("type") for e in events)

    # recent activity feed (last 10 meaningful events)
    recent_feed = []
    for e in events[:20]:
        etype   = e.get("type", "")
        repo_n  = (e.get("repo") or {}).get("name", "")
        created = e.get("created_at", "")[:10]
        if etype == "PushEvent":
            commits_n = len((e.get("payload") or {}).get("commits", []))
            recent_feed.append(f"{created} — Pushed {commits_n} commit(s) to {repo_n}")
        elif etype == "CreateEvent":
            ref_type = (e.get("payload") or {}).get("ref_type", "")
            recent_feed.append(f"{created} — Created {ref_type} in {repo_n}")
        elif etype == "IssuesEvent":
            action = (e.get("payload") or {}).get("action", "")
            recent_feed.append(f"{created} — {action.capitalize()} issue in {repo_n}")
        elif etype == "PullRequestEvent":
            action = (e.get("payload") or {}).get("action", "")
            recent_feed.append(f"{created} — {action.capitalize()} PR in {repo_n}")
        elif etype == "WatchEvent":
            recent_feed.append(f"{created} — Starred {repo_n}")
        elif etype == "ForkEvent":
            recent_feed.append(f"{created} — Forked {repo_n}")
        if len(recent_feed) >= 10:
            break

    return {
        "last_push_date":       last_push.isoformat() if last_push else None,
        "days_since_last_push": days_since,
        "activity_level":       level,
        "recent_event_types":   dict(event_types.most_common(8)),
        "recent_activity_feed": recent_feed,
        "total_events_sampled": len(events),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE BREAKDOWN
# ─────────────────────────────────────────────────────────────────────────────

def _language_metrics(repos: list) -> dict:
    totals: Counter = Counter()
    for r in repos:
        totals.update(r.get("languages", {}))

    total_bytes = sum(totals.values()) or 1
    breakdown   = {k: round(v/total_bytes*100, 1) for k, v in totals.most_common(10)}
    primary     = totals.most_common(1)[0][0] if totals else "Unknown"

    return {
        "primary_language":       primary,
        "language_breakdown_pct": breakdown,
        "total_languages_used":   len(totals),
        "specialization": (
            "Full-Stack"  if any(l in totals for l in ["JavaScript","TypeScript","HTML","CSS"]) and
                             any(l in totals for l in ["Python","Go","Java","Ruby","PHP"]) else
            "Frontend"    if any(l in totals for l in ["JavaScript","TypeScript","HTML","CSS","Vue"]) else
            "Backend"     if any(l in totals for l in ["Python","Go","Java","Ruby","PHP","C#","Rust"]) else
            "Systems"     if any(l in totals for l in ["C","C++","Rust","Assembly"]) else
            "Data/ML"     if any(l in totals for l in ["Python","R","Jupyter Notebook"]) else
            "Mobile"      if any(l in totals for l in ["Swift","Kotlin","Dart"]) else
            "General"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# COLLABORATION
# ─────────────────────────────────────────────────────────────────────────────

def _collaboration_metrics(repos: list) -> dict:
    all_contributors = set()
    solo = collab = 0
    total_issues = open_issues = closed_issues = 0
    total_prs = merged_prs = 0

    for r in repos:
        contribs = r.get("contributors", [])
        for c in contribs:
            if c.get("login"):
                all_contributors.add(c["login"])
        if len(contribs) <= 1: solo += 1
        else:                  collab += 1

        for issue in r.get("issues", []):
            if issue.get("pull_request"):
                continue
            total_issues += 1
            if issue.get("state") == "open":   open_issues  += 1
            else:                              closed_issues += 1

        for pr in r.get("pulls", []):
            total_prs += 1
            if pr.get("merged_at"):
                merged_prs += 1

    n = len(repos) or 1
    return {
        "unique_collaborators":       len(all_contributors),
        "solo_repos":                 solo,
        "collaborative_repos":        collab,
        "collaboration_rate_pct":     round(collab / n * 100, 1),
        "total_issues_tracked":       total_issues,
        "open_issues":                open_issues,
        "closed_issues":              closed_issues,
        "issue_resolution_rate_pct":  round(closed_issues / max(total_issues,1) * 100, 1),
        "total_pull_requests":        total_prs,
        "merged_pull_requests":       merged_prs,
        "pr_merge_rate_pct":          round(merged_prs / max(total_prs,1) * 100, 1),
    }


# ─────────────────────────────────────────────────────────────────────────────
# REPO CARDS (top repos detailed)
# ─────────────────────────────────────────────────────────────────────────────

def _repo_cards(repos: list) -> list:
    cards = []
    sorted_repos = sorted(repos, key=lambda r: r["meta"].get("stargazers_count", 0), reverse=True)

    for r in sorted_repos[:10]:
        meta      = r["meta"]
        tree      = r.get("tree", [])
        commits   = r.get("commits", [])
        languages = r.get("languages", {})
        contribs  = r.get("contributors", [])
        releases  = r.get("releases", [])
        issues    = r.get("issues", [])
        pulls     = r.get("pulls", [])

        # file type breakdown for this repo
        ext_counter = Counter()
        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path", "")
                if "." in path:
                    ext_counter[path.split(".")[-1].lower()] += 1

        # commit dates for this repo
        commit_dates = []
        for c in commits:
            dt = _parse_dt(((c.get("commit") or {}).get("author") or {}).get("date"))
            if dt: commit_dates.append(dt)

        last_commit = max(commit_dates).date().isoformat() if commit_dates else None

        # code file analysis
        code_analysis = []
        for s in r.get("code_samples", []):
            content  = s["content"]
            lines    = content.splitlines()
            funcs    = content.count("def ") + content.count("function ") + content.count("func ")
            classes  = content.count("class ")
            comments = sum(1 for l in lines if l.strip().startswith(("#","//","/*","*","'''","\"\"\"")) )
            imports  = sum(1 for l in lines if l.strip().startswith(("import ","from ","require","using ")))
            code_analysis.append({
                "filename":       s["filename"],
                "total_lines":    len(lines),
                "functions_found":funcs,
                "classes_found":  classes,
                "comment_lines":  comments,
                "import_lines":   imports,
                "comment_ratio":  round(comments / max(len(lines),1), 2),
            })

        cards.append({
            "name":             meta.get("name"),
            "description":      meta.get("description"),
            "url":              meta.get("html_url"),
            "stars":            meta.get("stargazers_count", 0),
            "forks":            meta.get("forks_count", 0),
            "watchers":         meta.get("watchers_count", 0),
            "language":         meta.get("language"),
            "languages":        languages,
            "size_kb":          meta.get("size", 0),
            "created_at":       meta.get("created_at", "")[:10],
            "last_pushed":      meta.get("pushed_at", "")[:10],
            "last_commit_date": last_commit,
            "total_commits":    len(commits),
            "total_files":      sum(1 for i in tree if i.get("type")=="blob"),
            "file_types":       dict(ext_counter.most_common(8)),
            "contributors":     len(contribs),
            "releases":         len(releases),
            "open_issues":      sum(1 for i in issues if i.get("state")=="open" and not i.get("pull_request")),
            "closed_issues":    sum(1 for i in issues if i.get("state")=="closed" and not i.get("pull_request")),
            "pull_requests":    len(pulls),
            "topics":           meta.get("topics", []),
            "has_readme":       any(i.get("path","").lower().startswith("readme") for i in tree if i.get("type")=="blob"),
            "has_tests":        any("test" in i.get("path","").lower() for i in tree if i.get("type")=="blob"),
            "has_ci":           any(".github/workflows" in i.get("path","").lower() or
                                    ".travis" in i.get("path","").lower() for i in tree),
            "has_docker":       any("dockerfile" in i.get("path","").lower() for i in tree),
            "archived":         meta.get("archived", False),
            "code_file_analysis": code_analysis,
        })

    return cards


# ─────────────────────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────────────────────

def _compute_score(repo_m, commit_m, code_m, activity_m, collab_m) -> dict:
    if repo_m.get("no_public_repos"):
        return {"overall_score": 0, "verdict": "INSUFFICIENT_DATA",
                "breakdown": {}, "note": "No public repositories."}

    total_c  = commit_m.get("total_commits", 0)
    vague_p  = commit_m.get("commit_message_quality", {}).get("vague_messages_pct", 50)
    trend    = commit_m.get("activity_trend", "STABLE")
    span     = commit_m.get("active_span_days", 0)

    # commit score (0-100)
    commit_score = min(100, total_c / 5)
    if trend == "INCREASING": commit_score = min(100, commit_score * 1.15)
    if trend == "DECLINING":  commit_score = max(0,   commit_score * 0.80)
    commit_score *= (1 - vague_p / 200)

    # code quality score (0-100)
    code_score = (
        code_m.get("repos_with_readme_pct",     0) * 0.20 +
        code_m.get("repos_with_tests_pct",       0) * 0.25 +
        code_m.get("repos_with_ci_cd_pct",       0) * 0.20 +
        code_m.get("repos_with_quality_cfg_pct", 0) * 0.15 +
        code_m.get("repos_with_docker_pct",      0) * 0.10 +
        min(code_m.get("avg_readme_quality_score", 0) * 10, 100) * 0.10
    )

    # consistency score (0-100)
    consistency_score = min(100, span / 3.65)

    # collaboration score (0-100)
    collab_score = (
        min(collab_m.get("unique_collaborators", 0) * 5, 40) +
        collab_m.get("collaboration_rate_pct", 0) * 0.30 +
        collab_m.get("issue_resolution_rate_pct", 0) * 0.20 +
        collab_m.get("pr_merge_rate_pct", 0) * 0.10
    )
    collab_score = min(100, collab_score)

    # popularity score (0-100)
    stars = repo_m.get("total_stars", 0)
    popularity_score = min(100, stars * 1.5)

    # activity recency score (0-100)
    level_map = {"VERY_ACTIVE":100,"ACTIVE":80,"MODERATE":50,"INACTIVE":20,"DORMANT":5,"UNKNOWN":0}
    recency_score = level_map.get(activity_m.get("activity_level","UNKNOWN"), 0)

    # weighted final
    final = (
        commit_score      * 0.25 +
        code_score        * 0.25 +
        consistency_score * 0.15 +
        recency_score     * 0.15 +
        collab_score      * 0.10 +
        popularity_score  * 0.10
    )
    final = round(final, 1)

    verdict = "STRONG_ACCEPT" if final >= 80 else \
              "ACCEPT"        if final >= 65 else \
              "REVIEW"        if final >= 45 else \
              "REJECT"        if final >= 25 else "STRONG_REJECT"

    green_flags = []
    red_flags   = []

    if total_c > 200:           green_flags.append(f"Strong commit history ({total_c} commits)")
    if trend == "INCREASING":   green_flags.append("Activity is increasing recently")
    if code_m.get("repos_with_tests_pct", 0) > 50:   green_flags.append("Good test coverage across repos")
    if code_m.get("repos_with_ci_cd_pct", 0) > 50:   green_flags.append("CI/CD pipelines in place")
    if stars > 50:              green_flags.append(f"Community recognition ({stars} stars)")
    if collab_m.get("unique_collaborators", 0) > 3:   green_flags.append("Active collaborator")
    if span > 365:              green_flags.append(f"Long-term consistency ({span} days active)")
    if commit_m.get("commit_message_quality",{}).get("conventional_commits_pct",0) > 50:
        green_flags.append("Uses conventional commit messages")

    if total_c < 20:            red_flags.append("Very low commit count")
    if trend == "DECLINING":    red_flags.append("Declining activity trend")
    if code_m.get("repos_with_tests_pct", 0) == 0:   red_flags.append("No test files found in any repo")
    if code_m.get("repos_with_readme_pct", 0) < 50:  red_flags.append("Most repos lack documentation")
    if vague_p > 40:            red_flags.append(f"High rate of vague commit messages ({vague_p}%)")
    if activity_m.get("activity_level") in ("INACTIVE","DORMANT"): red_flags.append("Account appears inactive")

    return {
        "overall_score":  final,
        "verdict":        verdict,
        "green_flags":    green_flags,
        "red_flags":      red_flags,
        "breakdown": {
            "commit_activity":  round(commit_score,      1),
            "code_quality":     round(code_score,        1),
            "consistency":      round(consistency_score, 1),
            "recency":          round(recency_score,     1),
            "collaboration":    round(collab_score,      1),
            "popularity":       round(popularity_score,  1),
        },
        "weights": {
            "commit_activity": "25%", "code_quality": "25%",
            "consistency":     "15%", "recency":       "15%",
            "collaboration":   "10%", "popularity":    "10%",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# COMPARISON ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def compare_users(data1: dict, data2: dict) -> dict:
    u1 = data1["username"]
    u2 = data2["username"]
    s1 = data1["scoring"]
    s2 = data2["scoring"]

    def winner(v1, v2, label):
        if v1 > v2:   return {"metric": label, "winner": u1, "values": {u1: v1, u2: v2}}
        elif v2 > v1: return {"metric": label, "winner": u2, "values": {u1: v1, u2: v2}}
        else:         return {"metric": label, "winner": "TIE", "values": {u1: v1, u2: v2}}

    comparisons = [
        winner(s1["overall_score"],                              s2["overall_score"],                              "Overall Score"),
        winner(s1["breakdown"]["commit_activity"],               s2["breakdown"]["commit_activity"],               "Commit Activity"),
        winner(s1["breakdown"]["code_quality"],                  s2["breakdown"]["code_quality"],                  "Code Quality"),
        winner(s1["breakdown"]["consistency"],                   s2["breakdown"]["consistency"],                   "Consistency"),
        winner(s1["breakdown"]["recency"],                       s2["breakdown"]["recency"],                       "Recency"),
        winner(s1["breakdown"]["collaboration"],                 s2["breakdown"]["collaboration"],                 "Collaboration"),
        winner(s1["breakdown"]["popularity"],                    s2["breakdown"]["popularity"],                    "Popularity"),
        winner(data1["commit_metrics"].get("total_commits",0),  data2["commit_metrics"].get("total_commits",0),   "Total Commits"),
        winner(data1["repository_metrics"].get("total_stars",0),data2["repository_metrics"].get("total_stars",0), "Total Stars"),
        winner(data1["code_quality"].get("repos_with_tests_pct",0), data2["code_quality"].get("repos_with_tests_pct",0), "Test Coverage %"),
        winner(data1["code_quality"].get("repos_with_ci_cd_pct",0), data2["code_quality"].get("repos_with_ci_cd_pct",0), "CI/CD Coverage %"),
        winner(data1["collaboration"].get("unique_collaborators",0), data2["collaboration"].get("unique_collaborators",0), "Collaborators"),
    ]

    wins1 = sum(1 for c in comparisons if c["winner"] == u1)
    wins2 = sum(1 for c in comparisons if c["winner"] == u2)
    overall_winner = u1 if s1["overall_score"] > s2["overall_score"] else \
                     u2 if s2["overall_score"] > s1["overall_score"] else "TIE"

    comparison_summary = _generate_comparison_summary(u1, u2, data1, data2, comparisons, overall_winner)

    return {
        "user1": u1,
        "user2": u2,
        "overall_winner":    overall_winner,
        "score_user1":       s1["overall_score"],
        "score_user2":       s2["overall_score"],
        "verdict_user1":     s1["verdict"],
        "verdict_user2":     s2["verdict"],
        "wins_user1":        wins1,
        "wins_user2":        wins2,
        "metric_comparisons":comparisons,
        "comparison_summary":comparison_summary,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def _generate_summary(username, profile, repo_m, commit_m, code_m,
                      activity_m, lang_m, collab_m, repo_cards, score) -> str:

    if repo_m.get("no_public_repos"):
        return (f"{username} has no public repositories. "
                "Cannot assess technical skills from GitHub alone. "
                "Request portfolio or private repo access before deciding.")

    if not AI_API_KEY:
        return _fallback_summary(username, repo_m, commit_m, lang_m, score)

    # top repos summary
    top_repos_text = ""
    for card in repo_cards[:5]:
        top_repos_text += (
            f"\n  • {card['name']}: {card['stars']}⭐ | {card['total_commits']} commits | "
            f"{card['language']} | tests:{card['has_tests']} ci:{card['has_ci']} docker:{card['has_docker']}"
        )
        for cf in card.get("code_file_analysis", [])[:1]:
            top_repos_text += (
                f"\n    └ {cf['filename']}: {cf['total_lines']} lines, "
                f"{cf['functions_found']} functions, comment ratio {cf['comment_ratio']}"
            )

    prompt = f"""You are a senior engineering hiring manager writing a technical evaluation of a GitHub profile.

CANDIDATE: {username}
Account age: {profile.get('account_age_years')} years | Bio: {profile.get('bio','N/A')}
Followers: {profile.get('followers')} | Following: {profile.get('following')}

REPOSITORIES: {repo_m.get('total_repositories')} public repos
Stars: {repo_m.get('total_stars')} | Forks: {repo_m.get('total_forks')} | Releases: {repo_m.get('total_releases')}
Topics: {repo_m.get('top_topics',[])}

LANGUAGES:
Primary: {lang_m.get('primary_language')} | Specialization: {lang_m.get('specialization')}
Breakdown: {lang_m.get('language_breakdown_pct',{})}

COMMITS: {commit_m.get('total_commits')} total
Span: {commit_m.get('active_span_days')} days | Avg/month: {commit_m.get('avg_commits_per_month')}
Last 30 days: {commit_m.get('commits_last_30_days')} | Trend: {commit_m.get('activity_trend')}
Busiest day: {commit_m.get('busiest_day_of_week')} | Weekend: {commit_m.get('weekend_commit_pct')}%
Message quality: conventional={commit_m.get('commit_message_quality',{}).get('conventional_commits_pct')}%, vague={commit_m.get('commit_message_quality',{}).get('vague_messages_pct')}%, rating={commit_m.get('commit_message_quality',{}).get('quality_rating')}

CODE QUALITY:
README: {code_m.get('repos_with_readme_pct')}% | Tests: {code_m.get('repos_with_tests_pct')}% | CI/CD: {code_m.get('repos_with_ci_cd_pct')}%
Docker: {code_m.get('repos_with_docker_pct')}% | Quality configs: {code_m.get('repos_with_quality_cfg_pct')}%
Test/total file ratio: {code_m.get('test_to_total_file_ratio')} | Avg README quality: {code_m.get('avg_readme_quality_score')}/10

COLLABORATION:
Collaborators: {collab_m.get('unique_collaborators')} | Collab rate: {collab_m.get('collaboration_rate_pct')}%
Issues resolved: {collab_m.get('issue_resolution_rate_pct')}% | PR merge rate: {collab_m.get('pr_merge_rate_pct')}%

ACTIVITY: {activity_m.get('activity_level')} | Last push: {activity_m.get('days_since_last_push')} days ago
Recent: {activity_m.get('recent_activity_feed',[][:3])}

TOP REPOSITORIES WITH CODE ANALYSIS:{top_repos_text}

SCORE: {score.get('overall_score')}/100 | VERDICT: {score.get('verdict')}
Green flags: {score.get('green_flags',[])}
Red flags: {score.get('red_flags',[])}

Write a 250-300 word professional hiring evaluation. Cover:
1. Overall developer profile and estimated experience level (junior/mid/senior)
2. Technical specialization and stack depth
3. Code quality and engineering discipline (tests, CI/CD, documentation, commit hygiene)
4. Activity consistency and work habits
5. Collaboration and community engagement
6. Specific strengths (cite numbers) and concerns
7. Final hiring recommendation with one clear justification sentence

Write in flowing paragraphs. Be direct and specific. No bullet points."""

    return _call_ai(prompt)


def _generate_comparison_summary(u1, u2, d1, d2, comparisons, winner) -> str:
    if not AI_API_KEY:
        s1 = d1["scoring"]["overall_score"]
        s2 = d2["scoring"]["overall_score"]
        return (f"{winner} is the stronger candidate. "
                f"{u1}: {s1}/100 ({d1['scoring']['verdict']}) vs "
                f"{u2}: {s2}/100 ({d2['scoring']['verdict']}). "
                "Set AI_API_KEY for a detailed comparison narrative.")

    wins = {c["winner"]: 0 for c in comparisons}
    for c in comparisons:
        wins[c["winner"]] = wins.get(c["winner"], 0) + 1

    prompt = f"""You are a senior technical hiring manager comparing two GitHub profiles for a software engineering role.

CANDIDATE 1: {u1}
Score: {d1['scoring']['overall_score']}/100 | Verdict: {d1['scoring']['verdict']}
Language: {d1['languages'].get('primary_language')} | Specialization: {d1['languages'].get('specialization')}
Commits: {d1['commit_metrics'].get('total_commits')} | Stars: {d1['repository_metrics'].get('total_stars')}
Tests: {d1['code_quality'].get('repos_with_tests_pct')}% | CI/CD: {d1['code_quality'].get('repos_with_ci_cd_pct')}%
Activity: {d1['activity'].get('activity_level')} | Trend: {d1['commit_metrics'].get('activity_trend')}
Green flags: {d1['scoring'].get('green_flags',[])}
Red flags: {d1['scoring'].get('red_flags',[])}

CANDIDATE 2: {u2}
Score: {d2['scoring']['overall_score']}/100 | Verdict: {d2['scoring']['verdict']}
Language: {d2['languages'].get('primary_language')} | Specialization: {d2['languages'].get('specialization')}
Commits: {d2['commit_metrics'].get('total_commits')} | Stars: {d2['repository_metrics'].get('total_stars')}
Tests: {d2['code_quality'].get('repos_with_tests_pct')}% | CI/CD: {d2['code_quality'].get('repos_with_ci_cd_pct')}%
Activity: {d2['activity'].get('activity_level')} | Trend: {d2['commit_metrics'].get('activity_trend')}
Green flags: {d2['scoring'].get('green_flags',[])}
Red flags: {d2['scoring'].get('red_flags',[])}

METRIC WINS: {u1}={wins.get(u1,0)}, {u2}={wins.get(u2,0)}
OVERALL WINNER: {winner}

Write a 200-250 word head-to-head comparison for a hiring decision. Cover:
1. Key differences in technical depth and specialization
2. Who has better code quality discipline and why
3. Who is more active and consistent
4. Each candidate's biggest strength and biggest weakness
5. Clear recommendation of who to hire and why

Be direct and specific. Use the numbers. No bullet points."""

    return _call_ai(prompt)


def _call_ai(prompt: str) -> str:
    try:
        if AI_PROVIDER == "openai":
            r = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {AI_API_KEY}", "content-type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800
                },
                timeout=40,
            )
            if r.status_code != 200:
                return f"[AI error {r.status_code}: {r.json()}]"
            return r.json()["choices"][0]["message"]["content"].strip()

        elif AI_PROVIDER == "groq":
            r = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {AI_API_KEY}", "content-type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "max_tokens": 800},
                timeout=40,
            )
            if r.status_code != 200:
                return f"[AI error {r.status_code}: {r.json()}]"
            return r.json()["choices"][0]["message"]["content"].strip()

        elif AI_PROVIDER == "gemini":
            models = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash-latest"]
            for model in models:
                r = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={AI_API_KEY}",
                    headers={"content-type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"maxOutputTokens": 800, "temperature": 0.4}},
                    timeout=40,
                )
                if r.status_code == 200:
                    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            return "[Gemini error: no available model found]"

        elif AI_PROVIDER == "anthropic":
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": AI_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]},
                timeout=40,
            )
            if r.status_code != 200:
                return f"[AI error {r.status_code}: {r.json()}]"
            return r.json()["content"][0]["text"].strip()

        else:
            return f"[Unknown AI_PROVIDER: {AI_PROVIDER}]"

    except Exception as e:
        return f"[AI unavailable: {e}]"

def _fallback_summary(username, repo_m, commit_m, lang_m, score):
    return (
        f"{username} is a {lang_m.get('primary_language','Unknown')}-focused "
        f"{lang_m.get('specialization','General')} developer with "
        f"{repo_m.get('total_repositories',0)} public repos, "
        f"{repo_m.get('total_stars',0)} stars, and "
        f"{commit_m.get('total_commits',0)} commits sampled. "
        f"Activity trend: {commit_m.get('activity_trend','UNKNOWN')}. "
        f"Score: {score.get('overall_score','N/A')}/100 — Verdict: {score.get('verdict','N/A')}. "
        "Set AI_API_KEY in .env for a full AI narrative."
    )
