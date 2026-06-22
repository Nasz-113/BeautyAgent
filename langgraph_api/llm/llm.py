from langchain_openrouter import ChatOpenRouter
from dotenv import load_dotenv

def get_llm():
    load_dotenv()
    return ChatOpenRouter(
        model="qwen/qwen-3.5-2b-instruct",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )