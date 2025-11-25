import streamlit as st
import requests
import time
import json

BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Autonomous QA Agent", page_icon="🤖")
st.title("🤖 Autonomous QA Agent")
st.markdown("*Build intelligent test cases from your project documentation*")

try:
    resp = requests.get(f"{BACKEND_URL}/", timeout=2)
    if resp.status_code == 200:
        st.success(" Backend is connected")
    else:
        st.error(" Backend connection issue")
except:
    st.error("Backend is not running. Please start it with: `python -m uvicorn backend.main:app --port 8000`")
    st.stop()

st.header("Phase 1: Build Knowledge Base")
st.markdown("Upload your project documentation (specs, API docs, UI guidelines, etc.)")

uploaded_files = st.file_uploader(
    "Upload Support Documents",
    type=["pdf", "txt", "md", "json", "html"],
    accept_multiple_files=True,
    help="Supported formats: PDF, TXT, Markdown, JSON, HTML"
)

if uploaded_files:
    st.info(f" {len(uploaded_files)} file(s) ready to upload")
    for file in uploaded_files:
        st.text(f"  • {file.name} ({file.size} bytes)")

if st.button(" Build Knowledge Base", type="primary"):
    if not uploaded_files:
        st.error(" Please upload at least one file")
    else:
        with st.spinner("Processing documents..."):
            files_payload = [("files", (f.name, f.read(), "application/octet-stream")) for f in uploaded_files]
            try:
                resp = requests.post(f"{BACKEND_URL}/build-kb", files=files_payload, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(f" Knowledge Base Built Successfully!")
                    st.metric("Chunks Indexed", result.get("chunks_indexed", 0))
                else:
                    st.error(f"Error: {resp.text}")
            except Exception as e:
                st.error(f"Failed to build KB: {e}")

st.markdown("---")

st.header("Phase 2: Test Case Generation")
st.markdown("Generate comprehensive test cases using AI-powered RAG pipeline")

with st.expander("ℹ️ LLM Configuration"):
    st.markdown("""
    **LLM Provider: Ollama (Local)**

    The system is currently configured to use a local Ollama model for test case generation.
    - **Model**: `llama3.1:8b`
    - **Context Window**: 8192 tokens
    - **Usage**: No API key required; runs on your machine
    - **JSON Handling**: Basic repair and fallback parsing
    - **Simplified Pipeline**: Removed cloud provider and advanced cross-document checks

    **Current Configuration (.env):**
    ```bash
    LLM_PROVIDER=ollama
    OLLAMA_MODEL=llama3.1:8b
    ```

    To change the model, edit `OLLAMA_MODEL` in `.env` and restart the backend.
    """)

test_prompt = st.text_area(
    "Describe what you want to test:",
    placeholder="e.g., Generate all positive and negative test cases for the discount code feature",
    help="Be specific about the feature, functionality, or user flow you want to test",
    height=100
)

html_file_for_tc = st.file_uploader(
    "Upload HTML File (Optional - for form validation awareness)",
    type=["html", "htm"],
    help="Upload HTML to enable dependency graph analysis - ensures test cases fill ALL required fields before submit",
    key="tc_html_upload"
)
if html_file_for_tc:
    st.success(f" HTML uploaded: {html_file_for_tc.name} - Dependency graph will be analyzed")
    st.info("The system will analyze form dependencies to ensure generated test cases are executable")

col1, col2 = st.columns([3, 1])
with col1:
    feature_name = st.text_input(
        "Feature Name (optional):",
        placeholder="e.g., Discount Code System",
        help="Specify the feature name for better organization"
    )
with col2:
    top_k = st.number_input(
        "Context chunks:",
        min_value=3,
        max_value=20,
        value=10,
        help="Number of documentation chunks to retrieve"
    )

if st.button(" Generate Test Cases", type="primary", key="generate_tc"):
    if not test_prompt:
        st.warning("Please describe what you want to test")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text(" Sending request to backend...")
        progress_bar.progress(10)
        
        try:
            start_time = time.time()
            
            status_text.text(" Retrieving relevant documentation...")
            progress_bar.progress(20)
            
            status_text.text(" AI is generating test cases... (60-180 seconds)")
            progress_bar.progress(30)

            payload = {
                "prompt": test_prompt,
                "feature": feature_name,
                "top_k": top_k
            }
            

            if html_file_for_tc:
                html_content = html_file_for_tc.getvalue().decode('utf-8')
                payload["html_content"] = html_content
                status_text.text(" Analyzing form dependencies from HTML...")
                progress_bar.progress(40)
            
            status_text.text(" AI is generating test cases... (60-180 seconds)")
            progress_bar.progress(50)
            
            resp = requests.post(
                f"{BACKEND_URL}/generate-test-cases",
                json=payload,
                timeout=300 
            )
            
            elapsed = time.time() - start_time
            status_text.text(f" Completed in {elapsed:.1f} seconds")
            progress_bar.progress(100)
            
            if resp.status_code == 200:
                result = resp.json()
                test_cases = result.get("test_cases", [])
                count = result.get("count", 0)
                sources = result.get("sources", [])
                llm_provider = result.get("llm_provider", result.get("provider", "unknown"))
                model = result.get("model", "unknown")
                metadata = result.get("metadata", {})
                
                st.success(f" Generated {count} test case(s)")
                
                dropped_details = metadata.get("dropped_cases_details", [])
                if dropped_details:
                    st.warning(f" Dropped {len(dropped_details)} test case(s) due to critical hallucinations")
                    with st.expander(" View Dropped Test Cases"):
                        for drop in dropped_details:
                            st.error(f"**{drop['test_id']}**: {drop['reason']}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Test Cases", count)
                with col2:
                    st.metric("Source Docs", len(sources))
                with col3:
                    st.metric("Provider", llm_provider)
                with col4:
                    st.metric("Model", model)
                
                if metadata:
                    with st.expander(" Processing Details"):
                        st.json(metadata)

                if sources:
                    with st.expander(" Grounded in documents:"):
                        for source in sources:
                            st.markdown(f"- `{source}`")

                st.session_state['test_cases'] = test_cases

                if test_cases:
                    st.markdown("---")
                    st.subheader("Generated Test Cases")
                    
                    for i, tc in enumerate(test_cases, 1):
                        test_id = tc.get("test_id", f"TC-{i:03d}")
                        feature = tc.get("feature", "Unknown Feature")
                        test_type = tc.get("test_type", "unknown")
                        priority = tc.get("priority", "medium")
                        needs_review = tc.get("needs_review", False)

                        type_color = "🟢" if test_type == "positive" else "🔴" if test_type == "negative" else "⚪"
                        priority_badge = "🔥" if priority == "high" else "⚡" if priority == "medium" else "📌"
                        review_badge = "⚠️ NEEDS REVIEW" if needs_review else ""
                        
                        title = f"{type_color} {test_id}: {feature} {priority_badge} {review_badge}"
                        
                        with st.expander(title):
                            if needs_review:
                                st.warning(f"⚠️ **Review Required:** {tc.get('_review_reason', 'No verbatim evidence in docs')}")
                            
                            if tc.get("_hallucination_warning"):
                                st.error(f"⚠️ **Hallucination Warning:** {tc.get('_hallucination_warning')}")
                            
                            st.markdown(f"**Test Type:** {test_type.capitalize()}")
                            st.markdown(f"**Priority:** {priority.capitalize()}")
                            st.markdown(f"**Scenario:** {tc.get('test_scenario', 'N/A')}")
                            
                            st.markdown("**Test Steps:**")
                            steps = tc.get("test_steps", [])
                            if isinstance(steps, list):
                                for step_num, step in enumerate(steps, 1):
                                    st.markdown(f"{step_num}. {step}")
                            else:
                                st.markdown(steps)
                            
                            st.markdown(f"**Expected Result:** {tc.get('expected_result', 'N/A')}")
                            st.markdown(f"**Grounded In:** `{tc.get('grounded_in', 'N/A')}`")
                            
                            st.code(str(tc), language="json")

                    st.markdown("---")
                    test_cases_json = json.dumps(test_cases, indent=2)
                    st.download_button(
                        label="📥 Download Test Cases (JSON)",
                        data=test_cases_json,
                        file_name="test_cases.json",
                        mime="application/json"
                    )
                    
                    markdown_output = "# Test Cases\n\n"
                    for i, tc in enumerate(test_cases, 1):
                        markdown_output += f"## {tc.get('test_id', f'TC-{i:03d}')}: {tc.get('feature', 'Test Case')}\n\n"
                        markdown_output += f"**Test Type:** {tc.get('test_type', 'N/A')}\n\n"
                        markdown_output += f"**Priority:** {tc.get('priority', 'N/A')}\n\n"
                        markdown_output += f"**Scenario:** {tc.get('test_scenario', 'N/A')}\n\n"
                        markdown_output += f"**Test Steps:**\n"
                        steps = tc.get("test_steps", [])
                        if isinstance(steps, list):
                            for step_num, step in enumerate(steps, 1):
                                markdown_output += f"{step_num}. {step}\n"
                        markdown_output += f"\n**Expected Result:** {tc.get('expected_result', 'N/A')}\n\n"
                        markdown_output += f"**Grounded In:** {tc.get('grounded_in', 'N/A')}\n\n"
                        markdown_output += "---\n\n"
                    
                    st.download_button(
                        label="📥 Download Test Cases (Markdown)",
                        data=markdown_output,
                        file_name="test_cases.md",
                        mime="text/markdown"
                    )
                else:
                    st.warning("No test cases were generated. Try rephrasing your prompt.")
            
            elif resp.status_code == 404:
                st.error("⚠️ Knowledge base is empty. Please build the knowledge base first in Phase 1.")
            else:
                st.error(f"Error: {resp.text}")
        
        except requests.exceptions.Timeout:
            progress_bar.empty()
            status_text.empty()
            st.error(" **Request timed out after 5 minutes.**")
            st.error("This usually means:")
            st.error("- Ollama is processing a very large prompt")
            st.error("- System resources (CPU/Memory) are constrained")
            st.error("- The llama3.1:8b model needs more time for complex requests")
            st.info(" Try:\n1. Reduce the number of context chunks (top_k)\n2. Simplify your prompt\n3. Check if Ollama is running: `docker exec qa-agent-ollama ollama list`\n4. Check system resources (CPU/RAM usage)")
        except requests.exceptions.ConnectionError:
            progress_bar.empty()
            status_text.empty()
            st.error(" **Cannot connect to backend.**")
            st.error("Please ensure the backend is running on http://127.0.0.1:8000")
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f" **Generation failed:** {str(e)}")
            st.error("Check backend logs for details: `tail -100 backend.log`")

