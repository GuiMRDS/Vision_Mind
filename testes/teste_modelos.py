"""
Testa quais modelos do Gemini respondem com a sua chave.

Execute a partir da raiz do projeto:
    python -m testes.teste_modelos
"""

from google import genai
from my_keys import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

for model_name in [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.0-flash",
]:
    try:
        print(f"\nTestando {model_name}")

        response = client.models.generate_content(
            model=model_name,
            contents="Diga apenas OK"
        )

        print(response.text)

    except Exception as e:
        print("ERRO:", e)
