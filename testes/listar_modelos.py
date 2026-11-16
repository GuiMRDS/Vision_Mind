"""
Lista os modelos disponíveis para a sua chave do Gemini.

Execute a partir da raiz do projeto:
    python -m testes.listar_modelos
"""

from google import genai
from my_keys import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

for model in client.models.list():
    print(model.name)
