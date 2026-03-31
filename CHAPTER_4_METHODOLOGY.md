# Chapter 4: System Architecture and Methodology

## 4.1 Introduction to the Agent-Based Architecture
To address the challenges of answering natural language queries over a highly domain-specific e-commerce schema, this system abandons the traditional "single-prompt" Text-to-SQL approach. Instead, it adopts a multi-phase, state-driven agent architecture implemented using LangGraph. The system models the analytical process of a human business analyst: determining the scope of the question, writing the query using domain knowledge, executing the query, recovering from syntax or logical errors, and finally reporting the interpreted results.

The core of the system is the `BusinessAnalystAgent`, which maintains an `AgentState`—a typed dictionary containing the user's question, inferred product filters, generated SQL, execution errors, resulting data, and the final narrative answer. The workflow is modeled as a state machine with the following interconnected nodes:
1. **Lookup Node**: Analyzes the question scope and determines product/brand filtering strategy.
2. **Architect Node**: Generates PostgreSQL-compliant SQL using injected domain knowledge.
3. **Executor Node**: Executes the SQL against the database and traps errors.
4. **Conditional Edge (Self-Correction)**: Re-routes execution back to the Architect if errors occur (up to a 3-attempt limit).
5. **Reporter Node**: Formulates a natural language narrative and visual chart configuration based on the data.

## 4.2 Phase 1: Product Lookup and Scope Resolution
Before any SQL is generated, the system must constrain the scope of the question to prevent hallucinated `IN` lists or overly broad `ILIKE` clauses. The `node_lookup` function serves as an intent and entity classifier.

When a user submits a question (e.g., "Which Samsung products have the highest return rates?"), the LLM is prompted to return strict JSON mapping the request to two keys:
*   `search_term`: The specific product, brand, or the default `ALL_MARKET`.
*   `filter_mode`: Classified as `brand` (e.g., "Sony"), `item` (e.g., "iPhone"), or `both` (e.g., "Samsung", where the name acts as both company and product line).

By delegating entity resolution to a dedicated pre-processing step, the system reduces the cognitive load on the SQL generation phase. The output of this node (e.g., `search_term="Samsung"`, `filter_mode="both"`) is appended to the `AgentState` and passed down the graph.

## 4.3 Phase 2: The Architect (Reasoning Engine and Domain Knowledge)
The SQL generation phase (`node_architect`) is responsible for translating the user's natural language, constrained by the lookup parameters, into executable PostgreSQL. To ensure strict adherence to corporate business rules, the Architect utilizes a highly tailored prompt injection strategy referred to as the "Semantic Brain."

### 4.3.1 Dynamic Filtering Logic
The Architect first consumes the `search_term` and `filter_mode` from the `AgentState`. Rather than passing the raw entity to the LLM, the system dynamically constructs explicit SQL filtering instructions. For instance, if `filter_mode` is `both` for "Samsung", the Architect explicitly instructs the LLM: 
*   "Brand and title may both contain this phrase. Filter with `(brand_name ILIKE '%Samsung%' OR item_name ILIKE '%Samsung%')` on each relevant table."

This deterministic rule injection prevents the LLM from making assumptions about which column to query, effectively enforcing schema compliance before the SQL is even drafted.

### 4.3.2 The Semantic Brain (`DOMAIN_KNOWLEDGE`)
The most significant methodological contribution of the Architect is the injection of the `DOMAIN_KNOWLEDGE` string. Rather than fine-tuning a model on thousands of queries—which is expensive and brittle when business rules change—this system leverages the massive zero-shot context window of `gpt-4-turbo`. 

The injected knowledge base defines:
1.  **The Golden Linking Rule**: It explicitly instructs the model on how to join the revenue side (`shipped_raw`) to the cost side (`concession_raw`). Specifically, it mandates the use of `c.asin = s.asin AND c.mapped_year = s.year AND c.mapped_month = s.month AND c.mapped_week = s.week`, eliminating the common hallucination of joining returns simply by arbitrary datetimes.
2.  **Calculated Metric Definitions**: Business-specific metrics like "Return Rate %" are mathematically defined `((SUM(conceded_units) * 100.0) / NULLIF(SUM(shipped_units), 0))` so the LLM does not invent its own formulas.
3.  **Semantic Nuances**: It defines what "bleeding products" (high NCRC) or "safe products" (low return rate, no Andon Cord pulled) mean in the context of the data dictionary.

## 4.4 Phase 3 & 4: Execution and Self-Correction (Retry Loop)
The `node_executor` attempts to execute the generated query via SQLAlchemy using a robust context manager. The system relies on the `pandas.read_sql` method to stream the result set into a DataFrame. 

Because LLMs inevitably make SQL syntax errors (e.g., hallucinating a column like `c.asp_bucket` instead of `s.asp_bucket`) or logical errors (e.g., division by zero), the methodology incorporates a self-correcting feedback loop.

If an exception is raised by the `pg8000` database driver, the error string is caught and written directly to the `sql_error` key of the `AgentState`. The LangGraph conditional edge (`check_status`) evaluates this state. If an error exists and the `attempt_count` is less than 3, the graph routes execution backwards to the Architect. The Architect receives the exact PostgreSQL error traceback, allowing the LLM to understand its syntax mistake and re-draft the query in a subsequent attempt. This retry loop is primarily responsible for elevating the system's execution success rate on complex queries.

## 4.5 Phase 5: The Reporter Module
Once a query executes successfully (or if it definitively fails after 3 attempts), the execution passes to the `node_reporter`. The Reporter acts as a virtual BI Manager.

The node receives the user's original question alongside a truncated preview of the returned dataset (capped at 2500 characters to respect token limits while preserving statistical aggregations). The LLM is instructed to perform two tasks:
1.  **Narrative Synthesis**: Answer the question directly and provide context (e.g., "Why is NCRC so high? Driven largely by the 'Product Defect' category").
2.  **Chart Generation**: Output a strict JSON configuration representing an analytical visualization (e.g., plotting monthly trends on a bar chart), complete with labels and values extracted directly from the dataset.

The final payload—a Python dictionary containing the narrative string, the JSON chart data, the raw SQL used, and the raw CSV datasets—is returned to the FastAPI backend, where it is presented to the user via the Streamlit interface. This fulfills the objective of providing a complete end-to-end conversational analytics pipeline.
