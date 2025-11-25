import re
import math
import os
import json
import logging
from typing import List, Dict
from collections import Counter

logger = logging.getLogger(__name__)

DF_MAP = {}
TOTAL_DOCS = 0


def load_corpus_statistics(corpus_stats_file: str = "logs/corpus_stats.json"):
    
    global DF_MAP, TOTAL_DOCS
    
    try:
        if os.path.exists(corpus_stats_file):
            with open(corpus_stats_file, 'r') as f:
                data = json.load(f)
                DF_MAP = data.get("df_map", {})
                TOTAL_DOCS = data.get("total_docs", 0)
                logger.info(f"Loaded corpus stats: {TOTAL_DOCS} docs, {len(DF_MAP)} terms")
    except Exception as e:
        logger.warning(f"Could not load corpus stats: {e}")


def calculate_bm25_score(query: str, document: str, k1: float = 1.5, b: float = 0.75) -> float:
    
    query_terms = set(re.findall(r'\w+', query.lower()))
    doc_terms = re.findall(r'\w+', document.lower())
    doc_length = len(doc_terms)
    avg_doc_length = 500
    
    score = 0.0
    doc_term_freq = Counter(doc_terms)
    total_docs_for_idf = max(TOTAL_DOCS, 1)
    
    for term in query_terms:
        tf = doc_term_freq.get(term, 0)
        if tf > 0:
            df = DF_MAP.get(term, 0)
            idf = math.log((1 + total_docs_for_idf) / (1 + df)) + 1.0
            
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
            score += idf * (numerator / denominator)
    
    return score


def classify_document_type(source: str) -> str:
    
    from backend.services.semantic_matcher import get_semantic_matcher
    
    try:
        semantic_matcher = get_semantic_matcher()
        doc_type, confidence = semantic_matcher.classify_document_type(source)
        logger.debug(f"Document '{source}' classified as '{doc_type}' (confidence: {confidence:.3f})")
        return doc_type
    except Exception as e:
        logger.error(f"Document classification failed, using fallback: {e}")
        source_lower = source.lower()
        if 'spec' in source_lower or 'requirement' in source_lower:
            return 'specification'
        elif 'validation' in source_lower or 'rule' in source_lower:
            return 'validation_rules'
        elif 'api' in source_lower:
            return 'api_documentation'
        elif 'ui' in source_lower or 'ux' in source_lower:
            return 'ui_guidelines'
        else:
            return 'general'


def hybrid_rank_chunks(chunks: List[Dict], query: str, weights: Dict[str, float] = None) -> List[Dict]:
    
    if weights is None:
        weights = {
            "embedding": 0.50,
            "bm25": 0.30,
            "metadata": 0.15,
            "phrase": 0.05
        }
    doc_type_weights = {
        'specification': 1.5,
        'validation_rules': 1.4,
        'api_documentation': 1.3,
        'ui_guidelines': 1.1,
        'general': 1.0
    }
    
    ranked_chunks = []
    
    for chunk in chunks:
        new_chunk = dict(chunk)
        embedding_score = chunk.get("distance", 1.0)
        embedding_score = 1.0 - embedding_score
        
        text = chunk.get("text", "")
        bm25_score = calculate_bm25_score(query, text)
        bm25_normalized = min(1.0, bm25_score / 10.0)
        metadata_score = 0.5
        if len(text) > 100:
            metadata_score += 0.2
        if len(text) > 500:
            metadata_score += 0.1
        
        source = chunk.get("source", "")
        doc_type = classify_document_type(source)
        new_chunk["doc_type"] = doc_type
        
        phrase_score = 0.0
        query_words = query.lower().split()
        if len(query_words) >= 2:
            for i in range(len(query_words) - 1):
                phrase = f"{query_words[i]} {query_words[i+1]}"
                if phrase in text.lower():
                    phrase_score += 0.25
        phrase_score = min(1.0, phrase_score)
        hybrid_score = (
            embedding_score * weights["embedding"] +
            bm25_normalized * weights["bm25"] +
            metadata_score * weights["metadata"] +
            phrase_score * weights["phrase"]
        )
        type_weight = doc_type_weights.get(doc_type, 1.0)
        hybrid_score *= type_weight
        
        new_chunk["hybrid_score"] = hybrid_score
        new_chunk["bm25_score"] = bm25_score
        ranked_chunks.append(new_chunk)
    
    ranked_chunks.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)
    if ranked_chunks:
        top_score = ranked_chunks[0].get("hybrid_score", 0)
        logger.info(f"Hybrid ranking: Top score={top_score:.3f}, BM25 enabled")
    
    return ranked_chunks


