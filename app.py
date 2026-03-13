from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from finance_logic import EXPENSE_CATEGORIES, EXPENSE_LABELS, compute_summary
from storage import (
    init_db,
    load_all_months,
    load_month_record,
    upsert_month,
    init_debt_table,
    upsert_debt_payment,
    load_debt_payments,
    DEBT_OPENING_BALANCE,
)


st.set_page_config(page_title="Family Budget Tracker", page_icon="EUR", layout="wide")
st.title("Family Budget Tracker")
st.caption("Track monthly income, fixed expenses, and settlement amounts.")

base_dir = Path(__file__).parent.resolve()
db_path = init_db(base_dir)
init_debt_table(db_path)

EXPENSE_FIELDS = [
    "car_lease",
    "car_insurance",
    "accident_insurance",
    "house_insurance",
    "legal_insurance",
    "emma_private_health_insurance",
    "emma_savings_account",
    "kindergarten",
    "rent",
    "energy_bill",
    "internet_bill",
    "orf",
    "nebenkosten",
    "jobrad",
]


def month_default() -> str:
    return date.today().strftime("%Y-%m")


def _normalize_month(value: str) -> str | None:
    month = value.strip()
    if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        return month
    return None


def _set_form_defaults() -> None:
    defaults = {
        "month_input": month_default(),
        "noel_net_salary": 0.0,
        "noel_extra_income": 0.0,
        "valentina_net_salary": 0.0,
        "valentina_extra_income": 0.0,
        "child_support_amount": 0.0,
        "child_support_receiver": "Valentina",
    }
    for key in EXPENSE_FIELDS:
        defaults[f"expense_{key}"] = 0.0

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _to_float(value: object) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _build_record_from_inputs(month: str, payload: dict[str, object], expenses: dict[str, float]) -> dict:
    summary_values = compute_summary(payload)
    return {
        "month": month,
        "noel_net_salary": _to_float(payload.get("noel_net_salary", 0.0)),
        "noel_extra_income": _to_float(payload.get("noel_extra_income", 0.0)),
        "valentina_net_salary": _to_float(payload.get("valentina_net_salary", 0.0)),
        "valentina_extra_income": _to_float(payload.get("valentina_extra_income", 0.0)),
        "child_support_amount": _to_float(payload.get("child_support_amount", 0.0)),
        "child_support_receiver": str(payload["child_support_receiver"]),
        "car_lease": expenses["car_lease"],
        "car_insurance": expenses["car_insurance"],
        "accident_insurance": expenses["accident_insurance"],
        "house_insurance": expenses["house_insurance"],
        "legal_insurance": expenses["legal_insurance"],
        "emma_private_health_insurance": expenses["emma_private_health_insurance"],
        "emma_savings_account": expenses["emma_savings_account"],
        "kindergarten": expenses["kindergarten"],
        "rent": expenses["rent"],
        "energy_bill": expenses["energy_bill"],
        "internet_bill": expenses["internet_bill"],
        "orf": expenses["orf"],
        "nebenkosten": expenses["nebenkosten"],
        "jobrad": expenses["jobrad"],
        "shared_expenses_total": summary_values["shared_expenses_total"],
        "household_expenses_total": summary_values["household_expenses_total"],
        "noel_ratio": summary_values["noel_ratio"],
        "valentina_ratio": summary_values["valentina_ratio"],
        "noel_target": summary_values["noel_target"],
        "valentina_target": summary_values["valentina_target"],
        "noel_adjustment": summary_values["noel_adjustment"],
        "valentina_adjustment": summary_values["valentina_adjustment"],
        "noel_final_payment": summary_values["noel_final_payment"],
        "valentina_final_payment": summary_values["valentina_final_payment"],
    }


