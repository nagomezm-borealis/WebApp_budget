from finance_logic import compute_summary


def test_noel_adjustment_remains_negative_when_deducted() -> None:
    payload = {
        "noel_net_salary": 2000,
        "noel_extra_income": 0,
        "valentina_net_salary": 2000,
        "valentina_extra_income": 0,
        "child_support_amount": 100,
        "child_support_receiver": "Valentina",
        "expenses": {
            "rent": 1000,
            "jobrad": 100,
        },
    }

    summary = compute_summary(payload)

    assert summary["noel_adjustment"] == -150.0
    assert summary["valentina_adjustment"] == 0.0
    assert summary["noel_final_payment"] == 350.0
    assert summary["valentina_final_payment"] == 500.0


def test_invalid_child_support_receiver_applies_no_deduction() -> None:
    payload = {
        "noel_net_salary": 2000,
        "noel_extra_income": 0,
        "valentina_net_salary": 2000,
        "valentina_extra_income": 0,
        "child_support_amount": 100,
        "child_support_receiver": "unknown",
        "expenses": {
            "rent": 1000,
        },
    }

    summary = compute_summary(payload)

    assert summary["noel_adjustment"] == 0.0
    assert summary["valentina_adjustment"] == 0.0
    assert summary["noel_final_payment"] == 500.0
    assert summary["valentina_final_payment"] == 500.0


def test_non_numeric_expenses_are_treated_as_zero() -> None:
    payload = {
        "noel_net_salary": 2000,
        "noel_extra_income": 0,
        "valentina_net_salary": 2000,
        "valentina_extra_income": 0,
        "child_support_amount": 0,
        "child_support_receiver": "Valentina",
        "expenses": {
            "rent": "bad-data",
            "energy_bill": 200,
            "jobrad": "bad-data",
        },
    }

    summary = compute_summary(payload)

    assert summary["shared_expenses_total"] == 200.0
    assert summary["jobrad"] == 0.0
    assert summary["household_expenses_total"] == 200.0
