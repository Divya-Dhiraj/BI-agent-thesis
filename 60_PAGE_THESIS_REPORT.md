# Comprehensive 60-Page Thesis Strategy & Outline
**Topic**: A Natural Language Interface for Business Intelligence: An Agent-Based System for Text-to-SQL, Product Lookup, and Narrative Reporting

Writing a 60-page technical thesis requires expanding beyond high-level summaries into detailed architectural discussions, methodological justifications, exhaustive literature reviews, and deep analysis of results. This document breaks down your project into a structured, chapter-by-chapter guide with specific page targets and content recommendations sourced directly from your codebase.

---

## Overall Page Budget & Breakdown (Target: ~60 Pages)

| Chapter | Title | Estimated Pages | Focus |
|---------|-------|-----------------|-------|
| 1 | Introduction | 4 - 5 | Problem statement, motivation, domain overview, objectives. |
| 2 | Background & Literature Review | 8 - 10 | NLIDB history, LLMs in Text-to-SQL, Agent workflows, BI systems. |
| 3 | Domain Context & Data Engineering | 6 - 8 | The E-commerce Returns dataset, schema, domain logic, ingestion. |
| 4 | System Architecture & Methodology | 12 - 15 | LangGraph agent, the 5 phases, prompt engineering, retry logic. |
| 5 | Implementation Details | 8 - 10 | Tech stack, vector search, database interactions, FastAPI. |
| 6 | Evaluation & Results | 10 - 12 | Benchmark setup, metrics, quantitative results, error analysis. |
| 7 | Conclusion & Future Work | 3 - 4 | Summary of contributions, limitations, and future directions. |
| 8 | References | 3 - 4 | Academic citations and tool documentation. |
| 9 | Appendices | 4+ | Schema definitions, sample Queries, extensive SQL examples. |
| **Total** | | **~58 - 68 Pages** | |

---

## Chapter-by-Chapter Writing Guide

### Chapter 1: Introduction (4 - 5 Pages)
*   **Motivation (1-2 pages)**: Start broad. Discuss the exploding volume of data in modern enterprises and the bottleneck created when only SQL-proficient analysts can extract insights. Introduce the need for democratized, conversational Business Intelligence (BI).
*   **Problem Statement (1 page)**: Define the specific problem. It is not just about Text-to-SQL; it's about domain-specific correctness. Highlight the challenges: mapping natural language to complex schemas (like joining `shipped_raw` and `concession_raw` via mapped dates), handling product disambiguation (e.g., matching "iPhone" to ASINs), and providing actionable narratives.
*   **Objectives & Contributions (1 page)**: List your practical contributions. 
    *   Building a multi-phase LangGraph agent.
    *   Implementing a hybrid lookup mechanism (brand vs. item).
    *   Injecting deterministic domain knowledge into the prompt.
    *   Implementing a self-correcting retry loop for failed SQL.
*   **Thesis Structure (0.5 pages)**: A roadmap to the rest of the document.

### Chapter 2: Background & Literature Review (8 - 10 Pages)
*To fill 10 pages here, you need to cite actual academic papers and thoroughly explain their approaches.*
*   **Natural Language Interfaces to Databases (3 pages)**: Trace the history from early rule-based systems to seq2seq neural networks, culminating in modern LLM approaches. Discuss the paradigm shift from training custom models to prompt-engineering frontier LLMs.
*   **Text-to-SQL Benchmarks (2.5 pages)**: Discuss Spider, BIRD, Spider 2.0, and BEAVER. Explain why these benchmarks are important but often fail to capture enterprise-specific business logic (e.g., BIRD focuses on dirty data, but enterprise BI heavily relies on domain-specific aggregations and metrics like CIR%).
*   **Agentic Workflows in AI (2.5 pages)**: Explain the concept of LLM Agents (ReAct, state graphs). Discuss why a single-prompt approach fails for BI, necessitating your LangGraph multi-step approach (Lookup -> Architect -> Execute -> Report).
*   **Conversational BI Platforms (2 pages)**: Analyze existing systems (InsightBench, DataLab). Contrast them with your requirement for explicit product catalog lookup prior to query generation.

