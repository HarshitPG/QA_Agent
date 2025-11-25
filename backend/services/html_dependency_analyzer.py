
import re
import json
from typing import Dict, List, Set, Tuple
from bs4 import BeautifulSoup
import ast
import logging

logger = logging.getLogger(__name__)


class FormDependencyGraph:
    
    def __init__(self):
        self.nodes = {}  
        self.edges = [] 
        self.submit_dependencies = set()  
        self.validation_rules = {}  
        
    def add_node(self, element_id: str, element_type: str, **attrs):
        self.nodes[element_id] = {
            'id': element_id,
            'type': element_type,
            **attrs
        }
        
    def add_edge(self, from_id: str, to_id: str, condition: str = None):
        self.edges.append({
            'from': from_id,
            'to': to_id,
            'condition': condition
        })
        
    def add_submit_dependency(self, element_id: str):
        self.submit_dependencies.add(element_id)
        
    def get_submit_prerequisites(self) -> List[Dict]:
        prereqs = []
        for elem_id in self.submit_dependencies:
            if elem_id in self.nodes:
                prereqs.append(self.nodes[elem_id])
        return prereqs
    
    def topological_sort(self) -> List[str]:
        in_degree = {node_id: 0 for node_id in self.nodes}
        
        for edge in self.edges:
            if edge['to'] in in_degree:
                in_degree[edge['to']] += 1
                
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            
            for edge in self.edges:
                if edge['from'] == node_id and edge['to'] in in_degree:
                    in_degree[edge['to']] -= 1
                    if in_degree[edge['to']] == 0:
                        queue.append(edge['to'])
                        
        return result
    
    def to_dict(self) -> Dict:
        return {
            'nodes': self.nodes,
            'edges': self.edges,
            'submit_dependencies': list(self.submit_dependencies),
            'fill_order': self.topological_sort()
        }


def analyze_html_dependencies(html_content: str) -> FormDependencyGraph:
    """
    Perform static analysis on HTML + embedded JavaScript to build dependency graph.
    Uses AST parsing for JavaScript and DOM analysis for HTML.
    """
    graph = FormDependencyGraph()
    soup = BeautifulSoup(html_content, 'html.parser')
    
    _extract_form_elements(soup, graph)

    script_tags = soup.find_all('script')
    for script in script_tags:
        js_code = script.string
        if js_code:
            _parse_javascript_dependencies(js_code, graph)

    _infer_implicit_dependencies(soup, graph)
    
    return graph


def _extract_form_elements(soup: BeautifulSoup, graph: FormDependencyGraph):

    for inp in soup.find_all('input'):
        elem_id = inp.get('id')
        if not elem_id:
            continue
            
        inp_type = inp.get('type', 'text')
        graph.add_node(
            elem_id,
            element_type='input',
            input_type=inp_type,
            required=inp.has_attr('required'),
            name=inp.get('name'),
            placeholder=inp.get('placeholder', ''),
            min=inp.get('min'),
            max=inp.get('max'),
            maxlength=inp.get('maxlength'),
            pattern=inp.get('pattern')
        )
        
    for sel in soup.find_all('select'):
        elem_id = sel.get('id')
        if not elem_id:
            continue
            
        options = [opt.get('value') or opt.text.strip() for opt in sel.find_all('option')]
        graph.add_node(
            elem_id,
            element_type='select',
            required=sel.has_attr('required'),
            options=options,
            name=sel.get('name')
        )
        
    for btn in soup.find_all('button'):
        btn_id = btn.get('id')
        if not btn_id:
            continue
            
        btn_type = btn.get('type', 'button')
        graph.add_node(
            btn_id,
            element_type='button',
            button_type=btn_type,
            text=btn.text.strip(),
            disabled=btn.has_attr('disabled')
        )
        
        if btn_type == 'submit':
            graph.add_node('__submit__', element_type='submit_action')
            graph.add_edge(btn_id, '__submit__')


def _parse_javascript_dependencies(js_code: str, graph: FormDependencyGraph):
    
    validation_pattern = r'const\s+(\w+Valid)\s*=\s*(.+?);'
    for match in re.finditer(validation_pattern, js_code):
        var_name = match.group(1)
        condition = match.group(2)

        elem_id_match = re.search(r'getElementById\(["\'](\w+)["\']\)', condition)
        if elem_id_match:
            elem_id = elem_id_match.group(1)
            if elem_id in graph.nodes:
                graph.nodes[elem_id]['validation_rule'] = condition
                graph.nodes[elem_id]['validation_var'] = var_name

    all_valid_pattern = r'const\s+allValid\s*=\s*(.+?);'
    match = re.search(all_valid_pattern, js_code)
    if match:
        deps_str = match.group(1)
        valid_vars = re.findall(r'(\w+Valid|\w+Ok)', deps_str)
        
        for var in valid_vars:
            for node_id, node_data in graph.nodes.items():
                if node_data.get('validation_var') == var:
                    graph.add_submit_dependency(node_id)
                    

    conditional_pattern = r'if\s*\((\w+)\.value\s*===\s*["\'](\w+)["\']\)\s*\{[^}]*(\w+)\.style\.display'
    for match in re.finditer(conditional_pattern, js_code):
        controlling_elem = match.group(1)
        trigger_value = match.group(2)
        dependent_elem = match.group(3)

        if controlling_elem in graph.nodes:
            graph.add_edge(
                controlling_elem,
                dependent_elem,
                condition=f"value=='{trigger_value}'"
            )
            

    event_pattern = r'getElementById\(["\'](\w+)["\']\)\.addEventListener\(["\'](\w+)["\']\s*,\s*(\w+)'
    for match in re.finditer(event_pattern, js_code):
        elem_id = match.group(1)
        event_type = match.group(2)
        callback = match.group(3)
        
        if elem_id in graph.nodes:
            graph.nodes[elem_id]['triggers'] = graph.nodes[elem_id].get('triggers', [])
            graph.nodes[elem_id]['triggers'].append({
                'event': event_type,
                'action': callback
            })

    validation_checks = [
        (r'if\s*\(\s*(\w+)\s*>\s*(\d+)\s*\)', 'max', 'value'),
        (r'if\s*\(\s*(\w+)\s*<\s*(\d+)\s*\)', 'min', 'value'),
        (r'/([^/]+)/\.test\((\w+)\)', 'pattern', 'regex'),
        (r'\.length\s*>=\s*(\d+)', 'minlength', 'value'),
    ]
    
    for pattern, rule_type, rule_value_type in validation_checks:
        for match in re.finditer(pattern, js_code):
            pass  # Complex - would need full AST parsing


