
import json
import logging
from typing import Dict, List, Any
from datetime import datetime
import re

from .html_parser_service import parse_html_structure, format_html_structure_for_context
from .llm_service import format_context_from_retrieved_docs
from .llm_service.config import OLLAMA_MODEL, GENERATION_TEMPERATURE
from .llm_service.generators import generate_test_cases_with_ollama
from .deterministic_selenium_generator import generate_deterministic_selenium_script

logger = logging.getLogger(__name__)


def generate_selenium_script(
    html_content: bytes | str,
    test_cases: List[Dict],
    retrieved_docs: List[Dict],
    framework: str = "pytest",
    browser: str = "chrome"
) -> Dict[str, Any]:
    
    logger.info(f"Starting Selenium script generation - Framework: {framework}, Browser: {browser}")
    
    html_structure = parse_html_structure(html_content)
    html_context = format_html_structure_for_context(html_structure)
    
    doc_context = format_context_from_retrieved_docs(retrieved_docs) if retrieved_docs else ""
    
    if not test_cases:
        synthesized_tc = {
            "test_id": "TC-001",
            "feature": html_structure.get("page_title", "UI Validation"),
            "test_scenario": f"Basic interaction with {html_structure.get('page_title', 'page')} form elements",
            "test_steps": [
                "Open page",
                "Populate first input field (if any)",
                "Click first button (if any)",
                "Verify no errors thrown"
            ],
            "expected_result": "Page responds without errors and elements are interactable",
            "test_type": "positive",
            "priority": "medium",
            "grounded_in": retrieved_docs[0].get("source", "unknown") if retrieved_docs else "inference"
        }
        test_cases = [synthesized_tc]
        logger.info("Selenium generation: synthesized fallback test case due to empty test_cases input")

    prompt = build_selenium_generation_prompt(
        html_structure=html_structure,
        html_context=html_context,
        test_cases=test_cases,
        doc_context=doc_context,
        framework=framework,
        browser=browser
    )
    
    logger.info(f"Prompt tokens (estimated): {len(prompt.split())}")
    
    logger.info("Using deterministic Selenium script generation")
    try:
        script = generate_deterministic_selenium_script(
            html_structure=html_structure,
            test_cases=test_cases,
            framework=framework,
            browser=browser,
            page_url="file:///path/to/page.html"
        )
        fallback_used = False
        logger.info(f"Deterministic script generated successfully: {len(script)} chars")
    except Exception as e:
        import traceback
        logger.error(f"Deterministic generation failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise RuntimeError(f"Failed to generate Selenium script: {str(e)}")

    script = validate_and_enhance_script(script, html_structure, framework)
    
    script, applied_fallback = ensure_script_quality(
        script,
        html_structure,
        test_cases,
        framework,
        browser
    )
    fallback_used = fallback_used or applied_fallback

    result = {
        "script": script,
        "framework": framework,
        "browser": browser,
        "elements_mapped": count_mapped_elements(html_structure),
        "test_cases_covered": len(test_cases),
        "html_forms": len(html_structure.get('forms', [])),
        "html_inputs": len(html_structure.get('inputs', [])),
        "html_buttons": len(html_structure.get('buttons', [])),
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": OLLAMA_MODEL,
            "page_title": html_structure.get('page_title', 'Unknown'),
            "fallback_used": fallback_used
        }
    }

    logger.info(f"Selenium script generated (fallback={fallback_used}) - {len(script)} chars")
    return result


