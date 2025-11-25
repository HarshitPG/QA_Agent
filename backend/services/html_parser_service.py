
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import json
import re


def parse_html_structure(html_content: bytes | str) -> Dict[str, Any]:
   
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='ignore')
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for script in soup(["script", "style"]):
        script.extract()
    
    structure = {
        "forms": extract_forms(soup),
        "buttons": extract_buttons(soup),
        "links": extract_links(soup),
        "inputs": extract_inputs(soup),
        "selects": extract_selects(soup),
        "text_areas": extract_textareas(soup),
        "checkboxes": extract_checkboxes(soup),
        "radio_groups": extract_radio_groups(soup),
        "conditional_sections": extract_conditional_sections(soup),
        "dynamic_elements": extract_dynamic_elements(soup),
        "error_elements": extract_error_elements(soup),
        "success_elements": extract_success_elements(soup),
        "headings": extract_headings(soup),
        "page_title": soup.title.string if soup.title else "Untitled Page",
        "page_structure": build_page_hierarchy(soup),
        "important_attributes": extract_important_attributes(soup),
        "interactive_elements": extract_interactive_elements(soup),
        "validation_attributes": extract_validation_attributes(soup),
        "behavior_analysis": analyze_page_behavior(soup)
    }
    
    return structure


def extract_forms(soup: BeautifulSoup) -> List[Dict]:
    forms = []
    
    for idx, form in enumerate(soup.find_all('form'), 1):
        form_data = {
            "form_index": idx,
            "id": form.get('id', f"form_{idx}"),
            "name": form.get('name', ''),
            "action": form.get('action', ''),
            "method": form.get('method', 'GET').upper(),
            "fields": []
        }
        
        for input_elem in form.find_all(['input', 'select', 'textarea']):
            field = {
                "tag": input_elem.name,
                "type": input_elem.get('type', 'text'),
                "id": input_elem.get('id', ''),
                "name": input_elem.get('name', ''),
                "placeholder": input_elem.get('placeholder', ''),
                "required": input_elem.has_attr('required'),
                "value": input_elem.get('value', ''),
                "class": ' '.join(input_elem.get('class', [])),
                "aria_label": input_elem.get('aria-label', ''),
                "pattern": input_elem.get('pattern', ''),
                "maxlength": input_elem.get('maxlength', ''),
                "minlength": input_elem.get('minlength', '')
            }
            
            if input_elem.name == 'select':
                field['options'] = [
                    {
                        "value": opt.get('value', opt.text.strip()),
                        "text": opt.text.strip()
                    }
                    for opt in input_elem.find_all('option')
                ]
            
            form_data['fields'].append(field)
        
        for button in form.find_all(['button', 'input']):
            if button.name == 'button' or button.get('type') in ['submit', 'button']:
                form_data['fields'].append({
                    "tag": "button",
                    "type": button.get('type', 'submit'),
                    "id": button.get('id', ''),
                    "name": button.get('name', ''),
                    "text": button.text.strip() if button.name == 'button' else button.get('value', ''),
                    "class": ' '.join(button.get('class', [])),
                    "onclick": button.get('onclick', ''),
                    "disabled": button.has_attr('disabled')
                })
        
        forms.append(form_data)
    
    return forms


def extract_buttons(soup: BeautifulSoup) -> List[Dict]:
    buttons = []
    
    for button in soup.find_all(['button', 'input']):
        if button.name == 'input' and button.get('type') not in ['button', 'submit', 'reset']:
            continue
            
        button_data = {
            "tag": button.name,
            "type": button.get('type', 'button'),
            "id": button.get('id', ''),
            "name": button.get('name', ''),
            "text": button.text.strip() if button.name == 'button' else button.get('value', ''),
            "class": ' '.join(button.get('class', [])),
            "onclick": button.get('onclick', ''),
            "disabled": button.has_attr('disabled'),
            "aria_label": button.get('aria-label', ''),
            "data_attributes": {k: v for k, v in button.attrs.items() if k.startswith('data-')}
        }
        buttons.append(button_data)
    
    return buttons


