from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import base64
import os
import shutil
import logging
from pathlib import Path

from .services.parser_service import extract_text_from_file
from .services.chunker import chunks_with_metadata
from .services.embedding_service import embed_texts, get_embedding_model
from .services.vectorstore_service import upsert_chunks, query_top_k
from .services.llm_service import generate_test_cases, format_context_from_retrieved_docs
from .services.corpus_stats_builder import build_corpus_statistics
from .services.selenium_generator_service import (
    generate_selenium_script,
    generate_selenium_from_test_case_only,
    format_selenium_script_output
)
from .services.html_parser_service import parse_html_structure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Autonomous QA Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML_FOLDER = Path("html")
HTML_FOLDER.mkdir(exist_ok=True)

def save_html_file(content: bytes, original_filename: str) -> tuple[str, str]:
    for existing_file in HTML_FOLDER.glob("*.html"):
        existing_file.unlink()
    
    safe_filename = "test.html"
    
    file_path = HTML_FOLDER / safe_filename
    with open(file_path, 'wb') as f:
        f.write(content)
    
    file_url = f"file:///{file_path.absolute().as_posix()}"
    
    return str(file_path), file_url

@app.post("/parse-file")
async def parse_file(request: Request):
    content = None
    filename = None

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if not upload:
            raise HTTPException(422, "Missing file")
        content = await upload.read()
        filename = upload.filename

    elif "application/json" in content_type:
        body = await request.json()
        filename = body.get("filename")
        b64 = body.get("content_base64")
        if not filename or not b64:
            raise HTTPException(422, "filename/content_base64 missing")
        content = base64.b64decode(b64)

    else:
        raise HTTPException(415, "Unsupported Content-Type")

    text = extract_text_from_file(filename, content)
    return {"filename": filename, "extracted_text": text}

@app.post("/build-kb")
async def build_kb(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "No files uploaded")

    all_chunks = []

    for file in files:
        content = await file.read()
        text = extract_text_from_file(file.filename, content)

        chunks = chunks_with_metadata(text, source=file.filename)
        all_chunks.extend(chunks)

    embeddings = embed_texts([c["text"] for c in all_chunks])
    upsert_chunks(all_chunks, embeddings)
    
    try:
        build_corpus_statistics(all_chunks)
    except Exception as e:
        print(f"Warning: Failed to build corpus statistics: {e}")

    return {"status": "ok", "chunks_indexed": len(all_chunks)}

@app.post("/query-kb")
async def query_kb(request: dict):
    query = request.get("query")
    if not query:
        raise HTTPException(400, "Query text missing")

    model = get_embedding_model()
    q_emb = model.encode(query).tolist()

    results = query_top_k(q_emb, k=5)

    return {"query": query, "results": results}

