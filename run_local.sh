#!/usr/bin/env bash
# Run the BI Agent project locally (API + Streamlit dashboard).
# Requires: Postgres with pgvector on localhost:5433 (e.g. docker-compose up postgres)

set -e
cd "$(dirname "$0")"

# Local overrides: DB and API URL for non-Docker run
export DATABASE_URL="${DATABASE_URL:-postgresql://user:password@localhost:5433/thesisdb}"
export AGENT_API_URL="${AGENT_API_URL:-http://localhost:8000}"

# Venv
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
if ! python -c "import fastapi, uvicorn, streamlit" 2>/dev/null; then
  pip install -r requirements.txt
fi

# Run API in background
echo "Starting FastAPI on http://localhost:8000 ..."
PYTHONPATH=. uvicorn src.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Give API a moment to start
sleep 3

# Run Streamlit (foreground)
echo "Starting Streamlit dashboard on http://localhost:9090 ..."
PYTHONPATH=. streamlit run src/dashboard.py --server.port 9090 --server.address 0.0.0.0

# If Streamlit exits, kill API
kill $API_PID 2>/dev/null || true
