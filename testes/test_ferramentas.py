"""
Testes automatizados das ferramentas e do agente.

Não acessam a internet nem gastam cota: o Gemini é substituído
por um modelo falso do LangChain.

Execute a partir da raiz do projeto:
    python -m unittest discover -s testes -t . -p "test_*.py"
"""

import unittest

from langchain_core.language_models.fake_chat_models import (
    FakeListChatModel,
)

from agente.orquestrador import AgenteOrquestrador, formatar_historico
from ferramentas.entrada import ler_entrada
from ferramentas.ferramenta_analisadora_imagem import (
    FerramentaAnalisadoraImagem,
)
from ferramentas.ferramenta_explicadora import FerramentaExplicadora


class TestLerEntrada(unittest.TestCase):

    def test_json(self):
        self.assertEqual(ler_entrada('{"tema": "redes"}'), {"tema": "redes"})

    def test_dict_python(self):
        self.assertEqual(ler_entrada("{'tema': 'redes'}"), {"tema": "redes"})

    def test_texto_puro(self):
        self.assertEqual(ler_entrada("redes neurais"), "redes neurais")

    def test_texto_entre_aspas(self):
        self.assertEqual(ler_entrada("'teste.jpg'"), "teste.jpg")

    def test_bloco_de_codigo(self):
        entrada = '```json\n{"nome_imagem": "a.jpg"}\n```'
        self.assertEqual(ler_entrada(entrada), {"nome_imagem": "a.jpg"})


class TestFerramentaExplicadora(unittest.TestCase):

    def test_aceita_json_e_texto_puro(self):
        llm = FakeListChatModel(responses=["resposta 1", "resposta 2"])
        ferramenta = FerramentaExplicadora(llm=llm)

        self.assertEqual(ferramenta.run('{"tema": "redes"}'), "resposta 1")
        self.assertEqual(ferramenta.run("redes neurais"), "resposta 2")


class TestFerramentaAnalisadoraImagem(unittest.TestCase):

    def test_imagem_inexistente(self):
        llm = FakeListChatModel(responses=["não deveria ser chamado"])
        ferramenta = FerramentaAnalisadoraImagem(llm=llm)

        resposta = ferramenta.run('{"nome_imagem": "nao_existe.jpg"}')

        self.assertIn("imagem não encontrada", resposta)

    def test_imagem_de_exemplo(self):
        llm = FakeListChatModel(responses=["### Gráfico"])
        ferramenta = FerramentaAnalisadoraImagem(llm=llm)

        resposta = ferramenta.run(
            '{"nome_imagem": "exemplo_grafico.jpg", "pergunta": "Qual o maior valor?"}'
        )

        self.assertEqual(resposta, "### Gráfico")

    def test_bloqueia_caminho_fora_da_pasta(self):
        llm = FakeListChatModel(responses=["não deveria ser chamado"])
        ferramenta = FerramentaAnalisadoraImagem(llm=llm)

        resposta = ferramenta.run("../server.py")

        self.assertIn("imagem não encontrada", resposta)


class TestAgente(unittest.TestCase):

    def test_formatar_historico(self):
        self.assertIn("nenhuma", formatar_historico([]))

        texto = formatar_historico([("oi", "x" * 5000)])

        self.assertIn("Usuário: oi", texto)
        self.assertLess(len(texto), 2000)

    def test_agente_usa_ferramenta_explicadora(self):
        llm = FakeListChatModel(responses=[
            'Thought: preciso explicar\n'
            'Action: Ferramenta Explicadora\n'
            'Action Input: {"tema": "o que é IA"}',
            "IA é a área que cria sistemas inteligentes.",
        ])

        agente = AgenteOrquestrador(llm=llm)
        agente.executor.verbose = False

        resposta = agente.responder("O que é IA?", [("oi", "olá")])

        self.assertEqual(
            resposta,
            "IA é a área que cria sistemas inteligentes.",
        )

    def test_agente_responde_direto(self):
        llm = FakeListChatModel(responses=[
            "Thought: é só um cumprimento\nFinal Answer: Olá! Como posso ajudar?",
        ])

        agente = AgenteOrquestrador(llm=llm)
        agente.executor.verbose = False

        self.assertEqual(agente.responder("oi"), "Olá! Como posso ajudar?")


if __name__ == "__main__":
    unittest.main()
