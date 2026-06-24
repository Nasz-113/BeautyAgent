from langgraph.graph import StateGraph, START, END
from model.BeautyState import BeautyState

builder = StateGraph(BeautyState)

builder.add_node("router", router)
builder.add_node("retrieve", retrieve)
builder.add_node("sql", sql)
builder.add_node("vector", vector)
builder.add_node("fusion", fusion)
builder.add_node("rerank", rerank)
builder.add_node("answer", answer)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "sql")
builder.add_edge("sql", "vector")
builder.add_edge("vector", "fusion")
builder.add_edge("fusion", "rerank")
builder.add_edge("rerank", "answer")
builder.add_edge("answer", END)