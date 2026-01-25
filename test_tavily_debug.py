"""
Debug script to inspect Tavily API response and improve price extraction.
Shows raw response data to help debug price extraction issues.
"""

from src.agents.web_agent import WebScoutAgent
from src.config import Config
import json
from tavily import TavilyClient

def debug_tavily_response():
    """Debug Tavily API response to see what we're getting."""
    print("\n" + "="*70)
    print("TAVILY API DEBUG - Raw Response Inspection")
    print("="*70)
    
    if not Config.TAVILY_API_KEY:
        print("❌ TAVILY_API_KEY not found!")
        return
    
    # Get raw response
    client = TavilyClient(api_key=Config.TAVILY_API_KEY)
    query = "Preis iPhone 15 kaufen MediaMarkt Saturn Amazon.de Deutschland aktuell"
    
    print(f"\n🔍 Query: {query}")
    print("⏳ Fetching response...\n")
    
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=10,
            include_answer=True
        )
        
        print("="*70)
        print("RAW RESPONSE STRUCTURE")
        print("="*70)
        print(f"Keys in response: {list(response.keys())}")
        print(f"Number of results: {len(response.get('results', []))}")
        print(f"Has answer: {'answer' in response}")
        
        # Show answer
        print("\n" + "="*70)
        print("ANSWER TEXT (from Tavily)")
        print("="*70)
        answer = response.get('answer', '')
        print(answer[:1000] + "..." if len(answer) > 1000 else answer)
        
        # Show results
        print("\n" + "="*70)
        print("SEARCH RESULTS")
        print("="*70)
        results = response.get('results', [])
        for i, result in enumerate(results[:5], 1):
            print(f"\n--- Result {i} ---")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"URL: {result.get('url', 'N/A')}")
            content = result.get('content', '')
            print(f"Content (first 300 chars): {content[:300]}...")
            
            # Try to find prices in this result
            import re
            price_patterns = [
                r'€\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
                r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*€',
                r'EUR\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
            ]
            
            found_prices = []
            for pattern in price_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                found_prices.extend(matches)
            
            if found_prices:
                print(f"💰 Potential prices found: {found_prices[:5]}")
            else:
                print("⚠️  No prices found with current patterns")
        
        # Test extraction
        print("\n" + "="*70)
        print("TESTING PRICE EXTRACTION")
        print("="*70)
        scout = WebScoutAgent()
        result = scout.get_competitor_prices("iPhone 15")
        
        print(f"\nExtracted prices: {len(result.get('prices', []))}")
        if result.get('prices'):
            for p in result.get('prices', []):
                print(f"  - {p.get('retailer')}: €{p.get('price')}")
        else:
            print("⚠️  No prices extracted")
            print("\nThis suggests the price extraction patterns need adjustment.")
            print("Check the raw response above to see what format prices are in.")
        
        # Save full response to file for inspection
        print("\n" + "="*70)
        print("SAVING FULL RESPONSE")
        print("="*70)
        with open('tavily_response_debug.json', 'w', encoding='utf-8') as f:
            json.dump(response, f, indent=2, ensure_ascii=False)
        print("✅ Full response saved to: tavily_response_debug.json")
        print("   You can inspect this file to see the exact response format.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_tavily_response()
