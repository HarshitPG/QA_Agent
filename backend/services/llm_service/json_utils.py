import json
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def repair_json(text: str) -> str:
    
    text = re.sub(r',\s*([}\]])', r'\1', text)
    text = re.sub(r'}\s*{', '},{', text)
    open_braces = text.count('{'); close_braces = text.count('}')
    if open_braces > close_braces:
        text += '}' * (open_braces - close_braces)
    open_brackets = text.count('['); close_brackets = text.count(']')
    if open_brackets > close_brackets:
        text += ']' * (open_brackets - close_brackets)
    cleaned = text.strip()
    if cleaned.startswith('{') and cleaned.endswith('}') and not cleaned.startswith('['):
        cleaned = f'[{cleaned}]'
    return cleaned


def extract_json_from_response(text: str, stop_token: str = '</END_JSON>') -> str:
    
    text = text.replace(stop_token, '')
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        return match.group(0)
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        return match.group(0)
    return text


def aggressive_json_extraction(raw_text: str) -> str:
    
    start = raw_text.find('[')
    end = raw_text.rfind(']')
    if start != -1 and end != -1 and end > start:
        candidate = raw_text[start:end+1]
        return repair_json(candidate)
    start = raw_text.find('{')
    end = raw_text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = raw_text[start:end+1]
        return repair_json(candidate)
    return '[]'


def secondary_json_format_pass(raw_text: str) -> List[Dict]:
    
    logger.warning("Secondary JSON formatting pass engaged")
    objects: List[Dict] = []
    for m in re.finditer(r'\{[\s\S]*?\}', raw_text):
        candidate = m.group(0)
        try:
            parsed = json.loads(repair_json(candidate))
            if isinstance(parsed, dict):
                objects.append(parsed)
            elif isinstance(parsed, list):
                objects.extend([o for o in parsed if isinstance(o, dict)])
        except Exception:
            continue
        if len(objects) >= 10:
            break
    return objects
