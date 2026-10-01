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

        print("TIPO:", type(acao))
        print("VALOR:", repr(acao))

        try:
            dados = ast.literal_eval(acao)

            if isinstance(dados, dict):
                nome_imagem = dados["nome_imagem"]
            else:
                nome_imagem = acao

        except Exception:
            nome_imagem = acao

        nome_imagem = nome_imagem.strip()

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

        print("\n========== DEBUG ==========")
        print("BASE_DIR:", BASE_DIR)
        print("IMAGEM:", nome_imagem)

        for caminho in caminhos_possiveis:
            print(
                f"EXISTE? {os.path.exists(caminho)} -> {caminho}"
            )

        print("===========================\n")

        if caminho_arquivo is None:
            return {
                "erro": (
                    f"Imagem não encontrada: "
                    f"{nome_imagem}"
                )
            }

        print("ARQUIVO ENCONTRADO:")
        print(caminho_arquivo)

        imagem = encode_image(caminho_arquivo)

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
                                        "data:image/jpeg;base64,"
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
                "imagem_informada": imagem
            }
        )

        return resposta