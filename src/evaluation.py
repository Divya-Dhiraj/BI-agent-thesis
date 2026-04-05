"""
Evaluate the BI agent against data/test_queries.json (id, question, gold_sql, complexity).

Outputs:
  eval/results/{id}_gold.csv, {id}_generated.csv, {id}_gold.sql, {id}_generated.sql
  eval/summary.json — per-question match, SQL, execution flags, aggregates

Run (project root):
  python -m src.evaluation                 # all queries
  python -m src.evaluation 5               # only 5th query (1-based index)
  python -m src.evaluation 3 10            # queries 3–10 inclusive
  python -m src.evaluation --benchmark path/to/other.json   # alternate test file

Legacy BIAgentEvaluator-style run (category ground_truth, no gold match files):
  python -m src.evaluation --legacy [test_file.json]
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import text

from src.agents.sql_agent import BusinessAnalystAgent
from src.database import DatabaseManager

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEST_PATH = PROJECT_ROOT / "data" / "test_queries.json"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"
SUMMARY_PATH = PROJECT_ROOT / "eval" / "summary.json"

RTOL = 1e-6
ATOL = 1e-3

COLUMN_ALIASES = {
    "total_sales": ["total_sales", "total_sales_gms", "total_revenue", "revenue"],
    "total_shipped_units": ["total_shipped_units", "shipped_units", "units_sold", "units", "shipped_units_samsung"],
    "total_conceded_units": ["total_conceded_units", "conceded_units", "returned_units"],
    "total_ncrc": ["total_ncrc", "ncrc"],
    "return_rate_pct": ["return_rate_pct", "return_rate", "return_rate_percent"],
    "net_margin": ["net_margin"],
    "distinct_products": ["distinct_products", "count", "high_return_rate_products", "product_count"],
    # Gold COUNT(DISTINCT ...) often aliases as product_count; models may use descriptive names.
    "product_count": [
        "product_count",
        "distinct_products",
        "count",
        "distinct_iphone_asins_shipped",
        "distinct_asins",
        "num_distinct_asins",
    ],
    "total_revenue": ["total_revenue", "revenue", "total_sales_gms"],
    "return_count": ["return_count", "return_records", "concession_records"],
    "item_count": ["item_count", "concession_records", "return_records"],
    "total_units": ["total_units", "conceded_units", "shipped_units", "returned_units"],
    "total_cogs": ["total_cogs", "shipped_cogs", "total_cost_of_goods_sold"],
    "avg_selling_price": ["avg_selling_price", "asp", "average_selling_price"],
    "group_name": ["group_name", "product_family", "brand_name"],
}


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_test_queries(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Test queries not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("test_queries.json must be a JSON array")
    return data


def _gold_sql_for_item(item: Dict[str, Any]) -> Optional[str]:
    g = item.get("gold_sql")
    if g:
        return str(g).strip()
    gt = item.get("ground_truth") or {}
    g = gt.get("gold_sql")
    return str(g).strip() if g else None


def run_sql_to_dataframe(db_manager: DatabaseManager, sql: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if not sql or not sql.strip():
        return None, "No SQL provided"
    try:
        with db_manager.engine.connect() as conn:
            df = pd.read_sql(text(sql.strip()), conn)
        return df, None
    except Exception as e:
        return None, str(e)


def normalize_for_comparison(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    df = df.reindex(sorted(df.columns), axis=1)
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values(by=list(df.columns)).reset_index(drop=True)
    return df


def _align_frames_by_shared_keys(gold_n: pd.DataFrame, gen_n: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Sort both frames the same way on columns present in both, so row order matches for grouped results."""
    common = sorted(set(gold_n.columns) & set(gen_n.columns))
    if not common:
        return gold_n, gen_n
    gold_n = gold_n.sort_values(by=common).reset_index(drop=True)
    gen_n = gen_n.sort_values(by=common).reset_index(drop=True)
    return gold_n, gen_n


def _series_close(g: pd.Series, p: pd.Series) -> bool:
    g = g.reset_index(drop=True)
    p = p.reset_index(drop=True)
    if len(g) != len(p):
        return False
    gn = pd.to_numeric(g, errors="coerce")
    pn = pd.to_numeric(p, errors="coerce")
    if gn.notna().all() and pn.notna().all():
        return bool(np.isclose(gn.astype(float), pn.astype(float), rtol=RTOL, atol=ATOL, equal_nan=True).all())
    return g.astype(str).fillna("").equals(p.astype(str).fillna(""))


