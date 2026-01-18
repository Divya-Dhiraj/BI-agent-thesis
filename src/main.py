from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.agents.sql_agent import BusinessAnalystAgent
from loguru import logger

app = FastAPI()

# Initialize Agent once
agent = BusinessAnalystAgent()

class QueryRequest(BaseModel):
    prompt: str
    session_id: str = "default"

# --- THE CRITICAL SCHEMA ---
class QueryResponse(BaseModel):
    answer: str
    # These fields MUST be here for the Dashboard to see them
    sql_query: Optional[str] = None
    raw_data: Optional[str] = None
    chart_data: Optional[Dict[str, Any]] = None
    considered_products: Optional[List[str]] = None
    session_id: str

@app.get("/")
async def root():
    return {"status": "Agent Ready", "model": "v7.2-Hybrid"}

@app.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    logger.info(f"Received Query: {request.prompt}")
    try:
        # Call the agent
        result = agent.ask(request.prompt, thread_id=request.session_id)
        
        # DEBUG LOG: Check if SQL exists before sending
        sql_status = "PRESENT" if result.get("sql_query") else "MISSING"
        logger.info(f"Response Prepared | SQL: {sql_status}")
        
        return QueryResponse(
            answer=result.get("answer", "Processing error."),
            sql_query=result.get("sql_query"),
            raw_data=result.get("raw_data"),
            chart_data=result.get("chart_data"),
            considered_products=result.get("considered_products"),
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"API Route Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))