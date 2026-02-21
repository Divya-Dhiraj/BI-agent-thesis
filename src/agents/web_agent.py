from tavily import TavilyClient
from src.config import Config
from loguru import logger
from langchain_core.tools import tool

class WebScoutAgent:
    def __init__(self):
        self.client = TavilyClient(api_key=Config.TAVILY_API_KEY)
        logger.success("Web Scout Agent (Tavily) Initialized.")

    @tool
    def get_competitor_prices(self, product_name: str):
        """
        Searches for current prices of a smartphone on German retail sites 
        (MediaMarkt, Saturn, Amazon.de) and returns a summary.
        """
        query = f"Preis {product_name} kaufen MediaMarkt Saturn Amazon.de Deutschland"
        logger.info(f"Web Search Query: {query}")
        
        try:
            # We use 'advanced' depth for higher accuracy in pricing
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True
            )
            
            # Extract the AI-generated answer which usually contains the price summary
            return response.get('answer', "No direct price found, check search results.")
        except Exception as e:
            logger.error(f"Web Search failed: {e}")
            return "Competitor price search currently unavailable."

# For standalone testing
if __name__ == "__main__":
    scout = WebScoutAgent()
    print(scout.get_competitor_prices("Apple iPhone 15 128GB"))