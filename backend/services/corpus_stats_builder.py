
import json
import os
import re
import logging
from collections import Counter
from typing import List, Dict

logger = logging.getLogger(__name__)

CORPUS_STATS_FILE = "logs/corpus_stats.json"


def build_corpus_statistics(chunks: List[Dict]):

    try:
        df_map = Counter()
        
        for chunk in chunks:
            text = chunk.get("text", "").lower()
            terms = set(re.findall(r'\w+', text))  
            for term in terms:
                df_map[term] += 1

        corpus_stats = {
            "total_docs": len(chunks),
            "df_map": dict(df_map),
            "generated_at": str(__import__('datetime').datetime.now())
        }
        
        os.makedirs("logs", exist_ok=True)
        
        with open(CORPUS_STATS_FILE, 'w') as f:
            json.dump(corpus_stats, f, indent=2)
        
        logger.info(f" Built corpus statistics: {len(chunks)} chunks, {len(df_map)} unique terms")
        return corpus_stats
        
    except Exception as e:
        logger.error(f"Failed to build corpus statistics: {e}")
        return None


def update_corpus_statistics_from_vectorstore(vectorstore):

    try:

        results = vectorstore._collection.get()
        
        chunks = []
        if results and results.get("documents"):
            for doc in results["documents"]:
                chunks.append({"text": doc})
        
        if chunks:
            return build_corpus_statistics(chunks)
        else:
            logger.warning("No chunks found in vectorstore")
            return None
            
    except Exception as e:
        logger.error(f"Failed to update corpus stats from vectorstore: {e}")
        return None
