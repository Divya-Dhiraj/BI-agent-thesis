# Evaluation

## Gold benchmark (`data/test_queries.json`)

Each row: `id`, `question`, `complexity`, `gold_sql` (and optional `category`).

```bash
# All 29 queries → eval/results/* + eval/summary.json
python -m src.evaluation

# Single query (1-based index)
python -m src.evaluation 7

# Range
python -m src.evaluation 1 6

# Another JSON file
python -m src.evaluation --benchmark path/to/tests.json
```

### Outputs

| Path | Content |
|------|---------|
| `eval/results/{id}_gold.csv` | Gold SQL result |
| `eval/results/{id}_generated.csv` | Agent SQL result |
| `eval/results/{id}_gold.sql` | Gold SQL text |
| `eval/results/{id}_generated.sql` | Generated SQL |
| `eval/summary.json` | `match`, errors, latency, aggregates |

**Match** is relaxed: column aliases, numeric tolerance (`numpy.isclose`), and single-row overall return rate vs multi-row monthly breakdown when applicable.

## Legacy mode (pattern / table checks)

For the older test format with `ground_truth.expected_tables` only:

```bash
python -m src.evaluation --legacy data/test_queries.json
```

Writes `evaluation_results.json` (no per-query CSVs in `eval/results/`).
