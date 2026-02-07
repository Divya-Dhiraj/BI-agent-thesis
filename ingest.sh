#!/usr/bin/env bash
# Ingest TSV data into Postgres (product catalog + transactions).
# Requires: Postgres with pgvector, .env, and data/shipped_data.tsv + data/concession_data.tsv

set -e
cd "$(dirname "$0")"

# Local overrides when not using Docker
export DATABASE_URL="${DATABASE_URL:-postgresql://user:password@localhost:5433/thesisdb}"

# Optional: use venv if present
if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

if [[ ! -f data/shipped_data.tsv ]] || [[ ! -f data/concession_data.tsv ]]; then
  echo "Missing data files. Add both:"
  echo "  - data/shipped_data.tsv"
  echo "  - data/concession_data.tsv"
  exit 1
fi

echo "Starting ingestion (product catalog + transactions)..."
PYTHONPATH=. python -m src.ingestion
echo "Done."
