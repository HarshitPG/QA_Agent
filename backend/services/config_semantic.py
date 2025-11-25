


THRESHOLDS = {
    "semantic_match": 0.35,
    "final_action": 0.35,            
    "submit_button": 0.30,           
    "button_action": 0.35,           
    "checkbox_match": 0.40,          
    "radio_match": 0.40,             
    "negative_action": 0.50,         
    "select_action": 0.25,           
    "document_classification": 0.38, 
}


LLM_CONFIG = {
    "temperature": 0.2,
    "max_tokens": {
        "html": 600,
        "dependencies": 800,
        "test_cases": 4000,
    }
}


TEST_DATA_PATTERNS = {
    "email": "test_{random}@example.com",
    "phone": "555{random:7}",
    "zip": "{random:5}",
    "password": "Test@{random:3}",
    "date": "2024-{month:02d}-{day:02d}",
    "coupon": "TEST{random:4}",
    "generic_text": "Test Value",
}


class Priority:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
class TestType:
    POSITIVE = "positive"
    NEGATIVE = "negative"
    EDGE_CASE = "edge_case"


NEGATIVE_ACTIONS = [
    "cancel", "back", "close", "abort", "dismiss", 
    "exit", "quit", "reject", "decline", "delete",
    "remove", "discard", "clear", "reset"
]
