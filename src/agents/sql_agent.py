import json
import re
from typing import TypedDict, List, Annotated, Optional
import operator

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import text
from src.database import DatabaseManager
from src.config import Config
from src.knowledge import DOMAIN_KNOWLEDGE  # <--- IMPORT THE BRAIN
from loguru import logger

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add] 
    question: str
    target_asins: List[str]
    search_term: str
    product_filter_mode: str  # "brand" | "item" | "both"
    sql_query: Optional[str]
    sql_error: Optional[str]
    data_result: Optional[str]
    attempt_count: int
    final_answer: Optional[str]
    chart_json: Optional[dict]

class BusinessAnalystAgent:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.llm = ChatOpenAI(model=Config.OPENAI_MODEL, temperature=0, api_key=Config.OPENAI_API_KEY)
        self.checkpointer = MemorySaver()

        # Define Graph
        workflow = StateGraph(AgentState)
        workflow.add_node("lookup", self.node_lookup)
        workflow.add_node("architect", self.node_architect) # <--- THE SMART LOGIC
        workflow.add_node("executor", self.node_executor)
        workflow.add_node("reporter", self.node_reporter)
        
        workflow.set_entry_point("lookup")
        workflow.add_edge("lookup", "architect")
        workflow.add_edge("architect", "executor")
        
        workflow.add_conditional_edges(
            "executor",
            self.check_status,
            {"retry": "architect", "success": "reporter", "fail": "reporter"}
        )
        workflow.add_edge("reporter", END)
        self.app = workflow.compile(checkpointer=self.checkpointer)
        logger.success("Agent v28.0 (Brand vs product filter) Compiled.")

    @staticmethod
    def _parse_lookup_json(raw: str) -> tuple[str, str]:
        """Returns (search_term, filter_mode) where filter_mode is brand|item|both."""
        text_clean = raw.strip()
        # Strip markdown code fence if present
        if "```" in text_clean:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text_clean)
            if m:
                text_clean = m.group(1).strip()
        try:
            data = json.loads(text_clean)
            term = (data.get("search_term") or "").strip().replace('"', "")
            mode = (data.get("filter_mode") or "item").strip().lower()
            if mode not in ("brand", "item", "both"):
                mode = "both"
            if not term:
                return "ALL_MARKET", "item"
            return term, mode
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
        # Fallback: plain ALL_MARKET or single line term → default both (safe for Samsung-style names)
        line = text_clean.split("\n")[0].strip().strip('"')
        if not line or line.upper() == "ALL_MARKET":
            return "ALL_MARKET", "item"
        return line, "both"

    def node_lookup(self, state: AgentState):
        """Phase 1: Extract scope + whether to filter by brand_name, item_name, or both."""
        last_msg = state["messages"][-1]
        question = last_msg.content if isinstance(last_msg, HumanMessage) else state.get("question")
        
        logger.info(f"Step 1: Identifying products for: '{question}'")

        prompt = f"""
Analyze this question: "{question}"

Output ONLY valid JSON (no markdown):
{{"search_term": "<phrase or ALL_MARKET>", "filter_mode": "brand"|"item"|"both"}}

Rules:
- search_term = ALL_MARKET for whole-business questions (overall sales, all brands, market trends).
- filter_mode "brand": user means the company/manufacturer/brand (e.g. "Apple products", "Nike", "Sony returns", "Microsoft").
- filter_mode "item": user means a product line/model usually in the title (e.g. "iPhone", "Pixel", "AirPods", "Galaxy S24").
- filter_mode "both": brand name often doubles as product wording (Samsung, LG, Dell, Google, Xiaomi) OR unclear — match brand_name OR item_name.

search_term: shortest useful phrase (e.g. Apple, iPhone, Samsung).
"""
        try:
            raw = self.llm.invoke(prompt).content
            search_term, product_filter_mode = self._parse_lookup_json(raw)
        except Exception as e:
            logger.error(f"LLM Lookup Error: {e}")
            search_term, product_filter_mode = "ALL_MARKET", "item"

        logger.info(f"Lookup: term={search_term!r} filter_mode={product_filter_mode}")
        target_asins: List[str] = []

        return {
            "target_asins": target_asins,
            "search_term": search_term,
            "product_filter_mode": product_filter_mode,
            "question": question,
            "attempt_count": 0,
        }

    def node_architect(self, state: AgentState):
        """Phase 2: The Reasoning Engine."""
        logger.info("Step 2: Architecting SQL")
        search_term = (state.get("search_term") or "").strip()
        mode = (state.get("product_filter_mode") or "item").strip().lower()
        if mode not in ("brand", "item", "both"):
            mode = "item"

        filter_logic = ""
        if search_term and search_term.upper() != "ALL_MARKET":
            esc = search_term.replace("'", "''")
            pat = f"%{esc}%"
            if mode == "brand":
                filter_logic = (
                    f"User asked about a company/brand. Filter using brand_name ILIKE '{pat}' "
                    f"(use table alias: s.brand_name for shipped_raw, c.brand_name for concession_raw). "
                    f"Do not rely on item_name alone for this filter. "
                    f"No ASIN IN lists unless user asked by ASIN."
                )
            elif mode == "item":
                filter_logic = (
                    f"User asked about a product line/model. Filter using item_name ILIKE '{pat}' "
                    f"(s.item_name / c.item_name with correct aliases). "
                    f"No ASIN IN lists unless user asked by ASIN."
                )
            else:  # both
                filter_logic = (
                    f"Brand and title may both contain this phrase. Filter with "
                    f"(brand_name ILIKE '{pat}' OR item_name ILIKE '{pat}') on each relevant table "
                    f"(e.g. (s.brand_name ILIKE '{pat}' OR s.item_name ILIKE '{pat}')). "
                    f"No ASIN IN lists unless user asked by ASIN."
                )
        
        # --- THE PROMPT THAT MAKES IT SMART ---
        system_prompt = f"""
        You are an Expert Amazon Data Analyst. 
        You have deep knowledge of the database schema and business definitions.
        
        ### YOUR KNOWLEDGE BASE (STRICTLY ADHERE TO THIS)
        {DOMAIN_KNOWLEDGE}

        ### AVAILABLE TABLES
        1. **shipped_raw** (Sales): ncrc_su_pk, asin, item_name, year, month, shipped_units, shipped_cogs, product_gms, brand_name, manufacturer_name...
        2. **concession_raw** (Returns): ncrc_cu_pk, asin, year, month, mapped_year, mapped_month, conceded_units, ncrc, defect_category, root_cause, brand_name...
        
        ### USER QUESTION
        "{state['question']}"
        
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
            return {"sql_error": str(e), "data_result": None}

    def check_status(self, state: AgentState):
        """Phase 4: Self-Correction."""
        if state.get("sql_error") and state.get("attempt_count", 0) < 3:
            logger.warning(f"Retrying due to error: {state['sql_error']}")
            return "retry"
        return "success" if state.get("data_result") else "fail"

    def node_reporter(self, state: AgentState):
        """Phase 5: Analyst Summary."""
        logger.info("Step 4: Reporting")
        # safely handle NoneType for data_result
        data_preview = (state.get("data_result") or "No data found.")[:2500]
        
        prompt = f"""
        You are a BI Manager presenting to executives.
        Question: {state['question']}
        Data Evidence: 
        {data_preview}
        
        Task:
        1. Answer the question directly using the data.
        2. Explain *why* (using the logic like "High NCRC driven by defects").
        3. Create a chart configuration.
        
        Output strictly JSON: {{ "narrative": "...", "chart": {{ "type": "bar", "data": {{ "labels": [], "values": [] }}, "title": "..." }} }}
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

        return {
            "final_answer": narrative,
            "chart_json": chart,
            "messages": [AIMessage(content=str(narrative))]
        }

    def ask(self, question: str, thread_id: str = "default"):
        config = {"configurable": {"thread_id": thread_id}}
        try:
            final = self.app.invoke({"messages": [HumanMessage(content=question)]}, config=config)
            return {
                "answer": final.get("final_answer", "No answer generated."),
                "chart_data": final.get("chart_json"),
                "sql_query": final.get("sql_query"),
                "raw_data": final.get("data_result")
            }
        except Exception as e:
            logger.error(f"Critical Agent Error: {e}")
            return {
                "answer": f"System Error: {str(e)}",
                "sql_query": None,
                "raw_data": None
            }