def _find_matching_gen_column(gold_col: str, gen_columns: List[str]) -> Optional[str]:
    gen_set = set(gen_columns)
    gold_lower = gold_col.lower()
    if gold_col in gen_set:
        return gold_col
    low_map = {c.lower(): c for c in gen_columns}
    if gold_lower in low_map:
        return low_map[gold_lower]
    for canonical, aliases in COLUMN_ALIASES.items():
        if gold_col == canonical or gold_lower == canonical.lower():
            for a in aliases:
                if a in gen_set:
                    return a
                if a.lower() in low_map:
                    return low_map[a.lower()]
            break
    for canonical, aliases in COLUMN_ALIASES.items():
        if gold_col == canonical or gold_lower == canonical.lower():
            for c in gen_columns:
                if c in aliases or c.lower() in {x.lower() for x in aliases}:
                    return c
            break
    for c in gen_columns:
        if gold_lower in c.lower() or c.lower() in gold_lower:
            return c
    # Gold often aliases CIR as cir_pct_YYYY; models use return_rate_pct / return_rate.
    if re.fullmatch(r"cir_pct_\d{4}", gold_lower):
        for name in ("return_rate_pct", "return_rate", "return_rate_percent"):
            if name in low_map:
                return low_map[name]
    return None


def _single_aggregate_return_rate_match(gold_df: pd.DataFrame, gen_df: pd.DataFrame) -> bool:
    if gold_df is None or gen_df is None or len(gold_df) != 1 or gold_df.empty or gen_df.empty:
        return False
    gold_col = gold_df.columns[0]
    if gold_col.lower() not in {"return_rate_pct", "return_rate", "return_rate_percent"}:
        return False
    gold_val = pd.to_numeric(gold_df.iloc[0, 0], errors="coerce")
    if pd.isna(gold_val):
        return False
    gen_lower = {c.lower(): c for c in gen_df.columns}
    if "shipped_units" in gen_lower and "conceded_units" in gen_lower:
        s = gen_df[gen_lower["shipped_units"]].astype(float).sum()
        c = gen_df[gen_lower["conceded_units"]].astype(float).sum()
        if s and s > 0:
            computed = (c * 100.0) / s
            return bool(np.isclose(computed, float(gold_val), rtol=RTOL, atol=ATOL))
    return False


def _single_scalar_pair_match(gold_df: pd.DataFrame, gen_df: pd.DataFrame) -> bool:
    """Gold and gen each have one row and one column: compare values, ignore header names."""
    if (
        gold_df is None
        or gen_df is None
        or len(gold_df) != 1
        or len(gen_df) != 1
        or len(gold_df.columns) != 1
        or len(gen_df.columns) != 1
    ):
        return False
    g = gold_df.iloc[:, 0]
    p = gen_df.iloc[:, 0]
    return _series_close(g, p)


def dataframes_match(gold_df: pd.DataFrame, gen_df: pd.DataFrame) -> bool:
    if gold_df is None and gen_df is None:
        return True
    if gold_df is None or gen_df is None:
        return False
    if gold_df.empty and gen_df.empty:
        return True
    if gold_df.empty or gen_df.empty:
        return False

    gold_n = normalize_for_comparison(gold_df.copy())
    gen_n = normalize_for_comparison(gen_df.copy())
    gold_n, gen_n = _align_frames_by_shared_keys(gold_n, gen_n)

    if len(gold_n) == 1 and len(gold_n.columns) == 1 and len(gen_n) > 1:
        if _single_aggregate_return_rate_match(gold_n, gen_n):
            return True

    if _single_scalar_pair_match(gold_n, gen_n):
        return True

    if len(gold_n) != len(gen_n):
        return False

    gold_to_gen: Dict[str, str] = {}
    for gcol in gold_n.columns:
        m = _find_matching_gen_column(gcol, list(gen_n.columns))
        if m is not None:
            gold_to_gen[gcol] = m

    if not gold_to_gen:
        return False

    for gcol, gencol in gold_to_gen.items():
        if not _series_close(gold_n[gcol], gen_n[gencol]):
            return False
    return True


def save_result_csv(df: Optional[pd.DataFrame], path: Path) -> None:
    if df is not None:
        df.to_csv(path, index=False)
    else:
        path.write_text("", encoding="utf-8")


