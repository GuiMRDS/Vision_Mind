import io
import os
import re
import sys
import json
import time
import base64
import hashlib
import argparse
import threading
import traceback
import urllib.parse

from collections import OrderedDict
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

from PIL import Image

from my_helper import configurar_console
from my_models import GEMINI_FLASH


configurar_console()


# ─────────────────────────────────────────────────────────────
# Diretórios e limites
# ─────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SITE_DIR = os.path.join(BASE_DIR, "site")
IMAGEM_DIR = os.path.join(BASE_DIR, "imagem")
SITE_IMAGEM_DIR = os.path.join(SITE_DIR, "imagem")

TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024

# Formato detectado pelo Pillow → extensão salva
FORMATOS_PERMITIDOS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}

# Imagens versionadas no projeto (nunca são apagadas pela limpeza)
IMAGENS_DO_PROJETO = {
    "exemplo_grafico.jpg",
    "VisionMind.jpg",
    "VisionMind_conversa.jpg",
}

# Uploads mais antigos que isso são removidos
TEMPO_VIDA_UPLOAD_SEGUNDOS = 24 * 60 * 60

# Histórico de conversa mantido por sessão
MAX_SESSOES = 100
MAX_TURNOS_POR_SESSAO = 6


# ─────────────────────────────────────────────────────────────
# Agente
# ─────────────────────────────────────────────────────────────

agente = None


def inicializar_agente():
    """
    Cria o Agente Orquestrador. Em caso de falha o servidor
    continua no ar e /api/chat responde 503.
    """

    global agente

    try:
        from agente.orquestrador import AgenteOrquestrador

        print("Inicializando Agente Orquestrador do VisionMind...")

        agente = AgenteOrquestrador()

        print("Agente Orquestrador inicializado com sucesso!")

    except Exception as e:
        print(f"[ERRO] Falha ao inicializar o agente: {e}")
        traceback.print_exc()

        agente = None


# ─────────────────────────────────────────────────────────────
# Histórico das conversas
# ─────────────────────────────────────────────────────────────

_sessoes = OrderedDict()
_sessoes_lock = threading.Lock()


def _obter_historico(sessao: str) -> list:
    if not sessao:
        return []

    with _sessoes_lock:
        return list(_sessoes.get(sessao, []))


def _registrar_turno(sessao: str, pergunta: str, resposta: str):
    if not sessao:
        return

    with _sessoes_lock:
        historico = _sessoes.pop(sessao, [])
        historico.append((pergunta, resposta))

        _sessoes[sessao] = historico[-MAX_TURNOS_POR_SESSAO:]

        # Descarta as sessões usadas há mais tempo
        while len(_sessoes) > MAX_SESSOES:
            _sessoes.popitem(last=False)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _limpar_uploads_antigos():
    """Remove uploads com mais de 24h de imagem/."""

    limite = time.time() - TEMPO_VIDA_UPLOAD_SEGUNDOS

    for filename in os.listdir(IMAGEM_DIR):
        if filename in IMAGENS_DO_PROJETO:
            continue

        caminho = os.path.join(IMAGEM_DIR, filename)

        try:
            if os.path.isfile(caminho) and os.path.getmtime(caminho) < limite:
                os.remove(caminho)
        except OSError:
            pass


def _salvar_imagem(base64_str: str, nome: str) -> str:
    """
    Decodifica uma imagem Base64, valida o conteúdo
    e salva em imagem/.

    Retorna o nome final do arquivo.
    """

    # Exemplo:
    # data:image/jpeg;base64,/9j/4AAQSkZJRg...
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]

    try:
        dados = base64.b64decode(base64_str, validate=True)
    except Exception as e:
        raise ValueError(f"Base64 inválido: {e}")

    if len(dados) > TAMANHO_MAXIMO_BYTES:
        raise ValueError("Imagem muito grande. Limite: 10 MB.")

    # Confere se o conteúdo é realmente uma imagem suportada
    try:
        with Image.open(io.BytesIO(dados)) as img:
            img.verify()
            formato = (img.format or "").upper()
    except Exception:
        raise ValueError("O arquivo enviado não é uma imagem válida.")

    if formato not in FORMATOS_PERMITIDOS:
        raise ValueError(
            "Formato não suportado. Use JPG, PNG ou WEBP."
        )

    extensao = FORMATOS_PERMITIDOS[formato]

    base, _ = os.path.splitext(os.path.basename(nome))
    base = re.sub(r"[^a-zA-Z0-9._-]", "_", base).strip("._")

    if not base:
        base = f"imagem_{int(time.time())}"

    os.makedirs(IMAGEM_DIR, exist_ok=True)
    _limpar_uploads_antigos()

    nome_seguro = f"{base}{extensao}"
    caminho_imagem = os.path.join(IMAGEM_DIR, nome_seguro)

    # Mesmo nome com conteúdo diferente → acrescenta um hash
    # para não sobrescrever a imagem de outra conversa
    if os.path.isfile(caminho_imagem):
        with open(caminho_imagem, "rb") as arquivo:
            if arquivo.read() == dados:
                return nome_seguro

        sufixo = hashlib.sha1(dados).hexdigest()[:8]
        nome_seguro = f"{base}_{sufixo}{extensao}"
        caminho_imagem = os.path.join(IMAGEM_DIR, nome_seguro)

    with open(caminho_imagem, "wb") as arquivo:
        arquivo.write(dados)

    return nome_seguro


