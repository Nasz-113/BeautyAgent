from fastapi import FastAPI
from model.ChatRequest import ChatRequest

app = FastAPI()

@app.get("/health")
def health_check():
    return {"message": "LangGraph API is running"}

@app.post("/chat/workflow")
def chat_workflow(request: ChatRequest):
    return {"message": "LangGraph API is running"}

@app.post("/chat/agent")
def chat_agent(request: ChatRequest):
    return {"message": "LangGraph API is running"}