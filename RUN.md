# How to Run the Project & Ingest Data

## Prerequisites

- **Docker Desktop** (for Postgres, or full stack)
- **`.env`** with `OPENAI_API_KEY`, `TAVILY_API_KEY`, and `DATABASE_URL`
- **Data files** (for ingestion):
  - `data/shipped_data.tsv`
  - `data/concession_data.tsv`  
  Place these in the `data/` folder. The ingestion script expects tab-separated columns compatible with `shipped_raw` / `concession_raw` (see `src/database.py`).

---

## Quick overview

1. **Start infrastructure** (Postgres, optionally API + dashboard).  
2. **Ingest data** (TSV → product catalog + transactions).  
3. **Run the app** (API + Streamlit dashboard) if not already running via Docker.

---

## Option A: Docker (all-in-one)

### 1. Start services

```bash
docker-compose up --build
```

This runs Postgres (port `5433`), the API (port `9010`), and the Streamlit dashboard (port `9090`).

### 2. Ingest data

In **another terminal**, run ingestion **inside the app container** (project is mounted, so it sees `data/`):

```bash
docker-compose exec agent_app python -m src.ingestion
```

Or use a one-off run:

```bash
docker-compose run --rm agent_app python -m src.ingestion
```

### 3. Use the app

- **Dashboard:** http://localhost:9090  
- **API:** http://localhost:9010  

---

## Option B: Local (API + Streamlit on your machine)

### 1. Start Postgres only

```bash
docker-compose up -d postgres
```

### 2. Ingest data

```bash
chmod +x ingest.sh && ./ingest.sh
```

Or manually:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5433/thesisdb"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m src.ingestion
```

### 3. Run API + dashboard

```bash
./run_local.sh
```

### 4. Open the app

- **Dashboard:** http://localhost:9090  
- **API:** http://localhost:8000  

---

## What ingestion does

- **Creates schema** (pgvector extension, tables) if missing.  
- **Product catalog:** Reads ASIN, item name, brand, etc. from both TSVs → `product_catalog` with embeddings and full-text search vectors.  
- **Transactions:** Truncates `shipped_raw` and `concession_raw`, then loads the TSV data into them.

Run ingestion **after** Postgres is up and **before** (or anytime before) using the BI agent.  
Re-running ingestion will add new products and **replace** transaction data.

---

## Optional: Reindex search vectors

If you change catalog text and want to refresh only the keyword search index (no re-embedding):

```bash
# Docker
docker-compose exec agent_app python -m src.reindex

# Local
export DATABASE_URL="postgresql://user:password@localhost:5433/thesisdb"
PYTHONPATH=. python -m src.reindex
```

---

## Troubleshooting

- **Docker “permission denied”:** Start Docker Desktop and ensure your user can use Docker.  
- **Config validation fails:** Check `OPENAI_API_KEY`, `TAVILY_API_KEY`, and `DATABASE_URL` in `.env`.  
  For local runs, use `DATABASE_URL=...@localhost:5433/...` (not `@postgres:5432`).  
- **“Missing data files”:** Add `data/shipped_data.tsv` and `data/concession_data.tsv` before running `ingest.sh` or `python -m src.ingestion`.  
- **Ingestion errors:** Ensure the TSVs exist, are tab-separated, and include expected columns (e.g. `asin`, `item_name`, `brand_name`, etc.).
