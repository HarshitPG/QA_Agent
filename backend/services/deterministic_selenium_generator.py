import re
from typing import Dict, List, Any
from datetime import datetime
import logging
import numpy as np
import random
from backend.services.embedding_service import get_embedding_model
from backend.services.config_semantic import THRESHOLDS, TEST_DATA_PATTERNS, NEGATIVE_ACTIONS
from backend.services.semantic_matcher import get_semantic_matcher
from backend.services.document_intelligence import get_document_intelligence

logger = logging.getLogger(__name__)


class DeterministicSeleniumGenerator:
    
    def __init__(self, html_structure: Dict, framework: str = "pytest", browser: str = "chrome"):
        self.html_structure = html_structure
        self.framework = framework
        self.browser = browser
        self.page_title = html_structure.get('page_title', 'Page')
        self.semantic_matcher = get_semantic_matcher()
        self.doc_intelligence = get_document_intelligence()
        
    def generate_complete_script(self, test_cases: List[Dict], page_url: str = None) -> str:
        
        imports = self._generate_imports()
        page_class = self._generate_page_class()
        fixture = self._generate_fixture()
        tests = self._generate_tests(test_cases, page_url)
        main_block = self._generate_main_block()
        
        script_parts = [
            f"# Selenium Test Script for {self.page_title}",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            imports,
            "",
            page_class,
            "",
            fixture,
            "",
            tests,
            "",
            main_block
        ]
        
        return "\n".join(script_parts)
    
    def _generate_imports(self) -> str:
        imports = [
            "from selenium import webdriver",
            "from selenium.webdriver.common.by import By",
            "from selenium.webdriver.support.ui import WebDriverWait",
            "from selenium.webdriver.support import expected_conditions as EC",
            "from selenium.webdriver.support.ui import Select",
        ]
        
        if self.framework == "pytest":
            imports.append("import pytest")
        else:
            imports.append("import unittest")
        
        return "\n".join(imports)
    
    def _generate_page_class(self) -> str:
        class_name = "Page"
        locators = self._generate_locators()
        methods = self._generate_page_methods()
        
        page_class = [
            f"class {class_name}:",
            "    def __init__(self, driver):",
            "        self.driver = driver",
            "        self.wait = WebDriverWait(driver, 10)",
        ]
        
        for locator in locators:
            page_class.append(f"        {locator}")
        page_class.append("")
        
        for method in methods:
            page_class.extend(method)
            page_class.append("")
        
        return "\n".join(page_class)
    
    def _generate_locators(self) -> List[str]:
        locators = []
        seen = set()
        
        
        for select in self.html_structure.get('selects', []):
            if select.get('id') and select['id'] not in seen:
                field_name = select['id'].replace('-', '_')
                locators.append(f"self.{field_name} = (By.ID, '{select['id']}')")
                seen.add(select['id'])
        
        
        for inp in self.html_structure.get('inputs', []):
            if inp.get('id') and inp['id'] not in seen:
                field_name = inp['id'].replace('-', '_')
                locators.append(f"self.{field_name} = (By.ID, '{inp['id']}')")
                seen.add(inp['id'])
        
        
        for cb in self.html_structure.get('checkboxes', []):
            if cb.get('id') and cb['id'] not in seen:
                field_name = cb['id'].replace('-', '_')
                locators.append(f"self.{field_name} = (By.ID, '{cb['id']}')")
                seen.add(cb['id'])
        
        
        for rg in self.html_structure.get('radio_groups', []):
            name = rg.get('name')
            if name and name not in seen and rg.get('options'):
                field_name = name.replace('-', '_')
                
                locators.append(f"self.{field_name} = (By.NAME, '{name}')")
                seen.add(name)
        
        
        for btn in self.html_structure.get('buttons', []):
            if btn.get('id') and btn['id'] not in seen:
                field_name = btn['id'].replace('-', '_')
                locators.append(f"self.{field_name} = (By.ID, '{btn['id']}')")
                seen.add(btn['id'])
        
        
        for elem in self.html_structure.get('success_elements', []):
            if elem.get('id') and elem['id'] not in seen:
                field_name = elem['id'].replace('-', '_')
                locators.append(f"self.{field_name} = (By.ID, '{elem['id']}')")
                seen.add(elem['id'])
        
        
        for elem in self.html_structure.get('dynamic_elements', []):
            if elem.get('id') and elem['id'] not in seen:
                field_name = elem['id'].replace('-', '_')
                locators.append(f"self.{field_name} = (By.ID, '{elem['id']}')")
                seen.add(elem['id'])
        
        return locators
    
    def _generate_page_methods(self) -> List[List[str]]:
        methods = []
        
        if self.html_structure.get('inputs'):
            methods.append(self._method_fill_input_field())
        
        if self.html_structure.get('selects'):
            methods.append(self._method_select_dropdown_option())
        
        if self.html_structure.get('checkboxes'):
            methods.append(self._method_check_checkbox())
        
        if self.html_structure.get('radio_buttons') or any(inp.get('type') == 'radio' for inp in self.html_structure.get('inputs', [])):
            methods.append(self._method_select_radio())
        
        if self.html_structure.get('buttons'):
            methods.append(self._method_click_button())
            methods.append(self._method_click_button_by_text())
            methods.append(self._method_click_button_by_class())
            methods.append(self._method_click_button_by_onclick())

            submit_btn = next((b for b in self.html_structure.get('buttons', []) 
                              if b.get('type') == 'submit'), None)
            if submit_btn:
                methods.append(self._method_wait_button_enabled())
        
        
        if self.html_structure.get('success_elements') or self.html_structure.get('dynamic_elements'):
            methods.append(self._method_get_element_text())
        
        methods.append(self._method_wait_for_element())
        
        return methods
    
    def _method_fill_input_field(self) -> List[str]:

        return [
            "    def fill_input_field(self, field_id: str, value: str):",
            "        \"\"\"Fill any text input field (text/email/tel/number) by its ID\"\"\"",
            "        field = self.driver.find_element(By.ID, field_id)",
            "        field.clear()",
            "        field.send_keys(value)"
        ]
    
    def _method_select_dropdown_option(self) -> List[str]:
        return [
            "    def select_dropdown_option(self, field_id: str, option_text: str):",
            "        \"\"\"Select option from dropdown by visible text\"\"\"",
            "        select = Select(self.driver.find_element(By.ID, field_id))",
            "        select.select_by_visible_text(option_text)"
        ]
    
    def _method_check_checkbox(self) -> List[str]:
        return [
            "    def check_checkbox(self, field_id: str):",
            "        \"\"\"Check a checkbox by its ID\"\"\"",
            "        checkbox = self.driver.find_element(By.ID, field_id)",
            "        if not checkbox.is_selected():",
            "            checkbox.click()"
        ]
    
    def _method_select_radio(self) -> List[str]:
        return [
            "    def select_radio(self, radio_id: str):",
            "        \"\"\"Select a radio button by its ID\"\"\"",
            "        radio = self.driver.find_element(By.ID, radio_id)",
            "        if not radio.is_selected():",
            "            radio.click()"
        ]
    
    def _method_click_button(self) -> List[str]:
        return [
            "    def click_button(self, button_id: str):",
            "        \"\"\"Click any button by its ID\"\"\"",
            "        self.driver.find_element(By.ID, button_id).click()"
        ]
    
    def _method_wait_button_enabled(self) -> List[str]:
        return [
            "    def wait_button_enabled(self, button_id: str, timeout: int = 10):",
            "        \"\"\"Wait for button to become enabled (for JS validation)\"\"\"",
            "        WebDriverWait(self.driver, timeout).until(",
            "            lambda d: d.find_element(By.ID, button_id).is_enabled()",
            "        )"
        ]
    
    def _method_click_button_by_text(self) -> List[str]:
        return [
            "    def click_button_by_text(self, button_text: str):",
            "        \"\"\"Click button by its visible text\"\"\"",
            "        self.driver.find_element(By.XPATH, f\"//button[contains(text(), '{button_text}')]\").click()"
        ]
    
    def _method_click_button_by_class(self) -> List[str]:
        return [
            "    def click_button_by_class(self, class_name: str):",
            "        \"\"\"Click first button with given class name\"\"\"",
            "        self.driver.find_element(By.CLASS_NAME, class_name).click()"
        ]
    
    def _method_click_button_by_onclick(self) -> List[str]:
        return [
            "    def click_button_by_onclick(self, onclick_text: str):",
            "        \"\"\"Click button whose onclick attribute contains the given text\"\"\"",
            "        self.driver.find_element(By.XPATH, f\"//button[contains(@onclick, '{onclick_text}')]\").click()"
        ]
    
    def _method_get_element_text(self) -> List[str]:
        return [
            "    def get_element_text(self, element_id: str, wait: bool = True):",
            "        \"\"\"Get text content from any element by ID\"\"\"",
            "        if wait:",
            "            self.wait.until(EC.visibility_of_element_located((By.ID, element_id)))",
            "        return self.driver.find_element(By.ID, element_id).text"
        ]
    
    def _method_wait_for_element(self) -> List[str]:
        return [
            "    def wait_for_element(self, element_id: str, timeout: int = 10):",
            "        \"\"\"Wait for element to be visible\"\"\"",
            "        WebDriverWait(self.driver, timeout).until(",
            "            EC.visibility_of_element_located((By.ID, element_id))",
            "        )"
        ]

    
    def _generate_fixture(self) -> str:
        if self.framework == "pytest":
            return """@pytest.fixture(scope='module')
def driver():
    \"\"\"Create and configure WebDriver instance\"\"\"
    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.implicitly_wait(5)
    yield driver
    driver.quit()"""
        else:
            return """class TestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = webdriver.Chrome()
        cls.driver.maximize_window()
        cls.driver.implicitly_wait(5)
    
    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()"""
    
    def _generate_tests(self, test_cases: List[Dict], page_url: str = None) -> str:
        tests = []
        
        for idx, tc in enumerate(test_cases, 1):
            test_id = tc.get('test_id', f'TC-{idx:03d}').replace('-', '_').lower()
            test_name = f"test_{test_id}"
            
            if self.framework == "pytest":
                tests.append(self._generate_pytest_test(tc, test_name, page_url))
            else:
                tests.append(self._generate_unittest_test(tc, test_name, page_url))
        
        return "\n\n".join(tests)
    
    def _generate_pytest_test(self, test_case: Dict, test_name: str, page_url: str) -> str:
        scenario = test_case.get('test_scenario', 'Test scenario')
        steps = test_case.get('test_steps') or test_case.get('steps', [])
        
        if not isinstance(steps, list):
            steps = []
        
        
        
        url = page_url if page_url else "file:///path/to/page.html"
        url = page_url if page_url else "file:///path/to/page.html"
        
        test = [
            f"def {test_name}(driver):",
            f'    """',
            f'    {scenario}',
            f'    Test ID: {test_case.get("test_id", "Unknown")}',
            f'    Priority: {test_case.get("priority", "medium")}',
            f'    """',
            "    page = Page(driver)",
            f"    driver.get('{url}')",
            ""
        ]
        
        test_body = self._generate_test_body_from_steps(steps, test_case)
        test.extend(test_body)
        
        return "\n".join(test)
    
    def _generate_unittest_test(self, test_case: Dict, test_name: str, page_url: str) -> str:
        scenario = test_case.get('test_scenario', 'Test scenario')
        steps = test_case.get('test_steps') or test_case.get('steps', [])
        
        if not isinstance(steps, list):
            steps = []
        
        url = page_url if page_url else "file:///path/to/page.html"
        
        test = [
            f"    def {test_name}(self):",
            f'        """',
            f'        {scenario}',
            f'        """',
            "        page = Page(self.driver)",
            f"        self.driver.get('{url}')",
            ""
        ]
        
        test_body = self._generate_test_body_from_steps(steps, test_case)
        test.extend(["        " + line if line else "" for line in test_body])
        
        return "\n".join(test)
    
    def _generate_test_body_from_steps(self, steps: List[str], test_case: Dict) -> List[str]:
        body = []
        
        normalized_steps = []
        for step in steps:
            if isinstance(step, str):
                normalized_steps.append(step)
            elif isinstance(step, dict):
                normalized_steps.append(step.get('description', str(step)))
            else:
                normalized_steps.append(str(step))

        from backend.services.llm_service.generators import generate_step_actions

        element_inventory = self._build_element_inventory()

        try:
            action_mapping = generate_step_actions(normalized_steps, element_inventory, test_case)
            if action_mapping and len(action_mapping) > 0:
                for action in action_mapping:
                    self._generate_action_code(action, body)
            else:
                logger.warning("LLM returned empty actions, using fallback")
                body = self._generate_generic_fallback(normalized_steps)

        except Exception as e:
            logger.error(f"LLM mapping failed: {e}, falling back to generic approach")
            body = self._generate_generic_fallback(normalized_steps)

        body.extend(self._generate_final_verification())
        
        return body
    
    def _build_element_inventory(self) -> Dict:
        inventory = {
            "text_inputs": [],
            "dropdowns": [],
            "checkboxes": [],
            "buttons": [],
            "dynamic_elements": []
        }

        for inp in self.html_structure.get('inputs', []):
            inventory["text_inputs"].append({
                "id": inp.get('id'),
                "type": inp.get('type'),
                "name": inp.get('name'),
                "placeholder": inp.get('placeholder', '')
            })
        
        for sel in self.html_structure.get('selects', []):
            inventory["dropdowns"].append({
                "id": sel.get('id'),
                "options": sel.get('options', [])
            })
        
        for cb in self.html_structure.get('checkboxes', []):
            inventory["checkboxes"].append({
                "id": cb.get('id'),
                "label": cb.get('label', '')
            })
        
        for btn in self.html_structure.get('buttons', []):
            inventory["buttons"].append({
                "id": btn.get('id'),
                "type": btn.get('type'),
                "text": btn.get('text', '')
            })
        
        for elem in self.html_structure.get('dynamic_elements', []):
            inventory["dynamic_elements"].append({
                "id": elem.get('id'),
                "purpose": elem.get('purpose', '')
            })
        
        return inventory
    
    def _generate_action_code(self, action: Dict, body: List[str]):
        action_type = action.get('type')
        comment = action.get('comment', '')
        
        if comment:
            body.append(f"    # {comment}")
        
        if action_type == 'fill_input':
            field_id = action['field_id']
            value = action['value']
            body.append(f"    page.fill_input_field('{field_id}', '{value}')")
            
        elif action_type == 'select_dropdown':
            field_id = action['field_id']
            option = action['option']
            body.append(f"    page.select_dropdown_option('{field_id}', '{option}')")
            
        elif action_type == 'check_checkbox':
            field_id = action['field_id']
            body.append(f"    page.check_checkbox('{field_id}')")
            
        elif action_type == 'click_button':
            button_id = action['button_id']
            if action.get('wait_enabled'):
                body.append(f"    page.wait_button_enabled('{button_id}')")
            body.append(f"    page.click_button('{button_id}')")
            
        elif action_type == 'wait_and_verify':
            element_id = action['element_id']
            expected_text = action.get('expected_text')
            body.append(f"    page.wait_for_element('{element_id}')")
            if expected_text:
                body.append(f"    result = page.get_element_text('{element_id}')")
                body.append(f"    assert '{expected_text}' in result, f'Expected \"{expected_text}\", got: {{result}}'")
        
        body.append("")
    
    def _generate_generic_fallback(self, steps: List[str]) -> List[str]:
        body = []
        
        if not steps or not isinstance(steps, list):
            steps = []
        

        normalized_steps = []
        for step in steps:
            if isinstance(step, str):
                normalized_steps.append(step)
            elif isinstance(step, dict):
                normalized_steps.append(step.get('description', str(step)))
            else:
                normalized_steps.append(str(step))
        

        filled_fields = set()
        
        for step in normalized_steps:

            clean_step = re.sub(r'^\d+\.?\s*', '', step)
            step_lower = clean_step.lower()
            explicit_id = re.search(r"id\s*[=:\s]\s*['\"]([^'\"]+)['\"]", clean_step, re.IGNORECASE)
            explicit_class = re.search(r"class\s*[=:\s]\s*['\"]([^'\"]+)['\"]", clean_step, re.IGNORECASE)
            explicit_name = re.search(r"name\s*[=:\s]\s*['\"]([^'\"]+)['\"]", clean_step, re.IGNORECASE)

            numeric_matches = re.findall(r'\d+', clean_step)
            
            matched = False
            

            
            is_verification, verification_confidence = self.semantic_matcher.is_verification_step(clean_step)
            if is_verification and verification_confidence > 0.30: 
                logger.info(f"Verification step detected: '{clean_step}' (confidence: {verification_confidence:.3f})")
                body.append(f"    # VERIFICATION: {clean_step}")
                body.append(f"    # TODO: Implement assertion for this verification step")
                body.append("")
                matched = True
                continue
            
            
            
            is_select_action, select_confidence = self.semantic_matcher.match_select_action(step_lower)
            if is_select_action:
                logger.debug(f"Select action detected: '{clean_step}' (confidence: {select_confidence:.3f})")
                for sel in self.html_structure.get('selects', []):
                    sel_id = sel.get('id', '')
                    if not sel_id or sel_id in filled_fields:
                        continue
                    
                    options = sel.get('options', [])
                    normalized_options = []
                    for opt in options:
                        if isinstance(opt, str):
                            normalized_options.append(opt)
                        elif isinstance(opt, dict):
                            normalized_options.append(opt.get('text', opt.get('value', str(opt))))
                        else:
                            normalized_options.append(str(opt))
                    
                    id_match = sel_id.lower() in step_lower or sel.get('name', '').lower() in step_lower
                    option_match = any(opt.lower() in step_lower for opt in normalized_options if opt)
                    explicit_id_match = explicit_id and explicit_id.group(1).lower() == sel_id.lower()

                    if explicit_id_match or id_match or option_match:
                        selected_option = None
                        for opt in normalized_options:
                            if opt and opt.lower() in step_lower:
                                selected_option = opt
                                break

                        if not selected_option:
                            selected_option = normalized_options[0] if normalized_options else ''

                        body.append(f"     # {clean_step}")
                        body.append(f"    page.select_dropdown_option('{sel_id}', '{selected_option}')")
                        body.append("")
                        filled_fields.add(sel_id)
                        matched = True
                        break
            
            if matched:
                continue
            
            for sel in self.html_structure.get('selects', []):
                sel_id = sel.get('id', '')
                if not sel_id or sel_id in filled_fields:
                    continue

                options = sel.get('options', [])
                normalized_options = []
                for opt in options:
                    if isinstance(opt, str):
                        normalized_options.append(opt)
                    elif isinstance(opt, dict):
                        normalized_options.append(opt.get('text', opt.get('value', str(opt))))
                    else:
                        normalized_options.append(str(opt))

                id_match = sel_id.lower() in step_lower or sel.get('name', '').lower() in step_lower
                option_match = any(opt.lower() in step_lower for opt in normalized_options if opt)

                if id_match or option_match:
                    selected_option = None
                    for opt in normalized_options:
                        if opt and opt.lower() in step_lower:
                            selected_option = opt
                            break

                    if not selected_option:
                        selected_option = normalized_options[0] if normalized_options else ''

                    body.append(f"     # {clean_step}")
                    body.append(f"    page.select_dropdown_option('{sel_id}', '{selected_option}')")
                    body.append("")
                    filled_fields.add(sel_id)
                    matched = True
                    break
            
            if matched:
                continue
            
            for cb in self.html_structure.get('checkboxes', []):
                cb_id = cb.get('id', '')
                if not cb_id or cb_id in filled_fields:
                    continue
                
                label = cb.get('label', '')
                id_match = cb_id.lower() in step_lower
                label_match = label and any(word.lower() in step_lower for word in label.split() if len(word) > 3)
                
                from backend.services.semantic_matcher import get_semantic_matcher
                semantic_matcher = get_semantic_matcher()
                checkbox_attrs = {
                    'label': label,
                    'id': cb_id,
                    'name': cb.get('name', '')
                }
                purpose, purpose_score = semantic_matcher.match_checkbox_purpose(checkbox_attrs)
                semantic_match = purpose_score > THRESHOLDS['checkbox_match'] and cb_id.lower() in step_lower
                
                if id_match or label_match or semantic_match:
                    body.append(f"    # {clean_step}")
                    body.append(f"    page.check_checkbox('{cb_id}')")
                    body.append("")
                    filled_fields.add(cb_id)
                    matched = True
                    break
            
            if matched:
                continue
            
            for inp in self.html_structure.get('inputs', []):
                inp_id = inp.get('id', '')
                inp_name = inp.get('name', '')
                inp_type = inp.get('type', 'text')
                

                if inp_type in ['checkbox', 'radio']:
                    continue
                
                if not inp_id or inp_id in filled_fields:
                    continue

                id_match = inp_id.lower() in step_lower
                name_match = inp_name and inp_name.lower() in step_lower
                
                if id_match or name_match:
                    input_type = inp.get('type', 'text')
                    value = None

                    if input_type == 'number' and numeric_matches:
                        value = numeric_matches[0]  
                    elif input_type == 'email':
                        value = TEST_DATA_PATTERNS['email'].replace('{random}', str(random.randint(100, 999)))
                    elif input_type == 'tel' or 'phone' in inp_id.lower():
                        value = TEST_DATA_PATTERNS['phone'].replace('{random:7}', ''.join([str(random.randint(0, 9)) for _ in range(7)]))
                    elif 'zip' in inp_id.lower() or 'postal' in inp_id.lower():
                        value = TEST_DATA_PATTERNS['zip'].replace('{random:5}', ''.join([str(random.randint(0, 9)) for _ in range(5)]))
                    elif 'date' in input_type:
                        value = TEST_DATA_PATTERNS['date'].format(month=random.randint(1, 12), day=random.randint(1, 28))
                    elif 'search' in inp_id.lower():
                        search_match = re.search(r'search for (.+?)(?:\s|$)', step_lower)
                        value = search_match.group(1) if search_match else 'test'
                    else:
                        from backend.services.semantic_matcher import get_semantic_matcher
                        semantic_matcher = get_semantic_matcher()
                        input_attrs = {
                            'placeholder': inp.get('placeholder', ''),
                            'id': inp_id,
                            'name': inp_name,
                            'type': input_type
                        }
                        purpose, purpose_score = semantic_matcher.detect_input_purpose(input_attrs)
                        
                        if purpose == 'promo' and purpose_score > 0.5:
                            doc_value, doc_confidence = self.doc_intelligence.extract_valid_input_value('promo', inp_id, input_attrs)
                            
                            if doc_value and doc_confidence > 0.7:
                                value = doc_value
                                logger.info(f"Using document-extracted promo code: {value} (confidence: {doc_confidence:.2f})")
                            else:
                                code_match = re.search(r'\b([A-Z0-9]{4,})\b', clean_step)
                                value = code_match.group(1) if code_match else TEST_DATA_PATTERNS['coupon'].replace('{random:4}', ''.join([str(random.randint(0, 9)) for _ in range(4)]))
                                logger.warning(f"Using generated promo code: {value} (no valid code found in documents)")
                        elif input_type == 'password':
                            value = TEST_DATA_PATTERNS['password'].replace('{random:3}', str(random.randint(100, 999)))
                        else:
                            value = TEST_DATA_PATTERNS['generic_text']
                    
                    body.append(f"    # {clean_step}")
                    body.append(f"    page.fill_input_field('{inp_id}', '{value}')")
                    
                    from backend.services.semantic_matcher import get_semantic_matcher
                    semantic_matcher = get_semantic_matcher()
                    input_attrs = {'id': inp_id, 'name': inp_name, 'placeholder': inp.get('placeholder', '')}
                    purpose, purpose_score = semantic_matcher.detect_input_purpose(input_attrs)
                    
                    if purpose == 'promo' and purpose_score > 0.5:
                        apply_btn = next((b for b in self.html_structure.get('buttons', [])
                                         if any(kw in b.get('id', '').lower() or kw in b.get('text', '').lower() 
                                               for kw in ['apply', 'submit', 'validate'])), None)
                        if apply_btn and apply_btn.get('id'):
                            body.append(f"    page.click_button('{apply_btn['id']}')")
                            result_elem = next((d for d in self.html_structure.get('dynamic_elements', [])
                                              if any(kw in d.get('id', '').lower() for kw in ['result', 'message', 'status'])), None)
                            if result_elem:
                                body.append(f"    page.wait_for_element('{result_elem['id']}')")
                    
                    body.append("")
                    filled_fields.add(inp_id)
                    matched = True
                    break
            
            if matched:
                continue
            
            for inp in self.html_structure.get('inputs', []):
                if inp.get('type') != 'radio':
                    continue
                    
                radio_id = inp.get('id', '')
                radio_name = inp.get('name', '')
                radio_value = inp.get('value', '')
                
                if not radio_id or radio_id in filled_fields:
                    continue

                id_match = radio_id.lower() in step_lower
                value_match = radio_value and radio_value.lower() in step_lower
                name_match = radio_name and radio_name.lower() in step_lower
                
                from backend.services.semantic_matcher import get_semantic_matcher
                semantic_matcher = get_semantic_matcher()
                radio_options = [{'id': radio_id, 'value': radio_value, 'name': radio_name}]
                matched_id = semantic_matcher.match_radio_option_intent(step, radio_options)
                semantic_match = matched_id == radio_id
                
                if id_match or value_match or semantic_match:
                    body.append(f"    # {clean_step}")
                    body.append(f"    page.select_radio('{radio_id}')")
                    body.append("")
                    filled_fields.add(radio_id)
                    matched = True
                    break
            
            if matched:
                continue
            
            is_button_action, action_confidence = self.semantic_matcher.match_button_action(step_lower)
            if is_button_action:
                logger.debug(f"Button action detected: '{clean_step}' (confidence: {action_confidence:.3f})")
                target_class = explicit_class.group(1) if explicit_class else None
                target_id = explicit_id.group(1) if explicit_id else None
                product_id_match = re.search(r'\b(P\d{3})\b', clean_step, re.IGNORECASE)
                product_id = product_id_match.group(1) if product_id_match else None
                
                for btn in self.html_structure.get('buttons', []):
                    btn_id = btn.get('id', '')
                    btn_text = btn.get('text', '')
                    btn_class = btn.get('class', '')
                    btn_onclick = btn.get('onclick', '')
                    
                    if btn_id and btn_id in filled_fields:
                        continue
                    
                    explicit_id_match = target_id and btn_id and target_id.lower() == btn_id.lower()
                    explicit_class_match = target_class and btn_class and target_class.lower() in btn_class.lower()
                    onclick_product_match = product_id and btn_onclick and product_id.upper() in btn_onclick.upper()
                    id_match = not target_id and btn_id and btn_id.lower() in step_lower
                    text_match = btn_text and btn_text.lower() in step_lower
                    class_match = not target_class and btn_class and any(cls.lower() in step_lower for cls in btn_class.split())
                    
                    if explicit_id_match or explicit_class_match or onclick_product_match or id_match or text_match or class_match:
                        body.append(f"    # {clean_step}")

                        if btn_id:
                            body.append(f"    page.click_button('{btn_id}')")
                            filled_fields.add(btn_id)
                        elif onclick_product_match and product_id:
                            body.append(f"    page.click_button_by_onclick('{product_id}')")
                        elif explicit_class_match or (target_class and btn_class):
                            use_class = target_class if target_class else btn_class.split()[0]
                            body.append(f"    page.click_button_by_class('{use_class}')")
                        elif btn_text:
                            body.append(f"    page.click_button_by_text('{btn_text}')")
                        elif btn_class:  
                            first_class = btn_class.split()[0]
                            body.append(f"    page.click_button_by_class('{first_class}')")
                        
                        body.append("")
                        matched = True
                        break
            
            if matched:
                continue

            candidates = []
            
            for inp in self.html_structure.get('inputs', []):
                if inp.get('id') and inp['id'] not in filled_fields:
                    c = inp.copy()
                    c['tag'] = 'input'
                    candidates.append(c)

            for btn in self.html_structure.get('buttons', []):
                if btn.get('id') and btn['id'] in filled_fields:
                    continue
                c = btn.copy()
                c['tag'] = 'button'
                candidates.append(c)
                

            for sel in self.html_structure.get('selects', []):
                if sel.get('id') and sel['id'] not in filled_fields:
                    c = sel.copy()
                    c['tag'] = 'select'
                    candidates.append(c)
            
            semantic_match = self._find_semantic_match(step_lower, candidates, threshold=THRESHOLDS['semantic_match'])
            
            if semantic_match:
                tag = semantic_match.get('tag')
                elem_id = semantic_match.get('id')
                
                body.append(f"    # {clean_step} (Semantic Match: {tag} {elem_id or semantic_match.get('text', 'N/A')})")
                
                if tag == 'button':
                    if elem_id:
                        body.append(f"    page.click_button('{elem_id}')")
                        filled_fields.add(elem_id)
                    elif semantic_match.get('text'):
                        body.append(f"    page.click_button_by_text('{semantic_match['text']}')")
                    elif semantic_match.get('class'):
                        cls = semantic_match['class'].split()[0]
                        body.append(f"    page.click_button_by_class('{cls}')")
                    elif semantic_match.get('onclick'):
                        pid_match = re.search(r'\b(P\d{3})\b', semantic_match['onclick'], re.IGNORECASE)
                        if pid_match:
                            body.append(f"    page.click_button_by_onclick('{pid_match.group(1)}')")
                        
                elif tag == 'input':
                    val = TEST_DATA_PATTERNS['generic_text']
                    inp_type = semantic_match.get('type', 'text')
                    if inp_type == 'email': 
                        val = TEST_DATA_PATTERNS['email'].replace('{random}', str(random.randint(100, 999)))
                    elif inp_type == 'number': val = '1'
                    elif inp_type == 'tel': 
                        val = TEST_DATA_PATTERNS['phone'].replace('{random:7}', ''.join([str(random.randint(0, 9)) for _ in range(7)]))
                    
                    body.append(f"    page.fill_input_field('{elem_id}', '{val}')")
                    filled_fields.add(elem_id)
                    
                elif tag == 'select':
                    opts = semantic_match.get('options', [])
                    val = opts[0] if opts else ''
                    if isinstance(val, dict): val = val.get('value', '')
                    
                    body.append(f"    page.select_dropdown_option('{elem_id}', '{val}')")
                    filled_fields.add(elem_id)
                
                body.append("")
                matched = True
            
            if matched:
                continue
            
            final_action_similarity = self._is_final_action_step(step_lower)
            if final_action_similarity > THRESHOLDS['final_action']:  
                for inp in self.html_structure.get('inputs', []):
                    if inp.get('id') and inp['id'] not in filled_fields:
                        inp_type = inp.get('type', 'text')
                        if inp_type in ['text', 'email', 'tel', 'number']:
                            if inp_type == 'email':
                                val = TEST_DATA_PATTERNS['email'].replace('{random}', str(random.randint(100, 999)))
                            elif inp_type == 'tel':
                                val = TEST_DATA_PATTERNS['phone'].replace('{random:7}', ''.join([str(random.randint(0, 9)) for _ in range(7)]))
                            elif inp_type == 'number':
                                val = '1'
                            else:
                                val = TEST_DATA_PATTERNS['generic_text']
                            body.append(f"    page.fill_input_field('{inp['id']}', '{val}')")
                
                for cb in self.html_structure.get('checkboxes', []):
                    if cb.get('id') and cb['id'] not in filled_fields:
                        label_lower = cb.get('label', '').lower()
                        if any(keyword in label_lower for keyword in ['term', 'agree', 'accept', 'consent']):
                            body.append(f"    page.check_checkbox('{cb['id']}')")
                
                if body and body[-1] != "":
                    body.append("")

                submit_btn = self._find_submit_button_semantic()
                if submit_btn:
                    submit_id = submit_btn.get('id')
                    submit_text = submit_btn.get('text')
                    submit_class = submit_btn.get('class')
                    
                    body.append(f"    # {clean_step}")

                    if submit_id:
                        if submit_btn.get('disabled'):
                            body.append(f"    page.wait_button_enabled('{submit_id}')")
                        body.append(f"    page.click_button('{submit_id}')")
                    elif submit_text:
                        body.append(f"    page.click_button_by_text('{submit_text}')")
                    elif submit_class:
                        first_class = submit_class.split()[0]
                        body.append(f"    page.click_button_by_class('{first_class}')")
                    
                    body.append("")
                matched = True
        
        return body
    
    def _generate_final_verification(self) -> List[str]:
        body = []
        
        submit_btn = self._find_submit_button_semantic()
        
        success_elem = next((e for e in self.html_structure.get('success_elements', [])), None)
        
        if submit_btn and success_elem:
            submit_id = submit_btn.get('id')
            submit_text = submit_btn.get('text')
            submit_class = submit_btn.get('class')
            
            body.append(f"    # Submit form and verify")
            
            if submit_btn.get('disabled') and submit_id:
                body.append(f"    page.wait_button_enabled('{submit_id}')")

            if submit_id:
                body.append(f"    page.click_button('{submit_id}')")
            elif submit_text:
                body.append(f"    page.click_button_by_text('{submit_text}')")
            elif submit_class:
                first_class = submit_class.split()[0]
                body.append(f"    page.click_button_by_class('{first_class}')")
            body.append("")
        
        if success_elem and success_elem.get('id'):
            elem_id = success_elem['id']
            body.append(f"    # Verify success")
            body.append(f"    page.wait_for_element('{elem_id}')")
            body.append(f"    confirmation = page.get_element_text('{elem_id}')")
            body.append(f"    assert confirmation, 'Confirmation message should be displayed'")
            
            if success_elem.get('text_content'):
                expected = success_elem['text_content']
                body.append(f"    assert '{expected}' in confirmation, f'Expected \"{expected}\", got: {{confirmation}}'")
        elif submit_btn:
            submit_id = submit_btn.get('id')
            submit_text = submit_btn.get('text')
            submit_class = submit_btn.get('class')
            
            body.append("    # Submit form")
            
            if submit_id:
                if submit_btn.get('disabled'):
                    body.append(f"    page.wait_button_enabled('{submit_id}')")
                body.append(f"    page.click_button('{submit_id}')")
            elif submit_text:
                body.append(f"    page.click_button_by_text('{submit_text}')")
            elif submit_class:
                first_class = submit_class.split()[0]
                body.append(f"    page.click_button_by_class('{first_class}')")
        else:
            body.append("    # No submit button detected")
        
        return body
    
    def _generate_main_block(self) -> str:
        if self.framework == "pytest":
            return """if __name__ == '__main__':
    # Run with: pytest <filename> -v
    pytest.main([__file__, '-v'])"""
        else:
            return """if __name__ == '__main__':
    unittest.main(verbosity=2)"""
    
    def _find_semantic_match(self, step_text: str, candidates: List[Dict], threshold: float = 0.35) -> Dict:

        if not candidates:
            return None
            
        try:
            candidate_texts = []
            for c in candidates:
                desc = f"{c.get('tag', 'element')} "
                if c.get('text'): desc += f"text='{c.get('text')}' "
                if c.get('id'): desc += f"id='{c.get('id')}' "
                if c.get('name'): desc += f"name='{c.get('name')}' "
                if c.get('placeholder'): desc += f"placeholder='{c.get('placeholder')}' "
                if c.get('label'): desc += f"label='{c.get('label')}' "
                if c.get('class'): desc += f"class='{c.get('class')}' "
                if c.get('onclick'): desc += f"onclick='{c.get('onclick')}' "
                if c.get('options'): desc += f"options='{c.get('options')}' "
                candidate_texts.append(desc)
                
            model = get_embedding_model()
            embeddings = model.encode([step_text] + candidate_texts)
            
            step_embedding = embeddings[0]
            candidate_embeddings = embeddings[1:]
            
            from numpy import dot
            from numpy.linalg import norm
            
            similarities = []
            for cand_emb in candidate_embeddings:
                sim = dot(step_embedding, cand_emb) / (norm(step_embedding) * norm(cand_emb))
                similarities.append(sim)
                
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            
            if best_score >= threshold:
                return candidates[best_idx]
                
        except Exception as e:
            logger.error(f"Semantic matching failed: {e}")
            
        return None
    
    def _is_final_action_step(self, step_text: str) -> float:
        final_action_intents = [
            "submit the form",
            "complete the action",
            "finalize transaction",
            "proceed with operation",
            "confirm and continue",
            "finish the process"
        ]
        
        try:
            model = get_embedding_model()

            all_texts = [step_text] + final_action_intents
            embeddings = model.encode(all_texts)
            
            step_embedding = embeddings[0]
            intent_embeddings = embeddings[1:]
            
            from numpy import dot
            from numpy.linalg import norm
            
            similarities = []
            for intent_emb in intent_embeddings:
                sim = dot(step_embedding, intent_emb) / (norm(step_embedding) * norm(intent_emb))
                similarities.append(sim)

            return max(similarities)
            
        except Exception as e:
            logger.error(f"Final action detection failed: {e}")
            final_keywords = ['submit', 'ok', 'okay', 'proceed', 'continue', 'finish', 
                            'complete', 'confirm', 'checkout', 'pay', 'purchase', 'book']
            return 0.8 if any(kw in step_text for kw in final_keywords) else 0.0
    
    def _find_submit_button_semantic(self) -> Dict:
        buttons = self.html_structure.get('buttons', [])
        if not buttons:
            return None
        

        type_submit = next((b for b in buttons if b.get('type') == 'submit'), None)
        if type_submit:
            return type_submit
        
        submit_intents = [
            "submit form",
            "complete action",
            "finalize transaction",
            "proceed with operation",
            "confirm and continue"
        ]
        
        try:
            model = get_embedding_model()
            
            button_descriptions = []
            valid_buttons = []  
            
            for btn in buttons:
                desc_parts = []

                if btn.get('text'):
                    desc_parts.append(btn['text'])

                if btn.get('onclick'):
                    onclick = btn['onclick']
                    func_name = re.sub(r'[();"]', '', onclick)
                    func_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', func_name)
                    desc_parts.append(func_name)
                
                if btn.get('id'):
                    btn_id = btn['id'].replace('-', ' ').replace('_', ' ')
                    desc_parts.append(btn_id)
                
                if btn.get('class'):
                    btn_class = btn['class'].replace('-', ' ').replace('_', ' ')
                    desc_parts.append(btn_class)
                
                if desc_parts:
                    button_descriptions.append(' '.join(desc_parts).lower())
                    valid_buttons.append(btn)
            
            if not button_descriptions:
                return None

            all_texts = submit_intents + button_descriptions
            embeddings = model.encode(all_texts)
            
            intent_embeddings = embeddings[:len(submit_intents)]
            button_embeddings = embeddings[len(submit_intents):]
            
            avg_intent = np.mean(intent_embeddings, axis=0)
            
            from numpy import dot
            from numpy.linalg import norm
            
            best_score = -1
            best_button = None
            
            for idx, btn_emb in enumerate(button_embeddings):
                btn_text = valid_buttons[idx].get('text', '').lower()
                btn_id = valid_buttons[idx].get('id', '').lower()
                
                if any(neg in btn_text or neg in btn_id for neg in NEGATIVE_ACTIONS):
                    continue
                
                similarity = dot(avg_intent, btn_emb) / (norm(avg_intent) * norm(btn_emb))

                if valid_buttons[idx].get('type') == 'button':
                    similarity *= 1.1

                if valid_buttons[idx].get('onclick'):
                    similarity *= 1.15
                
                if similarity > best_score:
                    best_score = similarity
                    best_button = valid_buttons[idx]

            if best_score > THRESHOLDS['submit_button']:
                logger.info(f"Found submit button via semantic matching: {best_button.get('id')} (score: {best_score:.3f})")
                return best_button
            
        except Exception as e:
            logger.error(f"Semantic submit button detection failed: {e}")

        return buttons[-1] if buttons else None


def generate_deterministic_selenium_script(
    html_structure: Dict,
    test_cases: List[Dict],
    framework: str = "pytest",
    browser: str = "chrome",
    page_url: str = None
) -> str:
    generator = DeterministicSeleniumGenerator(html_structure, framework, browser)
    return generator.generate_complete_script(test_cases, page_url)