st.markdown("---")
st.caption("Phase 6 Complete: Test Case Generation with RAG Pipeline")

st.markdown("---")

st.header("Phase 3: Selenium Script Generation")
st.markdown("Generate automated Selenium WebDriver scripts from HTML pages and test cases")

# Tab selection
tab2 = st.tabs([ "🧪 Generate with Test Cases"])

with tab2:
    st.markdown("### Generate with Test Cases & Knowledge Base")
    st.markdown("Upload HTML and use generated test cases + KB context for comprehensive automation")
    
    html_file_advanced = st.file_uploader(
        "Upload HTML File",
        type=["html", "htm"],
        help="Upload the HTML page you want to automate",
        key="advanced_html_upload"
    )
    
    test_cases_input = st.text_area(
        "Test Cases (JSON format)",
        placeholder='''[
  {
    "test_id": "TC001",
    "feature": "Login Form",
    "test_steps": ["Navigate to page", "Fill username", "Fill password", "Click submit"],
    "expected_result": "User is logged in successfully"
  }
]''',
        help="Paste test cases in JSON format (from Phase 6 output)",
        height=200,
        key="test_cases_input"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        advanced_framework = st.selectbox(
            "Testing Framework",
            options=["pytest", "unittest"],
            index=0,
            help="Choose your preferred Python testing framework",
            key="advanced_framework"
        )
    with col2:
        advanced_browser = st.selectbox(
            "Target Browser",
            options=["chrome", "firefox", "edge"],
            index=0,
            help="Browser for Selenium WebDriver",
            key="advanced_browser"
        )
    
    use_kb_context = st.checkbox(
        "Include Knowledge Base Context",
        value=True,
        help="Retrieve relevant documentation from KB to enhance script generation",
        key="use_kb_context"
    )
    
    if use_kb_context:
        kb_prompt = st.text_input(
            "KB Search Query",
            placeholder="e.g., validation rules, UI guidelines",
            help="Describe what context to retrieve from KB",
            key="kb_prompt"
        )
    
    if st.button(" Generate Advanced Script", type="primary", key="advanced_generate"):
        if not html_file_advanced:
            st.error(" Please upload an HTML file")
        else:
            with st.spinner("Generating advanced Selenium script..."):
                try:
                    test_cases_list = []
                    if test_cases_input.strip():
                        try:
                            test_cases_list = json.loads(test_cases_input)
                        except json.JSONDecodeError:
                            st.warning("Invalid JSON in test cases. Proceeding without test cases.")
                    
                    html_content = html_file_advanced.getvalue()
                    payload = {
                        "html_content": html_content.decode('utf-8'),
                        "html_filename": html_file_advanced.name,
                        "test_cases": test_cases_list,
                        "framework": advanced_framework,
                        "browser": advanced_browser,
                        "include_kb_context": use_kb_context,
                        "prompt": kb_prompt if use_kb_context else ""
                    }
                    
                    resp = requests.post(
                        f"{BACKEND_URL}/generate-selenium",
                        json=payload,
                        timeout=180
                    )
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        st.success(" Advanced Selenium Script Generated Successfully!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Test Cases", result.get("test_cases_covered", 0))
                        with col2:
                            st.metric("Elements Mapped", result.get("elements_mapped", 0))
                        with col3:
                            st.metric("KB Chunks", result.get("retrieved_chunks", 0))
                        with col4:
                            fallback_used = result.get("metadata", {}).get("fallback_used", False)
                            st.metric("Mode", "Fallback" if fallback_used else "LLM")
                        
                        # Display script
                        st.markdown("### Generated Script")
                        script = result.get("script", "")
                        st.code(script, language="python", line_numbers=True)

                        st.download_button(
                            label="📥 Download Script",
                            data=script,
                            file_name=f"selenium_test_{html_file_advanced.name.replace('.html', '')}_advanced.py",
                            mime="text/x-python"
                        )
                        
                        with st.expander("📖 How to Use This Script"):
                            st.markdown(f"""
                            **Prerequisites:**
                            ```bash
                            pip install selenium {advanced_framework} webdriver-manager
                            ```
                            
                            **Run the tests:**
                            ```bash
                            {advanced_framework} selenium_test_{html_file_advanced.name.replace('.html', '')}_advanced.py -v
                            ```
                            
                            **Script Features:**
                            - Page Object Model (POM) pattern for maintainability
                            - Explicit waits for stability
                            - {result.get('test_cases_covered', 0)} test case(s) implemented
                            - {result.get('elements_mapped', 0)} HTML elements mapped
                            - KB context: {"✓ Included" if result.get('kb_context_used') else "✗ Not used"}
                            
                            **Before Running:**
                            1. Update `driver.get()` URL to point to your actual page
                            2. Ensure the target browser driver is installed
                            3. Implement actual interactions in test methods (replace `pass` statements)
                            """)
                    else:
                        st.error(f"Error: {resp.text}")
                        
                except requests.exceptions.Timeout:
                    st.error(" Request timed out. Try reducing test cases or simplifying the request.")
                except Exception as e:
                    st.error(f"Generation failed: {e}")

st.markdown("---")
st.caption("Phase 7 & 8 Complete: Selenium Script Generation with UI Integration")