def _montar_prompt(pergunta: str, nome_imagem: str) -> str:
    if nome_imagem and pergunta:
        return (
            f"Sobre a imagem '{nome_imagem}', "
            f"responda: {pergunta}"
        )

    if nome_imagem:
        return f"Analise detalhadamente a imagem '{nome_imagem}'."

    return pergunta


# ─────────────────────────────────────────────────────────────
# HTTP Handler
# ─────────────────────────────────────────────────────────────

class VisionMindHTTPRequestHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            directory=SITE_DIR,
            **kwargs,
        )

    # ─────────────────────────────────────────────────────────
    # JSON Response
    # ─────────────────────────────────────────────────────────

    def _json(
        self,
        data: dict,
        status: int = 200,
    ):
        body = json.dumps(
            data,
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header(
            "Content-Length",
            str(len(body)),
        )

        self.end_headers()

        self.wfile.write(body)

    # ─────────────────────────────────────────────────────────
    # GET
    # ─────────────────────────────────────────────────────────

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # ─────────────────────────────────────────────────────
        # /api/status
        # ─────────────────────────────────────────────────────

        if path == "/api/status":
            self._json({
                "status": "online",
                "agente_conectado": agente is not None,
                "modelo": GEMINI_FLASH,
                "ferramentas": (
                    [tool.name for tool in agente.tools]
                    if agente
                    else []
                ),
            })

            return

        # ─────────────────────────────────────────────────────
        # /imagem/<nome>
        # ─────────────────────────────────────────────────────

        if path.startswith("/imagem/"):

            filename = os.path.basename(
                urllib.parse.unquote(path)
            )

            # Primeiro procura em imagem/, depois em site/imagem/
            for pasta in (IMAGEM_DIR, SITE_IMAGEM_DIR):
                file_path = os.path.join(pasta, filename)

                if os.path.isfile(file_path):
                    self._servir_imagem(file_path, filename)
                    return

            self.send_error(
                404,
                "Imagem não encontrada",
            )

            return

        # ─────────────────────────────────────────────────────
        # Outros GET → site/
        # ─────────────────────────────────────────────────────

        return super().do_GET()

    # ─────────────────────────────────────────────────────────
    # Servir imagem
    # ─────────────────────────────────────────────────────────

    def _servir_imagem(
        self,
        file_path: str,
        filename: str,
    ):
        ext = os.path.splitext(
            filename
        )[1].lower()

        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }

        content_type = content_types.get(
            ext,
            "application/octet-stream",
        )

        with open(file_path, "rb") as arquivo:
            dados = arquivo.read()

        self.send_response(200)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Content-Length",
            str(len(dados)),
        )

        self.send_header(
            "Cache-Control",
            "no-cache",
        )

        self.end_headers()

        self.wfile.write(dados)

    # ─────────────────────────────────────────────────────────
    # POST
    # ─────────────────────────────────────────────────────────

    def _ler_json(self):
        """
        Lê o corpo da requisição como JSON.
        Retorna None (e já responde com erro) se for inválido.
        """

        length = int(
            self.headers.get(
                "Content-Length",
                0,
            )
        )

        # Base64 ocupa ~4/3 do tamanho original + margem do JSON
        if length > TAMANHO_MAXIMO_BYTES * 4 // 3 + 64 * 1024:
            self._json({
                "success": False,
                "error": "Requisição muito grande. Limite: 10 MB.",
            }, 413)

            return None

        body = self.rfile.read(length)

        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            data = None

        if not isinstance(data, dict):
            self._json({
                "success": False,
                "error": "JSON inválido.",
            }, 400)

            return None

        return data

    def do_POST(self):

        path = urllib.parse.urlparse(
            self.path
        ).path

        if path == "/api/upload":
            self._api_upload()
            return

        if path == "/api/chat":
            self._api_chat()
            return

        self._json({
            "success": False,
            "error": "Rota não encontrada.",
        }, 404)

    # ─────────────────────────────────────────────────────────
    # /api/upload
    # ─────────────────────────────────────────────────────────

    def _api_upload(self):

        data = self._ler_json()

        if data is None:
            return

        imagem_base64 = data.get("imagem", "")

        if not imagem_base64:
            self._json({
                "success": False,
                "error": "Nenhuma imagem enviada.",
            }, 400)

            return

        try:
            nome_final = _salvar_imagem(
                imagem_base64,
                data.get("nome", ""),
            )

        except ValueError as e:
            self._json({
                "success": False,
                "error": str(e),
            }, 400)

            return

        self._json({
            "success": True,
            "nome": nome_final,
            "url": f"/imagem/{nome_final}",
        })

    # ─────────────────────────────────────────────────────────
    # /api/chat
    # ─────────────────────────────────────────────────────────

    def _api_chat(self):

        data = self._ler_json()

        if data is None:
            return

        pergunta = str(data.get("pergunta", "")).strip()
        sessao = str(data.get("sessao", "")).strip()[:64]
        imagem_base64 = data.get("imagem", "")
        nome_imagem = str(data.get("nome_imagem", "")).strip()

        # ─────────────────────────────────────────────────────
        # 1. Salvar imagem
        # ─────────────────────────────────────────────────────

        if imagem_base64:
            try:
                nome_imagem = _salvar_imagem(
                    imagem_base64,
                    nome_imagem or f"upload_{int(time.time())}.jpg",
                )

            except ValueError as e:
                self._json({
                    "success": False,
                    "error": str(e),
                }, 400)

                return

        else:
            # Sem conteúdo enviado, o nome não aponta para nada
            nome_imagem = ""

        # ─────────────────────────────────────────────────────
        # 2. Montar prompt
        # ─────────────────────────────────────────────────────

        prompt_agente = _montar_prompt(pergunta, nome_imagem)

        if not prompt_agente:
            self._json({
                "success": False,
                "error": "Envie uma pergunta ou uma imagem.",
            }, 400)

            return

        print(f"\n[API Chat] Prompt → '{prompt_agente}'")

        # ─────────────────────────────────────────────────────
        # 3. Verificar agente
        # ─────────────────────────────────────────────────────

        if agente is None:
            self._json({
                "success": False,
                "error": (
                    "Agente VisionMind não está disponível. "
                    "Verifique o terminal do servidor."
                ),
            }, 503)

            return

        # ─────────────────────────────────────────────────────
        # 4. Executar agente
        # ─────────────────────────────────────────────────────

        inicio = time.time()

        try:
            output_texto = agente.responder(
                prompt_agente,
                _obter_historico(sessao),
            )

        except Exception as e:
            traceback.print_exc()

            self._json({
                "success": False,
                "error": f"Falha ao gerar a resposta: {e}",
            }, 500)

            return

        duracao = round(time.time() - inicio, 2)

        _registrar_turno(sessao, prompt_agente, output_texto)

        print(f"[API Chat] Concluído em {duracao}s")

        # ─────────────────────────────────────────────────────
        # 5. Resposta ao frontend
        # ─────────────────────────────────────────────────────

        self._json({
            "success": True,
            "output": output_texto,
            "tempo": duracao,
            "prompt_usado": prompt_agente,
            "imagem_usada": nome_imagem,
        })


