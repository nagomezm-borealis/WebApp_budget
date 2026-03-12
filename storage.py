from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DB_NAME = "budget_tracker.db"


def _connect(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def init_db(base_dir: Path) -> Path:
    db_path = base_dir / DB_NAME
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monthly_records (
                month TEXT PRIMARY KEY,
                noel_net_salary REAL,
                noel_extra_income REAL,
                valentina_net_salary REAL,
                valentina_extra_income REAL,
                child_support_amount REAL,
                child_support_receiver TEXT,
                car_lease REAL,
                car_insurance REAL,
                accident_insurance REAL,
                house_insurance REAL,
                legal_insurance REAL,
                emma_private_health_insurance REAL,
                emma_savings_account REAL,
                kindergarten REAL,
                rent REAL,
                energy_bill REAL,
                internet_bill REAL,
                orf REAL,
                nebenkosten REAL,
                jobrad REAL,
                shared_expenses_total REAL,
                household_expenses_total REAL,
                noel_ratio REAL,
                valentina_ratio REAL,
                noel_target REAL,
                valentina_target REAL,
                noel_adjustment REAL,
                valentina_adjustment REAL,
                noel_final_payment REAL,
                valentina_final_payment REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    return db_path


def upsert_month(db_path: Path, record: dict) -> None:
    columns = ", ".join(record.keys())
    placeholders = ", ".join(["?"] * len(record))
    updates = ", ".join([f"{col}=excluded.{col}" for col in record if col != "month"])

    sql = f"""
        INSERT INTO monthly_records ({columns})
        VALUES ({placeholders})
        ON CONFLICT(month) DO UPDATE SET
        {updates}
    """

    with _connect(db_path) as conn:
        conn.execute(sql, list(record.values()))


def load_all_months(db_path: Path) -> pd.DataFrame:
    with _connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM monthly_records ORDER BY month ASC",
            conn,
        )
    return df


def load_month_record(db_path: Path, month: str) -> pd.DataFrame:
    with _connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM monthly_records WHERE month = ? LIMIT 1",
            conn,
            params=[month],
        )
    return df


# ---------------------------------------------------------------------------
# Debt tracker
# ---------------------------------------------------------------------------

DEBT_OPENING_BALANCE: float = 7650.00

_DEBT_SEED: list[tuple[str, float]] = [
    ("2025-02", 203.0),
    ("2025-03", 200.0),
    ("2025-04", 94.10),
    ("2025-07", 185.1843),
    ("2025-08", 262.5822),
    ("2025-09", 222.0145),
    ("2025-10", 272.239),
    ("2025-11", 550.7508),
    ("2025-12", 71.9879),
    ("2026-01", 66.46),
    ("2026-02", 138.197),
]


def init_debt_table(db_path: Path) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS debt_payments (
                month TEXT PRIMARY KEY,
                noel_budget_share REAL,
                noel_actual_payment REAL NOT NULL,
                debt_payment REAL NOT NULL,
                balance REAL NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM debt_payments").fetchone()[0]
        if count == 0:
            balance = DEBT_OPENING_BALANCE
            for month, paid in _DEBT_SEED:
                balance = round(balance - paid, 2)
                conn.execute(
                    """
                    INSERT INTO debt_payments
                        (month, noel_budget_share, noel_actual_payment, debt_payment, balance)
                    VALUES (?, NULL, ?, ?, ?)
                    """,
                    (month, paid, paid, balance),
                )


def upsert_debt_payment(
    db_path: Path,
    month: str,
    noel_budget_share: float | None,
    noel_actual_payment: float,
    debt_payment: float,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO debt_payments
                (month, noel_budget_share, noel_actual_payment, debt_payment, balance)
            VALUES (?, ?, ?, ?, 0.0)
            ON CONFLICT(month) DO UPDATE SET
                noel_budget_share     = excluded.noel_budget_share,
                noel_actual_payment   = excluded.noel_actual_payment,
                debt_payment          = excluded.debt_payment
            """,
            (month, noel_budget_share, noel_actual_payment, debt_payment),
        )
        # Recompute running balances for all rows in chronological order.
        rows = conn.execute(
            "SELECT month, debt_payment FROM debt_payments ORDER BY month ASC"
        ).fetchall()
        balance = DEBT_OPENING_BALANCE
        for row_month, row_dp in rows:
            balance = round(balance - row_dp, 2)
            conn.execute(
                "UPDATE debt_payments SET balance = ? WHERE month = ?",
                (balance, row_month),
            )


def load_debt_payments(db_path: Path) -> pd.DataFrame:
    with _connect(db_path) as conn:
        return pd.read_sql_query(
            "SELECT * FROM debt_payments ORDER BY month ASC",
            conn,
        )
    return df
