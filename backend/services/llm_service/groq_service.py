import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

from .config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_BASE_URL,
    GENERATION_TEMPERATURE,
    GROQ_RATE_LIMITS,
    STOP_TOKEN
)

logger = logging.getLogger(__name__)


class GroqServiceError(Exception):
    
    pass


def generate_test_cases_with_groq(
    prompt: str,
    num_predict: int = 4000,
    temperature: float = None,
    stream: bool = False
) -> Dict[str, Any]:
    
    if not GROQ_API_KEY:
        raise GroqServiceError("GROQ_API_KEY not configured in environment")
    
    if temperature is None:
        temperature = GENERATION_TEMPERATURE
    rate_limits = GROQ_RATE_LIMITS.get(GROQ_MODEL, {})
    logger.info(f"Using Groq model: {GROQ_MODEL} (TPM: {rate_limits.get('tpm', 'N/A')}, RPM: {rate_limits.get('rpm', 'N/A')})")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    messages = [
        {
            "role": "system",
            "content": "You are an expert QA engineer who generates comprehensive, accurate test cases from documentation. Generate complete, detailed test cases in valid JSON format. Follow the exact schema provided."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": num_predict,
        "top_p": 0.9,
        "stream": stream
    }
    
    try:
        logger.info(f"Calling Groq API: {GROQ_MODEL}, max_tokens={num_predict}, temp={temperature}")
        
        response = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"Groq API raw response keys: {list(result.keys())}")
        
        if "choices" in result and len(result["choices"]) > 0:
            generated_text = result["choices"][0]["message"]["content"]
            
            logger.info(f"Extracted text length: {len(generated_text)} chars")
            logger.info(f"First 200 chars: {generated_text[:200]}")
            
            usage = result.get("usage", {})
            logger.info(f"Groq API success: {usage.get('prompt_tokens', 0)} prompt tokens, "
                       f"{usage.get('completion_tokens', 0)} completion tokens, "
                       f"{usage.get('total_tokens', 0)} total tokens")
            
            return {
                "response": generated_text,
                "usage": usage,
                "model": GROQ_MODEL
            }
        else:
            raise GroqServiceError("No response generated from Groq API")
    
    except requests.exceptions.Timeout:
        raise GroqServiceError("Groq API request timed out after 60 seconds")
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = f"{error_msg} - {error_detail}"
            except:
                error_msg = f"{error_msg} - {e.response.text}"
        raise GroqServiceError(f"Groq API request failed: {error_msg}")
    except Exception as e:
        raise GroqServiceError(f"Unexpected error calling Groq API: {str(e)}")


def extract_json_from_groq_response(response_text: str) -> Optional[Dict]:
    
    if not response_text:
        return None
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    import re
    json_block = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except json.JSONDecodeError:
            pass
    generic_block = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
    if generic_block:
        try:
            return json.loads(generic_block.group(1))
        except json.JSONDecodeError:
            pass
    array_match = re.search(r'\[.*\]', response_text, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass
    
    object_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if object_match:
        try:
            return json.loads(object_match.group(0))
        except json.JSONDecodeError:
            pass
    
    logger.warning("Could not extract valid JSON from Groq response")
    return None


def validate_groq_connection() -> bool:
    
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY not configured")
        return False
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "user", "content": "Test"}
            ],
            "max_tokens": 10
        }
        response = requests.post(
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Groq connection validated: {GROQ_MODEL}")
        return True
        
    except Exception as e:
        logger.error(f"Groq connection validation failed: {e}")
        return False
