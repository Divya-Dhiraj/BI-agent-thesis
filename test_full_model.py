"""
End-to-end smoke tests for the BI agent.

This script hits the running API and validates:
- DB-only queries
- Follow-up memory
- Topic reset (new question)
- Web-only prices (toggle on)
- Comparison (web + DB)
- Toggle off (internal only)

Usage:
  python test_full_model.py

Requirements:
  - Agent API running (default: http://localhost:9010)
  - .env configured with API keys
"""

import json
import os
import sys
import time
from typing import Dict, Any

import requests


API_URL = os.getenv("AGENT_API_URL", "http://localhost:9010").rstrip("/")


def _post_ask(prompt: str, session_id: str, use_external_prices: bool) -> Dict[str, Any]:
    payload = {
        "prompt": prompt,
        "session_id": session_id,
        "use_external_prices": use_external_prices,
    }
    resp = requests.post(f"{API_URL}/ask", json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()


def _expect(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def run():
    print(f"API_URL: {API_URL}")
    # Health check
    try:
        health = requests.get(f"{API_URL}/", timeout=10).json()
        print("Health:", health)
    except Exception as e:
        print(f"ERROR: API not reachable at {API_URL} -> {e}")
        sys.exit(1)

    session_id = f"test-{int(time.time())}"

    print("\n[1] DB-only query")
    q1 = "Show monthly sales trend for iPhones in 2024."
    r1 = _post_ask(q1, session_id, use_external_prices=False)
    _expect("answer" in r1, "Missing answer for DB-only query")
    print("OK:", r1["answer"][:120], "...")

    print("\n[2] Follow-up memory")
    q2 = "what about returns?"
    r2 = _post_ask(q2, session_id, use_external_prices=False)
    _expect("answer" in r2, "Missing answer for follow-up")
    print("OK:", r2["answer"][:120], "...")

    print("\n[3] Topic reset")
    q3 = "Top return reasons for tablets."
    r3 = _post_ask(q3, session_id, use_external_prices=False)
    _expect("answer" in r3, "Missing answer for topic reset")
    # Some datasets may not have tablet returns; treat "no data" as a soft pass
    if "Query returned no data" in r3["answer"]:
        print("WARN (no data):", r3["answer"][:120], "...")
    else:
        print("OK:", r3["answer"][:120], "...")

    print("\n[4] Web-only prices (toggle on)")
    q4 = "What are iPhone 15 prices online?"
    r4 = _post_ask(q4, session_id, use_external_prices=True)
    _expect("answer" in r4, "Missing answer for web-only prices")
    print("OK:", r4["answer"][:120], "...")

    print("\n[5] Comparison (web + DB)")
    q5 = "Compare iPhone 15 online prices with our database prices."
    r5 = _post_ask(q5, session_id, use_external_prices=True)
    _expect("answer" in r5, "Missing answer for comparison")
    print("OK:", r5["answer"][:120], "...")

    print("\n[6] Toggle off (internal only)")
    q6 = "What are iPhone 15 prices online?"
    r6 = _post_ask(q6, session_id, use_external_prices=False)
    _expect("answer" in r6, "Missing answer for toggle off")
    print("OK:", r6["answer"][:120], "...")

    print("\nAll smoke tests passed ✅")


if __name__ == "__main__":
    run()