@app.post("/generate-test-cases")
async def generate_test_cases_endpoint(request: dict):
    prompt = request.get("prompt")
    if not prompt:
        raise HTTPException(400, "Prompt is required")
    
    feature = request.get("feature", "")
    
    html_content = request.get("html_content")
    html_structure = None
    if html_content:
        try:
            from backend.services.html_parser_service import parse_html_structure
            html_structure = parse_html_structure(html_content)
            logger.info(f"Parsed HTML structure: {len(html_structure.get('inputs', []))} inputs, "
                       f"{len(html_structure.get('selects', []))} selects, "
                       f"{len(html_structure.get('buttons', []))} buttons")
        except Exception as e:
            logger.warning(f"Failed to parse HTML structure: {e}")
    
    model = get_embedding_model()
    query_embedding = model.encode(prompt).tolist()
    
    k = request.get("top_k", 10)
    results = query_top_k(query_embedding, k=k)
    
    if not results or not results.get("documents") or len(results["documents"][0]) == 0:
        raise HTTPException(404, "No documentation found in knowledge base. Please build KB first.")
    
    retrieved_docs = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    
    for doc_id, doc_text, meta in zip(ids, documents, metadatas):
        retrieved_docs.append({
            "id": doc_id,
            "text": doc_text,
            "source": meta.get("source", "unknown")
        })
    
    context = format_context_from_retrieved_docs(retrieved_docs)
    
    try:
        result = generate_test_cases(prompt, context, retrieved_docs, html_structure, html_content)
        
        return {
            "prompt": prompt,
            "test_cases": result.get("test_cases", []),
            "count": result.get("count", 0),
            "sources": result.get("sources", []),
            "provider": result.get("llm_provider", "unknown"),
            "llm_provider": result.get("llm_provider", "unknown"),
            "model": result.get("model", "unknown"),
            "metadata": result.get("metadata", {}),
            "note": result.get("note", None),
            "retrieved_chunks": len(retrieved_docs)
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in /generate-test-cases: {error_trace}")
        raise HTTPException(500, f"Test case generation failed: {str(e)}")

@app.get("/")
def root():
    return {"status": "Backend running"}

@app.post("/generate-selenium")
async def generate_selenium_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON body: {str(e)}")
    
    html_content = body.get("html_content")
    html_filename = body.get("html_filename", "page.html")
    test_cases = body.get("test_cases", [])
    prompt = body.get("prompt", "")
    framework = body.get("framework", "pytest")
    browser = body.get("browser", "chrome")
    include_kb_context = body.get("include_kb_context", True)
    
    if not html_content:
        raise HTTPException(400, "html_content is required")
    
    if isinstance(html_content, str) and html_content.startswith("data:"):
        import base64
        html_content = base64.b64decode(html_content.split(",")[1])
    elif isinstance(html_content, str):
        html_content = html_content.encode('utf-8')
    
    saved_path, file_url = save_html_file(html_content, html_filename)
    
    retrieved_docs = []
    if include_kb_context and prompt:
        try:
            model = get_embedding_model()
            query_embedding = model.encode(prompt).tolist()
            results = query_top_k(query_embedding, k=5)
            
            if results and results.get("documents") and len(results["documents"][0]) > 0:
                ids = results.get("ids", [[]])[0]
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                
                for doc_id, doc_text, meta in zip(ids, documents, metadatas):
                    retrieved_docs.append({
                        "id": doc_id,
                        "text": doc_text,
                        "source": meta.get("source", "unknown")
                    })
        except Exception as e:
            print(f"Warning: KB context retrieval failed: {e}")
    
    try:
        if test_cases and len(test_cases) > 0:
            result = generate_selenium_script(
                html_content=html_content,
                test_cases=test_cases,
                retrieved_docs=retrieved_docs,
                framework=framework,
                browser=browser
            )
        else:
            default_test_case = {
                "title": "Basic Form Interaction Test",
                "description": "Test form filling and submission",
                "steps": [
                    "Navigate to the page",
                    "Fill in all required form fields",
                    "Click submit button",
                    "Verify successful submission"
                ],
                "expected_result": "Form is submitted successfully"
            }
            result = generate_selenium_from_test_case_only(
                test_case=default_test_case,
                html_content=html_content,
                framework=framework,
                browser=browser
            )

        script = result["script"]
        script = script.replace('https://example.com/page.html', file_url)
        script = script.replace('file:///path/to/page.html', file_url)
        
        return {
            "status": "success",
            "script": script,
            "framework": result["framework"],
            "browser": result["browser"],
            "test_cases_covered": result.get("test_cases_covered", 1),
            "elements_mapped": result.get("elements_mapped", 0),
            "html_filename": html_filename,
            "html_path": saved_path,
            "html_url": file_url,
            "metadata": result.get("metadata", {}),
            "kb_context_used": len(retrieved_docs) > 0,
            "retrieved_chunks": len(retrieved_docs)
        }
        
    except Exception as e:
        raise HTTPException(500, f"Selenium script generation failed: {str(e)}")


@app.post("/parse-html")
async def parse_html_endpoint(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON body: {str(e)}")
    
    html_content = body.get("html_content")
    if not html_content:
        raise HTTPException(400, "html_content is required")

    if isinstance(html_content, str) and html_content.startswith("data:"):
        import base64
        html_content = base64.b64decode(html_content.split(",")[1])
    
    try:
        structure = parse_html_structure(html_content)
        return {
            "status": "success",
            "structure": structure
        }
    except Exception as e:
        raise HTTPException(500, f"HTML parsing failed: {str(e)}")


@app.post("/generate-selenium-simple")
async def generate_selenium_simple(
    html_file: UploadFile = File(...),
    framework: str = "pytest",
    browser: str = "chrome"
):
    if not html_file:
        raise HTTPException(400, "HTML file is required")
    
    html_content = await html_file.read()
    
    saved_path, file_url = save_html_file(html_content, html_file.filename)
    
    default_test_case = {
        "title": "Automated UI Test",
        "description": "Comprehensive UI interaction test",
        "steps": [
            "Open the webpage",
            "Interact with all form elements",
            "Submit forms and verify responses",
            "Test navigation and links"
        ],
        "expected_result": "All UI elements work correctly"
    }
    
    try:
        result = generate_selenium_from_test_case_only(
            test_case=default_test_case,
            html_content=html_content,
            framework=framework,
            browser=browser
        )
        
        script = result["script"]
        script = script.replace('https://example.com/page.html', file_url)
        script = script.replace('file:///path/to/page.html', file_url)
        
        return {
            "status": "success",
            "script": script,
            "framework": framework,
            "browser": browser,
            "html_filename": html_file.filename,
            "html_path": saved_path,
            "html_url": file_url,
            "metadata": result.get("metadata", {})
        }
    except Exception as e:
        raise HTTPException(500, f"Selenium script generation failed: {str(e)}")
