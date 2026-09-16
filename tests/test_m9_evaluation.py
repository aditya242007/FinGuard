import os
import pytest
from src.m9_agent.agent import investigate

EVALUATION_QUESTIONS = [
    "Investigate CLU00604.",
    "Why is CLU00604 an investigation candidate?",
    "Show me the evidence behind CLU00604.",
    "Investigate USR58627.",
    "Show USR58627's chargeback history.",
    "Investigate merchant MCH6502.",
    "Investigate transaction TXN00011869.",
    "Show the strongest investigation candidates.",
    "What risk signals are present for USR40970?",
    "What data-quality limitations affect transaction TXN00011869?"
]

FORBIDDEN_TERMS = [
    "fraud probability", "confirmed fraud", "is fraudulent", "fraudster"
]

@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY")
    and not os.environ.get("GEMINI_API_KEY")
    and not os.environ.get("FIN_GUARD_LLM_API_KEY"),
    reason="API Key required for LLM evaluation (set OPENAI_API_KEY, GEMINI_API_KEY, or FIN_GUARD_LLM_API_KEY)."
)
@pytest.mark.parametrize("question", EVALUATION_QUESTIONS)
def test_evaluate_question(question):
    result = investigate(question)
    assert "error" not in result, f"LLM returned error: {result.get('error')}"
    
    content = result["response"].lower()
    
    # 1. Terminology safety: No forbidden terms
    for term in FORBIDDEN_TERMS:
        assert term not in content, f"Forbidden term '{term}' found in response!"
        
    # 2. At least mentions 'investigation candidate', 'risk', or 'evidence'
    assert any(w in content for w in ["investigation candidate", "risk", "evidence", "insufficient"]), \
        "Response lacks required cautious terminology or evidence markers."
        
    # 3. If it found an entity, ensure it structured it nicely
    if "CLU00604" in question.upper():
        assert "clu00604" in content
    if "USR58627" in question.upper():
        assert "usr58627" in content
