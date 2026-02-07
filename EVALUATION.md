# BI Agent Evaluation Framework

This document outlines comprehensive evaluation methods for your BI Agent system. The agent converts natural language questions to SQL queries, executes them, and generates narrative answers with visualizations.

---

## 1. SQL Generation Evaluation

### 1.1 Syntax Correctness
**Metric**: Percentage of syntactically valid SQL queries generated

**Method**:
- Parse each generated SQL query using PostgreSQL's parser
- Track syntax errors (missing keywords, invalid joins, etc.)
- Calculate: `(Valid SQL Queries / Total Queries) × 100`

**Implementation**:
```python
def evaluate_sql_syntax(sql_queries: List[str]) -> Dict:
    valid_count = 0
    errors = []
    for sql in sql_queries:
        try:
            # Use PostgreSQL to validate syntax
            with db.engine.connect() as conn:
                conn.execute(text(f"EXPLAIN {sql}"))
            valid_count += 1
        except Exception as e:
            errors.append({"sql": sql, "error": str(e)})
    return {
        "syntax_accuracy": valid_count / len(sql_queries),
        "errors": errors
    }
```

### 1.2 Semantic Correctness
**Metric**: Alignment with user intent and domain knowledge

**Evaluation Criteria**:
- ✅ Uses correct table names (`shipped_raw`, `concession_raw`)
- ✅ Applies proper join logic (mapped_year/month/week alignment)
- ✅ Selects appropriate columns for the question
- ✅ Applies correct filters (ASIN, date ranges, etc.)
- ✅ Uses correct aggregations (SUM, COUNT, AVG)
- ✅ Follows business rules (e.g., FBA COGS = 0)

**Method**: Manual review or LLM-based evaluation comparing generated SQL to expected SQL for a test set.

### 1.3 Domain Knowledge Adherence
**Metric**: Correctness of business logic implementation

**Test Cases**:
- **Join Logic**: Does it use `mapped_year/month` for linking returns to sales?
- **COGS Calculation**: Does it handle FBA vs RET fulfillment channels correctly?
- **Metric Definitions**: Does it calculate Return Rate, Net Margin correctly?
- **Flag Interpretation**: Does it correctly interpret `is_andon_cord`, `is_hrr_asin`?

---

## 2. Query Execution Evaluation

### 2.1 Execution Success Rate
**Metric**: Percentage of queries that execute without errors

**Track**:
- SQL errors (syntax, missing columns, type mismatches)
- Timeout errors
- Empty result sets (may be valid or indicate query issues)

**Implementation**:
```python
def evaluate_execution_success(queries: List[Dict]) -> Dict:
    results = {
        "success": 0,
        "syntax_error": 0,
        "runtime_error": 0,
        "empty_result": 0,
        "timeout": 0
    }
    for query_data in queries:
        sql = query_data["sql"]
        try:
            with db.engine.connect() as conn:
                df = pd.read_sql(text(sql), conn)
                if df.empty:
                    results["empty_result"] += 1
                else:
                    results["success"] += 1
        except ProgrammingError as e:
            results["syntax_error"] += 1
        except Exception as e:
            results["runtime_error"] += 1
    return results
```

### 2.2 Retry Mechanism Effectiveness
**Metric**: Success rate after retries

**Track**:
- Initial failure rate
- Success rate after 1st retry
- Success rate after 2nd retry
- Queries that fail after all retries

---

## 3. Product Lookup Evaluation

### 3.1 Search Accuracy
**Metric**: Relevance of products found for user queries

**Test Cases**:
- "iPhone sales" → Should find Apple products with "iPhone" in name
- "Samsung phones" → Should find Samsung brand products
- "premium smartphones" → Should find products with `is_premium_flag = 'Y'`

**Method**:
```python
def evaluate_product_lookup(test_cases: List[Dict]) -> Dict:
    """
    test_cases: [{"query": "iPhone", "expected_asins": ["B08...", ...], "expected_count": 5}]
    """
    results = []
    for case in test_cases:
        agent_result = agent.ask(case["query"])
        found_asins = agent_result.get("considered_products", [])
        
        precision = len(set(found_asins) & set(case["expected_asins"])) / len(found_asins) if found_asins else 0
        recall = len(set(found_asins) & set(case["expected_asins"])) / len(case["expected_asins"]) if case["expected_asins"] else 0
        
        results.append({
            "query": case["query"],
            "precision": precision,
            "recall": recall,
            "f1": 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        })
    return results
```

### 3.2 Hybrid Search Performance
**Metric**: Comparison of vector search vs keyword search vs hybrid

**A/B Testing**:
- Test vector-only search
- Test keyword-only search (full-text)
- Test hybrid (current implementation)
- Compare precision/recall for each

---

## 4. Answer Quality Evaluation

### 4.1 Correctness
**Metric**: Accuracy of the narrative answer compared to ground truth

**Method**: Create a test set with:
- Natural language questions
- Expected SQL queries (ground truth)
- Expected answers (ground truth)

