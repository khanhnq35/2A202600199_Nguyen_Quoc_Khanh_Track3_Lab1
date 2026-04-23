import json
import time
import urllib.request
from typing import Literal

from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM
from .utils import normalize_answer

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2"

def call_llm(messages: list[dict], format: Literal["json", ""] = "") -> tuple[str, int, int]:
    """Gọi Ollama API, trả về (response_text, token_count, latency_ms)"""
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0 # Để output nhất quán
        }
    }
    if format == "json":
        payload["format"] = "json"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"})
    
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"Error calling Ollama API: {e}")
        return "", 0, int((time.perf_counter() - start_time) * 1000)
        
    end_time = time.perf_counter()
    
    latency_ms = int((end_time - start_time) * 1000)
    response_text = result.get("message", {}).get("content", "")
    
    prompt_tokens = result.get("prompt_eval_count", 0)
    completion_tokens = result.get("eval_count", 0)
    token_count = prompt_tokens + completion_tokens
    
    return response_text, token_count, latency_ms

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str]) -> tuple[str, int, int]:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {example.question}"
    
    if agent_type == "reflexion" and reflection_memory:
        mem_str = "\n".join([f"- {m}" for m in reflection_memory])
        user_prompt += f"\n\nReflection Memory from past mistakes:\n{mem_str}"
        
    messages = [
        {"role": "system", "content": ACTOR_SYSTEM},
        {"role": "user", "content": user_prompt}
    ]
    
    answer, tokens, latency = call_llm(messages)
    return answer.strip(), tokens, latency

def evaluator(example: QAExample, answer: str) -> tuple[JudgeResult, int, int]:
    # Phase 6 Bonus: Implement structured_evaluator (Exact Match)
    start_time = time.perf_counter()
    
    norm_ans = normalize_answer(answer)
    norm_gold = normalize_answer(example.gold_answer)
    
    # Kiểm tra nếu khớp chính xác hoặc đáp án chuẩn nằm trong câu trả lời
    if norm_gold == norm_ans or norm_gold in norm_ans.split():
        score = 1
        reason = "Exact match after normalization."
    else:
        score = 0
        reason = f"Answer '{answer}' does not match gold answer '{example.gold_answer}'."
        
    judge = JudgeResult(score=score, reason=reason, missing_evidence=[], spurious_claims=[])
    
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Trả về 0 token vì không gọi LLM
    return judge, 0, latency_ms

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> tuple[ReflectionEntry, int, int]:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    
    user_prompt = (
        f"Context:\n{context_str}\n\n"
        f"Question: {example.question}\n"
        f"Evaluator Feedback: {judge.reason}\n"
        f"Missing Evidence: {judge.missing_evidence}\n"
        f"Spurious Claims: {judge.spurious_claims}"
    )
    
    messages = [
        {"role": "system", "content": REFLECTOR_SYSTEM},
        {"role": "user", "content": user_prompt}
    ]
    
    response_text, tokens, latency = call_llm(messages, format="json")
    
    try:
        result_dict = json.loads(response_text)
        # Fix: Nếu LLM trả về list cho strategy (lỗi phổ biến ở llama3.2), nối lại thành string
        if isinstance(result_dict.get("next_strategy"), list):
            result_dict["next_strategy"] = ". ".join(result_dict["next_strategy"])
        if isinstance(result_dict.get("failure_reason"), list):
            result_dict["failure_reason"] = " ".join(result_dict["failure_reason"])
            
        result_dict["attempt_id"] = attempt_id
        entry = ReflectionEntry(**result_dict)
    except Exception as e:
        entry = ReflectionEntry(
            attempt_id=attempt_id, 
            failure_reason=f"Failed to parse JSON: {e}", 
            lesson="Always ensure output is valid JSON.", 
            next_strategy="Analyze the question carefully and find the specific entity."
        )
        
    return entry, tokens, latency
