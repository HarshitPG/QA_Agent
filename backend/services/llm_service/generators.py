import requests
import logging
import json
from typing import Dict, List

from .config import (
    LLM_PROVIDER,
    OLLAMA_URL,
    OLLAMA_MODEL,
    GROQ_API_KEY,
    STOP_TOKEN
)
from .json_utils import aggressive_json_extraction
from .prompt_utils import estimate_tokens

logger = logging.getLogger(__name__)


def generate_test_cases_with_ollama(
    full_prompt: str,
    num_predict: int,
    temperature: float = 0.3,
    top_p: float = 0.9,
    top_k: int = 40,
    retries: int = 2
) -> str:
    logger.info("="*70)
    logger.info(f"LLM GENERATION REQUEST (Provider: {LLM_PROVIDER.upper()})")
    logger.info("="*70)
    
    if not full_prompt or not full_prompt.strip():
        logger.error("Empty prompt provided to LLM generation")
        return "[]"
    
    if LLM_PROVIDER == "groq":
        return _generate_with_groq(full_prompt, num_predict, temperature, retries)
    else:
        return _generate_with_ollama(full_prompt, num_predict, temperature, top_p, top_k, retries)


def _generate_with_groq(
    full_prompt: str,
    num_predict: int,
    temperature: float,
    retries: int
) -> str:
    from .groq_service import generate_test_cases_with_groq, extract_json_from_groq_response, GroqServiceError

    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Groq attempt {attempt}/{retries}: max_tokens={num_predict}, temp={temperature}")

            result = generate_test_cases_with_groq(
                prompt=full_prompt,
                num_predict=num_predict,
                temperature=temperature
            )

            response_text = result.get("response", "")
            if response_text:
                logger.info(f"Groq returned {len(response_text)} chars")
                return response_text
            else:
                logger.warning(f"Groq returned empty response on attempt {attempt}")

        except GroqServiceError as e:
            logger.error(f"Groq API error on attempt {attempt}: {e}")
            if attempt == retries:
                logger.error("All Groq attempts failed, returning empty array")
                return "[]"
        except Exception as e:
            logger.error(f"Unexpected error with Groq on attempt {attempt}: {e}")
            if attempt == retries:
                return "[]"

    return "[]"


def _generate_with_ollama(
    full_prompt: str,
    num_predict: int,
    temperature: float,
    top_p: float,
    top_k: int,
    retries: int
) -> str:

    if num_predict < 100:
        logger.warning(f"num_predict too low ({num_predict}), setting to 200")
        num_predict = 200
    elif num_predict > 2000:
        logger.warning(f"num_predict too high ({num_predict}), capping at 2000")
        num_predict = 2000

    logger.info(f"Request Configuration:")
    logger.info(f"  - Ollama URL: {OLLAMA_URL}")
    logger.info(f"  - Model: {OLLAMA_MODEL}")
    logger.info(f"  - Prompt length: {len(full_prompt)} chars")
    logger.info(f"  - Prompt preview (first 200 chars): {full_prompt[:200]}...")
    logger.info(f"  - Prompt preview (last 200 chars): ...{full_prompt[-200:]}")
    logger.info(f"  - num_predict: {num_predict}")
    logger.info(f"  - temperature: {temperature}")
    logger.info(f"  - top_p: {top_p}")
    logger.info(f"  - top_k: {top_k}")
    logger.info(f"  - retries: {retries}")
    logger.info(f"  - stop tokens: {[STOP_TOKEN, '---END---', '</test_cases>']}")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "num_predict": num_predict,
            "stop": [STOP_TOKEN, "---END---", "</test_cases>", "```", "\n\n\n"],
            "num_ctx": 8192
        },
        "format": "json"
    }

    attempt = 0
    last_error = None

    while attempt <= retries:
        try:
            estimated_prompt_tokens = estimate_tokens(full_prompt)
            logger.info("-" * 70)
            logger.info(f"Attempt {attempt+1}/{retries+1}:")
            logger.info(f"  - Estimated prompt tokens: {estimated_prompt_tokens}")
            logger.info(f"  - Max response tokens: {num_predict}")
            logger.info(f"  - Total estimated: {estimated_prompt_tokens + num_predict}")
            logger.info(f"  - Timeout: 300 seconds")
            logger.info(f"  - Starting request at: {__import__('datetime').datetime.now().isoformat()}")

            import time
            start_time = time.time()

            base_timeout = 120
            attempt_timeout = 180 if attempt > 0 else base_timeout
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload,
                timeout=attempt_timeout
            )

            elapsed_time = time.time() - start_time
            logger.info(f"  - Request completed in: {elapsed_time:.2f} seconds")
            response.raise_for_status()

            result = response.json()
            raw_text = result.get("response", "")

            logger.info(f"Response received:")
            logger.info(f"  - Status code: {response.status_code}")
            logger.info(f"  - Response length: {len(raw_text)} chars")
            logger.info(f"  - Response preview (first 300 chars): {raw_text[:300]}...")
            logger.info(f"  - Response preview (last 200 chars): ...{raw_text[-200:]}")

            if 'eval_count' in result:
                logger.info(f"Model Stats:")
                logger.info(f"  - Eval count: {result.get('eval_count', 'N/A')}")
                logger.info(f"  - Eval duration: {result.get('eval_duration', 0) / 1e9:.2f}s")
                logger.info(f"  - Prompt eval count: {result.get('prompt_eval_count', 'N/A')}")
                logger.info(f"  - Prompt eval duration: {result.get('prompt_eval_duration', 0) / 1e9:.2f}s")
                logger.info(f"  - Total duration: {result.get('total_duration', 0) / 1e9:.2f}s")

            if not raw_text or len(raw_text.strip()) < 10:
                logger.warning(f"Ollama returned empty/short response (attempt {attempt+1})")
                logger.warning(f"Full result object: {result}")
                attempt += 1
                continue

            logger.info("="*70)
            logger.info("OLLAMA GENERATION SUCCESS")
            logger.info("="*70)
            return raw_text

        except requests.exceptions.Timeout as e:
            last_error = f"Ollama request timed out after {attempt_timeout}s"
            logger.error("="*70)
            logger.error(f"TIMEOUT ERROR (attempt {attempt+1})")
            logger.error(f"  - Error: {last_error}")
            logger.error(f"  - URL: {OLLAMA_URL}/api/generate")
            logger.error(f"  - Model: {OLLAMA_MODEL}")
            logger.error(f"  - Prompt length: {len(full_prompt)} chars")
            logger.error(f"  - num_predict: {num_predict}")
            logger.error(f"  - Exception: {str(e)}")
            logger.error("Possible causes:")
            logger.error("  1. Ollama service is slow/overloaded")
            logger.error("  2. Model is too large for available resources")
            logger.error("  3. Prompt is too long")
            logger.error("  4. System memory/CPU constraints")
            logger.error("="*70)
            if attempt == 0 and num_predict > 600:
                logger.warning(f"Reducing num_predict from {num_predict} to 600 for retry to mitigate timeout")
                payload["options"]["num_predict"] = 600
            attempt += 1

        except requests.exceptions.ConnectionError as e:
            last_error = f"Cannot connect to Ollama at {OLLAMA_URL}"
            logger.error("="*70)
            logger.error(f"CONNECTION ERROR (attempt {attempt+1})")
            logger.error(f"  - {last_error}")
            logger.error(f"  - Exception: {str(e)}")
            logger.error("Check:")
            logger.error("  1. Is Ollama running? (ollama serve)")
            logger.error("  2. Is it listening on the correct port?")
            logger.error("  3. Firewall blocking the connection?")
            logger.error("="*70)
            attempt += 1

        except requests.exceptions.HTTPError as e:
            last_error = f"Ollama HTTP error: {e.response.status_code}"
            logger.error("="*70)
            logger.error(f"HTTP ERROR (attempt {attempt+1})")
            logger.error(f"  - Status: {e.response.status_code}")
            logger.error(f"  - Response: {e.response.text[:500]}")
            logger.error(f"  - Exception: {str(e)}")
            logger.error("="*70)
            attempt += 1

        except Exception as e:
            last_error = f"Ollama generation failed: {str(e)}"
            logger.error("="*70)
            logger.error(f"UNEXPECTED ERROR (attempt {attempt+1})")
            logger.error(f"  - Error: {last_error}")
            logger.error(f"  - Type: {type(e).__name__}")
            logger.error(f"  - Exception: {str(e)}")
            import traceback
            logger.error(f"  - Traceback: {traceback.format_exc()}")
            logger.error("="*70)
            attempt += 1

    logger.error("="*70)
    logger.error("OLLAMA GENERATION FAILED - ALL RETRIES EXHAUSTED")
    logger.error("="*70)
    logger.error(f"Total attempts: {retries+1}")
    logger.error(f"Final error: {last_error}")
    logger.error(f"Returning empty result: []")
    logger.error("="*70)
    return "[]"


