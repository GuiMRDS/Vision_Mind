import os

from langchain.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from my_helper import encode_image
from ferramentas.entrada import ler_entrada


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

PROMPT_SISTEMA = """
Você é um analisador de imagens. Responda sempre em português do Brasil,
em markdown, de forma clara e objetiva.

- Se o usuário fez uma pergunta específica sobre a imagem, responda a
  pergunta diretamente, usando os detalhes visíveis (números, textos,
  cores, objetos) como evidência.
- Se o usuário pediu uma análise geral, use o formato:

### <título curto para a imagem>

<descrição detalhada do conteúdo>

**Rótulos:** <três termos-chave separados por vírgula>

- Não invente informações que não estejam visíveis na imagem.
"""

PERGUNTA_PADRAO = "Faça uma análise geral da imagem."


def _localizar_imagem(nome_imagem: str):
    for pasta in (
        os.path.join(BASE_DIR, "imagem"),
        os.path.join(BASE_DIR, "site", "imagem"),
    ):
        caminho = os.path.join(pasta, nome_imagem)

        if os.path.isfile(caminho):
            return caminho

    return None


def _conteudo_para_texto(conteudo) -> str:
    # Alguns modelos devolvem uma lista de partes em vez de string
    if isinstance(conteudo, list):
        return "".join(
            parte.get("text", "") if isinstance(parte, dict) else str(parte)
            for parte in conteudo
        )

    return str(conteudo)


class FerramentaAnalisadoraImagem(BaseTool):

    name: str = "Ferramenta Analisadora Imagem"

    description: str = """
    Utilize esta ferramenta sempre que for solicitada uma análise de
    imagem ou uma pergunta sobre o conteúdo de uma imagem.

    Entrada (JSON):

    - nome_imagem (str): nome do arquivo, ex.: teste.jpg
    - pergunta (str): o que o usuário quer saber sobre a imagem
    """

    # A resposta já sai pronta para o usuário
    return_direct: bool = True

    llm: BaseChatModel

    def _run(self, acao):

        dados = ler_entrada(acao)

        if isinstance(dados, dict):
            nome_imagem = str(dados.get("nome_imagem", ""))
            pergunta = str(dados.get("pergunta", ""))
        else:
            nome_imagem = dados
            pergunta = ""

        nome_imagem = os.path.basename(nome_imagem.strip().strip("'\""))
        pergunta = pergunta.strip() or PERGUNTA_PADRAO

        caminho_arquivo = _localizar_imagem(nome_imagem) if nome_imagem else None

        if caminho_arquivo is None:
            return f"Erro: imagem não encontrada: {nome_imagem or '(sem nome)'}"

        extensao = os.path.splitext(caminho_arquivo)[1].lower()
        mime_type = TIPOS_MIME.get(extensao, "image/jpeg")

        imagem = encode_image(caminho_arquivo)

        mensagens = [
            SystemMessage(content=PROMPT_SISTEMA),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": pergunta,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{imagem}",
                        },
                    },
                ]
            ),
        ]

        resposta = self.llm.invoke(mensagens)

        return _conteudo_para_texto(resposta.content)