# ─────────────────────────────────────────────────────────────
# Servidor
# ─────────────────────────────────────────────────────────────

def run(port: int = 8000, host: str = "127.0.0.1"):

    os.makedirs(IMAGEM_DIR, exist_ok=True)

    inicializar_agente()

    httpd = ThreadingHTTPServer(
        (host, port),
        VisionMindHTTPRequestHandler,
    )

    httpd.daemon_threads = True

    status_agente = (
        "OK"
        if agente
        else "INDISPONÍVEL"
    )

    endereco = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    print(
        f"""
╔══════════════════════════════════════════════════╗
║       VisionMind · GenLabs Design System         ║
╠══════════════════════════════════════════════════╣
║  Acesse: {endereco:<40}║
║  Agente: {status_agente:<40}║
║  Pressione Ctrl+C para encerrar                  ║
╚══════════════════════════════════════════════════╝
"""
    )

    if host == "0.0.0.0":
        print(
            "[AVISO] Servidor aberto para a rede: qualquer "
            "pessoa nela pode usar sua chave do Gemini.\n"
        )

    try:
        httpd.serve_forever()

    except KeyboardInterrupt:
        print(
            "\nEncerrando VisionMind..."
        )

    finally:
        httpd.server_close()


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Servidor web do VisionMind",
    )

    parser.add_argument(
        "porta",
        nargs="?",
        type=int,
        default=8000,
        help="porta HTTP (padrão: 8000)",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "interface de rede (padrão: 127.0.0.1; "
            "use 0.0.0.0 para abrir na rede local)"
        ),
    )

    args = parser.parse_args()

    run(args.porta, args.host)
