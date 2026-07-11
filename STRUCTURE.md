# BeautyAgent
Agentic AI tailored for Makeup and Skincares


I think your stack choice is pretty good. In fact, for a beauty recommendation/search agent, I would probably build almost exactly this.

# Architecture I'd recommend

```text
                        User
                         │
                         ▼
                 FastAPI / .NET API
                         │
                         ▼
                 LangGraph Agent
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   MCP Tool         MCP Tool        MCP Tool
(SQL Search)    (Vector Search)  (Review Search)
        │                │                │
        ▼                ▼                ▼
 PostgreSQL          Qdrant         PostgreSQL
(product db)      embeddings       reviews db

        │
        ▼
  Reranker (optional)
        │
        ▼
     Qwen3-8B / 14B
        │
        ▼
      Response
```

---

# Components

## 1. PostgreSQL

You already have almost the perfect schema.

Tables

```text
brand_info

product_info

variant_info

filter_type_info

filter_info

variant_filter_info

review_info
```

I'd add

```sql
review_info
(
review_id
product_id
rating
review_text
review_date
source
user_name
)
```

---

## 2. Qdrant

I would not embed everything.

Only embed semantic text.

### Collection: product_collection

Payload

```json
{
product_id:123,
brand:"Huda Beauty",
product_name:"Easy Blur Foundation",

benefits:"Long lasting matte",

description:"..."

}
```

Embedding text

```text
Huda Beauty Easy Blur Foundation

Long lasting matte finish

Suitable for oily skin

Contains niacinamide

Natural coverage
```

---

### Collection: review_collection

Embedding text

```text
This foundation oxidizes after 3 hours.
Good for oily skin.
Not suitable for dry skin.
```

Payload

```json
{
review_id:1234,
product_id:432,
rating:4
}
```

---

# 3. MCP servers

This is where I'd spend effort.

## MCP Product SQL

Tool

```text
search_products(
brand=None,
skin_type=None,
ingredient=None,
price_max=None
)
```

Agent calls

```python
search_products(
brand="Huda Beauty",
price_max=200
)
```

returns

```json
[
{
id:123,
name:"Easy Blur Foundation",
price:189
}
]
```

---

## MCP Vector Search

Tool

```python
semantic_search(query,k=10)
```

Internally

```python
embedding=query_embed(query)

qdrant.search(
collection_name="product_collection",
query_vector=embedding
)
```

---

## MCP Review Search

Tool

```python
search_reviews(
query,
product_id=None
)
```

Example

User

```text
Foundation for oily skin that doesn't oxidize
```

Agent

```python
search_reviews(
query="doesn't oxidize oily skin"
)
```

returns

```text
Review 1

Stayed matte for 8 hours


Review 2

No oxidation after gym


Review 3

Became darker after 2 hours
```

---

# LangGraph workflow

I think graph-based orchestration is better than a ReAct agent here.

## State

```python
class BeautyState(TypedDict):

question:str

sql_result:list

vector_result:list

review_result:list

final_answer:str
```

---

## Router node

Determine intent

Question

```text
Find Huda Beauty foundations under RM200
```

Route

```text
SQL only
```

Question

```text
Foundation for oily skin that doesn't oxidize
```

Route

```text
Vector

+

Review
```

Question

```text
Show me products similar to Dior Forever Skin Glow
```

Route

```text
Vector only
```

---

## Retrieve node

Execute tools

```python
sql_products()



vector_search()



review_search()
```

---

## Fusion node

Merge

```python
candidate_products



candidate_reviews



metadata
```

---

## Rerank node

Optional

Use

Cross Encoder

Example

Top 30 Qdrant hits

↓

CrossEncoder

↓

Top 5

---

## Answer node

Prompt

```text
You are a Sephora beauty advisor.

Use product metadata.

Use reviews.

Use retrieved context only.

Do not hallucinate products.
```

---

# QLoRA on Qwen3.5-2B

I think this is the part I'd postpone.

For your use case,

RAG quality contributes roughly

```text
Embeddings      45%

Review corpus   25%

Reranker        20%

LLM             10%
```

A well-built RAG with

* Qwen3-8B-Instruct
* Qdrant
* good reviews
* reranking

will likely outperform

Qwen3.5-2B + QLoRA

for recommendation tasks.

---

# If you still want to train

Using Unsloth

Training samples

```json
{
"instruction":
"Recommend products for oily skin",

"context":
"Product A...

Review A...

Product B...

Review B...",


"output":
"Product A is better because..."
}
```

Only a few thousand examples would probably be needed.

---

# What I'd build first

### Phase 1

Postgres

Qdrant

MCP servers

LangGraph

Qwen3-8B

---

### Phase 2

Review scraper

Reranker

---

### Phase 3

QLoRA with Unsloth

---

### Phase 4

Memory

User profile table

```text
user_id

skin_type

undertone

budget

favorite_brands

avoided_ingredients

preferred_finish
```

Then your agent becomes much more interesting.

User:

> Recommend a foundation

Agent:

```text
Memory:
Dry skin
Warm undertone
Budget RM150

↓

SQL

↓

Reviews

↓

Qdrant

↓

Answer
```

This is honestly close to what I would expect from a portfolio project for an AI engineer candidate in 2026. It demonstrates data engineering, RAG, MCP, agent orchestration, retrieval optimization, and optional model adaptation without becoming unnecessarily complicated.