def build_selenium_generation_prompt(
    html_structure: Dict,
    html_context: str,
    test_cases: List[Dict],
    doc_context: str,
    framework: str,
    browser: str
) -> str:
    prompt_parts = []
    
    prompt_parts.append("You are an expert QA automation engineer specializing in Selenium WebDriver.\n\n")
    
    prompt_parts.append("# TASK\n")
    prompt_parts.append(f"Generate a complete {framework} Selenium WebDriver script for {browser} browser.\n")
    prompt_parts.append("The script should automate the test cases provided based on the HTML structure and documentation.\n\n")
    
    prompt_parts.append("# HTML PAGE STRUCTURE\n")
    prompt_parts.append(html_context)
    prompt_parts.append("\n\n")
    
    if test_cases:
        prompt_parts.append("# TEST CASES TO AUTOMATE\n")
        for idx, tc in enumerate(test_cases[:5], 1):
            prompt_parts.append(f"\n## Test Case {idx}: {tc.get('title', 'Untitled')}\n")
            prompt_parts.append(f"Description: {tc.get('description', 'N/A')}\n")
            
            if tc.get('steps'):
                prompt_parts.append("Steps:\n")
                for step_idx, step in enumerate(tc['steps'], 1):
                    prompt_parts.append(f"  {step_idx}. {step}\n")
            
            if tc.get('expected_result'):
                prompt_parts.append(f"Expected: {tc['expected_result']}\n")
        prompt_parts.append("\n")
    
    if doc_context:
        prompt_parts.append("# DOCUMENTATION CONTEXT\n")
        prompt_parts.append(doc_context[:2000])
        prompt_parts.append("\n\n")
    
    prompt_parts.append("# REQUIREMENTS\n")
    prompt_parts.append("1. Use Page Object Model (POM) pattern for maintainability\n")
    prompt_parts.append("2. Include proper waits (WebDriverWait) - avoid time.sleep()\n")
    prompt_parts.append("3. **CRITICAL**: Wait for enabled state on buttons marked as initially disabled\n")
    prompt_parts.append("4. **CRITICAL**: Include ALL form fields: text inputs, selects, checkboxes, radio buttons\n")
    prompt_parts.append("5. **CRITICAL**: Handle required fields marked with * or required attribute\n")
    prompt_parts.append("6. **CRITICAL**: Handle conditional sections (aria-hidden, display:none) that show/hide based on selections\n")
    prompt_parts.append("7. **CRITICAL**: Validate success/confirmation messages using actual HTML element content\n")
    prompt_parts.append("8. Use explicit selectors (ID > CSS > XPath) based on HTML structure\n")
    prompt_parts.append("9. Add assertions to verify ONLY what the HTML actually displays (no inferred values)\n")
    prompt_parts.append("10. Include setup (browser initialization) and teardown methods\n")
    prompt_parts.append("11. Add docstrings and comments for clarity\n")
    prompt_parts.append("12. Handle common exceptions (NoSuchElementException, TimeoutException)\n")
    prompt_parts.append(f"13. Use {framework} decorators and assertions\n")
    prompt_parts.append(f"14. Configure for {browser} browser using webdriver\n\n")
    
    prompt_parts.append("# OUTPUT FORMAT\n")
    prompt_parts.append("Provide ONLY the complete Python script. No explanations before or after.\n")
    prompt_parts.append("Start with imports and end with if __name__ == '__main__': block.\n\n")
    
    prompt_parts.append("# GENERATE SCRIPT NOW\n")
    prompt_parts.append("```python\n")
    
    return ''.join(prompt_parts)


def extract_script_from_response(response: str) -> str:
    if '```python' in response:
        start = response.find('```python') + len('```python')
        end = response.find('```', start)
        if end > start:
            script = response[start:end].strip()
        else:
            script = response[start:].strip()
    elif '```' in response:
        start = response.find('```') + len('```')
        end = response.find('```', start)
        if end > start:
            script = response[start:end].strip()
        else:
            script = response[start:].strip()
    else:
        script = response.strip()
    
    return script


def validate_and_enhance_script(script: str, html_structure: Dict, framework: str) -> str:
    essential_imports = [
        "from selenium import webdriver",
        "from selenium.webdriver.common.by import By",
        "from selenium.webdriver.support.ui import WebDriverWait",
        "from selenium.webdriver.support import expected_conditions as EC"
    ]
    
    if framework == "pytest":
        essential_imports.append("import pytest")
    elif framework == "unittest":
        essential_imports.append("import unittest")
    
    missing_imports = []
    for imp in essential_imports:
        if imp not in script:
            missing_imports.append(imp)
    
    if missing_imports:
        script = '\n'.join(missing_imports) + '\n\n' + script
    
    return script


def ensure_script_quality(
    script: str,
    html_structure: Dict,
    test_cases: List[Dict],
    framework: str,
    browser: str
) -> tuple[str, bool]:
    json_only = False
    try:
        parsed = json.loads(script)
        if isinstance(parsed, dict) or isinstance(parsed, list):
            json_only = True
    except Exception:
        pass

    has_driver_get = "driver.get" in script
    has_pytest_test = re.search(r"def\s+test_", script) is not None
    has_unittest_class = re.search(r"class\s+\w+\(unittest\.TestCase\)", script) is not None

    structural_ok = has_driver_get and (has_pytest_test or has_unittest_class) and not json_only
    too_short = len(script.strip()) < 120

    if structural_ok and not too_short:
        return script, False

    logger.info("Script quality check failed, using deterministic generator")
    fallback = generate_deterministic_selenium_script(
        html_structure=html_structure,
        test_cases=test_cases,
        framework=framework,
        browser=browser,
        page_url="file:///path/to/page.html"
    )
    return fallback, True


