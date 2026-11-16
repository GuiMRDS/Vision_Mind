from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain.prompts import PromptTemplate

from ferramentas.entrada import ler_entrada


class FerramentaExplicadora(BaseTool):
    name : str = "Ferramenta Explicadora"
    description : str = """
    Utilize esta ferramenta sempre que for solicitado que você explique um conteúdo para pessoas.

    # Entrada (JSON)
    - 'tema' (str) : solicitação completa do usuário
    """

    return_direct : bool = True

    llm : BaseChatModel

    def _run(self, acao):
        # O agente pode mandar {"tema": "..."} ou apenas o texto puro
        dados = ler_entrada(acao)

        if isinstance(dados, dict):
            tema_parametro = str(dados.get("tema", ""))
        else:
            tema_parametro = dados

        tema_parametro = tema_parametro.strip()

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
            | self.llm
            | StrOutputParser()
        )

        resposta = cadeia.invoke(
            {"tema": tema_parametro}
        )

        return resposta
