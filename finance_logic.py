from __future__ import annotations

from typing import Dict, Tuple


EXPENSE_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "Housing": (
        "rent",
        "nebenkosten",
        "energy_bill",
        "internet_bill",
        "orf",
    ),
    "Transportation": (
        "car_lease",
        "car_insurance",
    ),
    "Insurance": (
        "accident_insurance",
        "house_insurance",
        "legal_insurance",
        "emma_private_health_insurance",
    ),
    "Family": (
        "emma_savings_account",
        "kindergarten",
    ),
    "Personal Adjustments": (
        "jobrad",
    ),
}

EXPENSE_LABELS: Dict[str, str] = {
    "car_lease": "Car lease",
    "car_insurance": "Car insurance",
    "accident_insurance": "Accidents",
    "house_insurance": "House",
    "legal_insurance": "Legal",
    "emma_private_health_insurance": "Emma PHI",
    "emma_savings_account": "Emma savings account",
    "kindergarten": "Kindergarten",
    "rent": "Rent",
    "energy_bill": "Energy bill",
    "internet_bill": "Internet bill",
    "orf": "ORF",
    "nebenkosten": "Nebenkosten",
    "jobrad": "JobRad",
}


def _safe(value: float) -> float:
    return round(max(0.0, float(value)), 2)


def _round_money(value: float) -> float:
    return round(float(value), 2)


def _num(payload: Dict[str, object], key: str) -> float:
    raw = payload.get(key, 0.0)
    if not isinstance(raw, (int, float, str)):
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def compute_summary(payload: Dict[str, object]) -> Dict[str, float]:
    noel_income = _safe(_num(payload, "noel_net_salary") + _num(payload, "noel_extra_income"))
    val_income = _safe(_num(payload, "valentina_net_salary") + _num(payload, "valentina_extra_income"))

    incomes_total = _safe(noel_income + val_income)
    noel_ratio = (noel_income / incomes_total) if incomes_total else 0.5
    val_ratio = (val_income / incomes_total) if incomes_total else 0.5

    raw_expenses = payload.get("expenses", {})
    expenses: Dict[str, float] = raw_expenses if isinstance(raw_expenses, dict) else {}
    shared_expenses = sum(_num(expenses, k) for k in expenses if k != "jobrad")
    shared_expenses = _safe(shared_expenses)
    jobrad = _safe(_num(expenses, "jobrad"))

    child_support_amount = _safe(_num(payload, "child_support_amount"))
    child_support_receiver = str(payload.get("child_support_receiver", "Valentina"))
    receiver_normalized = child_support_receiver.strip().lower()
    is_noel_receiver = receiver_normalized == "noel"
    is_valentina_receiver = receiver_normalized == "valentina"

    noel_target = _safe(shared_expenses * noel_ratio)
    val_target = _safe(shared_expenses * val_ratio)

    noel_adjustment = 0.0
    val_adjustment = 0.0

    # Deduct half child support from the partner who did not receive it.
    if child_support_amount > 0:
        half_support = child_support_amount / 2
        if is_noel_receiver:
            val_adjustment -= half_support
        elif is_valentina_receiver:
            noel_adjustment -= half_support

    # JobRad payment reduces Noel's final amount to pay.
    noel_adjustment -= jobrad

    noel_final = _safe(max(0.0, noel_target + noel_adjustment))
    val_final = _safe(max(0.0, val_target + val_adjustment))

    return {
        "noel_income": _safe(noel_income),
        "valentina_income": _safe(val_income),
        "income_total": _safe(incomes_total),
        "noel_ratio": round(noel_ratio, 4),
        "valentina_ratio": round(val_ratio, 4),
        "shared_expenses_total": _safe(shared_expenses),
        "jobrad": _safe(jobrad),
        "household_expenses_total": _safe(shared_expenses + jobrad),
        "child_support_amount": _safe(child_support_amount),
        "noel_target": _safe(noel_target),
        "valentina_target": _safe(val_target),
        "noel_adjustment": _round_money(noel_adjustment),
        "valentina_adjustment": _round_money(val_adjustment),
        "noel_final_payment": _safe(noel_final),
        "valentina_final_payment": _safe(val_final),
    }
