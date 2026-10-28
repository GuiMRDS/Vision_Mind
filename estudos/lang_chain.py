from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate
from langchain.globals import set_debug

from my_keys import GEMINI_API_KEY
from my_models import GEMINI_FLASH
from my_helper import encode_image
from estudos.detalhes_imagem_modelo import DetalhesImagemModelo

# Ativa logs de depuração (execute com: python -m estudos.lang_chain)
set_debug(True)

# Instancia o modelo LLM com as credenciais e configuração adequadas
llm = ChatGoogleGenerativeAI(
    api_key=GEMINI_API_KEY,
    model=GEMINI_FLASH
)


# Codifica a imagem em base64
imagem = encode_image("imagem/exemplo_grafico.jpg")

# Template para análise da imagem
template_analisador = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Assuma que você é um analisador de imagens. Sua tarefa é analisar a imagem
            e extrair informações de forma objetiva.

            # FORMATO DE SAÍDA
            Descrição da Imagem: 'Insira aqui sua descrição'
            Rótulos: 'Insira três termos-chave separados por vírgula'
            """
        ),
        (
            "user",
            [
                {"type": "text", "text": "Descreva a imagem:"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{imagem_informada}"}}
            ]
        )
    ]
)

# Cadeia de análise da imagem: Template -> Modelo -> Saída em texto
cadeia_analise_imagem = template_analisador | llm | StrOutputParser()

# Parser para transformar a saída final em um formato JSON validado pelo modelo DetalhesImagemModelo
parser_json_imagem = JsonOutputParser(pydantic_object=DetalhesImagemModelo)

# Template para gerar um resumo final, estruturando o resultado em JSON
template_resposta = PromptTemplate(
    template="""
    Gere um resumo em linguagem clara e objetiva, focado no público brasileiro.
    A comunicação deve ser simples, pensando em consultas futuras.

    # Resultado da imagem
    {resposta_cadeia_analise_imagem}

    # FORMATO DE SAÍDA
    {formato_saida}
    """,
    input_variables=["resposta_cadeia_analise_imagem"],
    partial_variables={
        "formato_saida": parser_json_imagem.get_format_instructions()
    }
)

# Cadeia para resumir o resultado anterior em JSON
cadeia_resumo = template_resposta | llm | parser_json_imagem

# Combina as duas cadeias: primeiro análise da imagem, depois resumo formatado
cadeia_completa = cadeia_analise_imagem | cadeia_resumo

# Executa a cadeia completa com a imagem fornecida
resposta = cadeia_completa.invoke({"imagem_informada": imagem})

# Imprime a resposta final estruturada em JSON
print(resposta)