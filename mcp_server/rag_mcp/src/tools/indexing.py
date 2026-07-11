from qdrant_client import QdrantClient, models
from llm.llm import get_embedding_model

def indexing(qdrant_client: QdrantClient, collection_name: str, payload: list[dict], key_to_embed: str):
    
    points = []
    model = get_embedding_model()
    try:
        for item in payload:
            if "id" not in item:
                return f"Error indexing payload: id is required"
            if key_to_embed not in item:
                return f"Error indexing payload: key_to_embed is required"
            item["key_to_embed"] = key_to_embed
            point = models.PointStruct(
                id=item["id"],
                vector=model.encode(item[key_to_embed]),
                payload=item,
            )
            points.append(point)

        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        return f"Payload indexed successfully into collection {collection_name}"
    except Exception as e:
        return f"Error indexing payload: {e}"