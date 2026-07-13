from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import settings

def get_chat_model(temperature: float = 0):
    return ChatOpenAI(
        model = settings.openai_model,
        api_key = settings.openai_api_key,
        base_url = settings.openai_base_url,
        temperature = temperature
    )

def get_embedding_model():
    return OpenAIEmbeddings(
        model = settings.embedding_model,
        api_key = settings.embedding_api_key,
        base_url = settings.embedding_base_url
    )
