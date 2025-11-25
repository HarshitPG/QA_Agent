import os
import json
import logging
from datetime import datetime
from typing import Dict, List

from .config import LLM_PROVIDER, OLLAMA_MODEL

logger = logging.getLogger(__name__)


def log_generation_request(
    prompt: str,
    num_chunks: int,
    query: str,
    session_id: str = "unknown"
) -> None:
    
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "llm_generations.jsonl")

        prompt_preview = prompt[:2000] + "..." if len(prompt) > 2000 else prompt
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "generation_request",
            "session_id": session_id,
            "provider": LLM_PROVIDER,
            "model": OLLAMA_MODEL,
            "num_chunks_used": num_chunks,
            "query": query[:200],
            "prompt_preview": prompt_preview
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log generation request: {e}")


def log_generation_response(
    test_cases: List[Dict],
    dropped_count: int,
    session_id: str = "unknown"
) -> None:
    
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "llm_generations.jsonl")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "generation_response",
            "session_id": session_id,
            "provider": LLM_PROVIDER,
            "model": OLLAMA_MODEL,
            "num_test_cases": len(test_cases),
            "num_dropped": dropped_count,
            "test_ids": [tc.get("test_id", "unknown") for tc in test_cases]
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log generation response: {e}")
