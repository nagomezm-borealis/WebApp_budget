# Family Budget Tracker

A personal Streamlit app for tracking monthly household budgets and calculating fair payment splits based on each person's income ratio.

## Tech stack

- **[Streamlit](https://streamlit.io/)** — UI and app workflow
- **[Plotly](https://plotly.com/python/)** — Interactive charts
- **[SQLite](https://www.sqlite.org/)** — Local month-by-month persistence

## Features

- Monthly income input per person (net salary + extra income)
- Child support tracking with automatic half-deduction from the non-receiving partner
- Fixed expenses grouped by category (Housing, Transportation, Insurance, Family, Personal Adjustments)
- JobRad deduction applied directly to Noel's final payment
- Income-ratio-based payment split suggestion
- Month-by-month SQLite storage with upsert on re-save
- Load any previously saved month back into the form for editing
- Historical charts tab with expense trends and income comparisons
- CSV export for backup and CSV import for migration/restore

## Project structure

```
├── app.py               # Streamlit entry point (UI, layout, form handling)
├── finance_logic.py     # Pure calculation logic (income ratio, payment split)
├── storage.py           # SQLite helpers (init, upsert, load)
├── requirements.txt     # Python dependencies
└── tests/
    └── test_finance_logic.py
```

## Getting started

### Prerequisites

- Python 3.11+

### Installation

```bash
git clone https://github.com/<your-username>/family-budget-tracker.git
cd family-budget-tracker
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the tests

```bash
pytest
```

## Calculation rules

- **Income ratio** is based on `net salary + extra income` per person.
- **Shared expenses** are split proportionally by that ratio.
- **Child support**: half of the received amount is deducted from the partner who did *not* receive it.
- **JobRad**: the monthly amount is deducted directly from Noel's final payment.
- Saving a month that already exists in the database performs an upsert (update).
- Month keys are validated as `YYYY-MM` for all load, save, and CSV import operations.

## Data storage

The app stores all data locally in a SQLite file (`budget_tracker.db`) that is created automatically on first run. This file is excluded from version control via `.gitignore` — no personal financial data is committed to the repository.