def adaptive_test_generation_strategy(chunks: List[Dict], prompt: str) -> Dict:
    
    if not chunks:
        return {
            "strategy": "abort",
            "confidence": 0.0,
            "recommendation": "No relevant documentation found.",
            "should_proceed": False
        }
    prompt_lower = prompt.lower()
    all_text = " ".join([chunk.get("text", "") for chunk in chunks]).lower()
    prompt_terms = set(re.findall(r'\b[a-z0-9]{3,}\b', prompt_lower))
    common_words = {
        'test', 'case', 'cases', 'generate', 'create', 'make', 'for', 'the', 'and', 'that', 'this', 
        'with', 'from', 'will', 'should', 'would', 'could', 'have', 'been', 'which', 'their', 'what', 
        'about', 'when', 'where', 'there', 'some', 'into', 'than', 'them', 'these', 'those', 'your', 
        'write', 'using', 'verify', 'check', 'validate', 'ensure', 'positive', 'negative', 'scenario',
        'step', 'steps', 'result', 'expected', 'outcome', 'feature', 'function', 'system', 'application'
    }
    prompt_domain_terms = prompt_terms - common_words
    matched_terms = sum(1 for term in prompt_domain_terms if term in all_text)
    domain_overlap_ratio = matched_terms / len(prompt_domain_terms) if prompt_domain_terms else 0
    
    logger.info(f"Domain relevance check: {matched_terms}/{len(prompt_domain_terms)} terms matched ({domain_overlap_ratio:.2%})")
    logger.info(f"Prompt domain terms: {list(prompt_domain_terms)[:10]}")
    logger.info(f"Matched terms: {[t for t in prompt_domain_terms if t in all_text][:10]}")
    if domain_overlap_ratio < 0.3:
        return {
            "strategy": "abort",
            "confidence": 0.0,
            "recommendation": f"Out-of-domain request. Only {domain_overlap_ratio:.0%} of prompt terms found in documentation. Cannot generate reliable test cases.",
            "should_proceed": False,
            "domain_relevance": domain_overlap_ratio
        }
    total_score = sum(chunk.get("hybrid_score", 0) for chunk in chunks)
    avg_score = total_score / len(chunks) if chunks else 0
    has_specifics = bool(re.findall(r'\$\d+|\d+%|[A-Z]{2,}\d+|P\d{3}', all_text))
    has_rules = any(kw in all_text for kw in [
        "must be", "should be", "required field", "limit", "constraint", 
        "validation", "error message", "minimum", "maximum"
    ])
    has_examples = any(kw in all_text for kw in [
        "example", "e.g.", "for instance", "such as"
    ])
    confidence = min(1.0, 
        domain_overlap_ratio * 0.5 +
        avg_score * 0.25 + 
        (0.15 if has_specifics else 0) + 
        (0.08 if has_rules else 0) +
        (0.02 if has_examples else 0)
    )
    
    if confidence < 0.4:
        strategy = "abort"
        recommendation = f"Documentation quality too low (confidence: {confidence:.2f}). Domain relevance: {domain_overlap_ratio:.0%}"
        should_proceed = False
    elif confidence < 0.6:
        strategy = "minimal"
        recommendation = "Low confidence. Generate basic test cases with warnings."
        should_proceed = True
    elif confidence < 0.8:
        strategy = "standard"
        recommendation = "Moderate confidence. Standard test case generation."
        should_proceed = True
    else:
        strategy = "comprehensive"
        recommendation = "High confidence. Comprehensive test coverage possible."
        should_proceed = True
    
    return {
        "strategy": strategy,
        "confidence": confidence,
        "recommendation": recommendation,
        "should_proceed": should_proceed,
        "has_specific_values": has_specifics,
        "has_validation_rules": has_rules,
        "has_examples": has_examples
    }

load_corpus_statistics()
