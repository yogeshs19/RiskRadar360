
# streamlit_app.py — RiskRadar360 (Right‑Panel Intelligence Edition)
import os, re, datetime, math
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

st.set_page_config(page_title="RiskRadar360", layout="wide")

# ---------- Styles ----------
st.markdown(
    """
    <style>
    .rr-hero {background: linear-gradient(90deg, #2563eb, #06b6d4); padding: 20px 24px; border-radius: 16px; color: white; margin-bottom: 14px;}
    .rr-hero h1 {margin: 0; font-size: 28px;}
    .rr-hero p {margin: 6px 0 0 0; opacity: 0.95;}
    .rr-card {border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: #ffffff; box-shadow: 0 2px 12px rgba(0,0,0,0.04); margin-bottom: 14px;}
    .rr-metric { font-size: 24px; font-weight: 700; }
    .rr-muted { color: #475569; }
    .rr-badge { display:inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; margin-left: 8px; }
    .rr-badge.high { background:#fee2e2; color:#991b1b; }
    .rr-badge.medium { background:#fef3c7; color:#92400e; }
    .rr-badge.low { background:#dcfce7; color:#166534; }
    .rr-pill { display:inline-block; padding: 2px 8px; border-radius: 10px; background:#f1f5f9; margin-right:6px; font-size:12px;}
    </style>
    """, unsafe_allow_html=True
)

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

def plot_heatmap(rows, title="Risk Matrix (Likelihood × Impact)"):
    grid = [[0,0,0],[0,0,0],[0,0,0]]
    for r in rows:
        L = int(r["likelihood"])-1; I = int(r["impact"])-1
        if 0 <= L < 3 and 0 <= I < 3: grid[L][I] += 1
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

def plot_defects_bar(def_counts):
    fig, ax = plt.subplots()
    labels = list(def_counts.keys()); values = [def_counts[k] for k in labels]
    ax.bar(labels, values)
    ax.set_title("Defects snapshot")
    st.pyplot(fig)

def plot_scatter(rows, title="Risk Scatter (L vs I)"):
    if not rows:
        st.info("No risks to plot."); return
    x = [r["impact"] for r in rows]
    y = [r["likelihood"] for r in rows]
    labels = [r["risk_name"] for r in rows]
    fig, ax = plt.subplots()
    ax.scatter(x, y)
    for i, label in enumerate(labels):
        ax.annotate(label, (x[i]+0.03, y[i]+0.03), fontsize=8)
    ax.set_xlabel("Impact"); ax.set_ylabel("Likelihood"); ax.set_xlim(0.8,3.2); ax.set_ylim(0.8,3.2)
    ax.set_title(title)
    st.pyplot(fig)

# ---------- Risk Definitions ----------
# (category, risk_name, question, risk_when_true, L, I, mitigation, group)
L10N_RISKS = [
    ("File Handling", "FTP used instead of Git", "Are handoffs still using FTP instead of Git?", True, 3, 3, "Switch all handoffs to Git; deprecate FTP", "Handoffs"),
    ("Tooling", "Mixed HTTPS/SSH setup", "Is there a mixed HTTPS/SSH Git setup that may cause token/login failures?", True, 3, 2, "Standardize to HTTPS and document PAT setup", "Repo Access"),
    ("Tooling", "Wrong clone URLs", "Are correct clone URLs guaranteed (no Gerrit admin URLs)?", False, 2, 3, "Provide canonical clone URL list; CI guardrails", "Repo Access"),
    ("Quality", "Automation disabled", "Are automated checks (SourceChecker/TransChecker) enabled?", False, 2, 3, "Enable and gate on automated pre-checks", "Quality"),
    ("Schedule", "Drops misaligned", "Are translation drops aligned with the sprint calendar?", False, 3, 3, "Publish drop calendar; align with PI planning", "Schedule"),
    ("Resources", "Screenshot bandwidth", "Is screenshot validation bandwidth planned (with vendor support)?", False, 2, 2, "Plan capacity; share build early; vendor assist", "QA & Screens"),
    ("Tooling", "Permissions missing", "Are all Git/Gerrit permissions granted pre-drop?", False, 2, 2, "Raise access requests early; track in KT docs", "Repo Access"),
    ("File Handling", "Parser/encoding not standardized", "Are parser/encoding settings standardized (e.g., Passolo UTF-8)?", False, 2, 3, "Standardize and version parser configs", "Build/Parser"),
    ("Tooling", "ezL10n mapping absent", "Is the Git repo mapped for ezL10n automation?", False, 2, 3, "Map repo to ezL10n; validate jobs", "Automation"),
]

