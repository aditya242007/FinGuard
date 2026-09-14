import os
import json
from typing import Dict, Any, List
import openai

from src.m9_agent import data_tools

def get_llm_client():
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing API key. Set OPENAI_API_KEY or GEMINI_API_KEY.")
        
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return openai.OpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ), "gemini-2.5-flash"
    else:
        return openai.OpenAI(api_key=api_key), "gpt-4o-mini"

SYSTEM_PROMPT = """You are FINguard AI, an Explainable AI Investigation Assistant.
Your job is to investigate entities using the deterministic data tools provided, which fetch real evidence from M3-M7 analytical layers.

CRITICAL RULES:
1. EVIDENCE FIRST: Never invent evidence. You must reason ONLY from retrieved evidence.
2. If a requested fact cannot be retrieved, say exactly: "Insufficient evidence in the available FinGuard dataset."
3. FRAUD CLAIM SAFETY: There are NO ground-truth fraud labels. NEVER use terms like "confirmed fraud", "this transaction is fraudulent", "fraud probability", or "fraudster".
4. SAFE TERMINOLOGY: Use ONLY these terms: "investigation candidate", "elevated-risk activity", "observed risk signal", "suspicious behavioral pattern", "requires investigation", "risk is elevated based on observed signals".
5. PRESERVE SEMANTICS: For clusters, the "chargeback rate" means distinct transactions with >=1 chargeback / total transactions. Do not redefine it.

RESPONSE FORMAT:
Use the exact structure below for entity investigations.

### Investigation Summary
Entity: [ID]
Risk Level: [Level]
Risk Score: [Score]

### Evidence
- [Signal or Fact] (Source: [source_dataset], Field: [field])

### Related Activity
Transactions: [Count]
Users: [Count]
Merchants: [Count]
Chargebacks: [Count]
Clusters: [Cluster IDs]

### Why This Matters
Explain the observed behavioral pattern based on the evidence.

### Data Limitations
Mention relevant data quality issues (e.g. missing KYC, missing UTR) if retrieved from tools.

### Analyst Conclusion
[Provide a cautious conclusion. e.g. "These observed signals make this entity an investigation candidate. They do not establish confirmed fraud."]
"""

def _make_tool(name: str, desc: str, param: str = None):
    schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
    if param:
        schema["function"]["parameters"]["properties"][param] = {"type": "string"}
        schema["function"]["parameters"]["required"] = [param]
    return schema

TOOLS_SCHEMA = [
    _make_tool("get_cluster", "Retrieve cluster details", "cluster_id"),
    _make_tool("get_cluster_members", "Retrieve cluster members", "cluster_id"),
    _make_tool("get_user", "Retrieve user profile details", "user_id"),
    _make_tool("get_user_transactions", "Retrieve user transactions", "user_id"),
    _make_tool("get_user_chargebacks", "Retrieve user chargebacks", "user_id"),
    _make_tool("get_user_merchants", "Retrieve user connected merchants", "user_id"),
    _make_tool("get_user_clusters", "Retrieve user connected clusters", "user_id"),
    _make_tool("get_merchant", "Retrieve merchant profile details", "merchant_id"),
    _make_tool("get_merchant_transactions", "Retrieve merchant transactions", "merchant_id"),
    _make_tool("get_merchant_chargebacks", "Retrieve merchant chargebacks", "merchant_id"),
    _make_tool("get_merchant_users", "Retrieve merchant connected users", "merchant_id"),
    _make_tool("get_merchant_clusters", "Retrieve merchant connected clusters", "merchant_id"),
    _make_tool("get_transaction", "Retrieve transaction details", "txn_id"),
    _make_tool("get_transaction_chargebacks", "Retrieve transaction chargeback history", "txn_id"),
    _make_tool("get_transaction_risk", "Retrieve transaction risk scores", "txn_id"),
    _make_tool("get_user_risk", "Retrieve user risk scores", "user_id"),
    _make_tool("get_merchant_risk", "Retrieve merchant risk scores", "merchant_id"),
    _make_tool("get_cluster_risk", "Retrieve cluster risk scores", "cluster_id"),
    _make_tool("get_top_investigation_candidates", "Get top risky clusters to investigate"),
]

# We need custom tools for get_risk_signals and get_data_quality_context which take two parameters
TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "get_risk_signals",
        "description": "Retrieve behavioral risk signals and explanation",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "enum": ["cluster", "user", "merchant", "transaction"]},
                "entity_id": {"type": "string"}
            },
            "required": ["entity_type", "entity_id"]
        }
    }
})

TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "get_data_quality_context",
        "description": "Retrieve data quality limitations",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "enum": ["transaction"]},
                "entity_id": {"type": "string"}
            },
            "required": ["entity_type", "entity_id"]
        }
    }
})

TOOL_FUNCTIONS = {
    "get_cluster": data_tools.get_cluster,
    "get_cluster_members": data_tools.get_cluster_members,
    "get_user": data_tools.get_user,
    "get_user_transactions": data_tools.get_user_transactions,
    "get_user_chargebacks": data_tools.get_user_chargebacks,
    "get_user_merchants": data_tools.get_user_merchants,
    "get_user_clusters": data_tools.get_user_clusters,
    "get_merchant": data_tools.get_merchant,
    "get_merchant_transactions": data_tools.get_merchant_transactions,
    "get_merchant_chargebacks": data_tools.get_merchant_chargebacks,
    "get_merchant_users": data_tools.get_merchant_users,
    "get_merchant_clusters": data_tools.get_merchant_clusters,
    "get_transaction": data_tools.get_transaction,
    "get_transaction_chargebacks": data_tools.get_transaction_chargebacks,
    "get_transaction_risk": data_tools.get_transaction_risk,
    "get_user_risk": data_tools.get_user_risk,
    "get_merchant_risk": data_tools.get_merchant_risk,
    "get_cluster_risk": data_tools.get_cluster_risk,
    "get_top_investigation_candidates": data_tools.get_top_investigation_candidates,
    "get_risk_signals": data_tools.get_risk_signals,
    "get_data_quality_context": data_tools.get_data_quality_context,
}

def investigate(query: str) -> Dict[str, Any]:
    try:
        client, model = get_llm_client()
    except ValueError as e:
        return {"error": str(e)}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query}
    ]

    for _ in range(8):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        if not message.tool_calls:
            return {"response": message.content}
            
        messages.append(message)
        
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}
                
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
