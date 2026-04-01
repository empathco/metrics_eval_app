# Skill Model Evaluation Explorer

A Streamlit app for exploring LLM skill inference evaluation results across experiments. Provides a read-only drill-down UI: **experiments → jobs → individual inferences**, with TP/FP/FN counts and P/R/F1/F0.5 metrics at every level.

🔗 **Live demo:** https://infevaldemo.streamlit.app/

---

## ☁️ Deployed on Streamlit Community Cloud

The app is live at **https://infevaldemo.streamlit.app/**.

To deploy your own fork:
1. Push this repo to GitHub (ensure `Job_Skill_Model_Comparison.xlsx` is committed).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **"New app"** → select this repo → set `app.py` as the main file.
4. Click **Deploy**. No extra config files needed.

---

## 🚀 Run with Docker Compose

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone <repo-url>
cd eval_app
docker-compose up
```

Then open http://localhost:8501.

The compose file uses a `python:3.11-slim` image directly — no `Dockerfile` needed. It mounts the project directory into the container, so the following files must all be present:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Compose config |
| `app.py` | Streamlit UI |
| `data_loader.py` | Data access layer |
| `requirements.txt` | Python dependencies |
| `Job_Skill_Model_Comparison.xlsx` | Data source |

---

## 🐍 Run locally with Python

```bash
pip install -r requirements.txt
streamlit run app.py
```



