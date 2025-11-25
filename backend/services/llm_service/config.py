import os
from dotenv import load_dotenv

load_dotenv()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
MODEL_TOKEN_LIMITS = {
    "llama3.2": 4096,
    "llama3.1": 8192,
    "llama2": 4096,
    "mistral": 8192,
    "qwen2.5": 8192,
    "codellama": 4096,
    "llama-3.1-8b-instant": 131072,
    "llama-3.1-70b-versatile": 131072,
    "llama-3.3-70b-versatile": 131072,
    "openai/gpt-oss-120b": 131072,
    "openai/gpt-oss-20b": 131072
}
if LLM_PROVIDER == "groq":
    MODEL_WINDOW = MODEL_TOKEN_LIMITS.get(GROQ_MODEL, 131072)
    RESERVED_RESPONSE_TOKENS = 4000  
else:
    MODEL_WINDOW = MODEL_TOKEN_LIMITS.get(OLLAMA_MODEL.split(":")[0], 8192)
    RESERVED_RESPONSE_TOKENS = 1200

AVAILABLE_CONTEXT_TOKENS = MODEL_WINDOW - RESERVED_RESPONSE_TOKENS
CORPUS_STATS_FILE = "logs/corpus_stats.json"
STOP_TOKEN = "</END_JSON>"
GENERATION_TEMPERATURE = float(os.getenv("GENERATION_TEMPERATURE", "0.2"))
GENERATION_TOP_P = 0.9
GENERATION_TOP_K = 40

GROQ_RATE_LIMITS = {
    "llama-3.1-8b-instant": {"tpm": 250000, "rpm": 1000},
    "llama-3.1-70b-versatile": {"tpm": 300000, "rpm": 1000},
    "llama-3.3-70b-versatile": {"tpm": 300000, "rpm": 1000},
    "openai/gpt-oss-120b": {"tpm": 250000, "rpm": 1000},
    "openai/gpt-oss-20b": {"tpm": 250000, "rpm": 1000}
}
VALIDATION_PATTERNS = {
    "price": {
        "pattern": r'\$\d+(?:\.\d{2})?',
        "enabled": True,
        "description": "USD price format ($10, $10.99)"
    },
    "percentage": {
        "pattern": r'\d+%',
        "enabled": True,
        "description": "Percentage values (10%, 50%)"
    },
    "code": {
        "pattern": r'\b[A-Z][A-Z0-9]{3,}\b',
        "enabled": True,
        "description": "Uppercase codes (SAVE10, FREESHIP)",
        "blacklist": {"STEP", "TEST", "HTTP", "JSON", "NOTE", "TODO", "FAIL", "PASS", 
                     "MISSING", "POST", "GET", "PUT", "DELETE", "TRUE", "FALSE", "NULL"}
    }
}
MAX_TEXT_SIZE = int(os.getenv("MAX_TEXT_SIZE", "5000000"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
