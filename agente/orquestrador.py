from langchain_google_genai import ChatGoogleGenerativeAI
from my_models import GEMINI_FLASH
from my_keys import GEMINI_API_KEY
from langchain.globals import set_debug
set_debug(False)

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from agente.prompt_react import PROMPT_REACT
from ferramentas.ferramenta_analisadora_imagem import FerramentaAnalisadoraImagem
from ferramentas.ferramenta_explicadora import FerramentaExplicadora


# Respostas longas são cortadas no histórico para não inflar o prompt
MAX_CARACTERES_RESPOSTA_HISTORICO = 1500


def formatar_historico(historico) -> str:
    """
    Converte [(pergunta, resposta), ...] no texto
    que entra no prompt do agente.
    """

    if not historico:
        return "(nenhuma mensagem anterior)"

    linhas = []

    for pergunta, resposta in historico:
        if len(resposta) > MAX_CARACTERES_RESPOSTA_HISTORICO:
            resposta = resposta[:MAX_CARACTERES_RESPOSTA_HISTORICO] + "…"

        linhas.append(f"Usuário: {pergunta}")
        linhas.append(f"VisionMind: {resposta}")

    return "\n".join(linhas)


class AgenteOrquestrador:
    def __init__(self, llm=None):
        """
        llm: modelo a usar no lugar do Gemini (usado nos testes).
        """

        if llm is None:
            if not GEMINI_API_KEY:
                raise RuntimeError(
                    "GEMINI_API_KEY não encontrada. Crie um arquivo .env na "
                    "raiz do projeto com a linha: GEMINI_API_KEY=\"sua_chave\""
                )

            # Um único cliente do Gemini, compartilhado com as ferramentas
            llm = ChatGoogleGenerativeAI(
                api_key = GEMINI_API_KEY,
                model = GEMINI_FLASH,
            )

        self.llm = llm

        self.tools = [
            FerramentaAnalisadoraImagem(llm = self.llm),
            FerramentaExplicadora(llm = self.llm),
        ]

        prompt = PromptTemplate.from_template(PROMPT_REACT)
        self.agente = create_react_agent(self.llm, self.tools, prompt)

        self.executor = AgentExecutor(
            agent = self.agente,
            tools = self.tools,
            verbose = True,
            handle_parsing_errors = True,
            max_iterations = 5,
        )

    def responder(self, pergunta: str, historico=None) -> str:
        """
        Executa o agente e devolve a resposta em texto.

        historico: lista de (pergunta, resposta) da conversa atual.
        """

        resposta = self.executor.invoke({
            "input": pergunta,
            "chat_history": formatar_historico(historico),
        })

        return str(resposta.get("output", ""))
