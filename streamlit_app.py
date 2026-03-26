"""
streamlit_app.py — Full GitHub Analyzer UI
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import requests
import time

API = "http://localhost:8000"

st.set_page_config(page_title="GitHub Candidate Analyzer", page_icon="🔍", layout="wide")

st.markdown("""
<style>
  .verdict-STRONG_ACCEPT{background:#065f46;color:#d1fae5;padding:10px 20px;border-radius:8px;font-size:1.1rem;font-weight:700;display:inline-block}
  .verdict-ACCEPT       {background:#166534;color:#bbf7d0;padding:10px 20px;border-radius:8px;font-size:1.1rem;font-weight:700;display:inline-block}
  .verdict-REVIEW       {background:#92400e;color:#fef3c7;padding:10px 20px;border-radius:8px;font-size:1.1rem;font-weight:700;display:inline-block}
  .verdict-REJECT       {background:#991b1b;color:#fecaca;padding:10px 20px;border-radius:8px;font-size:1.1rem;font-weight:700;display:inline-block}
  .verdict-STRONG_REJECT{background:#450a0a;color:#fca5a5;padding:10px 20px;border-radius:8px;font-size:1.1rem;font-weight:700;display:inline-block}
  .summary-box{background:#1e1b4b;border-left:4px solid #818cf8;padding:18px 22px;border-radius:0 8px 8px 0;line-height:1.8;font-size:0.96rem;color:#e0e7ff}
  .flag-green{background:#052e16;color:#86efac;padding:5px 10px;border-radius:4px;margin:3px 0;display:block;font-size:0.85rem}
  .flag-red  {background:#450a0a;color:#fca5a5;padding:5px 10px;border-radius:4px;margin:3px 0;display:block;font-size:0.85rem}
  .repo-card {background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px;margin:8px 0}
  .winner-badge{background:#854d0e;color:#fef08a;padding:8px 16px;border-radius:6px;font-weight:700;display:inline-block}
</style>
""", unsafe_allow_html=True)


def score_bar(label, value, max_val=100):
    pct   = min(value / max_val * 100, 100)
    color = "#22c55e" if pct >= 70 else "#f59e0b" if pct >= 45 else "#ef4444"
    st.markdown(f"""
    <div style="margin:5px 0">
      <div style="display:flex;justify-content:space-between;font-size:.84rem;margin-bottom:2px">
        <span>{label}</span><span style="font-weight:600">{value:.1f}</span>
      </div>
      <div style="background:#334155;border-radius:4px;height:9px">
        <div style="background:{color};width:{pct:.1f}%;height:9px;border-radius:4px"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def verdict_badge(verdict):
    icons = {"STRONG_ACCEPT":"🏆","ACCEPT":"✅","REVIEW":"🔶","REJECT":"❌","STRONG_REJECT":"🚫"}
    icon  = icons.get(verdict, "🔶")
    return f'<span class="verdict-{verdict}">{icon} {verdict.replace("_"," ")}</span>'


def render_profile(data):
    profile  = data["profile"]
    repos    = data["repository_metrics"]
    commits  = data["commit_metrics"]
    code     = data["code_quality"]
    activity = data["activity"]
    lang     = data["languages"]
    collab   = data["collaboration"]
    score    = data["scoring"]
    summary  = data["summary"]
    top_repos= data["top_repositories"]

    # ── Header ──────────────────────────────────────────────
    hc1, hc2 = st.columns([1, 4])
    with hc1:
        if profile.get("avatar_url"):
            st.image(profile["avatar_url"], width=120)
    with hc2:
        st.markdown(f"### {profile.get('name') or data['username']}  `{data['username']}`")
        if profile.get("bio"): st.caption(profile["bio"])
        parts = []
        if profile.get("location"): parts.append(f"📍 {profile['location']}")
        if profile.get("company"):  parts.append(f"🏢 {profile['company']}")
        if profile.get("blog"):     parts.append(f"🌐 {profile['blog']}")
        if profile.get("email"):    parts.append(f"✉️ {profile['email']}")
        if parts: st.markdown("  ·  ".join(parts))
        st.markdown(
            f"**{profile.get('followers',0)}** followers · "
            f"**{profile.get('following',0)}** following · "
            f"**{profile.get('public_repos',0)}** public repos · "
            f"**{profile.get('account_age_years','?')}** yrs on GitHub"
        )
        if profile.get("profile_url"):
            st.markdown(f"[Open GitHub ↗]({profile['profile_url']})")

    st.divider()

    if repos.get("no_public_repos"):
        st.warning("⚠️ No public repositories found.")
        st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)
        return

    # ── Verdict + score ──────────────────────────────────────
    vc1, vc2 = st.columns([2, 3])
    with vc1:
        st.markdown("#### 🎯 Hiring Verdict")
        st.markdown(verdict_badge(score.get("verdict","REVIEW")), unsafe_allow_html=True)
        st.metric("Overall Score", f"{score.get('overall_score',0):.1f} / 100")
        spec = lang.get("specialization","—")
        st.markdown(f"**Specialization:** {spec}")
        st.markdown(f"**Primary Language:** {lang.get('primary_language','—')}")
    with vc2:
        st.markdown("#### 📊 Score Breakdown")
        bd = score.get("breakdown", {})
        for label, key in [
            ("Commit Activity","commit_activity"),("Code Quality","code_quality"),
            ("Consistency","consistency"),("Recency","recency"),
            ("Collaboration","collaboration"),("Popularity","popularity")
        ]:
            score_bar(label, bd.get(key, 0))

    st.divider()

    # ── Green / Red flags ────────────────────────────────────
    fc1, fc2 = st.columns(2)
    with fc1:
        st.markdown("#### ✅ Strengths")
        for f in score.get("green_flags", []):
            st.markdown(f'<span class="flag-green">✓ {f}</span>', unsafe_allow_html=True)
        if not score.get("green_flags"):
            st.caption("No notable strengths detected.")
    with fc2:
        st.markdown("#### ⚠️ Concerns")
        for f in score.get("red_flags", []):
            st.markdown(f'<span class="flag-red">✗ {f}</span>', unsafe_allow_html=True)
        if not score.get("red_flags"):
            st.caption("No major concerns detected.")

    st.divider()

    # ── AI Summary ───────────────────────────────────────────
    st.markdown("#### 🤖 AI Hiring Summary")
    st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Metrics grid ─────────────────────────────────────────
    st.markdown("#### 📈 Full Metrics")
    t1, t2, t3, t4 = st.tabs(["Commits","Code Quality","Collaboration","Activity"])

    with t1:
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Total Commits",     commits.get("total_commits",0))
        c2.metric("Avg / Month",       commits.get("avg_commits_per_month",0))
        c3.metric("Last 30 Days",      commits.get("commits_last_30_days",0))
        c4.metric("Trend",             commits.get("activity_trend","—"))
        c1.metric("Active Span",       f"{commits.get('active_span_days',0)} days")
        c2.metric("Busiest Day",       commits.get("busiest_day_of_week","—"))
        c3.metric("Weekend Commits",   f"{commits.get('weekend_commit_pct',0)}%")
        c4.metric("Avg / Repo",        commits.get("average_commits_per_repo",0))
        mq = commits.get("commit_message_quality",{})
        st.markdown("**Commit Message Quality**")
        mc1,mc2,mc3,mc4 = st.columns(4)
        mc1.metric("Conventional",  f"{mq.get('conventional_commits_pct',0)}%")
        mc2.metric("Vague",         f"{mq.get('vague_messages_pct',0)}%")
        mc3.metric("Avg Length",    f"{mq.get('avg_message_length_chars',0)} chars")
        mc4.metric("Quality Rating",mq.get("quality_rating","—"))

        if commits.get("repo_commit_counts"):
            st.markdown("**Commits per Repository**")
            rc = commits["repo_commit_counts"]
            for rname, cnt in list(rc.items())[:10]:
                score_bar(rname, cnt, max_val=max(rc.values()) or 1)

    with t2:
        q1,q2,q3,q4 = st.columns(4)
        q1.metric("README Coverage",   f"{code.get('repos_with_readme_pct',0)}%")
        q2.metric("Test Coverage",     f"{code.get('repos_with_tests_pct',0)}%")
        q3.metric("CI/CD Coverage",    f"{code.get('repos_with_ci_cd_pct',0)}%")
        q4.metric("Docker Coverage",   f"{code.get('repos_with_docker_pct',0)}%")
        q1.metric("Quality Configs",   f"{code.get('repos_with_quality_cfg_pct',0)}%")
        q2.metric("Total Files",       code.get("total_files",0))
        q3.metric("Test Files",        code.get("total_test_files",0))
        q4.metric("Test/File Ratio",   code.get("test_to_total_file_ratio",0))
        st.metric("Avg README Quality",f"{code.get('avg_readme_quality_score',0)}/10")

        ftd = code.get("file_type_distribution",[])
        if ftd:
            st.markdown("**File Type Distribution**")
            total_f = sum(c for _,c in ftd) or 1
            for ext, cnt in ftd[:12]:
                score_bar(f".{ext}", cnt, max_val=total_f)

    with t3:
        col1,col2,col3,col4 = st.columns(4)
        col1.metric("Collaborators",      collab.get("unique_collaborators",0))
        col2.metric("Collab Rate",        f"{collab.get('collaboration_rate_pct',0)}%")
        col3.metric("Issues Resolved",    f"{collab.get('issue_resolution_rate_pct',0)}%")
        col4.metric("PR Merge Rate",      f"{collab.get('pr_merge_rate_pct',0)}%")
        col1.metric("Total Issues",       collab.get("total_issues_tracked",0))
        col2.metric("Open Issues",        collab.get("open_issues",0))
        col3.metric("Closed Issues",      collab.get("closed_issues",0))
        col4.metric("Pull Requests",      collab.get("total_pull_requests",0))

    with t4:
        a1,a2,a3 = st.columns(3)
        a1.metric("Activity Level",       activity.get("activity_level","—"))
        a2.metric("Days Since Last Push", activity.get("days_since_last_push","—"))
        a3.metric("Events Sampled",       activity.get("total_events_sampled",0))

        feed = activity.get("recent_activity_feed",[])
        if feed:
            st.markdown("**Recent Activity Feed**")
            for item in feed:
                st.markdown(f"• {item}")

        et = activity.get("recent_event_types",{})
        if et:
            st.markdown("**Event Type Breakdown**")
            ec1,ec2 = st.columns(2)
            items = list(et.items())
            for i, (etype, cnt) in enumerate(items):
                (ec1 if i%2==0 else ec2).metric(etype.replace("Event",""), cnt)

    st.divider()

    # ── Language breakdown ────────────────────────────────────
    lang_bd = lang.get("language_breakdown_pct",{})
    if lang_bd:
        st.markdown("#### 🧑‍💻 Language Breakdown")
        items = sorted(lang_bd.items(), key=lambda x: -x[1])
        for language, pct in items:
            score_bar(f"{language}  ({pct}%)", pct, max_val=100)

    st.divider()

    # ── Repo metrics ──────────────────────────────────────────
    st.markdown("#### 🏆 Repository Overview")
    rc1,rc2,rc3,rc4 = st.columns(4)
    rc1.metric("Total Stars",    repos.get("total_stars",0))
    rc2.metric("Total Forks",    repos.get("total_forks",0))
    rc3.metric("Total Releases", repos.get("total_releases",0))
    rc4.metric("Archived Repos", repos.get("archived_repos",0))
    rc1.metric("Most Starred",   repos.get("most_starred_repo","—"))
    rc2.metric("Largest Repo",   repos.get("largest_repo","—"))
    rc3.metric("With Topics",    repos.get("repos_with_topics",0))
    rc4.metric("With Homepage",  repos.get("repos_with_homepage",0))

    if repos.get("top_topics"):
        st.markdown("**Top Topics:** " + "  ".join(f"`{t}`" for t in repos["top_topics"]))

    st.divider()

    # ── Top repositories ──────────────────────────────────────
    st.markdown("#### 📁 Top Repositories (Deep Analysis)")
    for card in top_repos[:8]:
        with st.expander(f"{'⭐' if card['stars']>0 else '📁'} {card['name']}  —  {card['stars']}⭐ · {card['total_commits']} commits · {card.get('language','?')}"):
            rc1,rc2,rc3 = st.columns(3)
            rc1.markdown(f"**Stars:** {card['stars']}  |  **Forks:** {card['forks']}")
            rc2.markdown(f"**Files:** {card['total_files']}  |  **Size:** {card['size_kb']} KB")
            rc3.markdown(f"**Contributors:** {card['contributors']}  |  **Releases:** {card['releases']}")

            badges = []
            if card.get("has_readme"): badges.append("📄 README")
            if card.get("has_tests"):  badges.append("🧪 Tests")
            if card.get("has_ci"):     badges.append("⚙️ CI/CD")
            if card.get("has_docker"): badges.append("🐳 Docker")
            if card.get("archived"):   badges.append("📦 Archived")
            if badges: st.markdown("  ".join(badges))

            if card.get("description"):
                st.caption(card["description"])
            if card.get("topics"):
                st.markdown("Topics: " + " ".join(f"`{t}`" for t in card["topics"]))

            if card.get("code_file_analysis"):
                st.markdown("**Code File Analysis:**")
                for cf in card["code_file_analysis"]:
                    st.markdown(
                        f"&nbsp;&nbsp;`{cf['filename']}` — "
                        f"{cf['total_lines']} lines · "
                        f"{cf['functions_found']} functions · "
                        f"{cf['classes_found']} classes · "
                        f"comment ratio: {cf['comment_ratio']}"
                    )

            if card.get("url"):
                st.markdown(f"[Open on GitHub ↗]({card['url']})")

    st.divider()
    with st.expander("📄 Full Raw JSON"):
        st.json(data)


def render_comparison(data):
    st.markdown("#### 👥 Compare Two Candidates")
    cc1, cc2 = st.columns(2)
    with cc1:
        u1 = st.text_input("Candidate 1 GitHub username", placeholder="e.g. torvalds", key="u1")
    with cc2:
        u2 = st.text_input("Candidate 2 GitHub username", placeholder="e.g. gvanrossum", key="u2")

    if st.button("⚖️ Compare Candidates", type="primary"):
        if not u1 or not u2:
            st.warning("Please enter both usernames.")
            return
        if u1.strip() == u2.strip():
            st.warning("Please enter two different usernames.")
            return

        with st.spinner(f"Analyzing {u1} and {u2}... this may take 30–60 seconds."):
            try:
                t0   = time.time()
                resp = requests.post(f"{API}/compare",
                                     json={"username1": u1.strip(), "username2": u2.strip()},
                                     timeout=300)
                elapsed = round(time.time()-t0, 1)
                if resp.status_code != 200:
                    st.error(f"Error: {resp.json().get('detail', resp.text)}")
                    return
                result = resp.json()
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach FastAPI. Run: uvicorn main:app --reload")
                return

        comp  = result["comparison"]
        data1 = result["candidate1"]
        data2 = result["candidate2"]

        st.divider()

        # ── Winner banner ───────────────────────────────────
        winner = comp["overall_winner"]
        st.markdown(f'<div class="winner-badge">🏆 Overall Winner: {winner}</div>', unsafe_allow_html=True)
        st.markdown("")

        # ── Score comparison ─────────────────────────────────
        sc1, sc2, sc3 = st.columns([2,1,2])
        with sc1:
            st.markdown(f"### {u1}")
            st.markdown(verdict_badge(comp["verdict_user1"]), unsafe_allow_html=True)
            st.metric("Score", f"{comp['score_user1']}/100")
        with sc2:
            st.markdown("### VS", help="Head to head comparison")
        with sc3:
            st.markdown(f"### {u2}")
            st.markdown(verdict_badge(comp["verdict_user2"]), unsafe_allow_html=True)
            st.metric("Score", f"{comp['score_user2']}/100")

        st.divider()

        # ── AI comparison summary ─────────────────────────────
        st.markdown("#### 🤖 AI Comparison Summary")
        st.markdown(f'<div class="summary-box">{comp["comparison_summary"]}</div>', unsafe_allow_html=True)

        st.divider()

        # ── Metric by metric ─────────────────────────────────
        st.markdown("#### 📊 Metric-by-Metric Comparison")
        for c in comp["metric_comparisons"]:
            v1  = c["values"].get(u1, 0)
            v2  = c["values"].get(u2, 0)
            mx  = max(v1, v2, 1)
            w   = c["winner"]
            col1, col_mid, col2 = st.columns([3,2,3])
            with col1:
                pct1 = v1/mx*100
                color1 = "#22c55e" if w==u1 else "#64748b"
                st.markdown(f"""
                <div style="text-align:right;margin:4px 0">
                  <span style="font-size:.85rem">{v1}</span>
                  <div style="background:#334155;border-radius:4px;height:8px;margin-top:3px">
                    <div style="background:{color1};width:{pct1:.0f}%;height:8px;border-radius:4px;float:right"></div>
                  </div>
                </div>""", unsafe_allow_html=True)
            with col_mid:
                st.markdown(f"<div style='text-align:center;font-size:.8rem;padding-top:6px;color:#94a3b8'>{c['metric']}</div>", unsafe_allow_html=True)
            with col2:
                pct2 = v2/mx*100
                color2 = "#22c55e" if w==u2 else "#64748b"
                st.markdown(f"""
                <div style="text-align:left;margin:4px 0">
                  <span style="font-size:.85rem">{v2}</span>
                  <div style="background:#334155;border-radius:4px;height:8px;margin-top:3px">
                    <div style="background:{color2};width:{pct2:.0f}%;height:8px;border-radius:4px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # ── Side by side profiles ─────────────────────────────
        st.markdown("#### 👤 Side-by-Side Profiles")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(f"**{u1}**")
            with st.container():
                render_profile(data1)
        with p2:
            st.markdown(f"**{u2}**")
            with st.container():
                render_profile(data2)

        st.caption(f"⏱ Comparison completed in {elapsed}s")


# ── Main app ──────────────────────────────────────────────────────────────────
st.title("🔍 GitHub Candidate Analyzer")
st.caption("Deep technical analysis of GitHub profiles for hiring decisions.")

tab1, tab2 = st.tabs(["👤 Single Candidate", "⚖️ Compare Two Candidates"])

with tab1:
    ci, cb = st.columns([5,1])
    with ci:
        username = st.text_input("GitHub username", placeholder="e.g. torvalds",
                                 label_visibility="collapsed", key="single_input")
    with cb:
        go = st.button("Analyze ▶", type="primary", use_container_width=True)

    if go and username:
        with st.spinner(f"⏳ Analyzing **{username}** — fetching repos, commits, code files, events…"):
            try:
                t0   = time.time()
                resp = requests.get(f"{API}/analyze/{username.strip()}", timeout=300)
                elapsed = round(time.time()-t0, 1)
                if resp.status_code == 404:
                    st.error(f"❌ User **{username}** not found on GitHub.")
                    st.stop()
                if resp.status_code != 200:
                    st.error(f"❌ Error {resp.status_code}: {resp.json().get('detail', resp.text)}")
                    st.stop()
                data = resp.json()
            except requests.exceptions.ConnectionError:
                st.error("❌ Cannot reach FastAPI. Run:\n```\nuvicorn main:app --reload\n```")
                st.stop()

        render_profile(data)
        st.caption(f"⏱ Analysis completed in {elapsed}s")

    elif go and not username:
        st.warning("Please enter a GitHub username.")

with tab2:
    render_comparison(None)
