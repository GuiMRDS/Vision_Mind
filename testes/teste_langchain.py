"""
Chamada simples ao Gemini através do LangChain.

Execute a partir da raiz do projeto:
    python -m testes.teste_langchain
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from my_keys import GEMINI_API_KEY
from my_models import GEMINI_FLASH

llm = ChatGoogleGenerativeAI(
    model=GEMINI_FLASH,
    google_api_key=GEMINI_API_KEY
)

resposta = llm.invoke(
    "Explique o que é LangChain em uma frase."
)

print(resposta.content)