### Chapter 3: Domain Context & Data Engineering (6 - 8 Pages)
*This chapter elevates the thesis by showing deep domain understanding, moving beyond generic AI into applied business data.*
*   **The E-commerce Smartphone Domain (2 pages)**: Explain the specifics of the German marketplace (Marketplace 4). Describe the dynamics of tracking outbound shipments vs. inbound returns.
*   **Data Dictionary & Schema (3 pages)**: Detail the two primary tables:
    *   `shipped_raw` (The Revenue Side): Explain `product_gms`, `shipped_cogs`, `fulfillment_channel` rules (FBA vs RET).
    *   `concession_raw` (The Cost Side): Explain `conceded_units`, `ncrc` (Net Cost of Returns - the total loss to Amazon), `defect_category`, and critical flags like `is_andon_cord` (safety/quality defects).
*   **The Golden Linking Rule (1.5 pages)**: This is a major technical hurdle you solved. Explain why `c.asin = s.asin` is not enough, and why joining on `c.mapped_year = s.year`, `mapped_month`, and `mapped_week` is strictly necessary to correctly calculate return rates (CIR%).
*   **Data Ingestion & Cataloging (1.5 pages)**: Describe how the TSV data is cleaned and loaded. Detail the `product_catalog` table, the extraction of unique ASINs, and the creation of the `search_vector` (`tsvector`) for PostgreSQL full-text search.

### Chapter 4: System Architecture & Methodology (12 - 15 Pages)
*This is the core of your thesis. Devote multiple pages to each node of your LangGraph state machine.*
*   **Overview of the Multi-Phase Agent (2 pages)**: Introduce `BusinessAnalystAgent` and the `AgentState` typed dictionary. Provide a diagram showing the node graph: Lookup -> Architect -> Executor (Conditional Retry) -> Reporter.
*   **Phase 1: Product Lookup Node (3 pages)**: Dive deep into `node_lookup`. Explain the LLM prompt that extracts `search_term` and `filter_mode` ("brand", "item", or "both"). Give examples (e.g., "iPhone" -> item, "Apple" -> brand, "Samsung" -> both). Explain how this pre-processing prevents the SQL generator from hallucinating IN-lists or using bad ILIKE clauses.
*   **Phase 2: The Architect / Reasoning Engine (4 pages)**: This is crucial. 
    *   Explain how `filter_logic` is dynamically built based on the lookup phase.
    *   **The Semantic Brain**: Spend 2 pages detailing `DOMAIN_KNOWLEDGE` from `src/knowledge.py`. Explain the philosophy of explicitly defining calculated metrics (Net Margin, Return Rate %) and Query Strategies inside the system prompt. Explain why this zero-shot, highly-contextual prompting works better than fine-tuning for rapidly changing business rules.
*   **Phase 3 & 4: Executor & Self-Correction (2 pages)**: Detail the `node_executor` and `check_status`. Explain the failsafe mechanism: how `pandas.read_sql` catches database errors (like missing columns `c.asp_bucket`), feeds the exact `pg8000.dbapi.ProgrammingError` back into the state, and transitions back to `architect` up to 3 times.
*   **Phase 5: The Reporter (2 pages)**: Explain `node_reporter`. Discuss how the data preview (truncated to 2500 chars) is fed to the LLM to generate an executive narrative and a structured JSON chart configuration. 

### Chapter 5: Implementation Details (8 - 10 Pages)
*   **Technology Stack Justification (2 pages)**: Why Python, PostgreSQL, LangGraph, and ChatOpenAI (GPT-4-turbo)? Discuss trade-offs (e.g., why PostgreSQL with `tsvector` instead of ElasticSearch).
*   **Database Interactions (2 pages)**: Talk about SQLAlchemy ORM usage in `src/database.py`. Show snippets of how connections are explicitly managed via context managers.
*   **Vector Search & Full-Text Search integration (2.5 pages)**: Even if vector search is partially future work, explain the `search_vector @@ websearch_to_tsquery('simple', :term)` logic. Explain the inclusion of `pgvector` and the `HNSW` index on the 1536-dimensional embeddings.
*   **API & User Interface (2 pages)**: Describe the FastAPI implementation (`POST /ask`), thread management (`thread_id`), and how the Streamlit dashboard connects to the backend API to render narratives and dynamic charts.

