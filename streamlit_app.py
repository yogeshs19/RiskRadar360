
# streamlit_app.py — RiskRadar360 (final, newline-safe & unique keys)
import os, re, datetime, math
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

st.set_page_config(page_title="RiskRadar360", layout="wide")

# ---- Helpers ----
def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "", name)

def key_for(tab: str, name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    return f"{tab}_{safe}"

def score_to_rating(risk_rows):
    max_cell = max((row["score"] for row in risk_rows), default=0)
    total = sum(row["score"] for row in risk_rows)
    if max_cell >= 7:
        return "High"
    elif total >= 12:
        return "Medium"
    else:
        return "Low"

def render_heatmap(risk_rows, title="Risk Matrix (Likelihood × Impact)"):
    grid = [[0,0,0],[0,0,0],[0,0,0]]
    for r in risk_rows:
        L = int(r["likelihood"]) - 1
        I = int(r["impact"]) - 1
        if 0 <= L < 3 and 0 <= I < 3:
            grid[L][I] += 1
    fig, ax = plt.subplots()
    ax.imshow(grid)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(grid[i][j]), ha="center", va="center")
    ax.set_xticks([0,1,2]); ax.set_yticks([0,1,2])
    ax.set_xticklabels(["Impact 1","Impact 2","Impact 3"])
    ax.set_yticklabels(["Lik 1","Lik 2","Lik 3"])
    ax.set_title(title)
    st.pyplot(fig)

def render_radar(category_scores, title="Category Radar"):
    labels = list(category_scores.keys())
    values = [category_scores.get(k,0) for k in labels]
    N = len(labels)
    if N == 0:
        st.info("No category scores to plot.")
        return
    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    values += values[:1]; angles += angles[:1]
    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, values); ax.fill(angles, values, alpha=0.25)
    ax.set_xticks([n / float(N) * 2 * math.pi for n in range(N)])
    ax.set_xticklabels(labels); ax.set_title(title)
    st.pyplot(fig)

def ensure_results_dir():
    out_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

def save_results_csv(project, version, tab, df):
    out_dir = ensure_results_dir()
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    fname = f"{sanitize_filename(project)}_{sanitize_filename(version)}_{date_str}_{sanitize_filename(tab)}.csv"
    path = os.path.join(out_dir, fname)
    df.to_csv(path, index=False, encoding="utf-8")
    return path

# ---- Risk Definitions ----
# (category, risk_name, question, risk_when_true, L, I, mitigation, group)
L10N_RISKS = [
    ("File Handling", "FTP used instead of Git", "Are handoffs still using FTP instead of Git?", True, 3, 3, "Switch all handoffs to Git; deprecate FTP", "File Handling"),
    ("Tooling", "Mixed HTTPS/SSH setup", "Is there a mixed HTTPS/SSH Git setup that may cause token/login failures?", True, 3, 2, "Standardize to HTTPS and document PAT setup", "Tooling"),
    ("Tooling", "Wrong clone URLs", "Are correct clone URLs guaranteed (no Gerrit admin URLs)?", False, 2, 3, "Provide canonical clone URL list; CI guardrails", "Tooling"),
    ("Quality", "Automation disabled", "Are automated checks (SourceChecker/TransChecker) enabled?", False, 2, 3, "Enable and gate on automated pre-checks", "Quality"),
    ("Schedule", "Drops misaligned", "Are translation drops aligned with the sprint calendar?", False, 3, 3, "Publish drop calendar; align with PI planning", "Schedule"),
    ("Resources", "Screenshot bandwidth", "Is screenshot validation bandwidth planned (with vendor support)?", False, 2, 2, "Plan capacity; share build early; vendor assist", "Resources"),
    ("Tooling", "Permissions missing", "Are all Git/Gerrit permissions granted pre-drop?", False, 2, 2, "Raise access requests early; track in KT docs", "Tooling"),
    ("File Handling", "Parser/encoding not standardized", "Are parser/encoding settings standardized (e.g., Passolo UTF-8)?", False, 2, 3, "Standardize and version parser configs", "File Handling"),
    ("Tooling", "ezL10n mapping absent", "Is the Git repo mapped for ezL10n automation?", False, 2, 3, "Map repo to ezL10n; validate jobs", "Tooling"),
]

LOCOPS_RISKS = [
    ("Tooling", "Pipeline instability", "Have pipelines been ≥95% green in the last 14 days?", False, 2, 3, "Blue/green runners; staggered rollout; rollback plan", "Tooling"),
    ("Tooling", "License server outage risk", "Are license servers monitored with alerting?", False, 2, 3, "Add HA; monitoring; vendor support", "Tooling"),
    ("Tooling", "Secrets management gaps", "Are credentials rotated and stored in a vault?", False, 2, 3, "Use secrets vault; rotation policy", "Tooling"),
    ("Tooling", "Parser regressions", "Are parser/plugin versions pinned with canary tests?", False, 2, 2, "Pin versions; canary pipelines; rollback artifact", "Tooling"),
    ("Tooling", "Staging/server availability", "Is staging/artifact server availability monitored?", False, 2, 3, "SLOs; uptime monitoring; escalation", "Tooling"),
    ("Resources", "Agent env drift", "Are build agents standardized (toolchain pinned)?", False, 2, 2, "Golden images; config mgmt; audits", "Resources"),
    ("Knowledge", "Guardrails missing", "Are MR templates and required approvals enforced?", False, 2, 3, "Templates; protected branches; reviewers", "Knowledge"),
    ("Knowledge", "Backup/restore gaps", "Are backups verified with periodic restore tests?", False, 2, 3, "Nightly backups; quarterly restore drills", "Knowledge"),
    ("Tooling", "Monitoring SLAs", "Are monitoring SLAs (MTTD/MTTR) defined and met?", False, 2, 2, "Define SLAs; alert tuning; postmortems", "Tooling"),
]

