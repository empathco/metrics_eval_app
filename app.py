"""
Skill Model Evaluation Explorer
================================
PoC Streamlit app for exploring experiment results and inference evaluations.

Architecture notes:
- Currently loads data from a local Excel file (data_loader.py)
- TODO: Replace data_loader.py with PostgreSQL queries once DB schema is finalized
- State management uses st.session_state for drill-down navigation
"""

import pandas as pd
import streamlit as st
from data_loader import load_experiments, load_inf_eval

st.set_page_config(
    page_title="Skill Model Explorer",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state init ────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_experiment" not in st.session_state:
    st.session_state.selected_experiment = None
if "selected_job_code" not in st.session_state:
    st.session_state.selected_job_code = None


def go(page, **kwargs):
    st.session_state.page = page
    for k, v in kwargs.items():
        st.session_state[k] = v
    st.rerun()


def get_clicked_row_if_allowed(event, columns, allowed_columns):
    """Return clicked row index only when click is in an allowed column."""
    if not event.selection.cells:
        return None

    cell = event.selection.cells[0]

    if isinstance(cell, dict):
        row_idx = cell.get("row")
        col_ref = cell.get("column")
    elif isinstance(cell, (tuple, list)) and len(cell) >= 2:
        row_idx, col_ref = cell[0], cell[1]
    else:
        # Handle SelectionCell objects that expose attributes.
        row_idx = getattr(cell, "row", None)
        col_ref = getattr(cell, "column", None)

    if row_idx is None or col_ref is None:
        return None

    if isinstance(col_ref, int):
        if col_ref < 0 or col_ref >= len(columns):
            return None
        col_name = columns[col_ref]
    else:
        col_text = str(col_ref).strip()
        if col_text.isdigit():
            col_idx = int(col_text)
            if col_idx < 0 or col_idx >= len(columns):
                return None
            col_name = columns[col_idx]
        else:
            # Header text can contain sort arrows (e.g., "↑ experiment_name").
            col_name = col_text.lstrip("↑↓ ")

    if col_name not in allowed_columns:
        return None

    return int(row_idx)


# ── Pages ─────────────────────────────────────────────────────────────────────

def page_home():
    st.title("Skill Model Experiments")
    st.caption("Click an experiment name to drill into its evaluation results.")

    experiments = load_experiments()

    rows = []
    for _, row in experiments.iterrows():
        inf   = load_inf_eval(row["experiment_name"])
        tp    = int((inf["label"] == "TP").sum())
        fp    = int((inf["label"] == "FP").sum())
        fn    = int((inf["label"] == "FN").sum())
        total = tp + fp + fn
        rows.append({
            "experiment_name": row["experiment_name"],
            "TP": tp, "FP": fp, "FN": fn, "Total": total,
            "Precision": row["Precision"], "Recall": row["Recall"],
            "F1": row["F1"], "F0.5": row["F0.5"], "F0.3": row["F0.3"],
        })
    display_df = pd.DataFrame(rows)

    metrics = ["Precision", "Recall", "F1", "F0.5", "F0.3"]

    def percentile_color(series):
        ranks = series.rank(pct=True)
        colors = []
        for r in ranks:
            red   = int(231 + (46  - 231) * r)
            green = int(76  + (204 - 76)  * r)
            blue  = int(60  + (113 - 60)  * r)
            colors.append(f"background-color: rgb({red},{green},{blue}); color: #111")
        return colors

    styled = display_df.style.apply(
        lambda col: percentile_color(col) if col.name in metrics else [""] * len(col),
        axis=0,
    ).format({m: "{:.3f}" for m in metrics})

    event = st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-cell",
    )

    selected_row = get_clicked_row_if_allowed(
        event,
        list(display_df.columns),
        {"experiment_name"},
    )

    if selected_row is not None:
        exp_name = display_df.iloc[selected_row]["experiment_name"]
        go("job_list", selected_experiment=exp_name)


