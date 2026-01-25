# BI Agent Thesis Project - Complete Logic Explanation

## 🎯 Project Overview

This is an **Agentic Business Intelligence (BI) System** that uses AI agents to answer business questions about Amazon smartphone sales and returns data. The system combines:
- **Natural Language Processing** (NLP) to understand user questions
- **Hybrid Search** (Vector + Keyword) to find relevant products
- **SQL Generation** to query a PostgreSQL database
- **Data Visualization** to present insights
- **Web Search** capabilities for competitive intelligence

---

## 🏗️ Architecture Overview

The system follows a **multi-agent architecture** with these main components:

```
┌─────────────────┐
│  Streamlit UI   │  (Frontend Dashboard)
└────────┬────────┘
         │ HTTP POST /ask
         ▼
┌─────────────────┐
│  FastAPI Server │  (Backend API)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  BusinessAnalystAgent (LangGraph)   │
│  ┌───────────────────────────────┐  │
│  │ 1. Lookup Node               │  │  → Find products
│  │ 2. Architect Node            │  │  → Generate SQL
│  │ 3. Executor Node             │  │  → Execute Query
│  │ 4. Reporter Node             │  │  → Generate Report
│  └───────────────────────────────┘  │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL DB  │  (With pgvector extension)
│  - shipped_raw  │  (Sales data)
│  - concession_  │  (Returns data)
│    raw          │
│  - product_     │  (Catalog with vectors)
│    catalog      │
└─────────────────┘
```

---

## 📊 Data Model & Schema

### 1. **Product Catalog** (`product_catalog`)
The "brain" of product search:
- **Columns**: `asin`, `item_name`, `brand_name`, `manufacturer_name`, `subcategory_description`
- **Vector Embedding** (1536-dim): Semantic search using OpenAI embeddings
- **TSVECTOR**: Full-text search index for keyword matching
- **Purpose**: Enables hybrid search (semantic + keyword) to find products

### 2. **Sales Data** (`shipped_raw`)
Tracks all product shipments/sales:
- **Key Metrics**:
  - `shipped_units`: Number of units sold
  - `product_gms`: Gross Merchandise Sales (Revenue)
  - `shipped_cogs`: Cost of Goods Sold
- **Time Dimensions**: `year`, `month`, `week`
- **Product Info**: `asin`, `brand_name`, `manufacturer_name`, `item_name`
- **Business Logic**: If `fulfillment_channel = 'FBA'`, then `shipped_cogs = 0`

### 3. **Returns Data** (`concession_raw`)
Tracks all returns and concessions:
- **Key Metrics**:
  - `conceded_units`: Number of units returned
  - `ncrc`: Net Cost of Returns (THE LOSS metric)
  - `gcv`: Gross Concession Value (refund amount)
- **Time Dimensions**: 
  - `year`, `month`, `week`: When return happened
  - `mapped_year`, `mapped_month`, `mapped_week`: **When original sale happened** (for joining)
- **Diagnostics**: `defect_category`, `root_cause`, `is_andon_cord` (stop sale flag)

### 4. **The Golden Linking Rule**
To join returns to their original sales:
```sql
WHERE c.asin = s.asin 
  AND c.mapped_year = s.year 
  AND c.mapped_month = s.month 
  AND c.mapped_week = s.week
```

---

## 🔄 Complete Data Flow

### **Phase 1: Data Ingestion** (`ingestion.py`)

1. **Load TSV Files**:
   - Reads `data/shipped_data.tsv` (~385k rows)
   - Reads `data/concession_data.tsv` (~493k rows)

2. **Product Catalog Creation**:
   - Extracts unique products by `asin`
   - Generates **vector embeddings** using OpenAI `text-embedding-3-small`
   - Creates **TSVECTOR** index for full-text search
   - Stores in `product_catalog` table

