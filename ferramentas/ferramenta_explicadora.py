from langchain.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate


from my_keys import GEMINI_API_KEY
from my_models import GEMINI_FLASH
import ast

class FerramentaExplicadora(BaseTool):
    name : str = "Ferramenta Explicadora"
    description : str = """
    Utilize esta ferramente sempre que for solicitado que você explique um conteudo para pessoas.
    
    # Entrada Requeridas
    - 'tema' (str) : Tema principal informado na pergunta do usuario
    """

    return_direct : bool = True

    def _run(self, acao):
        acao = ast.literal_eval(acao)
        tema_parametro  = acao.get("tema", "")

        llm = ChatGoogleGenerativeAI(
            api_key=GEMINI_API_KEY,
            model=GEMINI_FLASH,
        )

        template_resposta = PromptTemplate(
        template="""
        Você é um assistente inteligente especializado em educação, tecnologia, programação, negócios, ciência e assuntos gerais.

        Seu objetivo é responder à solicitação do usuário de maneira clara, útil e objetiva.

        Instruções:

        - Analise cuidadosamente a pergunta antes de responder.
        - Adapte o nível de profundidade da resposta ao contexto apresentado.
        - Explique conceitos complexos de forma simples quando necessário.
        - Utilize exemplos práticos sempre que agregarem valor.
        - Caso a pergunta envolva programação, apresente exemplos em Python, comentados e explicados passo a passo.
        - Caso a pergunta envolva análise, comparação ou tomada de decisão, organize a resposta em tópicos.
        - Caso existam múltiplas abordagens possíveis, apresente as principais vantagens e desvantagens de cada uma.
        - Caso a solicitação seja ambígua, faça a melhor interpretação possível com base no contexto fornecido.
        - Priorize precisão, clareza e utilidade.

        Solicitação do usuário:

        {tema}
        """,
        input_variables=["tema"]
        )

        cadeia = (
            template_resposta
            | llm
            | StrOutputParser()
        )

        resposta = cadeia.invoke(
            {"tema": tema_parametro}
        )

        print("RESPOSTA:", resposta)

        return resposta