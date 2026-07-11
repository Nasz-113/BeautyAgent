from llm.llm import get_reranker_model

async def reranker(query: str, results: list[dict]):
    model = get_reranker_model()
    try:
        pairs = [(query, text[text["key_to_embed"]]) for text in results]
        scores = model.predict(pairs)

        sorted_results = sorted(zip(scores, results), key=lambda x: float(x[0]), reverse=True)

        return [
            {"rank": i + 1, "score": float(score),
                "result": result,}
            for i, (score, result) in enumerate(sorted_results)
        ]

    except Exception as e:
        return f"Error reranking: {e}."