For your use case, I think separating **knowledge**, **tools**, **workflows**, and **agents** from the beginning will save you a lot of pain later.

# 1. Suggested architecture

```text
User
 │
 ▼
FastAPI
 │
 ├── /chat/workflow
 │       │
 │       ▼
 │   LangGraph Workflow
 │
 └── /chat/agent
         │
         ▼
     ReAct Agent
         │
 ┌───────┼────────┐
 ▼       ▼        ▼
SQL   Vector    Reviews
Tool   Tool      Tool
 │      │         │
 ▼      ▼         ▼
Postgres Qdrant  Postgres
```

---

# 2. Folder structure

I'd probably do something like this.

```text
beauty-agent/

├── app/
│   ├── api/
│   │   ├── chat.py
│   │   └── health.py
│   │
│   ├── agents/
│   │   ├── react_agent.py
│   │   └── prompts.py
│   │
│   ├── workflows/
│   │   ├── beauty_workflow.py
│   │   ├── nodes/
│   │   │   ├── retrieve.py
│   │   │   ├── sql_search.py
│   │   │   ├── review_search.py
│   │   │   └── summarize.py
│   │   │
│   │   └── graph.py
│   │
│   ├── tools/
│   │   ├── sql_tool.py
│   │   ├── qdrant_tool.py
│   │   ├── review_tool.py
│   │   └── reranker.py
│   │
│   ├── mcp/
│   │   ├── server.py
│   │   └── tools.py
│   │
│   ├── embeddings/
│   │   ├── embedder.py
│   │   └── ingestion.py
│   │
│   ├── database/
│   │   ├── postgres.py
│   │   └── models.py
│   │
│   └── llm/
│       ├── qwen_client.py
│       └── prompts.py
│
├── scripts/
│   ├── scrape_sephora.py
│   ├── scrape_reviews.py
│   └── ingest_qdrant.py
│
├── notebooks/
│
├── tests/
│
├── docker/
│
├── requirements.txt
│
└── main.py
```

---

# 3. Two modes

I actually think having both modes is a good learning project.

## Mode 1 — Workflow

Workflow means **you already know the steps beforehand**.

Example

User:

> Recommend a matte lipstick under RM120

Graph

```text
START

↓

Retrieve relevant docs

↓

Generate SQL filters

↓

Query postgres

↓

Fetch reviews

↓

Summarize

↓

END
```

LangGraph code

```python
builder.add_node("retrieve")

builder.add_node("sql")

builder.add_node("reviews")

builder.add_node("summary")



builder.add_edge("retrieve","sql")

builder.add_edge("sql","reviews")

builder.add_edge("reviews","summary")
```

Advantages

* deterministic

* cheap

* fast

* easy debugging

---

## Mode 2 — Agent

User asks anything.

Example

> Which perfume smells similar to Black Opium but lasts longer?

Agent decides

```text
Thought

Need semantic similarity


Action

Qdrant Search


Observation

Found Libre Intense



Thought

Need longevity reviews


Action

Review Tool


Observation

Average longevity 7.5h



Thought

Need price


Action

SQL Tool


Observation

RM625



Final Answer
```

You don't know beforehand how many tools will be called.

---

# 4. ReAct agent

ReAct means

Reasoning + Acting

Paper name:

ReAct: Synergizing Reasoning and Acting in Language Models

It follows a loop

```text
Question

↓

Thought

↓

Action

↓

Observation

↓

Thought

↓

Action

↓

Observation

↓

Final Answer
```

Example

Question

> Find a red lipstick suitable for dry skin.

LLM output

```text
Thought:
Need products for dry skin


Action:
SQLTool("red lipstick")


Observation:
23 products


Thought:
Need hydrating formula


Action:
VectorSearch("hydrating lipstick")


Observation:
5 products


Thought:
Need customer feedback


Action:
ReviewTool(product_ids)


Observation:
4 products highly rated


Final Answer:
...
```

---

# 5. MCP usage

Your tools become MCP servers.

SQL MCP

```text
postgres_mcp

query_products()

get_product()

get_variant()

```

Qdrant MCP

```text
qdrant_mcp

search_similarity()

insert_embeddings()

```

Review MCP

```text
review_mcp

get_reviews()

average_rating()

sentiment()

```

Agent connects to MCP.

```python
agent = create_react_agent(

    model,

    tools=[

        postgres_mcp,

        qdrant_mcp,

        review_mcp

    ]

)
```

---

# 6. Where QLoRA fits

QLoRA is not necessary for the first version.

I would do this progression:

Stage 1

```text
Qwen3-8B-Instruct

+

Qdrant

+

RAG
```

Stage 2

```text
Add review retrieval
```

Stage 3

```text
Add ReAct agent
```

Stage 4

```text
Fine tune
Qwen3.5-2B

using Unsloth

training examples

Question

Retrieved docs

SQL results

Expected answer
```

Stage 5

```text
Replace prompt engineering

with

fine-tuned model
```

For a beauty recommendation assistant, I'd expect **80–90% of the quality gain to come from good retrieval, reviews, reranking, and tool usage**, and only **10–20% from QLoRA fine-tuning**. Fine-tuning becomes more valuable if you want a very specific response style or domain-specific reasoning behavior.
