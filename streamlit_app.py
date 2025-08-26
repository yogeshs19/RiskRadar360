
import os, re, datetime
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

st.set_page_config(page_title="RiskRadar360", layout="wide")

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
    fig, ax = plt.subplots(figsize=(4,4))  # smaller figure size
    ax.imshow(grid, cmap="viridis")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, str(grid[i][j]), ha="center", va="center", color="white" if grid[i][j]>0 else "black")
    ax.set_xticks([0,1,2]); ax.set_yticks([0,1,2])
    ax.set_xticklabels(["Impact 1","Impact 2","Impact 3"])
    ax.set_yticklabels(["Poss 1","Poss 2","Poss 3"])
    ax.set_title(title)
    st.pyplot(fig)

SCALE_HELP_P = "1 = Low (unlikely), 2 = Medium (could happen), 3 = High (very likely)"
SCALE_HELP_I = "1 = Low (minor), 2 = Medium (some rework/delay), 3 = High (major disruption)"

# simplified demonstration with defect summary and heatmap fix
def demo_app():
    st.title("Demo Fix — Defects Summary & Heatmap")
    sev_b = st.number_input("Blocker", 0, 999, 4)
    sev_c = st.number_input("Critical", 0, 999, 2)
    sev_mj = st.number_input("Major", 0, 999, 4)
    sev_mn = st.number_input("Minor", 0, 999, 10)
    defects_summary = f"Blocker={sev_b}, Critical={sev_c}, Major={sev_mj}, Minor={sev_mn}"
    st.write("Formatted defects summary:", defects_summary)
    rows = [{"possibility":3,"impact":3}] * (sev_b+sev_c+sev_mj+sev_mn)
    plot_heatmap(rows)

if __name__ == "__main__":
    demo_app()