def extract_links(soup: BeautifulSoup) -> List[Dict]:
    links = []
    
    for link in soup.find_all('a'):
        link_data = {
            "href": link.get('href', ''),
            "text": link.text.strip(),
            "id": link.get('id', ''),
            "class": ' '.join(link.get('class', [])),
            "target": link.get('target', ''),
            "title": link.get('title', '')
        }
        links.append(link_data)
    
    return links


def extract_inputs(soup: BeautifulSoup) -> List[Dict]:
    inputs = []
    
    for input_elem in soup.find_all('input'):
        input_data = {
            "type": input_elem.get('type', 'text'),
            "id": input_elem.get('id', ''),
            "name": input_elem.get('name', ''),
            "placeholder": input_elem.get('placeholder', ''),
            "value": input_elem.get('value', ''),
            "class": ' '.join(input_elem.get('class', [])),
            "required": input_elem.has_attr('required'),
            "disabled": input_elem.has_attr('disabled'),
            "readonly": input_elem.has_attr('readonly'),
            "pattern": input_elem.get('pattern', ''),
            "maxlength": input_elem.get('maxlength', ''),
            "minlength": input_elem.get('minlength', ''),
            "min": input_elem.get('min', ''),
            "max": input_elem.get('max', ''),
            "aria_label": input_elem.get('aria-label', ''),
            "autocomplete": input_elem.get('autocomplete', '')
        }
        inputs.append(input_data)
    
    return inputs


def extract_selects(soup: BeautifulSoup) -> List[Dict]:
    selects = []
    
    for select in soup.find_all('select'):
        select_data = {
            "id": select.get('id', ''),
            "name": select.get('name', ''),
            "class": ' '.join(select.get('class', [])),
            "required": select.has_attr('required'),
            "multiple": select.has_attr('multiple'),
            "disabled": select.has_attr('disabled'),
            "aria_label": select.get('aria-label', ''),
            "options": [
                {
                    "value": opt.get('value', opt.text.strip()),
                    "text": opt.text.strip(),
                    "selected": opt.has_attr('selected')
                }
                for opt in select.find_all('option')
            ]
        }
        selects.append(select_data)
    
    return selects


def extract_textareas(soup: BeautifulSoup) -> List[Dict]:
    textareas = []
    
    for textarea in soup.find_all('textarea'):
        textarea_data = {
            "id": textarea.get('id', ''),
            "name": textarea.get('name', ''),
            "placeholder": textarea.get('placeholder', ''),
            "class": ' '.join(textarea.get('class', [])),
            "required": textarea.has_attr('required'),
            "disabled": textarea.has_attr('disabled'),
            "readonly": textarea.has_attr('readonly'),
            "rows": textarea.get('rows', ''),
            "cols": textarea.get('cols', ''),
            "maxlength": textarea.get('maxlength', ''),
            "aria_label": textarea.get('aria-label', '')
        }
        textareas.append(textarea_data)
    
    return textareas


def extract_headings(soup: BeautifulSoup) -> List[Dict]:
    headings = []
    
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        heading_data = {
            "level": heading.name,
            "text": heading.text.strip(),
            "id": heading.get('id', ''),
            "class": ' '.join(heading.get('class', []))
        }
        headings.append(heading_data)
    
    return headings


def build_page_hierarchy(soup: BeautifulSoup) -> Dict:
    hierarchy = {
        "title": soup.title.string if soup.title else "",
        "main_sections": []
    }
    
    for section in soup.find_all(['main', 'section', 'article', 'div'], limit=20):
        if section.get('id') or section.get('class'):
            hierarchy['main_sections'].append({
                "tag": section.name,
                "id": section.get('id', ''),
                "class": ' '.join(section.get('class', [])),
                "role": section.get('role', ''),
                "has_forms": len(section.find_all('form')) > 0,
                "has_inputs": len(section.find_all('input')) > 0
            })
    
    return hierarchy


def extract_important_attributes(soup: BeautifulSoup) -> Dict:
    attributes = {
        "ids": [],
        "classes": set(),
        "names": []
    }
    
    for elem in soup.find_all(id=True):
        attributes['ids'].append(elem.get('id'))
    
    for elem in soup.find_all(class_=True):
        attributes['classes'].update(elem.get('class', []))
    
    for elem in soup.find_all(attrs={'name': True}):
        attributes['names'].append(elem.get('name'))
    
    attributes['classes'] = sorted(list(attributes['classes']))
    
    return attributes


