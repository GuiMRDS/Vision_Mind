import ast
import os

from langchain.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import (
    StrOutputParser,
    JsonOutputParser,
)
from langchain.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
)

from my_keys import GEMINI_API_KEY
from my_models import GEMINI_FLASH
from my_helper import encode_image
from agente.detalhes_imagem_modelo import (
    DetalhesImagemModelo,
)


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

TIPOS_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class FerramentaAnalisadoraImagem(BaseTool):

    name: str = "Ferramenta Analisadora Imagem"

    description: str = """
    Utilize esta ferramenta sempre que for solicitada
    uma análise de imagem.

    Entradas:

    - nome_imagem (str)

    Exemplo:
    teste.jpg
    """

    return_direct: bool = False

    def _run(self, acao):

        try:
            dados = ast.literal_eval(acao)

            if isinstance(dados, dict):
                nome_imagem = dados["nome_imagem"]
            else:
                nome_imagem = acao

        except Exception:
            nome_imagem = acao

        nome_imagem = os.path.basename(
            str(nome_imagem).strip().strip("'\"")
        )

        caminhos_possiveis = [
            os.path.join(
                BASE_DIR,
                "imagem",
                nome_imagem,
            ),
            os.path.join(
                BASE_DIR,
                "site",
                "imagem",
                nome_imagem,
            ),
        ]

        caminho_arquivo = None

        for caminho in caminhos_possiveis:
            if os.path.exists(caminho):
                caminho_arquivo = caminho
                break

        if caminho_arquivo is None:
            return f"Erro: imagem não encontrada: {nome_imagem}"

        imagem = encode_image(caminho_arquivo)

        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        mime_type = TIPOS_MIME.get(extensao, "image/jpeg")

        llm = ChatGoogleGenerativeAI(
            api_key=GEMINI_API_KEY,
            model=GEMINI_FLASH,
        )

        template_analisador = (
            ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
                        Assuma que você é um analisador
                        de imagens.

                        Sua tarefa consiste em
                        analisar uma imagem e extrair
                        informações importantes.

                        FORMATO:

                        Descrição da Imagem:
                        ...

                        Rótulos:
                        ...
                        """,
                    ),
                    (
                        "user",
                        [
                            {
                                "type": "text",
                                "text": (
                                    "Descreva a imagem."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url":
                                    (
                                        "data:{mime_type};base64,"
                                        "{imagem_informada}"
                                    )
                                },
                            },
                        ],
                    ),
                ]
            )
        )

        cadeia_analise_imagem = (
            template_analisador
            | llm
            | StrOutputParser()
        )

        parser_json_imagem = JsonOutputParser(
            pydantic_object=
            DetalhesImagemModelo
        )

        template_resposta = PromptTemplate(
            template="""
            Gere um resumo utilizando
            linguagem clara e objetiva.

            Resultado da imagem:

            {resposta_cadeia_analise_imagem}

            FORMATO:

            {formato_saida}
            """,
            input_variables=[
                "resposta_cadeia_analise_imagem"
            ],
            partial_variables={
                "formato_saida":
                parser_json_imagem
                .get_format_instructions()
            },
        )

        cadeia_resumo = (
            template_resposta
            | llm
            | parser_json_imagem
        )

        cadeia_completa = (
            cadeia_analise_imagem
            | cadeia_resumo
        )

        resposta = cadeia_completa.invoke(
            {
                "imagem_informada": imagem,
                "mime_type": mime_type,
            }
        )

        return _formatar_resposta(resposta)


def _formatar_resposta(resposta) -> str:
    """
    Converte o JSON {titulo, descricao, rotulos} em
    texto markdown, já que o agente espera uma string.
    """

    if not isinstance(resposta, dict):
        return str(resposta)

    titulo = resposta.get("titulo", "Análise da imagem")
    descricao = resposta.get("descricao", "")
    rotulos = resposta.get("rotulos") or []

    texto = f"### {titulo}\n\n{descricao}"

    if rotulos:
        texto += "\n\n**Rótulos:** " + ", ".join(
            str(rotulo) for rotulo in rotulos
        )

    return texto