def build_fallback_script(
    html_structure: Dict,
    test_cases: List[Dict],
    framework: str,
    browser: str
) -> str:
    inputs = html_structure.get("inputs", [])[:15]
    selects = html_structure.get("selects", [])[:5]
    checkboxes = html_structure.get("checkboxes", [])[:5]
    radio_groups = html_structure.get("radio_groups", [])[:3]
    buttons = html_structure.get("buttons", [])[:5]
    success_elements = html_structure.get("success_elements", [])[:3]
    page_title = html_structure.get("page_title", "Page")
    behavior = html_structure.get("behavior_analysis", {})

    url_comment = "# REPLACE_URL: Set this to your actual page URL before running"
    page_url = "https://example.com/page.html"

    locators_lines = []
    seen_fields = set()

    for idx, field in enumerate(inputs, 1):
        fid = field.get("id") or field.get("name") or f"input_{idx}"
        if fid in seen_fields:
            continue
        seen_fields.add(fid)
        locator = f"(By.ID, '{fid}')" if field.get("id") else f"(By.NAME, '{fid}')"
        locators_lines.append(f"        self.{fid.replace('-', '_')} = {locator}")

    for select in selects:
        sid = select.get("id") or select.get("name")
        if sid and sid not in seen_fields:
            seen_fields.add(sid)
            locator = f"(By.ID, '{sid}')" if select.get("id") else f"(By.NAME, '{sid}')"
            locators_lines.append(f"        self.{sid.replace('-', '_')} = {locator}")

    for cb in checkboxes:
        cbid = cb.get("id")
        if cbid and cbid not in seen_fields:
            seen_fields.add(cbid)
            locators_lines.append(f"        self.{cbid.replace('-', '_')} = (By.ID, '{cbid}')")

    for rg in radio_groups:
        if rg['options'] and rg['options'][0].get('id'):
            rid = rg['options'][0]['id']
            if rid not in seen_fields:
                seen_fields.add(rid)
                locators_lines.append(f"        self.{rid.replace('-', '_')} = (By.ID, '{rid}')")

    for idx, btn in enumerate(buttons, 1):
        bid = btn.get("id") or btn.get("name") or f"button_{idx}"
        if bid in seen_fields:
            continue
        seen_fields.add(bid)
        locator = f"(By.ID, '{bid}')" if btn.get("id") else f"(By.XPATH, '//button[{idx}]')"
        locators_lines.append(f"        self.{bid.replace('-', '_')} = {locator}")

    for se in success_elements:
        seid = se.get("id")
        if seid and seid not in seen_fields:
            seen_fields.add(seid)
            locators_lines.append(f"        self.{seid.replace('-', '_')} = (By.ID, '{seid}')")

    tc_snippets = []
    selected_cases = test_cases[:3] if test_cases else [
        {
            "id": "TC_FALLBACK",
            "title": "Complete Form Interaction",
            "steps": ["Open page", "Fill all fields", "Handle checkboxes", "Click submit", "Verify success"],
            "expected_result": "Form submits successfully and confirmation appears"
        }
    ]

    if framework == "pytest":
        for tc in selected_cases:
            fn_name = re.sub(r"[^a-zA-Z0-9_]", "_", tc.get("id", tc.get("title", "tc")).lower())
            steps_comment = "\n    # " + "\n    # ".join(tc.get("steps", []))
            expected = tc.get("expected_result", "Expected result placeholder")
            
            wait_logic = ""
            disabled_btns = behavior.get("disabled_buttons", [])
            if disabled_btns:
                btn_id = disabled_btns[0].get("id")
                if btn_id:
                    wait_logic = f"\n    # Wait for {btn_id} to become enabled\n    WebDriverWait(driver, 10).until(lambda d: d.find_element(*page.{btn_id.replace('-', '_')}).is_enabled())\n"
            
            tc_snippets.append(
                f"def test_{fn_name}(driver):\n"
                f"    page = Page(driver)\n"
                f"    driver.get('{page_url}')  {url_comment}\n"
                f"{steps_comment}\n"
                "    # Example interaction (adjust based on actual test requirements)\n"
                "    try:\n"
                "        # Fill inputs, select options, check checkboxes, etc.\n"
                "        # Example: driver.find_element(*page.name).send_keys('Test Name')\n"
                "        # Example: driver.find_element(*page.terms).click()\n"
                "        pass  # Replace with actual test logic\n"
                f"{wait_logic}"
                "    except Exception as e:\n"
                "        pytest.fail(f'Unexpected exception: {e}')\n"
                f"    assert True, '{expected}'\n\n"
            )
    else:  # unittest
        for tc in selected_cases:
            method_name = re.sub(r"[^a-zA-Z0-9_]", "_", tc.get("id", tc.get("title", "tc")).lower())
            steps_lines = [f"        # {s}" for s in tc.get("steps", [])]
            expected = tc.get("expected_result", "Expected result placeholder")
            tc_snippets.append(
                f"    def test_{method_name}(self):\n"
                f"        page = Page(self.driver)\n"
                f"        self.driver.get('{page_url}')  {url_comment}\n"
                + "\n".join(steps_lines) + "\n"
                "        # Example interaction placeholder\n"
                "        self.assertTrue(True, '{expected}')\n\n"
            )

    imports = [
        "from selenium import webdriver",
        "from selenium.webdriver.common.by import By",
        "from selenium.webdriver.support.ui import WebDriverWait",
        "from selenium.webdriver.support import expected_conditions as EC",
    ]
    if framework == "pytest":
        imports.append("import pytest")
    else:
        imports.append("import unittest")

    page_object = [
        "class Page:",
        "    def __init__(self, driver):",
        "        self.driver = driver",
    ] + locators_lines + ["", "    # Add helper methods as needed"]

    if framework == "pytest":
        driver_block = [
            "@pytest.fixture(scope='module')",
            "def driver():",
            "    driver = webdriver.Chrome()  # Optionally use webdriver_manager",
            "    driver.maximize_window()",
            "    yield driver",
            "    driver.quit()",
            "",
        ]
        tests_block = tc_snippets
        end_block = ["if __name__ == '__main__':", "    # Run with: pytest -v", "    pass"]
    else:
        driver_block = [
            "class TestSuite(unittest.TestCase):",
            "    @classmethod",
            "    def setUpClass(cls):",
            "        cls.driver = webdriver.Chrome()",
            "        cls.driver.maximize_window()",
            "    @classmethod",
            "    def tearDownClass(cls):",
            "        cls.driver.quit()",
            "",
        ]
        tests_block = tc_snippets
        end_block = ["if __name__ == '__main__':", "    unittest.main(verbosity=2)"]

    parts = ["# Fallback generated script", f"# Page Title: {page_title}", *imports, "", *page_object, "", *driver_block, *tests_block, *end_block]
    return "\n".join(parts)