**Evaluation**:
- **Exact Match**: Does the answer match expected answer?
- **Semantic Similarity**: Use embeddings to compare answer similarity
- **Factual Accuracy**: Does the answer correctly interpret the data?

**Implementation**:
```python
from sentence_transformers import SentenceTransformer

def evaluate_answer_correctness(predicted: str, expected: str) -> Dict:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Semantic similarity
    pred_emb = model.encode(predicted)
    exp_emb = model.encode(expected)
    similarity = cosine_similarity([pred_emb], [exp_emb])[0][0]
    
    # Extract key facts (numbers, trends, products)
    pred_facts = extract_facts(predicted)  # Extract numbers, product names
    exp_facts = extract_facts(expected)
    
    fact_overlap = len(set(pred_facts) & set(exp_facts)) / len(set(exp_facts))
    
    return {
        "semantic_similarity": similarity,
        "factual_overlap": fact_overlap
    }
```

### 4.2 Completeness
**Metric**: Does the answer address all aspects of the question?

**Checklist**:
- ✅ Direct answer to the question
- ✅ Supporting data/evidence
- ✅ Explanation of "why" (if requested)
- ✅ Chart/visualization (if appropriate)

### 4.3 Relevance
**Metric**: Is the answer relevant to the question asked?

**Method**: Use LLM-based evaluation:
```python
def evaluate_relevance(question: str, answer: str) -> float:
    prompt = f"""
    Rate the relevance of this answer to the question (0-1):
    Question: {question}
    Answer: {answer}
    
    Output only a number between 0 and 1.
    """
    score = llm.invoke(prompt).content
    return float(score.strip())
```

---

## 5. System Performance Evaluation

### 5.1 Latency Metrics
**Track**:
- **Total Response Time**: Time from question to final answer
- **Lookup Time**: Time for product search
- **SQL Generation Time**: Time to generate SQL
- **Query Execution Time**: Database query time
- **Answer Generation Time**: Time to generate narrative

**Implementation**:
```python
import time

def measure_latency(question: str) -> Dict:
    start = time.time()
    
    lookup_start = time.time()
    # ... lookup phase
    lookup_time = time.time() - lookup_start
    
    sql_start = time.time()
    # ... SQL generation
    sql_time = time.time() - sql_start
    
    exec_start = time.time()
    # ... query execution
    exec_time = time.time() - exec_start
    
    report_start = time.time()
    # ... answer generation
    report_time = time.time() - report_start
    
    total_time = time.time() - start
    
    return {
        "total_latency": total_time,
        "lookup_latency": lookup_time,
        "sql_generation_latency": sql_time,
        "execution_latency": exec_time,
        "reporting_latency": report_time
    }
```

### 5.2 Throughput
**Metric**: Queries processed per second/minute

**Test**: Run N concurrent queries and measure:
- Average queries per second
- Peak capacity
- Degradation under load

### 5.3 Resource Usage
**Track**:
- API calls to OpenAI (cost tracking)
- Database query complexity
- Memory usage
- CPU usage

---

## 6. User Experience Evaluation

### 6.1 Question Coverage
**Metric**: Percentage of user questions successfully answered

**Categories to Test**:
- **Simple Queries**: "What are total sales?"
- **Product-Specific**: "How many iPhones were sold?"
- **Trend Analysis**: "Show sales trends over time"
- **Comparative**: "Compare Apple vs Samsung"
- **Complex Multi-Step**: "Which products have high return rates and low margins?"

### 6.2 Error Handling
**Metric**: Quality of error messages and recovery

**Evaluate**:
- Are error messages user-friendly?
- Does the system gracefully handle edge cases?
- Does retry logic improve outcomes?

### 6.3 Chart Quality
**Metric**: Appropriateness and correctness of generated charts

**Check**:
- Chart type matches data (bar for categories, line for trends)
- Data correctly mapped to chart
- Labels and titles are meaningful

---

## 7. Domain-Specific Evaluation

### 7.1 Business Logic Correctness
**Test Cases**:

1. **Return Rate Calculation**:
   - Question: "What is the return rate for iPhone?"
   - Expected: `(conceded_units / shipped_units) * 100`
   - Verify: Uses correct tables and date alignment

2. **Net Margin Calculation**:
   - Question: "What is the net margin?"
   - Expected: `product_gms - shipped_cogs - ncrc`
   - Verify: Includes all components

3. **FBA COGS Handling**:
   - Question: "What is the COGS for FBA products?"
   - Expected: Should be 0 or handled correctly
   - Verify: Filter by `fulfillment_channel = 'FBA'`

4. **Andon Cord Interpretation**:
   - Question: "Which products have safety issues?"
   - Expected: Filter by `is_andon_cord = 'Y'`
   - Verify: Correctly identifies stopped sales

### 7.2 Date Alignment
**Critical Test**: Verify `mapped_year/month` usage for joins