def page_job_list():
    exp = st.session_state.selected_experiment
    if st.button("← Back to Experiments"):
        go("home")

    st.title(f"{exp} — Job Summary")
    st.caption("Aggregated P/R/F1/F0.5 per job. Click job code or title to see individual inferences.")

    inf_eval = load_inf_eval(exp)

    def compute_metrics(group):
        tp = int((group["label"] == "TP").sum())
        fp = int((group["label"] == "FP").sum())
        fn = int((group["label"] == "FN").sum())
        total     = tp + fp + fn
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1  = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        f05 = (1.25 * precision * recall) / (0.25 * precision + recall) if (0.25 * precision + recall) > 0 else 0.0
        return {"job_title": group["job_title"].iloc[0],
                "TP": tp, "FP": fp, "FN": fn, "Total": total,
                "Precision": precision, "Recall": recall, "F1": f1, "F0.5": f05}

    summary = (
        inf_eval.groupby("job_code")
        .apply(compute_metrics, include_groups=False)
        .apply(pd.Series)
        .reset_index()
    )

    metrics = ["Precision", "Recall", "F1", "F0.5"]
    counts  = ["TP", "FP", "FN", "Total"]

    def percentile_color(series):
        ranks = series.rank(pct=True)
        colors = []
        for r in ranks:
            red   = int(231 + (46  - 231) * r)
            green = int(76  + (204 - 76)  * r)
            blue  = int(60  + (113 - 60)  * r)
            colors.append(f"background-color: rgb({red},{green},{blue}); color: #111")
        return colors

    display_df = summary[["job_code", "job_title"] + counts + metrics].copy()

    styled = display_df.style.apply(
        lambda col: percentile_color(col) if col.name in metrics else [""] * len(col),
        axis=0,
    ).format({m: "{:.3f}" for m in metrics})

    # on_select="rerun" triggers a rerun when a cell is clicked.
    # Drill down only if the clicked cell is in job_code or job_title.
    event = st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-cell",
    )

    selected_row = get_clicked_row_if_allowed(
        event,
        list(display_df.columns),
        {"job_code", "job_title"},
    )

    if selected_row is not None:
        job_code = display_df.iloc[selected_row]["job_code"]
        go("job_detail", selected_job_code=job_code)


def page_job_detail():
    exp = st.session_state.selected_experiment
    job_code = st.session_state.selected_job_code

    col_back, _ = st.columns([1, 5])
    if col_back.button("← Back to Jobs"):
        go("job_list")

    inf_eval = load_inf_eval(exp)
    job_rows = inf_eval[inf_eval["job_code"] == job_code].copy()

    job_title = job_rows["job_title"].iloc[0] if not job_rows.empty else job_code
    st.title(f"{job_code} — {job_title}")
    st.caption(f"Experiment: **{exp}**")

    label_order = {"TP": 0, "FP": 1, "FN": 2}
    job_rows["_label_rank"] = job_rows["label"].map(label_order).fillna(9)
    job_rows = job_rows.sort_values(
        ["_label_rank", "score", "skill_name"],
        ascending=[True, False, True],
    )

    display_cols = ["job_title", "skill_name", "label", "score",
                    "skill_category", "job_code", "abbreviation"]
    display_cols = [c for c in display_cols if c in job_rows.columns]
    out = job_rows[display_cols].reset_index(drop=True)

    def color_label(val):
        colors = {"TP": "#2ecc71", "FP": "#e74c3c", "FN": "#f39c12"}
        bg = colors.get(val, "#888")
        return f"background-color: {bg}; color: white; font-weight: bold"

    styled = out.style.map(color_label, subset=["label"])
    if "score" in out.columns:
        styled = styled.format({"score": "{:.4f}"})

    st.dataframe(styled, width="stretch", hide_index=True)


# ── Router ────────────────────────────────────────────────────────────────────

page = st.session_state.page
if page == "home":
    page_home()
elif page == "job_list":
    page_job_list()
elif page == "job_detail":
    page_job_detail()
