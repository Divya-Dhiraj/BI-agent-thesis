# Tavily API Price Scraping Test Guide

## 🎯 Overview

This guide explains how to test if the Tavily API is working correctly for scraping product prices from German retailers.

---

## 🚀 Quick Test

For a fast check, run:
```bash
python test_tavily_quick.py
```

This will:
- ✅ Check if API key is configured
- ✅ Test connection to Tavily API
- ✅ Fetch prices for "iPhone 15"
- ✅ Show results

---

## 📋 Full Test Suite

For comprehensive testing, run:
```bash
python test_tavily_prices.py
```

This runs 5 test scenarios:

### **Test 1: API Connection**
- Verifies Tavily API key is set
- Initializes WebScoutAgent
- Checks basic connectivity

### **Test 2: Single Product Price Fetching**
- Tests price fetching for "iPhone 15 128GB"
- Validates price extraction
- Shows detailed results

### **Test 3: Multiple Products**
- Tests multiple products:
  - iPhone 15 128GB
  - Samsung Galaxy S23
  - iPad Pro
- Compares success rates

### **Test 4: Price Extraction Patterns**
- Validates price extraction logic
- Checks price ranges (€50-€5000)
- Identifies invalid prices

### **Test 5: Error Handling**
- Tests edge cases:
  - Empty strings
  - Non-existent products
  - Very long strings
- Ensures graceful error handling

---

## 📊 Expected Output

### **Successful Test:**
```
✅ WebScoutAgent initialized successfully
✅ Tavily API Key: tvly-dev-d...
🔍 Searching for prices: iPhone 15 128GB
⏳ This may take 5-10 seconds...

📊 RESULTS:
Product: iPhone 15 128GB
Sources Found: 3
Average Price: €949.99
Price Range: €939.99 - €959.99

💰 Individual Prices Found:
1. MediaMarkt: €949.99 (EUR)
2. Saturn: €939.99 (EUR)
3. Amazon: €959.99 (EUR)

✅ SUCCESS: Found average price €949.99
```

### **Failed Test:**
```
❌ ERROR: Tavily API key not found!
or
⚠️  WARNING: No average price calculated
```

---

## 🔧 Troubleshooting

### **Issue: "TAVILY_API_KEY not found"**
**Solution:**
1. Check your `.env` file exists
2. Add: `TAVILY_API_KEY=your_key_here`
3. Get key from: https://tavily.com

### **Issue: "No prices found"**
**Possible Causes:**
1. **API Key Invalid**: Check your Tavily API key
2. **Rate Limiting**: Wait a few minutes and try again
3. **Product Not Found**: Try a more common product name
4. **Price Extraction**: Prices might be in different format

**Solutions:**
- Try different product names: "iPhone", "Samsung Galaxy", "iPad"
- Check Tavily API dashboard for usage/quota
- Verify API key is active

### **Issue: "Connection Error"**
**Possible Causes:**
1. No internet connection
2. Tavily API is down
3. Firewall blocking requests

**Solutions:**
- Check internet connection
- Visit https://tavily.com to check API status
- Check firewall/proxy settings

### **Issue: "Invalid prices extracted"**
**Possible Causes:**
- Price extraction patterns not matching German price formats
- Prices in different currencies
- Incorrect parsing

**Solutions:**
- Check `src/agents/web_agent.py` price extraction patterns
- Verify prices are in EUR format
- Adjust regex patterns if needed

---

## 🧪 Manual Testing

You can also test manually in Python:

```python
from src.agents.web_agent import WebScoutAgent

scout = WebScoutAgent()
result = scout.get_competitor_prices("iPhone 15")

print(f"Average Price: €{result.get('average_price', 'N/A')}")
print(f"Prices Found: {len(result.get('prices', []))}")
```

---

## 📝 Test Scripts

### **1. `test_tavily_quick.py`**
- Quick verification test
- Single product test
- Fast execution (~10 seconds)

### **2. `test_tavily_prices.py`**
- Comprehensive test suite
- Multiple test scenarios
- Detailed reporting
- Takes ~1-2 minutes

---

## ✅ Success Criteria

A test is considered successful if:
1. ✅ API key is configured
2. ✅ WebScoutAgent initializes without errors
3. ✅ At least one price is extracted
4. ✅ Average price is calculated
5. ✅ Prices are in reasonable range (€50-€5000)

---

## 🔍 What Gets Tested

### **Price Sources:**
- MediaMarkt (German retailer)
- Saturn (German retailer)
- Amazon.de (German Amazon)
- Other German retailers

### **Price Formats:**
- €999.99
- 999,99€
- EUR 999.99
- 999 Euro

### **Validation:**
- Price range: €50 - €5000
- Currency: EUR
- Retailer identification
- Source URL tracking

---

## 📈 Interpreting Results

### **Good Results:**
- ✅ 3+ prices found
- ✅ Average price calculated
- ✅ Prices in reasonable range
- ✅ Multiple retailers identified

### **Warning Signs:**
- ⚠️  Only 1-2 prices found
- ⚠️  Prices outside €50-€5000 range
- ⚠️  No retailer names identified

### **Failures:**
- ❌ No prices found
- ❌ API connection errors
- ❌ Invalid API key
- ❌ Timeout errors

---

## 🎓 Example Usage

```bash
# Quick test
python test_tavily_quick.py

# Full test suite
python test_tavily_prices.py

# Test specific product
python -c "from src.agents.web_agent import WebScoutAgent; scout = WebScoutAgent(); print(scout.get_competitor_prices('Samsung Galaxy S23'))"
```

---

## 📚 Related Files

- `src/agents/web_agent.py` - WebScoutAgent implementation
- `src/config.py` - Configuration (API keys)
- `.env` - Environment variables

---

## ✅ Summary

**Quick Test:** `python test_tavily_quick.py`
**Full Test:** `python test_tavily_prices.py`

Both scripts will tell you if Tavily API is working correctly for price scraping! 🎉
