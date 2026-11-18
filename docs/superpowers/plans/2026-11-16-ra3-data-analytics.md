# RA3 Data Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete RA3 in the existing Online Retail project with descriptive analysis, interpreted visualizations, representativeness discussion, and a supervised daily-value regression.

**Architecture:** Keep the notebook generator as the source of notebook structure and embed reusable RA3 analysis functions from a focused script, matching the existing data preparation pattern. Update the README and presentation guide, and record the measured results and limits in an RA3 report after executing the notebook.

**Tech Stack:** Python, pandas, NumPy, Matplotlib, scikit-learn, Jupyter Notebook, existing project runtime (Python 3.12 and Java 17).

**Spec:** `C:/Users/Gast/Downloads/aaaaa.pdf` (RA3 scope); this plan follows its requirements and the repository's current notebook workflow.

## Global Constraints

- Preserve RA1 and RA2 behavior, data, and untracked user files.
- Analyze only the prepared positive merchandise records; describe the measure as gross value of positive item records, not net sales or profit.
- Use a chronological train/test split for daily prediction and compare the model to a seasonal-naive baseline.
- Include at least three labeled visualizations with short interpretations, descriptive statistics, representativeness/limitations, and reproducible execution instructions.
- Keep notebook generation reproducible through `scripts/build_notebook.py` and avoid assumptions that fail in Google Colab.

## Review Focus

- Missing calendar dates must be represented as zero daily item value before lag features are built.
- Lag and rolling features must use prior observations only; the target day must never enter its own features.
- The test partition must occur after the training partition and preserve date order.
- Positive-item gross value must not be presented as net revenue, profit, or current-market behavior.
- Plots must label units and identify transformed axes, especially the log-scaled line-item value distribution.

---

### Task 1: Add RA3 analysis functions and dependencies

**Files:**
- Create: `scripts/ra3_analysis.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces `build_daily_dataset(prepared)`, descriptive-statistics helpers, and `fit_daily_value_model(prepared)` returning daily observations, ordered train/test predictions, and MAE/RMSE metrics.

- [x] Implement daily aggregation, calendar completion, lag/rolling features, a time-ordered split, RandomForest regression, seasonal-naive baseline, and descriptive-statistics tables.
- [x] Pin/add Matplotlib and scikit-learn dependencies used by the notebook.

### Task 2: Integrate RA3 into the generated notebook

**Files:**
- Modify: `scripts/build_notebook.py`
- Regenerate: `projeto_data_analytics.ipynb`

- [x] Add RA3 scope, descriptive tables, four labeled visualizations, model comparison, interpretation, representativeness, limitations, and references.
- [x] Update the compact Markdown mapping and execution record for RA3 outputs and library versions.

### Task 3: Document and execute the RA3 delivery

**Files:**
- Modify: `README.md`
- Modify: `docs/preparacao_apresentacao.md`
- Create: `docs/relatorio_ra3.md`
- Update: `evidence/`

- [x] Add RA3 reproduction and presentation guidance plus a report populated from actual notebook results.
- [x] Execute the notebook in the repository's supported runtime, review the outputs/figures/PDF, and record remaining environment or data limitations.

---