LOCOPS_RISKS = [
    ("Tooling", "Pipeline instability", "Have pipelines been ≥95% green in the last 14 days?", False, 2, 3, "Blue/green runners; staggered rollout; rollback plan", "CI Health"),
    ("Tooling", "License server outage risk", "Are license servers monitored with alerting?", False, 2, 3, "Add HA; monitoring; vendor support", "Infra"),
    ("Tooling", "Secrets management gaps", "Are credentials rotated and stored in a vault?", False, 2, 3, "Use secrets vault; rotation policy", "Security"),
    ("Tooling", "Parser regressions", "Are parser/plugin versions pinned with canary tests?", False, 2, 2, "Pin versions; canary pipelines; rollback artifact", "Build/Parser"),
    ("Tooling", "Staging/server availability", "Is staging/artifact server availability monitored?", False, 2, 3, "SLOs; uptime monitoring; escalation", "Infra"),
    ("Resources", "Agent env drift", "Are build agents standardized (toolchain pinned)?", False, 2, 2, "Golden images; config mgmt; audits", "CI Health"),
    ("Knowledge", "Guardrails missing", "Are MR templates and required approvals enforced?", False, 2, 3, "Templates; protected branches; reviewers", "Process/Policy"),
    ("Knowledge", "Backup/restore gaps", "Are backups verified with periodic restore tests?", False, 2, 3, "Nightly backups; quarterly restore drills", "Infra"),
    ("Tooling", "Monitoring SLAs", "Are monitoring SLAs (MTTD/MTTR) defined and met?", False, 2, 2, "Define SLAs; alert tuning; postmortems", "SRE/Monitoring"),
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

# ---------- App Header ----------
st.markdown('<div class="rr-hero"><h1>RiskRadar360</h1><p>Modern pre‑mortem dashboard for L10n • LocOps • General</p></div>', unsafe_allow_html=True)

# ---------- Assess Page ----------
def assess_tab(tab_name: str):
    top = st.container()
    with top:
        c1, c2, c3, c4 = st.columns([2,2,1,1])
        project = c1.text_input("Project", key=key_for(tab_name, "Project"))
        version = c2.text_input("Version", key=key_for(tab_name, "Version"))
        assessor = c3.text_input("Assessor", key=key_for(tab_name, "Assessor"))
        today = datetime.date.today().strftime("%Y-%m-%d")
        c4.markdown(f"<div class='rr-card'><div class='rr-muted'>Date</div><div class='rr-metric'>{today}</div></div>", unsafe_allow_html=True)

    # Weights row
    st.markdown("#### Weights & Advanced")
    wc1, wc2 = st.columns([3,1])
    with wc1:
        cats = sorted({c for (c, *_rest) in TAB_DEF[tab_name]} | {"Release","Quality Metrics","Process"})
        weights = {}
        wcols = st.columns(len(cats)) if len(cats)>0 else []
        for i, c in enumerate(cats):
            with wcols[i]:
                weights[c] = st.slider(c, 0.5, 2.0, 1.0, 0.1, key=key_for(tab_name, f"wt_{c}"))
    with wc2:
        show_adv = st.toggle("Advanced controls", value=True, key=key_for(tab_name, "adv"))

    # Main: left checklist, right intelligence panel
    left, right = st.columns([2,1])
    risk_rows = []
    categories_scores = {}
    red_flags = []

    # LEFT — questions
    with left:
        st.markdown("### Checklist → Signals")
        for (cat, rname, question, risk_when_true, L, I, mitigation, group) in TAB_DEF[tab_name]:
            with st.container():
                cols = st.columns([5,2,2,3])
                default_yes = not risk_when_true
                default_index = 0 if default_yes else 1
                ans = cols[0].radio(question, ["Yes","No"], index=default_index, horizontal=True, key=key_for(tab_name, rname))
                item_L, item_I = L, I
                if show_adv:
                    item_L = cols[1].selectbox("L", [1,2,3], index=L-1, key=key_for(tab_name, rname+"_L"))
                    item_I = cols[2].selectbox("I", [1,2,3], index=I-1, key=key_for(tab_name, rname+"_I"))
                evidence = cols[3].text_input("Evidence / link (optional)", key=key_for(tab_name, rname+"_evi"))
                is_risk = (ans == "No") if default_yes else (ans == "Yes")
                likelihood = int(item_L) if is_risk else 1
                impact = int(item_I) if is_risk else 1
                base_score = likelihood * impact
                weighted_score = base_score * weights.get(cat, 1.0)
                categories_scores[cat] = categories_scores.get(cat, 0) + weighted_score
                if is_risk:
                    risk_rows.append({
                        "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                        "category": cat, "risk_name": rname, "likelihood": likelihood, "impact": impact,
                        "score": base_score, "weighted_score": weighted_score, "mitigation": mitigation,
                        "evidence": evidence, "assessor": assessor
                    })
                    if base_score >= 6: red_flags.append((rname, cat, base_score, mitigation))

    # RIGHT — intelligence panel
    with right:
        st.markdown("### Intelligence Panel")
        # Release Tracker (ValueEdge or similar)
        st.markdown("##### Release tracker")
        rel_url = st.text_input("Release link (ValueEdge / Jira / other)", key=key_for(tab_name, "rel_url"))
        rel_status = st.selectbox("Gate status", ["Unknown","Draft","In progress","Ready","Blocked"], index=0, key=key_for(tab_name, "rel_status"))
        rel_date = st.date_input("Planned release date", key=key_for(tab_name, "rel_date"))
        st.caption("Link and status help reviewers validate scope & timing gates.")
        if rel_status in ["Unknown","Blocked"]:
            # add risk
            rname = "Release tracker unclear/blocked"
            cat = "Release"
            L, I = (2,3) if rel_status=="Unknown" else (3,3)
            base_score = L*I
            weighted_score = base_score * weights.get(cat, 1.0)
            risk_rows.append({
                "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                "category": cat, "risk_name": rname, "likelihood": L, "impact": I, "score": base_score,
                "weighted_score": weighted_score, "mitigation": "Clarify release scope/gates; unblock owners", "evidence": rel_url, "assessor": assessor
            })
            categories_scores[cat] = categories_scores.get(cat, 0) + weighted_score
            red_flags.append((rname, cat, base_score, "Clarify release gates; unblock"))

        # Defects snapshot
        st.markdown("##### Ongoing defects")
        dcols = st.columns(4)
        sev_b = dcols[0].number_input("Blocker", 0, 999, 0, key=key_for(tab_name, "def_blocker"))
        sev_c = dcols[1].number_input("Critical", 0, 999, 0, key=key_for(tab_name, "def_critical"))
        sev_mj = dcols[2].number_input("Major", 0, 999, 0, key=key_for(tab_name, "def_major"))
        sev_mn = dcols[3].number_input("Minor", 0, 999, 0, key=key_for(tab_name, "def_minor"))
        def_counts = {"Blocker":sev_b, "Critical":sev_c, "Major":sev_mj, "Minor":sev_mn}
        plot_defects_bar(def_counts)
        defect_score = sev_b*6 + sev_c*4 + sev_mj*2 + sev_mn*1
        if defect_score >= 12:
            cat = "Quality Metrics"; rname = "High defect load"
            L, I = (3,3) if sev_b>0 or sev_c>2 else (2,3)
            base_score = L*I; weighted_score = base_score * weights.get(cat, 1.0)
            risk_rows.append({
                "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                "category": cat, "risk_name": rname, "likelihood": L, "impact": I, "score": base_score,
                "weighted_score": weighted_score, "mitigation": "Focus on blocker/critical burndown; triage; freeze risky areas", "evidence": str(def_counts), "assessor": assessor
            })
            categories_scores[cat] = categories_scores.get(cat, 0) + weighted_score
            red_flags.append((rname, cat, base_score, "Blocker/critical burndown"))

        # Process clarifications / gates
        st.markdown("##### Process gates")
        g1 = st.checkbox("String freeze declared", key=key_for(tab_name, "gate_freeze"))
        g2 = st.checkbox("Pseudolocalization passed", key=key_for(tab_name, "gate_pseudo"))
        g3 = st.checkbox("ICU/plurals coverage confirmed", key=key_for(tab_name, "gate_icu"))
        g4 = st.checkbox("RTL/BiDi support validated (if applicable)", key=key_for(tab_name, "gate_bidi"))
        g5 = st.checkbox("Font/glyph readiness verified", key=key_for(tab_name, "gate_font"))
        g6 = st.checkbox("Locale list finalized & vendor aligned", key=key_for(tab_name, "gate_locales"))
        g7 = st.checkbox("Legal/brand review complete", key=key_for(tab_name, "gate_legal"))
        # any missing gate => risk
        gates = {"String freeze":g1,"Pseudolocalization":g2,"ICU/plurals":g3,"RTL/BiDi":g4,"Font/glyph":g5,"Locales finalized":g6,"Legal/brand":g7}
        for gate_name, ok in gates.items():
            if not ok:
                cat = "Process"
                rname = f"Gate missing: {gate_name}"
                L, I = (2,2) if gate_name in ["Font/glyph","Locales finalized"] else (2,3)
                base_score = L*I; weighted_score = base_score * weights.get(cat, 1.0)
                risk_rows.append({
                    "project_name": project, "version": version, "assessment_date": today, "tab": tab_name,
                    "category": cat, "risk_name": rname, "likelihood": L, "impact": I, "score": base_score,
                    "weighted_score": weighted_score, "mitigation": f"Complete gate: {gate_name}", "evidence": "", "assessor": assessor
                })
                categories_scores[cat] = categories_scores.get(cat, 0) + weighted_score
                if base_score >= 6: red_flags.append((rname, cat, base_score, f"Complete {gate_name}"))

        # Useful links
        st.markdown("##### Links & artifacts")
        st.text_input("Git/Gerrit repo URL", key=key_for(tab_name, "link_repo"))
        st.text_input("CI pipeline URL", key=key_for(tab_name, "link_ci"))
        st.text_input("Spec/Confluence URL", key=key_for(tab_name, "link_spec"))

    # Summary & charts
    st.markdown("---")
    total_score = sum(r["score"] for r in risk_rows)
    max_cell = max((r["score"] for r in risk_rows), default=0)
    rating = score_to_rating(total_score, max_cell)

    badge = f"<span class='rr-badge {rating.lower()}'>{rating}</span>"
    st.markdown(f"### Summary {badge}", unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='rr-card'><div class='rr-muted'>Overall rating</div><div class='rr-metric'>{rating}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='rr-card'><div class='rr-muted'>High‑risk items (≥7)</div><div class='rr-metric'>{sum(1 for r in risk_rows if r['score']>=7)}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='rr-card'><div class='rr-muted'>Weighted score</div><div class='rr-metric'>{int(sum(r['weighted_score'] for r in risk_rows))}</div></div>", unsafe_allow_html=True)

    cA, cB = st.columns(2)
    with cA: plot_heatmap(risk_rows)
    with cB: plot_scatter(risk_rows)

    st.markdown("### 🔴 Red Flags (auto)")
    if red_flags:
        for name, cat, s, mit in sorted(red_flags, key=lambda x: x[2], reverse=True)[:5]:
            st.markdown(f"- **{name}** in *{cat}* — score {s} → _Mitigation:_ {mit}")
    else:
        st.info("No red flags identified.")

    # Data + download
    cols = ["project_name","version","assessment_date","tab","category","risk_name","likelihood","impact","score","weighted_score","mitigation","evidence","assessor"]
    df = pd.DataFrame(risk_rows, columns=cols)
    st.dataframe(df, use_container_width=True)

    if project and version and not df.empty:
        path = save_results_csv(project, version, tab_name, df)
        st.download_button("⬇️ Download CSV", data=df.to_csv(index=False).encode("utf-8"),
                           file_name=os.path.basename(path), mime="text/csv", key=key_for(tab_name, "dl"))
    elif not project or not version:
        st.warning("Enter Project & Version to enable CSV download.")

# ---------- Tabs ----------
tabs = st.tabs(["L10n", "LocOps", "General"])
with tabs[0]: assess_tab("L10n")
with tabs[1]: assess_tab("LocOps")
with tabs[2]: assess_tab("General")
