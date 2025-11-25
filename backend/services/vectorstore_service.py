import os
from chromadb import PersistentClient

CHROMA_DIR = os.path.join(os.getcwd(), "vectorstore")

_client = None
_collection = None


def get_client():
    global _client
    if _client is None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        _client = PersistentClient(path=CHROMA_DIR)
    return _client


def get_collection(name: str = "qa_kb"):
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(name)
    return _collection


def upsert_chunks(chunks, embeddings):
    collection = get_collection()

    ids = [c["chunk_id"] for c in chunks]
    docs = [c["text"] for c in chunks]
    metas = [{"source": c["source"]} for c in chunks]

    collection.upsert(
        ids=ids,
        documents=docs,
        metadatas=metas,
        embeddings=embeddings
    )


def query_top_k(query_embedding, k=5):
    collection = get_collection()
    return collection.query(query_embeddings=[query_embedding], n_results=k)


def get_vectorstore():
    return get_collection()
