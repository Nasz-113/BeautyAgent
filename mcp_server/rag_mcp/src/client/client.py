from qdrant_client import QdrantClient
import os

def get_qdrant_client():
    try:
        return QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    except Exception as e:
        return f"Error getting qdrant client: {e}"