"""
Test script for price comparison feature.
Run this to verify web price comparison works correctly.
"""

from src.agents.sql_agent import BusinessAnalystAgent
from loguru import logger

def test_price_comparison():
    """Test that price comparison works."""
    agent = BusinessAnalystAgent()
    session_id = "test_price_session"
    
    print("\n" + "="*60)
    print("TESTING PRICE COMPARISON FEATURE")
    print("="*60 + "\n")
    
    # Test 1: Direct price comparison question
    print("Test 1: Price comparison question")
    print("-" * 60)
    result1 = agent.ask(
        "What are the prices of iPhone from other sources?", 
        thread_id=session_id
    )
    print(f"Answer Preview: {result1['answer'][:300]}...")
    print(f"Has Chart: {result1.get('chart_data') is not None}")
    print("\n")
    
    # Test 2: Compare prices question
    print("Test 2: Compare prices question")
    print("-" * 60)
    result2 = agent.ask(
        "Compare iPhone prices with online retailers", 
        thread_id=session_id
    )
    print(f"Answer Preview: {result2['answer'][:300]}...")
    print(f"Has Chart: {result2.get('chart_data') is not None}")
    print("\n")
    
    # Test 3: Follow-up price question
    print("Test 3: Follow-up price question")
    print("-" * 60)
    result3 = agent.ask(
        "Show me iPhone sales", 
        thread_id=session_id
    )
    print(f"First Answer: {result3['answer'][:200]}...")
    print("\n")
    
    result4 = agent.ask(
        "What about prices from other sources?", 
        thread_id=session_id
    )
    print(f"Follow-up Answer: {result4['answer'][:300]}...")
    print(f"Has Chart: {result4.get('chart_data') is not None}")
    print("\n")
    
    print("="*60)
    print("PRICE COMPARISON TEST RESULTS:")
    print("- If Test 1 shows web prices + database prices → ✅ Works!")
    print("- If Test 2 shows comparison → ✅ Works!")
    print("- If Test 3 follow-up understands context → ✅ Memory works!")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_price_comparison()