def save_sql(sql: Optional[str], path: Path) -> None:
    path.write_text(sql if sql else "-- No SQL\n", encoding="utf-8")


def run_gold_benchmark(
    test_path: Path,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> Dict[str, Any]:
    ensure_dirs()
    test_queries = load_test_queries(test_path)
    if start is not None and end is not None:
        test_queries = test_queries[start - 1 : end]
        logger.info(f"Evaluating queries {start}–{end} ({len(test_queries)} items)")
    elif start is not None:
        test_queries = test_queries[start - 1 : start]
        logger.info(f"Evaluating query {start} only")

    db_manager = DatabaseManager()
    agent = BusinessAnalystAgent()

    summary: Dict[str, Any] = {
        "evaluator": "gold_sql_benchmark",
        "test_file": str(test_path),
        "per_question": [],
        "aggregate": {
            "total": 0,
            "with_gold_sql": 0,
            "execution_success_gold": 0,
            "execution_success_generated": 0,
            "result_match": 0,
            "by_complexity": {},
        },
    }
    agg = summary["aggregate"]

    for idx, item in enumerate(test_queries):
        global_i = (start - 1 + idx + 1) if start else (idx + 1)
        qid = item.get("id") or f"q{global_i}"
        question = item.get("question", "")
        gold_sql = _gold_sql_for_item(item)
        complexity = item.get("complexity") or item.get("category") or "unknown"

        row: Dict[str, Any] = {
            "id": qid,
            "question": question[:200] + "..." if len(question) > 200 else question,
            "complexity": complexity,
            "gold_sql": gold_sql,
            "generated_sql": None,
            "execution_ok_gold": False,
            "execution_ok_generated": False,
            "match": False,
            "match_skipped_no_gold": gold_sql is None,
            "error_gold": None,
            "error_generated": None,
            "latency_seconds": None,
        }

        agg["total"] += 1
        if complexity not in agg["by_complexity"]:
            agg["by_complexity"][complexity] = {"total": 0, "exec_gen_ok": 0, "match": 0}
        agg["by_complexity"][complexity]["total"] += 1

        t0 = time.time()
        thread_id = f"eval_{qid}_{int(t0 * 1000)}"
        try:
            response = agent.ask(question, thread_id=thread_id)
        except Exception as e:
            logger.error(f"Agent error ({qid}): {e}")
            response = {"sql_query": None, "answer": str(e)}

        row["latency_seconds"] = round(time.time() - t0, 2)
        gen_sql = response.get("sql_query")
        row["generated_sql"] = gen_sql

        gold_df: Optional[pd.DataFrame] = None
        gen_df: Optional[pd.DataFrame] = None

        if gold_sql:
            agg["with_gold_sql"] += 1
            gold_df, err_g = run_sql_to_dataframe(db_manager, gold_sql)
            row["execution_ok_gold"] = err_g is None
            row["error_gold"] = err_g
            if err_g is None:
                agg["execution_success_gold"] += 1
            save_result_csv(gold_df, RESULTS_DIR / f"{qid}_gold.csv")
            save_sql(gold_sql, RESULTS_DIR / f"{qid}_gold.sql")
        else:
            (RESULTS_DIR / f"{qid}_gold.csv").write_text("", encoding="utf-8")
            save_sql(None, RESULTS_DIR / f"{qid}_gold.sql")

        if gen_sql:
            gen_df, err_p = run_sql_to_dataframe(db_manager, gen_sql)
            row["execution_ok_generated"] = err_p is None
            row["error_generated"] = err_p
            if err_p is None:
                agg["execution_success_generated"] += 1
                agg["by_complexity"][complexity]["exec_gen_ok"] += 1

        save_result_csv(gen_df, RESULTS_DIR / f"{qid}_generated.csv")
        save_sql(gen_sql, RESULTS_DIR / f"{qid}_generated.sql")

        if gold_sql and row["execution_ok_gold"] and row["execution_ok_generated"]:
            row["match"] = bool(dataframes_match(gold_df, gen_df))
            if row["match"]:
                agg["result_match"] += 1
                agg["by_complexity"][complexity]["match"] += 1
        elif not gold_sql:
            row["match"] = None

        summary["per_question"].append(row)

    n, wg = agg["total"], agg["with_gold_sql"]
    agg["execution_rate_gold"] = agg["execution_success_gold"] / wg if wg else None
    agg["execution_rate_generated"] = agg["execution_success_generated"] / n if n else None
    agg["match_rate_on_executable_pair"] = agg["result_match"] / wg if wg else None

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(
        f"Wrote {SUMMARY_PATH}; exec(gen) {agg['execution_success_generated']}/{n}, "
        f"match {agg['result_match']}/{wg}"
    )
    return summary


# --- Legacy BIAgentEvaluator (optional) ---

from sqlalchemy.exc import ProgrammingError  # noqa: E402


class BIAgentEvaluator:
    """Category / pattern checks without per-query gold CSV artifacts."""

    def __init__(self):
        self.agent = BusinessAnalystAgent()
        self.db_manager = DatabaseManager()
        logger.info("BIAgentEvaluator initialized")

    def evaluate_sql_syntax(self, sql_query: str) -> Dict[str, Any]:
        if not sql_query:
            return {"valid": False, "error": "Empty SQL query"}
        try:
            q = (sql_query or "").strip().rstrip(";")
            if not q:
                return {"valid": False, "error": "Empty SQL query"}
            with self.db_manager.engine.connect() as conn:
                conn.execute(text(f"EXPLAIN {q}"))
            return {"valid": True, "error": None}
        except ProgrammingError as e:
            return {"valid": False, "error": str(e)}
        except Exception as e:
            return {"valid": False, "error": f"Unexpected error: {str(e)}"}

    def evaluate_execution(self, sql_query: str) -> Dict[str, Any]:
        if not sql_query:
            return {"success": False, "error": "Empty SQL query", "row_count": 0, "execution_time": 0}
        start_time = time.time()
        try:
            with self.db_manager.engine.connect() as conn:
                df = pd.read_sql(text(sql_query), conn)
            execution_time = time.time() - start_time
            return {
                "success": True,
                "error": None,
                "row_count": len(df),
                "execution_time": execution_time,
                "empty_result": df.empty,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "row_count": 0,
                "execution_time": time.time() - start_time,
            }

    def _compare_result_sets(self, df_pred: pd.DataFrame, df_gold: pd.DataFrame) -> Dict[str, Any]:
        if df_pred is None or df_gold is None:
            return {"execution_accuracy": False, "row_count_match": False, "exact_match": False}
        try:
            pred_cols = sorted(df_pred.columns)
            gold_cols = sorted(df_gold.columns)
            if pred_cols != gold_cols:
                return {"execution_accuracy": False, "row_count_match": False, "exact_match": False}
            pred = df_pred[pred_cols].sort_values(by=pred_cols).reset_index(drop=True)
            gold = df_gold[gold_cols].sort_values(by=gold_cols).reset_index(drop=True)
            row_match = len(pred) == len(gold)
            exact = row_match and pred.equals(gold)
            return {
                "execution_accuracy": exact,
                "row_count_match": row_match,
                "exact_match": exact,
                "pred_rows": len(pred),
                "gold_rows": len(gold),
            }
        except Exception as e:
            logger.warning(f"Result comparison failed: {e}")
            return {"execution_accuracy": False, "row_count_match": False, "exact_match": False}

    def evaluate_single_query(
        self,
        question: str,
        ground_truth: Optional[Dict] = None,
        category: Optional[str] = None,
        thread_id: str = "default",
    ) -> Dict[str, Any]:
        logger.info(f"Evaluating: {question}")
        start_time = time.time()
        try:
            response = self.agent.ask(question, thread_id=thread_id)
            total_latency = time.time() - start_time
        except Exception as e:
            return {"question": question, "category": category, "error": str(e), "success": False}

        sql_query = response.get("sql_query")
        answer = response.get("answer", "")
        sql_syntax = self.evaluate_sql_syntax(sql_query) if sql_query else {"valid": False, "error": "No SQL generated"}
        sql_execution = (
            self.evaluate_execution(sql_query)
            if sql_query
            else {"success": False, "error": "No SQL to execute", "row_count": 0, "execution_time": 0}
        )

        execution_accuracy_result: Dict[str, Any] = {}
        gt = dict(ground_truth or {})
        if gt.get("gold_sql") and sql_execution.get("success"):
            gold_exec = self.evaluate_execution(gt["gold_sql"])
            if gold_exec.get("success"):
                try:
                    with self.db_manager.engine.connect() as conn:
                        df_pred = pd.read_sql(text(sql_query), conn)
                        df_gold = pd.read_sql(text(gt["gold_sql"]), conn)
                    execution_accuracy_result = self._compare_result_sets(df_pred, df_gold)
                except Exception as e:
                    execution_accuracy_result = {"execution_accuracy": False, "error": str(e)}
            else:
                execution_accuracy_result = {"execution_accuracy": False, "gold_sql_failed": True}

        ground_truth_comparison: Dict[str, Any] = {}
        if ground_truth:
            if "expected_sql_pattern" in ground_truth:
                pat = ground_truth["expected_sql_pattern"].lower()
                ground_truth_comparison["sql_pattern_match"] = pat in (sql_query or "").lower()
            if "expected_tables" in ground_truth:
                low = (sql_query or "").lower()
                ground_truth_comparison["uses_expected_tables"] = all(
                    t.lower() in low for t in ground_truth["expected_tables"]
                )

        return {
            "question": question,
            "category": category,
            "success": sql_execution["success"] and bool(answer and answer.strip()),
            "total_latency": total_latency,
            "sql_syntax": sql_syntax,
            "sql_execution": sql_execution,
            "answer_quality": {
                "has_answer": bool(answer and answer.strip()),
                "has_chart": response.get("chart_data") is not None,
            },
            "ground_truth_match": ground_truth_comparison,
            "execution_accuracy": execution_accuracy_result,
            "sql_query": sql_query,
        }

    def run_benchmark(self, test_set: List[Dict]) -> Dict[str, Any]:
        results = []
        for i, test_case in enumerate(test_set, 1):
            gt = dict(test_case.get("ground_truth") or {})
            if test_case.get("gold_sql"):
                gt["gold_sql"] = test_case["gold_sql"]
            results.append(
                self.evaluate_single_query(
                    test_case.get("question", ""),
                    gt,
                    category=test_case.get("category"),
                    thread_id=f"legacy_eval_{i}_{int(time.time() * 1000)}",
                )
            )
        total = len(results)
        successful = sum(1 for r in results if r.get("success"))
        ex_checked = [r for r in results if r.get("execution_accuracy", {}).get("execution_accuracy") is not None]
        ex_correct = sum(1 for r in results if r["execution_accuracy"].get("execution_accuracy"))
        return {
            "summary": {
                "total_queries": total,
                "success_rate": successful / total if total else 0,
                "execution_accuracy_ex": ex_correct / len(ex_checked) if ex_checked else None,
                "execution_accuracy_n": len(ex_checked),
            },
            "detailed_results": results,
            "errors": [],
            "by_category": {},
            "performance": {"average_latency": 0},
        }

    def save_results(self, results: Dict, output_file: str) -> None:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

    def print_summary(self, results: Dict) -> None:
        s = results.get("summary", {})
        print("\n" + "=" * 60)
        print("LEGACY EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total: {s.get('total_queries', 0)}  Success rate: {s.get('success_rate', 0):.2%}")
        if s.get("execution_accuracy_n"):
            print(f"EX (strict): {s.get('execution_accuracy_ex', 0):.2%} (n={s['execution_accuracy_n']})")
        print("=" * 60 + "\n")


def _run_legacy_main(test_file: str) -> None:
    import os

    p = Path(test_file)
    if not p.is_absolute():
        p = PROJECT_ROOT / test_file
    with open(p, "r", encoding="utf-8") as f:
        test_set = json.load(f)
    ev = BIAgentEvaluator()
    results = ev.run_benchmark(test_set)
    ev.print_summary(results)
    out = os.getenv("EVAL_OUTPUT", "evaluation_results.json")
    outp = str(PROJECT_ROOT / out) if not os.path.isabs(out) else out
    ev.save_results(results, outp)
    logger.info(f"Legacy results saved to {outp}")


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    if args and args[0] == "--legacy":
        tf = args[1] if len(args) > 1 else str(DEFAULT_TEST_PATH)
        _run_legacy_main(tf)
        return
    if args and args[0] == "--benchmark":
        test_path = Path(args[1]) if len(args) > 1 else DEFAULT_TEST_PATH
        if not test_path.is_absolute():
            test_path = PROJECT_ROOT / test_path
        rest = args[2:]
    else:
        test_path = DEFAULT_TEST_PATH
        rest = args

    start = end = None
    if len(rest) == 1:
        start = end = int(rest[0])
    elif len(rest) == 2:
        start, end = int(rest[0]), int(rest[1])

    run_gold_benchmark(test_path, start=start, end=end)


if __name__ == "__main__":
    main()
