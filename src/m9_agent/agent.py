import os
import json
from typing import Dict, Any, List

# Try importing openai; fallback if not available (though we installed it)
import openai

from src.m9_agent import data_tools

# We provide a generic OpenAI-compatible abstraction that can be used with OpenAI, Gemini (via OpenAI compat), etc.
def get_llm_client():
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing API key. Set OPENAI_API_KEY or GEMINI_API_KEY.")
        
    # If GEMINI_API_KEY is present without OPENAI_API_KEY, point to Google's OpenAI compat endpoint
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return openai.OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ), "gemini-2.5-flash" # or another model name available
    else:
        return openai.OpenAI(api_key=api_key), "gpt-4o-mini"

SYSTEM_PROMPT = """You are FINguard AI, an expert FinTech risk investigation assistant.
Your job is to investigate entities using the deterministic data tools provided.

CRITICAL RULES:
1. NO FRAUD CLAIMS: Never say "fraud", "fraudulent", or "fraud probability". 
   Instead, use terms like "elevated-risk transaction", "investigation candidate", "suspicious cluster", "risk signal", "observed behavioral pattern".
2. EVIDENCE FIRST: Never invent evidence. Every claim must be supported by data returned from your tools.
3. If data is missing or tools return errors, state: "Insufficient evidence in the available dataset."

RESPONSE FORMAT:
Use Markdown. Structure your response as follows (omit sections if inapplicable):

### Investigation Summary
Entity: [ID]
Risk level: [Level]
Risk score: [Score]

### Evidence
- [Signal 1]
- [Signal 2]

### Related Activity
Transactions: [Count]
Merchants: [Count]
Chargebacks: [Count]
Cluster: [Cluster ID]

### Why This Matters
Explain the observable behavioral pattern based on the risk signals.

### Data Limitations
Mention relevant data quality issues (e.g., missing UTR, unmatched KYC) if present in the tool response.

### Analyst Conclusion
"These signals make this entity an investigation candidate." (Use cautious language. Never conclude confirmed fraud).
"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_cluster",
            "description": "Retrieve an investigation candidate cluster by ID.",
            "parameters": {
                "type": "object",
                "properties": {"cluster_id": {"type": "string"}},
                "required": ["cluster_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_cluster_members",
            "description": "Retrieve users and merchants associated with a cluster.",
            "parameters": {
                "type": "object",
                "properties": {"cluster_id": {"type": "string"}},
                "required": ["cluster_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user",
            "description": "Retrieve a user profile and their risk score.",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant",
            "description": "Retrieve a merchant profile and their risk score.",
            "parameters": {
                "type": "object",
                "properties": {"merchant_id": {"type": "string"}},
                "required": ["merchant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transaction",
            "description": "Retrieve transaction details and risk signals.",
            "parameters": {
                "type": "object",
                "properties": {"txn_id": {"type": "string"}},
                "required": ["txn_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_transactions",
            "description": "Retrieve top recent/risky transactions for a user.",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_transactions",
            "description": "Retrieve top recent/risky transactions for a merchant.",
            "parameters": {
                "type": "object",
                "properties": {"merchant_id": {"type": "string"}},
                "required": ["merchant_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_chargebacks",
            "description": "Retrieve chargebacks filed by a specific user.",
            "parameters": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_investigation_candidates",
            "description": "Retrieve top N highest risk entities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "enum": ["cluster", "user", "merchant"]}
                },
                "required": ["entity_type"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "get_cluster": data_tools.get_cluster,
    "get_cluster_members": data_tools.get_cluster_members,
    "get_user": data_tools.get_user,
    "get_merchant": data_tools.get_merchant,
    "get_transaction": data_tools.get_transaction,
    "get_user_transactions": data_tools.get_user_transactions,
    "get_merchant_transactions": data_tools.get_merchant_transactions,
    "get_user_chargebacks": data_tools.get_user_chargebacks,
    "get_top_investigation_candidates": data_tools.get_top_investigation_candidates,
}

def investigate(query: str) -> Dict[str, Any]:
    """Main entrypoint for the AI investigation agent."""
    try:
        client, model = get_llm_client()
    except ValueError as e:
        return {"error": str(e)}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query}
    ]

    # Max 5 tool call iterations to prevent infinite loops
    for _ in range(5):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        if not message.tool_calls:
            # Done, LLM provided final answer
            return {"response": message.content}
            
        messages.append(message) # Add LLM's tool call message
        
        # Execute tools
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            if func_name in TOOL_FUNCTIONS:
                try:
                    result = TOOL_FUNCTIONS[func_name](**args)
                except Exception as e:
                    result = {"error": str(e)}
            else:
                result = {"error": f"Tool {func_name} not found"}
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": json.dumps(result)
            })

    return {"error": "Exceeded maximum tool iterations."}
