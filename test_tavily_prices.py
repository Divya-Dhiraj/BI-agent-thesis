"""
Test script to verify Tavily API is working for scraping product prices.
This script tests the WebScoutAgent's ability to fetch prices from German retailers.
"""

import json
import sys
from src.agents.web_agent import WebScoutAgent
from src.config import Config
from loguru import logger

def test_tavily_connection():
    """Test basic Tavily API connection."""
    print("\n" + "="*70)
    print("TEST 1: Tavily API Connection Test")
    print("="*70)
    
    try:
        scout = WebScoutAgent()
        print("✅ WebScoutAgent initialized successfully")
        print(f"✅ Tavily API Key: {Config.TAVILY_API_KEY[:10]}..." if Config.TAVILY_API_KEY else "❌ Tavily API Key not found!")
        return scout
    except Exception as e:
        print(f"❌ Failed to initialize WebScoutAgent: {e}")
        return None

def test_single_product_price(scout: WebScoutAgent, product_name: str):
    """Test price fetching for a single product."""
    print(f"\n{'='*70}")
    print(f"TEST 2: Price Fetching for '{product_name}'")
    print("="*70)
    
    try:
        print(f"\n🔍 Searching for prices: {product_name}")
        print("⏳ This may take 5-10 seconds...\n")
        
        result = scout.get_competitor_prices(product_name)
        
        print("📊 RESULTS:")
        print("-" * 70)
        print(f"Product: {result.get('product', 'Unknown')}")
        print(f"Sources Found: {result.get('source_count', 0)}")
        print(f"Average Price: €{result.get('average_price', 'N/A')}")
        
        if result.get('min_price') and result.get('max_price'):
            print(f"Price Range: €{result['min_price']:.2f} - €{result['max_price']:.2f}")
        
        print(f"\n📝 Summary:")
        print(result.get('summary', 'No summary available'))
        
        prices = result.get('prices', [])
        if prices:
            print(f"\n💰 Individual Prices Found:")
            print("-" * 70)
            for i, price_info in enumerate(prices, 1):
                retailer = price_info.get('retailer', 'Unknown')
                price = price_info.get('price', 0)
                currency = price_info.get('currency', 'EUR')
                source = price_info.get('source', 'N/A')
                print(f"{i}. {retailer}: €{price:.2f} ({currency})")
                if source and source != 'Tavily Answer':
                    print(f"   Source: {source[:60]}...")
        else:
            print("\n⚠️  No individual prices extracted")
        
        # Validate results
        if result.get('average_price'):
            print(f"\n✅ SUCCESS: Found average price €{result['average_price']:.2f}")
            return True
        else:
            print(f"\n⚠️  WARNING: No average price calculated")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiple_products(scout: WebScoutAgent):
    """Test price fetching for multiple products."""
    print(f"\n{'='*70}")
    print("TEST 3: Multiple Products Test")
    print("="*70)
    
    test_products = [
        "iPhone 15 128GB",
        "Samsung Galaxy S23",
        "iPad Pro"
    ]
    
    results = []
    for product in test_products:
        print(f"\n🔍 Testing: {product}")
        try:
            result = scout.get_competitor_prices(product)
            success = result.get('average_price') is not None
            results.append({
                'product': product,
                'success': success,
                'avg_price': result.get('average_price'),
                'sources': result.get('source_count', 0)
            })
            
            if success:
                print(f"  ✅ Found price: €{result.get('average_price'):.2f} ({result.get('source_count', 0)} sources)")
            else:
                print(f"  ⚠️  No price found ({result.get('source_count', 0)} sources)")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                'product': product,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("="*70)
    successful = sum(1 for r in results if r.get('success'))
    print(f"Successful: {successful}/{len(results)}")
    
    for r in results:
        status = "✅" if r.get('success') else "❌"
        print(f"{status} {r['product']}: ", end="")
        if r.get('success'):
            print(f"€{r['avg_price']:.2f} ({r['sources']} sources)")
        else:
            print(f"Failed - {r.get('error', 'No price found')}")
    
    return successful == len(results)

def test_price_extraction_patterns(scout: WebScoutAgent):
    """Test if price extraction patterns are working."""
    print(f"\n{'='*70}")
    print("TEST 4: Price Extraction Pattern Validation")
    print("="*70)
    
    # Test with a common product
    product = "iPhone 15"
    print(f"\n🔍 Testing price extraction for: {product}")
    
    try:
        result = scout.get_competitor_prices(product)
        prices = result.get('prices', [])
        
        print(f"\nFound {len(prices)} price entries")
        
        # Check price validity
        valid_prices = []
        invalid_prices = []
        
        for price_info in prices:
            price = price_info.get('price', 0)
            if 50 <= price <= 5000:  # Reasonable range for smartphones
                valid_prices.append(price_info)
            else:
                invalid_prices.append(price_info)
        
        print(f"\n✅ Valid prices (€50-€5000): {len(valid_prices)}")
        print(f"⚠️  Invalid prices (outside range): {len(invalid_prices)}")
        
        if invalid_prices:
            print("\nInvalid prices found:")
            for p in invalid_prices:
                print(f"  - {p.get('retailer')}: €{p.get('price')}")
        
        return len(valid_prices) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_error_handling(scout: WebScoutAgent):
    """Test error handling for edge cases."""
    print(f"\n{'='*70}")
    print("TEST 5: Error Handling Test")
    print("="*70)
    
    edge_cases = [
        "",  # Empty string
        "NonExistentProductXYZ123",  # Non-existent product
        "a" * 200,  # Very long string
    ]
    
    for test_case in edge_cases:
        print(f"\n🔍 Testing edge case: '{test_case[:30]}...'")
        try:
            result = scout.get_competitor_prices(test_case)
            # Should not crash, but may return empty results
            if result.get('average_price'):
                print(f"  ⚠️  Unexpected: Found price €{result['average_price']:.2f}")
            else:
                print(f"  ✅ Handled gracefully: No price found (expected)")
        except Exception as e:
            print(f"  ❌ Error occurred: {e}")
    
    return True

def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TAVILY API PRICE SCRAPING TEST SUITE")
    print("="*70)
    
    # Check configuration
    if not Config.TAVILY_API_KEY:
        print("\n❌ ERROR: TAVILY_API_KEY not found in environment!")
        print("Please set TAVILY_API_KEY in your .env file")
        sys.exit(1)
    
    # Initialize scout
    scout = test_tavily_connection()
    if not scout:
        print("\n❌ Cannot proceed without WebScoutAgent")
        sys.exit(1)
    
    # Run tests
    test_results = []
    
    # Test 1: Single product (iPhone)
    test_results.append(("Single Product (iPhone)", test_single_product_price(scout, "iPhone 15 128GB")))
    
    # Test 2: Multiple products
    test_results.append(("Multiple Products", test_multiple_products(scout)))
    
    # Test 3: Price extraction patterns
    test_results.append(("Price Extraction Patterns", test_price_extraction_patterns(scout)))
    
    # Test 4: Error handling
    test_results.append(("Error Handling", test_error_handling(scout)))
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*70}")
    print(f"Overall: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! Tavily API is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
