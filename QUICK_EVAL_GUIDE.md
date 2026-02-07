# Quick Start: Evaluating Your BI Agent

This guide will help you quickly start evaluating your BI agent model.

## Prerequisites

1. **Database is set up and data is ingested**
   ```bash
   # Make sure you've run ingestion
   python -m src.ingestion
   ```

2. **Environment variables are configured** (`.env` file)
   - `OPENAI_API_KEY`
   - `DATABASE_URL`

## Quick Evaluation

### Option 1: Run with Default Test Set

```bash
# From project root
python -m src.evaluation
```

This will:
- Load test queries from `data/test_queries.json`
- Run each query through your agent
- Evaluate SQL syntax, execution, and answer quality
- Print a summary and save results to `evaluation_results.json`

### Option 2: Run with Custom Test Set

```bash
# Create your own test_queries.json file, then:
python -m src.evaluation path/to/your/test_queries.json
```

### Option 3: Evaluate a Single Query

```python
from src.evaluation import BIAgentEvaluator

evaluator = BIAgentEvaluator()
result = evaluator.evaluate_single_query("What are total sales?")
print(result)
```

## Understanding the Results

### Summary Metrics

- **Success Rate**: Percentage of queries that completed successfully
- **SQL Syntax Accuracy**: Percentage of syntactically valid SQL queries
- **SQL Execution Success**: Percentage of queries that executed without errors
- **Answer Generation Rate**: Percentage of queries that produced answers

### Performance Metrics

- **Average Latency**: Total time from question to answer
- **Execution Time**: Time spent executing SQL queries

### Error Analysis

The results include detailed error information for failed queries, helping you identify:
- SQL syntax errors
- Runtime execution errors
- Missing answers

## Customizing Evaluation

### Add Your Own Test Queries

Edit `data/test_queries.json` to add questions relevant to your domain:

```json
{
  "question": "Your question here",
  "category": "your_category",
  "ground_truth": {
    "expected_tables": ["shipped_raw"],
    "expected_sql_pattern": "sum(product_gms)"
  }
}
```

### Evaluate Specific Aspects

You can modify `src/evaluation.py` to focus on specific metrics:

- **SQL Quality**: Check `sql_syntax` and `sql_execution` in results
- **Answer Quality**: Check `answer_quality` in results
- **Performance**: Check `total_latency` and `execution_time`

## Next Steps

1. **Baseline Evaluation**: Run the default test set to establish baseline metrics
2. **Identify Weak Areas**: Review error analysis to find common failure patterns
3. **Iterate**: Make improvements and re-run evaluation
4. **Scale Up**: Add more test cases as you identify edge cases

## Advanced Evaluation

For more comprehensive evaluation, see `EVALUATION.md` which covers:
- Semantic correctness evaluation
- Product lookup accuracy
- Answer quality scoring
- Domain-specific business logic validation
- A/B testing frameworks

## Troubleshooting

**"No module named 'src'"**
```bash
export PYTHONPATH=.
python -m src.evaluation
```

**"Database connection error"**
- Check your `.env` file has correct `DATABASE_URL`
- Ensure PostgreSQL is running

**"OpenAI API error"**
- Verify `OPENAI_API_KEY` in `.env`
- Check API quota/rate limits
