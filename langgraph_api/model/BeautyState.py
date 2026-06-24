from typing import TypedDict

class BeautyState(TypedDict):
    question: str
    sql_result: list
    vector_result: list
    review_result: list
    final_answer: str