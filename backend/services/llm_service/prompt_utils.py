import re
import hashlib
from typing import List, Dict, Tuple
from .prompt_optimizer import get_prompt_optimizer
from .config import OLLAMA_MODEL


def redact_sensitive(text: str) -> str:
  if not text:
    return text
  text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL]', text)
  text = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD]', text)
  return text


def sanitize_text(text: str) -> str:
  if not text:
    return ""
  text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', ' ', text)
  text = re.sub(r'\s+', ' ', text).strip()
  return text


def estimate_tokens(text: str) -> int:
  return max(1, len(text) // 4)


def truncate_context_smart(chunks: List[Dict], max_tokens: int = 6000) -> Tuple[str, bool, List[Dict]]:
  selected = []
  total = 0
  for chunk in chunks:
    t = chunk.get('text', '')
    tok = estimate_tokens(t)
    if total + tok > max_tokens:
      break
    selected.append(chunk)
    total += tok
  parts = []
  for c in selected:
    parts.append(f"[Source: {c.get('source','unknown')}]\n{sanitize_text(c.get('text',''))}\n")
  context = '\n'.join(parts)
  return context, len(selected) < len(chunks), selected


def deduplicate_chunks(chunks: List[Dict]) -> Tuple[List[Dict], int]:
  seen = set(); out = []
  for c in chunks:
    h = hashlib.md5(c.get('text','').strip().lower().encode()).hexdigest()
    if h not in seen:
      seen.add(h); out.append(c)
  return out, len(chunks) - len(out)


def build_dynamic_prompt(user_prompt: str, context: str, requested_count: int = 1, html_structure: Dict = None, dependency_graph: Dict = None) -> str:
  
  optimizer = get_prompt_optimizer(OLLAMA_MODEL)
  if dependency_graph and html_structure:
    return optimizer.build_optimized_prompt(
      user_prompt=user_prompt,
      context=context,
      requested_count=requested_count,
      html_structure=html_structure,
      dependency_graph=dependency_graph
    )

  html_section = ""
  if html_structure:
    html_section = f"""
HTML STRUCTURE REFERENCE (Use these EXACT element IDs/names in test steps):
{_format_html_structure_for_prompt(html_structure)}
"""
  dependency_section = ""
  if dependency_graph:
    dependency_section = f"""
FORM VALIDATION & DEPENDENCY RULES (CRITICAL - Follow this exact order):
{_format_dependency_graph_for_prompt(dependency_graph)}

IMPORTANT: The submit button is DISABLED until ALL required fields are valid.
You MUST include ALL prerequisite steps before the submit action.
"""
  
  return f"""You are a QA test case generator. Your task is to create test cases based ONLY on the provided documentation and HTML structure.

CRITICAL RULES:
1. Use ONLY information from the CONTEXT below
2. Do NOT invent prices, numbers, or data
3. Test steps must reference ACTUAL element IDs/names from HTML structure
4. Do NOT include specific values like "$18.00" or "$1.80" in test steps
5. Generate EXACTLY {requested_count} test case(s)
6. Each test step should be actionable and map to HTML elements

**MANDATORY FORM VALIDATION RULES (NON-NEGOTIABLE):**
7. If REQUIRED FIELDS are listed below, you MUST include steps to fill ALL of them
8. If a RECOMMENDED FILL ORDER is provided, follow it exactly
9. The submit button will be DISABLED until all required fields are valid
10. Even if the user's request is brief (e.g., "test discount code"), you MUST still fill ALL required fields first
11. NEVER generate a test case that tries to submit without filling required fields - it will FAIL in real execution

CONTEXT (Your ONLY source of truth):
{context[:3000]}
{html_section}
{dependency_section}
USER REQUEST:
{user_prompt}

OUTPUT FORMAT (JSON array only, no markdown):
[
  {{
    "test_id": "TC-001",
    "feature": "Brief feature name from context",
    "test_scenario": "What is being tested",
    "test_steps": [
      "Select [element_name] from dropdown",
      "Enter value in [field_id]",
      "Click [button_id] button"
    ],
    "expected_result": "Expected outcome from context",
    "test_type": "positive",
    "priority": "high",
    "grounded_in": "document_name_from_context"
  }}
]

Generate the JSON array now:"""


def _format_html_structure_for_prompt(html_structure: Dict) -> str:
  
  sections = []
  if html_structure.get('inputs'):
    sections.append("INPUT FIELDS:")
    for inp in html_structure['inputs'][:15]:
      inp_info = f"  - ID: {inp.get('id', 'N/A')}"
      if inp.get('name'):
        inp_info += f", Name: {inp['name']}"
      inp_info += f", Type: {inp.get('type', 'text')}"
      if inp.get('placeholder'):
        inp_info += f", Placeholder: '{inp['placeholder']}'"
      sections.append(inp_info)
  if html_structure.get('selects'):
    sections.append("\nDROPDOWN MENUS:")
    for sel in html_structure['selects'][:10]:
      sel_info = f"  - ID: {sel.get('id', 'N/A')}"
      if sel.get('name'):
        sel_info += f", Name: {sel['name']}"
      if sel.get('options'):
        options = sel['options'][:5]
        if options and isinstance(options[0], dict):
          options_str = ', '.join([opt.get('value', opt.get('text', '')) for opt in options])
        else:
          options_str = ', '.join(options)
        sel_info += f"\n    Options: [{options_str}]"
      sections.append(sel_info)
  if html_structure.get('buttons'):
    sections.append("\nBUTTONS:")
    for btn in html_structure['buttons'][:10]:
      btn_info = f"  - ID: {btn.get('id', 'N/A')}"
      if btn.get('text'):
        btn_info += f", Text: '{btn['text']}'"
      if btn.get('type'):
        btn_info += f", Type: {btn['type']}"
      sections.append(btn_info)
  if html_structure.get('checkboxes'):
    sections.append("\nCHECKBOXES:")
    for cb in html_structure['checkboxes'][:10]:
      cb_info = f"  - ID: {cb.get('id', 'N/A')}"
      if cb.get('label'):
        cb_info += f", Label: '{cb['label']}'"
      sections.append(cb_info)
  if html_structure.get('success_elements'):
    sections.append("\nSUCCESS/CONFIRMATION ELEMENTS:")
    for elem in html_structure['success_elements'][:5]:
      elem_info = f"  - ID: {elem.get('id', 'N/A')}"
      if elem.get('text_content'):
        elem_info += f", Content: '{elem['text_content'][:50]}'"
      sections.append(elem_info)
  if html_structure.get('dynamic_elements'):
    sections.append("\nDYNAMIC ELEMENTS (for validation/waiting):")
    for elem in html_structure['dynamic_elements'][:5]:
      elem_info = f"  - ID: {elem.get('id', 'N/A')}"
      if elem.get('class'):
        elem_info += f", Class: {elem['class']}"
      sections.append(elem_info)
  return '\n'.join(sections)


def _format_dependency_graph_for_prompt(dependency_graph: Dict) -> str:
  
  if not dependency_graph:
    return ""
    
  sections = []
  sections.append("\n" + "="*80)
  sections.append("  FORM DEPENDENCY GRAPH - MUST FOLLOW EXACTLY ")
  sections.append("="*80)
  

  if dependency_graph.get('required_fields'):
    sections.append("\n REQUIRED FIELDS (ALL must be filled before ANY submit action):")
    for field_id in dependency_graph['required_fields']:
      sections.append(f" {field_id}")
    sections.append("\n CRITICAL: Test cases that skip required fields WILL FAIL in execution!")
    sections.append(" ALWAYS include steps to fill ALL required fields, even if user's prompt doesn't mention them.")
      

  if dependency_graph.get('fill_order'):
    sections.append("\n RECOMMENDED FILL ORDER (follow this sequence):")
    for i, elem_id in enumerate(dependency_graph['fill_order'][:15], 1):
      is_required = elem_id in dependency_graph.get('required_fields', [])
      marker = " REQUIRED" if is_required else "optional"
      sections.append(f"  {i}. {elem_id} ({marker})")
      
  if dependency_graph.get('conditional_fields'):
    sections.append("\n CONDITIONAL DEPENDENCIES:")
    for dep in dependency_graph['conditional_fields']:
      sections.append(f"  - {dep['to']} depends on {dep['from']} (condition: {dep.get('condition', 'N/A')})")
      
  if dependency_graph.get('validation_rules'):
    sections.append("\nVALIDATION RULES:")
    for elem_id, rule in dependency_graph['validation_rules'].items():
      if rule:
        sections.append(f"  - {elem_id}: {rule[:100]}")
        
  if dependency_graph.get('submit_button_enabled_when'):
    sections.append(f"\n SUBMIT BUTTON STATUS: {dependency_graph['submit_button_enabled_when']}")
    sections.append("  Attempting to click submit before meeting these conditions will FAIL!")
    
  sections.append("\n" + "="*80)
  return "\n".join(sections)
