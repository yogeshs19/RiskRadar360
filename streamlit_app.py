
# streamlit_app.py — RiskRadar360 (full + fixes: formatted defects summary, smaller heatmap)
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
    # Build 3x3 grid of counts
    grid = [[0,0,0],[0,0,0],[0,0,0]]
    for r in rows:
        try:
            P = int(r["possibility"]) - 1
            I = int(r["impact"]) - 1
        except Exception:
            continue
        if 0 <= P < 3 and 0 <= I < 3:
            grid[P][I] += 1

    # Smaller figure so it doesn't dominate the page
    fig, ax = plt.subplots(figsize=(4.5, 4.5), dpi=120)
    im = ax.imshow(grid, cmap="viridis")

    # Annotate cells
    for i in range(3):
        for j in range(3):
            val = grid[i][j]
            ax.text(j, i, str(val), ha="center", va="center",
                    color="white" if val > 0 else "black", fontsize=10)

    ax.set_xticks([0,1,2]); ax.set_yticks([0,1,2])
    ax.set_xticklabels(["Impact 1","Impact 2","Impact 3"], fontsize=9)
    ax.set_yticklabels(["Poss 1","Poss 2","Poss 3"], fontsize=9)
    ax.set_title(title, fontsize=13, pad=8)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=False)

SCALE_HELP_P = "1 = Low (unlikely), 2 = Medium (could happen), 3 = High (very likely)"
SCALE_HELP_I = "1 = Low (minor), 2 = Medium (some rework/delay), 3 = High (major disruption)"

# ---------- Risk Definitions ----------
# tuple: (category, risk_name, question, risk_when_true, P, I, mitigation, group)
L10N_RISKS = [
    ("File Handling", "FTP used instead of Git", "Are handoffs still using FTP instead of Git?", True, 3, 3, "Switch handoffs to Git; deprecate FTP", "Handoffs"),
    ("Tooling", "Mixed HTTPS/SSH setup", "Is there a mixed HTTPS/SSH Git setup that may cause token/login failures?", True, 3, 2, "Standardize to HTTPS; document PAT", "Repo Access"),
    ("Tooling", "Wrong clone URLs", "Are correct clone URLs guaranteed (no Gerrit admin URLs)?", False, 2, 3, "Publish canonical clone URLs; CI guardrails", "Repo Access"),
    ("Quality", "Automation disabled", "Are automated checks (SourceChecker/TransChecker) enabled?", False, 2, 3, "Enable and gate on checks", "Quality"),
    ("Schedule", "Drops misaligned", "Are translation drops aligned with the sprint calendar?", False, 3, 3, "Publish drop calendar; align with PI", "Schedule"),
    ("Resources", "Screenshot bandwidth", "Is screenshot validation bandwidth planned (with vendor support)?", False, 2, 2, "Plan capacity; early build share", "QA & Screens"),
    ("Tooling", "Permissions missing", "Are all Git/Gerrit permissions granted pre-drop?", False, 2, 2, "Raise access early; track in KT docs", "Repo Access"),
    ("File Handling", "Parser/encoding not standardized", "Are parser/encoding settings standardized (e.g., Passolo UTF-8)?", False, 2, 3, "Standardize and version configs", "Build/Parser"),
    ("Tooling", "ezL10n mapping absent", "Is the Git repo mapped for ezL10n automation?", False, 2, 3, "Map repo to ezL10n; validate jobs", "Automation"),
]

LOCOPS_RISKS = [
    ("Automation", "ezL10n repo mapping drift", "Is ezL10n mapping up-to-date for this repo & branch?", False, 3, 3, "Sync mappings; validate job paths", "ezL10n"),
    ("Automation", "ezL10n job health", "Have the last 10 ezL10n jobs succeeded (no chronic failures)?", False, 2, 3, "Fix chronic failures; canary job; alerts", "ezL10n"),
    ("Quality Gates", "SourceChecker coverage gaps", "Is SourceChecker enforced for all products in scope?", False, 2, 3, "Gate on SourceChecker; block failures", "SourceChecker"),
    ("Quality Gates", "Source placeholder risk", "Do SourceChecker rules include placeholder/escape checks?", False, 2, 2, "Enable placeholder/escape validations", "SourceChecker"),
    ("Quality Gates", "TransChecker not enforced", "Is TransChecker required for vendor handback?", False, 2, 3, "Run TransChecker pre-HB; reject failing packs", "TransChecker"),
    ("Quality Gates", "TM/term consistency checks", "Are TM & terminology consistency checks part of handback?", False, 2, 2, "Integrate term rules; update glossaries", "TransChecker"),
    ("DocOps", "DocOps staging failures", "Has the DocOps pipeline been green for staging in the last 2 weeks?", False, 2, 3, "Stabilize staging; retry policy; alerts", "DocOps"),
    ("DocOps", "Prod publish risk", "Is production publish tested with rollback artifacts?", False, 2, 3, "Add rollback build; run preflight", "DocOps"),
    ("SCA", "i18n SCA skipped", "Is the i18n static analysis part of CI for new features?", False, 2, 3, "Add SCA job; enforce pre-merge", "SCA"),
    ("SCA", "Hardcoded strings risk", "Are hardcoded string detections triaged within SLA?", False, 2, 2, "Triage dashboard; fix SLA", "SCA"),
    ("Screens", "SnapGen outdated", "Is the screenshot generator aligned to current builds & locales?", False, 2, 2, "Update SnapGen configs; smoke test", "SnapGen"),
    ("Screens", "Vendor screenshot validation", "Is vendor LQA process integrated with SnapGen output?", False, 2, 2, "Provide annotated packs; define acceptance", "SnapGen"),
    ("Infra", "License server SPOF", "Are Passolo/MT license servers redundant & monitored?", False, 2, 3, "Add HA; monitoring; vendor plan", "Licenses"),
    ("Security", "Secrets/token rotation overdue", "Are CI tokens & vendor creds rotated per policy?", False, 2, 3, "Use secrets vault; rotate; audit", "Secrets"),
    ("CI Runners", "Agent env drift", "Are build agents pinned (toolchain versions) & reproducible?", False, 2, 2, "Golden images; config mgmt; audits", "Runners"),
]

