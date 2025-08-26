# RiskRadar360 (Starter)

A lightweight Streamlit app to assess and visualize project risks, with tabs for **L10n**, **LocOps**, and **General** projects.
- Calculates risk score (Likelihood × Impact)
- Shows a 3×3 risk matrix and a category radar chart
- **One-click Save** to CSV with project name, version, date, and tab

## Quickstart
```bash
pip install -r requirements.txt
streamlit run app.py
```

## File Structure
```
RiskRadar360/
├─ app.py
├─ requirements.txt
├─ README.md
└─ results/
   └─ (CSV files saved here)
```

## CSV Schema (saved rows)
- project_name, version, assessment_date, tab
- category, risk_name, likelihood, impact, score
- mitigation, assessor (optional), notes (optional)

## Filename Pattern
`results/<Project>_<Version>_<YYYY-MM-DD>_<Tab>.csv`
Example: `results/DP_25.3_2025-08-26_L10n.csv`
