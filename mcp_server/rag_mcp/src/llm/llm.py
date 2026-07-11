from sentence_transformers import SentenceTransformer, CrossEncoder
import os

def get_embedding_model():
    return SentenceTransformer(os.getenv("EMBEDDING_MODEL"))

def get_reranker_model():
    return CrossEncoder(os.getenv("RERANKER_MODEL"))