GENERAL_RISKS = [
    ("Schedule", "Sprint misalignment", "Are milestones aligned with sprint/PI and dependencies tracked?", False, 3, 3, "Dependency board; early alignment", "Planning"),
    ("Quality", "Missing reviews", "Are design/quality/accessibility reviews scheduled?", False, 2, 2, "Schedule formal reviews; checklist", "Quality"),
    ("Knowledge", "Specs/KT gaps", "Are specs/KT complete and up-to-date?", False, 2, 3, "KT docs; owner assignment; versioning", "Docs"),
    ("Tooling", "CI/CD & repo stability", "Are CI/CD and repo configs stable and documented?", False, 2, 3, "Harden CI; doc configs; change control", "Tooling"),
    ("Resources", "Bandwidth & time zones", "Are bandwidth and time zones planned into the schedule?", False, 2, 2, "Follow-the-sun plan; handoff SOP", "Resourcing"),
    ("Stakeholders", "Signoffs missing", "Are early stakeholder signoffs scheduled and tracked?", False, 2, 2, "RACI; signoff gates", "Stakeholders"),
]

TAB_DEF = {"L10n": L10N_RISKS, "LocOps": LOCOPS_RISKS, "General": GENERAL_RISKS}

def assess_tab(tab_name: str):
    top = st.container()
    with top:
        c1, c2, c3, c4 = st.columns([2,2,1,1])
        project = c1.text_input("Project", key=key_for(tab_name, "Project"))
        version = c2.text_input("Version", key=key_for(tab_name, "Version"))
        assessor = c3.text_input("Assessor", key=key_for(tab_name, "Assessor"))
        today = datetime.date.today().strftime("%Y-%m-%d")
        c4.markdown(f"**Date**: {today}")

    st.markdown("#### Weights & Advanced ⚙️")
    st.caption("Adjust how much each category contributes. Toggle **Advanced** to tune default Possibility (P) & Impact (I) per item.")
    wc1, wc2 = st.columns([3,1])
    with wc1:
        cats = sorted({c for (c, *_rest) in TAB_DEF[tab_name]} | {"Release","Quality Metrics","Process"})
        weights = {}
        wcols = st.columns(len(cats)) if cats else []
        for i, c in enumerate(cats):
            with wcols[i]:
                weights[c] = st.slider(c, 0.5, 2.0, 1.0, 0.1, key=key_for(tab_name, f"wt_{c}"))
    with wc2:
        show_adv = st.toggle("Advanced controls", value=True, key=key_for(tab_name, "adv"))

    left, right = st.columns([2,1])
    risk_rows = []
    red_flags = []

    # LEFT — checklist
    with left:
        st.markdown("### Checklist → Signals")
        for (cat, rname, question, risk_when_true, P, I, mitigation, group) in TAB_DEF[tab_name]:
            with st.container():
                cols = st.columns([5,2,2,3])
                default_yes = not risk_when_true
                ans = cols[0].radio(question, ["Yes","No"], index=0 if default_yes else 1, horizontal=True, key=key_for(tab_name, rname))
                item_P, item_I = P, I
                if show_adv:
                    item_P = cols[1].selectbox("Possibility (P)", [1,2,3], index=max(0, min(2, P-1)), key=key_for(tab_name, rname+"_P"))
                    item_I = cols[2].selectbox("Impact (I)", [1,2,3], index=max(0, min(2, I-1)), key=key_for(tab_name, rname+"_I"))
                cols[1].caption(SCALE_HELP_P); cols[2].caption(SCALE_HELP_I)
                evidence = cols[3].text_input("Evidence / link (optional)", key=key_for(tab_name, rname+"_evi"))
                # Risk logic
                is_risk = (ans == "No") if default_yes else (ans == "Yes")
                poss = int(item_P) if is_risk else 1
                impact = int(item_I) if is_risk else 1
                base_score = poss * impact
                weighted_score = round(base_score * weights.get(cat, 1.0), 1)
                if is_risk:
                    risk_rows.append({
                        "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                        "category": cat, "risk_name": rname, "possibility": poss, "impact": impact,
                        "score": base_score, "weighted_score": weighted_score, "mitigation": mitigation,
                        "evidence": evidence, "defects_summary": "", "assessor": assessor
                    })
                    if base_score >= 6:
                        red_flags.append((rname, cat, base_score, mitigation))

    # RIGHT — intelligence panel
    with right:
        st.markdown("### Intelligence Panel")
        st.markdown("##### Release tracker")
        rel_url = st.text_input("Release link (ValueEdge / Jira / other)", key=key_for(tab_name, "rel_url"))
        rel_status = st.selectbox("Gate status", ["Unknown","Draft","In progress","Ready","Blocked"], index=0, key=key_for(tab_name, "rel_status"))
        rel_date = st.date_input("Planned release date", key=key_for(tab_name, "rel_date"))
        st.caption("Link & status help validate scope/timing gates.")
        if rel_status in ["Unknown","Blocked"]:
            rname = "Release tracker unclear/blocked"; cat = "Release"
            P2, I2 = (2,3) if rel_status=="Unknown" else (3,3)
            base_score = P2*I2
            weighted_score = round(base_score * weights.get(cat, 1.0), 1)
            risk_rows.append({
                "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                "category": cat, "risk_name": rname, "possibility": P2, "impact": I2, "score": base_score,
                "weighted_score": weighted_score, "mitigation": "Clarify release scope/gates; unblock owners",
                "evidence": rel_url, "defects_summary": "", "assessor": assessor
            })
            red_flags.append((rname, cat, base_score, "Clarify release gates; unblock"))

        st.markdown("##### Ongoing defects")
        dcols = st.columns(4)
        sev_b = dcols[0].number_input("Blocker", 0, 999, 0, key=key_for(tab_name, "def_blocker"))
        sev_c = dcols[1].number_input("Critical", 0, 999, 0, key=key_for(tab_name, "def_critical"))
        sev_mj = dcols[2].number_input("Major", 0, 999, 0, key=key_for(tab_name, "def_major"))
        sev_mn = dcols[3].number_input("Minor", 0, 999, 0, key=key_for(tab_name, "def_minor"))
        defect_score = sev_b*6 + sev_c*4 + sev_mj*2 + sev_mn*1
        if defect_score >= 12:
            cat = "Quality Metrics"; rname = "High defect load"
            P3, I3 = (3,3) if sev_b>0 or sev_c>2 else (2,3)
            base_score = P3*I3
            weighted_score = round(base_score * weights.get(cat, 1.0), 1)
            defects_summary = f"Blocker={sev_b}, Critical={sev_c}, Major={sev_mj}, Minor={sev_mn}"
            risk_rows.append({
                "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                "category": cat, "risk_name": rname, "possibility": P3, "impact": I3, "score": base_score,
                "weighted_score": weighted_score, "mitigation": "Focus blocker/critical burndown; triage",
                "evidence": "", "defects_summary": defects_summary, "assessor": assessor
            })
            red_flags.append((rname, cat, base_score, "Blocker/critical burndown"))

        st.markdown("##### Links & artifacts")
        st.text_input("Git/Gerrit repo URL", key=key_for(tab_name, "link_repo"))
        st.text_input("CI pipeline URL", key=key_for(tab_name, "link_ci"))
        st.text_input("Spec/Confluence URL", key=key_for(tab_name, "link_spec"))

    # Summary
    st.markdown("---")
    total_score = sum(r["score"] for r in risk_rows)
    max_cell = max((r["score"] for r in risk_rows), default=0)
    rating = score_to_rating(total_score, max_cell)
    sL, sR = st.columns([1,1])
    with sL:
        st.subheader(f"Summary — {rating}")
        st.write(f"High‑risk items (≥7): {sum(1 for r in risk_rows if r['score']>=7)}")
        st.write(f"Weighted score: {int(sum(r['weighted_score'] for r in risk_rows))}")
    with sR:
        plot_heatmap(risk_rows)

    st.markdown("### 🔴 Red Flags (auto)")
    if red_flags:
        for name, cat, s, mit in sorted(red_flags, key=lambda x: x[2], reverse=True)[:5]:
            st.markdown(f"- **{name}** in *{cat}* — score {s} → _Mitigation:_ {mit}")
    else:
        st.info("No red flags identified.")

    cols = ["project_name","version","assessment_date","tab","category","risk_name","possibility","impact","score","weighted_score","mitigation","evidence","defects_summary","assessor"]
    df = pd.DataFrame(risk_rows, columns=cols)
    display_cols = {"possibility":"Possibility (P)", "impact":"Impact (I)"}
    st.dataframe(df.rename(columns=display_cols), use_container_width=True)

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
