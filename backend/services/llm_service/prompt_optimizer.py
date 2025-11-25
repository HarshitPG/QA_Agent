
from typing import Dict, List, Tuple
import json


class PromptOptimizer:
    
    
    def __init__(self, model_context_window: int = 8192, target_utilization: float = 0.7):
        
        self.model_context_window = model_context_window
        self.target_utilization = target_utilization
        self.max_prompt_tokens = int(model_context_window * target_utilization)
        
    def optimize_dependency_graph(self, dependency_graph: Dict, max_tokens: int = 800) -> str:
        
        if not dependency_graph:
            return ""
        
        sections = []
        sections.append("⚠️ FORM VALIDATION RULES (MANDATORY):")
        required_fields = dependency_graph.get('required_fields', [])
        if required_fields:
            sections.append(f"\n🔴 REQUIRED (ALL must be filled): {', '.join(required_fields)}")
            sections.append("⚠️ Submit button DISABLED until all required fields valid")
        validation_rules = dependency_graph.get('validation_rules', {})
        if validation_rules:
            sections.append("\n✅ Validation constraints:")
            for field, rule in list(validation_rules.items())[:3]:
                if '>=' in rule:
                    constraint = rule.split('>=')[-1].strip().split(')')[0]
                    sections.append(f"  - {field}: min length {constraint}")
                elif 'required' in rule.lower():
                    sections.append(f"  - {field}: required")
        fill_order = dependency_graph.get('fill_order', [])
        if fill_order and required_fields:
            required_order = [f for f in fill_order if f in required_fields or f == '__submit__']
            if required_order:
                sections.append(f"\n📋 Fill order: {' → '.join(required_order[:10])}")
        conditionals = dependency_graph.get('conditional_fields', [])
        if conditionals:
            sections.append(f"\n🔀 Conditional: {len(conditionals)} field(s) depend on other selections")
        
        return "\n".join(sections)
    
    def optimize_html_structure(self, html_structure: Dict, max_tokens: int = 600) -> str:
        
        if not html_structure:
            return ""
        
        sections = []
        sections.append("📄 HTML ELEMENTS (use exact IDs):")
        inputs = html_structure.get('inputs', [])
        if inputs:
            input_strs = []
            for inp in inputs[:8]:
                id_val = inp.get('id', 'N/A')
                type_val = inp.get('type', 'text')
                input_strs.append(f"{id_val}[{type_val}]")
            sections.append(f"  Inputs: {', '.join(input_strs)}")
        selects = html_structure.get('selects', [])
        if selects:
            select_strs = []
            for sel in selects[:5]:
                id_val = sel.get('id', 'N/A')
                options = sel.get('options', [])
                if options:
                    if isinstance(options[0], dict):
                        opt_vals = [o.get('value', o.get('text', '')) for o in options[:2]]
                    else:
                        opt_vals = options[:2]
                    select_strs.append(f"{id_val}({'/'.join(opt_vals)}...)")
                else:
                    select_strs.append(id_val)
            sections.append(f"  Selects: {', '.join(select_strs)}")
        buttons = html_structure.get('buttons', [])
        if buttons:
            button_strs = []
            for btn in buttons[:5]:
                id_val = btn.get('id', 'N/A')
                text = btn.get('text', '')
                button_strs.append(f"{id_val}[{text}]" if text else id_val)
            sections.append(f"  Buttons: {', '.join(button_strs)}")
        
        return "\n".join(sections)
    
    def build_optimized_prompt(
        self,
        user_prompt: str,
        context: str,
        requested_count: int,
        html_structure: Dict = None,
        dependency_graph: Dict = None
    ) -> str:
        
        html_section = ""
        if html_structure:
            html_section = self.optimize_html_structure(html_structure, max_tokens=600)
        
        dependency_section = ""
        if dependency_graph:
            dependency_section = self.optimize_dependency_graph(dependency_graph, max_tokens=800)
        if len(context) > 3000:
            context = context[:3000] + "...[truncated]"
        prompt = f"""Generate test cases following these MANDATORY rules:

{dependency_section}

{html_section}

CONTEXT (factual reference):
{context[:700]}

USER REQUEST: {user_prompt}

OUTPUT REQUIREMENTS:
- Generate EXACTLY {requested_count} test case(s)
- Include ALL required fields from validation rules above
- Follow the recommended fill order
- Use exact element IDs from HTML structure
- Output ONLY valid JSON array (no markdown, no extra text):

[
  {{
    "test_id": "TC-001",
    "feature": "Brief feature name",
    "test_scenario": "What is being tested",
    "test_steps": [
      "Step 1 with [element_id]",
      "Step 2 with [element_id]",
      "..."
    ],
    "expected_result": "Expected outcome",
    "test_type": "positive",
    "priority": "high"
  }}
]

CRITICAL: If required fields are listed above, your test case MUST include steps to fill ALL of them before submit. Submit button is DISABLED until requirements met."""

        return prompt


def get_prompt_optimizer(model_name: str = "llama3.1:8b") -> PromptOptimizer:
    
    context_windows = {
        "llama3.1": 8192,
        "llama3.2": 4096,
        "llama-3.3-70b": 131072,
        "mistral": 8192,
        "qwen2.5": 8192,
    }
    base_model = model_name.split(":")[0]
    context_window = context_windows.get(base_model, 8192)
    target_utilization = 0.65 if context_window <= 8192 else 0.75
    
    return PromptOptimizer(
        model_context_window=context_window,
        target_utilization=target_utilization
    )
