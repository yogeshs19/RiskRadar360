
# streamlit_app.py — RiskRadar360 (Corrected: possibility rename, defects_summary fix)
import os, re, datetime
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

st.set_page_config(page_title="RiskRadar360", layout="wide")

# ---------- Helpers ----------
def sanitize_filename(name: str) -> str:
    name = name.strip().replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "", name)

def key_for(tab: str, name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", name)
    return f"{tab}_{safe}"

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

def score_to_rating(total_score: int, max_cell: int) -> str:
    if max_cell >= 7:
        return "High"
    elif total_score >= 12:
        return "Medium"
    else:
        return "Low"

def plot_heatmap(rows, title="Risk Matrix (Possibility × Impact)"):
    grid = [[0,0,0],[0,0,0],[0,0,0]]
    for r in rows:
        P = int(r["possibility"])-1
        I = int(r["impact"])-1
        if 0 <= P < 3 and 0 <= I < 3:
            grid[P][I] += 1
    fig, ax = plt.subplots()
    ax.imshow(grid)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(grid[i][j]), ha="center", va="center")
    ax.set_xticks([0,1,2]); ax.set_yticks([0,1,2])
    ax.set_xticklabels(["Impact 1","Impact 2","Impact 3"])
    ax.set_yticklabels(["Poss 1","Poss 2","Poss 3"])
    ax.set_title(title)
    st.pyplot(fig)

# ---------- Risks (simplified for demo) ----------
L10N_RISKS = [
    ("Quality", "Automation disabled", "Are automated checks enabled?", False, 2, 3, "Enable checks", "Quality"),
    ("Resources", "Screenshot bandwidth", "Is screenshot validation bandwidth planned?", False, 2, 2, "Plan capacity", "QA"),
]

LOCOPS_RISKS = [
    ("Automation", "ezL10n repo mapping drift", "Is ezL10n mapping up-to-date?", False, 3, 3, "Sync mappings", "ezL10n"),
]

GENERAL_RISKS = [
    ("Schedule", "Sprint misalignment", "Are milestones aligned with sprint?", False, 3, 3, "Align milestones", "Planning"),
]

TAB_DEF = {"L10n": L10N_RISKS, "LocOps": LOCOPS_RISKS, "General": GENERAL_RISKS}

SCALE_HELP_P = "1 = Low (unlikely), 2 = Medium (could happen), 3 = High (very likely)"
SCALE_HELP_I = "1 = Low (minor), 2 = Medium (some delay), 3 = High (major disruption)"

def assess_tab(tab_name: str):
    project = st.text_input("Project", key=key_for(tab_name, "Project"))
    version = st.text_input("Version", key=key_for(tab_name, "Version"))
    assessor = st.text_input("Assessor", key=key_for(tab_name, "Assessor"))
    today = datetime.date.today().strftime("%Y-%m-%d")

    st.markdown("### Checklist")
    risk_rows = []
    for (cat, rname, question, risk_when_true, P, I, mitigation, group) in TAB_DEF[tab_name]:
        cols = st.columns([5,2,2,3])
        ans = cols[0].radio(question, ["Yes","No"], index=0, horizontal=True, key=key_for(tab_name, rname))
        item_P = cols[1].selectbox("Possibility (P)", [1,2,3], index=P-1, key=key_for(tab_name, rname+"_P"))
        item_I = cols[2].selectbox("Impact (I)", [1,2,3], index=I-1, key=key_for(tab_name, rname+"_I"))
        cols[1].caption(SCALE_HELP_P); cols[2].caption(SCALE_HELP_I)
        evidence = cols[3].text_input("Evidence / link (optional)", key=key_for(tab_name, rname+"_evi"))
        is_risk = (ans == "No")
        poss = int(item_P) if is_risk else 1
        impact = int(item_I) if is_risk else 1
        base_score = poss * impact
        weighted_score = round(base_score, 1)
        if is_risk:
            risk_rows.append({
                "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                "category": cat, "risk_name": rname, "possibility": poss, "impact": impact,
                "score": base_score, "weighted_score": weighted_score, "mitigation": mitigation,
                "evidence": evidence, "defects_summary": "", "assessor": assessor
            })

    # Data output
    cols = ["project_name","version","assessment_date","tab","category","risk_name","possibility","impact","score","weighted_score","mitigation","evidence","defects_summary","assessor"]
    df = pd.DataFrame(risk_rows, columns=cols)
    display_cols = {
        "possibility":"Possibility (P)",
        "impact":"Impact (I)"
    }
    df_display = df.rename(columns=display_cols)
    st.dataframe(df_display, use_container_width=True)

    if project and version and not df.empty:
        path = save_results_csv(project, version, tab_name, df)
        st.download_button("⬇️ Download CSV", data=df.to_csv(index=False).encode("utf-8"),
                           file_name=os.path.basename(path), mime="text/csv", key=key_for(tab_name, "dl"))
    elif not project or not version:
        st.warning("Enter Project & Version to enable CSV download.")

tabs = st.tabs(["L10n", "LocOps", "General"])
with tabs[0]: assess_tab("L10n")
with tabs[1]: assess_tab("LocOps")
with tabs[2]: assess_tab("General")
