from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from src.m9_agent.agent import investigate

app = FastAPI(title="FINguard AI Agent API")

# Allow dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    error: str | None = None

@app.post("/api/investigate", response_model=QueryResponse)
def handle_investigate(req: QueryRequest):
    result = investigate(req.query)
    
    if "error" in result:
        return QueryResponse(response="", error=result["error"])
        
    return QueryResponse(response=result["response"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
