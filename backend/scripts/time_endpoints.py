"""Time the list and insight endpoints against a seeded database.

Usage (from backend/, after `alembic upgrade head` and `python -m app.seed`):

    python scripts/time_endpoints.py [--runs 30]

Requests go through the full app in-process (routing, auth, validation,
serialisation, database) but not over a network, so the numbers are server time.
A throwaway HR login is configured for the run; no real credentials are needed.
"""

import argparse
import secrets
import statistics
import sys
import time
from datetime import date
from pathlib import Path

import bcrypt
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.clock import FixedClock
from app.core.config import Settings, get_settings
from app.main import create_app
from app.models import Employee
from app.seed.generator import SEED_TODAY

BUDGET_MS = 300.0


def _endpoints(ravi_id: int) -> list[tuple[str, str]]:
    employees = "/api/v1/employees"
    insights = "/api/v1/insights"
    return [
        ("Directory, first page", f"{employees}"),
        ("Directory, India + Engineering", f"{employees}?country=IN&department=1"),
        ("Directory, sorted by total pay (USD)", f"{employees}?sort=total_pay_usd&order=desc"),
        ("Directory, below band", f"{employees}?band_position=below&page_size=100"),
        ("Directory, name search", f"{employees}?q=Ravi"),
        ("Profile", f"{employees}/{ravi_id}"),
        ("Compensation history", f"{employees}/{ravi_id}/compensation"),
        ("Insights summary", f"{insights}/summary"),
        ("Breakdown by country", f"{insights}/breakdown?group_by=country"),
        ("Breakdown by department", f"{insights}/breakdown?group_by=department"),
        ("Breakdown by level", f"{insights}/breakdown?group_by=level"),
        ("Band distribution", f"{insights}/band-distribution"),
        ("Exceptions, below band", f"{insights}/exceptions?type=below"),
        ("Exceptions, due soon", f"{insights}/exceptions?type=pending"),
        ("Recent changes", f"{insights}/recent-changes"),
        ("CSV export, all employees (not in the budget)", f"{employees}/export.csv"),
    ]


def _percentile(samples: list[float], percent: float) -> float:
    ordered = sorted(samples)
    index = max(0, min(len(ordered) - 1, round(percent / 100 * len(ordered)) - 1))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=30)
    args = parser.parse_args()

    password = secrets.token_urlsafe(16)
    settings = Settings(
        database_url=get_settings().database_url,
        hr_admin_email="timing@acme.example",
        hr_admin_password_hash=SecretStr(
            bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
        ),
        session_secret=SecretStr(secrets.token_urlsafe(48)),
    )
    app = create_app(settings, clock=FixedClock(SEED_TODAY))
    with app.state.session_factory() as session:
        ravi_id = session.scalar(select(Employee.id).where(Employee.employee_code == "EMP-04821"))
        count = session.scalar(select(Employee.id).order_by(Employee.id.desc()).limit(1))
    if ravi_id is None:
        raise SystemExit("No seeded data found. Run `python -m app.seed` first.")

    client = TestClient(app, base_url="https://localhost")
    client.post("/api/v1/auth/login", json={"email": settings.hr_admin_email, "password": password})

    print(f"{count:,} employees, as of {SEED_TODAY}, {args.runs} runs each (after 3 warm-up runs)")
    print(f"| Endpoint | p50 (ms) | p95 (ms) | max (ms) | Within {BUDGET_MS:.0f} ms |")
    print("|---|---:|---:|---:|:---:|")
    for name, url in _endpoints(ravi_id):
        for _ in range(3):
            client.get(url).raise_for_status()
        samples = []
        for _ in range(args.runs):
            started = time.perf_counter()
            client.get(url).raise_for_status()
            samples.append((time.perf_counter() - started) * 1000)
        p95 = _percentile(samples, 95)
        verdict = "n/a" if "not in the budget" in name else ("yes" if p95 < BUDGET_MS else "**no**")
        print(
            f"| {name} | {statistics.median(samples):.0f} | {p95:.0f} | {max(samples):.0f} "
            f"| {verdict} |"
        )
    print(f"\nMeasured {date.today().isoformat()}.")


if __name__ == "__main__":
    main()