GENERAL_RISKS = [
    ("Schedule", "Sprint misalignment", "Are milestones aligned with sprint/PI and dependencies tracked?", False, 3, 3, "Dependency board; early alignment", "Schedule"),
    ("Quality", "Missing reviews", "Are design/quality/accessibility reviews scheduled?", False, 2, 2, "Schedule formal reviews; checklist", "Quality"),
    ("Knowledge", "Specs/KT gaps", "Are specs/KT complete and up-to-date?", False, 2, 3, "KT docs; owner assignment; versioning", "Knowledge"),
    ("Tooling", "CI/CD & repo stability", "Are CI/CD and repo configs stable and documented?", False, 2, 3, "Harden CI; doc configs; change control", "Tooling"),
    ("Resources", "Bandwidth & time zones", "Are bandwidth and time zones planned into the schedule?", False, 2, 2, "Follow-the-sun plan; handoff SOP", "Resources"),
    ("Stakeholders", "Signoffs missing", "Are early stakeholder signoffs scheduled and tracked?", False, 2, 2, "RACI; signoff gates", "Stakeholders"),
]

TAB_DEF = {"L10n": L10N_RISKS, "LocOps": LOCOPS_RISKS, "General": GENERAL_RISKS}

# ---- Core Tab Function ----
def assess_tab(tab_name: str):
    st.markdown(f"## {tab_name} Project Risk Assessment")

    with st.form(key=key_for(tab_name, "Form")):
        c1, c2, c3 = st.columns([2,2,1])
        project = c1.text_input("Project Name", key=key_for(tab_name, "ProjectName"))
        version = c2.text_input("Version / Release", key=key_for(tab_name, "Version"))
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        c3.markdown("**Date**\n" + date_str)  # explicit newline
        assessor = st.text_input("Assessor (optional)", "", key=key_for(tab_name, "Assessor"))
        notes = st.text_area("Notes (optional)", "", key=key_for(tab_name, "Notes"))
        st.markdown("---")

        risk_rows = []
        categories = {}

        def ask(question, default_yes: bool, L: int, I: int, rname: str, cat: str, mitigation: str):
            default_index = 0 if default_yes else 1  # "Yes" by default if default_yes else "No"
            ans = st.radio(question, ["Yes","No"], index=default_index, horizontal=True, key=key_for(tab_name, rname))
            is_risk = (ans == "No") if default_yes else (ans == "Yes")
            likelihood = L if is_risk else 1
            impact = I if is_risk else 1
            score = likelihood * impact
            if is_risk:
                risk_rows.append({
                    "project_name": project,
                    "version": version,
                    "assessment_date": date_str,
                    "tab": tab_name,
                    "category": cat,
                    "risk_name": rname,
                    "likelihood": likelihood,
                    "impact": impact,
                    "score": score,
                    "mitigation": mitigation,
                    "assessor": assessor,
                    "notes": notes,
                })
            categories[cat] = categories.get(cat, 0) + score

        # Ask all questions
        for (cat, rname, question, risk_when_true, L, I, mitigation, group) in TAB_DEF[tab_name]:
            default_yes = not risk_when_true
            ask(question, default_yes, L, I, rname, cat, mitigation)

        submitted = st.form_submit_button(f"Calculate & Save ({tab_name})", use_container_width=True)

    if submitted:
        overall = score_to_rating(risk_rows)
        high_count = sum(1 for r in risk_rows if r["score"] >= 7)
        total_score = sum(r["score"] for r in risk_rows)

        cA, cB, cC = st.columns(3)
        cA.metric("Overall Rating", overall)
        cB.metric("High-Risk Items (≥7)", high_count)
        cC.metric("Total Score", total_score)

        st.markdown("---")
        left, right = st.columns(2)
        with left: render_heatmap(risk_rows)
        with right: render_radar(categories)

        df = pd.DataFrame(risk_rows, columns=[
            "project_name","version","assessment_date","tab",
            "category","risk_name","likelihood","impact","score",
            "mitigation","assessor","notes"
        ])
        st.dataframe(df, use_container_width=True)

        if project and version:
            path = save_results_csv(project, version, tab_name, df)
            st.success(f"Saved to {path}")
            st.download_button("⬇️ Download CSV", data=df.to_csv(index=False).encode("utf-8"),
                               file_name=os.path.basename(path), mime="text/csv", key=key_for(tab_name, "Download"))
        else:
            st.error("Please provide Project Name and Version to save.")

# ---- App ----
st.markdown("# 🌐 RiskRadar360")
st.caption("Cross-functional risk assessment & post‑mortem tool (L10n • LocOps • General).")

tab_l10n, tab_locops, tab_general = st.tabs(["L10n", "LocOps", "General"])
with tab_l10n:
    assess_tab("L10n")
with tab_locops:
    assess_tab("LocOps")
with tab_general:
    assess_tab("General")
