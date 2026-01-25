"""
Simple test script to verify agent memory works correctly.
Run this to test follow-up question understanding.
"""

from src.agents.sql_agent import BusinessAnalystAgent
from loguru import logger

def test_memory():
    """Test that the agent remembers previous questions."""
    agent = BusinessAnalystAgent()
    session_id = "test_session_123"
    
    print("\n" + "="*60)
    print("TESTING AGENT MEMORY")
    print("="*60 + "\n")
    
    # Question 1: Initial question
    print("Question 1: What are the top selling iPhones?")
    result1 = agent.ask("What are the top selling iPhones?", thread_id=session_id)
    print(f"Answer: {result1['answer'][:200]}...")
    print(f"SQL Generated: {result1['sql_query'][:100] if result1['sql_query'] else 'None'}...")
    print("\n" + "-"*60 + "\n")
    
    # Question 2: Follow-up question (should understand context)
    print("Question 2: What about returns for those?")
    result2 = agent.ask("What about returns for those?", thread_id=session_id)
    print(f"Answer: {result2['answer'][:200]}...")
    print(f"SQL Generated: {result2['sql_query'][:100] if result2['sql_query'] else 'None'}...")
    print("\n" + "-"*60 + "\n")
    
    # Question 3: Another follow-up
    print("Question 3: Show me more details")
    result3 = agent.ask("Show me more details", thread_id=session_id)
    print(f"Answer: {result3['answer'][:200]}...")
    print(f"SQL Generated: {result3['sql_query'][:100] if result3['sql_query'] else 'None'}...")
    print("\n" + "="*60 + "\n")
    
    # Verify memory is working
    print("MEMORY TEST RESULTS:")
    print("- If Question 2 understood 'those' = iPhones → Memory works! ✅")
    print("- If Question 3 understood 'more details' = about iPhones → Memory works! ✅")
    print("- If answers are generic → Memory might not be working ❌")

if __name__ == "__main__":
    test_memory()