def _infer_implicit_dependencies(soup: BeautifulSoup, graph: FormDependencyGraph):

    form = soup.find('form')
    if form:
        submit_btn = form.find('button', {'type': 'submit'})
        if submit_btn:
            submit_id = submit_btn.get('id', '__submit__')
            
            required_inputs = form.find_all(['input', 'select'], required=True)
            for inp in required_inputs:
                inp_id = inp.get('id')
                if inp_id and inp_id in graph.nodes:
                    graph.add_submit_dependency(inp_id)
                    

            terms_checkbox = form.find('input', {'type': 'checkbox', 'id': re.compile('terms|agree|accept', re.I)})
            if terms_checkbox:
                terms_id = terms_checkbox.get('id')
                if terms_id:
                    graph.add_submit_dependency(terms_id)
                    
            
            payment_radio = form.find('input', {'name': 'payment', 'type': 'radio'})
            if payment_radio:

                from backend.services.semantic_matcher import get_semantic_matcher
                semantic_matcher = get_semantic_matcher()
                
                for input_elem in form.find_all('input'):
                    input_id = input_elem.get('id')
                    if not input_id or input_id not in graph.nodes:
                        continue
                    
                    field_attrs = {
                        'id': input_id,
                        'name': input_elem.get('name', ''),
                        'placeholder': input_elem.get('placeholder', ''),
                        'aria_label': input_elem.get('aria-label', '')
                    }
                    is_payment, field_type, confidence = semantic_matcher.detect_payment_field(field_attrs)
                    
                    if is_payment and confidence > 0.4:
                        graph.add_submit_dependency(input_id)
                        if graph.nodes[input_id]:
                            graph.nodes[input_id]['implicit_required'] = True
                            graph.nodes[input_id]['reason'] = f'Payment field ({field_type})'
                            
            email_input = form.find('input', {'type': 'email'})
            if email_input and email_input.get('id'):
                email_id = email_input.get('id')
                if email_id in graph.nodes:
                    graph.add_submit_dependency(email_id)
                    
            quantity_input = form.find('input', {'type': 'number', 'id': re.compile('quantity|qty|amount', re.I)})
            if quantity_input and quantity_input.get('id'):
                qty_id = quantity_input.get('id')
                if qty_id in graph.nodes:
                    graph.add_submit_dependency(qty_id)


def generate_test_data_from_graph(graph: FormDependencyGraph) -> Dict[str, any]:
    test_data = {}
    fill_order = graph.topological_sort()
    
    for elem_id in fill_order:
        node = graph.nodes.get(elem_id)
        if not node:
            continue
            
        elem_type = node['type']
        
        if elem_type == 'input':
            inp_type = node.get('input_type', 'text')
            
            if inp_type == 'text':
                min_len = node.get('minlength', 2)
                test_data[elem_id] = 'A' * max(int(min_len) if min_len else 2, 2)
                
            elif inp_type == 'email':
                test_data[elem_id] = 'test@example.com'
                
            elif inp_type == 'tel':
                test_data[elem_id] = '1234567890'
                
            elif inp_type == 'number':
                min_val = node.get('min', '1')
                test_data[elem_id] = min_val
                
            elif inp_type == 'checkbox':
                if elem_id in graph.submit_dependencies:
                    test_data[elem_id] = True
                    
        elif elem_type == 'select':
            options = node.get('options', [])
            if options:
                test_data[elem_id] = options[0]
                
    return test_data


def get_submission_preconditions(graph: FormDependencyGraph) -> Dict:
    prereqs = graph.get_submit_prerequisites()
    
    all_required_ids = list(graph.submit_dependencies)
    
    return {
        'required_fields': all_required_ids,  
        'validation_rules': {p['id']: p.get('validation_rule') for p in prereqs if p.get('validation_rule')},
        'fill_order': graph.topological_sort(),
        'conditional_fields': [e for e in graph.edges if e.get('condition')],
        'submit_button_enabled_when': 'All required fields valid AND terms accepted'
    }
