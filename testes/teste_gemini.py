"""
Chamada simples ao Gemini usando o SDK oficial (google-genai).

Execute a partir da raiz do projeto:
    python -m testes.teste_gemini
"""

from google import genai
from my_keys import GEMINI_API_KEY
from my_models import GEMINI_FLASH

client = genai.Client(api_key=GEMINI_API_KEY)

response = client.models.generate_content(
    model=GEMINI_FLASH,
    contents="Explique o que é LangChain em uma frase."
)

print(response.text)