def count_mapped_elements(html_structure: Dict) -> int:
    count = 0
    count += len(html_structure.get('forms', []))
    count += len(html_structure.get('inputs', []))
    count += len(html_structure.get('buttons', []))
    count += len(html_structure.get('selects', []))
    count += len(html_structure.get('links', []))
    return count


def generate_selenium_from_test_case_only(
    test_case: Dict,
    html_content: bytes | str,
    framework: str = "pytest",
    browser: str = "chrome"
) -> Dict[str, Any]:
    html_structure = parse_html_structure(html_content)
    html_context = format_html_structure_for_context(html_structure)
    
    prompt = f"""You are an expert QA automation engineer specializing in Selenium WebDriver.

# TASK
Generate a complete {framework} Selenium WebDriver script for {browser} browser to automate the following test case.

{html_context}

# TEST CASE
Title: {test_case.get('title', 'Test Case')}
Description: {test_case.get('description', 'N/A')}

Steps:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(test_case.get('steps', []), 1))}

Expected Result: {test_case.get('expected_result', 'N/A')}

# REQUIREMENTS
- Use Page Object Model pattern
- Include WebDriverWait with explicit waits
- Add proper assertions
- Use {framework} framework
- Target {browser} browser
- Include setup and teardown

Provide ONLY the complete Python script:

```python
"""
    
    fallback_used = False
    try:
        raw_response = generate_test_cases_with_ollama(
            full_prompt=prompt,
            num_predict=1024,
            temperature=0.3
        )
        script = extract_script_from_response(raw_response)
    except Exception as e:
        logger.error(f"LLM simple generation failed, using fallback: {e}")
        script = ""
        fallback_used = True

    script = validate_and_enhance_script(script, html_structure, framework)
    script, applied_fallback = ensure_script_quality(
        script,
        html_structure,
        [test_case],
        framework,
        browser
    )
    fallback_used = fallback_used or applied_fallback

    return {
        "script": script,
        "framework": framework,
        "browser": browser,
        "test_case": test_case.get('title', 'Test Case'),
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": OLLAMA_MODEL,
            "fallback_used": fallback_used
        }
    }


def format_selenium_script_output(result: Dict) -> str:
    output_parts = []
    
    output_parts.append(f"# Selenium WebDriver Script")
    output_parts.append(f"# Framework: {result['framework']}")
    output_parts.append(f"# Browser: {result['browser']}")
    output_parts.append(f"# Generated: {result['metadata']['generated_at']}")
    output_parts.append(f"# Test Cases Covered: {result.get('test_cases_covered', 1)}")
    output_parts.append(f"# Elements Mapped: {result.get('elements_mapped', 'N/A')}")
    output_parts.append("\n")
    output_parts.append(result['script'])
    
    return '\n'.join(output_parts)
