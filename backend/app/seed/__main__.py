"""Load the demo data set: `python -m app.seed [--reset] [--employees N]`.

Uses DATABASE_URL from the app settings. Run `alembic upgrade head` first.
"""

import argparse
import time

from app.core.config import get_settings
from app.core.db import create_db_engine, create_session_factory
from app.seed.loader import seed_database


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Load ACME's demo salary data.")
    parser.add_argument("--employees", type=int, default=10_000, help="how many employees")
    parser.add_argument(
        "--reset", action="store_true", help="clear existing data and load it again"
    )
    args = parser.parse_args(argv)

    engine = create_db_engine(get_settings().database_url)
    started = time.perf_counter()
    with create_session_factory(engine)() as session:
        result = seed_database(session, employees=args.employees, reset=args.reset)
    elapsed = time.perf_counter() - started
    engine.dispose()

    if result.loaded:
        print(
            f"Loaded {result.employees:,} employees and {result.versions:,} "
            f"compensation versions in {elapsed:.1f} s."
        )
    else:
        print(
            f"The database already has {result.employees:,} employees. "
            "Nothing was changed; use --reset to load the demo data again."
        )


if __name__ == "__main__":
    main()