3. **Transaction Data Loading**:
   - Cleans column names (lowercase, underscores)
   - Filters to valid schema columns
   - Bulk loads into `shipped_raw` and `concession_raw` tables

### **Phase 2: User Query Processing** (`sql_agent.py`)

The agent uses **LangGraph** with a state machine:

#### **Node 1: Lookup** (`node_lookup`)
**Purpose**: Identify if query is about specific products or general trends

**Logic**:
1. LLM analyzes question: "Is this about a specific product/brand or general stats?"
2. If specific → Extract search term (e.g., "iPhone 13")
3. **Hybrid Search**:
   ```sql
   SELECT asin FROM product_catalog 
   WHERE search_vector @@ websearch_to_tsquery('simple', 'iphone 13')
   LIMIT 20
   ```
4. Returns list of matching `asin` values
5. If general → Returns `"ALL_MARKET"`

**Output**: `target_asins` list, `search_term`

#### **Node 2: Architect** (`node_architect`)
**Purpose**: Generate SQL query using domain knowledge

**Logic**:
1. Builds filter clause if `target_asins` exist:
   ```python
   filter_logic = f"AND s.asin IN ('{asin1}', '{asin2}', ...)"
   ```

2. **Critical Prompt Engineering**:
   - Injects `DOMAIN_KNOWLEDGE` (from `knowledge.py`) into system prompt
   - Provides schema details
   - Explains business rules (e.g., mapped_year for joins)
   - Instructs on aggregation strategies

3. LLM generates PostgreSQL SQL query

4. **Self-Correction**: If SQL fails, retries up to 3 times

**Output**: `sql_query` string

#### **Node 3: Executor** (`node_executor`)
**Purpose**: Execute SQL and retrieve data

**Logic**:
1. Validates SQL exists
2. Executes query using SQLAlchemy
3. Converts result to CSV string
4. Handles errors gracefully

**Output**: `data_result` (CSV string) or `sql_error`

#### **Node 4: Reporter** (`node_reporter`)
**Purpose**: Generate human-readable answer + visualization

**Logic**:
1. Takes data preview (first 2500 chars)
2. LLM generates:
   - **Narrative**: Executive summary answer
   - **Chart JSON**: Visualization config (bar chart with labels/values)
3. Returns formatted response

**Output**: `final_answer`, `chart_json`

### **Phase 3: API Response** (`main.py`)

FastAPI endpoint `/ask`:
- Receives: `{"prompt": "question", "session_id": "uuid"}`
- Calls agent with thread_id (for conversation memory)
- Returns:
  ```json
  {
    "answer": "Executive summary...",
    "sql_query": "SELECT ...",
    "raw_data": "CSV string",
    "chart_data": {"type": "bar", "data": {...}},
    "session_id": "uuid"
  }
  ```

### **Phase 4: Dashboard Display** (`dashboard.py`)

Streamlit UI:
1. **Chat Interface**: User types question
2. **API Call**: POSTs to `/ask` endpoint
3. **Display**:
   - Answer text
   - Bar chart (if chart_data exists)
   - SQL query (expandable)
   - Raw data table (expandable)
4. **Session Memory**: Stores conversation history

---

## 🧠 Key Business Logic

### **1. Domain Knowledge** (`knowledge.py`)

The system has **hardcoded business rules** that guide SQL generation:

- **Net Margin Calculation**: `SUM(product_gms) - SUM(shipped_cogs) - SUM(ncrc)`
- **Return Rate**: `(SUM(conceded_units) * 100.0) / NULLIF(SUM(shipped_units), 0)`
- **"Bleeding" Products**: High `ncrc` or high `conceded_units`
- **Time Alignment**: Always use `mapped_year`, `mapped_month` for joins

### **2. Product Search Strategy**

**Hybrid Search** combines:
- **Vector Search**: Semantic similarity (e.g., "iPhone" matches "Apple smartphone")
- **Keyword Search**: Exact term matching using PostgreSQL TSVECTOR

