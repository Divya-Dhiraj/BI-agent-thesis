# Best Evaluation Methods for Your BI Agent

This guide prioritizes evaluation methods by **impact** and **feasibility** for your Text-to-SQL + answer-generation BI agent. You already have a strong base in `src/evaluation.py` and `EVALUATION.md`; here is what to emphasize and what to add.

---

## Tier 1: Core (You Already Have These — Keep Using Them)

| Method | What It Measures | Your Implementation | Target |
|--------|------------------|---------------------|--------|
| **SQL syntax correctness** | Valid SQL parses/explains | `EXPLAIN` in PostgreSQL | >95% |
| **Execution success rate** | Query runs without runtime error | `evaluate_execution()` | >90% |
| **End-to-end success** | Valid SQL + executed + non-empty answer | `success` in results | >85% |
| **Latency** | Total time question → answer | `total_latency` | <10s avg |
| **Answer presence** | Non-empty narrative + optional chart/data | `has_answer`, `has_chart`, `has_raw_data` | All true when applicable |

**Run:** `python -m src.evaluation` (with DB up). Use `data/test_queries.json` or your own JSON test set.

---

## Tier 2: High-Impact Additions (Recommended Next)

### 1. **Execution accuracy (EX)** — Gold standard for Text-to-SQL

**Idea:** For each question, you have a **gold SQL** query. Run both the model’s SQL and the gold SQL; compare result sets (e.g. row count, or sorted row equality).

**Metrics:**
- **Exact set match (EM):** Result sets identical (order-invariant).
- **Execution accuracy (EX):** Same row count and same values (e.g. after normalizing types and order).

**How to add:** Extend `data/test_queries.json` with optional `ground_truth.gold_sql`. In the evaluator, if `gold_sql` exists:
- Execute both `sql_query` and `gold_sql`.
- Compare DataFrames (e.g. sort columns, compare shapes and values).
- Report per-query EX/EM and overall rates.

**Target:** EX >80% on a curated test set.

---

### 2. **Category-level breakdown**

**Idea:** Your test set has `category` (e.g. `simple_aggregation`, `trend_analysis`, `calculated_metric`). Report metrics **per category** so you see which question types fail.

**Metrics:**
- Success rate, syntax accuracy, execution success, latency **by category**.
- Identify weak categories (e.g. joins, time filters, multi-table).

**How to add:** In `aggregate_results()`, group `detailed_results` by `category` (from test case) and compute the same summary stats per group. Add a `by_category` section to the JSON and to `print_summary()`.

**Target:** No category below ~70% success; aim for >85% on “easy” categories.

---

### 3. **Ground-truth SQL pattern / table checks (you already started)**

**Idea:** Even without full gold SQL, check that the generated SQL:
- Uses **expected tables** (`expected_tables`).
- Contains **expected patterns** (`expected_sql_pattern`, e.g. `sum(product_gms)`, `group by`, `ncrc`).

**Metrics:**
- `uses_expected_tables`: all expected tables present.
- `sql_pattern_match`: expected substring in normalized SQL.

**You have this in `evaluate_single_query()`.** Optionally add checks for:
- `expected_columns` (all present in SELECT/list).
- `expected_join` (JOIN present when required).
- `expected_limit` (e.g. LIMIT 10 for top-10 questions).

**Target:** >90% pattern match and table use on tests that define ground truth.

---

### 4. **Answer correctness (when you have expected answers)**

**Idea:** For a subset of questions, maintain an **expected answer** (e.g. one sentence or key numbers). Compare model answer to expected.

**Options:**
- **Semantic similarity:** Embed model answer and expected answer (e.g. `sentence-transformers`), compute cosine similarity. Good for thesis and ablations.
- **Fact overlap:** Extract numbers and key entities; compute overlap or F1.
- **LLM-as-judge:** Use an LLM to score “Does this answer correctly address the question?” (1–5 or binary). Useful when exact text match is not possible.

**How to add:** Add optional `ground_truth.expected_answer` in test JSON. In evaluator:
- If present, compute similarity (and/or fact overlap) and store in result.
- Optionally call an LLM judge and store score.

**Target:** Semantic similarity >0.85 on answered questions; LLM judge “correct” >80%.

---

## Tier 3: Deeper / Research-Oriented

### 5. **Semantic SQL equivalence**

**Idea:** Two different SQL queries can return the same result. Compare by **execution result** only: run gold SQL and model SQL and compare result sets (as in EX above). This is often what people mean by “execution accuracy” in Text-to-SQL benchmarks (Spider, BIRD, etc.).

### 6. **Product lookup quality** (if your agent does ASIN/product search)

**Idea:** For questions like “sales for iPhone”, check that the set of ASINs used matches expected (or overlaps well).

**Metrics:** Precision, recall, F1 of retrieved ASINs vs. a small labeled set.

### 7. **Stability / consistency**

**Idea:** Run the same question multiple times (e.g. 3–5) with temperature=0. Same SQL and same result set → stable. Different but both correct → acceptable. One correct, one wrong → flag for review.

**Metric:** % of questions where all runs are execution-correct.

### 8. **A/B comparisons**

**Idea:** Compare two setups (e.g. two models, two prompts, with/without retries) on the same test set. Report difference in success rate, EX, latency.

---

## Suggested priority order

1. **Keep and monitor** Tier 1 (syntax, execution, E2E success, latency).
2. **Add category breakdown** (quick win, no new labels).
3. **Add execution accuracy (EX)** for questions where you can write gold SQL (start with 10–20).
4. **Add answer correctness** (semantic similarity or LLM judge) for a subset with expected answers.
5. **Expand test set** to 50+ queries covering all categories and edge cases.
6. Optionally add product-lookup metrics, stability, and A/B tests for thesis experiments.

---

## Quick reference: what to report in a thesis

- **SQL:** Syntax accuracy, execution success rate, execution accuracy (EX) vs. gold SQL, optional semantic match.
- **Answer:** Answer generation rate, semantic similarity or LLM-judge score when expected answer exists, chart/data presence.
- **System:** Latency (p50, p95, mean), optional breakdown (lookup, SQL gen, execution, report).
- **Coverage:** Per-category success and EX; error analysis (typical failure modes).

Your existing `evaluation_results.json` and `print_summary()` already support most of this; the enhancements above fill in EX, by-category stats, and answer quality for a complete evaluation story.
