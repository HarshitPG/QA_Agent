from typing import List
from sentence_transformers import SentenceTransformer

_model = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_texts(texts: List[str]) -> List[List[float]]:
    model = get_embedding_model()
    vectors = model.encode(texts, convert_to_numpy=True)
    return vectors.tolist()