def _apply_month_to_session(row: "pd.Series") -> None:
    st.session_state["noel_net_salary"] = _to_float(row.get("noel_net_salary", 0.0))
    st.session_state["noel_extra_income"] = _to_float(row.get("noel_extra_income", 0.0))
    st.session_state["valentina_net_salary"] = _to_float(row.get("valentina_net_salary", 0.0))
    st.session_state["valentina_extra_income"] = _to_float(row.get("valentina_extra_income", 0.0))
    st.session_state["child_support_amount"] = _to_float(row.get("child_support_amount", 0.0))
    receiver = str(row.get("child_support_receiver", "Valentina"))
    st.session_state["child_support_receiver"] = (
        receiver if receiver in {"Valentina", "Noel"} else "Valentina"
    )
    for key in EXPENSE_FIELDS:
        st.session_state[f"expense_{key}"] = _to_float(row.get(key, 0.0))


_set_form_defaults()


with st.sidebar:
    st.subheader("Record")
    month = st.text_input("Month (YYYY-MM)", key="month_input")
    st.caption("Tip: Saving the same month updates that record.")
    month_preview = _normalize_month(month)
    if month_preview is None:
        st.error("Invalid month format. Use YYYY-MM (example: 2026-03).")
    else:
        st.caption(f"Month format looks good: {month_preview}")

    if st.button("Load selected month"):
        month_key = _normalize_month(month)
        if month_key is None:
            st.error("Invalid month format. Use YYYY-MM (example: 2026-03).")
        else:
            loaded = load_month_record(db_path, month_key)
            if loaded.empty:
                st.warning(f"No record found for {month_key}.")
            else:
                _apply_month_to_session(loaded.iloc[0])
                st.success(f"Loaded month {month_key} into form fields.")
                st.rerun()

    st.markdown("---")
    st.caption("Saved months:")
    _saved_months_df = load_all_months(db_path)
    if _saved_months_df.empty:
        st.caption("No saved months yet.")
    else:
        for _m in reversed(_saved_months_df["month"].tolist()):
            st.text(_m)


tab_income, tab_expenses, tab_summary, tab_history, tab_debt = st.tabs(
    ["Monthly income", "Fixed monthly expenses", "Monthly summary", "History & charts", "Debt tracker"]
)

with tab_income:
    st.subheader("Monthly income per person")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Noel**")
        noel_net_salary = st.number_input(
            "Net salary (Noel)", min_value=0.0, step=50.0, key="noel_net_salary"
        )
        noel_extra_income = st.number_input(
            "Extra income (Noel)", min_value=0.0, step=50.0, key="noel_extra_income"
        )
    with col2:
        st.markdown("**Valentina**")
        valentina_net_salary = st.number_input(
            "Net salary (Valentina)", min_value=0.0, step=50.0, key="valentina_net_salary"
        )
        valentina_extra_income = st.number_input(
            "Extra income (Valentina)", min_value=0.0, step=50.0, key="valentina_extra_income"
        )

    st.markdown("**Child support**")
    c1, c2 = st.columns(2)
    with c1:
        child_support_amount = st.number_input(
            "Child support amount", min_value=0.0, step=10.0, key="child_support_amount"
        )
    with c2:
        child_support_receiver = st.selectbox(
            "Who received child support?", ["Valentina", "Noel"], key="child_support_receiver"
        )

with tab_expenses:
    st.subheader("Fixed monthly expenses")
    st.caption("Expenses are grouped by category.")

    expenses: dict[str, float] = {}
    for category, keys in EXPENSE_CATEGORIES.items():
        category_total = sum(
            st.session_state.get(f"expense_{k}", 0.0) for k in keys
        )
        with st.expander(f"{category} — EUR {category_total:.2f}", expanded=True):
            for key in keys:
                expenses[key] = st.number_input(
                    EXPENSE_LABELS[key],
                    min_value=0.0,
                    step=10.0,
                    key=f"expense_{key}",
                )

payload = {
    "noel_net_salary": noel_net_salary,
    "noel_extra_income": noel_extra_income,
    "valentina_net_salary": valentina_net_salary,
    "valentina_extra_income": valentina_extra_income,
    "child_support_amount": child_support_amount,
    "child_support_receiver": child_support_receiver,
    "expenses": expenses,
}
summary = compute_summary(payload)

