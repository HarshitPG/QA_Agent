import re
import json
import logging
from typing import List, Dict, Tuple
from backend.services.config_semantic import Priority, TestType

logger = logging.getLogger(__name__)

try:
    from .config import VALIDATION_PATTERNS
except ImportError:
    VALIDATION_PATTERNS = {
        "price": {
            "pattern": r'\$\d+(?:\.\d{2})?',
            "enabled": True,
            "blacklist": set()
        },
        "percentage": {
            "pattern": r'\d+%',
            "enabled": True,
            "blacklist": set()
        },
        "code": {
            "pattern": r'\b[A-Z][A-Z0-9]{3,}\b',
            "enabled": True,
            "blacklist": {"STEP", "TEST", "HTTP", "JSON", "NOTE", "TODO", "FAIL", "PASS", 
                         "MISSING", "POST", "GET", "PUT", "DELETE", "TRUE", "FALSE", "NULL"}
        }
    }


def validate_test_case_schema(test_case: Dict, retrieved_chunks: List[Dict]) -> Tuple[Dict, List[str]]:
    issues: List[str] = []
    required = ["test_id", "feature", "test_scenario", "test_steps", "expected_result", "test_type", "priority"]
    for f in required:
        if f not in test_case or not test_case[f]:
            test_case[f] = f"[MISSING: {f}]"; issues.append(f"missing:{f}")
    if not isinstance(test_case.get("test_steps"), list):
        raw = str(test_case.get("test_steps", ""))
        test_case["test_steps"] = [s.strip() for s in re.split(r'[\n;]+', raw) if s.strip()][:6] or ["Step 1", "Step 2"]
    if test_case.get("test_type") not in {TestType.POSITIVE, TestType.NEGATIVE, "boundary", "edge_case"}:
        test_case["test_type"] = TestType.POSITIVE
    if test_case.get("priority") not in {Priority.HIGH, Priority.MEDIUM, Priority.LOW}:
        test_case["priority"] = Priority.MEDIUM
    if not test_case.get("grounded_in"):
        sources = [c.get("source","unknown") for c in retrieved_chunks]
        test_case["grounded_in"] = sources[0] if sources else "document.txt"
    context_text = " ".join(c.get("text","") for c in retrieved_chunks).lower()
    content_text = f"{test_case.get('test_scenario','')} {test_case.get('expected_result','')} {' '.join(test_case.get('test_steps',[]))}"
    patterns = []
    for pattern_name, pattern_config in VALIDATION_PATTERNS.items():
        if pattern_config.get("enabled", True):
            patterns.append((pattern_config["pattern"], pattern_name))
    
    fabricated = []
    for pat, ptype in patterns:
        for val in re.findall(pat, content_text):
            blacklist = VALIDATION_PATTERNS.get(ptype, {}).get("blacklist", set())
            if blacklist and val in blacklist:
                continue
            if ptype == 'code' and test_case.get("test_type") == TestType.NEGATIVE:
                continue
            check_val = val.lower()
            if ptype == 'price':
                if check_val.endswith('.00'):
                    check_val = check_val[:-3]
                if check_val == '$0':
                    from backend.services.semantic_matcher import get_semantic_matcher
                    semantic_matcher = get_semantic_matcher()
                    is_zero_cost, confidence = semantic_matcher.is_validation_context_zero_cost(context_text)
                    if is_zero_cost:
                        continue
            if check_val not in context_text:
                fabricated.append(val)

    if fabricated:
        test_case["_action"] = "drop"
        test_case["_hallucination_warning"] = f"fabricated: {', '.join(fabricated[:5])}"
        issues.append("hallucination")
    return test_case, issues


def detect_semantic_duplicates(test_cases: List[Dict]) -> List[int]:
    indices: List[int] = []
    seen_signatures = {}
    for i, tc in enumerate(test_cases):
        sig_words = set(re.findall(r'\w+', (tc.get('test_scenario','') + ' ' + ' '.join(tc.get('test_steps',[]))).lower()))
        sig = tuple(sorted(w for w in sig_words if len(w) > 4)[:25])
        if sig in seen_signatures:
            indices.append(i)
        else:
            seen_signatures[sig] = i
    return indices


def ensure_unique_test_ids(test_cases: List[Dict]) -> List[Dict]:
    for i, tc in enumerate(test_cases, 1):
        if isinstance(tc, dict):
            tc['test_id'] = f'TC-{i:03d}'
    return test_cases


def has_verbatim_evidence(tc: Dict, used_chunks: List[Dict]) -> bool:
    context = " ".join(c.get('text','').lower() for c in used_chunks)
    tokens = set(re.findall(r'(\$\d+(?:\.\d{2})?|\d+%|\b[A-Z][A-Z0-9]{4,}\b)', json.dumps(tc)))
    
    if not tokens:
        return True
        
    for t in tokens:
        t_lower = t.lower()
        if t_lower in context:
            return True
        if t_lower == '$0' or t_lower == '$0.00':
            from backend.services.semantic_matcher import get_semantic_matcher
            semantic_matcher = get_semantic_matcher()
            is_zero_cost, confidence = semantic_matcher.is_validation_context_zero_cost(context)
            if is_zero_cost:
                return True
            
    return False
