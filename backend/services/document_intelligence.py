
import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from functools import lru_cache
from pathlib import Path
import json

from backend.services.embedding_service import get_embedding_model

logger = logging.getLogger(__name__)


class DocumentIntelligence:

    
    def __init__(self, support_docs_paths: List[str] = None):

        self.model = get_embedding_model()
        self.support_docs_paths = support_docs_paths or []
        self.document_cache = {}
        self._load_documents()
    
    def _load_documents(self):

        for doc_path in self.support_docs_paths:
            try:
                path = Path(doc_path)
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.document_cache[path.name] = {
                            'content': content,
                            'path': str(path),
                            'type': self._classify_document_content(content, path.name)
                        }
                        logger.info(f"Loaded document: {path.name} (type: {self.document_cache[path.name]['type']})")
            except Exception as e:
                logger.warning(f"Could not load document {doc_path}: {e}")
    
    def _classify_document_content(self, content: str, filename: str) -> str:
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        if any(kw in content_lower for kw in ['discount', 'coupon', 'promo', 'code']):
            return 'discount_rules'
        elif any(kw in content_lower for kw in ['product', 'item', 'catalog', 'price']):
            return 'product_catalog'
        elif any(kw in content_lower for kw in ['validation', 'rule', 'constraint', 'regex']):
            return 'validation_rules'
        elif any(kw in content_lower for kw in ['api', 'endpoint', 'route']):
            return 'api_spec'
        else:
            return 'general'
    
    @lru_cache(maxsize=500)
    def _get_embedding(self, text: str):
        return self.model.encode(text)
    
    def _semantic_similarity(self, text1: str, text2: str) -> float:
        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
    
    def extract_discount_codes(self, context: str = "") -> List[Dict[str, Any]]:

        discount_codes = []
        
        for doc_name, doc_data in self.document_cache.items():
            content = doc_data['content']
            
            table_pattern = r'\|\s*([A-Z0-9]+)\s*\|([^|]+)\|([^|]+)\|'
            matches = re.finditer(table_pattern, content, re.MULTILINE)
            
            for match in matches:
                code = match.group(1).strip()
                description = match.group(2).strip()
                value = match.group(3).strip()
                
                if re.match(r'^[A-Z0-9]{4,15}$', code):
                    discount_codes.append({
                        'code': code,
                        'description': description,
                        'value': value,
                        'confidence': 0.95,
                        'source': doc_name
                    })
            

            list_pattern = r'\b([A-Z0-9]{4,15})\b\s*[-:–]\s*([^.\n]+)'
            matches = re.finditer(list_pattern, content)
            
            for match in matches:
                code = match.group(1).strip()
                description = match.group(2).strip()

                context_window = content[max(0, match.start()-100):match.end()+100].lower()
                if any(kw in context_window for kw in ['discount', 'coupon', 'promo', 'code', 'save', 'off']):
                    if not any(dc['code'] == code for dc in discount_codes):  
                        discount_codes.append({
                            'code': code,
                            'description': description,
                            'value': 'See document for details',
                            'confidence': 0.85,
                            'source': doc_name
                        })
            

            if 'discount' in content.lower() or 'coupon' in content.lower():

                sections = re.split(r'\n#{1,3}\s+', content)
                for section in sections:
                    if any(kw in section.lower() for kw in ['discount', 'coupon', 'promo']):
                        codes_in_section = re.findall(r'\b([A-Z]{4,15})\b', section)
                        for code in codes_in_section:
                            if re.match(r'^[A-Z0-9]{4,15}$', code) and code not in ['HTTPS', 'HTTP', 'POST', 'GET']:
                                if not any(dc['code'] == code for dc in discount_codes):
                                    discount_codes.append({
                                        'code': code,
                                        'description': 'Extracted from discount section',
                                        'value': 'See document',
                                        'confidence': 0.75,
                                        'source': doc_name
                                    })

        discount_codes.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"Extracted {len(discount_codes)} discount codes from documents")
        for dc in discount_codes:
            logger.debug(f"  - {dc['code']}: {dc['description']} (confidence: {dc['confidence']:.2f})")
        
        return discount_codes
    
    def extract_product_ids(self) -> List[Dict[str, Any]]:

        products = []
        
        for doc_name, doc_data in self.document_cache.items():
            content = doc_data['content']

            id_pattern = r'(?:ID|id|Product\s*ID):\s*([A-Z0-9-]+)'
            matches = re.finditer(id_pattern, content)
            
            for match in matches:
                product_id = match.group(1).strip()
                
                context = content[max(0, match.start()-200):match.end()+200]
                
                name_match = re.search(r'\*\*([^*]+)\*\*', context)
                name = name_match.group(1).strip() if name_match else 'Unknown Product'
                
                price_match = re.search(r'\$\s*(\d+(?:\.\d{2})?)', context)
                price = f"${price_match.group(1)}" if price_match else 'N/A'
                
                products.append({
                    'id': product_id,
                    'name': name,
                    'price': price,
                    'confidence': 0.90,
                    'source': doc_name
                })
        
        logger.info(f"Extracted {len(products)} product IDs from documents")
        return products
    
    def extract_valid_input_value(self, field_purpose: str, field_name: str = "", 
                                   field_attrs: Dict = None) -> Tuple[Optional[str], float]:

        if field_purpose in ['promo', 'discount', 'coupon']:
            codes = self.extract_discount_codes()
            if codes:
                best_code = codes[0]  
                logger.info(f"Using extracted discount code: {best_code['code']} from {best_code['source']}")
                return best_code['code'], best_code['confidence']

        if field_purpose in ['product', 'product_id', 'item_id']:
            products = self.extract_product_ids()
            if products:
                best_product = products[0]
                logger.info(f"Using extracted product ID: {best_product['id']} from {best_product['source']}")
                return best_product['id'], best_product['confidence']
        
        if field_purpose == 'email':
            for doc_name, doc_data in self.document_cache.items():
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, doc_data['content'])
                if emails:
                    real_emails = [e for e in emails if 'example.com' not in e.lower() and 'test.com' not in e.lower()]
                    if real_emails:
                        logger.info(f"Using extracted email: {real_emails[0]} from {doc_name}")
                        return real_emails[0], 0.85
        

        if field_purpose == 'phone':
            for doc_name, doc_data in self.document_cache.items():
                phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
                phones = re.findall(phone_pattern, doc_data['content'])
                if phones:
                    phone = f"({phones[0][0]}) {phones[0][1]}-{phones[0][2]}"
                    logger.info(f"Using extracted phone: {phone} from {doc_name}")
                    return phone, 0.85
        
        return None, 0.0
    
    def validate_generated_value(self, field_purpose: str, value: str) -> Tuple[bool, float, str]:

        if field_purpose in ['promo', 'discount', 'coupon']:
            valid_codes = self.extract_discount_codes()
            valid_code_list = [dc['code'] for dc in valid_codes]
            
            if value in valid_code_list:
                return True, 0.95, f"Code '{value}' found in support documents"
            else:
                return False, 0.0, f"Code '{value}' not found. Valid codes: {', '.join(valid_code_list[:3])}"
        
        if field_purpose in ['product', 'product_id']:
            valid_products = self.extract_product_ids()
            valid_ids = [p['id'] for p in valid_products]
            
            if value in valid_ids:
                return True, 0.95, f"Product ID '{value}' found in support documents"
            else:
                return False, 0.0, f"Product ID '{value}' not found. Valid IDs: {', '.join(valid_ids[:3])}"

        for doc_name, doc_data in self.document_cache.items():
            if doc_data['type'] == 'validation_rules':
                content = doc_data['content']

                if field_purpose in content.lower():
                    regex_pattern = r'regex:\s*([^\n]+)'
                    regex_match = re.search(regex_pattern, content, re.IGNORECASE)
                    if regex_match:
                        pattern = regex_match.group(1).strip()
                        pattern = pattern.strip('/').strip()
                        try:
                            if re.match(pattern, value):
                                return True, 0.85, f"Value matches regex pattern from {doc_name}"
                            else:
                                return False, 0.0, f"Value does not match regex pattern: {pattern}"
                        except re.error:
                            logger.warning(f"Invalid regex pattern: {pattern}")
        
        return True, 0.5, "No validation rules found in documents"


_document_intelligence = None


def get_document_intelligence(support_docs_paths: List[str] = None) -> DocumentIntelligence:

    global _document_intelligence
    
    if _document_intelligence is None:
        if support_docs_paths is None:
            from pathlib import Path
            base_path = Path(__file__).parent.parent.parent
            support_docs_paths = [
                str(base_path / 'supportDocs' / 'product_specs.md'),
                str(base_path / 'supportDocs' / 'validation_rules.txt'),
                str(base_path / 'supportDocs' / 'api_endpoints.json'),
                str(base_path / 'supportDocs' / 'ui_ux_guide.txt'),
            ]
        
        _document_intelligence = DocumentIntelligence(support_docs_paths)
        logger.info("DocumentIntelligence singleton initialized")
    
    return _document_intelligence



import numpy as np
