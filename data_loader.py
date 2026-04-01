"""
data_loader.py
==============
Abstraction layer between the UI and the data source.

Current backend: local Excel file (Job_Skill_Model_Comparison.xlsx).

TODO: Replace all functions here with PostgreSQL queries once the DB schema
      is finalized. The UI (app.py) should not need any changes — just swap
      the implementations below.

Expected future schema (sketch):
  - experiments(id, name, precision, recall, f1, f05, f03, created_at)
  - inf_eval(id, experiment_id, job_code, job_title, abbreviation, label,
             score, skill_name, skill_category, lvl_inf, lvl_conf, ...)
"""

import pandas as pd
import streamlit as st

# TODO: Replace with st.secrets["DATABASE_URL"] and SQLAlchemy engine
EXCEL_PATH = "Job_Skill_Model_Comparison.xlsx"

# Map experiment display names → sheet names in the Excel file.
# TODO: Remove this mapping when switching to DB; experiment names will come
#       from the `experiments` table directly.
_SHEET_MAP = {
    "exp_20260306": "Old Model Inf Eval",
    "exp_20260325": "New Model Inf Eval",
}


@st.cache_data
def load_experiments() -> pd.DataFrame:
    """
    Returns a DataFrame with one row per experiment and overall metrics.

    Columns: experiment_name, Precision, Recall, F1, F0.5, F0.3

    TODO: Replace body with:
        engine = get_engine()
        return pd.read_sql("SELECT * FROM experiments ORDER BY created_at", engine)
    """
    df = pd.read_excel(EXCEL_PATH, sheet_name="Results")
    df = df.rename(columns={"Unnamed: 0": "experiment_name"})
    df["experiment_name"] = df["experiment_name"].str.strip()
    return df


@st.cache_data
def load_inf_eval(experiment_name: str) -> pd.DataFrame:
    """
    Returns the raw inference evaluation rows for a given experiment.

    Columns (at minimum): job_code, job_title, abbreviation, label, score,
                          skill_name, skill_category

    TODO: Replace body with:
        engine = get_engine()
        return pd.read_sql(
            "SELECT * FROM inf_eval WHERE experiment_id = "
            "(SELECT id FROM experiments WHERE name = %s)",
            engine, params=(experiment_name,)
        )
    """
    sheet = _SHEET_MAP.get(experiment_name)
    if sheet is None:
        raise ValueError(f"Unknown experiment: {experiment_name!r}. "
                         f"Known: {list(_SHEET_MAP)}")
    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet)
    return df


# TODO: Add get_engine() once switching to PostgreSQL:
# from sqlalchemy import create_engine
# @st.cache_resource
# def get_engine():
#     return create_engine(st.secrets["DATABASE_URL"])
