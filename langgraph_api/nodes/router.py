from llm.llm import get_llm
from model.GraphState import BeautyState
llm = get_llm()

def router(state: BeautyState) -> BeautyState:
    return llm.invoke(state["question"])