def extract_interactive_elements(soup: BeautifulSoup) -> List[Dict]:
    interactive = []
    
    for elem in soup.find_all(attrs={'onclick': True}):
        interactive.append({
            "tag": elem.name,
            "id": elem.get('id', ''),
            "class": ' '.join(elem.get('class', [])),
            "onclick": elem.get('onclick', ''),
            "text": elem.text.strip()[:50]
        })
    
    for elem in soup.find_all(lambda tag: any(attr.startswith('data-') for attr in tag.attrs)):
        data_attrs = {k: v for k, v in elem.attrs.items() if k.startswith('data-')}
        interactive.append({
            "tag": elem.name,
            "id": elem.get('id', ''),
            "class": ' '.join(elem.get('class', [])),
            "data_attributes": data_attrs,
            "text": elem.text.strip()[:50]
        })
    
    return interactive


def extract_validation_attributes(soup: BeautifulSoup) -> List[Dict]:
    validations = []
    
    for input_elem in soup.find_all(['input', 'textarea', 'select']):
        if input_elem.get('pattern') or input_elem.has_attr('required') or input_elem.get('minlength') or input_elem.get('maxlength'):
            validations.append({
                "id": input_elem.get('id', ''),
                "name": input_elem.get('name', ''),
                "type": input_elem.get('type', input_elem.name),
                "required": input_elem.has_attr('required'),
                "pattern": input_elem.get('pattern', ''),
                "minlength": input_elem.get('minlength', ''),
                "maxlength": input_elem.get('maxlength', ''),
                "min": input_elem.get('min', ''),
                "max": input_elem.get('max', '')
            })
    
    return validations


def extract_checkboxes(soup: BeautifulSoup) -> List[Dict]:
    checkboxes = []
    
    for checkbox in soup.find_all('input', type='checkbox'):
        label_text = ''
        if checkbox.get('id'):
            label = soup.find('label', attrs={'for': checkbox.get('id')})
            if label:
                label_text = label.text.strip()
        if not label_text:
            parent_label = checkbox.find_parent('label')
            if parent_label:
                label_text = parent_label.text.strip()
        
        checkbox_data = {
            "id": checkbox.get('id', ''),
            "name": checkbox.get('name', ''),
            "value": checkbox.get('value', 'on'),
            "checked": checkbox.has_attr('checked'),
            "required": checkbox.has_attr('required'),
            "disabled": checkbox.has_attr('disabled'),
            "label": label_text,
            "class": ' '.join(checkbox.get('class', []))
        }
        checkboxes.append(checkbox_data)
    
    return checkboxes


def extract_radio_groups(soup: BeautifulSoup) -> List[Dict]:
    radio_groups = {}
    
    for radio in soup.find_all('input', type='radio'):
        name = radio.get('name', '')
        if not name:
            continue
        
        if name not in radio_groups:
            radio_groups[name] = {
                "name": name,
                "options": [],
                "required": radio.has_attr('required')
            }
        
        label_text = ''
        if radio.get('id'):
            label = soup.find('label', attrs={'for': radio.get('id')})
            if label:
                label_text = label.text.strip()
        if not label_text:
            parent_label = radio.find_parent('label')
            if parent_label:
                label_text = parent_label.text.strip()
        
        radio_groups[name]['options'].append({
            "id": radio.get('id', ''),
            "value": radio.get('value', ''),
            "checked": radio.has_attr('checked'),
            "label": label_text
        })
    
    return list(radio_groups.values())


def extract_conditional_sections(soup: BeautifulSoup) -> List[Dict]:
    conditional = []
    
    for elem in soup.find_all(['div', 'section', 'fieldset']):
        is_conditional = False
        condition_type = None
        
        if elem.get('aria-hidden') == 'true':
            is_conditional = True
            condition_type = 'aria-hidden'
        
        style = elem.get('style', '')
        if 'display:none' in style.replace(' ', '') or 'display: none' in style:
            is_conditional = True
            condition_type = 'display:none'
        
        classes = elem.get('class', [])
        if any(c in ['hidden', 'disabled', 'collapsed'] for c in classes):
            is_conditional = True
            condition_type = 'css-class'
        
        if is_conditional:
            conditional.append({
                "id": elem.get('id', ''),
                "tag": elem.name,
                "condition_type": condition_type,
                "class": ' '.join(classes),
                "contains_inputs": len(elem.find_all(['input', 'select', 'button'])) > 0
            })
    
    return conditional