def generate_step_actions(steps: List[str], element_inventory: Dict, test_case: Dict) -> List[Dict]:
    prompt = f"""You are a test automation expert. Map the following test steps to specific HTML element interactions.

## Available HTML Elements:
{json.dumps(element_inventory, indent=2)}

## Test Steps to Implement:
{json.dumps(steps, indent=2)}

## Test Case Context:
{json.dumps(test_case, indent=2)}

Your task: For EACH step, determine which HTML element(s) to interact with and generate action objects.

Action types available:
- fill_input: Fill a text input field
- select_dropdown: Select option from dropdown
- check_checkbox: Check a checkbox
- click_button: Click a button
- wait_and_verify: Wait for element and verify text

Return a JSON array of actions. Each action must have:
- type: One of the action types above
- comment: Brief description of what this action does
- For fill_input: field_id, value
- For select_dropdown: field_id, option
- For check_checkbox: field_id
- For click_button: button_id, wait_enabled (boolean)
- For wait_and_verify: element_id, expected_text (optional)

CRITICAL RULES:
1. Map steps to ACTUAL element IDs from the inventory
2. If a step is vague (e.g., "Book ticket"), break it into atomic actions (select ticket type, fill name, fill email, etc.)
3. Before clicking submit button, ensure ALL required inputs are filled
4. Use realistic test data (e.g., "John Doe" for name, "test@example.com" for email)
5. Return ONLY the JSON array, no other text

Example output format:
[
  {{
    "type": "fill_input",
    "comment": "Enter customer name",
    "field_id": "name",
    "value": "John Doe"
  }},
  {{
    "type": "select_dropdown",
    "comment": "Select ticket type",
    "field_id": "ticketType",
    "option": "General Admission"
  }},
  {{
    "type": "click_button",
    "comment": "Submit the form",
    "button_id": "submitBtn",
    "wait_enabled": true
  }}
]

Generate the actions now:"""

    try:
        response = generate_test_cases_with_ollama(
            full_prompt=prompt,
            num_predict=1500,
            temperature=0.2,
            retries=1
        )

        actions = aggressive_json_extraction(response)

        if isinstance(actions, list) and len(actions) > 0:
            logger.info(f"LLM successfully mapped {len(steps)} steps to {len(actions)} actions")
            return actions
        else:
            logger.warning("LLM returned empty or invalid actions")
            return []

    except Exception as e:
        logger.error(f"Failed to generate step actions: {e}")
        return []

