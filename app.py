from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html import escape
from textwrap import dedent
from typing import Iterable

import dotenv
import pandas as pd
import requests
import streamlit as st

dotenv.load_dotenv()
if "saved_email" not in st.session_state:
    st.session_state["saved_email"] = os.getenv("GOOGLE_WORKSPACE_EMAIL", "")
if "saved_pass" not in st.session_state:
    st.session_state["saved_pass"] = os.getenv("GOOGLE_WORKSPACE_PASSWORD", "")
if "google_linked" not in st.session_state:
    st.session_state["google_linked"] = bool(st.session_state["saved_email"] and st.session_state["saved_pass"])

# ── BACKEND API CONFIGURATION ─────────────────────────────────────────────────
API_BASE = "http://localhost:8000"


def _auth_headers() -> dict:
    """Return Authorization header if the user is logged in."""
    token = st.session_state.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_get(path: str, params: dict | None = None) -> dict | list | None:
    """GET request to the backend API."""
    try:
        resp = requests.get(f"{API_BASE}{path}", headers=_auth_headers(), params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to backend. Is the server running on port 8000?")
        return None
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            st.session_state.clear()
            st.rerun()
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def api_post(path: str, data: dict | None = None) -> dict | None:
    """POST request to the backend API."""
    try:
        resp = requests.post(f"{API_BASE}{path}", headers=_auth_headers(), json=data, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to backend. Is the server running on port 8000?")
        return None
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            st.session_state.clear()
            st.rerun()
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def api_put(path: str, data: dict | None = None) -> dict | None:
    """PUT request to the backend API."""
    try:
        resp = requests.put(f"{API_BASE}{path}", headers=_auth_headers(), json=data, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to backend. Is the server running on port 8000?")
        return None
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            st.session_state.clear()
            st.rerun()
        st.error(f"API error: {e.response.status_code} — {e.response.text}")
        return None


def api_upload(path: str, file) -> dict | None:
    """Upload a file to the backend API."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        resp = requests.post(f"{API_BASE}{path}", headers=_auth_headers(), files=files, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        st.error("⚠️ Cannot connect to backend.")
        return None
    except requests.HTTPError as e:
        st.error(f"Upload error: {e.response.status_code} — {e.response.text}")
        return None


def call_llama(prompt: str, expect_json: bool = False, system: str = "") -> str:
    """Route LLM calls through the backend chat endpoint."""
    result = api_post("/api/ai/chat", {"message": prompt, "context": system})
    if result:
        return result.get("reply", "")
    return '{"error": "Backend unavailable"}' if expect_json else "Error: Backend unavailable"
# ─────────────────────────────────────────────────────────────────────────────


st.set_page_config(
    page_title="AI-Driven Smart Hiring Platform Copilot",
    layout="wide",
    initial_sidebar_state="expanded",
)





@dataclass(frozen=True)
class CandidateAction:
    candidate: str
    role: str
    action: str
    detail: str


def clean_html(markup: str) -> str:
    return dedent(markup).strip()


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

def inject_css() -> None:
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>\n{css}\n</style>", unsafe_allow_html=True)


import streamlit.components.v1 as components


def inject_loader() -> None:
    components.html("""
    <script>
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById("custom-loader-overlay")) {
        const overlay = parentDoc.createElement("div");
        overlay.id = "custom-loader-overlay";
        overlay.innerHTML = `
            
            Loading...
        `;
        parentDoc.body.appendChild(overlay);
        
        const blockContainer = parentDoc.querySelector('[data-testid="stAppViewBlockContainer"]');
        if (blockContainer) {
            blockContainer.style.opacity = '0';
        }

        setTimeout(() => {
            overlay.style.opacity = '0';
            if (blockContainer) {
                blockContainer.style.transition = 'opacity 0.3s';
                blockContainer.style.opacity = '1';
            }
            setTimeout(() => {
                overlay.remove();
            }, 500);
        }, 3500);
    }
    </script>
    """, height=0, width=0)

# ─────────────────────────────────────────────────────────────────────────────
# DATA (loaded from backend API)
# ─────────────────────────────────────────────────────────────────────────────

# Column name mappings: backend snake_case → frontend Title Case
_ROLE_COLUMNS = {
    "id": "ID", "req_id": "Req ID", "role": "Role", "business_unit": "Business Unit",
    "location": "Location", "openings": "Openings", "applicants": "Applicants",
    "screened": "Screened", "shortlisted": "Shortlisted", "interview": "Interview",
    "offer": "Offer", "hired": "Hired", "days_open": "Days Open",
    "target_days": "Target Days", "risk": "Risk", "priority": "Priority",
    "required_skills": "Required Skills", "experience_min": "Experience Min",
    "salary_band": "Salary Band",
}

_CANDIDATE_COLUMNS = {
    "id": "ID", "candidate": "Candidate", "role": "Role", "location": "Location",
    "experience": "Experience", "match": "Match", "stage": "Stage",
    "availability": "Availability", "salary_fit": "Salary Fit", "risk": "Risk",
    "skills": "Skills", "source": "Source", "last_touch": "Last Touch",
    "education": "Education", "certifications": "Certifications",
    "summary": "Summary", "resume_filename": "Resume File", "skills_match": "Skills Match",
}




def _api_to_df(data: list[dict] | None, col_map: dict) -> pd.DataFrame:
    """Convert API response list to a DataFrame with renamed columns."""
    if not data:
        return pd.DataFrame(columns=list(col_map.values()))
    df = pd.DataFrame(data)
    # Only rename columns that exist in the response
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    return df.rename(columns=rename)


def load_roles() -> pd.DataFrame:
    data = api_get("/api/roles")
    return _api_to_df(data, _ROLE_COLUMNS)


def load_candidates() -> pd.DataFrame:
    data = api_get("/api/candidates")
    return _api_to_df(data, _CANDIDATE_COLUMNS)


def skill_list(candidates: pd.DataFrame) -> list[str]:
    skills: set[str] = set()
    for values in candidates["Skills"]:
        skills.update(skill.strip() for skill in values.split(","))
    return sorted(skills)


def html_table(df: pd.DataFrame, columns: Iterable[str]) -> str:
    rows = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{row[column]}</td>" for column in columns)
        rows.append(f"<tr>{cells}</tr>")
    headers = "".join(f"<th>{column}</th>" for column in columns)
    return f"<table class='mini-table'><thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


# ─────────────────────────────────────────────────────────────────────────────
# EXISTING PAGES
# ─────────────────────────────────────────────────────────────────────────────

def render_header(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    active_jobs = len(roles)
    avg_match = round(candidates["Match"].mean(), 1)
    offers = int(roles["Offer"].sum())

    st.markdown(
        clean_html(
            f"""
        <div class="topline">
            <div class="brand-block">
                <div class="brand-kicker">AI-Driven Smart Hiring Platform Copilot</div>
                <h1 class="brand-title">Welcome, hiring team</h1>
                <div class="brand-copy">
                    See open jobs, find strong candidates, and schedule interviews
                    from one simple workspace.
                </div>
            </div>
            <div class="status-strip">
                <div class="status-label">Average candidate match</div>
                <div class="status-value">{avg_match:.1f}%</div>
                <div class="status-foot">{active_jobs} open jobs and {offers} offers in progress</div>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def metric_row(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    total_openings = int(roles["Openings"].sum())
    active_candidates = int(roles["Applicants"].sum())
    shortlisted = int(roles["Shortlisted"].sum())
    avg_days = round(roles["Days Open"].mean(), 1)
    offers = int(roles["Offer"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("People to hire", total_openings, "Across 6 jobs")
    c2.metric("Total applicants", f"{active_candidates:,}", f"{shortlisted} selected")
    c3.metric("Average hiring time", f"{avg_days} days", "About 5 days faster")
    c4.metric("Offers sent", offers, "3 added this week")


def render_quick_actions() -> None:
    st.subheader("Quick actions")
    st.markdown(
        clean_html(
            """
        <div class="quick-grid">
            <div class="quick-card blue">
                <div class="quick-number">1</div>
                <div class="quick-title">Analyse a Job Description</div>
                <div class="quick-copy">Upload or paste a JD — AI extracts skills, seniority, flags issues and rewrites it.</div>
            </div>
            <div class="quick-card teal">
                <div class="quick-number">2</div>
                <div class="quick-title">Match &amp; Chat a Resume</div>
                <div class="quick-copy">Upload a resume file, score it against a JD, and chat with AI about any candidate.</div>
            </div>
            <div class="quick-card pink">
                <div class="quick-number">3</div>
                <div class="quick-title">Recruitment Insights &amp; Skill Gaps</div>
                <div class="quick-copy">View pipeline health, detect bottlenecks, analyse skill gaps, and track recruitment performance.</div>
            </div>
            <div class="quick-card amber">
                <div class="quick-number">4</div>
                <div class="quick-title">Generate a Report</div>
                <div class="quick-copy">AI-generated recruitment summaries, pipeline reports, and talent gap analyses in one click.</div>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )
    buttons = st.columns(4)
    labels = ["Open JD Analyser", "Open Resume AI", "Recruitment Insights", "Generate Report"]
    messages = [
        "Go to JD Analyser in the sidebar.",
        "Go to Resume AI in the sidebar.",
        "Go to Recruitment Insights in the sidebar.",
        "Go to Reports in the sidebar.",
    ]
    for index, (column, label, message) in enumerate(zip(buttons, labels, messages)):
        with column:
            if st.button(label, key=f"quick-action-{index}", use_container_width=True):
                st.toast(message)


def render_pipeline(roles: pd.DataFrame) -> None:
    stage_map = [
        ("Applicants", int(roles["Applicants"].sum()), "#0f8b8d"),
        ("AI reviewed", int(roles["Screened"].sum()), "#2a9d8f"),
        ("Selected", int(roles["Shortlisted"].sum()), "#e9c46a"),
        ("Interviews", int(roles["Interview"].sum()), "#db2777"),
        ("Offers sent", int(roles["Offer"].sum()), "#e76f51"),
        ("Hired", int(roles["Hired"].sum()), "#264653"),
    ]
    max_value = max(value for _, value, _ in stage_map)
    cards = []
    for label, value, color in stage_map:
        conversion = round(value / max_value * 100)
        cards.append(
            clean_html(
                f"""
            <div class="stage" style="--stage-color: {color};">
                <div class="stage-label">{label}</div>
                <div class="stage-number">{value:,}</div>
                <div class="stage-meta">{conversion}% of applicants</div>
            </div>
            """
            )
        )

    st.markdown("<div class='pipeline'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_role_progress(roles: pd.DataFrame) -> None:
    rows = []
    for _, row in roles.sort_values(["Priority", "Days Open"], ascending=[True, False]).iterrows():
        coverage = min(100, round(row["Shortlisted"] / max(row["Openings"], 1) * 100))
        risk_class = "hot" if row["Risk"] == "High" else "good" if row["Risk"] == "Low" else ""
        rows.append(
            clean_html(
                f"""
            <div class="bar-row">
                <div class="bar-meta">
                    <span>{row['Role']}</span>
                    <span>{coverage}% candidate coverage</span>
                </div>
                <div class="bar-shell"><div class="bar-fill" style="--width: {coverage}%;"></div></div>
                <span class="pill {risk_class}">{row['Risk']} attention</span>
                <span class="pill">{row['Location']}</span>
                <span class="pill">{row['Openings']} openings</span>
            </div>
            """
            )
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_priority_actions(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    high_risk = roles[roles["Risk"] == "High"].sort_values("Days Open", ascending=False).head(2)
    top_candidate = candidates.sort_values("Match", ascending=False).iloc[0]
    overdue = roles[roles["Days Open"] > roles["Target Days"]]

    cards = [
        (
            "Job needs more candidates",
            f"{high_risk.iloc[0]['Role']} needs {high_risk.iloc[0]['Openings']} people and has been open for {high_risk.iloc[0]['Days Open']} days.",
            "",
        ),
        (
            "Strong candidate found",
            f"{top_candidate['Candidate']} is a {top_candidate['Match']}% match for {top_candidate['Role']} with {top_candidate['Availability']} availability.",
            "green",
        ),
        (
            "Jobs taking longer than planned",
            f"{len(overdue)} jobs have passed their target time. Schedule interviews and confirm salary approvals today.",
            "gold",
        ),
    ]

    html = ""
    for title, copy, class_name in cards:
        html += (
            f"<div class='action-card {class_name}'><div class='action-title'>{title}</div>"
            f"<div class='action-copy'>{copy}</div></div>"
        )
    st.markdown(html, unsafe_allow_html=True)


@st.fragment
def render_command_center(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    roles = load_roles()
    candidates = load_candidates()
    render_header(roles, candidates)
    
    c_left, c_right = st.columns([5, 1])
    with c_left:
        st.caption(f"🔄 **Live Data**: Last updated at {datetime.now().strftime('%I:%M:%S %p')}")
    with c_right:
        st.button("🔄 Refresh", use_container_width=True)
        
    metric_row(roles, candidates)
    st.markdown("### Hiring journey")
    st.markdown(
        '<div class="section-intro">A simple view of how applicants move from application to joining.</div>',
        unsafe_allow_html=True,
    )
    render_pipeline(roles)

    left, right = st.columns([1.4, 1])
    with left:
        st.markdown('<div class="panel"><div class="panel-title">Jobs and candidate coverage</div>', unsafe_allow_html=True)
        render_role_progress(roles)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="panel"><div class="panel-title">What to do today</div>', unsafe_allow_html=True)
        render_priority_actions(roles, candidates)
        st.markdown("</div>", unsafe_allow_html=True)

    trend_tab, jobs_tab, activity_tab = st.tabs(["Applications trend", "Hiring by job", "Recent activity"])
    with trend_tab:
        trend = pd.DataFrame(
            {
                "Week": [date.today() - timedelta(weeks=offset) for offset in range(7, -1, -1)],
                "Applicants": [148, 162, 185, 178, 204, 226, 241, 255],
                "Shortlisted": [21, 24, 29, 31, 35, 39, 43, 48],
                "Interviews": [9, 12, 14, 13, 16, 18, 19, 22],
            }
        ).set_index("Week")
        st.subheader("Applications over the last 8 weeks")
        st.line_chart(trend, height=280)

    with jobs_tab:
        funnel = roles[["Role", "Applicants", "Screened", "Shortlisted", "Interview", "Offer", "Hired"]].set_index("Role")
        st.subheader("Progress for each open job")
        st.bar_chart(funnel, height=280)

    with activity_tab:
        activity = pd.DataFrame(
            [
                {"Time": "10 minutes ago", "Update": "Aarav Mehta selected for an AI Engineer interview", "Owner": "Priya"},
                {"Time": "45 minutes ago", "Update": "Interview scheduled for Rohan Iyer", "Owner": "Vikram"},
                {"Time": "Today, 09:20", "Update": "Offer sent to Kabir Rao", "Owner": "Neha"},
                {"Time": "Yesterday", "Update": "12 new applications reviewed by AI", "Owner": "AI assistant"},
            ]
        )
        st.subheader("Latest team updates")
        st.dataframe(activity, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: FIND CANDIDATES (enhanced with Ranking + Comparison)
# ─────────────────────────────────────────────────────────────────────────────

def render_candidate_card(row: pd.Series) -> None:
    risk_class = "hot" if row["Risk"] == "High" else "good" if row["Risk"] == "Low" else ""
    skills_html = "".join(f"<span class='pill'>{skill.strip()}</span>" for skill in row["Skills"].split(",")[:5])
    st.markdown(
        clean_html(
            f"""
        <div class="candidate-card">
            <div class="candidate-head" style="justify-content: flex-start; gap: 20px;">
                <div style="display: flex; gap: 15px;">
                    <div style="text-align: center;">
                        <div class="score-ring" style="--score: {row['Match']}%;"><span>{row['Match']}</span></div>
                        <div style="font-size: 0.75rem; color: #86868b; margin-top: 4px;">ATS Match</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="score-ring" style="--score: {row.get('Skills Match', 0)}%; --ring-color: #34c759;"><span>{row.get('Skills Match', 0)}</span></div>
                        <div style="font-size: 0.75rem; color: #86868b; margin-top: 4px;">Skills Match</div>
                    </div>
                </div>
                <div>
                    <div class="candidate-name">{row['Candidate']}</div>
                    <div class="candidate-role">{row['Role']} - {row['Location']}</div>
                    <div style="margin-top:.45rem;">
                        <span class="pill {risk_class}">{row['Risk']} risk</span>
                        <span class="pill">{row['Source']}</span>
                        <span class="pill">Stage: {row['Stage']}</span>
                    </div>
                    <div style="margin-top:.6rem;">{skills_html}</div>
                </div>
            </div>
        </div>
        """,
        ),
        unsafe_allow_html=True,
    )


def compute_rank_score(row: pd.Series) -> float:
    """Ranking based purely on ATS Score (Match)."""
    return float(row["Match"])


@st.fragment
def render_candidate_match(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    st.title("Find Candidates")
    st.caption("Choose a job and the AI assistant will show the strongest matches first.")

    role_options = ["All jobs"] + roles["Role"].tolist()
    city_options = ["All cities"] + sorted(candidates["Location"].unique().tolist())

    filter_one, filter_two, filter_three, filter_four = st.columns([1, 1, 1, 1])
    with filter_one:
        selected_role = st.selectbox("Job", role_options, index=0)
    with filter_two:
        selected_city = st.selectbox("City", city_options, index=0)
    with filter_three:
        selected_skills = st.multiselect("Required skills", skill_list(candidates), default=[])
    with filter_four:
        search_name = st.text_input("Candidate name", placeholder="Type a name")

    min_match = st.slider("Minimum skill match", 70, 100, 82, 1)

    filtered = candidates[candidates["Match"] >= min_match].copy()
    if selected_role != "All jobs":
        filtered = filtered[filtered["Role"] == selected_role]
    if selected_city != "All cities":
        filtered = filtered[filtered["Location"] == selected_city]
    if search_name:
        filtered = filtered[filtered["Candidate"].str.contains(search_name, case=False, regex=False)]
    if selected_skills:
        skill_pattern = "|".join(selected_skills)
        filtered = filtered[filtered["Skills"].str.contains(skill_pattern, case=False, regex=True)]

    filtered = filtered.sort_values("Match", ascending=False)

    st.divider()
    average_match = f"{filtered['Match'].mean():.1f}%" if not filtered.empty else "0%"
    ready_count = int((filtered["Risk"] == "Low").sum()) if not filtered.empty else 0
    city_delta = selected_city if selected_city != "All cities" else "Across selected filters"
    summary_cards = [
        ("Candidates found", len(filtered), f"{len(candidates)} total profiles", "blue"),
        ("Average match", average_match, "Current results", "teal"),
        ("Ready now", ready_count, "Low follow-up needed", "gold"),
        ("Cities", filtered["Location"].nunique() if not filtered.empty else 0, city_delta, "coral"),
    ]
    summary_html = ""
    for label, value, meta, class_name in summary_cards:
        summary_html += clean_html(
            f"""
        <div class="finder-summary-card {class_name}">
            <div class="finder-summary-label">{label}</div>
            <div class="finder-summary-value">{value}</div>
            <div class="finder-summary-meta">{meta}</div>
        </div>
        """
        )
    st.markdown(f'<div class="finder-summary-grid">{summary_html}</div>', unsafe_allow_html=True)

    if filtered.empty:
        st.info("No candidates match the selected filters.")
        return

    tab_ranked, tab_compare = st.tabs(["🏆 AI Candidate Ranking", "⚖️ Compare Candidates"])

    # ── Tab 1: AI Candidate Ranking ─────────────────────────────────────────
    with tab_ranked:
        st.subheader("🏆 AI Candidate Ranking")
        st.caption("Candidates are ranked strictly by their ATS Match Score according to the Job Description.")

        ranked = filtered.copy()
        ranked["AI Score"] = ranked.apply(compute_rank_score, axis=1)
        ranked = ranked.sort_values("AI Score", ascending=False).reset_index(drop=True)


        rank_labels = ["🥇", "🥈", "🥉"]
        rank_classes = ["gold", "silver", "bronze"]

        for i, (_, row) in enumerate(ranked.iterrows()):
            badge_label = rank_labels[i] if i < 3 else str(i + 1)
            badge_class = rank_classes[i] if i < 3 else "default"
            risk_class = "hot" if row["Risk"] == "High" else "good" if row["Risk"] == "Low" else ""

            st.markdown(
                clean_html(f"""
                <div class="ranked-row">
                    <div class="rank-badge {badge_class}">{badge_label}</div>
                    <div class="ranked-info">
                        <div class="ranked-name">{row['Candidate']}</div>
                        <div class="ranked-role">{row['Role']} · {row['Location']} · {row['Experience']} yrs</div>
                        <div style="margin-top:.4rem;">
                            <span class="pill {risk_class}">{row['Risk']} risk</span>
                            <span class="pill">{row['Availability']}</span>
                            <span class="pill">{row['Salary Fit']}</span>
                        </div>
                    </div>
                    <div class="ranked-score-col" style="display: flex; gap: 15px; align-items: center; justify-content: flex-end;">
                        <div style="text-align:center;">
                            <div class="score-ring" style="--score: {row['Match']}%;"><span>{row['Match']}</span></div>
                            <div style="font-size:.72rem;color:var(--muted);margin-top:.3rem;">ATS Score</div>
                        </div>
                        <div style="text-align:center;">
                            <div class="score-ring" style="--score: {row.get('Skills Match', 0)}%; --ring-color: #34c759;"><span>{row.get('Skills Match', 0)}</span></div>
                            <div style="font-size:.72rem;color:var(--muted);margin-top:.3rem;">Skill Match</div>
                        </div>
                    </div>
                </div>
                """),
                unsafe_allow_html=True,
            )
            btn_sl, btn_rej = st.columns([1, 1])
            with btn_sl:
                if st.button(f"Shortlist {row['Candidate']}", key=f"ranked-sl-{i}-{row['Candidate']}", use_container_width=True):
                    res = api_put(f"/api/candidates/{row['ID']}", {"stage": "Interview Round 1"})
                    if res:
                        st.session_state.setdefault("actions", []).append(
                            CandidateAction(row["Candidate"], row["Role"], "Shortlist", "Added to shortlist")
                        )
                        st.toast(f"{row['Candidate']} added to shortlist and moved to Interview section")
            with btn_rej:
                if st.button(f"Reject {row['Candidate']}", key=f"ranked-rej-{i}-{row['Candidate']}", use_container_width=True):
                    res = api_put(f"/api/candidates/{row['ID']}", {"stage": "Rejected"})
                    if res:
                        st.session_state.setdefault("actions", []).append(
                            CandidateAction(row["Candidate"], row["Role"], "Reject", "Candidate rejected")
                        )
                        st.toast(f"{row['Candidate']} rejected.")
            
            with st.expander(f"AI Summary for {row['Candidate']}"):
                prompt = f"""
You are an expert technical recruiter. Briefly explain why {row['Candidate']} is a good fit for the {row['Role']} role.
Context:
- Skills: {row['Skills']}
- Experience: {row['Experience']} years
- Match Score: {row['Match']}%
Return ONLY a concise 2-sentence summary.
"""
                if st.button("Generate Summary", key=f"gen-summary-{i}-{row['Candidate']}"):
                    with st.spinner("Generating AI summary..."):
                        summary = call_llama(prompt)
                    st.write(summary)

        # Score breakdown chart
        if not ranked.empty:
            st.subheader("Score comparison")
            
            # Ensure Skills Match column exists for the chart even if it's somehow missing
            if "Skills Match" not in ranked.columns:
                ranked["Skills Match"] = 0
                
            chart_data = ranked.rename(columns={"Match": "ATS Score", "Skills Match": "Skill Match"}).set_index("Candidate")[["ATS Score", "Skill Match"]].head(8)
            st.bar_chart(chart_data, height=260)

    # ── Tab 2: Candidate Comparison ─────────────────────────────────────────
    with tab_compare:
        st.subheader("⚖️ Compare Candidates Side-by-Side")
        st.caption("Select 2 or 3 candidates to see a detailed AI-powered comparison.")

        all_names = filtered["Candidate"].tolist()
        if len(all_names) < 2:
            st.info("Filter must return at least 2 candidates to compare.")
        else:
            default_picks = all_names[:min(3, len(all_names))]
            selected_compare = st.multiselect(
                "Select candidates to compare",
                all_names,
                default=default_picks,
                max_selections=3,
                key="compare-select",
            )

            if len(selected_compare) >= 2:
                compare_df = filtered[filtered["Candidate"].isin(selected_compare)].set_index("Candidate")

                # Build comparison table
                attrs = ["Role", "Location", "Experience", "Match", "Stage", "Availability", "Salary Fit", "Risk", "Skills", "Education", "Certifications"]
                header = "<tr><th>Attribute</th>" + "".join(f"<th>{c}</th>" for c in selected_compare) + "</tr>"
                table_rows = ""
                for attr in attrs:
                    row_html = f"<tr><td><strong>{attr}</strong></td>"
                    for c in selected_compare:
                        val = compare_df.loc[c, attr] if attr in compare_df.columns else "–"
                        row_html += f"<td>{val}</td>"
                    row_html += "</tr>"
                    table_rows += row_html

                st.markdown(
                    f"<div style='overflow-x:auto'><table class='compare-table'><thead>{header}</thead><tbody>{table_rows}</tbody></table></div>",
                    unsafe_allow_html=True,
                )

                # AI Verdict
                st.subheader("🤖 AI Comparison Verdict")
                top = compare_df["Match"].idxmax()
                top_row = compare_df.loc[top]
                gap = int(compare_df["Match"].max() - compare_df["Match"].min())

                verdict_lines = [
                    f"<strong>{top}</strong> leads with the highest match score of {compare_df.loc[top, 'Match']}% and {top_row['Experience']} years of experience.",
                    f"The gap between highest and lowest match in this selection is <strong>{gap} points</strong>.",
                ]
                if compare_df.loc[top, "Risk"] == "Low":
                    verdict_lines.append(f"{top} is also the lowest risk candidate — making them the strongest overall recommendation.")
                if compare_df.loc[top, "Availability"] in ["Immediate", "15 days"]:
                    verdict_lines.append(f"{top} can join quickly ({top_row['Availability']}), which reduces time-to-productivity.")

                verdict_html = "<br>".join(verdict_lines)
                st.markdown(
                    f"<div class='verdict-card recommend'><div class='verdict-title'>✅ Recommended: {top}</div><div class='verdict-body'>{verdict_html}</div></div>",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: INTERVIEWS (enhanced with Hiring Recommendation)
# ─────────────────────────────────────────────────────────────────────────────

def build_hiring_recommendation(row) -> tuple[str, str, str]:
    score = row["Match"]
    risk = row.get("Risk", "Medium") if isinstance(row, dict) else row["Risk"]
    sal = row.get("Salary Fit", "Aligned") if isinstance(row, dict) else row["Salary Fit"]
    avail = str(row.get("Availability", "TBD") if isinstance(row, dict) else row["Availability"])
    name = row.get("Candidate", "This candidate") if isinstance(row, dict) else row.get("Candidate", "This candidate")

    prompt = f"""
You are a senior recruitment manager.
Write a 2-sentence hiring recommendation for {name}.
Context:
- Match score: {score}%
- Retention risk: {risk}
- Salary expectations: {sal}
- Availability: {avail}

Be decisive. If score >= 85 and risk is Low, recommend strongly. If score < 80, advise waiting or rejecting.
Return ONLY the reasoning text. No JSON, no markdown.
"""
    reason = call_llama(prompt)

    if score >= 90 and risk == "Low" and sal == "Aligned":
        verdict = "\u2705 Strongly Recommend"
        css = "recommend"
    elif score >= 85 and risk in ["Low", "Medium"]:
        verdict = "\U0001f44d Recommend"
        css = "recommend"
    elif score >= 80:
        verdict = "\u23f3 Waitlist"
        css = "waitlist"
    else:
        verdict = "\u274c Do Not Proceed"
        css = "decline"

    return verdict, css, reason



import smtplib
from email.message import EmailMessage


def send_interview_email(sender_email: str, sender_password: str, candidate_name: str, candidate_email: str, date_str: str, time_str: str, meet_link: str) -> tuple[bool, str]:
    if not sender_email or not sender_password or not candidate_email:
        return False, "Missing credentials or candidate email"
    try:
        msg = EmailMessage()
        msg.set_content(f"Hi {candidate_name},\n\nYour interview is scheduled for {date_str} at {time_str}.\n\nPlease join using this Google Meet link: {meet_link}\n\nBest regards,\nInfosys Recruitment Team")
        msg["Subject"] = f"Interview Scheduled: {candidate_name} - Infosys"
        msg["From"] = sender_email
        msg["To"] = candidate_email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Success"
    except Exception as e:
        print(f"Error sending email: {e}")
        return False, str(e)

@st.fragment
def render_interview_desk(candidates: pd.DataFrame, roles: pd.DataFrame = None) -> None:
    st.title("Interviews")
    st.caption("Plan interviews, prepare questions, get AI hiring recommendations, and collect feedback.")

    # Load roles if not passed
    if roles is None:
        roles = load_roles()

    interview_candidates = candidates[candidates["Stage"].str.contains("interview|manager|customer", case=False, regex=True)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Interviews to plan", len(interview_candidates), "5 in the next 2 days")
    c2.metric("Average skill match", f"{interview_candidates['Match'].mean():.1f}%", "Strong candidates")
    c3.metric("Feedback still needed", 7, "2 completed today")

    tab_desk, tab_pipeline, tab_ai = st.tabs(["📋 Interview Desk", "🔄 Interview Pipeline", "🧠 AI Interview Generator"])

    # ── TAB 1: Interview Desk (existing content) ───────────────────────
    with tab_desk:
        today = date.today()
        if "interview_schedule" not in st.session_state:
            st.session_state["interview_schedule"] = [
                {"Date": today + timedelta(days=1), "Time": "10:00", "Candidate": "Aarav Mehta", "Interview topic": "AI Architecture", "Mode": "Google Meet", "Status": "Confirmed", "Meet Link": "https://meet.google.com/new"},
                {"Date": today + timedelta(days=1), "Time": "14:30", "Candidate": "Rohan Iyer", "Interview topic": "Cloud Security", "Mode": "Google Meet", "Status": "Needs evaluator", "Meet Link": "https://meet.google.com/new"},
            ]
            
        schedule = pd.DataFrame(st.session_state["interview_schedule"])

        st.subheader("Upcoming interviews")
        col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2, 1.5, 3, 2, 2.5])
        col_h1.write("**Date**")
        col_h2.write("**Time**")
        col_h3.write("**Candidate**")
        col_h4.write("**Stage**")
        col_h5.write("**Action**")
        
        for i, row in schedule.iterrows():
            cand_name = row["Candidate"]
            matched = candidates[candidates["Candidate"] == cand_name]
            cand_stage = matched.iloc[0]["Stage"] if not matched.empty else "Unknown"
            cand_id = matched.iloc[0]["ID"] if not matched.empty else None
            meet_link = row.get("Meet Link", "https://meet.google.com/new")

            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 3, 2, 2.5])
            c1.write(row["Date"])
            c2.write(row["Time"])
            c3.write(cand_name)
            c4.write(cand_stage)
            with c5:
                bc1, bc2, bc3, bc4 = st.columns(4)
                with bc1:
                    st.markdown(f'<a href="{meet_link}" target="_blank" style="text-decoration:none;"><button style="background:none;border:none;cursor:pointer;font-size:1rem;" title="Start Interview">▶️</button></a>', unsafe_allow_html=True)
                with bc2:
                    if st.button("➡️", key=f"next_int_{i}_{cand_name}", help="Send to Next Round"):
                        if cand_id:
                            import re
                            current_stage = cand_stage
                            next_stage = "Interview Round 2"
                            match = re.search(r"Round (\d+)", current_stage, re.IGNORECASE)
                            if match:
                                next_round = int(match.group(1)) + 1
                                next_stage = f"Interview Round {next_round}"
                            elif "Interview" not in current_stage:
                                next_stage = "Interview Round 1"
                            
                            res = api_put(f"/api/candidates/{cand_id}", {"stage": next_stage})
                            if res:
                                st.toast(f"Candidate {cand_name} advanced to {next_stage}.")
                                import time as sys_time
                                sys_time.sleep(0.5)
                                st.rerun()
                with bc3:
                    if st.button("❌", key=f"rej_int_{i}_{cand_name}", help="Reject Candidate"):
                        if cand_id:
                            res = api_put(f"/api/candidates/{cand_id}", {"stage": "Rejected"})
                            if res:
                                st.toast(f"Candidate {cand_name} has been rejected.")
                                import time as sys_time
                                sys_time.sleep(0.5)
                                st.rerun()
                with bc4:
                    if st.button("🗑️", key=f"del_int_{i}_{cand_name}", help="Remove Interview"):
                        st.session_state["interview_schedule"].pop(i)
                        st.rerun()

        st.divider()
        candidate_name = st.selectbox(
            "Candidate to interview",
            interview_candidates["Candidate"].tolist(),
            key="interview-candidate",
        )
        
        if not candidate_name:
            st.info("No candidates currently in the interview stage to schedule or evaluate.")
        else:
            selected = candidates[candidates["Candidate"] == candidate_name].iloc[0]


            st.subheader("Interview scorecard")
            competencies = [
                "Problem framing",
                "Hands-on technical depth",
                "Delivery ownership",
                "Client communication",
                "Learning agility",
            ]
            rubric = pd.DataFrame(
                {
                    "What to check": competencies,
                    "Importance": ["Medium", "High", "Medium", "Medium", "Medium"],
                    "Question guide": [
                        f"Map to {selected['Role']} delivery scenarios",
                        selected["Skills"],
                        "Past program scope and accountability",
                        "Stakeholder examples and crisp tradeoffs",
                        "Recent learning, certifications, and applied practice",
                    ],
                }
            )
            st.dataframe(rubric, use_container_width=True, hide_index=True)

            # ── AI Interview Question Generator ─────────────────────────────────────
            st.subheader("🤖 AI Interview Question Generator")
            st.caption("Create role-specific, difficulty-calibrated questions for the interviewer.")

            col_a, col_b, col_c = st.columns(3)
            with col_a:
                question_focus = st.selectbox(
                    "Question focus",
                    ["Technical skills", "Problem solving", "Communication", "Leadership", "Situational / Behavioural"],
                    key="q-focus",
                )
            with col_b:
                difficulty = st.select_slider(
                    "Difficulty",
                    options=["Basic", "Intermediate", "Advanced", "Expert"],
                    value="Intermediate",
                    key="q-diff",
                )
            with col_c:
                question_count = st.slider("Number of questions", 3, 8, 5, key="q-count")

            if st.button("✨ Generate Interview Questions", key="generate-interview-questions", use_container_width=True):
                role = selected["Role"]
                exp = selected["Experience"]

                prompt = f"""
You are an expert technical interviewer hiring a {role} with {exp} years of experience.
Generate a list of {question_count} interview questions for the candidate.
Context:
- Candidate Skills: {selected['Skills']}
- Question Focus Area: {question_focus}
- Difficulty Level: {difficulty}

Output ONLY the questions as a numbered markdown list. Do not include introductory text.
"""
                with st.spinner(f"Llama 3.2 is generating {question_count} {difficulty.lower()} questions..."):
                    questions_text = call_llama(prompt)
                    
                st.success(f"Generated {question_count} {difficulty.lower()}-level questions focusing on {question_focus}.")
                st.markdown(questions_text)

            st.divider()
            st.subheader("Schedule an interview")
            st.caption(f"Plan the next interview for {candidate_name} via Google Meet.")
            
            if not st.session_state.get("google_linked"):
                st.warning("⚠️ Google Workspace is not linked. Emails will not be sent automatically. Please link your account in Settings > Integrations.")

            with st.form("schedule-interview-form"):
                interview_date = st.date_input("Date", value=date.today() + timedelta(days=1), min_value=date.today())
                interview_time = st.time_input("Time", value=time(10, 0))
                interviewer = st.text_input("Interviewer name", placeholder="Enter interviewer name")
                candidate_email = st.text_input("Candidate Email Address", placeholder="e.g. candidate@example.com")
                scheduled = st.form_submit_button("Schedule interview", type="primary", use_container_width=True)

            if scheduled:
                interviewer_name = interviewer or "the selected interviewer"
                meet_link = "https://meet.google.com/new"
                
                st.session_state.setdefault("interview_schedule", []).append({
                    "Date": interview_date,
                    "Time": interview_time.strftime("%H:%M"),
                    "Candidate": candidate_name,
                    "Interview topic": "General Interview", 
                    "Mode": "Google Meet",
                    "Status": "Scheduled",
                    "Meet Link": meet_link
                })
                
                st.success(
                    f"Interview scheduled for {candidate_name} with {interviewer_name} "
                    f"on {interview_date:%d %b} at {interview_time:%H:%M} via Google Meet."
                )
                
                if st.session_state.get("google_linked") and candidate_email:
                    sender_email = st.session_state.get("saved_email")
                    sender_password = st.session_state.get("saved_pass")
                    
                    with st.spinner("Sending email to candidate..."):
                        email_sent, err_msg = send_interview_email(
                            sender_email, 
                            sender_password, 
                            candidate_name, 
                            candidate_email, 
                            interview_date.strftime("%d %b %Y"), 
                            interview_time.strftime("%H:%M"), 
                            meet_link
                        )
                        
                        if email_sent:
                            st.toast("✅ Automated email sent to candidate successfully.")
                        else:
                            st.error(f"Failed to send automated email. Error: {err_msg}. Check your SMTP credentials in Settings.")

    # ── TAB 2: Interview Pipeline ──────────────────────────────────────
    with tab_pipeline:
        st.subheader("Candidate Interview Pipeline")
        st.caption("Track every candidate's position in the hiring pipeline at a glance.")

        # ── Filtering section ──────────────────────────────────────────
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            all_roles_list = ["All Roles"] + sorted(candidates["Role"].unique().tolist())
            pipe_role_filter = st.selectbox("Filter by Role", all_roles_list, key="pipe-role-filter")
        with fc2:
            match_threshold = st.slider("Min Match %", 0, 100, 0, key="pipe-match-filter")
        with fc3:
            stage_options = ["All Stages", "Screening", "Technical interview", "Manager interview",
                             "HR interview", "Offer discussion", "Hired", "Rejected"]
            pipe_stage_filter = st.selectbox("Filter by Stage", stage_options, key="pipe-stage-filter")

        # Apply filters
        pipe_cands = candidates.copy()
        if pipe_role_filter != "All Roles":
            pipe_cands = pipe_cands[pipe_cands["Role"] == pipe_role_filter]
        if match_threshold > 0:
            pipe_cands = pipe_cands[pipe_cands["Match"] >= match_threshold]
        if pipe_stage_filter != "All Stages":
            pipe_cands = pipe_cands[pipe_cands["Stage"].str.contains(pipe_stage_filter, case=False, regex=False)]

        if pipe_cands.empty:
            st.info("No candidates match the selected filters.")
        else:
            # ── Pipeline stage definitions ─────────────────────────────
            pipeline_stages = [
                ("Screening", "#6366f1", "🔍"),
                ("Technical interview", "#0f8b8d", "💻"),
                ("Manager interview", "#db2777", "👔"),
                ("HR interview", "#e76f51", "🤝"),
                ("Offer discussion", "#e9c46a", "📝"),
                ("Hired", "#264653", "✅"),
            ]

            # Classify candidates into stages
            def classify_stage(stage_str):
                s = str(stage_str).lower()
                if "hired" in s or "onboarded" in s:
                    return "Hired"
                elif "offer" in s:
                    return "Offer discussion"
                elif "hr" in s or "customer" in s:
                    return "HR interview"
                elif "manager" in s:
                    return "Manager interview"
                elif "technical" in s or "interview round" in s:
                    return "Technical interview"
                else:
                    return "Screening"

            pipe_cands = pipe_cands.copy()
            pipe_cands["Pipeline Stage"] = pipe_cands["Stage"].apply(classify_stage)

            # ── Summary KPI strip ──────────────────────────────────────
            stage_counts = {s: 0 for s, _, _ in pipeline_stages}
            for _, row in pipe_cands.iterrows():
                ps = row["Pipeline Stage"]
                if ps in stage_counts:
                    stage_counts[ps] += 1

            total_in_pipeline = len(pipe_cands)
            in_interview = sum(stage_counts[s] for s in ["Technical interview", "Manager interview", "HR interview"])
            in_offer = stage_counts.get("Offer discussion", 0)
            avg_match = round(pipe_cands["Match"].mean(), 1) if not pipe_cands.empty else 0

            kpi_html = (
                '<div class="pipeline-summary-strip">'
                f'<div class="pipeline-summary-item">'
                f'<div class="ps-num" style="color:#6366f1;">{total_in_pipeline}</div>'
                f'<div class="ps-label">Total Candidates</div></div>'
                f'<div class="pipeline-summary-item">'
                f'<div class="ps-num" style="color:#0f8b8d;">{in_interview}</div>'
                f'<div class="ps-label">In Interviews</div></div>'
                f'<div class="pipeline-summary-item">'
                f'<div class="ps-num" style="color:#e9c46a;">{in_offer}</div>'
                f'<div class="ps-label">Offer Stage</div></div>'
                f'<div class="pipeline-summary-item">'
                f'<div class="ps-num" style="color:#264653;">{avg_match}%</div>'
                f'<div class="ps-label">Avg Match Score</div></div>'
                '</div>'
            )
            st.markdown(kpi_html, unsafe_allow_html=True)

            # ── Visual funnel of candidates per stage ──────────────────
            max_count = max(stage_counts.values()) or 1
            funnel_html = '<div class="pipeline-funnel">'
            for idx, (stage_name, color, emoji) in enumerate(pipeline_stages):
                count = stage_counts[stage_name]
                bar_h = max(24, int(count / max_count * 150))
                funnel_html += (
                    f'<div class="funnel-step">'
                    f'<div class="funnel-bar" style="height:{bar_h}px;background:{color};"></div>'
                    f'<div class="funnel-count">{count}</div>'
                    f'<div class="funnel-label">{emoji} {stage_name.split()[0]}</div>'
                    f'</div>'
                )
                if idx < len(pipeline_stages) - 1:
                    funnel_html += '<div class="funnel-arrow">→</div>'
            funnel_html += '</div>'
            st.markdown(funnel_html, unsafe_allow_html=True)

            st.divider()

            # ── Kanban-style pipeline columns ──────────────────────────
            st.subheader("Candidates by Stage")

            # Create columns for each stage that has candidates
            active_stages = [(s, c, e) for s, c, e in pipeline_stages if stage_counts[s] > 0]

            if not active_stages:
                st.info("No candidates in the pipeline for the current filters.")
            else:
                cols = st.columns(len(active_stages))
                for col_idx, (stage_name, color, emoji) in enumerate(active_stages):
                    with cols[col_idx]:
                        count = stage_counts[stage_name]
                        # Stage header
                        header_html = (
                            f'<div style="text-align:center;padding:.6rem .4rem;border-radius:8px 8px 0 0;'
                            f'background:{color};color:#fff;margin-bottom:.5rem;">'
                            f'<div style="font-size:1.1rem;font-weight:800;">{emoji} {count}</div>'
                            f'<div style="font-size:.68rem;font-weight:600;text-transform:uppercase;'
                            f'letter-spacing:.04em;opacity:.9;">{stage_name}</div>'
                            f'</div>'
                        )
                        st.markdown(header_html, unsafe_allow_html=True)

                        # Candidate cards in this stage
                        stage_cands = pipe_cands[pipe_cands["Pipeline Stage"] == stage_name].sort_values("Match", ascending=False)
                        for _, cand in stage_cands.iterrows():
                            initials = "".join(w[0] for w in str(cand["Candidate"]).split()[:2]).upper()
                            match_val = int(cand["Match"])
                            if match_val >= 90:
                                match_color = "#11665c"
                                match_bg = "rgba(42,157,143,.12)"
                            elif match_val >= 80:
                                match_color = "#92400e"
                                match_bg = "rgba(233,196,106,.15)"
                            else:
                                match_color = "#9f1239"
                                match_bg = "rgba(231,111,81,.12)"

                            risk_val = str(cand.get("Risk", ""))
                            risk_dot = "🟢" if risk_val == "Low" else "🟡" if risk_val == "Medium" else "🔴" if risk_val == "High" else ""

                            card_html = (
                                f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;'
                                f'padding:.65rem .7rem;margin-bottom:.45rem;'
                                f'box-shadow:0 2px 8px rgba(15,23,42,.04);'
                                f'border-left:3px solid {color};">'
                                f'<div style="display:flex;align-items:center;gap:.45rem;margin-bottom:.35rem;">'
                                f'<div style="width:28px;height:28px;border-radius:50%;background:{color};'
                                f'color:#fff;display:flex;align-items:center;justify-content:center;'
                                f'font-size:.65rem;font-weight:800;flex-shrink:0;">{initials}</div>'
                                f'<div style="flex:1;min-width:0;">'
                                f'<div style="font-size:.78rem;font-weight:700;color:#0f172a;'
                                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{cand["Candidate"]}</div>'
                                f'<div style="font-size:.62rem;color:#64748b;">{cand["Role"]}</div>'
                                f'</div></div>'
                                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                                f'margin-top:.25rem;">'
                                f'<span style="font-size:.62rem;color:#64748b;">{cand.get("Availability", "")}</span>'
                                f'<div style="display:flex;align-items:center;gap:.3rem;">'
                                f'<span style="font-size:.6rem;">{risk_dot}</span>'
                                f'<span style="font-size:.68rem;font-weight:700;padding:.1rem .35rem;'
                                f'border-radius:10px;background:{match_bg};color:{match_color};">{match_val}%</span>'
                                f'</div></div>'
                                f'<div style="font-size:.58rem;color:#94a3b8;margin-top:.2rem;'
                                f'font-style:italic;">{cand["Stage"]}</div>'
                                f'</div>'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

            st.divider()

            # ── Detailed candidate table ───────────────────────────────
            st.subheader("📋 Pipeline Detail View")
            display_cols = ["Candidate", "Role", "Stage", "Match", "Availability", "Risk", "Salary Fit", "Source"]
            available_cols = [c for c in display_cols if c in pipe_cands.columns]
            detail_df = pipe_cands[available_cols].sort_values("Match", ascending=False).reset_index(drop=True)
            st.dataframe(detail_df, use_container_width=True, hide_index=True)


    # ── TAB 3: AI Interview Generator ──────────────────────────────────
    with tab_ai:
        st.subheader("🧠 Generate AI Interview Assessment")
        st.caption("Generate a tailored test for a candidate and share the link. The AI will score their answers.")

        if interview_candidates.empty:
            st.info("No candidates currently in the interview stage to generate tests for.")
        else:
            with st.form("ai-interview-generator-form"):
                st.write("**Configure Test**")
                
                candidate_list = interview_candidates["Candidate"].tolist()
                selected_cand_name = st.selectbox("Select Candidate", candidate_list)
                
                f_col1, f_col2, f_col3 = st.columns(3)
                with f_col1:
                    q_count = st.slider("Number of Questions", min_value=3, max_value=10, value=5)
                with f_col2:
                    q_diff = st.selectbox("Difficulty", ["Basic", "Intermediate", "Advanced", "Expert"])
                with f_col3:
                    q_focus = st.selectbox("Focus Area", ["Technical Skills", "Behavioral", "Problem Solving", "Mixed"])
                
                generate_btn = st.form_submit_button("🚀 Generate AI Interview", type="primary", use_container_width=True)

            if generate_btn:
                selected = candidates[candidates["Candidate"] == selected_cand_name].iloc[0]
                cand_id = selected["ID"]
                
                role_name = selected["Role"]
                matched_role = roles[roles["Role"] == role_name]
                if not matched_role.empty:
                    role_id = matched_role.iloc[0]["ID"]
                    
                    payload = {
                        "candidate_id": int(cand_id),
                        "role_id": int(role_id),
                        "num_questions": q_count,
                        "difficulty": q_diff,
                        "focus_area": q_focus
                    }
                    
                    with st.spinner(f"Generating tailored AI test for {selected_cand_name}..."):
                        res = api_post("/api/ai-interview/generate", payload)
                        
                        if res and "token" in res:
                            st.success(f"✅ AI Interview successfully generated for {selected_cand_name}!")
                            
                            st.markdown("### 🔗 Candidate Test Link")
                            st.info("Share this link with the candidate. They will not need an account to take the test.")
                            
                            # Build absolute URL from current origin
                            # (Since Streamlit doesn't easily expose the full absolute base URL in the frontend script,
                            # we give the relative query path. For a real deployed app, it would use the site domain.)
                            test_link_full = f"http://localhost:8501/?page=ai_test&token={res['token']}"
                            
                            st.code(test_link_full, language="text")
                        else:
                            st.error("Failed to generate AI interview.")
                else:
                    st.error(f"Could not find matching Role ID for '{role_name}'.")

        st.divider()
        st.subheader("Generated AI Interviews")
        
        interviews_data = api_get("/api/ai-interview/list")
        if not interviews_data:
            st.info("No AI interviews generated yet.")
        else:
            int_df = pd.DataFrame(interviews_data)
            
            # Reorder/rename columns for display
            display_df = int_df[["id", "candidate_name", "role_name", "difficulty", "focus_area", "status"]].copy()
            display_df.columns = ["ID", "Candidate", "Role", "Difficulty", "Focus", "Status"]
            
            # Table visualization
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Report Viewer
            completed = int_df[int_df["status"] == "completed"]
            if not completed.empty:
                st.write("**View AI Interview Reports**")
                report_options = {row["id"]: f"{row['candidate_name']} ({row['role_name']})" for _, row in completed.iterrows()}
                selected_report_id = st.selectbox("Select completed test to view report:", options=list(report_options.keys()), format_func=lambda x: report_options[x])
                
                if st.button("📊 Load Report", type="primary"):
                    report_data = api_get(f"/api/ai-interview/report/{selected_report_id}")
                    if report_data:
                        st.markdown(f"### AI Analysis Report: {report_data['candidate_name']}")
                        rep = report_data.get("report", {})
                        
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            score = rep.get("overall_score", 0)
                            st.metric("Overall AI Score", f"{score}%")
                        with rc2:
                            st.metric("Recommendation", rep.get("recommendation", "N/A"))
                            
                        st.markdown("**Strengths:**")
                        for s in rep.get("strengths", []):
                            st.markdown(f"- ✅ {s}")
                            
                        st.markdown("**Areas for Improvement:**")
                        for w in rep.get("weaknesses", []):
                            st.markdown(f"- ⚠️ {w}")
                            
                        st.divider()
                        st.markdown("#### Question Breakdown")
                        
                        evals = rep.get("evaluations", [])
                        q_list = report_data.get("questions", [])
                        a_list = report_data.get("answers", [])
                        
                        for i, ev in enumerate(evals):
                            q_text = ev.get("question", q_list[i] if i < len(q_list) else f"Question {i+1}")
                            a_text = a_list[i] if i < len(a_list) else "No answer provided"
                            score = ev.get("score", 0)
                            feedback = ev.get("feedback", "No feedback")
                            
                            with st.expander(f"Q{i+1}: Score {score}/10"):
                                st.markdown(f"**Question:** {q_text}")
                                st.markdown("**Candidate Answer:**")
                                st.info(a_text)
                                st.markdown("**AI Feedback:**")
                                st.success(feedback)
                    else:
                        st.error("Could not load report.")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: JD ANALYSER (NEW)
# ─────────────────────────────────────────────────────────────────────────────


def analyse_jd(jd_text: str) -> dict:
    prompt = f"""
You are an expert technical recruiter analyzing a job description. 
Extract the following details from the job description text below and return ONLY a valid JSON object. Do not include markdown formatting or extra text outside the JSON.

Expected JSON schema:
{{
  "skills": ["skill1", "skill2"],
  "seniority": "Junior | Mid-level | Senior | Principal / Staff | Any level",
  "exp_years": 5, // minimum years of experience required (integer)
  "flags": ["list", "of", "concerning", "phrases", "or", "red", "flags"],
  "salary": "estimated salary range string (e.g. '₹18L – ₹35L')",
  "tone_score": 85, // integer 0-100 based on inclusivity and clarity
  "rewrite": "A well-written, inclusive, and professional rewrite of the job description in markdown format."
}}

Job Description Text:
{jd_text}
"""
    response = call_llama(prompt, expect_json=True)
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        data = {
            "skills": ["Parse Error"],
            "seniority": "Unknown",
            "exp_years": 0,
            "flags": ["Could not parse LLM output"],
            "salary": "Unknown",
            "tone_score": 50,
            "rewrite": "Error analyzing JD with AI."
        }
    
    data["word_count"] = len(jd_text.split())
    
    seniority = data.get("seniority", "Any level")
    if seniority == "Principal / Staff":
        data["level_color"] = "#7c3aed"
    elif seniority == "Senior":
        data["level_color"] = "#2563eb"
    elif seniority == "Mid-level":
        data["level_color"] = "#0f8b8d"
    elif seniority == "Junior":
        data["level_color"] = "#2a9d8f"
    else:
        data["level_color"] = "#64748b"
        
    return {
        "skills": data.get("skills", []),
        "seniority": seniority,
        "level_color": data.get("level_color", "#64748b"),
        "exp_years": data.get("exp_years", 0),
        "flags": data.get("flags", []),
        "salary": data.get("salary", "Unknown"),
        "word_count": data.get("word_count", len(jd_text.split())),
        "tone_score": data.get("tone_score", 50),
        "rewrite": data.get("rewrite", "N/A"),
    }


_SKILL_KEYWORDS = ["Python", "Java", "C++", "JavaScript", "React", "Node.js", "SQL", "AWS", "Azure", "GCP", "Machine Learning", "AI", "Docker", "Kubernetes", "DevOps", "Agile", "Scrum", "Data Science", "Tableau", "PowerBI", "Communication", "Leadership"]

def parse_resume_text(text: str) -> dict:
    """Extract skills, experience and info from raw resume text."""
    text_lower = text.lower()
    found_skills = [s for s in _SKILL_KEYWORDS if s.lower() in text_lower]

    # Experience — ASCII-only guard prevents Unicode superscripts (², ³, etc.) from crashing int()
    exp_years = 0
    for part in text.split():
        p = part.strip(".,+'\"")
        if p.isascii() and p.isdigit():
            v = int(p)
            if 1 <= v <= 25:
                exp_years = max(exp_years, v)

    # Education keywords
    edu_map = {"phd": "PhD", "m.tech": "M.Tech", "mtech": "M.Tech", "m.s.": "M.S.",
                "mba": "MBA", "b.tech": "B.Tech", "btech": "B.Tech", "b.e.": "B.E.", "be ": "B.E."}
    detected_edu = "Not specified"
    for key, val in edu_map.items():
        if key in text_lower:
            detected_edu = val
            break

    # Certifications
    cert_keywords = ["aws", "azure", "gcp", "google", "cisco", "pmp", "cissp", "istqb", "safe", "scrum", "ceh"]
    certs = [c.upper() for c in cert_keywords if c in text_lower]

    return {
        "skills": found_skills,
        "exp_years": exp_years,
        "education": detected_edu,
        "certifications": certs,
    }


def score_resume_vs_role(
    resume: dict,
    role_row: "pd.Series",
    required_skills_override: list[str] | None = None,
) -> dict:
    required = required_skills_override if required_skills_override else [s.strip() for s in role_row["Required Skills"].split(",")]
    
    # Use Llama to extract matched and missing skills intelligently rather than just substring matching
    prompt = f"""
You are an expert technical recruiter matching a candidate's resume to a job role.
The job requires the following skills: {required}
The candidate has the following skills: {resume.get('skills', [])}

Return a JSON object containing two lists:
1. "matched_skills": A list of required skills the candidate clearly possesses (or close equivalents).
2. "missing_skills": A list of required skills the candidate is missing.

JSON Format:
{{
  "matched_skills": ["skillA", "skillB"],
  "missing_skills": ["skillC"]
}}
"""
    response = call_llama(prompt, expect_json=True)
    try:
        data = json.loads(response)
        matched = data.get("matched_skills", [])
        missing = data.get("missing_skills", required)
    except:
        matched = [s for s in required if any(s.lower() in rs.lower() for rs in resume["skills"])]
        missing = [s for s in required if s not in matched]

    coverage = round(len(matched) / max(len(required), 1) * 100)

    exp_ok = resume["exp_years"] >= role_row["Experience Min"]
    exp_bonus = 10 if resume["exp_years"] >= role_row["Experience Min"] + 3 else (5 if exp_ok else -10)
    base = coverage
    match_score = max(0, min(100, base + exp_bonus))

    if match_score >= 85:
        verdict = "Excellent fit"
        v_class = "recommend"
    elif match_score >= 70:
        verdict = "Good fit — minor gaps"
        v_class = "recommend"
    elif match_score >= 55:
        verdict = "Possible fit — train on gaps"
        v_class = "waitlist"
    else:
        verdict = "Significant gaps"
        v_class = "decline"

    return {
        "match_score": match_score,
        "coverage": coverage,
        "matched_skills": matched,
        "missing_skills": missing,
        "exp_ok": exp_ok,
        "verdict": verdict,
        "v_class": v_class,
    }


def build_resume_chat_reply(prompt: str, candidate: "pd.Series") -> str:
    system = f"""You are the AI-Driven Smart Hiring Platform Copilot. 
You are discussing a candidate profile with a recruiter. Keep answers concise, professional, and helpful.

Candidate Details:
Name: {candidate.get('Candidate', 'Unknown')}
Role Applied: {candidate.get('Role', 'Unknown')}
Skills: {candidate.get('Skills', 'Unknown')}
Experience: {candidate.get('Experience', 0)} years
Match Score: {candidate.get('Match', 0)}%
Current Stage: {candidate.get('Stage', 'Unknown')}
Availability: {candidate.get('Availability', 'Unknown')}
Salary Fit: {candidate.get('Salary Fit', 'Unknown')}
Risk Profile: {candidate.get('Risk', 'Unknown')}
Education: {candidate.get('Education', 'Not specified')}
Certifications: {candidate.get('Certifications', 'None listed')}
Summary: {candidate.get('Summary', '')}
"""
    return call_llama(prompt, system=system)


@st.fragment
def render_jd_analyser(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    st.title("📋 JD Analyser & Creator")
    st.caption("Analyse existing Job Descriptions or use AI to create and publish new ones.")
    
    tab_analyse, tab_create, tab_stats = st.tabs(["🔍 Analyse JD", "✨ Create & Publish JD", "📈 JD Performance & Stats"])
    
    with tab_analyse:
        st.subheader("Input Job Description")
        jd_input = ""
        uploaded_file = st.file_uploader("Upload JD (TXT or PDF)", type=["txt", "pdf"], key="jd-upload")
        if uploaded_file is not None:
            if uploaded_file.type == "text/plain":
                jd_input = uploaded_file.read().decode("utf-8", errors="ignore")
            else:
                jd_input = uploaded_file.read().decode("latin-1", errors="ignore")
                jd_input = "".join(c for c in jd_input if c.isprintable() or c in "\n\r\t")
            st.success("File uploaded successfully!")
        
        if st.button("✨ Run AI Analysis", type="primary", use_container_width=True):
            if not jd_input.strip():
                st.warning("Please paste a job description first.")
            else:
                with st.spinner("Llama 3.2 is analysing the Job Description..."):
                    analysis = analyse_jd(jd_input)
                    st.session_state["last_analysis"] = analysis
        
        analysis = st.session_state.get("last_analysis")
        if analysis:
            st.subheader("Analysis Results")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Required Skills:**")
                st.write(", ".join(analysis.get('skills', [])))
                st.markdown("**Minimum Experience:**")
                st.write(f"{analysis.get('experience', 'N/A')} years")
            with col2:
                st.markdown("**Seniority Level:**")
                st.write(analysis.get('seniority', 'N/A'))
                st.markdown("**Bias/Inclusivity Flags:**")
                if analysis.get('red_flags'):
                    for flag in analysis['red_flags']:
                        st.markdown(f"- 🚩 {flag}")
                else:
                    st.success("No red flags detected.")
            
            st.divider()
            st.subheader("AI Rewritten JD Suggestion")
            st.markdown(analysis.get('rewritten_jd', 'No suggestion provided.'))
            
            st.divider()
            st.subheader("Publish this JD")
            st.caption("Fill in the remaining details to post this analyzed JD for candidates.")
            with st.form("publish_analysed_jd_form"):
                ca1, ca2 = st.columns(2)
                with ca1:
                    a_req = st.text_input("Requisition ID*", placeholder="e.g. REQ-2026", key="a_req")
                    a_title = st.text_input("Role Title*", key="a_title")
                    a_bu = st.text_input("Business Unit*", placeholder="e.g. Engineering", key="a_bu")
                    a_loc = st.text_input("Location*", placeholder="e.g. Remote, NY", key="a_loc")
                    a_target = st.number_input("Target Days*", min_value=1, value=30, key="a_target")
                with ca2:
                    a_openings = st.number_input("Openings*", min_value=1, value=1, key="a_open")
                    
                    try:
                        exp_val = int(analysis.get("experience", 0))
                    except:
                        exp_val = 0
                        
                    a_exp = st.number_input("Minimum Experience (Years)*", min_value=0, value=exp_val, key="a_exp")
                    a_salary = st.text_input("Salary Band*", key="a_sal")
                    a_skills = st.text_input("Required Skills*", value=", ".join(analysis.get("skills", [])), key="a_skills")
                    a_priority = st.selectbox("Priority", ["Medium", "High", "Critical"], key="a_prio")
                    a_risk = st.selectbox("Risk", ["Low", "Medium", "High"], key="a_risk")
                
                a_submit = st.form_submit_button("🚀 Publish Analyzed Job", type="primary", use_container_width=True)
                if a_submit:
                    if not a_req or not a_title or not a_bu or not a_loc or not a_salary or not a_skills:
                        st.error("Please fill all required fields.")
                    else:
                        payload = {
                            "req_id": a_req,
                            "role": a_title,
                            "business_unit": a_bu,
                            "location": a_loc,
                            "openings": a_openings,
                            "required_skills": a_skills,
                            "experience_min": a_exp,
                            "salary_band": a_salary,
                            "target_days": a_target,
                            "priority": a_priority,
                            "risk": a_risk
                        }
                        res = api_post("/api/roles", payload)
                        if res and "req_id" in res:
                            st.success(f"Job {a_req} published successfully!")
                        else:
                            st.error("Failed to publish job. Requisition ID might already exist.")

    with tab_create:
        st.subheader("Fill and Publish Job Requisition")
        
        with st.form("publish_jd_form"):
            col1, col2 = st.columns(2)
            with col1:
                req_id = st.text_input("Requisition ID*", placeholder="e.g. REQ-2026")
                role_title = st.text_input("Role Title*")
                bu = st.text_input("Business Unit*", placeholder="e.g. Engineering")
                loc = st.text_input("Location*", placeholder="e.g. Remote, NY")
                target = st.number_input("Target Days*", min_value=1, value=30)
            with col2:
                openings = st.number_input("Openings*", min_value=1, value=1)
                exp = st.number_input("Minimum Experience (Years)*", min_value=0, value=0)
                salary = st.text_input("Salary Band*")
                skills = st.text_input("Required Skills (Comma separated)*")
                priority = st.selectbox("Priority", ["Medium", "High", "Critical"])
                risk = st.selectbox("Risk", ["Low", "Medium", "High"])
            
            submit_jd = st.form_submit_button("🚀 Publish Job to Candidates", type="primary", use_container_width=True)
            if submit_jd:
                if not req_id or not role_title or not bu or not loc or not salary or not skills:
                    st.error("Please fill all required fields.")
                else:
                    payload = {
                        "req_id": req_id,
                        "role": role_title,
                        "business_unit": bu,
                        "location": loc,
                        "openings": openings,
                        "required_skills": skills,
                        "experience_min": exp,
                        "salary_band": salary,
                        "target_days": target,
                        "priority": priority,
                        "risk": risk
                    }
                    res = api_post("/api/roles", payload)
                    if res and "req_id" in res:
                        st.success(f"Job {req_id} published successfully! Candidates can now apply.")
                    else:
                        st.error("Failed to publish job. Requisition ID might already exist.")
                        
    with tab_stats:
        st.subheader("Published JDs & Pipeline Stats")
        st.caption("Track the funnel of candidates for each of your published job descriptions.")
        
        if roles.empty:
            st.info("No job descriptions have been published yet.")
        else:
            # Create a clean dataframe for the stats table
            stats_cols = ["Role", "Req ID", "Applicants", "Screened", "Shortlisted", "Interview", "Offer", "Hired"]
            # Ensure all columns exist in roles dataframe
            available_cols = [c for c in stats_cols if c in roles.columns]
            stats_df = roles[available_cols]
            
            st.dataframe(
                stats_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Role": st.column_config.TextColumn("Role Title", width="large"),
                    "Req ID": st.column_config.TextColumn("Requisition ID"),
                    "Applicants": st.column_config.ProgressColumn("Applicants", format="%d", min_value=0, max_value=int(max(roles["Applicants"].max(), 100))),
                    "Hired": st.column_config.NumberColumn("Hired", format="%d 🏆"),
                }
            )

@st.fragment
def render_resume_ai(roles: "pd.DataFrame", candidates: "pd.DataFrame") -> None:
    st.title("\U0001f4c4 Resume AI")
    st.caption("Match resumes against a job description, get an AI hiring recommendation, and chat about any candidate profile.")

    tab_match = st.tabs(["\U0001f50d Resume Matcher"])[0]

    with tab_match:
        st.subheader("Match Candidate to Role")
        
        c1, c2 = st.columns(2)
        with c1:
            jd_source = st.radio("Match against", ["Existing Job Profile", "Upload JD from device"], horizontal=True, key="jd-source")
        if jd_source == "Existing Job Profile":
            selected_role_match = st.selectbox("Select target role", roles["Role"].tolist(), key="rm-role")
            role_row = roles[roles["Role"] == selected_role_match].iloc[0]
            st.markdown(f"**Required Skills for {selected_role_match}:** {role_row['Required Skills']}")
            st.markdown(f"**Minimum Experience:** {role_row['Experience Min']} years")
        else:
            uploaded_jd = st.file_uploader("Upload JD (TXT or PDF)", type=["txt", "pdf"], key="resume-jd-upload")
            if uploaded_jd is not None:
                if uploaded_jd.type == "text/plain":
                    jd_text = uploaded_jd.read().decode("utf-8", errors="ignore")
                else:
                    jd_text = uploaded_jd.read().decode("latin-1", errors="ignore")
                    jd_text = "".join(c for c in jd_text if c.isprintable() or c in "\n\r\t")
                st.success("JD uploaded successfully!")
                selected_role_match = "Custom Uploaded JD"
                role_row = pd.Series({"Role": "Custom Uploaded JD", "Required Skills": jd_text[:500] + "...", "Experience Min": 0})
            else:
                st.info("Please upload a JD to continue.")
                st.stop()

        source_mode = st.radio(
            "Select Resume Source",
            ["\U0001f4c1 Upload from device", "\U0001f464 Existing candidate profile"],
            horizontal=True,
            key="resume-source-mode",
            label_visibility="collapsed",
        )

        resume_data = None
        candidate_name_for_match = "Unknown"

        if source_mode == "\U0001f4c1 Upload from device":
            uploaded_file = st.file_uploader(
                "Upload resume (TXT or PDF)",
                type=["txt", "pdf"],
                key="resume-upload",
            )
            if uploaded_file is not None:
                if uploaded_file.type == "text/plain":
                    raw_text = uploaded_file.read().decode("utf-8", errors="ignore")
                else:
                    raw_text = uploaded_file.read().decode("latin-1", errors="ignore")
                    raw_text = "".join(c for c in raw_text if c.isprintable() or c in "\n\r\t")
                if raw_text.strip():
                    parsed = parse_resume_text(raw_text)
                    st.session_state["uploaded_resume_data"] = parsed
                    st.session_state["uploaded_resume_name"] = uploaded_file.name
                    st.success(f"\u2705 Resume uploaded \u2014 {len(parsed['skills'])} skills detected")
                else:
                    st.warning("Could not extract text. Try a plain-text .txt file.")

            if "uploaded_resume_data" in st.session_state:
                resume_data = st.session_state["uploaded_resume_data"]
                raw_fname = st.session_state.get("uploaded_resume_name", "Uploaded Resume")
                candidate_name_for_match = raw_fname
                st.caption(f"\U0001f4c4 Using: {raw_fname} | Skills found: {len(resume_data['skills'])}")

                # ── Save to Candidate Pool ────────────────────────────────────
                already_saved = st.session_state.get("uploaded_resume_saved") == raw_fname
                if not already_saved:
                    with st.expander("\U0001f4be Save this candidate to the pool", expanded=True):
                        st.caption("Fill in the details and save — this candidate will then appear across Find Candidates, Interviews, Rankings, and all other pages.")
                        sc1, sc2 = st.columns(2)
                        with sc1:
                            save_name = st.text_input(
                                "Candidate name \u2605",
                                value=raw_fname.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title(),
                                key="save-cand-name",
                                placeholder="Full name",
                            )
                            save_location = st.text_input(
                                "Location",
                                value="",
                                key="save-cand-location",
                                placeholder="e.g. Bengaluru",
                            )
                        with sc2:
                            save_role = st.selectbox(
                                "Applying for role",
                                roles["Role"].tolist(),
                                key="save-cand-role",
                            )
                            save_stage = st.selectbox(
                                "Current stage",
                                ["Applied", "Screening", "Technical interview", "Manager interview", "Offer discussion"],
                                key="save-cand-stage",
                            )

                        st.divider()
                        skill_preview = ", ".join(resume_data.get("skills", [])[:8]) or "No skills detected"
                        st.caption(f"\U0001f9e0 Skills detected: {skill_preview}")
                        st.caption(f"\U0001f4bc Experience detected: {resume_data.get('exp_years', 0)} years | Education: {resume_data.get('education', 'Not specified')}")

                        if st.button("\u2795 Add to Candidate Pool", key="save-cand-btn", use_container_width=True, type="primary"):
                            if not save_name.strip():
                                st.warning("\u26a0\ufe0f Please enter the candidate's name.")
                            else:
                                new_row = {
                                    "Candidate": save_name.strip(),
                                    "Role": save_role,
                                    "Location": save_location.strip() or "Not specified",
                                    "Experience": resume_data.get("exp_years", 0),
                                    "Match": 75,
                                    "Stage": save_stage,
                                    "Availability": "To be confirmed",
                                    "Salary Fit": "To be confirmed",
                                    "Risk": "Medium",
                                    "Skills": ", ".join(resume_data.get("skills", [])) or "See resume",
                                    "Source": "Resume Upload",
                                    "Last Touch": "Today",
                                    "Education": resume_data.get("education", "Not specified"),
                                    "Certifications": ", ".join(resume_data.get("certifications", [])) or "None listed",
                                    "Summary": (
                                        f"{resume_data.get('exp_years', '?')} yrs experience. "
                                        f"Uploaded via Resume AI. "
                                        f"Skills: {', '.join(resume_data.get('skills', [])[:5])}."
                                    ),
                                }
                                new_df = pd.DataFrame([new_row])
                                st.session_state["candidates"] = pd.concat(
                                    [st.session_state["candidates"], new_df], ignore_index=True
                                )
                                st.session_state["uploaded_resume_saved"] = raw_fname
                                candidate_name_for_match = save_name.strip()
                                st.success(f"\u2705 {save_name.strip()} added to the candidate pool! They now appear in Find Candidates, Interviews, Rankings, and all reports.")
                                # st.rerun()  # Disabled to prevent full screen reload
                else:
                    saved_name = st.session_state["candidates"][
                        st.session_state["candidates"]["Source"] == "Resume Upload"
                    ]["Candidate"].tolist()
                    saved_name_str = saved_name[-1] if saved_name else "Candidate"
                    st.success(f"\u2705 {saved_name_str} is already in the candidate pool. You can find them in Find Candidates.")

        else:
            selected_cand_name = st.selectbox(
                "Select existing candidate",
                candidates["Candidate"].tolist(),
                key="rm-cand"
            )
            cand_row = candidates[candidates["Candidate"] == selected_cand_name].iloc[0]
            candidate_name_for_match = cand_row["Candidate"]
            # Convert candidate row to the simple dict structure parse_resume_text outputs
            resume_data = {
                "skills": [s.strip() for s in cand_row["Skills"].split(",")],
                "exp_years": cand_row["Experience"],
                "education": cand_row.get("Education", "Not specified"),
                "certifications": [c.strip() for c in cand_row.get("Certifications", "").split(",") if c.strip()],
            }
            st.caption(f"\U0001f464 Loaded profile for {selected_cand_name} ({cand_row['Experience']} yrs exp)")

        st.divider()

        if resume_data:
            c_btn1, _ = st.columns([1, 2])
            with c_btn1:
                run_match = st.button(f"\u26a1 Score Match for {candidate_name_for_match}", use_container_width=True, type="primary")

            if run_match:
                with st.spinner("Llama 3.2 is scoring the resume match..."):
                    score_res = score_resume_vs_role(resume_data, role_row)

                st.subheader(f"Match Results: {candidate_name_for_match}")
                m1, m2, m3 = st.columns(3)
                m1.metric("Overall Match", f"{score_res['match_score']}%")
                m2.metric("Skill Coverage", f"{score_res['coverage']}%")
                m3.metric("Experience", "Pass \u2705" if score_res["exp_ok"] else "Gap \u26a0\ufe0f")

                st.markdown(f"**Verdict:** <span class='{score_res['v_class']}'>{score_res['verdict']}</span>", unsafe_allow_html=True)

                sc1, sc2 = st.columns(2)
                with sc1:
                    st.markdown("**\u2705 Matched Skills:**")
                    for s in score_res["matched_skills"]:
                        st.markdown(f"- {s}")
                with sc2:
                    st.markdown("**\u274c Missing Skills:**")
                    for s in score_res["missing_skills"]:
                        st.markdown(f"- {s}")

                st.divider()
                st.subheader("Hiring Recommendation")
                
                if source_mode == "\U0001f464 Existing candidate profile":
                    rec_input = cand_row.to_dict()
                else:
                    rec_input = {
                        "Candidate": candidate_name_for_match,
                        "Match": score_res["match_score"],
                        "Risk": "Medium",
                        "Salary Fit": "Unknown",
                        "Availability": "Unknown"
                    }
                
                with st.spinner("Llama 3.2 is generating a hiring recommendation..."):
                    verdict_r, css_r, reasoning_r = build_hiring_recommendation(rec_input)
                
                st.markdown(f"<h3 class='{css_r}'>{verdict_r}</h3>", unsafe_allow_html=True)
                st.info(reasoning_r)
        else:
            st.info("\u2b06\ufe0f Please upload a resume or select a candidate to see the match score.")

@st.fragment
def render_recruitment_insights(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    st.title("📊 Recruitment Insights")
    st.caption("Deep-dive into your recruitment pipeline health, skill gaps, and process efficiency.")

    tab_insight, tab_gap, tab_recruit = st.tabs([
        "🔭 Talent Overview",
        "🎯 Skill Gap Analyser",
        "🔬 Recruitment Analyser",
    ])

    # ── Tab 1: Talent Overview ───────────────────────────────────────────────
    with tab_insight:
        st.subheader("Key Talent Metrics")

        avg_match = round(candidates["Match"].mean(), 1)
        high_match = int((candidates["Match"] >= 88).sum())
        offer_rate = round(int(roles["Offer"].sum()) / max(int(roles["Interview"].sum()), 1) * 100, 1)
        hired_total = int(roles["Hired"].sum())
        avg_days = round(roles["Days Open"].mean(), 1)
        pipeline_health = min(100, round((avg_match * 0.4) + (offer_rate * 0.4) + (min(hired_total / max(int(roles["Openings"].sum()), 1) * 100, 100) * 0.2)))

        kpi_html = f"""
        <div class="insight-kpi-grid">
            <div class="insight-kpi blue">
                <div class="insight-kpi-value">{avg_match}%</div>
                <div class="insight-kpi-label">Avg Candidate Match</div>
                <div class="insight-kpi-trend">Across {len(candidates)} profiles</div>
            </div>
            <div class="insight-kpi teal">
                <div class="insight-kpi-value">{high_match}</div>
                <div class="insight-kpi-label">High-Quality Matches (≥88%)</div>
                <div class="insight-kpi-trend">Ready to progress</div>
            </div>
            <div class="insight-kpi gold">
                <div class="insight-kpi-value">{offer_rate}%</div>
                <div class="insight-kpi-label">Offer Conversion Rate</div>
                <div class="insight-kpi-trend">Interviews → Offers</div>
            </div>
            <div class="insight-kpi coral">
                <div class="insight-kpi-value">{avg_days}d</div>
                <div class="insight-kpi-label">Avg Days to Fill</div>
                <div class="insight-kpi-trend">Target: 36 days</div>
            </div>
        </div>
        """
        st.markdown(kpi_html, unsafe_allow_html=True)
        
        st.divider()
        st.subheader("🤖 AI Performance Summary")
        prompt = f"""
You are an expert HR Data Analyst. Based on the following pipeline health KPIs, write a concise 2-sentence summary of the recruitment process health.
- Avg Candidate Match: {avg_match}%
- High-Quality Matches (≥88%): {high_match}
- Offer Conversion Rate: {offer_rate}%
- Avg Days to Fill: {avg_days} days
Identify one positive and one area for improvement.
"""
        with st.spinner("Llama 3.2 is analysing the KPIs..."):
            summary = call_llama(prompt)
        st.info(summary)

        # Pipeline health score
        st.markdown(
            clean_html(f"""
            <div class="action-card {'green' if pipeline_health >= 70 else 'gold' if pipeline_health >= 50 else ''}">
                <div class="action-title">Pipeline Health Score: {pipeline_health}/100</div>
                <div class="action-copy">{'Strong pipeline — maintain momentum and close open offers.' if pipeline_health >= 70 else 'Moderate health — focus on accelerating interviews and improving offer rates.' if pipeline_health >= 50 else 'Pipeline needs attention — review bottlenecks and sourcing strategy.'}</div>
            </div>
            """),
            unsafe_allow_html=True,
        )

        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("Candidate Match Distribution")
            bins = {"70–79%": 0, "80–84%": 0, "85–89%": 0, "90–94%": 0, "95–100%": 0}
            for m in candidates["Match"]:
                if m < 80:
                    bins["70–79%"] += 1
                elif m < 85:
                    bins["80–84%"] += 1
                elif m < 90:
                    bins["85–89%"] += 1
                elif m < 95:
                    bins["90–94%"] += 1
                else:
                    bins["95–100%"] += 1
            st.bar_chart(pd.DataFrame.from_dict(bins, orient="index", columns=["Candidates"]), height=240)

        with col_r:
            st.subheader("Source Effectiveness")
            source_data = (
                candidates.groupby("Source")
                .agg(Count=("Candidate", "count"), AvgMatch=("Match", "mean"))
                .sort_values("AvgMatch", ascending=False)
            )
            source_data["AvgMatch"] = source_data["AvgMatch"].round(1)
            st.dataframe(source_data, use_container_width=True)

        st.subheader("Role-wise Metrics")
        role_metrics = roles[["Role", "Applicants", "Shortlisted", "Interview", "Offer", "Hired", "Days Open", "Risk"]].copy()
        role_metrics["Match Rate"] = (role_metrics["Shortlisted"] / role_metrics["Applicants"].clip(lower=1) * 100).round(1).astype(str) + "%"
        st.dataframe(role_metrics, use_container_width=True, hide_index=True)

    # ── Tab 2: Skill Gap Analyser ────────────────────────────────────────────
    with tab_gap:
        st.subheader("🎯 Skill Gap Analyser")
        st.caption("Select a role to see how well the current candidate pool covers required skills.")

        selected_role_gap = st.selectbox(
            "Select role to analyse",
            roles["Role"].tolist(),
            key="gap-role-select",
        )
        role_for_gap = roles[roles["Role"] == selected_role_gap].iloc[0]
        role_candidates = candidates[candidates["Role"] == selected_role_gap]
        required_skills = [s.strip() for s in role_for_gap["Required Skills"].split(",")]

        if role_candidates.empty:
            st.info("No candidates found for this role in the current dataset.")
        else:
            # Skill coverage per required skill
            coverage_rows = []
            for skill in required_skills:
                count = role_candidates["Skills"].str.contains(skill, case=False, regex=False).sum()
                pct = round(count / len(role_candidates) * 100)
                coverage_rows.append({"Skill": skill, "Candidates with skill": count, "Coverage %": pct})

            coverage_df = pd.DataFrame(coverage_rows).sort_values("Coverage %", ascending=False)

            # KPI summary
            g1, g2, g3 = st.columns(3)
            fully_covered = int((coverage_df["Coverage %"] >= 80).sum())
            partially = int(((coverage_df["Coverage %"] >= 40) & (coverage_df["Coverage %"] < 80)).sum())
            critical_gaps = int((coverage_df["Coverage %"] < 40).sum())
            g1.metric("Skills Well-Covered (≥80%)", fully_covered)
            g2.metric("Partially Covered (40-79%)", partially)
            g3.metric("Critical Gaps (<40%)", critical_gaps)

            # Bar chart of coverage
            st.subheader("Skill Coverage by Candidate Pool")
            st.bar_chart(coverage_df.set_index("Skill")["Coverage %"], height=280)

            # Detailed table
            def color_row(row):
                if row["Coverage %"] >= 80:
                    return ["background-color: #d1fae5"] * len(row)
                elif row["Coverage %"] >= 40:
                    return ["background-color: #fef3c7"] * len(row)
                else:
                    return ["background-color: #ffe4e6"] * len(row)

            st.subheader("Skill Gap Detail")
            st.dataframe(coverage_df.style.apply(color_row, axis=1), use_container_width=True, hide_index=True)

            # Recommendations
            st.subheader("🤖 AI Gap Recommendations")
            prompt = f"""
You are an expert Talent Analytics AI. Based on the following skill gap data for the role of {role_for_gap['Role']}:
{coverage_df.to_dict(orient='records')}

Provide 3 highly actionable, strategic recommendations to bridge these gaps (e.g., sourcing strategy, upskilling, requirement adjustment).
Output ONLY as a markdown list of suggestions. Do not include introductory text.
"""
            with st.spinner("Llama 3.2 is analysing gaps..."):
                gap_recs = call_llama(prompt)
            st.markdown(gap_recs)



    # ── Tab 3: Recruitment Analyser ──────────────────────────────────────────
    with tab_recruit:
        st.subheader("🔬 Recruitment Process Analyser")
        st.caption("Identify bottlenecks, measure source ROI, and get AI recommendations to fix pipeline leaks.")

        # Stage conversion analysis
        st.subheader("Pipeline Stage Conversions")
        total_app = int(roles["Applicants"].sum())
        total_screen = int(roles["Screened"].sum())
        total_short = int(roles["Shortlisted"].sum())
        total_int = int(roles["Interview"].sum())
        total_offer = int(roles["Offer"].sum())
        total_hire = int(roles["Hired"].sum())

        stages_data = {
            "Stage": ["Applied → Screened", "Screened → Shortlisted", "Shortlisted → Interview", "Interview → Offer", "Offer → Hired"],
            "Input": [total_app, total_screen, total_short, total_int, total_offer],
            "Output": [total_screen, total_short, total_int, total_offer, total_hire],
        }
        stages_df = pd.DataFrame(stages_data)
        stages_df["Conversion %"] = (stages_df["Output"] / stages_df["Input"].clip(lower=1) * 100).round(1)
        stages_df["Drop-off"] = stages_df["Input"] - stages_df["Output"]

        # Color highlight the worst drop-off
        worst_stage = stages_df.loc[stages_df["Drop-off"].idxmax(), "Stage"]

        for _, s in stages_df.iterrows():
            conv = s["Conversion %"]
            st.markdown(
                clean_html(f"""
                <div class="bar-row">
                    <div class="bar-meta"><span>{s['Stage']}</span><span>{s['Output']} / {s['Input']} = {conv}%</span></div>
                    <div class="bar-shell"><div class="bar-fill {'missing' if conv < 25 else ''}" style="--width:{min(conv*2, 100)}%;"></div></div>
                </div>
                """),
                unsafe_allow_html=True,
            )

        st.subheader("Bottleneck Detection")
        st.markdown(
            clean_html(f"""
            <div class="verdict-card waitlist">
                <div class="verdict-title">⚠️ Biggest bottleneck: {worst_stage}</div>
                <div class="verdict-body">
                    This stage has the highest candidate drop-off ({stages_df.loc[stages_df['Stage']==worst_stage, 'Drop-off'].values[0]} candidates lost).
                    Review the selection criteria, interviewer availability, and feedback turnaround time at this stage.
                </div>
            </div>
            """),
            unsafe_allow_html=True,
        )

        # Source ROI
        st.subheader("Source ROI Analysis")
        source_roi = (
            candidates.groupby("Source")
            .agg(
                Candidates=("Candidate", "count"),
                AvgMatch=("Match", "mean"),
                LowRisk=("Risk", lambda x: (x == "Low").sum()),
            )
            .reset_index()
        )
        source_roi["AvgMatch"] = source_roi["AvgMatch"].round(1)
        source_roi["Quality Score"] = ((source_roi["AvgMatch"] * 0.6) + (source_roi["LowRisk"] / source_roi["Candidates"].clip(lower=1) * 40)).round(1)
        source_roi = source_roi.sort_values("Quality Score", ascending=False)
        st.dataframe(source_roi, use_container_width=True, hide_index=True)

        best_source = source_roi.iloc[0]["Source"]

        # AI Recommendations
        st.subheader("🤖 AI Process Recommendations")
        overdue_roles = roles[roles["Days Open"] > roles["Target Days"]]
        prompt = f"""
You are an expert Recruitment Process Engineer AI. Based on the following data:
Best Source: {best_source} (Quality Score: {source_roi.iloc[0]['Quality Score']})
Worst Bottleneck Stage: {worst_stage}
Overdue Roles: {', '.join(overdue_roles['Role'].tolist()) if not overdue_roles.empty else 'None'}
Offer Conversion Rate: {stages_df.iloc[-1]['Conversion %']}%

Provide 3-4 strategic process improvements to optimize recruitment ROI, unblock bottlenecks, and improve conversion.
Output ONLY as a markdown list with bold headings for each point. Do not include introductory text.
"""
        with st.spinner("Llama 3.2 is generating process recommendations..."):
            process_recs = call_llama(prompt)
        st.markdown(process_recs)

        # Time-to-hire by role
        st.subheader("Time-to-Fill by Role")
        tti = roles[["Role", "Days Open", "Target Days", "Risk"]].copy()
        tti["Status"] = tti.apply(lambda r: "🔴 Overdue" if r["Days Open"] > r["Target Days"] else "🟢 On track", axis=1)
        st.dataframe(tti, use_container_width=True, hide_index=True)


# ───────────────────────────────────────────────────────────────────────────────
# PAGE: COMMUNICATIONS — AI Email Generator (NEW)
# ───────────────────────────────────────────────────────────────────────────────

_EMAIL_TEMPLATES = {
    "Shortlist Invitation": (
        "Interview Opportunity at Infosys – {role}",
        """Dear {name},

We are pleased to let you know that your application for the {role} position at Infosys has been reviewed and you have been shortlisted for the next stage of our selection process.

Based on your profile, we believe your background in {skills} aligns well with what we are looking for. Your {experience} years of experience makes you a strong contender.

Next Steps:
Our team will reach out within the next 2 business days to schedule a suitable time for a discussion. In the meantime, please feel free to review the role details and prepare any questions you may have.

We look forward to getting to know you better.

Warm regards,
Talent Acquisition Team
Infosys Limited"""
    ),
    "Interview Invitation": (
        "Interview Confirmation – {role} | Infosys",
        """Dear {name},

Thank you for your continued interest in the {role} position at Infosys.

We are delighted to invite you for a formal interview. Please find the details below:

Role: {role}
Mode: Microsoft Teams (link will be shared separately)
Duration: Approximately 60–90 minutes

To confirm your availability, please reply to this email with your preferred time from the options we will send separately.

Please have your updated resume, relevant project examples, and any certifications handy. The interview will cover your technical expertise in {skills} and situational scenarios.

We look forward to meeting you.

Best regards,
Talent Acquisition Team
Infosys Limited"""
    ),
    "Offer Letter": (
        "Offer of Employment – {role} | Infosys Limited",
        """Dear {name},

We are thrilled to extend this offer of employment for the position of {role} at Infosys Limited.

We are confident that your expertise in {skills} and your {experience} years of experience will make you a valuable addition to our team.

Key Details:
• Position: {role}
• Start Date: To be mutually agreed
• Compensation: As per our discussion (formal letter to follow)
• Location: As discussed

Please review the formal offer document that will be shared via our HR portal. We request your confirmation within 5 business days.

We look forward to welcoming you to the Infosys family.

Sincerely,
HR & Talent Acquisition
Infosys Limited"""
    ),
    "Rejection (with care)": (
        "Update on Your Application – {role} | Infosys",
        """Dear {name},

Thank you sincerely for the time and effort you invested in applying for the {role} position at Infosys and for engaging with our team throughout the process.

After careful consideration, we have decided to move forward with another candidate whose experience more closely matches our current requirements. This was a competitive process and your profile was impressive.

We encourage you to apply for future openings at Infosys that may align with your background in {skills}. We will retain your profile in our talent database for upcoming opportunities.

Thank you again, and we wish you every success in your career.

Warm regards,
Talent Acquisition Team
Infosys Limited"""
    ),
    "Follow-up / Status Update": (
        "Update on Your Application Status – {role}",
        """Dear {name},

We wanted to reach out with a quick update regarding your application for the {role} role at Infosys.

Your application is currently under active review and you are at the {stage} stage of the process. Our team is working to finalise next steps, and we appreciate your patience.

We will be in touch by the end of this week with a firm update. If you have any questions in the meantime, please do not hesitate to reach out.

Thank you for your continued interest in Infosys.

Best regards,
Talent Acquisition Team
Infosys Limited"""
    ),
    "AI Email Generator (Custom)": (
        "Custom AI-Generated Email",
        """Dear {name},

Thank you for your interest in the {role} position at Infosys.

We wanted to reach out regarding your application. Your profile — particularly your experience in {skills} — caught our attention.

[Customize this section with specific details relevant to your communication.]

Please do not hesitate to contact us if you have any questions.

Best regards,
Talent Acquisition Team
Infosys Limited"""
    ),
}


def generate_email(template_key: str, candidate: "pd.Series") -> tuple[str, str]:
    name = candidate["Candidate"]
    role = candidate["Role"]
    skills = candidate["Skills"]
    stage = candidate["Stage"]
    
    prompt = f"""
You are an AI assistant helping a recruiter write an email.
The email type is: {template_key}

Candidate details:
- Name: {name}
- Role Applied: {role}
- Skills: {skills}
- Current Stage: {stage}

Return ONLY a valid JSON object with EXACTLY two keys: "subject" and "body".
Do NOT include markdown formatting outside the JSON, no backticks, no explanations.
The body MUST use 
 for paragraphs and strictly follow a professional business template format.
"""
    response = call_llama(prompt, expect_json=True)
    try:
        data = json.loads(response)
        subject = data.get("subject", f"Update regarding your application for {role}")
        body = data.get("body", "Failed to generate email content.")
    except:
        subject = f"Update regarding your application for {role}"
        body = "An error occurred generating the email. Please try again."
        
    return subject, body



@st.fragment
def render_communications(candidates: pd.DataFrame) -> None:
    st.title("📧 Communications")
    st.caption("Generate professional recruitment emails with AI and send them directly from this platform.")

    if "sent_emails" not in st.session_state:
        st.session_state["sent_emails"] = []

    tab_compose, tab_sent = st.tabs(["✉️ Compose Email", "📬 Sent History"])

    with tab_compose:
        col_left, col_right = st.columns([1, 1.4])

        with col_left:
            st.subheader("Email Settings")

            email_type = st.selectbox(
                "Email type",
                list(_EMAIL_TEMPLATES.keys()),
                key="email-type-select",
            )
            candidate_pick = st.selectbox(
                "Candidate",
                candidates["Candidate"].tolist(),
                key="email-candidate-pick",
            )
            selected_cand = candidates[candidates["Candidate"] == candidate_pick].iloc[0]

            # Show candidate mini-summary
            st.markdown(
                clean_html(f"""
                <div class="field" style="margin-top:.5rem;">
                    <div class="field-label">Candidate Summary</div>
                    <div class="field-value">{selected_cand['Role']} · {selected_cand['Stage']} · {selected_cand['Match']}% match</div>
                </div>
                """),
                unsafe_allow_html=True,
            )

            candidate_email = st.text_input("Candidate Email Address", placeholder="e.g. candidate@example.com", key="email-candidate-email")
            recruiter_name = st.text_input("Your name (sender)", value="Priya Sharma", key="email-sender")

            if st.button("✨ Generate Email", key="generate-email-btn", use_container_width=True):
                with st.spinner(f"Llama 3.2 is drafting the {email_type} email..."):
                    subject, body = generate_email(email_type, selected_cand)
                st.session_state["email_subject"] = subject
                st.session_state["email_body"] = body
                st.session_state["email_candidate"] = candidate_pick
                st.session_state["email_type"] = email_type

        with col_right:
            st.subheader("Email Preview & Edit")

            subject_val = st.session_state.get("email_subject", "")
            body_val = st.session_state.get("email_body", "")

            if not subject_val:
                st.markdown(
                    "<div class='tip-box'>💡 Select email type and candidate, then click <strong>Generate Email</strong> to create a draft.</div>",
                    unsafe_allow_html=True,
                )
            else:
                edited_subject = st.text_input("Subject line", value=subject_val, key="email-subject-edit")
                edited_body = st.text_area("Email body (editable)", value=body_val, height=340, key="email-body-edit")

                col_send, col_dl = st.columns(2)
                with col_send:
                    if st.button("📤 Send Email", key="send-email-btn", use_container_width=True, type="primary"):
                        if not st.session_state.get("google_linked"):
                            st.warning("⚠️ Google Workspace is not linked. Please link your account in Settings > Integrations.")
                        elif not candidate_email:
                            st.error("Please provide a candidate email address.")
                        else:
                            sender_email = st.session_state.get("saved_email")
                            sender_password = st.session_state.get("saved_pass")
                            
                            with st.spinner("Sending email..."):
                                try:
                                    msg = EmailMessage()
                                    msg.set_content(edited_body)
                                    msg["Subject"] = edited_subject
                                    msg["From"] = sender_email
                                    msg["To"] = candidate_email

                                    server = smtplib.SMTP("smtp.gmail.com", 587)
                                    server.starttls()
                                    server.login(sender_email, sender_password)
                                    server.send_message(msg)
                                    server.quit()
                                    
                                    st.session_state["sent_emails"].append({
                                        "To": f"{st.session_state['email_candidate']} ({candidate_email})",
                                        "Type": st.session_state["email_type"],
                                        "Subject": edited_subject,
                                        "Sent At": date.today().strftime("%d %b %Y"),
                                        "Sender": recruiter_name,
                                        "Body": edited_body,
                                    })
                                    st.success(f"✅ Email sent successfully to {candidate_email}!")
                                except Exception as e:
                                    st.error(f"Failed to send email. Error: {str(e)}. Check your SMTP credentials in Settings.")

                with col_dl:
                    full_email = f"Subject: {edited_subject}\nFrom: {recruiter_name}\n\n{edited_body}"
                    st.download_button(
                        "⬇️ Download Draft",
                        data=full_email,
                        file_name=f"email_{candidate_pick.replace(' ', '_')}.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )

    with tab_sent:
        st.subheader("📬 Sent Email History")
        sent = st.session_state["sent_emails"]
        if not sent:
            st.info("No emails sent yet. Compose and send an email to see history here.")
        else:
            st.caption(f"{len(sent)} email(s) sent this session.")
            for i, email in enumerate(reversed(sent)):
                with st.expander(f"[{email['Type']}] → {email['To']} · {email['Sent At']}"):
                    st.markdown(f"**Subject:** {email['Subject']}")
                    st.markdown(f"**Sent by:** {email['Sender']} · {email['Sent At']}")
                    st.text_area("Body", value=email["Body"], height=200, key=f"sent-body-{i}", disabled=True)

            # Summary table
            sent_df = pd.DataFrame(sent)[["To", "Type", "Subject", "Sent At", "Sender"]]
            st.subheader("Summary")
            st.dataframe(sent_df, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: REPORTS — Report Generator (NEW)
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(
    report_type: str,
    roles: "pd.DataFrame",
    candidates: "pd.DataFrame",
    selected_roles: list[str],
    period_label: str,
) -> str:
    from datetime import date
    today_str = date.today().strftime("%d %B %Y")
    
    filtered_roles = roles if not selected_roles else roles[roles["Role"].isin(selected_roles)]
    filtered_cands = candidates if not selected_roles else candidates[candidates["Role"].isin(selected_roles)]
    
    total_app = int(filtered_roles["Applicants"].sum()) if not filtered_roles.empty else 0
    total_hire = int(filtered_roles["Hired"].sum()) if not filtered_roles.empty else 0
    avg_match = round(filtered_cands["Match"].mean(), 1) if not filtered_cands.empty else 0
    
    system = "You are an expert HR Data Analyst generating a recruitment report."
    
    prompt = f"""
Generate a professional {report_type} in Markdown format.

Context data:
- Date Generated: {today_str}
- Period: {period_label}
- Roles included: {', '.join(selected_roles) if selected_roles else 'All Roles'}
- Total Applications: {total_app}
- Total Hires: {total_hire}
- Average Candidate Match Score: {avg_match}%

You MUST follow this STRICT markdown structure containing exactly 5 headings. Use clean pointers/bullet points instead of long paragraphs. 
CRITICAL: Do NOT use any code blocks, triple backticks (```), or indented blocks (white boxes) for text. DO NOT indent your bullet points (indenting bullet points by 4 spaces turns them into code blocks in markdown, which looks bad). Do NOT use ASCII art graphs or Mermaid charts. Just use standard text and bullet points starting with a dash "-".

# 1. Executive Summary
- [Bullet point summary of the overall health of the recruitment pipeline]
- [Bullet point on general trends]

# 2. Key Metrics Analysis
- [Brief pointers on metrics and conversion rates]

# 3. Sourcing Channel Performance
- [Pointers on which sourcing channels are performing best vs worst]

# 4. Bottlenecks Analysis
- [Identify 3-4 specific bottlenecks in the current process]
- [Highlight where candidates are dropping off]

# 5. Strategic Recommendations
- [Provide 3-4 highly actionable recommendations to improve time-to-fill and offer-conversion]

Ensure the report relies heavily on pointers rather than dense text.
"""
    return call_llama(prompt, system=system)



@st.fragment
def render_reports(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    st.title("📑 Report Generator")
    st.caption("Generate comprehensive AI-powered recruitment reports in seconds and download as Markdown.")

    col_settings, col_preview = st.columns([1, 1.6])

    with col_settings:
        st.subheader("Report Settings")

        report_type = st.selectbox(
            "Report type",
            [
                "Recruitment Summary Report",
                "Candidate Pipeline Report",
                "Role-wise Analysis Report",
                "Talent Gap Report",
            ],
            key="report-type-select",
        )

        selected_roles_filter = st.multiselect(
            "Filter by role (leave blank for all)",
            roles["Role"].tolist(),
            default=[],
            key="report-role-filter",
        )

        period = st.selectbox(
            "Reporting period",
            ["This Week", "This Month", "Last 30 Days", "Last Quarter", "Year to Date"],
            key="report-period",
        )

        st.divider()

        if st.button("🤖 Generate Report", key="generate-report-btn", use_container_width=True, type="primary"):
            with st.spinner("Generating report..."):
                report_md = generate_report(
                    report_type, roles, candidates, selected_roles_filter, period
                )
                st.session_state["generated_report"] = report_md
                st.session_state["report_type_label"] = report_type

    with col_preview:
        st.subheader("Report Preview")

        report_md = st.session_state.get("generated_report", "")
        report_type_label = st.session_state.get("report_type_label", "")

        if not report_md:
            st.markdown(
                "<div class='tip-box'>💡 Configure the report settings on the left and click <strong>Generate Report</strong>.</div>",
                unsafe_allow_html=True,
            )
            # Show report type descriptions
            descriptions = {
                "Recruitment Summary Report": "High-level overview of the entire hiring process — applications, conversions, hires, and timelines.",
                "Candidate Pipeline Report": "Detailed view of all candidates by stage, match score, and risk profile.",
                "Role-wise Analysis Report": "Per-role breakdown with pipeline funnel, coverage, and status.",
                "Talent Gap Report": "Analysis of skill gaps in both external candidate pool and internal workforce.",
            }
            for rtype, desc in descriptions.items():
                st.markdown(f"**{rtype}:** {desc}")
        else:
            st.subheader("Report Visualizations")
            # Ensure roles is available in session state or passed correctly. Since we are inside render_reports, 'roles' is available.
            try:
                import plotly.express as px
                filtered_roles = roles
                if selected_roles_filter:
                    filtered_roles = roles[roles["Role"].isin(selected_roles_filter)]
                
                if report_type_label in ["Recruitment Summary Report", "Role-wise Analysis Report"]:
                    viz_data = filtered_roles[["Role", "Applicants", "Screened", "Interview", "Offer", "Hired"]].set_index("Role")
                    st.bar_chart(viz_data, use_container_width=True)
                    
                    fig = px.bar(filtered_roles, x="Role", y=["Days Open", "Target Days"], barmode="group", title="Time-to-Fill vs Target by Role")
                    st.plotly_chart(fig, use_container_width=True)
                    
                elif report_type_label == "Candidate Pipeline Report":
                    filtered_cands = candidates
                    if selected_roles_filter:
                        filtered_cands = candidates[candidates["Role"].isin(selected_roles_filter)]
                    if "Experience" in filtered_cands.columns:
                        fig = px.scatter(filtered_cands, x="Experience", y="Match", color="Stage", hover_name="Candidate", title="Candidate Match vs Experience by Stage")
                    else:
                        fig = px.scatter(filtered_cands, x="Role", y="Match", color="Stage", hover_name="Candidate", title="Candidate Match by Role and Stage")
                    st.plotly_chart(fig, use_container_width=True)
                    
                elif report_type_label == "Talent Gap Report":
                    filtered_cands = candidates
                    if selected_roles_filter:
                        filtered_cands = candidates[candidates["Role"].isin(selected_roles_filter)]
                    fig = px.histogram(filtered_cands, x="Match", nbins=10, title="Distribution of Candidate Match Scores", color="Role")
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    viz_data = filtered_roles[["Role", "Applicants", "Screened", "Interview", "Offer", "Hired"]].set_index("Role")
                    st.bar_chart(viz_data, use_container_width=True)
                    
            except Exception as e:
                st.error(f"Could not render chart: {e}")
                
            st.subheader("AI Analysis")
            st.markdown(report_md)
            st.divider()

            file_name = f"{report_type_label.replace(' ', '_').lower()}_{date.today().strftime('%Y%m%d')}.md"
            st.download_button(
                "⬇️ Download Report (.md)",
                data=report_md,
                file_name=file_name,
                mime="text/markdown",
                use_container_width=True,
            )

            # Also offer plain text
            plain_text = report_md.replace("**", "").replace("##", "").replace("#", "").replace("|", " | ")
            st.download_button(
                "⬇️ Download as Plain Text (.txt)",
                data=plain_text,
                file_name=file_name.replace(".md", ".txt"),
                mime="text/plain",
                use_container_width=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL COPILOT CHAT
# ─────────────────────────────────────────────────────────────────────────────

def build_copilot_reply(
    prompt: str,
    candidates: "pd.DataFrame",
    roles: "pd.DataFrame",
    user_role: str = "recruiter",
) -> str:
    if user_role == "candidate":
        system = """You are the AI-Driven Smart Hiring Platform Copilot.
        
ALLOWED TOPICS:
- Job profiles, required skills, application process, and general career advice.

STRICT RULES:
1. You MUST NOT disclose any internal HR operations, admin features, other candidates' data, internal performance data, or hiring insights.
2. If asked about admin sections, hiring pipelines, internal metrics, or other candidates, refuse to answer and state you are an assistant for candidates only.
3. Answer concisely and professionally.
"""
    else:
        active_roles_count = len(roles)
        total_cands = len(candidates)
        top_cand = candidates.sort_values("Match", ascending=False).iloc[0]["Candidate"] if not candidates.empty else "None"
        
        system = f"""You are the AI-Driven Smart Hiring Platform Copilot — a STRICTLY scoped AI assistant.

ALLOWED TOPICS (you may ONLY answer questions about these):
- Recruitment: candidates, job roles, job descriptions, interviews, hiring pipelines, resume screening, skill matching.
- HR Operations: reports, communications, emails, offer letters, JD analysis.
- Dashboard Features: how to use the Overview, Find Candidates, JD Analyser, Resume AI, Interviews, Recruitment Insights, Communications, Reports, or Chat with AI pages.

CURRENT DASHBOARD DATA:
- Active Roles: {active_roles_count}
- Total Candidates: {total_cands}
- Top External Candidate: {top_cand}

STRICT RULES:
1. If a question is NOT related to recruitment, HR, or this project's features, you MUST refuse to answer.
2. For any off-topic question (e.g. weather, sports, celebrities, movies, general knowledge, coding help, math, science, politics, personal advice), respond ONLY with:
   "I'm sorry, I can only assist with recruitment and HR-related queries within this platform. Please ask me something about candidates, job roles, or any feature of this dashboard!"
3. Do NOT attempt to answer off-topic questions even partially. Do NOT say "I don't know but..." and then answer anyway.
4. For on-topic questions, answer concisely and professionally using the dashboard data above.
"""
    return call_llama(prompt, system=system)



@st.fragment
def render_copilot_console(candidates: pd.DataFrame, roles: pd.DataFrame) -> None:
    st.divider()

    if "copilot_open" not in st.session_state:
        st.session_state["copilot_open"] = False
    if "copilot_messages" not in st.session_state:
        st.session_state["copilot_messages"] = [
            {
                "role": "assistant",
                "content": "Hi! I can help with candidates, interviews, skill gaps, emails, reports, JD analysis, and recruitment insights. What do you need?",
            }
        ]

    if not st.session_state["copilot_open"]:
        st.markdown(
            clean_html(
                """
            <div class="chatbot-launcher">
                <div class="chatbot-launcher-left">
                    <div class="chatbot-icon"></div>
                    <div>
                        <div class="chatbot-launcher-title">Ask the AI Copilot</div>
                        <div class="chatbot-launcher-copy">Open a chat about jobs, candidates, skill gaps, emails, or reports.</div>
                    </div>
                </div>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )
        if st.button("Open AI Copilot", key="open-copilot", use_container_width=True):
            st.session_state["copilot_open"] = True
            st.rerun()
        return

    header_cols = st.columns([1, .16])
    with header_cols[1]:
        if st.button("Close", key="close-copilot", use_container_width=True):
            st.session_state["copilot_open"] = False
            st.rerun()

    messages_html = ""
    for message in st.session_state["copilot_messages"]:
        role = "user" if message["role"] == "user" else "assistant"
        content = escape(message["content"]).replace("\n", "<br>")
        messages_html += f'<div class="chat-message {role}">{content}</div>'

    st.markdown(
        clean_html(
            f"""
        <div class="chatbot-panel">
            <div class="chatbot-header">
                <div>
                    <div class="chatbot-title">AI Copilot</div>
                    <div class="chatbot-status">● Online for this workspace</div>
                </div>
                <div class="chatbot-icon"></div>
            </div>
            <div class="chatbot-body">
                {messages_html}
            </div>
        </div>
        <div class="chatbot-input-note">Ask about candidates, jobs, skill gaps, emails, reports, or recruitment insights.</div>
        """
        ),
        unsafe_allow_html=True,
    )

    with st.form("copilot-chat-form", clear_on_submit=True, border=False):
        prompt = st.text_input(
            "Message the assistant",
            placeholder="Which city has the strongest candidate pipeline?",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send →")

    if submitted and prompt.strip():
        st.session_state["copilot_messages"].append({"role": "user", "content": prompt.strip()})
        st.session_state["copilot_messages"].append(
            {
                "role": "assistant",
                "content": build_copilot_reply(prompt.strip(), candidates, roles),
            }
        )



# ─────────────────────────────────────────────────────────────────────────────
# AI CHAT PAGE
# ─────────────────────────────────────────────────────────────────────────────


@st.fragment
def render_ai_chat(candidates: pd.DataFrame, roles: pd.DataFrame, user_role: str = "recruiter") -> None:
    st.header("🤖 Chat with AI")
    if user_role == "candidate":
        st.markdown("Your dedicated AI Assistant. Ask anything about job profiles, required skills, or application advice.")
    else:
        st.markdown("Your dedicated Copilot for recruitment and HR operations. Ask anything about roles, candidates, or skill gaps.")
    
    if "ai_chat_history" not in st.session_state:
        if user_role == "candidate":
            st.session_state["ai_chat_history"] = [
                {"role": "assistant", "content": "Hi! I'm the AI-Driven Smart Hiring Platform Copilot. I can help you understand job profiles, required skills, and the application process. How can I assist you today?"}
            ]
        else:
            st.session_state["ai_chat_history"] = [
                {"role": "assistant", "content": "Hi! I'm the AI-Driven Smart Hiring Platform Copilot. I can help you with recruitment and HR operations — ask me about candidates, job roles, hiring pipelines, interviews, skill gaps, reports, or any feature of this dashboard!\n\n*Note: I'm strictly scoped to this platform and won't answer questions outside of HR and recruitment.*"}
            ]
        
    chat_container = st.container(height=500)
    
    for msg in st.session_state["ai_chat_history"]:
        with chat_container.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    input_placeholder = "Ask about job profiles or requirements..." if user_role == "candidate" else "Ask about candidates, job roles, interviews, or dashboard features..."
    if prompt := st.chat_input(input_placeholder):
        st.session_state["ai_chat_history"].append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)
            
        with chat_container.chat_message("assistant"):
            with st.spinner("AI is thinking..."):
                reply = build_copilot_reply(prompt, candidates, roles, user_role=user_role)
                st.markdown(reply)
        st.session_state["ai_chat_history"].append({"role": "assistant", "content": reply})


# ─────────────────────────────────────────────────────────────────────────────
# ONBOARDING
# ─────────────────────────────────────────────────────────────────────────────


@st.fragment
def render_onboarding(roles: pd.DataFrame, candidates: pd.DataFrame) -> None:
    st.header("🎓 Candidate Onboarding")
    st.caption("Convert hired candidates. Upload and verify documents with AI, review extracted profile data, and complete the onboarding process.")

    # ── Candidate selector ────────────────────────────────────────────────
    # Show all candidates (they are already ready to join)
    if candidates.empty:
        st.info("No candidates available for onboarding.")
        return

    # Exclude already-onboarded candidates
    eligible = candidates[candidates["Stage"] != "Onboarded"] if "Stage" in candidates.columns else candidates
    onboarded = candidates[candidates["Stage"] == "Onboarded"] if "Stage" in candidates.columns else pd.DataFrame()

    if eligible.empty:
        st.success("🎉 All candidates have been onboarded!")
        return

    st.subheader("Select Candidate")
    candidate_names = eligible["Candidate"].tolist()
    selected_name = st.selectbox("Choose a candidate to onboard", candidate_names, key="onboard_candidate_select")
    selected = eligible[eligible["Candidate"] == selected_name].iloc[0]

    # ── Profile Card (auto-extracted from resume/application data) ────────
    st.divider()
    st.subheader("📋 Candidate Profile (Auto-Extracted)")

    st.markdown(
        clean_html(
            f"""
        <div style="background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
                    border: 1px solid rgba(15, 139, 141, 0.3);
                    border-radius: 16px; padding: 28px; margin-bottom: 20px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
                <div>
                    <h2 style="margin: 0; color: #fff; font-size: 1.6rem;">{selected['Candidate']}</h2>
                    <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.95rem;">
                        Applying for: <strong style="color: #4facfe;">{selected.get('Role', 'N/A')}</strong>
                    </p>
                </div>
                <div style="background: rgba(15, 139, 141, 0.2); padding: 8px 18px;
                            border-radius: 20px; font-size: 0.85rem; color: #5eead4;">
                    Match Score: <strong>{selected.get('Match', 'N/A')}%</strong>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 16px; margin-top: 20px;">
                <div>
                    <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Experience</span>
                    <p style="color: #e2e8f0; margin: 4px 0 0 0; font-weight: 600;">{selected.get('Experience', 'N/A')} years</p>
                </div>
                <div>
                    <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Location</span>
                    <p style="color: #e2e8f0; margin: 4px 0 0 0; font-weight: 600;">{selected.get('Location', 'N/A')}</p>
                </div>
                <div>
                    <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Education</span>
                    <p style="color: #e2e8f0; margin: 4px 0 0 0; font-weight: 600;">{selected.get('Education', 'N/A')}</p>
                </div>
                <div>
                    <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Availability</span>
                    <p style="color: #e2e8f0; margin: 4px 0 0 0; font-weight: 600;">{selected.get('Availability', 'N/A')}</p>
                </div>
            </div>
            <div style="margin-top: 16px;">
                <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Skills</span>
                <p style="color: #e2e8f0; margin: 4px 0 0 0; font-weight: 500;">{selected.get('Skills', 'N/A')}</p>
            </div>
            <div style="margin-top: 12px;">
                <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Certifications</span>
                <p style="color: #e2e8f0; margin: 4px 0 0 0; font-weight: 500;">{selected.get('Certifications', 'N/A') or 'None listed'}</p>
            </div>
            <div style="margin-top: 12px;">
                <span style="color: #64748b; font-size: 0.75rem; text-transform: uppercase; font-weight: 700;">Summary</span>
                <p style="color: #cbd5e1; margin: 4px 0 0 0; font-style: italic;">{selected.get('Summary', 'N/A') or 'No summary available'}</p>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )

    # ── Onboarding Details (auto-generated + recruiter input) ───────────────
    st.divider()
    st.subheader("🏢 Onboarding Details")

    # Auto-generate Onboarding ID
    today_str = date.today().strftime("%y%m%d")
    existing_count = len(onboarded) if not onboarded.empty else 0
    auto_emp_id = f"INF-ONB-{today_str}-{existing_count + 1:03d}"

    e_col1, e_col2 = st.columns(2)
    with e_col1:
        emp_id = st.text_input("Onboarding ID (Auto-Generated)", value=auto_emp_id, key="onboard_emp_id")
        designation = st.text_input("Designation", value=selected.get("Role", ""), key="onboard_designation")
        department = st.selectbox(
            "Department",
            ["Engineering & Technology", "Infosys Topaz", "Cloud & Infrastructure", "Digital Experience",
             "Consulting & Advisory", "Data & Analytics", "Cybersecurity", "HR & Operations", "Finance"],
            key="onboard_department",
        )
    with e_col2:
        manager = st.text_input("Reporting Manager", placeholder="e.g. Sarah Jenkins", key="onboard_manager")
        location = st.text_input("Office Location", value=selected.get("Location", ""), key="onboard_location")
        ready_for = st.text_input("Ready For (Target Role)", placeholder="e.g. Senior Engineer", key="onboard_ready_for")

    skill_gap = st.text_input("Identified Skill Gaps (if any)", placeholder="e.g. Cloud Architecture, Stakeholder Management", key="onboard_skill_gap")

    # ── Document Upload & AI Verification ─────────────────────────────────
    st.divider()
    st.subheader("📄 Document Upload & AI Verification")
    st.markdown("Upload onboarding documents for AI-powered verification. Accepted: PDF, DOCX, TXT, PNG, JPG.")

    # Document checklist
    required_docs = ["Identity Proof (Aadhaar/PAN/Passport)", "Salary Slip / Compensation Proof", "Educational Certificates", "Experience / Relieving Letter"]

    if "onboard_verified_docs" not in st.session_state:
        st.session_state["onboard_verified_docs"] = []

    # Show checklist
    checklist_html = ""
    for doc_name in required_docs:
        verified = any(d["name"] == doc_name for d in st.session_state["onboard_verified_docs"])
        icon = "✅" if verified else "⬜"
        checklist_html += f'<div style="padding: 6px 0; color: {"#5eead4" if verified else "#94a3b8"}; font-weight: 600;">{icon} {doc_name}</div>'

    st.markdown(
        f'<div style="background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(15, 139, 141, 0.2); border-radius: 12px; padding: 16px; margin-bottom: 16px;">'
        f'<div style="color: #e2e8f0; font-weight: 800; margin-bottom: 8px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em;">Document Checklist</div>'
        f'{checklist_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Upload widget
    doc_category = st.selectbox("Document Category", required_docs + ["Other"], key="onboard_doc_category")
    uploaded_doc = st.file_uploader(
        "Upload Document",
        type=["pdf", "docx", "doc", "txt", "png", "jpg", "jpeg"],
        key="onboard_doc_upload",
    )

    if uploaded_doc and st.button("🔍 Verify with AI", key="verify_doc_btn", use_container_width=True):
        with st.spinner("AI is analyzing the document..."):
            try:
                files = {"file": (uploaded_doc.name, uploaded_doc.getvalue(), uploaded_doc.type)}
                resp = requests.post(
                    f"{API_BASE}/api/onboarding/verify-document",
                    headers=_auth_headers(),
                    files=files,
                    timeout=120,
                )
                resp.raise_for_status()
                result = resp.json()

                is_valid = result.get("is_valid", False)
                confidence = result.get("confidence", "Low")
                doc_type = result.get("document_type", "Unknown")
                details = result.get("details", "")

                if is_valid:
                    icon = "✅"
                    border_color = "#10b981"
                    status_text = "VERIFIED"
                elif confidence == "Medium":
                    icon = "⚠️"
                    border_color = "#f59e0b"
                    status_text = "NEEDS REVIEW"
                else:
                    icon = "❌"
                    border_color = "#ef4444"
                    status_text = "INVALID"

                st.markdown(
                    f"""<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid {border_color};
                                border-radius: 8px; padding: 16px; margin-top: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <span style="font-size: 1.2rem;">{icon}</span>
                                <strong style="color: #e2e8f0; margin-left: 8px;">{doc_type}</strong>
                            </div>
                            <span style="color: {border_color}; font-weight: 800; font-size: 0.8rem;">{status_text} — Confidence: {confidence}</span>
                        </div>
                        <p style="color: #94a3b8; margin: 8px 0 0 0; font-size: 0.9rem;">{details}</p>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # Track verified docs
                if is_valid:
                    doc_entry = {"name": doc_category, "type": doc_type, "file": uploaded_doc.name}
                    if not any(d["name"] == doc_category for d in st.session_state["onboard_verified_docs"]):
                        st.session_state["onboard_verified_docs"].append(doc_entry)

            except requests.ConnectionError:
                st.error("⚠️ Cannot connect to backend. Is the server running?")
            except requests.HTTPError as e:
                st.error(f"Verification error: {e.response.status_code} — {e.response.text}")

    # Show previously verified documents
    if st.session_state["onboard_verified_docs"]:
        st.markdown("#### ✅ Verified Documents")
        for idx, doc in enumerate(st.session_state["onboard_verified_docs"]):
            st.markdown(f"**{idx + 1}.** {doc['name']} — `{doc['file']}` ({doc['type']})")

    # ── Onboard Button ────────────────────────────────────────────────────
    st.divider()

    verified_count = len(st.session_state["onboard_verified_docs"])
    total_required = len(required_docs)

    if verified_count < total_required:
        st.warning(f"📋 {verified_count}/{total_required} required documents verified. You can still proceed with onboarding.")

    if st.button("🎓 Complete Onboarding", type="primary", use_container_width=True, key="onboard_convert_btn"):
        if not manager.strip():
            st.error("Please enter a Reporting Manager before onboarding.")
            return

        with st.spinner("Processing onboarding..."):
            payload = {
                "candidate_id": int(selected["ID"]),
                "employee_id": emp_id,
                "department": department,
                "manager": manager,
                "designation": designation,
                "location": location,
                "ready_for": ready_for,
                "skill_gap": skill_gap,
            }
            result = api_post("/api/onboarding/convert", payload)

            if result:
                st.success(f"🎉 **{selected['Candidate']}** has been successfully onboarded as **{emp_id}**!")

                emp_data = result.get("employee", {})
                st.markdown(
                    f"""<div style="background: linear-gradient(135deg, #064e3b 0%, #0f766e 100%);
                                border-radius: 12px; padding: 20px; margin-top: 12px;
                                border: 1px solid rgba(16, 185, 129, 0.3);">
                        <h3 style="color: #5eead4; margin: 0 0 12px 0;">✅ Onboarding Complete</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                            <div><span style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase;">Onboarding ID</span>
                                 <p style="color: #fff; font-weight: 700; margin: 2px 0;">{emp_id}</p></div>
                            <div><span style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase;">Name</span>
                                 <p style="color: #fff; font-weight: 700; margin: 2px 0;">{emp_data.get('employee', selected['Candidate'])}</p></div>
                            <div><span style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase;">Designation</span>
                                 <p style="color: #fff; font-weight: 700; margin: 2px 0;">{emp_data.get('current_role', designation)}</p></div>
                            <div><span style="color: #94a3b8; font-size: 0.75rem; text-transform: uppercase;">Department</span>
                                 <p style="color: #fff; font-weight: 700; margin: 2px 0;">{department}</p></div>
                        </div>
                        <p style="color: #a7f3d0; margin-top: 12px; font-size: 0.85rem;">
                            📍 Candidate successfully onboarded.
                        </p>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # Clear session state for next onboarding
                st.session_state["onboard_verified_docs"] = []

    # ── Previously Onboarded ──────────────────────────────────────────────
    if not onboarded.empty:
        st.divider()
        st.subheader("📋 Previously Onboarded Candidates")
        display_cols = [c for c in ["Candidate", "Role", "Location", "Experience", "Match", "Skills"] if c in onboarded.columns]
        st.dataframe(onboarded[display_cols], use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────


@st.dialog("User Profile")
def show_profile_dialog(user_name, user_role):
    st.write("### Edit Profile")
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Full Name", value=user_name)
        st.text_input("Phone Number", value="+1 (555) 123-4567")
    with col2:
        st.selectbox("Role", ["Recruiter"], index=0, disabled=True)
        st.text_input("Location", value="New York, NY")
    
    st.text_area("Professional Bio", value="Experienced professional passionate about building great teams and leveraging AI in HR.", height=100)
    
    st.divider()
    if st.button("Save Profile", type="primary", use_container_width=True):
        if new_name != user_name:
            st.session_state["user_name"] = new_name
        st.success("Profile updated successfully!")
        time.sleep(0.5)
        st.rerun()

@st.dialog("Notifications")
def show_notifications_dialog():
    st.markdown("### 🔔 Unread Notifications (3)")
    st.warning("**Action Required:** Please review the latest candidate applications for the Senior Engineer role.")
    st.info("**System Update:** New Copilot AI features were just released.")
    st.success("**Interview Scheduled:** You have an upcoming interview with John Doe tomorrow at 10:00 AM.")
    
    st.divider()
    if st.button("Mark all as read", use_container_width=True):
        st.success("All notifications marked as read.")
        time.sleep(0.5)
        st.rerun()

@st.dialog("Settings")
def show_settings_dialog():
    st.write("### ⚙️ Account Settings")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Appearance", "Notifications", "Privacy", "Integrations"])
    
    with tab1:
        st.write("#### Theme")
        st.radio("Color Theme", ["System Default", "Light Mode", "Dark Mode"], horizontal=True)
        st.write("#### Layout")
        st.toggle("Compact Sidebar", value=False)
        st.toggle("Show Avatar in Header", value=True)
        
    with tab2:
        st.write("#### Email Alerts")
        st.toggle("New Candidate Applications", value=True)
        st.toggle("Weekly Talent Reports", value=True)
        st.toggle("System Maintenance Updates", value=False)
        st.write("#### Push Notifications")
        st.toggle("Enable Desktop Notifications", value=True)
        
    with tab3:
        st.write("#### Data Sharing")
        st.toggle("Allow AI to learn from my usage", value=True)
        st.toggle("Share analytics with Infosys", value=False)
        st.write("#### Security")
        st.button("Change Password", use_container_width=True)
        st.button("Enable Two-Factor Authentication (2FA)", use_container_width=True)

    with tab4:
        st.write("#### 🔗 External Integrations")
        st.write("Link external apps like Google Workspace (Meet & Gmail) to automate interview scheduling.")
        email_input = st.text_input("Sender Email Address", value=st.session_state.get("saved_email", ""), placeholder="e.g. recruiter@gmail.com")
        pass_input = st.text_input("App Password", value=st.session_state.get("saved_pass", ""), type="password", help="Use an App Password, not your standard account password.")
        if st.button("Link Account", use_container_width=True):
            if email_input and pass_input:
                st.session_state["saved_email"] = email_input
                st.session_state["saved_pass"] = pass_input
                st.session_state["google_linked"] = True
                
                import dotenv
                dotenv.set_key(".env", "GOOGLE_WORKSPACE_EMAIL", email_input)
                dotenv.set_key(".env", "GOOGLE_WORKSPACE_PASSWORD", pass_input)
                
                st.success("Google Workspace account linked successfully!")
            else:
                st.error("Please enter both an email and app password.")
        
        if st.session_state.get("google_linked"):
            st.success("✅ Google Workspace is currently linked.")

    st.divider()
    if st.button("Save Preferences", type="primary", use_container_width=True):
        st.success("Settings saved successfully!")
        time.sleep(0.5)
        st.rerun()



def render_sidebar() -> str:
    user_role = st.session_state.get("user_role", "candidate")
    user_name = st.session_state.get("user_name", "User")
    


    st.sidebar.title("AI-Driven Smart Hiring Platform Copilot")

    pages = [
        "🏠 Overview",
        "📋 JD Analyser",
        "🔍 Find Candidates",
        "📄 Resume AI",
        "🗓️ Interviews",
        "🎓 Onboarding",
        "📊 Recruitment Insights",
        "📧 Communications",
        "📑 Reports",
        "🤖 Chat with AI",
    ]

    page = st.sidebar.radio("Main menu", pages, label_visibility="collapsed")

    st.sidebar.divider()
    
    initials = "".join([part[0].upper() for part in user_name.split() if part][:2])
    st.sidebar.markdown(
        clean_html(
            """
            
            """
        ),
        unsafe_allow_html=True,
    )

    with st.sidebar.container(border=True):
        st.markdown(
            clean_html(
                f"""
                <div class="sidebar-profile" title="View Profile">
                    <div class="user-avatar">{initials}</div>
                    <div class="sidebar-user-info">
                        <span class="sidebar-user-name">{user_name}</span>
                        <span class="sidebar-user-role">{user_role.title()}</span>
                    </div>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("👤", help="Profile", use_container_width=True):
                show_profile_dialog(user_name, user_role)
        with c2:
            if st.button("🔔", help="Notifications", use_container_width=True):
                show_notifications_dialog()
        with c3:
            if st.button("⚙️", help="Settings", use_container_width=True):
                show_settings_dialog()

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    return page


# ─────────────────────────────────────────────────────────────────────────────
# AUTH UI
# ─────────────────────────────────────────────────────────────────────────────


def render_login_page() -> bool:
    """Shows login/register UI. Returns True if user is now authenticated."""
    st.markdown(
        clean_html("""
        
        """),
        unsafe_allow_html=True,
    )

    # Use columns to constrain width and center the card
    spacer_left, content, spacer_right = st.columns([1, 1, 1])

    with content:
        with st.container(border=True):
            st.markdown('<div id="main-login-card-marker" style="display:none; height:0;"></div>', unsafe_allow_html=True)
            st.markdown(
                clean_html("""
                <div style="text-align:center;">
                    <div class="login-title">
                        AI-Driven Smart Hiring Platform Copilot
                    </div>
                    <div class="login-subtitle">
                        AI-Powered Recruitment
                    </div>
                    <h3 style="margin-top: 20px; margin-bottom: 0;">🔑 Login</h3>
                </div>
                """),
                unsafe_allow_html=True,
            )

            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

                if submitted and email and password:
                    result = api_post("/api/auth/login", {"email": email, "password": password})
                    if result and "access_token" in result:
                        st.session_state["token"] = result["access_token"]
                        st.session_state["user_role"] = result["role"]
                        st.session_state["user_name"] = result["user_name"]
                        st.session_state["user_id"] = result["user_id"]
                        st.rerun()

            st.markdown("""
                <div class="demo-box">
                    <b>Demo accounts:</b><br>
                    Recruiter: recruiter@infosys.com / recruiter123<br>
                </div>
            """, unsafe_allow_html=True)

    return False


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PUBLIC AI TEST
# ─────────────────────────────────────────────────────────────────────────────

def render_ai_test_page(token: str) -> None:
    st.markdown("<div class='ai-test-page'>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div class="brand-block" style="text-align: center; margin-bottom: 2rem;">
            <div class="brand-kicker">AI-Driven Smart Hiring Platform Copilot</div>
            <h1 class="brand-title">Candidate Assessment</h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Check if already submitted in this session
    if st.session_state.get(f"test_submitted_{token}", False):
        st.success("✅ Your test has been successfully submitted! The recruiting team will review your answers.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    with st.spinner("Loading test details..."):
        test_data = api_get(f"/api/ai-interview/test/{token}")
        
    if not test_data:
        st.error("Test not found or already completed. Please check your link.")
        st.markdown("</div>", unsafe_allow_html=True)
        return
        
    st.markdown(f"### Assessment for: **{test_data['role_name']}**")
    st.markdown(f"**Hello {test_data['candidate_name']},** please answer the following questions to the best of your ability.")
    st.caption(f"Difficulty: {test_data['difficulty']} | Focus: {test_data['focus_area']}")
    
    st.divider()
    
    questions = test_data.get("questions", [])
    
    with st.form("candidate-test-form"):
        answers = []
        for i, q in enumerate(questions):
            st.markdown(f"**Question {i+1} of {len(questions)}**")
            st.info(q)
            ans = st.text_area("Your Answer", height=150, key=f"ans_{i}")
            answers.append(ans)
            st.markdown("<br>", unsafe_allow_html=True)
            
        submit_test = st.form_submit_button("📤 Submit Assessment", type="primary", use_container_width=True)
        
    if submit_test:
        # Validate that all answers have some content
        if any(len(a.strip()) < 10 for a in answers):
            st.error("Please provide a meaningful answer (at least 10 characters) for all questions.")
        else:
            with st.spinner("Submitting answers..."):
                res = api_post(f"/api/ai-interview/submit/{token}", {"answers": answers})
                if res:
                    st.session_state[f"test_submitted_{token}"] = True
                    st.rerun()
                else:
                    st.error("Failed to submit test. Please try again.")
    
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    inject_css()

    # Route check for public test page BEFORE auth gate
    query_params = st.query_params
    if query_params.get("page") == "ai_test" and "token" in query_params:
        render_ai_test_page(query_params.get("token"))
        return

    # Auth gate — show login page if not authenticated
    if "token" not in st.session_state:
        render_login_page()
        return

    user_role = st.session_state.get("user_role", "recruiter")

    # Load data
    roles = load_roles()
    candidates = load_candidates()

    page = render_sidebar()

    if page != st.session_state.get('prev_page_name'):
        st.session_state['prev_page_name'] = page
        inject_loader()

    # ── Recruiter pages ───────────────────────────────────────

    if page == "🏠 Overview":
        render_command_center(roles, candidates)
    elif page == "🔍 Find Candidates":
        render_candidate_match(roles, candidates)
    elif page == "📋 JD Analyser":
        render_jd_analyser(roles, candidates)
    elif page == "📄 Resume AI":
        render_resume_ai(roles, candidates)
    elif page == "🗓️ Interviews":
        render_interview_desk(candidates, roles)
    elif page == "🎓 Onboarding":
        render_onboarding(roles, candidates)
    elif page == "📊 Recruitment Insights":
        render_recruitment_insights(roles, candidates)
    elif page == "📧 Communications":
        render_communications(candidates)
    elif page == "📑 Reports":
        render_reports(roles, candidates)
    elif page == "🤖 Chat with AI":
        render_ai_chat(candidates, roles, user_role=user_role)


if __name__ == "__main__":
    main()
