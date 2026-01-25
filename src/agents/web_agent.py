import json
import re
import time
from typing import Dict, List, Optional
from tavily import TavilyClient
from src.config import Config
from loguru import logger
from langchain_core.tools import tool

class WebScoutAgent:
    def __init__(self):
        self.client = TavilyClient(api_key=Config.TAVILY_API_KEY)
        logger.success("Web Scout Agent (Tavily) Initialized.")

    def get_competitor_prices(self, product_name: str) -> Dict:
        """
        Searches for current prices of a product on German price comparison sites
        (idealo.de, geizhals.de, billiger.de, preis.de) for accurate pricing data.
        
        Returns:
            {
                "product": product_name,
                "prices": [
                    {"retailer": "MediaMarkt", "price": 999.99, "currency": "EUR"},
                    {"retailer": "Saturn", "price": 989.99, "currency": "EUR"},
                    ...
                ],
                "average_price": 994.99,
                "min_price": 989.99,
                "max_price": 999.99,
                "summary": "Price summary text"
            }
        """
        # Target German price comparison sites for accurate prices
        query = f"{product_name} preis idealo geizhals billiger preis.de Preisvergleich Deutschland"
        logger.info(f"Web Search Query (Price Comparison Sites): {query}")
        
        try:
            # Use 'advanced' depth for higher accuracy in pricing
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=10,
                include_answer=True
            )
            
            # Extract structured price data
            prices = self._extract_prices_from_response(response, product_name)
            
            # Calculate statistics
            price_values = [p["price"] for p in prices if p.get("price")]
            avg_price = sum(price_values) / len(price_values) if price_values else None
            min_price = min(price_values) if price_values else None
            max_price = max(price_values) if price_values else None

            # Use median when prices are highly skewed (robust average)
            avg_price_method = "mean"
            if price_values:
                median_price = self._median(price_values)
                if self._is_outlier_spread(price_values):
                    avg_price = median_price
                    avg_price_method = "median"
            
            # Log extraction results
            if prices:
                logger.info(f"Successfully extracted {len(prices)} prices for {product_name}")
                for p in prices[:3]:
                    logger.debug(f"  - {p.get('retailer')}: €{p.get('price')}")
            else:
                logger.warning(f"No prices extracted for {product_name}. Answer length: {len(response.get('answer', ''))}, Results: {len(response.get('results', []))}")
                # Log a sample of the answer text for debugging
                answer_sample = response.get('answer', '')[:200]
                logger.debug(f"Answer sample: {answer_sample}")
            
            return {
                "product": product_name,
                "prices": prices,
                "average_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "summary": response.get('answer', "Price information retrieved from web."),
                "source_count": len(prices),
                "average_price_method": avg_price_method,
                "fetched_at": time.time()
            }
        except Exception as e:
            logger.error(f"Web Search failed: {e}")
            return {
                "product": product_name,
                "prices": [],
                "average_price": None,
                "min_price": None,
                "max_price": None,
                "summary": f"Error retrieving prices: {str(e)}",
                "source_count": 0,
                "average_price_method": None,
                "fetched_at": time.time()
            }
    
    def _extract_prices_from_response(self, response: Dict, product_name: str) -> List[Dict]:
        """Extract structured price data from Tavily response."""
        prices = []
        
        # Try to extract prices from the answer text
        answer_text = response.get('answer', '')
        results = response.get('results', [])
        
        # Enhanced patterns to match German price formats
        # Patterns ordered by specificity (most specific first)
        price_patterns = [
            r'€\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # €999.99, €1.299,99, €999,99
            r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*€',  # 999.99€, 1.299,99€
            r'EUR\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # EUR 999.99
            r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*Euro',  # 999 Euro, 1.299,99 Euro
            r'Preis[:\s]+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # Preis: 999.99
            r'ab\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # ab 999€ (from price)
            r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*EUR',  # 999.99 EUR
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # German format: 1.299,99
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # US format: 1,299.99
        ]
        
        # Combine all text sources for better extraction
        all_text = answer_text + " "
        for result in results[:3]:
            all_text += result.get('content', '') + " "
            all_text += result.get('title', '') + " "
        
        logger.debug(f"Extracting prices from text (length: {len(all_text)})")
        
        # Extract from combined text
        extracted_prices = set()  # Use set to avoid duplicates
        for pattern in price_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches:
                try:
                    # Handle German format (1.299,99) and US format (1,299.99)
                    price_str = str(match)
                    # Replace thousands separators
                    if '.' in price_str and ',' in price_str:
                        # Determine format: if last comma before digits, it's German (1.299,99)
                        parts = price_str.split(',')
                        if len(parts) == 2 and len(parts[1]) == 2:
                            # German format: 1.299,99 -> 1299.99
                            price_str = price_str.replace('.', '').replace(',', '.')
                        else:
                            # US format: 1,299.99 -> 1299.99
                            price_str = price_str.replace(',', '')
                    elif ',' in price_str:
                        # Could be German decimal separator
                        if price_str.count(',') == 1:
                            price_str = price_str.replace(',', '.')
                        else:
                            price_str = price_str.replace(',', '')
                    elif '.' in price_str:
                        # Could be US format or German thousands
                        # If more than one dot, it's thousands separator
                        if price_str.count('.') > 1:
                            price_str = price_str.replace('.', '')
                    
                    price = float(price_str)
                    if 50 <= price <= 5000:  # Reasonable price range for smartphones
                        extracted_prices.add(round(price, 2))
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Failed to parse price '{match}': {e}")
                    continue
        
        # Filter prices by product category - smartphones should be €300-€2000
        # This helps filter out discount amounts, shipping costs, etc.
        product_lower_bound = self._get_price_lower_bound(product_name)
        product_upper_bound = self._get_price_upper_bound(product_name)
        
        filtered_prices = [
            p for p in extracted_prices 
            if product_lower_bound <= p <= product_upper_bound
        ]
        
        # If we filtered out all prices, use the original bounds as fallback
        if not filtered_prices and extracted_prices:
            logger.warning(f"All prices filtered out. Using original bounds (50-5000)")
            filtered_prices = [p for p in extracted_prices if 50 <= p <= 5000]
        
        # Collect fallback sources from results (prefer comparison sites)
        fallback_sources = []
        for result in results:
            url = result.get("url", "")
            if not url:
                continue
            if any(domain in url for domain in ["idealo.de", "geizhals.de", "billiger.de", "preis.de", "check24.de"]):
                fallback_sources.append(url)
        if not fallback_sources:
            # Use top result URLs as fallback if no comparison sites found
            fallback_sources = [r.get("url", "") for r in results if r.get("url")]

        # Convert to price info objects (attach a source link when possible)
        for idx, price_val in enumerate(sorted(filtered_prices)[:5]):  # Take first 5 unique prices
            source_url = fallback_sources[idx] if idx < len(fallback_sources) else None
            prices.append({
                "retailer": "Web Source",
                "price": price_val,
                "currency": "EUR",
                "source": source_url or "Tavily Answer"
            })
        
        logger.info(f"Extracted {len(prices)} prices from answer text (filtered from {len(extracted_prices)} candidates)")
        
        # Extract from individual search results (for retailer identification)
        # Include both comparison sites and retailers
        comparison_sites = ["idealo", "geizhals", "billiger", "preis.de", "Preisvergleich", "check24"]
        retailers = ["MediaMarkt", "Saturn", "Amazon", "Otto", "Zalando", "Cyberport", "Expert", "Notebooksbilliger"]
        all_sites = comparison_sites + retailers
        retailer_prices = {}  # Track prices by retailer
        
        for result in results[:10]:  # Check first 10 results
            title = result.get('title', '')
            content = result.get('content', '')
            url = result.get('url', '')
            
            # Try to identify retailer or comparison site
            retailer = None
            site_type = "Comparison Site"
            
            # Check if it's from a comparison site first (they aggregate prices)
            for comp_site in comparison_sites:
                if comp_site.lower() in title.lower() or comp_site.lower() in url.lower() or comp_site.lower() in content.lower():
                    retailer = comp_site  # Use comparison site name
                    site_type = "Price Comparison"
                    break
            
            # If not a comparison site, check for retailer
            if not retailer:
                for r in retailers:
                    if r.lower() in title.lower() or r.lower() in url.lower() or r.lower() in content.lower():
                        retailer = r
                        site_type = "Retailer"
                        break
            
            # If still not found, check URL domain
            if not retailer:
                url_lower = url.lower()
                if 'idealo.de' in url_lower:
                    retailer = "idealo"
                    site_type = "Price Comparison"
                elif 'geizhals.de' in url_lower:
                    retailer = "geizhals"
                    site_type = "Price Comparison"
                elif 'billiger.de' in url_lower:
                    retailer = "billiger"
                    site_type = "Price Comparison"
                elif 'preis.de' in url_lower:
                    retailer = "preis.de"
                    site_type = "Price Comparison"
                elif 'mediamarkt.de' in url_lower:
                    retailer = "MediaMarkt"
                    site_type = "Retailer"
                elif 'saturn.de' in url_lower:
                    retailer = "Saturn"
                    site_type = "Retailer"
                elif 'amazon.de' in url_lower:
                    retailer = "Amazon"
                    site_type = "Retailer"
            
            if not retailer:
                continue
            
            # Extract price from this result
            result_text = title + " " + content
            for pattern in price_patterns:
                matches = re.findall(pattern, result_text, re.IGNORECASE)
                for match in matches[:1]:  # One price per result
                    try:
                        # Same price parsing logic as above
                        price_str = str(match)
                        if '.' in price_str and ',' in price_str:
                            parts = price_str.split(',')
                            if len(parts) == 2 and len(parts[1]) == 2:
                                price_str = price_str.replace('.', '').replace(',', '.')
                            else:
                                price_str = price_str.replace(',', '')
                        elif ',' in price_str:
                            if price_str.count(',') == 1:
                                price_str = price_str.replace(',', '.')
                            else:
                                price_str = price_str.replace(',', '')
                        elif '.' in price_str:
                            if price_str.count('.') > 1:
                                price_str = price_str.replace('.', '')
                        
                        price = float(price_str)
                        # Use product-specific bounds for filtering
                        product_lower = self._get_price_lower_bound(product_name)
                        product_upper = self._get_price_upper_bound(product_name)
                        
                        if product_lower <= price <= product_upper:
                            # For comparison sites, they show prices from multiple retailers
                            # Extract retailer name from content if available
                            retailer_name = retailer
                            
                            # If from comparison site, try to extract actual retailer name
                            if site_type == "Price Comparison":
                                # Look for retailer mentions in content near the price
                                match_pos = content.lower().find(match.lower())
                                context = content[max(0, match_pos-150):match_pos+150].lower()
                                for r in retailers:
                                    if r.lower() in context:
                                        retailer_name = f"{retailer} ({r})"
                                        break
                            
                            # Store best price per retailer (comparison sites may have multiple prices)
                            price_key = retailer_name
                            if price_key not in retailer_prices or price < retailer_prices[price_key]['price']:
                                retailer_prices[price_key] = {
                                    "retailer": retailer_name,
                                    "price": round(price, 2),
                                    "currency": "EUR",
                                    "source": url,
                                    "site_type": site_type
                                }
                            break
                    except (ValueError, AttributeError):
                        continue
        
        # Add retailer-specific prices
        for retailer_price in retailer_prices.values():
            prices.append(retailer_price)
        
        logger.info(f"Extracted {len(retailer_prices)} retailer-specific prices")
        
        # Remove duplicates (same retailer, similar price)
        unique_prices = []
        seen_retailers = set()
        for price_info in prices:
            retailer_key = price_info["retailer"]
            if retailer_key not in seen_retailers:
                unique_prices.append(price_info)
                seen_retailers.add(retailer_key)
            elif len(unique_prices) < 5:  # Allow up to 5 prices
                unique_prices.append(price_info)
        
        return unique_prices[:5]  # Return max 5 prices

    def _median(self, values: List[float]) -> float:
        """Compute median for a list of floats."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        return sorted_vals[mid]

    def _is_outlier_spread(self, values: List[float]) -> bool:
        """Detect if values are highly skewed (suggests outliers)."""
        if not values:
            return False
        min_v = min(values)
        max_v = max(values)
        if min_v <= 0:
            return True
        # If max is more than 1.8x min, treat as skewed
        return (max_v / min_v) > 1.8
    
    def _get_price_lower_bound(self, product_name: str) -> float:
        """Get reasonable lower bound for product price based on product type."""
        product_lower = product_name.lower()
        
        # Smartphone price ranges
        if any(term in product_lower for term in ['iphone', 'samsung', 'galaxy', 'smartphone', 'phone']):
            return 300.0  # iPhones/Smartphones typically start around €300
        
        # Tablet price ranges
        if any(term in product_lower for term in ['ipad', 'tablet']):
            return 200.0
        
        # Default for electronics
        return 100.0
    
    def _get_price_upper_bound(self, product_name: str) -> float:
        """Get reasonable upper bound for product price based on product type."""
        product_lower = product_name.lower()
        
        # Premium smartphones can go up to €2000
        if any(term in product_lower for term in ['iphone', 'samsung', 'galaxy', 'smartphone', 'phone']):
            return 2500.0
        
        # Tablets
        if any(term in product_lower for term in ['ipad', 'tablet']):
            return 2000.0
        
        # Default for electronics
        return 5000.0

# For standalone testing
if __name__ == "__main__":
    scout = WebScoutAgent()
    result = scout.get_competitor_prices("Apple iPhone 15 128GB")
    print(json.dumps(result, indent=2))