"""
Evaluation Framework for BI Agent
Run: python -m src.evaluation
"""

import json
import time
import pandas as pd
from typing import List, Dict, Optional, Any
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from loguru import logger
from src.agents.sql_agent import BusinessAnalystAgent
from src.database import DatabaseManager

class BIAgentEvaluator:
    """Comprehensive evaluation suite for the BI Agent"""
    
    def __init__(self):
        self.agent = BusinessAnalystAgent()
        self.db_manager = DatabaseManager()
        self.results = []
        logger.info("Evaluator initialized")
    
    def evaluate_sql_syntax(self, sql_query: str) -> Dict[str, Any]:
        """Check if SQL query is syntactically valid"""
        if not sql_query:
            return {"valid": False, "error": "Empty SQL query"}
        
        try:
            with self.db_manager.engine.connect() as conn:
                # Use EXPLAIN to validate syntax without executing
                conn.execute(text(f"EXPLAIN {sql_query}"))
            return {"valid": True, "error": None}
        except ProgrammingError as e:
            return {"valid": False, "error": str(e)}
        except Exception as e:
            return {"valid": False, "error": f"Unexpected error: {str(e)}"}
    
    def evaluate_execution(self, sql_query: str) -> Dict[str, Any]:
        """Execute SQL and check for runtime errors"""
        if not sql_query:
            return {
                "success": False,
                "error": "Empty SQL query",
                "row_count": 0,
                "execution_time": 0
            }
        
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
                "empty_result": df.empty
            }
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "row_count": 0,
                "execution_time": execution_time
            }
    
    def _compare_result_sets(self, df_pred: pd.DataFrame, df_gold: pd.DataFrame) -> Dict[str, Any]:
        """Compare two query result DataFrames for execution accuracy (EX)."""
        if df_pred is None or df_gold is None:
            return {"execution_accuracy": False, "row_count_match": False, "exact_match": False}
        try:
            # Normalize: same column order, sort rows for comparison
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
    ) -> Dict[str, Any]:
        """Evaluate a single query end-to-end."""
        logger.info(f"Evaluating: {question}")

        start_time = time.time()

        # Get agent response
        try:
            response = self.agent.ask(question)
            total_latency = time.time() - start_time
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "question": question,
                "category": category,
                "error": str(e),
                "success": False,
            }

        sql_query = response.get("sql_query")
        answer = response.get("answer", "")
        chart_data = response.get("chart_data")
        raw_data = response.get("raw_data")

        # Evaluate SQL syntax
        sql_syntax = self.evaluate_sql_syntax(sql_query) if sql_query else {"valid": False, "error": "No SQL generated"}

        # Evaluate SQL execution
        sql_execution = self.evaluate_execution(sql_query) if sql_query else {
            "success": False,
            "error": "No SQL to execute",
            "row_count": 0,
            "execution_time": 0,
        }

        # Optional: execution accuracy vs gold SQL
        execution_accuracy_result = {}
        if ground_truth and ground_truth.get("gold_sql") and sql_execution.get("success"):
            gold_sql = ground_truth["gold_sql"]
            gold_exec = self.evaluate_execution(gold_sql)
            if gold_exec.get("success"):
                try:
                    with self.db_manager.engine.connect() as conn:
                        df_pred = pd.read_sql(text(sql_query), conn)
                        df_gold = pd.read_sql(text(gold_sql), conn)
                    execution_accuracy_result = self._compare_result_sets(df_pred, df_gold)
                except Exception as e:
                    execution_accuracy_result = {"execution_accuracy": False, "error": str(e)}
            else:
                execution_accuracy_result = {"execution_accuracy": False, "gold_sql_failed": True}

        # Check if answer is non-empty
        answer_quality = {
            "has_answer": bool(answer and answer.strip()),
            "answer_length": len(answer) if answer else 0,
            "has_chart": chart_data is not None,
            "has_raw_data": raw_data is not None,
        }

        # Compare with ground truth if provided
        ground_truth_comparison = {}
        if ground_truth:
            if "expected_sql_pattern" in ground_truth:
                expected_pattern = ground_truth["expected_sql_pattern"].lower()
                actual_sql = (sql_query or "").lower()
                ground_truth_comparison["sql_pattern_match"] = expected_pattern in actual_sql

            if "expected_tables" in ground_truth:
                expected_tables = [t.lower() for t in ground_truth["expected_tables"]]
                actual_sql = (sql_query or "").lower()
                ground_truth_comparison["uses_expected_tables"] = all(
                    table in actual_sql for table in expected_tables
                )

        result = {
            "question": question,
            "category": category,
            "success": sql_execution["success"] and answer_quality["has_answer"],
            "total_latency": total_latency,
            "sql_syntax": sql_syntax,
            "sql_execution": sql_execution,
            "answer_quality": answer_quality,
            "ground_truth_match": ground_truth_comparison,
            "execution_accuracy": execution_accuracy_result,
            "sql_query": sql_query,
            "answer_preview": answer[:200] if answer else None,
        }
        return result
    
    def run_benchmark(self, test_set: List[Dict]) -> Dict[str, Any]:
        """Run evaluation on a test set"""
        logger.info(f"Running benchmark on {len(test_set)} queries")
        
        results = []
        for i, test_case in enumerate(test_set, 1):
            logger.info(f"Processing {i}/{len(test_set)}")
            question = test_case.get("question", "")
            ground_truth = test_case.get("ground_truth", {})
            category = test_case.get("category")

            result = self.evaluate_single_query(question, ground_truth, category=category)
            results.append(result)
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return self.aggregate_results(results)
    
    def aggregate_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate aggregate metrics"""
        total = len(results)
        if total == 0:
            return {"error": "No results to aggregate"}
        
        successful = sum(1 for r in results if r.get("success", False))
        sql_valid = sum(1 for r in results if r.get("sql_syntax", {}).get("valid", False))
        sql_executed = sum(1 for r in results if r.get("sql_execution", {}).get("success", False))
        has_answer = sum(1 for r in results if r.get("answer_quality", {}).get("has_answer", False))
        
        latencies = [r.get("total_latency", 0) for r in results if r.get("total_latency")]
        execution_times = [
            r.get("sql_execution", {}).get("execution_time", 0) 
            for r in results 
            if r.get("sql_execution", {}).get("execution_time")
        ]
        
        # Error analysis
        errors = []
        for r in results:
            if not r.get("success", False):
                error_info = {
                    "question": r.get("question", "Unknown"),
                    "sql_error": r.get("sql_execution", {}).get("error"),
                    "syntax_error": r.get("sql_syntax", {}).get("error"),
                }
                errors.append(error_info)

        # Execution accuracy (EX) when gold_sql was provided in ground_truth
        ex_checked = [
            r for r in results
            if isinstance(r.get("execution_accuracy"), dict) and "execution_accuracy" in r["execution_accuracy"]
        ]
        ex_correct = sum(1 for r in ex_checked if r["execution_accuracy"].get("execution_accuracy", False))
        ex_rate = ex_correct / len(ex_checked) if ex_checked else None

        # Category-level breakdown
        by_category: Dict[str, Dict[str, Any]] = {}
        for r in results:
            cat = r.get("category") or "unknown"
            if cat not in by_category:
                by_category[cat] = {"total": 0, "success": 0, "sql_valid": 0, "sql_executed": 0, "has_answer": 0, "latencies": []}
            by_category[cat]["total"] += 1
            if r.get("success", False):
                by_category[cat]["success"] += 1
            if r.get("sql_syntax", {}).get("valid", False):
                by_category[cat]["sql_valid"] += 1
            if r.get("sql_execution", {}).get("success", False):
                by_category[cat]["sql_executed"] += 1
            if r.get("answer_quality", {}).get("has_answer", False):
                by_category[cat]["has_answer"] += 1
            if r.get("total_latency") is not None:
                by_category[cat]["latencies"].append(r["total_latency"])
        for cat, stats in by_category.items():
            n = stats["total"]
            stats["success_rate"] = stats["success"] / n if n else 0
            stats["sql_syntax_accuracy"] = stats["sql_valid"] / n if n else 0
            stats["sql_execution_success_rate"] = stats["sql_executed"] / n if n else 0
            stats["answer_generation_rate"] = stats["has_answer"] / n if n else 0
            stats["average_latency"] = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else None
            del stats["latencies"]

        return {
            "summary": {
                "total_queries": total,
                "success_rate": successful / total if total > 0 else 0,
                "sql_syntax_accuracy": sql_valid / total if total > 0 else 0,
                "sql_execution_success_rate": sql_executed / total if total > 0 else 0,
                "answer_generation_rate": has_answer / total if total > 0 else 0,
                "execution_accuracy_ex": ex_rate,
                "execution_accuracy_n": len(ex_checked),
            },
            "performance": {
                "average_latency": sum(latencies) / len(latencies) if latencies else 0,
                "min_latency": min(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0,
                "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            },
            "by_category": by_category,
            "errors": errors,
            "detailed_results": results,
        }
    
    def save_results(self, results: Dict, output_file: str = "evaluation_results.json"):
        """Save evaluation results to JSON file"""
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")
    
    def print_summary(self, results: Dict):
        """Print a human-readable summary."""
        summary = results.get("summary", {})
        performance = results.get("performance", {})

        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total Queries: {summary.get('total_queries', 0)}")
        print(f"Success Rate: {summary.get('success_rate', 0):.2%}")
        print(f"SQL Syntax Accuracy: {summary.get('sql_syntax_accuracy', 0):.2%}")
        print(f"SQL Execution Success: {summary.get('sql_execution_success_rate', 0):.2%}")
        print(f"Answer Generation Rate: {summary.get('answer_generation_rate', 0):.2%}")
        if summary.get("execution_accuracy_n"):
            print(f"Execution Accuracy (EX): {summary.get('execution_accuracy_ex', 0):.2%} (n={summary['execution_accuracy_n']})")
        print("\nPerformance Metrics:")
        print(f"  Average Latency: {performance.get('average_latency', 0):.2f}s")
        print(f"  Min Latency: {performance.get('min_latency', 0):.2f}s")
        print(f"  Max Latency: {performance.get('max_latency', 0):.2f}s")
        print(f"  Avg Execution Time: {performance.get('average_execution_time', 0):.2f}s")

        by_category = results.get("by_category", {})
        if by_category:
            print("\nBy Category:")
            for cat, stats in sorted(by_category.items()):
                sr = stats.get("success_rate", 0)
                n = stats.get("total", 0)
                lat = stats.get("average_latency")
                lat_str = f", avg latency {lat:.2f}s" if lat is not None else ""
                print(f"  {cat}: success {sr:.2%} ({stats.get('success', 0)}/{n}){lat_str}")

        errors = results.get("errors", [])
        if errors:
            print(f"\nErrors Found: {len(errors)}")
            for i, error in enumerate(errors[:5], 1):
                print(f"  {i}. {error.get('question', 'Unknown')[:50]}...")
                if error.get("sql_error"):
                    print(f"     SQL Error: {error['sql_error'][:100]}")
        print("=" * 60 + "\n")


# Sample test set
SAMPLE_TEST_SET = [
    {
        "question": "What are total sales?",
        "ground_truth": {
            "expected_tables": ["shipped_raw"],
            "expected_sql_pattern": "sum(product_gms)"
        }
    },
    {
        "question": "Show me sales trends over time",
        "ground_truth": {
            "expected_tables": ["shipped_raw"],
            "expected_sql_pattern": "group by"
        }
    },
    {
        "question": "Which products have the highest return rates?",
        "ground_truth": {
            "expected_tables": ["shipped_raw", "concession_raw"],
            "expected_sql_pattern": "join"
        }
    },
    {
        "question": "What is the net margin?",
        "ground_truth": {
            "expected_tables": ["shipped_raw", "concession_raw"],
            "expected_sql_pattern": "ncrc"
        }
    }
]


def load_test_set(file_path: str = "data/test_queries.json") -> List[Dict]:
    """Load test set from JSON file"""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Test file {file_path} not found, using sample test set")
        return SAMPLE_TEST_SET
    except Exception as e:
        logger.error(f"Error loading test set: {e}")
        return SAMPLE_TEST_SET


def main():
    """Run evaluation"""
    import sys
    import os
    
    evaluator = BIAgentEvaluator()
    
    # Load test set from file or use sample
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        test_file = "data/test_queries.json"
    
    test_set = load_test_set(test_file)
    logger.info(f"Loaded {len(test_set)} test queries from {test_file}")
    
    print("Starting evaluation...")
    results = evaluator.run_benchmark(test_set)
    
    # Print summary
    evaluator.print_summary(results)
    
    # Save results
    output_file = os.getenv("EVAL_OUTPUT", "evaluation_results.json")
    evaluator.save_results(results, output_file)
    
    return results


if __name__ == "__main__":
    main()