**Test**:
```sql
-- Should use mapped dates for returns
SELECT * FROM concession_raw c
JOIN shipped_raw s ON 
    c.asin = s.asin AND
    c.mapped_year = s.year AND
    c.mapped_month = s.month
```

---

## 8. Benchmark Dataset Creation

### 8.1 Test Query Set
Create a comprehensive test set with:

```python
BENCHMARK_QUERIES = [
    {
        "question": "What are total sales in 2023?",
        "category": "simple_aggregation",
        "expected_tables": ["shipped_raw"],
        "expected_columns": ["product_gms"],
        "expected_sql_pattern": "SELECT SUM(product_gms)",
        "ground_truth_answer": "Total sales were $X in 2023"
    },
    {
        "question": "Which iPhone models have the highest return rates?",
        "category": "product_specific",
        "expected_tables": ["shipped_raw", "concession_raw"],
        "expected_join": True,
        "expected_filter": "iPhone",
        "ground_truth_answer": "iPhone X has 15% return rate..."
    },
    # ... more test cases
]
```

### 8.2 Ground Truth Collection
1. **Manual SQL Writing**: Write correct SQL for each test question
2. **Expert Review**: Have domain experts validate answers
3. **Data Validation**: Verify answers against known data summaries

---

## 9. Automated Evaluation Script

### 9.1 Evaluation Pipeline
```python
# evaluation.py
import json
from typing import List, Dict
from src.agents.sql_agent import BusinessAnalystAgent

class BIAgentEvaluator:
    def __init__(self):
        self.agent = BusinessAnalystAgent()
        self.results = []
    
    def run_evaluation(self, test_set: List[Dict]) -> Dict:
        """Run full evaluation suite"""
        for test_case in test_set:
            result = self.evaluate_single_query(test_case)
            self.results.append(result)
        
        return self.aggregate_results()
    
    def evaluate_single_query(self, test_case: Dict) -> Dict:
        """Evaluate one query"""
        question = test_case["question"]
        
        # Get agent response
        response = self.agent.ask(question)
        
        # Evaluate SQL
        sql_metrics = self.evaluate_sql(response["sql_query"], test_case)
        
        # Evaluate answer
        answer_metrics = self.evaluate_answer(
            response["answer"], 
            test_case.get("ground_truth_answer")
        )
        
        # Evaluate execution
        exec_metrics = self.evaluate_execution(response)
        
        return {
            "question": question,
            "sql_metrics": sql_metrics,
            "answer_metrics": answer_metrics,
            "execution_metrics": exec_metrics
        }
    
    def aggregate_results(self) -> Dict:
        """Calculate overall metrics"""
        return {
            "total_queries": len(self.results),
            "sql_syntax_accuracy": self._calc_avg("sql_metrics.syntax_valid"),
            "sql_semantic_accuracy": self._calc_avg("sql_metrics.semantic_match"),
            "execution_success_rate": self._calc_avg("execution_metrics.success"),
            "answer_quality_score": self._calc_avg("answer_metrics.quality_score"),
            "average_latency": self._calc_avg("execution_metrics.latency")
        }
```

---

## 10. Evaluation Metrics Summary

### Key Performance Indicators (KPIs)

| Metric | Target | Measurement |
|--------|--------|-------------|
| SQL Syntax Accuracy | >95% | Automated parsing |
| SQL Semantic Correctness | >85% | Manual/LLM review |
| Execution Success Rate | >90% | After retries |
| Product Lookup Precision | >80% | Test set with known products |
| Answer Quality Score | >0.8 | Semantic similarity + factual accuracy |
| Average Latency | <5s | End-to-end timing |
| Question Coverage | >90% | Successful answers / total questions |

### Reporting
Generate evaluation reports with:
- Overall scores
- Per-category breakdowns
- Error analysis
- Improvement recommendations

---

## 11. Continuous Evaluation

### 11.1 Logging
Add comprehensive logging to track:
- All user questions
- Generated SQL queries
- Execution results
- Errors and retries
- Response times

### 11.2 A/B Testing
Compare different versions:
- Different LLM models
- Different prompts
- Different retry strategies
- Vector vs keyword search

### 11.3 User Feedback
Collect:
- User satisfaction ratings
- Answer helpfulness scores
- Correction requests

---

## 12. Implementation Checklist

- [ ] Create benchmark test set (50+ queries)
- [ ] Implement SQL syntax validator
- [ ] Implement SQL semantic evaluator
- [ ] Create ground truth dataset
- [ ] Build automated evaluation pipeline
- [ ] Add performance monitoring
- [ ] Set up logging infrastructure
- [ ] Create evaluation dashboard
- [ ] Run baseline evaluation
- [ ] Document evaluation results

---

## Next Steps

1. **Start with a small test set** (10-20 queries) covering different question types
2. **Establish baseline metrics** for current system
3. **Identify weak areas** (e.g., complex joins, date alignment)
4. **Iterate and improve** based on evaluation results
5. **Scale up** to larger test sets as confidence grows

This evaluation framework will help you systematically assess and improve your BI agent's performance throughout your thesis work.
