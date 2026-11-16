"""
Testes automatizados do servidor (sem iniciar o agente).

Execute a partir da raiz do projeto:
    python -m unittest discover -s testes -t . -p "test_*.py"
"""

import base64
import io
import os
import tempfile
import time
import unittest
from unittest import mock

from PIL import Image

import server


def _imagem_base64(formato="PNG", cor=(255, 0, 0)) -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), cor).save(buffer, formato)
    return base64.b64encode(buffer.getvalue()).decode()


class TestSalvarImagem(unittest.TestCase):

    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(server, "IMAGEM_DIR", self.pasta.name)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.pasta.cleanup()

    def test_salva_com_extensao_do_formato_real(self):
        nome = server._salvar_imagem(
            "data:image/png;base64," + _imagem_base64("PNG"),
            "foto.jpg",
        )

        self.assertEqual(nome, "foto.png")
        self.assertTrue(os.path.isfile(os.path.join(self.pasta.name, nome)))

    def test_nome_com_caminho_e_espacos(self):
        nome = server._salvar_imagem(_imagem_base64("JPEG"), "../../minha foto.jpg")

        self.assertEqual(nome, "minha_foto.jpg")

    def test_rejeita_arquivo_que_nao_e_imagem(self):
        with self.assertRaises(ValueError):
            server._salvar_imagem(base64.b64encode(b"ola").decode(), "x.jpg")

    def test_rejeita_base64_invalido(self):
        with self.assertRaises(ValueError):
            server._salvar_imagem("@@@", "x.jpg")

    def test_rejeita_imagem_grande(self):
        with mock.patch.object(server, "TAMANHO_MAXIMO_BYTES", 10):
            with self.assertRaises(ValueError):
                server._salvar_imagem(_imagem_base64(), "x.png")

    def test_mesmo_nome_conteudo_diferente_nao_sobrescreve(self):
        primeiro = server._salvar_imagem(_imagem_base64(cor=(255, 0, 0)), "a.png")
        repetido = server._salvar_imagem(_imagem_base64(cor=(255, 0, 0)), "a.png")
        diferente = server._salvar_imagem(_imagem_base64(cor=(0, 0, 255)), "a.png")

        self.assertEqual(primeiro, "a.png")
        self.assertEqual(repetido, "a.png")
        self.assertNotEqual(diferente, "a.png")
        self.assertTrue(diferente.startswith("a_"))

    def test_limpa_uploads_antigos_mas_mantem_imagens_do_projeto(self):
        antigo = os.path.join(self.pasta.name, "antigo.png")
        projeto = os.path.join(self.pasta.name, "exemplo_grafico.jpg")

        dois_dias_atras = time.time() - 2 * 24 * 60 * 60

        for caminho in (antigo, projeto):
            open(caminho, "wb").close()
            os.utime(caminho, (dois_dias_atras, dois_dias_atras))

        server._salvar_imagem(_imagem_base64(), "novo.png")

        self.assertFalse(os.path.exists(antigo))
        self.assertTrue(os.path.exists(projeto))


class TestPromptEHistorico(unittest.TestCase):

    def setUp(self):
        server._sessoes.clear()

    def test_montar_prompt(self):
        self.assertEqual(server._montar_prompt("oi", ""), "oi")
        self.assertIn("a.jpg", server._montar_prompt("", "a.jpg"))
        self.assertIn("qual?", server._montar_prompt("qual?", "a.jpg"))
        self.assertEqual(server._montar_prompt("", ""), "")

    def test_historico_limita_turnos(self):
        for i in range(server.MAX_TURNOS_POR_SESSAO + 3):
            server._registrar_turno("s1", f"p{i}", f"r{i}")

        historico = server._obter_historico("s1")

        self.assertEqual(len(historico), server.MAX_TURNOS_POR_SESSAO)
        self.assertEqual(historico[-1], (f"p{server.MAX_TURNOS_POR_SESSAO + 2}", f"r{server.MAX_TURNOS_POR_SESSAO + 2}"))

    def test_historico_limita_sessoes(self):
        with mock.patch.object(server, "MAX_SESSOES", 2):
            for sessao in ("a", "b", "c"):
                server._registrar_turno(sessao, "p", "r")

        self.assertEqual(server._obter_historico("a"), [])
        self.assertEqual(len(server._obter_historico("c")), 1)

    def test_sem_sessao_nao_guarda_historico(self):
        server._registrar_turno("", "p", "r")

        self.assertEqual(server._obter_historico(""), [])


if __name__ == "__main__":
    unittest.main()
