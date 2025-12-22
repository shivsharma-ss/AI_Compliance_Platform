#!/bin/bash
# Migration helper - run inside Cloud Run job or locally with Cloud SQL proxy

set -e

echo "Running Alembic migrations..."
alembic upgrade head
echo "✅ Migrations completed successfully"