with tab_summary:
    st.subheader("Monthly summary")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total household income", f"EUR {summary['income_total']:.2f}")
    c2.metric("Shared fixed expenses", f"EUR {summary['shared_expenses_total']:.2f}")
    c3.metric("Total household expenses", f"EUR {summary['household_expenses_total']:.2f}")

    c4, c5 = st.columns(2)
    c4.metric("Noel ratio", f"{summary['noel_ratio'] * 100:.2f}%")
    c5.metric("Valentina ratio", f"{summary['valentina_ratio'] * 100:.2f}%")

    st.markdown("### Final payment suggestion")
    a1, = st.columns(1)
    a1.metric("Noel pays", f"EUR {summary['noel_final_payment']:.2f}")

    st.caption(
        "Rule: half child support is deducted from the non-receiver; JobRad is deducted from Noel's final payment."
    )

    if st.button("Save month", type="primary"):
        month_key = _normalize_month(month)
        if month_key is None:
            st.error("Cannot save: invalid month format. Use YYYY-MM (example: 2026-03).")
        else:
            record = _build_record_from_inputs(month_key, payload, expenses)
            upsert_month(db_path, record)
            st.toast(f"Saved {month_key}.")
            st.rerun()

with tab_history:
    st.subheader("Historical view")
    df = load_all_months(db_path)

    st.markdown("### Backup and migration")
    if df.empty:
        st.caption("No records available for CSV export yet.")
    else:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV backup",
            data=csv_bytes,
            file_name="budget_tracker_backup.csv",
            mime="text/csv",
        )

    uploaded = st.file_uploader("Import CSV backup", type=["csv"])
    if uploaded is not None and st.button("Import CSV now"):
        imported_df = pd.read_csv(uploaded)
        if "month" not in imported_df.columns:
            st.error("CSV must include a 'month' column in YYYY-MM format.")
        else:
            imported_count = 0
            skipped_invalid_month = 0
            for _, row in imported_df.iterrows():
                month_val = _normalize_month(str(row.get("month", "")))
                if month_val is None:
                    skipped_invalid_month += 1
                    continue

                row_expenses = {k: _to_float(row.get(k, 0.0)) for k in EXPENSE_FIELDS}
                row_payload = {
                    "noel_net_salary": _to_float(row.get("noel_net_salary", 0.0)),
                    "noel_extra_income": _to_float(row.get("noel_extra_income", 0.0)),
                    "valentina_net_salary": _to_float(row.get("valentina_net_salary", 0.0)),
                    "valentina_extra_income": _to_float(row.get("valentina_extra_income", 0.0)),
                    "child_support_amount": _to_float(row.get("child_support_amount", 0.0)),
                    "child_support_receiver": (
                        "Noel"
                        if str(row.get("child_support_receiver", "Valentina")).strip().lower()
                        == "noel"
                        else "Valentina"
                    ),
                    "expenses": row_expenses,
                }
                row_record = _build_record_from_inputs(month_val, row_payload, row_expenses)
                upsert_month(db_path, row_record)
                imported_count += 1

            st.success(f"Imported {imported_count} month records from CSV.")
            if skipped_invalid_month:
                st.warning(
                    f"Skipped {skipped_invalid_month} row(s) due to invalid month format. Expected YYYY-MM."
                )
            st.rerun()

    if df.empty:
        st.info("No saved months yet. Fill in values and click Save month from Monthly summary.")
    else:
        df_plot = df.copy()
        df_plot["month"] = pd.to_datetime(df_plot["month"], format="%Y-%m", errors="coerce")
        df_plot = df_plot.sort_values("month")

        st.markdown("### Household expenses trend")
        line_fig = px.line(
            df_plot,
            x="month",
            y=["shared_expenses_total", "household_expenses_total"],
            markers=True,
            labels={"value": "Amount", "variable": "Series"},
        )
        st.plotly_chart(line_fig, use_container_width=True)

        st.markdown("### Final payment trend")
        pay_fig = px.bar(
            df_plot,
            x="month",
            y=["noel_final_payment", "valentina_final_payment"],
            barmode="group",
            labels={"value": "Amount", "variable": "Person"},
        )
        st.plotly_chart(pay_fig, use_container_width=True)

        st.markdown("### Latest month expense distribution")
        valid_month_rows = df_plot.dropna(subset=["month"])
        if valid_month_rows.empty:
            st.info("No valid month values available yet for expense distribution chart.")
        else:
            latest_row = valid_month_rows.iloc[-1]

            cat_totals = {}
            for category, keys in EXPENSE_CATEGORIES.items():
                cat_totals[category] = float(sum(latest_row.get(k, 0.0) for k in keys))

            pie_df = pd.DataFrame(
                {"Category": list(cat_totals.keys()), "Amount": list(cat_totals.values())}
            )
            pie_fig = px.pie(pie_df, values="Amount", names="Category")
            st.plotly_chart(pie_fig, use_container_width=True)

        st.markdown("### Saved records")
        st.dataframe(df, use_container_width=True)

