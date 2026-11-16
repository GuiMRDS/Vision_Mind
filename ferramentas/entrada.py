import ast
import json


def ler_entrada(acao):
    """
    Interpreta o "Action Input" enviado pelo agente.

    O modelo às vezes manda JSON ({"tema": "..."}), às vezes um
    dict no formato Python ({'tema': '...'}) e às vezes só o texto.
    Retorna um dict quando conseguir interpretar, senão o texto limpo.
    """

    if isinstance(acao, dict):
        return acao

    texto = str(acao).strip()

    # Remove cercas de código que o modelo às vezes coloca
    if texto.startswith("```"):
        texto = texto.strip("`").strip()

        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    for interpretar in (json.loads, ast.literal_eval):
        try:
            dados = interpretar(texto)
        except (ValueError, SyntaxError, TypeError):
            continue

        if isinstance(dados, dict):
            return dados

    return texto.strip("'\"")
