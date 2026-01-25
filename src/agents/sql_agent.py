import json
import re
from typing import TypedDict, List, Annotated, Optional, Dict, Any
import operator

from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from src.database import DatabaseManager
from src.config import Config
from src.knowledge import DOMAIN_KNOWLEDGE  # <--- IMPORT THE BRAIN
from src.agents.web_agent import WebScoutAgent
from loguru import logger

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add] 
    question: str
    target_asins: List[str]
    search_term: str
    sql_query: Optional[str]
    sql_error: Optional[str]
    data_result: Optional[str]
    attempt_count: int
    final_answer: Optional[str]
    chart_json: Optional[dict]
    needs_price_comparison: bool
    price_mode: Optional[str]
    use_external_prices: bool
    web_prices: Optional[Dict[str, Any]]
    db_prices: Optional[Dict[str, Any]]
    price_comparison_result: Optional[Dict[str, Any]]
    memory_summary: Optional[str]
    memory_topics: Optional[List[str]]
    memory_last_topic: Optional[str]
    memory_vectors: Optional[List[Dict[str, Any]]]

class BusinessAnalystAgent:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm = ChatOpenAI(model=Config.OPENAI_MODEL, temperature=0, api_key=Config.OPENAI_API_KEY)
        self.memory_embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key=Config.OPENAI_API_KEY)
        self.checkpointer = MemorySaver()
        self.web_scout = WebScoutAgent()

        # Define Graph
        workflow = StateGraph(AgentState)
        workflow.add_node("lookup", self.node_lookup)
        workflow.add_node("price_checker", self.node_price_checker)  # NEW: Check if price comparison needed
        workflow.add_node("price_comparison", self.node_price_comparison)  # NEW: Fetch and compare prices
        workflow.add_node("architect", self.node_architect) # <--- THE SMART LOGIC
        workflow.add_node("executor", self.node_executor)
        workflow.add_node("reporter", self.node_reporter)
        workflow.add_node("memory_update", self.node_memory_update)
        
        workflow.set_entry_point("lookup")
        workflow.add_edge("lookup", "price_checker")
        
        # Route based on whether price comparison is needed
        workflow.add_conditional_edges(
            "price_checker",
            self.should_do_price_comparison,
            {"yes": "price_comparison", "no": "architect"}
        )
        
        workflow.add_edge("price_comparison", "reporter")  # Price comparison goes directly to reporter
        workflow.add_edge("architect", "executor")
        
        workflow.add_conditional_edges(
            "executor",
            self.check_status,
            {"retry": "architect", "success": "reporter", "fail": "reporter"}
        )
        workflow.add_edge("reporter", "memory_update")
        workflow.add_edge("memory_update", END)
        self.app = workflow.compile(checkpointer=self.checkpointer)
        logger.success("Agent v28.0 (Robust + Knowledge + Price Comparison) Compiled.")

    def node_lookup(self, state: AgentState):
        """Phase 1: Identify if we need specific products or global stats."""
        last_msg = state["messages"][-1]
        question = last_msg.content if isinstance(last_msg, HumanMessage) else state.get("question")
        
        # Get conversation history for context
        conversation_history = self._get_conversation_context(
            state["messages"],
            question,
            state.get("memory_summary"),
            state.get("memory_topics"),
            state.get("memory_vectors")
        )
        
        logger.info(f"Step 1: Identifying products for: '{question}'")

        # Smart Extraction: Is this about a specific item or the whole business?
        # Now includes conversation context to understand follow-ups
        prompt = f"""
        You are analyzing a user's question about business data. Consider the conversation history to understand if this is a follow-up question.
        
        ### CONVERSATION HISTORY (Previous Q&A):
        {conversation_history}
        
        ### CURRENT QUESTION:
        "{question}"
        
        ### TASK:
        1. Determine if this is a follow-up question referring to previous context (e.g., "What about returns?", "Show me more details", "Compare that with...")
        2. If it's a follow-up, extract what it's referring to from the conversation history
        3. Extract the product/brand name if mentioned, or infer from context
        4. If asking about general performance/trends with no specific product, return 'ALL_MARKET'
        
        ### OUTPUT FORMAT:
        - If specific product/brand mentioned: Return the product/brand name
        - If follow-up about previous products: Return the product/brand from previous context
        - If general question: Return 'ALL_MARKET'
        
        Output ONLY the extracted term (product name or 'ALL_MARKET').
        """
        try:
            search_term = self.llm.invoke(prompt).content.strip().replace('"', '').replace("'", "")
            logger.info(f"Extracted search term: '{search_term}' (from context-aware analysis)")
        except Exception as e:
            logger.error(f"LLM Lookup Error: {e}")
            search_term = "ALL_MARKET"
        
        target_asins = []
        if search_term != "ALL_MARKET":
            session = self.db_manager.get_session()
            try:
                # Hybrid Search: Vectors + Keywords
                sql = text("SELECT asin FROM product_catalog WHERE search_vector @@ websearch_to_tsquery('simple', :t) LIMIT 20")
                results = session.execute(sql, {"t": search_term}).fetchall()
                target_asins = [row[0] for row in results]
                logger.info(f"DB Lookup found {len(target_asins)} items.")
            except Exception as e:
                logger.error(f"Lookup failed: {e}")
            finally:
                session.close()

        return {
            "target_asins": target_asins, 
            "search_term": search_term, 
            "question": question, 
            "attempt_count": 0,
            "needs_price_comparison": False,  # Will be set by price_checker node
            "price_mode": None,  # Will be set by price_checker node
            "use_external_prices": state.get("use_external_prices", True),
            "memory_vectors": state.get("memory_vectors", [])
        }

    def node_price_checker(self, state: AgentState):
        """Check if the question is about price comparison."""
        question = state.get("question", "")
        conversation_history = self._get_conversation_context(
            state["messages"],
            question,
            state.get("memory_summary"),
            state.get("memory_topics"),
            state.get("memory_vectors")
        )
        use_external_prices = state.get("use_external_prices", True)
        
        logger.info("Checking if price comparison is needed...")
        
        # Hard override: external prices disabled
        if not use_external_prices:
            return {"needs_price_comparison": False, "price_mode": "DB_ONLY"}

        # Quick keyword routing to reduce LLM misroutes
        q = (question or "").lower()
        if any(k in q for k in ["online", "external", "web", "market", "competitor", "price comparison", "compare"]):
            if any(k in q for k in ["compare", "vs", "versus", "difference", "gap"]):
                return {"needs_price_comparison": True, "price_mode": "COMPARE"}
            return {"needs_price_comparison": True, "price_mode": "WEB_ONLY"}
        if any(k in q for k in ["price", "pricing", "cost", "avg price", "average price"]):
            return {"needs_price_comparison": False, "price_mode": "DB_ONLY"}

        # Use LLM to detect if this is a price comparison or web-only price question
        prompt = f"""
        Analyze this question and choose ONE mode:
        - COMPARE: user wants online prices compared to database prices
        - WEB_ONLY: user wants online/market prices only (no DB comparison)
        - DB_ONLY: user wants only database/internal prices (price-related)
        - NOT_PRICE: not a price-related question
        
        ### CONVERSATION HISTORY:
        {conversation_history}
        
        ### CURRENT QUESTION:
        "{question}"
        
        ### TASK:
        Determine if the user is asking for:
        1. A comparison between online/market prices and database prices
        2. Only online/market prices
        3. Only database/internal prices
        
        ### OUTPUT:
        Respond with ONLY one of: COMPARE, WEB_ONLY, DB_ONLY, NOT_PRICE
        """
        
        try:
            response = self.llm.invoke(prompt).content.strip().upper()
            mode = "NOT_PRICE"
            if "COMPARE" in response:
                mode = "COMPARE"
            elif "WEB_ONLY" in response:
                mode = "WEB_ONLY"
            elif "DB_ONLY" in response:
                mode = "DB_ONLY"
            needs_comparison = mode in ("COMPARE", "WEB_ONLY")
            logger.info(f"Price mode detected: {mode}")
            return {"needs_price_comparison": needs_comparison, "price_mode": mode}
        except Exception as e:
            logger.error(f"Price checker error: {e}")
            return {"needs_price_comparison": False, "price_mode": "NOT_PRICE"}
    
    def should_do_price_comparison(self, state: AgentState) -> str:
        """Route to price comparison or regular SQL flow."""
        if state.get("needs_price_comparison", False):
            return "yes"
        return "no"
    
    def node_price_comparison(self, state: AgentState):
        """Fetch web prices and compare with database prices."""
        logger.info("Fetching and comparing prices...")
        
        question = state.get("question", "")
        target_asins = state.get("target_asins", [])
        search_term = state.get("search_term", "")
        conversation_history = self._get_conversation_context(
            state["messages"],
            question,
            state.get("memory_summary"),
            state.get("memory_topics"),
            state.get("memory_vectors")
        )
        
        # Determine product name for web search
        product_name = search_term if search_term != "ALL_MARKET" else ""
        
        # If no specific product, try to extract from question
        if not product_name or product_name == "ALL_MARKET":
            prompt = f"""
            Extract the product name from this question for price comparison:
            Question: "{question}"
            Conversation: {conversation_history}
            
            Output ONLY the product name (e.g., "iPhone 15", "Samsung Galaxy S23"). 
            If unclear, output "UNKNOWN".
            """
            try:
                product_name = self.llm.invoke(prompt).content.strip().replace('"', '').replace("'", "")
                if "UNKNOWN" in product_name.upper():
                    product_name = ""
            except:
                product_name = ""
        
        # Fetch web prices
        web_prices_data = None
        if product_name:
            logger.info(f"Fetching web prices for: {product_name}")
            web_prices_data = self.web_scout.get_competitor_prices(product_name)
        else:
            logger.warning("No product name found for web price search")
            web_prices_data = {
                "product": "Unknown",
                "prices": [],
                "average_price": None,
                "summary": "Could not identify product for price comparison."
            }
        
        # Fetch database prices only when needed
        price_mode = state.get("price_mode", "COMPARE")
        if price_mode == "WEB_ONLY":
            db_prices_data = {
                "product": product_name or "Unknown",
                "average_price": None,
                "summary": "Database comparison skipped (online prices only requested)."
            }
        else:
            db_prices_data = self._get_database_prices(target_asins, product_name)
        
        # Compare prices
        comparison_result = self._compare_prices(web_prices_data, db_prices_data, product_name)

        # If the user explicitly wants analysis, use LLM to generate a richer narrative
        wants_analysis = self._needs_price_analysis(
            state.get("question", ""),
            self._get_conversation_context(
                state["messages"],
                state.get("question", ""),
                state.get("memory_summary"),
                state.get("memory_topics"),
                state.get("memory_vectors")
            )
        )
        if wants_analysis:
            comparison_result["summary"] = self._generate_price_analysis(
                question=state.get("question", ""),
                product_name=product_name or web_prices_data.get("product", "Unknown"),
                web_prices=web_prices_data,
                db_prices=db_prices_data,
                base_summary=comparison_result.get("summary", ""),
                conversation_history=self._get_conversation_context(
                    state["messages"],
                    state.get("question", ""),
                    state.get("memory_summary"),
                    state.get("memory_topics"),
                    state.get("memory_vectors")
                )
            )
        
        return {
            "web_prices": web_prices_data,
            "db_prices": db_prices_data,
            "price_comparison_result": comparison_result,
            "final_answer": comparison_result.get("summary", "Price comparison completed."),
            "chart_json": comparison_result.get("chart_data")
        }
    
    def _get_database_prices(self, target_asins: List[str], product_name: str) -> Dict[str, Any]:
        """Get average selling prices from database."""
        try:
            session = self.db_manager.get_session()
            
            # If we already have ASINs, filter them to the exact model
            if target_asins:
                safe_asins = "', '".join([str(a).replace("'", "''") for a in target_asins])
                candidates = []
                try:
                    sql = text(f"""
                        SELECT asin, item_name
                        FROM product_catalog
                        WHERE asin IN ('{safe_asins}')
                        LIMIT 50
                    """)
                    results = session.execute(sql).fetchall()
                    candidates = [{"asin": r[0], "item_name": r[1]} for r in results]
                except Exception:
                    candidates = []

                if not candidates:
                    sql = text(f"""
                        SELECT DISTINCT asin, item_name
                        FROM shipped_raw
                        WHERE asin IN ('{safe_asins}')
                        LIMIT 50
                    """)
                    results = session.execute(sql).fetchall()
                    candidates = [{"asin": r[0], "item_name": r[1]} for r in results]

                if candidates:
                    target_asins = self._filter_asins_with_llm(product_name, candidates)

            if not target_asins:
                # Try to find products by name from catalog
                if product_name:
                    sql = text("""
                        SELECT asin, item_name FROM product_catalog 
                        WHERE search_vector @@ websearch_to_tsquery('simple', :term)
                        LIMIT 30
                    """)
                    results = session.execute(sql, {"term": product_name}).fetchall()
                    if results:
                        candidate_items = [{"asin": r[0], "item_name": r[1]} for r in results]
                        target_asins = self._filter_asins_with_llm(product_name, candidate_items)
            
            # Fallback: if no catalog match, try direct lookup in shipped_raw by name/brand/manufacturer
            if not target_asins and product_name:
                like_term = f"%{product_name}%"
                sql = text("""
                    SELECT DISTINCT s.asin, s.item_name
                    FROM shipped_raw s
                    WHERE s.item_name ILIKE :like_term
                       OR s.brand_name ILIKE :like_term
                       OR s.manufacturer_name ILIKE :like_term
                    LIMIT 30
                """)
                results = session.execute(sql, {"like_term": like_term}).fetchall()
                if results:
                    candidate_items = [{"asin": r[0], "item_name": r[1]} for r in results]
                    target_asins = self._filter_asins_with_llm(product_name, candidate_items)

            if not target_asins:
                return {
                    "product": product_name or "Unknown",
                    "average_price": None,
                    "min_price": None,
                    "max_price": None,
                    "price_data": [],
                    "summary": "No matching products found in database."
                }
            
            # Calculate average prices from shipped_raw
            safe_asins = "', '".join([str(a).replace("'", "''") for a in target_asins])
            sql = text(f"""
                SELECT 
                    s.asin,
                    s.item_name,
                    SUM(s.shipped_units) as total_units,
                    SUM(s.product_gms) as total_revenue,
                    CASE 
                        WHEN SUM(s.shipped_units) > 0 
                        THEN SUM(s.product_gms) / SUM(s.shipped_units)
                        ELSE NULL
                    END as avg_price
                FROM shipped_raw s
                WHERE s.asin IN ('{safe_asins}')
                GROUP BY s.asin, s.item_name
                HAVING SUM(s.shipped_units) > 0
                ORDER BY avg_price DESC
                LIMIT 10
            """)
            
            results = session.execute(sql).fetchall()
            
            price_data = []
            prices = []
            for row in results:
                asin, item_name, units, revenue, avg_price = row
                if avg_price:
                    price_data.append({
                        "asin": asin,
                        "item_name": item_name,
                        "average_price": float(avg_price),
                        "total_units": int(units),
                        "total_revenue": float(revenue)
                    })
                    prices.append(float(avg_price))
            
            session.close()
            
            avg_price = sum(prices) / len(prices) if prices else None
            min_price = min(prices) if prices else None
            max_price = max(prices) if prices else None
            
            return {
                "product": product_name or "Database Products",
                "average_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "price_data": price_data,
                "summary": f"Found {len(price_data)} products in database with average price of €{avg_price:.2f}" if avg_price else "No price data found."
            }
            
        except Exception as e:
            logger.error(f"Database price fetch error: {e}")
            error_text = str(e)
            if "relation \"product_catalog\" does not exist" in error_text:
                return {
                    "product": product_name or "Unknown",
                    "average_price": None,
                    "summary": (
                        "Database tables are not initialized. "
                        "Please run `python src/database.py` to create tables, "
                        "then `python src/ingestion.py` to load data."
                    )
                }
            return {
                "product": product_name or "Unknown",
                "average_price": None,
                "summary": f"Error fetching database prices: {error_text}"
            }
    
    def _compare_prices(self, web_prices: Dict, db_prices: Dict, product_name: str) -> Dict[str, Any]:
        """Compare web prices with database prices."""
        web_avg = web_prices.get("average_price")
        db_avg = db_prices.get("average_price")
        
        # If we have web prices but no database prices, still show web prices
        if web_avg and not db_avg:
            summary = f"""
**Price Information: {product_name}**

**Online Market Prices:**
"""
            # Add web price details
            for price_info in web_prices.get("prices", [])[:5]:
                retailer = price_info.get("retailer", "Unknown")
                price = price_info.get("price", 0)
                source = price_info.get("source")
                if source and source != "Tavily Answer":
                    summary += f"\n- {retailer}: €{price:.2f} ([source]({source}))"
                else:
                    summary += f"\n- {retailer}: €{price:.2f}"
            
            if web_avg:
                summary += f"\n\n**Average Online Price:** €{web_avg:.2f}"
                if web_prices.get("min_price") and web_prices.get("max_price"):
                    summary += f"\n**Price Range:** €{web_prices['min_price']:.2f} - €{web_prices['max_price']:.2f}"
            
            summary += f"\n\n**Database Prices:**\n{db_prices.get('summary', 'No matching products found in database. This product may not have sales records yet.')}"
            
            # Create chart with just web prices if available
            chart_data = None
            if web_avg and web_prices.get("prices"):
                chart_data = {
                    "type": "bar",
                    "title": f"Online Prices: {product_name}",
                    "data": {
                        "labels": [p.get("retailer", "Unknown") for p in web_prices.get("prices", [])[:5]],
                        "values": [p.get("price", 0) for p in web_prices.get("prices", [])[:5]]
                    }
                }
            
            return {"summary": summary, "chart_data": chart_data, "web_avg": web_avg, "db_avg": None}
        
        # If we have database prices but no web prices
        if db_avg and not web_avg:
            summary = f"""
**Price Information: {product_name}**

**Database Prices:**
{db_prices.get('summary', 'No database prices available')}
"""
            if db_prices.get("min_price") and db_prices.get("max_price"):
                summary += f"\n**Price Range:** €{db_prices['min_price']:.2f} - €{db_prices['max_price']:.2f}"
            
            summary += f"\n\n**Online Market Prices:**\n{web_prices.get('summary', 'Unable to fetch current online prices. Please try again later.')}"
            
            return {"summary": summary, "chart_data": None, "web_avg": None, "db_avg": db_avg}
        
        # If neither available
        if not web_avg and not db_avg:
            summary = f"""
**Price Information: {product_name}**

**Web Prices:**
{web_prices.get('summary', 'No web prices available')}

**Database Prices:**
{db_prices.get('summary', 'No database prices available')}

Note: Unable to retrieve price information from either source.
"""
            return {"summary": summary, "chart_data": None, "web_avg": None, "db_avg": None}
        
        # Calculate difference
        difference = db_avg - web_avg
        difference_percent = (difference / web_avg * 100) if web_avg > 0 else 0
        
        # Create comparison summary
        comparison_text = "higher" if difference > 0 else "lower"
        abs_diff = abs(difference)
        abs_percent = abs(difference_percent)
        
        summary = f"""
        **Price Comparison: {product_name}**
        
        **Database Average Price:** €{db_avg:.2f}
        **Online Market Average Price:** €{web_avg:.2f}
        
        **Difference:** Database prices are €{abs_diff:.2f} ({abs_percent:.1f}%) {comparison_text} than online market prices.
        
        **Web Price Sources:**
        """
        
        # Add web price details
        for price_info in web_prices.get("prices", [])[:5]:
            retailer = price_info.get("retailer", "Unknown")
            price = price_info.get("price", 0)
            source = price_info.get("source")
            if source and source != "Tavily Answer":
                summary += f"\n- {retailer}: €{price:.2f} ([source]({source}))"
            else:
                summary += f"\n- {retailer}: €{price:.2f}"
        
        summary += f"\n\n**Database Price Range:**"
        if db_prices.get("min_price") and db_prices.get("max_price"):
            summary += f"\n- Minimum: €{db_prices['min_price']:.2f}"
            summary += f"\n- Maximum: €{db_prices['max_price']:.2f}"
        
        # Create chart data
        chart_data = {
            "type": "bar",
            "title": f"Price Comparison: {product_name}",
            "data": {
                "labels": ["Database Average", "Online Market Average"],
                "values": [round(db_avg, 2), round(web_avg, 2)]
            }
        }
        
        return {
            "summary": summary,
            "chart_data": chart_data,
            "web_avg": web_avg,
            "db_avg": db_avg,
            "difference": difference,
            "difference_percent": difference_percent
        }

    def _filter_asins_with_llm(self, product_name: str, candidate_items: List[Dict[str, str]]) -> List[str]:
        """Use LLM to filter ASINs to the exact product/model requested."""
        if not candidate_items:
            return []

        # Pre-filter by exact model tokens to reduce noise (no hardcoded SKUs)
        product_lower = product_name.lower()
        variants = ["pro", "max", "plus", "mini", "ultra"]
        wants_variant = [v for v in variants if v in product_lower]

        def _matches_variant(name: str) -> bool:
            name_lower = name.lower()
            if wants_variant:
                return all(v in name_lower for v in wants_variant)
            # Exclude variant names if not requested
            return not any(v in name_lower for v in variants)

        filtered = [c for c in candidate_items if _matches_variant(c.get("item_name", ""))]
        if filtered:
            candidate_items = filtered

        # Keep prompt size reasonable
        candidate_items = candidate_items[:30]
        items_text = "\n".join([f"{c['asin']}\t{c['item_name']}" for c in candidate_items])

        prompt = f"""
        You are selecting which products match the user's requested model.
        User request: "{product_name}"

        Rules:
        - Be strict about the model name.
        - Do NOT include variants like Pro/Max/Plus unless explicitly mentioned.
        - If the request includes a variant (e.g., "Pro"), include only that variant.
        - Prefer exact/near-exact name matches.

        Candidates (ASIN<TAB>Item Name):
        {items_text}

        Return ONLY a JSON array of ASINs to keep. Example: ["B0001","B0002"]
        """
        try:
            response = self.llm.invoke(prompt).content.strip()
            match = re.search(r"\[(.*?)\]", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list) and parsed:
                    return [str(a) for a in parsed]
        except Exception as e:
            logger.error(f"ASIN filtering failed: {e}")

        # Fallback: keep all candidates if LLM fails
        return [c["asin"] for c in candidate_items]

    def _needs_price_analysis(self, question: str, conversation_history: str) -> bool:
        """Detect if the user asked for analysis/insights beyond a basic comparison."""
        prompt = f"""
        Determine if the user is explicitly asking for analysis/insights, not just a price list.

        Conversation:
        {conversation_history}

        Current question:
        "{question}"

        Return ONLY "YES" or "NO".
        YES if the user asks for analysis, insights, explanation, reasons, interpretation, or summary.
        NO if they only ask for prices or a simple comparison.
        """
        try:
            response = self.llm.invoke(prompt).content.strip().upper()
            return "YES" in response
        except Exception as e:
            logger.error(f"Price analysis intent check failed: {e}")
            return False

    def _generate_price_analysis(
        self,
        question: str,
        product_name: str,
        web_prices: Dict[str, Any],
        db_prices: Dict[str, Any],
        base_summary: str,
        conversation_history: str
    ) -> str:
        """Generate a more natural, analysis-style response using LLM."""
        web_list = web_prices.get("prices", [])
        db_avg = db_prices.get("average_price")
        web_avg = web_prices.get("average_price")

        # Build a compact, structured context for the LLM
        web_price_lines = []
        for p in web_list[:5]:
            retailer = p.get("retailer", "Unknown")
            price = p.get("price", 0)
            source = p.get("source")
            if source and source != "Tavily Answer":
                web_price_lines.append(f"- {retailer}: €{price:.2f} (source: {source})")
            else:
                web_price_lines.append(f"- {retailer}: €{price:.2f}")

        prompt = f"""
        You are a BI analyst. Provide a short, clear analysis in plain language.
        The user asked: "{question}"

        Product: {product_name}
        Database average price: {f"€{db_avg:.2f}" if db_avg else "N/A"}
        Online average price: {f"€{web_avg:.2f}" if web_avg else "N/A"}

        Web prices:
        {chr(10).join(web_price_lines) if web_price_lines else "No web price list available."}

        Base comparison summary:
        {base_summary}

        Instructions:
        - Keep it concise (4-6 sentences).
        - Explain what the comparison means (higher/lower, margin).
        - If data is missing, say what is missing and what was still found.
        - Do NOT invent sources or prices.
        - End with a short recommendation (1 sentence).
        """
        try:
            analysis = self.llm.invoke(prompt).content.strip()
        except Exception as e:
            logger.error(f"Price analysis generation failed: {e}")
            analysis = base_summary

        # Append a clean, hyperlink-friendly sources list
        source_lines = []
        for p in web_list[:5]:
            retailer = p.get("retailer", "Unknown")
            price = p.get("price", 0)
            source = p.get("source")
            if source and source != "Tavily Answer":
                source_lines.append(f"- {retailer}: €{price:.2f} ([source]({source}))")
            else:
                source_lines.append(f"- {retailer}: €{price:.2f}")

        if source_lines:
            analysis += "\n\n**Sources:**\n" + "\n".join(source_lines)

        return analysis

    def node_architect(self, state: AgentState):
        """Phase 2: The Reasoning Engine."""
        logger.info("Step 2: Architecting SQL")
        asins = state.get("target_asins", [])
        
        # Get conversation history for context
        conversation_history = self._get_conversation_context(
            state["messages"],
            state.get("question", ""),
            state.get("memory_summary"),
            state.get("memory_topics"),
            state.get("memory_vectors")
        )
        
        # Safe Filter Logic Construction
        filter_logic = ""
        if asins:
            # Manually construct the string to prevent f-string backslash errors
            safe_asins = "', '".join([str(a).replace("'", "''") for a in asins])
            filter_logic = f"AND s.asin IN ('{safe_asins}')"
        
        # --- THE PROMPT THAT MAKES IT SMART ---
        system_prompt = f"""
        You are an Expert Amazon Data Analyst. 
        You have deep knowledge of the database schema and business definitions.
        
        ### YOUR KNOWLEDGE BASE (STRICTLY ADHERE TO THIS)
        {DOMAIN_KNOWLEDGE}

        ### AVAILABLE TABLES
        1. **shipped_raw** (Sales): ncrc_su_pk, asin, item_name, year, month, shipped_units, shipped_cogs, product_gms, brand_name, manufacturer_name...
        2. **concession_raw** (Returns): ncrc_cu_pk, asin, year, month, mapped_year, mapped_month, conceded_units, ncrc, defect_category, root_cause, brand_name...
        
        ### CONVERSATION CONTEXT (Previous Questions & Answers)
        {conversation_history}
        
        ### CURRENT USER QUESTION
        "{state['question']}"
        
        ### IMPORTANT: CONTEXT AWARENESS
        - If this is a follow-up question (e.g., "What about returns?", "Show me more details", "Compare that"), 
          use information from the conversation history to understand what the user is referring to.
        - If the user says "that product", "those items", "it", etc., refer to products mentioned in previous questions.
        - Maintain consistency with previous queries (e.g., if they asked about iPhones, and now ask "what about returns?", 
          they likely mean returns for iPhones).
        
        ### INSTRUCTIONS
        1. **Interpret Meanings:** If user says "bad products", look for high NCRC or Defect Categories.
        2. **Join Correctly:** If you need both Sales and Returns, use the `mapped_year` logic defined in the Knowledge Base.
        3. **Filter:** {f"Apply filter: {filter_logic}" if filter_logic else "No product filter needed."}
        4. **Aggregation:** - If the user asks "Trend" or "High Level", GROUP BY Month/Quarter.
           - If the user asks "Details", show specific rows.
        5. **Failsafe:** Use `CAST(asin AS TEXT)` for joins to avoid type errors.
        
        Output ONLY valid PostgreSQL SQL.
        """
        
        try:
            response = self.llm.invoke(system_prompt).content
            # Clean markdown
            sql = response.replace("```sql", "").replace("```", "").strip()
            return {"sql_query": sql, "attempt_count": state.get("attempt_count", 0) + 1}
        except Exception as e:
            return {"sql_error": str(e)}

    def node_executor(self, state: AgentState):
        """Phase 3: Run Query."""
        logger.info("Step 3: Executing SQL")
        if not state.get("sql_query"):
             return {"sql_error": "No SQL generated"}

        try:
            import pandas as pd
            # --- FIX: Use a connection context manager ---
            with self.db_manager.engine.connect() as connection:
                df = pd.read_sql(text(state["sql_query"]), connection)
            # ---------------------------------------------
            
            if df.empty:
                return {"sql_error": "Query returned no data.", "data_result": None}
            return {"data_result": df.to_csv(index=False), "sql_error": None}
        except Exception as e:
            error_text = str(e)
            if "does not exist" in error_text:
                return {"sql_error": f"MISSING_TABLE: {error_text}", "data_result": None}
            return {"sql_error": error_text, "data_result": None}

    def check_status(self, state: AgentState):
        """Phase 4: Self-Correction."""
        if state.get("sql_error") and state.get("attempt_count", 0) < 3:
            logger.warning(f"Retrying due to error: {state['sql_error']}")
            return "retry"
        return "success" if state.get("data_result") else "fail"

    def node_reporter(self, state: AgentState):
        """Phase 5: Analyst Summary."""
        logger.info("Step 4: Reporting")
        
        # Check if this is a price comparison result
        if state.get("needs_price_comparison") and state.get("price_comparison_result"):
            comparison_result = state.get("price_comparison_result", {})
            summary = comparison_result.get("summary", "Price comparison completed.")
            summary = self._clean_text(summary)
            return {
                "final_answer": summary,
                "chart_json": comparison_result.get("chart_data"),
                "messages": [AIMessage(content=str(summary))]
            }

        if (state.get("sql_error") or "").startswith("MISSING_TABLE"):
            message = (
                "Database tables are not initialized. Please run `python src/database.py` "
                "to create tables, then `python src/ingestion.py` to load data. "
                "After that, internal queries will work."
            )
            return {
                "final_answer": message,
                "chart_json": None,
                "messages": [AIMessage(content=message)]
            }
        
        # Regular reporting flow
        # safely handle NoneType for data_result
        if state.get("sql_error") and not state.get("data_result"):
            message = f"Query failed: {state.get('sql_error')}"
            message = self._clean_text(message)
            return {
                "final_answer": message,
                "chart_json": None,
                "messages": [AIMessage(content=message)]
            }

        data_preview = (state.get("data_result") or "No data found.")[:2500]
        
        # Get conversation history for context
        conversation_history = self._get_conversation_context(
            state["messages"],
            state.get("question", ""),
            state.get("memory_summary"),
            state.get("memory_topics"),
            state.get("memory_vectors")
        )
        
        prompt = f"""
        You are a BI Manager presenting to executives.
        
        ### CONVERSATION CONTEXT (Previous Q&A):
        {conversation_history}
        
        ### CURRENT QUESTION:
        {state['question']}
        
        ### DATA EVIDENCE:
        {data_preview}
        
        ### TASK:
        1. Answer the question directly using the data.
        2. If this is a follow-up question, acknowledge the connection to previous questions (e.g., "Following up on your previous question about iPhones...").
        3. Explain *why* (using the logic like "High NCRC driven by defects").
        4. Create a chart configuration with the MOST suitable chart type:
           - line: trends over time (months/quarters)
           - bar: categorical comparisons
           - pie: share/percentage breakdowns
           - scatter: relationships/correlation
        5. Make your answer conversational and context-aware.
        
        Output strictly JSON: {{ "narrative": "...", "chart": {{ "type": "bar|line|pie|scatter", "data": {{ "labels": [], "values": [] }}, "title": "..." }} }}
        """
        
        narrative = "Could not generate report."
        chart = None

        try:
            res = self.llm.invoke(prompt).content
            # ROBUST JSON PARSING
            match = re.search(r"(\{.*\})", res, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))
                narrative = parsed.get("narrative", "No narrative provided.")
                chart = parsed.get("chart", None)
            else:
                narrative = res
        except Exception as e:
            logger.error(f"Reporting Error: {e}")
            narrative = f"Data was found, but the analysis failed: {e}. Here is the raw data preview: {data_preview[:500]}..."

        narrative = self._clean_text(narrative)
        return {
            "final_answer": narrative,
            "chart_json": chart,
            "messages": [AIMessage(content=str(narrative))]
        }

    def node_memory_update(self, state: AgentState):
        """Update dynamic memory after a response is produced."""
        question = state.get("question", "")
        answer = state.get("final_answer", "")
        memory_summary = state.get("memory_summary") or ""
        memory_topics = state.get("memory_topics") or []
        memory_last_topic = state.get("memory_last_topic")
        memory_vectors = state.get("memory_vectors") or []

        updated = self._update_memory_state(
            question=question,
            answer=answer,
            memory_summary=memory_summary,
            memory_topics=memory_topics,
            memory_last_topic=memory_last_topic
        )

        # Store semantic memory for retrieval
        memory_vectors = self._store_memory_vector(
            memory_vectors=memory_vectors,
            question=question,
            answer=answer,
            topics=updated.get("memory_topics") or []
        )

        return {
            "memory_summary": updated.get("memory_summary"),
            "memory_topics": updated.get("memory_topics"),
            "memory_last_topic": updated.get("memory_last_topic"),
            "memory_vectors": memory_vectors
        }

    def _update_memory_state(
        self,
        question: str,
        answer: str,
        memory_summary: str,
        memory_topics: List[str],
        memory_last_topic: Optional[str]
    ) -> Dict[str, Any]:
        """Summarize and update memory with relevance and topic shift handling."""
        prompt = f"""
        You are a memory manager for a chat assistant.
        Update the memory summary and topics based on the latest Q&A.

        Current memory summary:
        {memory_summary or "None"}

        Current memory topics (list):
        {memory_topics or []}

        Last topic:
        {memory_last_topic or "None"}

        Latest question:
        "{question}"

        Latest answer:
        "{answer}"

        Instructions:
        - If the latest question is a NEW TOPIC, start a new summary focused on the new topic.
        - If it is a FOLLOW-UP, update the existing summary.
        - Keep summary concise (3-6 sentences).
        - Update topics as a short list of key entities/models/metrics.
        - Output strict JSON with keys: memory_summary, memory_topics, memory_last_topic.
        """
        try:
            response = self.llm.invoke(prompt).content
            match = re.search(r"(\{.*\})", response, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))
                return {
                    "memory_summary": parsed.get("memory_summary", memory_summary),
                    "memory_topics": parsed.get("memory_topics", memory_topics),
                    "memory_last_topic": parsed.get("memory_last_topic", memory_last_topic)
                }
        except Exception as e:
            logger.error(f"Memory update failed: {e}")

        return {
            "memory_summary": memory_summary,
            "memory_topics": memory_topics,
            "memory_last_topic": memory_last_topic
        }

    def _get_conversation_context(
        self,
        messages: List[BaseMessage],
        question: str,
        memory_summary: Optional[str] = None,
        memory_topics: Optional[List[str]] = None,
        memory_vectors: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Extract conversation history only if the question is a follow-up."""
        if len(messages) <= 1:
            return "No previous conversation."

        if not self._is_follow_up(question, messages, memory_summary, memory_topics):
            return "No previous conversation."
        
        # Get last 5 exchanges (10 messages: 5 Q&A pairs) to avoid token limits
        recent_messages = messages[-10:] if len(messages) > 10 else messages[:-1]  # Exclude current question
        
        context_parts = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                context_parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Truncate long answers to keep context manageable
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                context_parts.append(f"Assistant: {content}")
        
        context_text = "\n".join(context_parts) if context_parts else "No previous conversation."

        # Add semantic memory (vector retrieval) when available
        semantic_memory = self._retrieve_semantic_memory(
            question=question,
            memory_vectors=memory_vectors or []
        )
        if semantic_memory:
            context_text += "\n\nRelevant memory:\n" + semantic_memory

        # Add summary as a compact long-term memory
        if memory_summary:
            context_text += "\n\nMemory summary:\n" + memory_summary

        return context_text

    def _is_follow_up(
        self,
        question: str,
        messages: List[BaseMessage],
        memory_summary: Optional[str],
        memory_topics: Optional[List[str]]
    ) -> bool:
        """Decide if the current question depends on previous context."""
        question_lower = (question or "").lower()
        followup_cues = ["that", "those", "it", "them", "same", "previous", "earlier", "above", "compare", "what about"]
        if any(cue in question_lower for cue in followup_cues):
            return True

        if memory_topics:
            for topic in memory_topics:
                if topic and topic.lower() in question_lower:
                    return True

        # LLM check for ambiguous cases
        prompt = f"""
        Is the user's current question a follow-up that depends on previous context?
        Reply ONLY YES or NO.

        Previous conversation (latest first):
        {self._format_recent_messages(messages)}

        Memory summary:
        {memory_summary or "None"}

        Current question:
        "{question}"
        """
        try:
            response = self.llm.invoke(prompt).content.strip().upper()
            return "YES" in response
        except Exception as e:
            logger.error(f"Follow-up detection failed: {e}")
            return False

    def _format_recent_messages(self, messages: List[BaseMessage]) -> str:
        """Format recent messages for follow-up detection prompt."""
        recent_messages = messages[-6:] if len(messages) > 6 else messages[:-1]
        parts = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                parts.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                parts.append(f"Assistant: {content}")
        return "\n".join(parts) if parts else "No previous conversation."

    def _clean_text(self, text: str) -> str:
        """Normalize formatting glitches from LLM output."""
        if not text:
            return text
        cleaned = text
        # Remove excessive spaces and newlines
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # Join sequences like "S a l e s" or "N o v" back into words
        def _join_spelled_words(match: re.Match) -> str:
            return match.group(0).replace(" ", "")

        cleaned = re.sub(r"\b(?:[A-Za-z]\s){3,}[A-Za-z]\b", _join_spelled_words, cleaned)

        # Fix broken currency/units like "53.5 M" -> "53.5M"
        cleaned = re.sub(r"(\d)\s+(M|K|B)\b", r"\1\2", cleaned)

        # Fix spacing before punctuation
        cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
        return cleaned.strip()

    def _embed_text(self, text: str) -> List[float]:
        """Create embeddings for semantic memory."""
        return self.memory_embeddings.embed_query(text)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _store_memory_vector(
        self,
        memory_vectors: List[Dict[str, Any]],
        question: str,
        answer: str,
        topics: List[str]
    ) -> List[Dict[str, Any]]:
        """Store a semantic memory vector for retrieval."""
        try:
            text = f"Q: {question}\nA: {answer}"
            embedding = self._embed_text(text)
            memory_vectors.append({
                "text": text[:2000],
                "embedding": embedding,
                "topics": topics[:5]
            })
            # Keep memory bounded
            return memory_vectors[-50:]
        except Exception as e:
            logger.error(f"Memory vector store failed: {e}")
            return memory_vectors

    def _retrieve_semantic_memory(
        self,
        question: str,
        memory_vectors: List[Dict[str, Any]]
    ) -> str:
        """Retrieve top-k semantic memories based on similarity."""
        if not memory_vectors:
            return ""
        try:
            q_emb = self._embed_text(question)
            scored = []
            for m in memory_vectors:
                sim = self._cosine_similarity(q_emb, m.get("embedding", []))
                scored.append((sim, m.get("text", "")))
            scored.sort(key=lambda x: x[0], reverse=True)
            top = [text for sim, text in scored[:3] if sim > 0.75 and text]
            return "\n".join(top)
        except Exception as e:
            logger.error(f"Semantic memory retrieval failed: {e}")
            return ""
    
    def ask(self, question: str, thread_id: str = "default", use_external_prices: bool = True):
        config = {"configurable": {"thread_id": thread_id}}
        try:
            # The checkpointer automatically retrieves previous messages for this thread_id
            # and adds them to the state, so we just need to add the new question
            final = self.app.invoke(
                {"messages": [HumanMessage(content=question)], "use_external_prices": use_external_prices},
                config=config
            )
            
            # For price comparison, sql_query will be None (expected)
            # Get chart_data from price_comparison_result if available
            chart_data = final.get("chart_json")
            if not chart_data and final.get("price_comparison_result"):
                chart_data = final.get("price_comparison_result", {}).get("chart_data")
            
            return {
                "answer": final.get("final_answer", "No answer generated."),
                "chart_data": chart_data,
                "sql_query": final.get("sql_query"),  # Will be None for price comparison (expected)
                "raw_data": final.get("data_result")
            }
        except Exception as e:
            logger.error(f"Critical Agent Error: {e}")
            return {
                "answer": f"System Error: {str(e)}",
                "sql_query": None,
                "raw_data": None,
                "chart_data": None
            }