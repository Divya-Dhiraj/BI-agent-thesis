"""
Quick test script to verify Tavily API is working.
Run this for a fast check: python test_tavily_quick.py
"""

from src.agents.web_agent import WebScoutAgent
from src.config import Config
import json

def quick_test():
    """Quick test of Tavily price scraping."""
    print("\n🔍 Testing Tavily API Price Scraping...")
    print("-" * 60)
    
    # Check API key
    if not Config.TAVILY_API_KEY:
        print("❌ ERROR: TAVILY_API_KEY not found!")
        print("Set it in your .env file: TAVILY_API_KEY=your_key")
        return False
    
    print(f"✅ API Key found: {Config.TAVILY_API_KEY[:10]}...")
    
    # Initialize scout
    try:
        scout = WebScoutAgent()
        print("✅ WebScoutAgent initialized")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False
    
    # Test with iPhone
    print("\n🔍 Fetching prices for 'iPhone 15'...")
    print("⏳ Please wait (5-10 seconds)...\n")
    
    try:
        result = scout.get_competitor_prices("iPhone 15")
        
        print("📊 RESULTS:")
        print("-" * 60)
        print(f"Product: {result.get('product', 'Unknown')}")
        print(f"Sources: {result.get('source_count', 0)}")
        
        if result.get('average_price'):
            print(f"✅ Average Price: €{result['average_price']:.2f}")
        else:
            print("⚠️  No average price found")
        
        prices = result.get('prices', [])
        if prices:
            print(f"\n💰 Prices Found ({len(prices)}):")
            for p in prices[:5]:  # Show first 5
                print(f"  - {p.get('retailer', 'Unknown')}: €{p.get('price', 0):.2f}")
        else:
            print("\n⚠️  No individual prices extracted")
        
        print(f"\n📝 Summary:")
        summary = result.get('summary', 'No summary')
        print(summary[:200] + "..." if len(summary) > 200 else summary)
        
        # Success check
        if result.get('average_price') or prices:
            print("\n✅ SUCCESS: Tavily API is working!")
            return True
        else:
            print("\n⚠️  WARNING: API responded but no prices extracted")
            print("This might be normal if:")
            print("  - Product not found in search results")
            print("  - Price extraction patterns need adjustment")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_test()
    exit(0 if success else 1)
