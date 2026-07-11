from qdrant_client import QdrantClient, models
import os

def create_collection(qdrant_client: QdrantClient, collection_name: str):

    try:
        # Create the collection with specified vector parameters
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=os.getenv("VECTOR_SIZE"),  # Dimensionality of the vectors
                distance=models.Distance.COSINE  # Distance metric for similarity search
            )
        )
        return f"Collection {collection_name} created successfully"
    except Exception as e:
        return f"Error creating collection: {e}"