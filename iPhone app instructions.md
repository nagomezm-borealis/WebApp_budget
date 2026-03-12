# iPhone App — Agent Build Instructions

## What This App Is

A personal family budget tracker for two people (Noel and Valentina). Each month they enter their incomes and fixed expenses; the app calculates how much each person owes toward shared costs, proportional to their income. It also tracks an ongoing debt one person is paying down over time.

---

## Target Platform

- **Native iOS app** using **Swift + SwiftUI**
- **Minimum deployment target:** iOS 17
- **Local-only data storage** using **SQLite** (via the `SQLite.swift` package, or the built-in `sqlite3` C library)

---

## Data Model

Create a SQLite database (`budget_tracker.db`) stored in the app's Documents directory with two tables:

### Table: `monthly_records`

| Column | Type |
|---|---|
| `month` | TEXT PRIMARY KEY (format: `YYYY-MM`) |
| `noel_net_salary` | REAL |
| `noel_extra_income` | REAL |
| `valentina_net_salary` | REAL |
| `valentina_extra_income` | REAL |
| `child_support_amount` | REAL |
| `child_support_receiver` | TEXT (`"Noel"` or `"Valentina"`) |
| `car_lease` | REAL |
| `car_insurance` | REAL |
| `accident_insurance` | REAL |
| `house_insurance` | REAL |
| `legal_insurance` | REAL |
| `emma_private_health_insurance` | REAL |
| `emma_savings_account` | REAL |
| `kindergarten` | REAL |
| `rent` | REAL |
| `energy_bill` | REAL |
| `internet_bill` | REAL |
| `orf` | REAL |
| `nebenkosten` | REAL |
| `jobrad` | REAL |
| `shared_expenses_total` | REAL |
| `household_expenses_total` | REAL |
| `noel_ratio` | REAL |
| `valentina_ratio` | REAL |
| `noel_target` | REAL |
| `valentina_target` | REAL |
| `noel_adjustment` | REAL |
| `valentina_adjustment` | REAL |
| `noel_final_payment` | REAL |
| `valentina_final_payment` | REAL |
| `created_at` | TEXT DEFAULT CURRENT_TIMESTAMP |

### Table: `debt_payments`

| Column | Type |
|---|---|
| `month` | TEXT PRIMARY KEY (format: `YYYY-MM`) |
| `noel_budget_share` | REAL (nullable) |
| `noel_actual_payment` | REAL |
| `debt_payment` | REAL |
| `balance` | REAL |

**Seed `debt_payments` on first launch** with these historical records (opening balance: **€7,650.00**). Compute the running balance by subtracting each payment from the previous balance:

| Month | Payment |
|---|---|
| 2025-02 | 203.00 |
| 2025-03 | 200.00 |
| 2025-04 | 94.10 |
| 2025-07 | 185.1843 |
| 2025-08 | 262.5822 |
| 2025-09 | 222.0145 |
| 2025-10 | 272.239 |
| 2025-11 | 550.7508 |
| 2025-12 | 71.9879 |
| 2026-01 | 66.46 |
| 2026-02 | 138.197 |

---

## Business Logic (implement exactly as described)

### Income and ratios

- `noel_income = noel_net_salary + noel_extra_income`
- `valentina_income = valentina_net_salary + valentina_extra_income`
- `income_total = noel_income + valentina_income`
- `noel_ratio = noel_income / income_total` (default to 0.5 if total is 0)
- `valentina_ratio = valentina_income / income_total` (default to 0.5 if total is 0)

### Expenses

- `shared_expenses_total` = sum of all expenses **except** `jobrad`
- `household_expenses_total = shared_expenses_total + jobrad`

### Settlement calculation

1. `noel_target = shared_expenses_total × noel_ratio`
2. `valentina_target = shared_expenses_total × valentina_ratio`
3. Adjustments start at 0 for both:
   - If `child_support_amount > 0`: subtract `child_support_amount / 2` from the partner who did **not** receive child support.
   - `jobrad` is Noel-specific: subtract `jobrad` from `noel_adjustment`.
4. `noel_final_payment = max(0, noel_target + noel_adjustment)`
5. `valentina_final_payment = max(0, valentina_target + valentina_adjustment)`

All monetary values must be rounded to 2 decimal places. Negative intermediate values are valid; only the final payments are clamped to 0.

---

## Expense Categories (for display grouping only)

| Category | Fields |
|---|---|
| Housing | rent, nebenkosten, energy_bill, internet_bill, orf |
| Transportation | car_lease, car_insurance |
| Insurance | accident_insurance, house_insurance, legal_insurance, emma_private_health_insurance |
| Family | emma_savings_account, kindergarten |
| Personal Adjustments | jobrad |

---

## Screens and Navigation

Use a **tab bar** with four tabs:

### Tab 1 — Monthly Entry

- At the top, a month picker (text field or date wheel, year-month only, default to current month).
- A "Load" button to populate the form with a saved record for that month.
- **Income section:** numeric fields for Noel and Valentina (net salary, extra income).
- **Child support section:** amount field + picker to select receiver (Noel / Valentina).
- **Expenses section:** one numeric field per expense item, grouped by category (see categories above). Use the human-readable labels below.
- A **"Save" button** at the bottom. Saving the same month overwrites the existing record (upsert).

**Human-readable labels:**

| Field | Label |
|---|---|
| car_lease | Car lease |
| car_insurance | Car insurance |
| accident_insurance | Accidents |
| house_insurance | House |
| legal_insurance | Legal |
| emma_private_health_insurance | Emma PVH |
| emma_savings_account | Emma savings account |
| kindergarten | Kindergarten |
| rent | Rent |
| energy_bill | Energy bill |
| internet_bill | Internet bill |
| orf | ORF |
| nebenkosten | Nebenkosten |
| jobrad | JobRad (Noel) |

### Tab 2 — Monthly Summary

- Displays the computed summary for the currently selected month (from Tab 1).
- Show: total incomes, income ratio per person, shared expenses total, child support, adjustments, and the **final payment amount per person** (prominently).
- If no record is saved for the selected month, show a placeholder message.

### Tab 3 — History & Charts

- A list of all saved months (newest first).
- A line chart showing `noel_final_payment` and `valentina_final_payment` over time.
- Use **Swift Charts** (available natively in iOS 16+).

### Tab 4 — Debt Tracker

- Shows the opening balance (€7,650.00) at the top.
- A list of all payments (from `debt_payments` table) with month, payment amount, and running balance.
- A form to add or update a payment for a given month: fields for `noel_actual_payment` and `debt_payment`. Recompute the running balance for all affected rows on save.
- Display the **current remaining balance** prominently.

---

## Formatting

- All monetary values displayed with 2 decimal places and a `€` prefix.
- Month values always in `YYYY-MM` format in storage; display as `MMM YYYY` (e.g., `Mar 2026`) in the UI.

---

## Project Structure

```
FamilyBudgetTracker/
  Models/
    MonthlyRecord.swift       // struct + SQLite mapping
    DebtPayment.swift         // struct + SQLite mapping
  Logic/
    BudgetCalculator.swift    // pure functions: compute_summary equivalent
  Storage/
    DatabaseManager.swift     // SQLite init, upsert, load methods
  Views/
    MonthlyEntryView.swift
    SummaryView.swift
    HistoryView.swift
    DebtTrackerView.swift
  FamilyBudgetTrackerApp.swift
```

---

## Dependencies

- **SQLite.swift** (via Swift Package Manager): `https://github.com/stephencelis/SQLite.swift`
- No other third-party dependencies. Swift Charts is part of the iOS SDK.

---

