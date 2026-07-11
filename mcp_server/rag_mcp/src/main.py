from mcp.server.fastmcp import FastMCP
from tools.create_collection import create_collection
from tools.indexing import indexing
from tools.vector_search import vector_search
from tools.hybrid_search import hybrid_search
from tools.reranker import reranker
from client.client import get_qdrant_client
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("RAG MCP", json_response=True)

qdrant_client = get_qdrant_client()


@mcp.tool()
def create_collection_tool(collection_name: str):
    """
    Create a new Qdrant collection.

    Configures a collection with cosine distance and a vector size defined by the
    environment variable `VECTOR_SIZE`. If the collection already exists, an error
    message is returned.

    Parameters
    ----------
    collection_name : str
        The name of the collection to create. Must be unique in the Qdrant instance.

    Returns
    -------
    str
        A plain‑text message indicating success or an error description.

    Example
    -------
    >>> create_collection_tool("my_documents")
    "Collection my_documents created successfully"
    """
    return create_collection(qdrant_client, collection_name)


@mcp.tool()
def indexing_tool(collection_name: str, payload: list[dict], key_to_embed: str):
    """
    Index a list of documents into a Qdrant collection.

    Each item in the payload must contain a unique `id` and a text field whose name
    is given by `key_to_embed`. The text is embedded and stored, and the entire item
    (including the key name in `"key_to_embed"`) becomes the point’s payload.

    Parameters
    ----------
    collection_name : str
        Name of the target Qdrant collection (must already exist).
    payload : list of dict
        List of documents to index. Each dictionary must include:
        - ``"id"`` : str or int – unique point identifier.
        - ``key_to_embed`` : str – the text that will be turned into an embedding.
        Any other fields (e.g., ``"title"``, ``"source"``) are stored as metadata.
    key_to_embed : str
        The name of the field that contains the text to embed (e.g., ``"text"``).

    Returns
    -------
    str
        A success message like ``"Payload indexed successfully into collection ..."``
        or an error description starting with ``"Error indexing payload: "``.

    Example
    -------
    >>> indexing_tool(
    ...     collection_name="my_documents",
    ...     payload=[
    ...         {"id": 1, "text": "Quantum computing basics", "source": "wiki"},
    ...         {"id": 2, "text": "Deep learning overview", "source": "paper"}
    ...     ],
    ...     key_to_embed="text"
    ... )
    "Payload indexed successfully into collection my_documents"
    """
    return indexing(qdrant_client, collection_name, payload, key_to_embed)


@mcp.tool()
async def vector_search_tool(collection_name: str, query: str, k: int = 10):
    """
    Perform a dense vector (semantic) search over a collection.

    The query text is embedded with the same model used during indexing, and the
    top‑`k` nearest points are returned. **The response contains only the stored
    payloads – no relevance scores are included.**

    Parameters
    ----------
    collection_name : str
        Name of the Qdrant collection to search.
    query : str
        Natural language query, e.g. ``"What is quantum computing?"``.
    k : int, optional
        Maximum number of results to return (default 10).

    Returns
    -------
    list of dict
        A list of the payload dictionaries of the closest points, as they were
        stored during indexing (including the ``"key_to_embed"`` field that holds
        the name of the text field). If an error occurs, a string error message is
        returned instead.

    Example
    -------
    >>> await vector_search_tool("my_documents", "quantum computing", k=2)
    [
        {
            "id": 1,
            "text": "Quantum computing basics",
            "source": "wiki",
            "key_to_embed": "text"
        },
        {
            "id": 2,
            "text": "Deep learning overview",
            "source": "paper",
            "key_to_embed": "text"
        }
    ]
    """
    return await vector_search(qdrant_client, collection_name, query, k)


@mcp.tool()
async def hybrid_search_tool(collection_name: str, query: str, k: int = 10):
    """
    Perform a hybrid search combining dense vector and sparse keyword matching.

    Not functional yet
    """
    return await hybrid_search(qdrant_client, collection_name, query, k)


@mcp.tool()
async def reranker_tool(query: str, results: list[dict]):
    """
    Re‑rank a list of search results using a cross‑encoder reranker model.

    The function extracts the original text from each result using the field name
    stored in ``"key_to_embed"`` (set during indexing), scores the pairs with the
    query, and returns the results sorted by descending relevance.

    Parameters
    ----------
    query : str
        The original query text.
    results : list of dict
        A list of candidate result dictionaries (e.g., the raw output of a vector
        search). Each dictionary **must** contain:
        - ``"key_to_embed"`` : the name of the text field (e.g. ``"text"``).
        - A field whose name equals the value of ``"key_to_embed"`` (that holds the
          text to be re‑ranked).
        Other keys are preserved unchanged.

    Returns
    -------
    list of dict
        A list of dictionaries, each containing:
        - ``"rank"`` : int – the 1‑based rank after re‑ranking.
        - ``"score"`` : float – the relevance score assigned by the reranker.
        - ``"result"`` : dict – the original input dictionary for that candidate.

    Example
    -------
    >>> await reranker_tool(
    ...     query="quantum computing",
    ...     results=[
    ...         {"id": 2, "text": "Deep learning overview", "key_to_embed": "text"},
    ...         {"id": 1, "text": "Quantum computing basics", "key_to_embed": "text"}
    ...     ]
    ... )
    [
        {
            "rank": 1,
            "score": 0.998,
            "result": {"id": 1, "text": "Quantum computing basics", "key_to_embed": "text"}
        },
        {
            "rank": 2,
            "score": 0.012,
            "result": {"id": 2, "text": "Deep learning overview", "key_to_embed": "text"}
        }
    ]
    """
    return await reranker(query, results)


if __name__ == "__main__":
    mcp.run(transport="sse")