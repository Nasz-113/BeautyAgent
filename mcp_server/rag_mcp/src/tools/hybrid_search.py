from qdrant_client import QdrantClient
from llm.llm import get_embedding_model

async def hybrid_search(qdrant_client: QdrantClient, collection_name: str, query: str, k: int):
    
    model = get_embedding_model()
    try:
        results = qdrant_client.query_points(
            collection_name=collection_name,
            query=model.encode(query),
            limit=k
        )
        text_results = []
        for result in results:
            text_results.append(result.payload["text"])
        return text_results
    except Exception as e:
        return f"Error hybrid searching: {e}"