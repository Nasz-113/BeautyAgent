# BeautyAgent

BeautyAgent is an agentic AI project for makeup and skincare search, retrieval,
and recommendations. The goal is to combine structured product data, customer
reviews, semantic search, reranking, and a LangGraph workflow so users can ask
beauty questions such as:

- "Find a foundation for oily skin that does not oxidize."
- "Compare these products for dry sensitive skin."
- "Which reviews mention long wear and transfer resistance?"

## Target Architecture

```text
User
  |
  v
FastAPI / LangGraph API
  |
  v
LangGraph workflow
  |
  +-- SQL retrieval over product, variant, filter, and review tables
  +-- Vector retrieval over Qdrant product/review collections
  +-- Result fusion and reranking
  |
  v
Beauty-focused final answer
```

## Repository Layout

```text
.
|-- compose.yaml                 # Local Qdrant service
|-- STRUCTURE.md                 # Architecture notes and early design plan
|-- langgraph_api/               # FastAPI and LangGraph orchestration skeleton
|-- mcp_server/rag_mcp/          # MCP server for Qdrant RAG tools
`-- sephora_scraper/             # Sephora product and review scraping scripts
```

## Current Status

The project is in the early integration stage.

### Done / In Progress

- Qdrant is defined in `compose.yaml` for local vector storage.
- Sephora scraper modules exist for:
  - brand, product, variant, filter, and variant-filter data
  - product review data from Bazaarvoice
  - Pydantic models for scraped records
  - PostgreSQL insert flows through `psycopg2`
- The RAG MCP server has a FastMCP entry point in
  `mcp_server/rag_mcp/src/main.py`.
- The RAG MCP server currently exposes tools for:
  - creating Qdrant collections
  - indexing payloads into Qdrant
  - vector search
  - reranking search results
  - hybrid search placeholder
- Embedding and reranking models are loaded with `sentence-transformers`.
- Qdrant client configuration is pulled from environment variables.
- The LangGraph API folder contains:
  - FastAPI health and chat route stubs
  - `BeautyState`
  - a planned graph flow: retrieve -> sql -> vector -> fusion -> rerank -> answer

### Not Ready Yet

- The top-level API endpoints still return placeholder responses.
- Most LangGraph node implementations are empty placeholders.
- `langgraph_api/graph/compile.py` needs imports and wiring before the graph can
  run.
- The hybrid search tool is marked as not functional yet.
- The scraper pipeline needs a cleanup pass, CLI/run instructions, and validation
  against the current database schema.
- RAG MCP tools need stronger input validation, model caching, and integration
  tests.
- No end-to-end flow is wired yet from user question -> retrieval -> rerank ->
  final beauty answer.

## Local Setup Notes

Start Qdrant:

```bash
docker compose up -d qdrant
```

The RAG MCP server expects these environment variables:

```text
QDRANT_URL=
QDRANT_API_KEY=
VECTOR_SIZE=
EMBEDDING_MODEL=
RERANKER_MODEL=
```

Run the RAG MCP server from its project folder:

```bash
cd mcp_server/rag_mcp
uv sync
uv run python src/main.py
```

The scraper modules also need PostgreSQL connection settings configured through
their `db_config.py` files before running ingestion.

## Next Plan

1. Stabilize configuration
   - Add `.env.example`.
   - Document required PostgreSQL and Qdrant settings.
   - Confirm vector size matches the selected embedding model.

2. Clean up and validate ingestion
   - Fix scraper syntax/runtime issues.
   - Confirm table creation scripts match the scraper insert payloads.
   - Add repeatable commands for loading product, variant, filter, and review
     data.

3. Build the Qdrant indexing pipeline
   - Define `product_collection` and `review_collection` payload shapes.
   - Index product descriptions, benefits, filters, and review text.
   - Verify retrieval quality with sample beauty queries.

4. Harden the RAG MCP server
   - Cache embedding and reranker models instead of loading them per request.
   - Return scores and metadata from search tools.
   - Implement real hybrid search or remove the placeholder until it is ready.
   - Add focused tests for collection creation, indexing, vector search, and
     reranking.

5. Wire the LangGraph API
   - Implement SQL, vector, fusion, rerank, and answer nodes.
   - Connect nodes to MCP tools and PostgreSQL retrieval.
   - Replace placeholder `/chat/workflow` and `/chat/agent` responses with real
     graph execution.

6. Add evaluation queries
   - Create a small test set for common beauty recommendation needs.
   - Check answer grounding, review evidence, product filtering, and rerank
     behavior.

7. Prepare for a user-facing client
   - Add response format conventions.
   - Decide whether the first client should be a minimal web UI, CLI, or API-only
     demo.