def extract_dynamic_elements(soup: BeautifulSoup) -> List[Dict]:
    dynamic = []
    
    for elem in soup.find_all(attrs={'aria-live': True}):
        dynamic.append({
            "id": elem.get('id', ''),
            "tag": elem.name,
            "aria_live": elem.get('aria-live'),
            "role": elem.get('role', ''),
            "class": ' '.join(elem.get('class', [])),
            "initial_content": elem.text.strip()[:100]
        })
    
    return dynamic


def extract_error_elements(soup: BeautifulSoup) -> List[Dict]:
    errors = []
    
    for elem in soup.find_all(['div', 'span', 'p']):
        classes = elem.get('class', [])
        role = elem.get('role', '')
        
        if 'error' in classes or role == 'alert':
            errors.append({
                "id": elem.get('id', ''),
                "tag": elem.name,
                "class": ' '.join(classes),
                "role": role,
                "initially_visible": 'display:none' not in elem.get('style', '') and 'display: none' not in elem.get('style', '')
            })
    
    return errors


def extract_success_elements(soup: BeautifulSoup) -> List[Dict]:
    success = []
    
    for elem in soup.find_all(['div', 'span', 'p']):
        classes = elem.get('class', [])
        
        if any(c in ['success', 'confirmation', 'alert-success'] for c in classes):
            success.append({
                "id": elem.get('id', ''),
                "tag": elem.name,
                "class": ' '.join(classes),
                "role": elem.get('role', ''),
                "text_content": elem.text.strip(),
                "initially_visible": 'display:none' not in elem.get('style', '') and 'display: none' not in elem.get('style', '')
            })
    
    return success


def analyze_page_behavior(soup: BeautifulSoup) -> Dict:
    analysis = {
        "required_fields": [],
        "disabled_buttons": [],
        "conditional_logic": [],
        "validation_indicators": []
    }
    
    for elem in soup.find_all(['input', 'select', 'textarea'], required=True):
        analysis['required_fields'].append({
            "id": elem.get('id', ''),
            "name": elem.get('name', ''),
            "type": elem.get('type', elem.name)
        })
    
    for label in soup.find_all('label'):
        if '*' in label.text:
            analysis['required_fields'].append({
                "label_for": label.get('for', ''),
                "label_text": label.text.strip()
            })
    
    for button in soup.find_all(['button', 'input'], disabled=True):
        if button.name == 'input' and button.get('type') not in ['submit', 'button']:
            continue
        analysis['disabled_buttons'].append({
            "id": button.get('id', ''),
            "text": button.text.strip() if button.name == 'button' else button.get('value', ''),
            "type": button.get('type', 'button')
        })
    
    for elem in soup.find_all(attrs={'aria-hidden': 'true'}):
        if elem.get('id'):
            analysis['conditional_logic'].append({
                "section_id": elem.get('id'),
                "initially_hidden": True,
                "trigger": "unknown (requires JS analysis)"
            })
    
    return analysis


