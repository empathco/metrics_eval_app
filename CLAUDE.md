# Skill Model Evaluation Explorer — Agent Instructions

## What this repo is

A Streamlit-based data exploration tool for reviewing LLM skill inference evaluation results across multiple experiments. Built as a PoC at Skillmore (Empath), intended to replace ad-hoc Excel review workflows.

The app is a **read-only drill-down UI**: experiments → jobs → individual inferences. No writes happen anywhere.

---

## Repo structure

```
eval_app/
├── app.py           # Streamlit UI — all pages and routing logic
├── data_loader.py   # Data access layer — ONLY file that touches data source
├── requirements.txt # Python dependencies
└── CLAUDE.md        # This file
```

Planned addition (not yet created):
```
├── .streamlit/
│   └── secrets.toml  # DB URL (git-ignored)
```

---

## How to run

```bash
conda create -n skillmore python=3.11 -y
conda activate skillmore
pip install -r requirements.txt
streamlit run app.py
```

Requires the Excel file `Job_Skill_Model_Comparison.xlsx` in the same directory as `app.py` (current dev mode). This goes away once the DB backend is wired up.

---

## Architecture

### Navigation model

Streamlit reruns the entire script on every interaction. Page state is managed via `st.session_state`:

```
st.session_state.page              # "home" | "job_list" | "job_detail"
st.session_state.selected_experiment   # e.g. "exp_20260325"
st.session_state.selected_job_code     # e.g. "AA524"
```

The `go(page, **kwargs)` helper sets state and calls `st.rerun()`. All navigation goes through it — do not call `st.rerun()` directly elsewhere.

### Pages

| Page function     | Route key     | Entry point                          |
|-------------------|---------------|--------------------------------------|
| `page_home()`     | `"home"`      | Lists experiments, clickable buttons |
| `page_job_list()` | `"job_list"`  | Per-job aggregated P/R/F1/F0.5       |
| `page_job_detail()`| `"job_detail"`| Raw inferences for one job           |

### Data layer (`data_loader.py`)

Two public functions, both cached with `@st.cache_data`:

- `load_experiments() → DataFrame` — overall metrics per experiment (one row per experiment)
- `load_inf_eval(experiment_name: str) → DataFrame` — raw inference rows for one experiment

**This is the only file to touch when migrating to PostgreSQL.** The UI calls these two functions and nothing else data-related.

### Metrics computation

P/R/F1/F0.5 are computed on-the-fly in `page_job_list()` from the raw `label` column (`TP`/`FP`/`FN`). They are not stored anywhere. Formula reference:

```
TP        = count of rows where label == "TP"
FP        = count of rows where label == "FP"
FN        = count of rows where label == "FN"
total     = TP + FP + FN

precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * P * R / (P + R)
F0.5      = 1.25 * P * R / (0.25 * P + R)   # precision-weighted
```

---

## Key constraints and decisions

- **pandas ≥ 2.2 required** — `include_groups=False` in `.groupby().apply()` is used to suppress deprecation warnings and will be mandatory in pandas 3.0. Do not remove it.
- **Streamlit ≥ 1.35 required** — `on_select="rerun"` on `st.dataframe` (used for row-click navigation in job list) was introduced in 1.35.
- **`applymap` vs `map`** — use `Styler.map()` not `Styler.applymap()` (deprecated in newer pandas). Currently used in `page_job_detail()`.
- **No form tags** — do not use HTML `<form>` elements. Use Streamlit widget callbacks.
- **Single-file app** — `app.py` is intentionally a single file for PoC simplicity. If pages grow, consider `st.navigation` + multi-file pages.

---

## Pending TODOs (tracked in data_loader.py)

### 1. PostgreSQL migration

Replace Excel loading with DB queries. Schema sketch:

```sql
-- experiments table
CREATE TABLE experiments (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    precision  FLOAT,
    recall     FLOAT,
    f1         FLOAT,
    f05        FLOAT,
    f03        FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- inf_eval table
CREATE TABLE inf_eval (
    id             SERIAL PRIMARY KEY,
    experiment_id  INT REFERENCES experiments(id),
    job_code       TEXT,
    job_title      TEXT,
    abbreviation   TEXT,
    label          TEXT,   -- 'TP', 'FP', or 'FN'
    score          FLOAT,
    skill_name     TEXT,
    skill_category TEXT,
    lvl_inf        INT,
    lvl_conf       INT
    -- add experiment-specific columns (e.g. original_phrase_inf, skill_desc) as nullable
);
```

Steps to migrate:
1. Add `get_engine()` to `data_loader.py` (SQLAlchemy, cached with `@st.cache_resource`)
2. Add `DATABASE_URL` to `.streamlit/secrets.toml` (git-ignored)
3. Replace `pd.read_excel(...)` bodies in `load_experiments()` and `load_inf_eval()` with `pd.read_sql(...)`
4. Remove `_SHEET_MAP`, `EXCEL_PATH`, and the Excel file dependency
5. `app.py` requires zero changes

### 2. Results page columns

The `Results` sheet currently has fixed columns (Precision, Recall, F1, F0.5, F0.3). When experiments with different metric sets are added, `page_home()` should dynamically render whatever columns are returned by `load_experiments()` rather than the hardcoded list.

### 3. Experiment metadata

Consider adding `created_at`, `model_id`, `description` columns to the experiments table and displaying them on the home page or as a detail panel.

---

## Data shape reference

### `load_experiments()` output

| Column          | Type  | Notes                        |
|-----------------|-------|------------------------------|
| experiment_name | str   | Display name, used as nav key|
| Precision       | float |                              |
| Recall          | float |                              |
| F1              | float |                              |
| F0.5            | float |                              |
| F0.3            | float |                              |

### `load_inf_eval()` output (minimum required columns)

| Column         | Type  | Notes                              |
|----------------|-------|------------------------------------|
| job_code       | str   | Primary grouping key               |
| job_title      | str   |                                    |
| abbreviation   | str   | Skill abbreviation                 |
| label          | str   | `"TP"`, `"FP"`, or `"FN"` only    |
| score          | float | Inference confidence score         |
| skill_name     | str   |                                    |
| skill_category | str   |                                    |

Additional columns (e.g. `lvl_inf`, `lvl_conf`, `original_phrase_inf`, `skill_desc`) may be present and are passed through transparently — add them to `display_cols` in `page_job_detail()` to surface them.

---

## What to avoid

- Do not add caching to `go()` or anything that writes to `st.session_state`
- Do not call `st.rerun()` outside of `go()`
- Do not put data-fetching logic in `app.py` — keep it in `data_loader.py`
- Do not hardcode experiment names in `app.py` — they must come from `load_experiments()`
- Do not use `st.experimental_*` APIs — all used APIs are stable as of Streamlit 1.35
