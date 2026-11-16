#!/bin/sh
# Container start-up: bring the schema up to date, then serve the API.
# The demo data is loaded separately, once: `python -m app.seed` (see docs/DEPLOYMENT.md).
set -e
alembic upgrade head
exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