def format_html_structure_for_context(html_structure: Dict) -> str:
    context_parts = []
    
    context_parts.append("=== HTML PAGE STRUCTURE ===\n")
    context_parts.append(f"Page Title: {html_structure['page_title']}\n\n")
    
    if html_structure['forms']:
        context_parts.append("=== FORMS ===\n")
        for form in html_structure['forms']:
            context_parts.append(f"\nForm: {form['id']} (Method: {form['method']}, Action: {form['action']})\n")
            context_parts.append("Fields:\n")
            for field in form['fields']:
                if field['tag'] == 'button':
                    context_parts.append(f"  - Button: {field['text']} (id={field['id']}, type={field['type']})\n")
                elif field['tag'] == 'select':
                    context_parts.append(f"  - Select: {field['name']} (id={field['id']}, options: {len(field.get('options', []))})\n")
                else:
                    context_parts.append(f"  - {field['type']}: {field['name']} (id={field['id']}, placeholder='{field['placeholder']}')\n")
    
    standalone_buttons = [b for b in html_structure['buttons'] if b['id'] or b['text']]
    if standalone_buttons:
        context_parts.append("\n=== STANDALONE BUTTONS ===\n")
        for button in standalone_buttons:
            context_parts.append(f"  - {button['text']} (id={button['id']}, class={button['class']})\n")

    if html_structure['interactive_elements']:
        context_parts.append("\n=== INTERACTIVE ELEMENTS ===\n")
        for elem in html_structure['interactive_elements'][:10]:  
            context_parts.append(f"  - {elem['tag']} (id={elem['id']}, text='{elem['text']}')\n")
    
    if html_structure.get('checkboxes'):
        context_parts.append("\n=== CHECKBOXES ===\n")
        for cb in html_structure['checkboxes']:
            status = []
            if cb['required']:
                status.append("REQUIRED")
            if cb['checked']:
                status.append("checked")
            context_parts.append(f"  - {cb['label']} (id={cb['id']}, {', '.join(status)})\n")
    
    if html_structure.get('radio_groups'):
        context_parts.append("\n=== RADIO GROUPS ===\n")
        for rg in html_structure['radio_groups']:
            context_parts.append(f"  - {rg['name']} ({'REQUIRED' if rg['required'] else 'optional'}):\n")
            for opt in rg['options']:
                context_parts.append(f"      * {opt['label']} (value={opt['value']})\n")
    
    if html_structure.get('conditional_sections'):
        context_parts.append("\n=== CONDITIONAL SECTIONS ===\n")
        for cs in html_structure['conditional_sections']:
            context_parts.append(f"  - {cs['id']} ({cs['condition_type']}, contains_inputs={cs['contains_inputs']})\n")
    
    if html_structure.get('dynamic_elements'):
        context_parts.append("\n=== DYNAMIC ELEMENTS (aria-live) ===\n")
        for de in html_structure['dynamic_elements']:
            context_parts.append(f"  - {de['id']} (role={de['role']}, aria-live={de['aria_live']})\n")
    
    if html_structure.get('success_elements'):
        context_parts.append("\n=== SUCCESS/CONFIRMATION ELEMENTS ===\n")
        for se in html_structure['success_elements']:
            context_parts.append(f"  - {se['id']} (class={se['class']}, initially_visible={se['initially_visible']})\n")
            if se['text_content']:
                context_parts.append(f"      Content: {se['text_content'][:50]}\n")
    
    if html_structure.get('error_elements'):
        context_parts.append("\n=== ERROR ELEMENTS ===\n")
        for ee in html_structure['error_elements']:
            context_parts.append(f"  - {ee['id']} (class={ee['class']}, role={ee['role']})\n")
    
    behavior = html_structure.get('behavior_analysis', {})
    if behavior.get('required_fields'):
        context_parts.append("\n=== REQUIRED FIELDS ===\n")
        for rf in behavior['required_fields']:
            if rf.get('id'):
                context_parts.append(f"  - {rf['name']} (id={rf['id']}, type={rf['type']})\n")
            elif rf.get('label_text'):
                context_parts.append(f"  - {rf['label_text']} (label_for={rf['label_for']})\n")
    
    if behavior.get('disabled_buttons'):
        context_parts.append("\n=== INITIALLY DISABLED BUTTONS ===\n")
        for db in behavior['disabled_buttons']:
            context_parts.append(f"  - {db['text']} (id={db['id']}, type={db['type']}) - WAITS FOR VALIDATION\n")
    
    if behavior.get('conditional_logic'):
        context_parts.append("\n=== CONDITIONAL LOGIC ===\n")
        for cl in behavior['conditional_logic']:
                context_parts.append(f"  - Section {cl['section_id']} (initially_hidden={cl['initially_hidden']})\n")
    
    if html_structure['validation_attributes']:
        context_parts.append("\n=== VALIDATION RULES ===\n")
        for val in html_structure['validation_attributes']:
            rules = []
            if val['required']:
                rules.append("required")
            if val['pattern']:
                rules.append(f"pattern={val['pattern']}")
            if val['minlength']:
                rules.append(f"minlength={val['minlength']}")
            if val['maxlength']:
                rules.append(f"maxlength={val['maxlength']}")
            context_parts.append(f"  - {val['name']} ({val['type']}): {', '.join(rules)}\n")
    
    return ''.join(context_parts)