with tab_debt:
    st.subheader("Noel \u2194 Valentina — debt tracker")
    st.caption(
        "Tracks the running balance Noel owes Valentina. "
        "Each month's debt reduction = Noel's actual payment \u2212 his budget share."
    )

    debt_df = load_debt_payments(db_path)
    current_balance = (
        float(debt_df.iloc[-1]["balance"]) if not debt_df.empty else DEBT_OPENING_BALANCE
    )

    st.metric("Current balance (Noel owes Valentina)", f"EUR {current_balance:,.2f}")

    st.markdown("### Log a payment")

    dp_month = st.text_input("Month (YYYY-MM)", value=month_default(), key="dp_month")
    dp_month_key = _normalize_month(dp_month) if dp_month else None
    if dp_month and dp_month_key is None:
        st.error("Invalid month format. Use YYYY-MM (example: 2026-03).")

    # Auto-load the budget share for the selected month if a record exists.
    budget_share: float = 0.0
    has_budget_record = False
    if dp_month_key:
        _br = load_month_record(db_path, dp_month_key)
        if not _br.empty:
            budget_share = float(_br.iloc[0]["noel_final_payment"])
            has_budget_record = True

    dp_col1, dp_col2 = st.columns(2)
    with dp_col1:
        st.metric(
            "Budget share (Noel)",
            f"EUR {budget_share:.2f}",
            help="Noel's computed share from the monthly budget analysis for this month.",
        )
        if dp_month_key and not has_budget_record:
            st.caption("No budget record for this month — full payment counted as debt reduction.")
    with dp_col2:
        dp_actual = st.number_input(
            "Noel's actual total payment (EUR)", min_value=0.0, step=10.0, key="dp_actual"
        )

    dp_debt_reduction = round(dp_actual - budget_share, 2)
    st.info(
        f"Debt reduction this month: **EUR {dp_debt_reduction:.2f}** "
        f"\u00a0(actual {dp_actual:.2f} \u2212 budget share {budget_share:.2f})"
    )

    if st.button("Save payment", disabled=(dp_month_key is None), type="primary", key="save_debt"):
        upsert_debt_payment(
            db_path,
            dp_month_key,
            budget_share if has_budget_record else None,
            dp_actual,
            dp_debt_reduction,
        )
        st.toast(f"Saved debt payment for {dp_month_key}.")
        st.rerun()

    if not debt_df.empty:
        st.markdown("### Balance over time")
        _debt_plot = debt_df.copy()
        _debt_plot["month_dt"] = pd.to_datetime(_debt_plot["month"], format="%Y-%m", errors="coerce")
        _debt_plot = _debt_plot.sort_values("month_dt")
        _bal_fig = px.line(
            _debt_plot,
            x="month_dt",
            y="balance",
            markers=True,
            labels={"balance": "Balance (EUR)", "month_dt": "Month"},
        )
        st.plotly_chart(_bal_fig, use_container_width=True)

        st.markdown("### Payment history")
        _hist = (
            debt_df[["month", "noel_budget_share", "noel_actual_payment", "debt_payment", "balance"]]
            .copy()
            .sort_values("month", ascending=False)
            .reset_index(drop=True)
            .rename(
                columns={
                    "month": "Month",
                    "noel_budget_share": "Budget share",
                    "noel_actual_payment": "Actual payment",
                    "debt_payment": "Debt reduction",
                    "balance": "Balance",
                }
            )
        )
        st.dataframe(_hist, use_container_width=True)
