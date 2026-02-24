# A Natural Language Interface for Business Intelligence: An Agent-Based System for Text-to-SQL, Product Lookup, and Narrative Reporting

**Thesis Document**  
BI Agent for Conversational Analytics

---

## Table of Contents

1. [Abstract](#1-abstract)
2. [Introduction](#2-introduction)
3. [Related Work](#3-related-work)
4. [Background and Preliminaries](#4-background-and-preliminaries)
5. [System Design and Methodology](#5-system-design-and-methodology)
6. [Implementation](#6-implementation)
7. [Evaluation](#7-evaluation)
8. [Conclusion and Future Work](#8-conclusion-and-future-work)
9. [References](#9-references)
10. [Appendices](#10-appendices)

---

## 1. Abstract

Business users often lack the technical skills to query databases directly, yet they need timely, accurate answers from organizational data. This thesis presents an agent-based system that bridges natural language and structured data by (1) interpreting user questions in the context of a domain-specific sales and returns database, (2) resolving product or brand scope via hybrid (keyword and vector) search, (3) generating executable SQL that adheres to business rules and schema, (4) executing queries with retry on failure, and (5) producing narrative answers and visualizations suitable for decision-making. The system is evaluated on SQL syntax and execution success, execution accuracy against gold SQL where available, end-to-end success rate, latency, and per-category performance. Results show that a pipeline combining product lookup, structured domain knowledge, and a state-graph agent can achieve robust Text-to-SQL and answer generation for a real-world business intelligence setting, and highlight which question types remain challenging. The work contributes a concrete architecture, an evaluation framework, and a discussion of design choices (product lookup, domain knowledge, retries) for conversational BI agents.

**Keywords:** Text-to-SQL, natural language interface to databases, business intelligence agent, conversational analytics, LLM, product lookup, execution accuracy, domain knowledge.

---

## 2. Introduction

### 2.1 Motivation

Organizations store critical business data in relational databases. Answering ad hoc questions—such as “What are total sales?”, “Which products have the highest return rates?”, or “What is the net margin for iPhone?”—typically requires writing SQL. Many business users cannot write SQL, and even analysts spend considerable time translating questions into queries. A system that accepts natural language and returns correct, interpretable answers (with optional charts) can democratize data access and speed up decision-making.

### 2.2 Problem Statement

The problem addressed in this thesis is: **How can we build a system that (1) accepts natural language questions over a domain-specific business database, (2) resolves which products or scope (e.g., “iPhone”, “all market”) the question refers to, (3) generates SQL that is both syntactically and semantically correct with respect to schema and business rules, (4) executes the query and, when needed, recovers from errors, and (5) produces a concise narrative answer and optional visualization?**

Challenges include: schema and domain complexity (e.g., correct joins between sales and returns using mapped dates), product disambiguation (e.g., “iPhone” → specific ASINs), handling ambiguous or under-specified questions, and evaluating both SQL correctness and answer quality in a reproducible way.

### 2.3 Objectives

- **Design** an agent-based pipeline that integrates product lookup, SQL generation, execution, and reporting.
- **Implement** the pipeline using a state-graph (LangGraph) agent, a PostgreSQL database with vector and full-text search, and a domain knowledge module.
- **Evaluate** the system on syntax correctness, execution success, execution accuracy (vs. gold SQL), end-to-end success, latency, and per-question-category performance.
- **Identify** which question types succeed or fail and how design choices (lookup, domain knowledge, retries) affect outcomes.

### 2.4 Contributions

1. **System architecture:** A multi-phase agent (lookup → architect → executor → reporter) with conditional retry and explicit domain knowledge injection.
2. **Product lookup:** Integration of keyword (full-text) search for product resolution before SQL generation, with optional extension to hybrid vector + keyword.
3. **Domain knowledge module:** A structured knowledge base (schema, join rules, metric definitions, business flags) used in the SQL-generation prompt to improve semantic correctness.
4. **Evaluation framework:** Automated evaluation of SQL syntax, execution success, execution accuracy (EX), answer presence, latency, and category-level breakdown, with support for ground-truth SQL and expected patterns.
5. **Empirical analysis:** Baseline results and error analysis on a curated test set spanning simple aggregation, trend analysis, calculated metrics, product-specific, and complex multi-criteria questions.

### 2.5 Thesis Structure

- **Section 3** reviews related work on Text-to-SQL, conversational BI, and evaluation.
- **Section 4** provides background on natural language interfaces to databases and the domain.
- **Section 5** describes the system design and methodology.
- **Section 6** details the implementation (stack, data model, API, evaluation).
- **Section 7** presents the evaluation setup, metrics, and research questions.
- **Section 8** concludes and outlines future work.
- **Section 9** lists references; **Section 10** gives appendices (schema, sample queries).

---

## 3. Related Work

### 3.1 Text-to-SQL and Benchmarks

**Spider** (Yu et al., 2018) introduced a large-scale, cross-domain benchmark for complex Text-to-SQL: models must generalize to unseen databases and query structures. Evaluation uses exact match (EM) and execution accuracy (EX). **BIRD** (Li et al., 2023) scales to large, dirty databases and emphasizes external knowledge and SQL efficiency; execution accuracy remains the primary metric. **Spider 2.0** (2024) and **BEAVER** (2024) focus on enterprise settings with real schemas and multi-query workflows, showing that academic benchmarks underestimate real-world difficulty. This thesis adopts execution accuracy (EX) and execution success rate as core metrics, and uses schema- and domain-specific design rather than cross-domain generalization.

### 3.2 Conversational BI and Analytics Agents

**InsightBench** (2024) evaluates business analytics agents on end-to-end insight generation (formulating questions, interpreting answers, generating summaries). **DataLab** (2024) presents a unified LLM-powered BI platform for data preparation, analysis, and visualization. **BI-REC** (2021) uses conversational recommendation to guide users through drill-down and roll-up operations. This thesis aligns with the “agent that answers NL questions with SQL + narrative + chart” paradigm and adds explicit product lookup and domain knowledge as first-class components.

### 3.3 Evaluation of Text-to-SQL and Answer Quality

Standard Text-to-SQL evaluation uses (1) syntax validity, (2) execution success, and (3) execution accuracy (comparison of result sets to gold SQL). Answer quality is harder to automate; options include semantic similarity to a reference answer, fact extraction and overlap, and **LLM-as-judge** scoring. This thesis uses syntax checks (PostgreSQL EXPLAIN), execution success, EX when gold SQL is available, and answer presence/latency; extension to semantic similarity or LLM-as-judge is supported by the evaluation framework.

---

## 4. Background and Preliminaries

### 4.1 Natural Language Interfaces to Databases (NLIDB)

An NLIDB maps natural language questions to executable database queries (typically SQL). Key sub-tasks include: **intent recognition**, **entity/slot filling** (e.g., product names, dates), **schema linking** (mapping phrases to tables and columns), and **SQL generation**. Modern approaches use large language models (LLMs) with in-context schema and optional retrieval. This system uses an LLM for both intent/product extraction and SQL generation, with schema and domain knowledge provided in the prompt.

### 4.2 Domain: Sales and Returns (E-commerce)

The application domain is smartphone sales and returns in a single marketplace. Two main tables are used:

- **shipped_raw:** Sales (revenue side): units shipped, product_gms (revenue), shipped_cogs (cost of goods), fulfillment_channel (e.g., FBA, RET), and time dimensions (year, month, week).
- **concession_raw:** Returns (cost side): conceded_units, ncrc (net cost of returns), defect_category, root_cause, and **mapped_year / mapped_month / mapped_week** used to link a return to the original sale.

Critical business rules include: (1) joining returns to sales via `asin`, `mapped_year`, `mapped_month`, `mapped_week`; (2) FBA COGS = 0; (3) return rate = (conceded_units / shipped_units) × 100; (4) net margin = product_gms − shipped_cogs − ncrc; (5) safety/quality flags such as `is_andon_cord`. These are encoded in a **domain knowledge** module and injected into the SQL-generation prompt.

### 4.3 Product Catalog and Search

Product identity is captured by ASIN (Amazon Standard Identification Number). The system maintains a **product_catalog** table with item_name, brand_name, and related attributes. To support questions like “sales for iPhone”, the system must map “iPhone” to a set of ASINs. This is done via **product lookup** using full-text search (PostgreSQL `tsvector` / `websearch_to_tsquery`); the implementation can be extended to hybrid search with vector embeddings. Resolved ASINs are passed to the SQL architect as an IN-list filter.

---

## 5. System Design and Methodology

### 5.1 High-Level Architecture

The system is structured as a **multi-phase agent** implemented with a state graph (LangGraph):

1. **Lookup:** Determine whether the question is about specific products/brands or the whole market; if specific, resolve to a list of ASINs via product search.
2. **Architect:** Generate PostgreSQL SQL using the user question, resolved ASINs (if any), schema, and **domain knowledge** (join rules, metric definitions, business flags).
3. **Executor:** Run the SQL against the database; capture success/failure and result set.
4. **Conditional edge:** If execution failed and attempt count &lt; 3, retry from Architect; otherwise proceed to Reporter.
5. **Reporter:** Given the question and (possibly empty) result data, generate a narrative answer and a chart configuration (e.g., bar/line) in JSON.

State is carried across nodes (messages, question, target_asins, search_term, sql_query, sql_error, data_result, attempt_count, final_answer, chart_json). The agent is invoked with a single question and returns answer, chart_data, sql_query, and raw_data.

### 5.2 Product Lookup (Phase 1)

- **Input:** Last user message (the question).
- **Logic:** An LLM extracts a search term (product/brand name) or “ALL_MARKET” for global questions. For non-global queries, the system queries `product_catalog` using full-text search (`search_vector @@ websearch_to_tsquery('simple', :term)`), limited to 20 ASINs.
- **Output:** `target_asins` (list), `search_term`, `question`, `attempt_count = 0`. These are merged into the shared state for the Architect.

### 5.3 SQL Generation – Architect (Phase 2)

- **Input:** State (question, target_asins, domain knowledge, schema summary).
- **Logic:** Build a filter clause `AND s.asin IN (...)` when target_asins is non-empty (with safe escaping). Compose a system prompt that includes: (1) role (Expert Amazon Data Analyst), (2) **domain knowledge** (DOMAIN_KNOWLEDGE from knowledge.py: dataset overview, golden linking rule, data dictionary, calculated metrics, query strategies), (3) available tables (shipped_raw, concession_raw), (4) user question, (5) instructions (interpret “bad products”, join with mapped_year/month, apply ASIN filter, aggregation guidance, CAST(asin AS TEXT) for joins). The LLM returns only valid PostgreSQL SQL; response is cleaned (markdown code blocks removed).
- **Output:** sql_query, incremented attempt_count; or sql_error on exception.

### 5.4 Executor and Retry (Phases 3–4)

- **Executor:** Runs the generated SQL via the database connection; returns data_result (CSV string) or sql_error. Empty result sets are treated as an error to trigger retry.
- **Conditional edge:** If there is an sql_error and attempt_count &lt; 3, transition to “retry” (back to Architect); else “success” (if data_result present) or “fail” (go to Reporter anyway). The Reporter can still produce a message when execution failed.

### 5.5 Reporter (Phase 5)

- **Input:** question, data_result (preview truncated to 2500 chars).
- **Logic:** An LLM is asked to act as a BI manager: answer the question directly, explain “why” where relevant, and output a chart configuration. Response is parsed as JSON with keys `narrative` and `chart` (type, data.labels, data.values, title).
- **Output:** final_answer (narrative), chart_json, and an AIMessage appended to messages.

### 5.6 Domain Knowledge Module

The **domain knowledge** is a single structured string (DOMAIN_KNOWLEDGE) containing: dataset overview (shipped_raw vs concession_raw), the golden linking rule (join on asin, mapped_year, mapped_month, mapped_week), a data dictionary for both tables (identifiers, time dimensions, metrics, flags), calculated metric definitions (net margin, return rate, “bleeding”/“safe” products), and query strategies (trend analysis, root cause, vendor performance). This string is injected verbatim into the Architect system prompt so the LLM can adhere to schema and business rules without training.

---

## 6. Implementation

### 6.1 Technology Stack

- **Language:** Python 3.
- **Database:** PostgreSQL with pgvector extension; SQLAlchemy ORM.
- **LLM:** OpenAI GPT (e.g., gpt-4-turbo) via LangChain ChatOpenAI; temperature 0 for reproducibility.
- **Agent framework:** LangGraph (StateGraph, MemorySaver for optional threading).
- **API:** FastAPI; POST /ask accepts prompt and session_id, returns answer, sql_query, raw_data, chart_data, considered_products.
- **Frontend:** Streamlit dashboard (and/or React frontend) for submitting questions and displaying answers and charts.
- **Configuration:** Environment variables (OPENAI_API_KEY, DATABASE_URL, OPENAI_MODEL_NAME, etc.) with validation at startup.

### 6.2 Data Model

- **product_catalog:** asin (PK), item_name, brand_name, manufacturer_name, subcategory_description; embedding (vector 1536 for future hybrid search); search_vector (tsvector) for full-text search. Indexes: HNSW on embedding, GIN on search_vector.
- **shipped_raw:** id, ncrc_su_pk, asin, item_name, brand_name, manufacturer_name, time dimensions (year, month, quarter, week, mapped_year), shipped_units, shipped_cogs, product_gms, fulfillment_channel, etc.
- **concession_raw:** id, ncrc_cu_pk, asin, item_name, brand_name, mapped_year/month/week/quarter, conceded_units, ncrc, defect_category, root_cause, is_andon_cord, is_hrr_asin, etc.

Ingestion: TSV files (shipped_data.tsv, concession_data.tsv) are cleaned, normalized, and loaded; product catalog is built from unique ASINs with embeddings (OpenAI text-embedding-3-small) and search_vector updated via SQL for full-text search.

### 6.3 API and Agent Interface

- **BusinessAnalystAgent.ask(question, thread_id):** Invokes the compiled graph with initial state `{ messages: [HumanMessage(question)] }` and returns a dictionary with answer, chart_data, sql_query, raw_data. The agent does not currently expose target_asins in the return; the API can be extended to include considered_products for evaluation.
- **Evaluation:** The evaluator (BIAgentEvaluator) calls agent.ask for each test question, then runs SQL syntax check (EXPLAIN), execution, optional EX vs. gold_sql, and records answer presence, latency, and category. Results are aggregated into summary, performance, by_category, errors, and detailed_results.

### 6.4 Evaluation Implementation

- **Syntax:** PostgreSQL EXPLAIN on generated SQL; valid/invalid and error message.
- **Execution:** Execute SQL; record success, row_count, execution_time, empty_result.
- **Execution accuracy (EX):** When ground_truth.gold_sql is provided, run both model SQL and gold SQL; compare result DataFrames (sorted columns, sorted rows); report execution_accuracy (exact match), row_count_match.
- **Ground-truth checks:** expected_tables (all must appear in SQL), expected_sql_pattern (substring in normalized SQL).
- **Category breakdown:** Each test case can have a category (e.g., simple_aggregation, trend_analysis, calculated_metric); aggregate success rate, syntax accuracy, execution success, answer generation rate, and average latency per category.
- **Output:** evaluation_results.json (summary, performance, by_category, errors, detailed_results) and console summary.

---

## 7. Evaluation

### 7.1 Research Questions

1. **RQ1 (Performance by category):** How well does the agent perform across question categories (simple aggregation, trend analysis, calculated metrics, product-specific, ranking, comparative, complex multi-criteria, flag interpretation, etc.), and which categories are hardest?
2. **RQ2 (Execution accuracy):** How does execution accuracy (EX) compare to exact match (EM) when gold SQL is available, and what failure modes (syntax, wrong tables/joins, filters) explain the gap?
3. **RQ3 (End-to-end success):** Does the pipeline achieve a usable end-to-end success rate (valid SQL, executed, non-empty correct answer), and where does it fail most (lookup, SQL generation, execution, reporting)?
4. **RQ4 (Design choices):** How much do product lookup and domain knowledge contribute to SQL correctness and answer relevance? (Ablations: disable lookup; reduce or remove domain knowledge.)
5. **RQ5 (Stability):** How stable are success and correctness when the same question is run multiple times (e.g., temperature=0)?

### 7.2 Metrics

| Metric | Description | Target (example) |
|--------|-------------|-------------------|
| SQL syntax accuracy | Fraction of generated queries that pass EXPLAIN | &gt; 95% |
| SQL execution success rate | Fraction of queries that run without runtime error | &gt; 90% |
| Execution accuracy (EX) | Fraction where result set matches gold SQL (when provided) | &gt; 80% |
| End-to-end success rate | Syntax valid ∧ execution success ∧ non-empty answer | &gt; 85% |
| Answer generation rate | Non-empty narrative returned | High |
| Average latency | Time from question to response (seconds) | &lt; 10 s |
| Per-category success rate | Success rate by question category | Identify weak categories |

### 7.3 Experimental Setup

- **Test set:** A curated set of natural language questions with optional category and ground_truth (expected_tables, expected_sql_pattern, gold_sql where available). Example file: data/test_queries.json (e.g., 15 questions spanning simple_aggregation, trend_analysis, calculated_metric, product_specific, ranking, comparative, complex_multi_criteria, root_cause_analysis, time_filtered, brand_analysis, flag_interpretation).
- **Environment:** Database populated via ingestion; same model and temperature across runs for reproducibility.
- **Run:** `python -m src.evaluation` (or with custom test file path); results saved to evaluation_results.json.

### 7.4 Results and Discussion (Placeholder)

- **Summary:** Report total_queries, success_rate, sql_syntax_accuracy, sql_execution_success_rate, answer_generation_rate, execution_accuracy_ex (and n), average_latency.
- **By category:** For each category, report success_rate and average_latency; identify categories with low success (e.g., complex joins, calculated metrics).
- **Error analysis:** Inspect errors list (question, sql_error, syntax_error); categorize failure modes (syntax, wrong table/column, join logic, filter, timeout).
- **Ablations (if run):** Compare full system vs. no product filter vs. reduced domain knowledge on a subset of questions.
- **Limitations:** Single domain, single LLM, English only; gold SQL and expected answers require manual curation.

---

## 8. Conclusion and Future Work

### 8.1 Summary

This thesis presented an agent-based natural language interface for business intelligence that combines (1) product lookup via full-text search, (2) domain-informed SQL generation, (3) execution with retry, and (4) narrative and chart reporting. The system is implemented with LangGraph, PostgreSQL (with vector and full-text search), and a structured domain knowledge module. An evaluation framework supports syntax, execution, execution accuracy (EX), and per-category analysis. The work demonstrates that a modular, knowledge-grounded pipeline can address real-world Text-to-SQL and answer generation for a specific BI domain, and provides a basis for measuring and improving performance.

### 8.2 Future Work

- **Hybrid product search:** Combine vector similarity and keyword search for better recall on product-specific questions.
- **Larger and more diverse test set:** Expand to 50+ questions with gold SQL and expected answers for robust EX and answer-quality metrics.
- **Answer quality metrics:** Add semantic similarity (e.g., sentence embeddings) and/or LLM-as-judge for “Does this answer correctly address the question?”
- **Multi-turn dialogue:** Support clarification and follow-up questions within the same session (e.g., “What about last quarter?”).
- **Additional data sources:** Extend schema and domain knowledge to more tables or data marts.
- **User study:** Collect subjective ratings of answer usefulness and correctness from business users.

---

## 9. References

1. T. Yu et al., “Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing and Text-to-SQL Task,” *EMNLP*, 2018. [arXiv:1809.08887](https://arxiv.org/abs/1809.08887)
2. J. Li et al., “Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Grounded Text-to-SQLs (BIRD),” *NeurIPS*, 2023. [arXiv:2305.03111](https://arxiv.org/abs/2305.03111)
3. Spider 2.0: Evaluating Language Models on Real-World Enterprise Text-to-SQL Workflows, 2024. [arXiv:2411.07763](https://arxiv.org/abs/2411.07763)
4. BEAVER: An Enterprise Benchmark for Text-to-SQL, 2024. [arXiv:2409.02038](https://arxiv.org/abs/2409.02038)
5. InsightBench: Evaluating Business Analytics Agents Through Multi-Step Insight Generation, 2024. [arXiv:2407.06423](https://arxiv.org/abs/2407.06423)
6. DataLab: A Unified Platform for LLM-Powered Business Intelligence, 2024. [arXiv:2412.02205](https://arxiv.org/abs/2412.02205)
7. BI-REC: Guided Data Analysis for Conversational Business Intelligence, 2021. [arXiv:2105.00467](https://arxiv.org/abs/2105.00467)
8. From Generation to Judgment: Opportunities and Challenges of LLM-as-a-Judge, 2024. [arXiv:2411.16594](https://arxiv.org/abs/2411.16594)

---

## 10. Appendices

### Appendix A: Schema Summary (Key Tables)

**product_catalog**  
- asin (PK), item_name, brand_name, manufacturer_name, subcategory_description  
- embedding (vector(1536)), search_vector (tsvector)

**shipped_raw**  
- id, ncrc_su_pk, asin, item_name, brand_name, manufacturer_name  
- year, month, quarter, week, mapped_year  
- shipped_units, shipped_cogs, product_gms, fulfillment_channel, ...

**concession_raw**  
- id, ncrc_cu_pk, asin, item_name, brand_name  
- year, month, mapped_year, mapped_month, mapped_week, mapped_quarter  
- conceded_units, ncrc, defect_category, root_cause, is_andon_cord, is_hrr_asin, ...

### Appendix B: Sample Test Queries (Categories)

| Category | Example Question |
|----------|------------------|
| simple_aggregation | What are total sales? |
| trend_analysis | Show me total sales by month |
| calculated_metric | What is the return rate? |
| product_ranking | Which products have the highest return rates? |
| financial_metric | What is the net margin? |
| product_specific | Show me sales for iPhone |
| flag_interpretation | Which products have safety issues? |
| ranking | What are the top 10 best-selling products? |
| comparative | Compare sales between Apple and Samsung |
| complex_multi_criteria | Show me products with high return rates and low margins |
| root_cause_analysis | What are the main reasons for returns? |
| time_filtered | How many units were shipped last month? |
| brand_analysis | Which brands have the highest NCRC? |

### Appendix C: File and Component Reference

| Component | Path / Description |
|-----------|---------------------|
| Agent (state graph) | src/agents/sql_agent.py – BusinessAnalystAgent, nodes: lookup, architect, executor, reporter |
| Domain knowledge | src/knowledge.py – DOMAIN_KNOWLEDGE string |
| Database models | src/database.py – ProductCatalog, ShippedRaw, ConcessionRaw, DatabaseManager |
| Config | src/config.py – Config (DB_URL, OPENAI_*, TAVILY_*) |
| Ingestion | src/ingestion.py – run_smart_ingestion (catalog + transactions) |
| Evaluation | src/evaluation.py – BIAgentEvaluator, run_benchmark, aggregate_results |
| API | src/main.py – FastAPI /ask endpoint |
| Test set | data/test_queries.json |
| Evaluation docs | EVALUATION.md, BEST_EVALUATION_METHODS.md |
| Run instructions | RUN.md |

---

*Document version: 1.0. Generated for the BI Agent thesis project.*