This ensures both fuzzy matching and exact matches work.

### **3. SQL Generation Intelligence**

The LLM is instructed to:
- **Interpret Intent**: "bad products" → High NCRC or defect categories
- **Join Correctly**: Use mapped dates for sales-returns joins
- **Aggregate Smartly**: 
  - Trends → GROUP BY month/quarter
  - Details → Show specific rows
- **Handle Edge Cases**: CAST types, NULL handling

### **4. Error Handling & Retry Logic**

- SQL errors trigger retry (up to 3 attempts)
- Each retry includes error message in prompt
- LLM self-corrects based on error feedback

---

## 🔧 Technical Stack

### **Backend**:
- **FastAPI**: REST API framework
- **LangGraph**: Agent orchestration (state machine)
- **LangChain**: LLM integration
- **OpenAI GPT-4 Turbo**: SQL generation & analysis
- **OpenAI Embeddings**: Vector generation
- **SQLAlchemy**: Database ORM
- **PostgreSQL + pgvector**: Database with vector extension

### **Frontend**:
- **Streamlit**: Interactive dashboard
- **Pandas**: Data manipulation
- **Plotly**: Charts (though currently using Streamlit's bar_chart)

### **Infrastructure**:
- **Docker Compose**: Multi-container setup
- **PostgreSQL**: Database server
- **pgvector**: Vector similarity search

### **Additional Agents**:
- **WebScoutAgent** (`web_agent.py`): Uses Tavily API for competitor price searches
- **SQLGuardian** (`sql_guardian.py`): Column definitions reference (not actively used)

---

## 📈 Example Query Flow

**User asks**: *"What are the worst performing iPhone models in terms of returns?"*

1. **Lookup**: 
   - Extracts "iPhone" → Searches product_catalog → Finds 20 iPhone ASINs

2. **Architect**:
   - Generates SQL:
     ```sql
     SELECT s.item_name, 
            SUM(c.conceded_units) as total_returns,
            SUM(c.ncrc) as total_loss
     FROM shipped_raw s
     JOIN concession_raw c ON c.asin = s.asin 
       AND c.mapped_year = s.year 
       AND c.mapped_month = s.month
     WHERE s.asin IN ('B08XYZ...', 'B09ABC...', ...)
     GROUP BY s.item_name
     ORDER BY total_loss DESC
     LIMIT 10
     ```

3. **Executor**: Runs query → Returns CSV data

4. **Reporter**: 
   - Analyzes data
   - Generates: "iPhone 13 Pro Max has the highest return rate at 15%, causing $50k in losses..."
   - Creates bar chart JSON

5. **Dashboard**: Displays answer + chart + SQL + data table

---

## 🎓 Key Innovations

1. **Hybrid Search**: Combines semantic (vector) and keyword (TSVECTOR) search
2. **Domain Knowledge Injection**: Hardcoded business rules guide LLM reasoning
3. **Self-Correcting SQL**: Retry logic with error feedback
4. **Conversation Memory**: LangGraph checkpointer maintains session context
5. **Transparency**: Always shows SQL + raw data for validation

---

## 🚀 How to Use

1. **Setup**:
   ```bash
   docker-compose up -d
   python src/ingestion.py  # Load data
   ```

2. **Start Services**:
   - API: `http://localhost:9010`
   - Dashboard: `http://localhost:9090`

3. **Ask Questions**:
   - "What are the top 10 best-selling smartphones?"
   - "Which products have the highest return rates?"
   - "Show me sales trends by month"
   - "What's the total NCRC for Samsung products?"

---

## 🔍 Utility Scripts

- **`check_search.py`**: Test product search functionality
- **`reindex.py`**: Rebuild TSVECTOR index if search breaks

---

This system demonstrates how **AI agents** can be used to make complex business intelligence accessible through natural language, while maintaining transparency and accuracy through SQL generation and data visualization.
