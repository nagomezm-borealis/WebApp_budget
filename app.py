from __future__ import annotations

from datetime import date
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from finance_logic import (
    EXPENSE_CATEGORIES,
    EXPENSE_LABELS,
    VARIABLE_COST_CATEGORIES,
    compute_summary,
)
from storage import (
    init_db,
    load_all_months,
    load_month_record,
    upsert_month,
    init_variable_costs_table,
    init_variable_expense_items_table,
    upsert_variable_expense_items,
    load_variable_expense_items,
)


st.set_page_config(page_title="Family Budget Tracker", page_icon="EUR", layout="wide")
st.title("Family Budget Tracker")
st.caption("Track monthly income, fixed expenses, and settlement amounts.")

base_dir = Path(__file__).parent.resolve()
db_path = init_db(base_dir)
init_variable_costs_table(db_path)
init_variable_expense_items_table(db_path)
df = load_all_months(db_path)

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
    defaults["vc_items"] = []


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


def _apply_month_to_session(row: "pd.Series", month_key: str | None = None) -> None:
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
    # Reset variable expense items, then load saved items for this month.
    st.session_state["vc_items"] = []
    if month_key:
        vc_items_df = load_variable_expense_items(db_path, month_key)
        if not vc_items_df.empty:
            st.session_state["vc_items"] = vc_items_df[["description", "category", "amount"]].to_dict("records")


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
                _apply_month_to_session(loaded.iloc[0], month_key)
                st.success(f"Loaded month {month_key} into form fields.")
                st.rerun()

    st.markdown("---")
    st.caption("Saved months:")
    if df.empty:
        st.caption("No saved months yet.")
    else:
        for _m in reversed(df["month"].tolist()):
            st.text(_m)


tab_income, tab_expenses, tab_variable_costs, tab_summary, tab_history = st.tabs(
    ["Monthly income", "Fixed monthly expenses", "Variable costs", "Monthly summary", "History & charts"]
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

with tab_variable_costs:
    st.subheader("Variable costs")
    st.caption(
        "Track household variable expenses. These are for your own records only "
        "and do not affect the shared expense split."
    )

    st.markdown("### Add expense")
    with st.form("vc_add_form", clear_on_submit=True):
        vc_col1, vc_col2, vc_col3 = st.columns([3, 2, 1.5])
        with vc_col1:
            vc_new_desc = st.text_input("Description", placeholder="e.g. Supermarket")
        with vc_col2:
            vc_new_cat = st.selectbox(
                "Category",
                options=list(VARIABLE_COST_CATEGORIES.values()),
            )
        with vc_col3:
            vc_new_amount = st.number_input("Amount (EUR)", min_value=0.0, step=1.0)

        vc_submitted = st.form_submit_button("Add expense", type="primary")

    if vc_submitted:
        if vc_new_amount > 0:
            st.session_state["vc_items"].append({
                "description": vc_new_desc,
                "category": vc_new_cat,
                "amount": vc_new_amount,
            })
            st.rerun()
        else:
            st.warning("Please enter an amount greater than zero.")

    vc_items = st.session_state.get("vc_items", [])
    if vc_items:
        st.markdown("### Expenses this month")
        for i, item in enumerate(list(vc_items)):
            ic1, ic2, ic3, ic4 = st.columns([3, 2, 1.5, 0.5])
            with ic1:
                st.write(item.get("description") or "—")
            with ic2:
                st.write(item.get("category", ""))
            with ic3:
                st.write(f"EUR {item['amount']:.2f}")
            with ic4:
                if st.button("×", key=f"vc_del_{i}", help="Remove this expense"):
                    st.session_state["vc_items"].pop(i)
                    st.rerun()
        vc_grand_total = sum(item["amount"] for item in vc_items)
        st.metric("Total variable costs", f"EUR {vc_grand_total:.2f}")

        st.markdown("### Breakdown by category")
        vc_pie_by_cat: dict[str, float] = {}
        for item in vc_items:
            cat = str(item.get("category", ""))
            if cat:
                vc_pie_by_cat[cat] = vc_pie_by_cat.get(cat, 0.0) + float(item.get("amount", 0.0))
        vc_pie_df = pd.DataFrame(
            {"Category": list(vc_pie_by_cat.keys()), "Amount": list(vc_pie_by_cat.values())}
        )
        vc_pie_fig = px.pie(vc_pie_df, values="Amount", names="Category")
        st.plotly_chart(vc_pie_fig, use_container_width=True)
    else:
        st.info("No variable expenses added yet for this month.")

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
    a1, a2 = st.columns(2)
    a1.metric("Noel pays", f"EUR {summary['noel_final_payment']:.2f}")
    a2.metric("Valentina pays", f"EUR {summary['valentina_final_payment']:.2f}")

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
            upsert_variable_expense_items(db_path, month_key, st.session_state.get("vc_items", []))
            st.toast(f"Saved {month_key}.")
            st.rerun()

    st.markdown("### Monthly expense distribution")
    # Fixed expense categories
    pie_labels: list[str] = []
    pie_values: list[float] = []
    for category, keys in EXPENSE_CATEGORIES.items():
        cat_total = float(sum(expenses.get(k, 0.0) for k in keys))
        if cat_total > 0:
            pie_labels.append(category)
            pie_values.append(cat_total)
    # Variable cost categories (aggregated from individual items)
    vc_by_cat: dict[str, float] = {}
    for item in st.session_state.get("vc_items", []):
        cat_label = str(item.get("category", ""))
        if cat_label:
            vc_by_cat[cat_label] = vc_by_cat.get(cat_label, 0.0) + float(item.get("amount", 0.0))
    for cat_label, vc_total in vc_by_cat.items():
        if vc_total > 0:
            pie_labels.append(cat_label)
            pie_values.append(vc_total)
    if pie_values:
        summary_pie_df = pd.DataFrame({"Category": pie_labels, "Amount": pie_values})
        summary_pie_fig = px.pie(
            summary_pie_df,
            values="Amount",
            names="Category",
            title="Fixed + variable expenses this month",
        )
        st.plotly_chart(summary_pie_fig, use_container_width=True)
    else:
        st.caption("Enter expenses above to see the distribution chart.")

with tab_history:
    st.subheader("Historical view")

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
