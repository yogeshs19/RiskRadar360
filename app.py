
import os
import re
import datetime
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import math

st.set_page_config(page_title="RiskRadar360", layout="wide")

def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "", name)

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
    # Build a 3x3 matrix counting risks per (L,I)
    grid = [[0,0,0],[0,0,0],[0,0,0]]
    for r in risk_rows:
        L = int(r["likelihood"])-1
        I = int(r["impact"])-1
        if 0 <= L < 3 and 0 <= I < 3:
            grid[L][I] += 1

    fig, ax = plt.subplots()
    ax.imshow(grid)
    # Annotate counts
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(grid[i][j]), ha="center", va="center")
    ax.set_xticks([0,1,2])
    ax.set_yticks([0,1,2])
    ax.set_xticklabels(["Impact 1","Impact 2","Impact 3"])
    ax.set_yticklabels(["Lik 1","Lik 2","Lik 3"])
    ax.set_title(title)
    st.pyplot(fig)

def render_radar(category_scores, title="Category Radar"):
    labels = list(category_scores.keys())
    values = [category_scores[k] for k in labels]
    N = len(labels)
    if N == 0:
        st.info("No category scores to plot.")
        return

    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    values += values[:1]
    angles += angles[:1]

    fig = plt.figure()
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, values)
    ax.fill(angles, values, alpha=0.25)
    ax.set_xticks([n / float(N) * 2 * math.pi for n in range(N)])
    ax.set_xticklabels(labels)
    ax.set_title(title)
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

# ---------------- Risk Definitions ----------------
# Each entry: (category, risk_name, question, risk_when_true, L, I, mitigation)
L10N_RISKS = [
    ("File Handling", "FTP used instead of Git", "Are handoffs still using FTP instead of Git?", True, 3, 3, "Switch all handoffs to Git; deprecate FTP"),
    ("Tooling", "Mixed HTTPS/SSH setup", "Is there a mixed HTTPS/SSH Git setup that may cause token/login failures?", True, 3, 2, "Standardize to HTTPS and document PAT setup"),
    ("Tooling", "Wrong clone URLs", "Are correct clone URLs guaranteed (no Gerrit admin URLs)?", False, 2, 3, "Provide canonical clone URL list; CI guardrails"),
    ("Quality", "Automation disabled", "Are automated checks (SourceChecker/TransChecker) enabled?", False, 2, 3, "Enable and gate on automated pre-checks"),
    ("Schedule", "Drops misaligned", "Are translation drops aligned with the sprint calendar?", False, 3, 3, "Publish drop calendar; align with PI planning"),
    ("Resources", "Screenshot bandwidth", "Is screenshot validation bandwidth planned (with vendor support)?", False, 2, 2, "Plan capacity; share build early; vendor assist"),
    ("Tooling", "Permissions missing", "Are all Git/Gerrit permissions granted pre-drop?", False, 2, 2, "Raise access requests early; track in KT docs"),
    ("File Handling", "Parser/encoding not standardized", "Are parser/encoding settings standardized (e.g., Passolo UTF-8)?", False, 2, 3, "Standardize and version parser configs"),
    ("Tooling", "ezL10n mapping absent", "Is the Git repo mapped for ezL10n automation?", False, 2, 3, "Map repo to ezL10n; validate jobs"),
]

LOCOPS_RISKS = [
    ("Tooling", "Pipeline instability", "Have pipelines been ≥95% green in the last 14 days?", False, 2, 3, "Blue/green runners; staggered rollout; rollback plan"),
    ("Tooling", "License server outage risk", "Are license servers monitored with alerting?", False, 2, 3, "Add HA; monitoring; vendor support"),
    ("Tooling", "Secrets management gaps", "Are credentials rotated and stored in a vault?", False, 2, 3, "Use secrets vault; rotation policy"),
    ("Tooling", "Parser regressions", "Are parser/plugin versions pinned with canary tests?", False, 2, 2, "Pin versions; canary pipelines; rollback artifact"),
    ("Tooling", "Staging/server availability", "Is staging/artifact server availability monitored?", False, 2, 3, "SLOs; uptime monitoring; escalation"),
    ("Resources", "Agent env drift", "Are build agents standardized (toolchain pinned)?", False, 2, 2, "Golden images; config mgmt; audits"),
    ("Knowledge", "Guardrails missing", "Are MR templates and required approvals enforced?", False, 2, 3, "Templates; protected branches; reviewers"),
    ("Knowledge", "Backup/restore gaps", "Are backups verified with periodic restore tests?", False, 2, 3, "Nightly backups; quarterly restore drills"),
    ("Tooling", "Monitoring SLAs", "Are monitoring SLAs (MTTD/MTTR) defined and met?", False, 2, 2, "Define SLAs; alert tuning; postmortems"),
]

