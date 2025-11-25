
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
from backend.services.embedding_service import get_embedding_model
from backend.services.config_semantic import THRESHOLDS

logger = logging.getLogger(__name__)


class SemanticMatcher:

    
    def __init__(self):
        self.model = get_embedding_model()
        self._embedding_cache = {}
    
    @lru_cache(maxsize=1000)
    def _get_cached_embedding(self, text: str) -> np.ndarray:
        return self.model.encode(text)
    
    def _cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
    
    def match_checkbox_purpose(self, checkbox_attrs: Dict) -> Tuple[str, float]:
        desc_parts = []
        if checkbox_attrs.get('label'):
            desc_parts.append(checkbox_attrs['label'])
        if checkbox_attrs.get('id'):
            desc_parts.append(checkbox_attrs['id'].replace('-', ' ').replace('_', ' '))
        if checkbox_attrs.get('name'):
            desc_parts.append(checkbox_attrs['name'].replace('-', ' ').replace('_', ' '))
        
        if not desc_parts:
            return "unknown", 0.0
        
        checkbox_desc = ' '.join(desc_parts).lower()
        
        purpose_intents = {
            "terms": "accept terms and conditions legal agreement policy",
            "newsletter": "subscribe to newsletter email updates marketing",
            "consent": "consent to data usage privacy agreement permissions",
            "notification": "enable notifications alerts push messages",
            "feature": "enable feature option preference setting"
        }
        
        try:
            checkbox_emb = self._get_cached_embedding(checkbox_desc)
            
            best_purpose = "unknown"
            best_score = 0.0
            
            for purpose, intent_desc in purpose_intents.items():
                intent_emb = self._get_cached_embedding(intent_desc)
                similarity = self._cosine_similarity(checkbox_emb, intent_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_purpose = purpose
            
            return best_purpose, best_score
            
        except Exception as e:
            logger.error(f"Checkbox semantic matching failed: {e}")
            return "unknown", 0.0
    
    def match_radio_option_intent(self, step_text: str, radio_options: List[Dict]) -> Optional[str]:
        if not radio_options:
            return None
        
        try:
            step_emb = self._get_cached_embedding(step_text.lower())
            
            best_match = None
            best_score = 0.0
            
            for option in radio_options:
                option_desc_parts = []
                if option.get('value'):
                    option_desc_parts.append(str(option['value']))
                if option.get('label'):
                    option_desc_parts.append(option['label'])
                if option.get('id'):
                    option_desc_parts.append(option['id'].replace('-', ' ').replace('_', ' '))
                
                if not option_desc_parts:
                    continue
                
                option_desc = ' '.join(option_desc_parts).lower()
                option_emb = self._get_cached_embedding(option_desc)
                
                similarity = self._cosine_similarity(step_emb, option_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = option.get('id')

            if best_score > THRESHOLDS['radio_match']:
                return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"Radio option semantic matching failed: {e}")
            return None
    
    def detect_input_purpose(self, input_attrs: Dict) -> Tuple[str, float]:
        desc_parts = []
        if input_attrs.get('placeholder'):
            desc_parts.append(input_attrs['placeholder'])
        if input_attrs.get('id'):
            desc_parts.append(input_attrs['id'].replace('-', ' ').replace('_', ' '))
        if input_attrs.get('name'):
            desc_parts.append(input_attrs['name'].replace('-', ' ').replace('_', ' '))
        if input_attrs.get('aria_label'):
            desc_parts.append(input_attrs['aria_label'])
        if input_attrs.get('type'):
            desc_parts.append(input_attrs['type'])
        
        if not desc_parts:
            return "text", 0.0
        
        input_desc = ' '.join(desc_parts).lower()
        
        purpose_intents = {
            "email": "email address electronic mail contact",
            "phone": "phone number telephone mobile contact",
            "postal": "zip code postal code location address",
            "promo": "promo code coupon discount voucher gift card referral reward offer",
            "payment": "credit card payment billing card number cvv expiry",
            "search": "search query find lookup",
            "date": "date calendar appointment schedule",
            "password": "password secret credentials secure",
            "name": "name full name first name last name",
            "address": "address street city location"
        }
        
        try:
            input_emb = self._get_cached_embedding(input_desc)
            
            best_purpose = "text"
            best_score = 0.0
            
            for purpose, intent_desc in purpose_intents.items():
                intent_emb = self._get_cached_embedding(intent_desc)
                similarity = self._cosine_similarity(input_emb, intent_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_purpose = purpose
            
            return best_purpose, best_score
            
        except Exception as e:
            logger.error(f"Input purpose semantic matching failed: {e}")
            return "text", 0.0
    
    def is_validation_context_zero_cost(self, context_text: str) -> Tuple[bool, float]:
        import re
        
        cost_price_pattern = r'(?:cost|fee|charge|price)(?:s)?\s+(?:is\s+)?\$(?!0(?:\.00)?(?:\s|$))\d+(?:\.\d{2})?'
        if re.search(cost_price_pattern, context_text.lower()):
            return False, 0.0
        
        zero_cost_intents = [
            "waived fee free of charge discount",
            "complimentary no cost included gift",
            "free service gratis no charge",
            "zero cost no fee included free",
            "free shipping delivery no cost",
            "gift included complimentary bonus"
        ]
        
        cost_intents = [
            "costs price payment",
            "charged amount billing",
            "cost is price is"
        ]
        
        try:
            context_emb = self._get_cached_embedding(context_text.lower())
            
            max_zero_similarity = 0.0
            for intent in zero_cost_intents:
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(context_emb, intent_emb)
                max_zero_similarity = max(max_zero_similarity, similarity)
            
            max_cost_similarity = 0.0
            for intent in cost_intents:
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(context_emb, intent_emb)
                max_cost_similarity = max(max_cost_similarity, similarity)
            
            is_zero_cost = (max_zero_similarity > 0.45 and 
                           max_zero_similarity > (max_cost_similarity + 0.1))
            return is_zero_cost, max_zero_similarity
            
        except Exception as e:
            logger.error(f"Zero cost detection failed: {e}")
            return False, 0.0
    
    def match_button_action(self, step_text: str) -> Tuple[bool, float]:
        try:
            step_emb = self._get_cached_embedding(step_text.lower())
            
            action_intents = [
                "click button press tap",
                "submit form send data",
                "proceed continue next forward",
                "confirm okay accept approve",
                "add insert create new",
                "trigger activate execute run",
                "push hit apply go",
                "launch start begin initiate",
                "process complete finish done",
                "purchase buy checkout pay"
            ]
            
            max_similarity = 0.0
            for intent in action_intents:
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(step_emb, intent_emb)
                max_similarity = max(max_similarity, similarity)
            
            threshold = THRESHOLDS.get("button_action", 0.35)
            is_action = max_similarity > threshold
            
            logger.debug(f"Button action match: '{step_text}' → {is_action} (score: {max_similarity:.3f})")
            return is_action, max_similarity
            
        except Exception as e:
            logger.error(f"Button action detection failed: {e}")
            return False, 0.0
    
    def match_select_action(self, step_text: str) -> Tuple[bool, float]:
        try:
            step_emb = self._get_cached_embedding(step_text.lower())
            
            select_intents = [
                "select choose pick option",
                "dropdown menu list picker",
                "opt for go with use",
                "set to change to switch to",
                "filter by sort by group by"
            ]
            
            max_similarity = 0.0
            for intent in select_intents:
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(step_emb, intent_emb)
                max_similarity = max(max_similarity, similarity)
            
            threshold = THRESHOLDS.get("select_action", 0.25)
            is_select = max_similarity > threshold
            
            logger.debug(f"Select action match: '{step_text}' → {is_select} (score: {max_similarity:.3f})")
            return is_select, max_similarity
            
        except Exception as e:
            logger.error(f"Select action detection failed: {e}")
            return False, 0.0
    
    def classify_document_type(self, source: str, content_sample: str = "") -> Tuple[str, float]:
        try:
            text = f"{source} {content_sample}".lower()
            text_emb = self._get_cached_embedding(text)
            
            doc_type_intents = {
                'specification': "product requirements features functionality specification guideline standard blueprint architecture schema definition",
                'validation_rules': "validation rules constraints checks policy verify sanitize validate compliance regulation requirement",
                'api_documentation': "api endpoint rest graphql webhook openapi swagger microservice service integration protocol",
                'ui_guidelines': "ui ux design interface mockup wireframe prototype component layout theme style visual brand"
            }
            
            best_type = 'general'
            best_score = 0.0
            
            for doc_type, intent in doc_type_intents.items():
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(text_emb, intent_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_type = doc_type
            
            threshold = THRESHOLDS.get("document_classification", 0.38)
            if best_score < threshold:
                best_type = 'general'
                best_score = 0.3
            
            logger.debug(f"Document classification: '{source}' → {best_type} (score: {best_score:.3f})")
            return best_type, best_score
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return 'general', 0.3
    
    def is_verification_step(self, step_text: str) -> Tuple[bool, float]:
        """
        Detect if a test step is a verification/assertion step (not an action)
        Uses semantic similarity to identify steps that verify/assert/check conditions
        
        Args:
            step_text: The test step text
        
        Returns:
            (is_verification, confidence_score)
        
        Examples:
        - "Verify that the error message is displayed" → (True, 0.89)
        - "Assert payment was successful" → (True, 0.85)
        - "Check if discount is applied" → (True, 0.82)
        - "Fill in the name field" → (False, 0.15)
        - "Click the submit button" → (False, 0.20)
        """
        try:
            step_lower = step_text.lower().strip()
   
            if any(pattern in step_lower for pattern in ['check if', 'check that', 'check whether']):
                return (True, 0.95)
            
            step_emb = self._get_cached_embedding(step_lower)
            
            verification_intents = [
                "verify check assert validate confirm",
                "ensure make sure that if whether",
                "expect should must display show",
                "see observe notice detect",
                "error message warning alert notification",
                "success confirmation completed finished",
                "disabled enabled visible hidden",
                "displayed shown appears rendered",
                "applied correctly successfully properly"
            ]
            
            max_verification_similarity = 0.0
            for intent in verification_intents:
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(step_emb, intent_emb)
                max_verification_similarity = max(max_verification_similarity, similarity)
            
            action_intents = [
                "click press tap submit",
                "fill enter type input",
                "select choose pick opt",
                "open close start stop"
            ]
            
            max_action_similarity = 0.0
            for intent in action_intents:
                intent_emb = self._get_cached_embedding(intent)
                similarity = self._cosine_similarity(step_emb, intent_emb)
                max_action_similarity = max(max_action_similarity, similarity)
            
            is_verification = (max_verification_similarity > 0.30 and 
                             max_verification_similarity > (max_action_similarity + 0.08))
            
            logger.debug(f"Verification detection: '{step_text}' → {is_verification} (ver: {max_verification_similarity:.3f}, act: {max_action_similarity:.3f})")
            return is_verification, max_verification_similarity
            
        except Exception as e:
            logger.error(f"Verification detection failed: {e}")
            return False, 0.0
    
    def detect_payment_field(self, field_attrs: Dict) -> Tuple[bool, str, float]:
        desc_parts = []
        for key in ['id', 'name', 'placeholder', 'aria_label']:
            if field_attrs.get(key):
                desc_parts.append(str(field_attrs[key]).replace('-', ' ').replace('_', ' '))
        
        if not desc_parts:
            return False, "", 0.0
        
        field_desc = ' '.join(desc_parts).lower()
        
        payment_field_intents = {
            "card_number": "credit card number debit card account number",
            "cvv": "cvv cvc security code verification code",
            "expiry": "expiration date expiry date valid through",
            "card_holder": "card holder name cardholder billing name",
            "billing_zip": "billing zip postal code billing address",
            "routing_number": "routing number aba number bank code",
            "account_number": "account number bank account checking",
            "iban": "iban international bank account number",
            "swift": "swift code bic bank identifier"
        }
        
        try:
            field_emb = self._get_cached_embedding(field_desc)
            
            best_type = ""
            best_score = 0.0
            
            for field_type, intent_desc in payment_field_intents.items():
                intent_emb = self._get_cached_embedding(intent_desc)
                similarity = self._cosine_similarity(field_emb, intent_emb)
                
                if similarity > best_score:
                    best_score = similarity
                    best_type = field_type
            
            is_payment = best_score > 0.4
            return is_payment, best_type if is_payment else "", best_score
            
        except Exception as e:
            logger.error(f"Payment field detection failed: {e}")
            return False, "", 0.0


_semantic_matcher = None

def get_semantic_matcher() -> SemanticMatcher:
    global _semantic_matcher
    if _semantic_matcher is None:
        _semantic_matcher = SemanticMatcher()
    return _semantic_matcher
