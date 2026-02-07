# Agentic Framework for Natural Language Interaction with Relational Databases

## 📖 Project Overview

This project implements an **Agentic Business Intelligence (BI) Framework** capable of answering complex business questions using natural language. It is designed to demonstrate how Large Language Models (LLMs) can be integrated with relational databases to create a robust, self-correcting, and context-aware analytics system.

The core innovation lies in its **Multi-Agent Architecture**, which breaks down the problem of "chatting with data" into discrete, manageable steps: **Lookup**, **Architecting**, **Execution**, and **Reporting**. This approach overcomes the limitations of simple "Text-to-SQL" scripts by adding layers of verification, domain knowledge injection, and error recovery.

### 🎓 Thesis Alignment
This implementation serves as the practical application for the thesis: *All-in-One: An Agentic Framework for Natural Language Interaction with Relational Database*.
- **Agentic**: Uses [LangGraph](https://langchain-ai.github.io/langgraph/) for stateful, cyclic graph orchestration (not just a DAG).
- **Natural Language Interaction**: Uses [OpenAI GPT-4](https://openai.com/) to parse intent and generate human-readable insights.
- **Relational Database**: Leverages [PostgreSQL](https://www.postgresql.org/) for reliable, structured data storage, enhanced with [pgvector](https://github.com/pgvector/pgvector) for semantic capabilities.

---

## 🚀 Key Features

### 1. 🧠 Hybrid Search (Semantic + Keyword)
The system doesn't just rely on exact keyword matches. It uses **Vector Embeddings** (OpenAI `text-embedding-3-small`) stored in PostgreSQL to understand semantic similarity.
- *User asks*: "expensive phones"
- *System finds*: Products with high price tags, even if the word "expensive" isn't in the description.
- *Implementation*: Combines `pgvector` (cosine similarity) with PostgreSQL's native `TSVECTOR` (BM25-style keyword search) for best-of-both-worlds retrieval.

### 2. 🛡️ Self-Correcting SQL Generation
LLMs sometimes write invalid SQL. This framework includes a **Self-Correction Loop**:
- If the generated SQL fails (e.g., syntax error, wrong column), the **Executor** node catches the error.
- It sends the error message *back* to the **Architect** node.
- The Architect analyzes the error and regenerates the query, learning from its mistake.
- This retry mechanism runs up to 3 times, significantly increasing reliability.

### 3. 🌐 Real-Time Price Comparison
The system integrates external web data using the **Tavily API**.
- It can fetch real-time market prices for products.
- It compares these "Web Prices" against internal "Database Prices" (COGS/ASP).
- It generates comparative insights (e.g., "Our price is 15% lower than the market average").

### 4. 📝 Domain Knowledge Injection
A specialized knowledge base (`knowledge.py`) is injected into the prompt context. This ensures the model understands strictly defined business logic, such as:
- **Net Margin** = `GMS - COGS - NCRC`
- **Return Rate** = `(Returns / Sales) * 100`
- **Linking Rule**: Joining Sales and Returns tables using `mapped_year`/`mapped_week`.

### 5. 💾 Conversation Memory
The system maintains context across a session. You can ask follow-up questions like "What about for Samsung?" or "Show me the returns for *that* product", and the agent will understand the reference.

---

## 🏗️ Technical Architecture

The application is built as a microservices-style architecture using Docker.

```mermaid
graph TD
    User[User] -->|Browser| UI[Streamlit Dashboard]
    UI -->|HTTP POST /ask| API[FastAPI Backend]
    
    subgraph "Agentic Brain (LangGraph)"
        API --> NodeLookup
        NodeLookup --> NodePrice{Price Check?}
        NodePrice -->|Yes| NodeWeb[Web Scout]
        NodePrice -->|No| NodeArchitect
        NodeWeb --> NodeReporter
        NodeArchitect --> NodeExecutor
        NodeExecutor -- Success --> NodeReporter
        NodeExecutor -- Error --> NodeArchitect
        NodeReporter --> API
    end
    
    subgraph "Data Layer"
        NodeArchitect -->|Generate SQL| DB[(PostgreSQL)]
        NodeExecutor -->|Run Query| DB
        NodeLookup -->|Vector Search| DB
    end
    
    subgraph "External World"
        NodeWeb -->|API Call| Tavily[Tavily Search API]
        NodeLookup -->|Embedding| OpenAI[OpenAI API]
        NodeArchitect -->|Completion| OpenAI
    end
```

### Component Breakdown

| Component | Technology | Description |
|-----------|------------|-------------|
| **Frontend** | Streamlit | Provides a chat interface, renders Markdown answers, and displays Plotly charts. |
| **Backend API** | FastAPI | Exposes the agent workflow as a REST endpoint. Handles request validation and thread management. |
| **Orchestrator** | LangGraph | Manages the state machine. Defines nodes (steps) and edges (transitions). |
| **Database** | PostgreSQL 15 | Primary data store. Hosted in a Docker container. |
| **Vector Engine** | pgvector | Extension for PostgreSQL to store and query high-dimensional vectors. |

---

## 📂 Database Schema

The database relies on a **Star Schema** variant optimized for analytics:

### `product_catalog` (Dimension)
- **Primary Key**: `asin`
- **Attributes**: Item Name, Brand, Manufacturer, Category.
- **Special Columns**:
    - `embedding`: 1536-dimensional vector for semantic search.
    - `search_vector`: TSVECTOR for full-text search.

### `shipped_raw` (Fact - Sales)
- **Granularity**: Transaction/Shipment level.
- **Metrics**: `shipped_units`, `product_gms` (Revenue), `shipped_cogs` (Cost).
- **Time**: `year`, `month`, `week`.

### `concession_raw` (Fact - Returns)
- **Granularity**: Return event level.
- **Metrics**: `conceded_units`, `ncrc` (Net Cost of Returns), `gcv` (Refund Value).
- **Linking**: Contains `mapped_year`, `mapped_month` to link back to the original sale in `shipped_raw`.

---

## 🛠️ Installation & Setup

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/)
- [OpenAI API Key](https://platform.openai.com/) (GPT-4 access recommended)
- [Tavily API Key](https://tavily.com/) (For web search features)

### Step 1: Clone & Configure
1. Clone the repository.
2. Create a `.env` file in the root directory:
   ```env
   # Database (Docker service name is 'postgres')
   DATABASE_URL=postgresql://user:password@postgres:5432/thesisdb
   
   # AI Keys
   OPENAI_API_KEY=sk-proj-...
   OPENAI_MODEL_NAME=gpt-4-turbo
   
   # Web Search
   TAVILY_API_KEY=tvly-...
   
   # Settings
   DEBUG_MODE=True
   ```

### Step 2: Build & Run
Run the entire stack with Docker Compose:
```bash
docker-compose up --build
```
This will start:
- **Postgres** (Port 5433 host / 5432 container)
- **Backend API** (Port 9010 host / 8000 container)
- **Dashboard** (Port 9090 host / 9090 container)

### Step 3: Initialize Data
Once the containers are running, you need to load the data. You can do this from your local machine (if you have python/venv setup) or inside the container.

**Option A: Inside Docker (Recommended)**
```bash
# Enter the backend container
docker exec -it agentic_thesis_app bash

# Run the ingestion script
python src/ingestion.py
```

**Option B: Local Machine**
```bash
# Create venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install deps
pip install -r requirements.txt

# Run ingestion (Ensure DATABASE_URL points to localhost:5433 in .env for local run)
python src/ingestion.py
```

### Step 4: Access the Application
Open your browser to:
**http://localhost:9090**

---

## 🖥️ Usage Guide

### Simple Questions
> "How many units of iPhone 13 did we sell last month?"

The agent will:
1. Identify "iPhone 13" as the product.
2. Generate SQL to sum `shipped_units` from `shipped_raw` where `item_name` matches.
3. Return the exact number.

### Analytical Questions
> "Which products have the highest return rate?"

The agent will:
1. Understand "Return Rate" requires querying `concession_raw` and `shipped_raw`.
2. Generate a complex JOIN query using the domain knowledge formula.
3. Calculate rates and sort descending.
4. Retrieve the top 10 offenders.

### Comparative Questions
> "Are we selling the Samsung S24 cheaper than Amazon?"

The agent will:
1. Detect "Price Comparison" intent.
2. Use `WebScoutAgent` to Google current prices for "Samsung S24".
3. Query the internal `shipped_raw` table for the Average Selling Price (ASP).
4. Compare the two and tell you if your price is competitive.

---

## 🧩 Advanced Customization

### Adding New Domain Knowledge
Edit `src/knowledge.py`. This file contains the "System Prompt" instructions. Adding rules here (e.g., "Exclude employee sales") automatically teaches the agent new business logic without changing code.

### Modifying the Agent Graph
Edit `src/agents/sql_agent.py`. The `BusinessAnalystAgent` class defines the LangGraph workflow. You can add new nodes (e.g., a "SlackNotifier" node) by defining a new function and adding it to the `workflow`.

### Changing the Schema
1. Modify `src/database.py` to add columns/tables.
2. Re-run `src/ingestion.py` to reload data (or use Alembic for migrations in a production env).

---

## 📜 License
[MIT License](LICENSE)
