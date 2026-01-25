# Price Comparison Feature - User Guide

## 🎯 Overview

The agent now supports **web price comparison**! When you ask about prices from other sources, the agent will:
1. Search the web using Tavily API for current market prices
2. Fetch average prices from your database
3. Compare them and show you the difference

---

## 💡 How to Use

### **Example Questions:**

1. **"What are the prices of iPhone 15 from other sources?"**
   - Agent fetches web prices from MediaMarkt, Saturn, Amazon.de
   - Compares with your database prices
   - Shows difference

2. **"Compare iPhone prices with online retailers"**
   - Same as above - detects price comparison intent

3. **"Show me competitor prices for Samsung Galaxy"**
   - Fetches web prices for Samsung products
   - Compares with database

4. **"What's the price difference between our prices and online prices for iPhone?"**
   - Explicit comparison request

---

## 🔄 How It Works

### **Step-by-Step Flow:**

```
User: "What are iPhone prices from other sources?"
    ↓
[Agent detects: Price comparison needed]
    ↓
[Extracts product name: "iPhone"]
    ↓
[Fetches web prices via Tavily API]
    ↓
[Fetches database prices from shipped_raw]
    ↓
[Calculates average prices]
    ↓
[Compares: Database vs Web]
    ↓
[Shows comparison with chart]
```

---

## 📊 What You'll See

### **Response Format:**

```
**Price Comparison: iPhone 15**

**Database Average Price:** €899.99
**Online Market Average Price:** €949.99

**Difference:** Database prices are €50.00 (5.3%) lower than online market prices.

**Web Price Sources:**
- MediaMarkt: €949.99
- Saturn: €939.99
- Amazon: €959.99

**Database Price Range:**
- Minimum: €849.99
- Maximum: €929.99

[Bar Chart showing comparison]
```

---

## 🔍 Technical Details

### **1. Price Detection**
The agent uses LLM to detect if your question is about price comparison:
- Keywords: "compare prices", "online prices", "competitor prices", "other sources"
- Intent: Price comparison vs regular database query

### **2. Web Price Fetching**
- Uses **Tavily API** to search German retail sites
- Searches: MediaMarkt, Saturn, Amazon.de, Otto, Zalando
- Extracts prices using regex patterns
- Returns structured price data

### **3. Database Price Calculation**
- Queries `shipped_raw` table
- Calculates: `Average Price = Total Revenue / Total Units`
- Formula: `SUM(product_gms) / SUM(shipped_units)`
- Groups by ASIN and product name

### **4. Comparison Logic**
- Compares average database price vs average web price
- Calculates absolute difference (€)
- Calculates percentage difference (%)
- Shows price range from database

---

## 🎨 Chart Visualization

The comparison includes a bar chart showing:
- **Database Average Price** (blue bar)
- **Online Market Average Price** (orange bar)

This makes it easy to see the price difference visually!

---

## ⚙️ Configuration

### **Required Environment Variables:**
```bash
TAVILY_API_KEY=your_tavily_api_key  # For web price search
OPENAI_API_KEY=your_openai_key       # For intent detection
DATABASE_URL=your_database_url        # For database prices
```

### **Tavily API Setup:**
1. Sign up at https://tavily.com
2. Get your API key
3. Add to `.env` file:
   ```
   TAVILY_API_KEY=tvly-xxxxx
   ```

---

## 🧪 Testing

### **Test Script:**
```bash
python test_price_comparison.py
```

### **Manual Testing:**
1. Start the system: `docker-compose up`
2. Open dashboard: `http://localhost:9090`
3. Ask: "What are iPhone prices from other sources?"
4. Verify: You see web prices + database prices + comparison

---

## 📝 Example Scenarios

### **Scenario 1: Competitive Pricing**
```
You: "Compare our iPhone prices with online retailers"
Agent: [Fetches web prices]
       [Gets database prices]
       [Shows: "Our prices are 5% lower than market"]
```

### **Scenario 2: Market Research**
```
You: "What are competitor prices for Samsung Galaxy?"
Agent: [Searches web for Samsung prices]
       [Compares with your database]
       [Shows price difference]
```

### **Scenario 3: Follow-up**
```
You: "Show me iPhone sales"
Agent: [Shows iPhone sales data]

You: "What about prices from other sources?"
Agent: [Understands context: iPhone prices]
       [Fetches web prices for iPhones]
       [Compares]
```

---

## 🚨 Limitations & Notes

### **Current Limitations:**
1. **Web Prices**: 
   - Depends on Tavily API accuracy
   - May not always find exact product matches
   - Prices change frequently online

2. **Database Prices**:
   - Uses historical sales data
   - Average price = Total Revenue / Total Units
   - May not reflect current prices if data is old

3. **Product Matching**:
   - Relies on product name extraction
   - May not match exact models (e.g., "iPhone 15" vs "iPhone 15 Pro")

### **Best Practices:**
- Be specific: "iPhone 15 128GB" vs "iPhone"
- Check if product exists in database first
- Web prices are current, database prices are historical

---

## 🔧 Troubleshooting

### **Issue: "No web prices found"**
- **Cause**: Tavily API couldn't find prices
- **Solution**: Check Tavily API key, try different product name

### **Issue: "No database prices"**
- **Cause**: Product not in database or no sales data
- **Solution**: Verify product exists, check if there are sales records

### **Issue: "Price comparison not triggered"**
- **Cause**: Question not detected as price comparison
- **Solution**: Use keywords like "compare prices", "online prices", "competitor prices"

---

## 📈 Future Enhancements

Potential improvements:
1. **Multiple Product Comparison**: Compare multiple products at once
2. **Historical Price Trends**: Show price changes over time
3. **Price Alerts**: Notify when prices differ significantly
4. **More Retailers**: Add more German retail sites
5. **Price Prediction**: Predict future price trends

---

## ✅ Summary

**Price Comparison Feature:**
- ✅ Fetches web prices from German retailers
- ✅ Gets database average prices
- ✅ Compares and shows difference
- ✅ Visualizes with charts
- ✅ Works with conversation memory

**Just ask:** *"What are iPhone prices from other sources?"* 🎉