GENERAL_RISKS = [
    ("Schedule", "Sprint misalignment", "Are milestones aligned with sprint/PI and dependencies tracked?", False, 3, 3, "Dependency board; early alignment"),
    ("Quality", "Missing reviews", "Are design/quality/accessibility reviews scheduled?", False, 2, 2, "Schedule formal reviews; checklist"),
    ("Knowledge", "Specs/KT gaps", "Are specs/KT complete and up-to-date?", False, 2, 3, "KT docs; owner assignment; versioning"),
    ("Tooling", "CI/CD & repo stability", "Are CI/CD and repo configs stable and documented?", False, 2, 3, "Harden CI; doc configs; change control"),
    ("Resources", "Bandwidth & time zones", "Are bandwidth and time zones planned into the schedule?", False, 2, 2, "Follow-the-sun plan; handoff SOP"),
    ("Stakeholders", "Signoffs missing", "Are early stakeholder signoffs scheduled and tracked?", False, 2, 2, "RACI; signoff gates"),
]

TAB_MAP = {
    "L10n": L10N_RISKS,
    "LocOps": LOCOPS_RISKS,
    "General": GENERAL_RISKS,
}

def assess_tab(tab_name):
    st.subheader(f"{tab_name} Project Risk Assessment")
    project = st.text_input("Project Name")
    version = st.text_input("Version / Release")
    assessor = st.text_input("Assessor (optional)", "")
    notes = st.text_area("Notes (optional)", "")
    today = datetime.date.today().strftime("%Y-%m-%d")
    st.caption(f"Assessment date: {today}")

    risk_rows = []
    categories = {}

    for (cat, rname, question, risk_when_true, L, I, mitigation) in TAB_MAP[tab_name]:
        if risk_when_true:
            ans = st.radio(question, ["No", "Yes"], horizontal=True, index=1)  # default "Yes"
            is_risk = (ans == "Yes")
        else:
            ans = st.radio(question, ["Yes", "No"], horizontal=True, index=0)  # default "Yes"
            is_risk = (ans == "No")

        likelihood = L if is_risk else 1
        impact = I if is_risk else 1
        score = likelihood * impact
        if is_risk:
            risk_rows.append({
                "project_name": project,
                "version": version,
                "assessment_date": today,
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

    overall = score_to_rating(risk_rows)
    st.markdown(f"### Overall Risk Rating: **{overall}**")

    c1, c2 = st.columns(2)
    with c1:
        render_heatmap(risk_rows)
    with c2:
        render_radar(categories)

    df = pd.DataFrame(risk_rows, columns=[
        "project_name","version","assessment_date","tab",
        "category","risk_name","likelihood","impact","score",
        "mitigation","assessor","notes"
    ])

    st.dataframe(df, use_container_width=True)

    if st.button(f"💾 Save Assessment ({tab_name})"):
        if not project or not version:
            st.error("Please enter Project Name and Version before saving.")
        else:
            path = save_results_csv(project, version, tab_name, df)
            st.success(f"Saved to {path}")

st.title("🌐 RiskRadar360")
st.caption("Cross-functional risk assessment & post-mortem tool (L10n • LocOps • General).")

tab_l10n, tab_locops, tab_general = st.tabs(["L10n", "LocOps", "General"])

with tab_l10n:
    assess_tab("L10n")

with tab_locops:
    assess_tab("LocOps")

with tab_general:
    assess_tab("General")
