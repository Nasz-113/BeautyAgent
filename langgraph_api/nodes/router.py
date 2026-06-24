from llm.llm import get_llm
from model.BeautyState import BeautyState
llm = get_llm()

def router(state: BeautyState) -> BeautyState:
    return llm.invoke(state["question"])