### Chapter 6: Evaluation & Results (10 - 12 Pages)
*Your `eval/summary.json` provides fantastic data for this chapter.*
*   **Evaluation Methodology (2 pages)**: Explain the "gold_sql_benchmark". Detail the 45 curated queries categorized into easy (15), medium (15), and hard (15). Explain the metrics: Execution Success Rate, and Execution Accuracy (does the execution of the generated query match the gold query results?).
*   **Quantitative Results (3 pages)**: Present the data from `summary.json`.
    *   **Execution Success**: Present the 97.7% execution success rate. (44 out of 45 queries resulted in executable SQL). Explain how the retry loop contributed to this high number.
    *   **Execution Accuracy**: Present the 40% exact match rate (18 out of 45). Break it down by complexity: Easy (9/15, 60%), Medium (7/15, 46%), Hard (2/15, 13%). Create tables and charts visualizing this drop-off.
*   **Qualitative & Error Analysis (5-6 pages)**: *This is where you earn high marks.* Select specific failing queries from `summary.json` and dissect them.
    *   **Case Study 1: Easy Failures**: Look at `q10_easy` ("distinct iPhone ASINs was shipped"). The gold query counts `DISTINCT asin`, but your agent generated `COUNT(DISTINCT CAST(s.asin AS TEXT))`. Explain how this technically isn't wrong but fails strict exact-match evaluation, highlighting the limitations of EX metrics.
    *   **Case Study 2: Join Complexity (Medium)**: Analyze `q29_medium` (sales and return rate by fulfillment channel). The agent attempts complex CTEs (`WITH sales... WITH returns_mapped...`) and misses exact match.
    *   **Case Study 3: The Single Execution Failure (Hard)**: Analyze query `q38_hard` ("sales by avg selling price bucket"). The agent hallucinated `c.asp_bucket` when it should have used `s.asp_bucket` (or the column didn't exist in that table). Display the exact SQLAlchemy error `column c.asp_bucket does not exist` and explain why the LLM failed to self-correct this within 3 tries.
*   **Latency Analysis (1 page)**: Discuss the timing. Queries take between 5 seconds (e.g., `q5_easy`) to 25.95 seconds (`q45_hard`). Discuss user experience implications.

### Chapter 7: Conclusion & Future Work (3 - 4 Pages)
*   **Summary of Findings (1.5 pages)**: Recap that you successfully built a resilient, agentic pipeline that achieved 97.7% execution success on complex enterprise schema, validating the approach of injecting structured domain knowledge.
*   **Limitations (1 page)**: Acknowledge the 40% exact match rate. Note that BIRD and Spider benchmarks show that enterprise-level SQL generation is still incredibly hard. Acknowledge latency issues (multi-step agents are slow).
*   **Future Work (1.5 pages)**: 
    *   Transitioning from purely full-text search to true hybrid search (combining exact keyword match with the `pgvector` 1536d embeddings already in the DB).
    *   LLM-as-a-judge for semantic evaluation rather than brittle exact-match dataframe comparisons.
    *   Cross-session memory for follow-up questions.

### Chapter 8: References (3 - 4 Pages)
*   Ensure rigorous formatting. Cite Spider (Yu et al.), BIRD (Li et al.), BEAVER, LangGraph documentation, PostgreSQL text search documentation, paper on LLM Agents (e.g., ReAct by Yao et al.).

### Chapter 9: Appendices (4+ Pages)
*   **Appendix A: Full Schema**: Show the exact `CREATE TABLE` and `CREATE INDEX` statements.
*   **Appendix B: Domain Knowledge Prompt**: Include the full text of `DOMAIN_KNOWLEDGE` from `src/knowledge.py`.
*   **Appendix C: Extensive Test Set**: Print out a large subset of the 45 test queries with their Gold SQL vs. Generated SQL to provide transparency to the graders.

---

## Actionable Next Steps for You
1.  **Draft Chapter 4 (Architecture)** first. It is the easiest to write because you just look at `src/agents/sql_agent.py` and describe what each function does in plain English paragraphs. You can easily write 10-15 pages just describing the input, logic, and output of `node_lookup`, `node_architect`, `node_executor`, and `node_reporter`.
2.  **Draft Chapter 6 (Evaluation)** second. Open `eval/summary.json` and start pulling out specific queries that failed. Dedicate half a page to each interesting failure, explaining *why* the LLM wrote what it wrote.
3.  **Expand Chapter 3 (Domain Context)** by explaining the Amazon-specific metrics (`ncrc`, `andon_cord`, `mapped_year`) to an academic audience who might not know e-commerce terms.
4.  **Literature Review**: Dedicate a few days to reading papers like "Spider 2.0" and "BIRD" to write a robust 8-page literature review.

*Generated by AI Assistant based on a deep pass of the `BI-agent-thesis` codebase.*
