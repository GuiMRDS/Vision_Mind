import os
import sys
import json
import time
import base64
import traceback
import urllib.parse

from http.server import HTTPServer, SimpleHTTPRequestHandler


# ─────────────────────────────────────────────────────────────
# Importações do agente
# ─────────────────────────────────────────────────────────────

try:
    from langchain.agents import AgentExecutor
    from agente.orquestrador import AgenteOrquestrador

    AGENTE_DISPONIVEL = True

except Exception as e:
    print(f"[AVISO] Não foi possível importar o agente: {e}")
    AGENTE_DISPONIVEL = False


# ─────────────────────────────────────────────────────────────
# Diretórios
# ─────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SITE_DIR = os.path.join(BASE_DIR, "site")
IMAGEM_DIR = os.path.join(BASE_DIR, "imagem")
SITE_IMAGEM_DIR = os.path.join(SITE_DIR, "imagem")

os.makedirs(IMAGEM_DIR, exist_ok=True)
os.makedirs(SITE_IMAGEM_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Inicialização do agente
# ─────────────────────────────────────────────────────────────

orquestrador = None

if AGENTE_DISPONIVEL:
    try:
        print("Inicializando Agente Orquestrador do VisionMind...")

        _agente = AgenteOrquestrador()

        orquestrador = AgentExecutor(
            agent=_agente.agente,
            tools=_agente.tools,
            verbose=True,
            handle_parsing_errors=True,
            return_intermediate_steps=False,
        )

        print("Agente Orquestrador inicializado com sucesso!")

    except Exception as e:
        print(f"[ERRO] Falha ao inicializar o agente: {e}")
        traceback.print_exc()

        orquestrador = None


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _salvar_imagem(base64_str: str, nome: str) -> str:
    """
    Decodifica uma imagem Base64 e salva em:

    imagem/
    site/imagem/

    Retorna o nome final do arquivo.
    """

    # Exemplo:
    # data:image/jpeg;base64,/9j/4AAQSkZJRg...
    if "," in base64_str:
        base64_str = base64_str.split(",", 1)[1]

    nome_seguro = os.path.basename(nome)

    if not nome_seguro:
        nome_seguro = f"imagem_{int(time.time())}.jpg"

    try:
        dados = base64.b64decode(base64_str)
    except Exception as e:
        raise ValueError(f"Base64 inválido: {e}")

    caminho_imagem = os.path.join(
        IMAGEM_DIR,
        nome_seguro,
    )

    caminho_site = os.path.join(
        SITE_IMAGEM_DIR,
        nome_seguro,
    )

    with open(caminho_imagem, "wb") as arquivo:
        arquivo.write(dados)

    with open(caminho_site, "wb") as arquivo:
        arquivo.write(dados)

    return nome_seguro


def _output_para_texto(output) -> str:
    """
    Converte diferentes tipos de retorno do LangChain
    para uma string que possa ser enviada ao frontend.
    """

    if output is None:
        return ""

    if isinstance(output, str):
        return output

    if isinstance(output, dict):
        if "output" in output:
            return str(output["output"])

        if "text" in output:
            return str(output["text"])

        if "content" in output:
            return str(output["content"])

        return json.dumps(
            output,
            ensure_ascii=False,
            default=str,
        )

    if hasattr(output, "content"):
        return str(output.content)

    return str(output)


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
    # Logs
    # ─────────────────────────────────────────────────────────

    def log_message(self, format, *args):
        super().log_message(format, *args)

    # ─────────────────────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────────────────────

    def _cors_headers(self):
        self.send_header(
            "Access-Control-Allow-Origin",
            "*",
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )

    def do_OPTIONS(self):
        self.send_response(200)

        self._cors_headers()

        self.end_headers()

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

        self._cors_headers()

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
                "agente_conectado": orquestrador is not None,
                "ferramentas": [
                    "Ferramenta Analisadora Imagem",
                    "Ferramenta Explicadora",
                ],
            })

            return

        # ─────────────────────────────────────────────────────
        # /api/exemplos
        # ─────────────────────────────────────────────────────

        if path == "/api/exemplos":
            imgs = []

            if os.path.isdir(IMAGEM_DIR):

                for filename in sorted(
                    os.listdir(IMAGEM_DIR)
                ):
                    if filename.lower().endswith(
                        (
                            ".jpg",
                            ".jpeg",
                            ".png",
                            ".webp",
                        )
                    ):
                        imgs.append({
                            "nome": filename,
                            "url": f"/imagem/{filename}",
                        })

            self._json({
                "success": True,
                "imagens": imgs,
            })

            return

        # ─────────────────────────────────────────────────────
        # /imagem/<nome>
        # ─────────────────────────────────────────────────────

        if path.startswith("/imagem/"):

            filename = os.path.basename(path)

            file_path = os.path.join(
                IMAGEM_DIR,
                filename,
            )

            # Primeiro procura em imagem/
            if os.path.isfile(file_path):
                self._servir_imagem(
                    file_path,
                    filename,
                )

                return

            # Depois procura em site/imagem/
            file_path2 = os.path.join(
                SITE_IMAGEM_DIR,
                filename,
            )

            if os.path.isfile(file_path2):
                self._servir_imagem(
                    file_path2,
                    filename,
                )

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

        self.send_response(200)

        self.send_header(
            "Content-Type",
            content_type,
        )

        self.send_header(
            "Cache-Control",
            "no-cache",
        )

        self._cors_headers()

        self.end_headers()

        with open(file_path, "rb") as arquivo:
            self.wfile.write(
                arquivo.read()
            )

    # ─────────────────────────────────────────────────────────
    # POST
    # ─────────────────────────────────────────────────────────

    def do_POST(self):

        parsed = urllib.parse.urlparse(
            self.path
        )

        path = parsed.path

        length = int(
            self.headers.get(
                "Content-Length",
                0,
            )
        )

        body = self.rfile.read(length)

        # ─────────────────────────────────────────────────────
        # /api/upload
        # ─────────────────────────────────────────────────────

        if path == "/api/upload":

            try:
                data = json.loads(
                    body.decode("utf-8")
                )

                imagem_base64 = data.get(
                    "imagem",
                    "",
                )

                nome = data.get(
                    "nome",
                    "",
                )

                if not imagem_base64:
                    self._json({
                        "success": False,
                        "error": "Nenhuma imagem enviada.",
                    }, 400)

                    return

                nome_final = _salvar_imagem(
                    imagem_base64,
                    nome,
                )

                self._json({
                    "success": True,
                    "nome": nome_final,
                    "url": f"/imagem/{nome_final}",
                })

            except Exception as e:
                traceback.print_exc()

                self._json({
                    "success": False,
                    "error": str(e),
                }, 500)

            return

        # ─────────────────────────────────────────────────────
        # /api/chat
        # ─────────────────────────────────────────────────────

        if path == "/api/chat":

            try:
                data = json.loads(
                    body.decode("utf-8")
                )

                pergunta = data.get(
                    "pergunta",
                    "",
                ).strip()

                imagem_base64 = data.get(
                    "imagem",
                    "",
                )

                nome_imagem = data.get(
                    "nome_imagem",
                    "",
                ).strip()

                # ─────────────────────────────────────────────
                # 1. Salvar imagem
                # ─────────────────────────────────────────────

                if imagem_base64:

                    if not nome_imagem:
                        nome_imagem = (
                            f"upload_{int(time.time())}.jpg"
                        )

                    nome_imagem = _salvar_imagem(
                        imagem_base64,
                        nome_imagem,
                    )

                # ─────────────────────────────────────────────
                # 2. Montar prompt
                # ─────────────────────────────────────────────

                if nome_imagem and pergunta:

                    prompt_agente = (
                        f"Analise a imagem "
                        f"'{nome_imagem}' e responda: "
                        f"{pergunta}"
                    )

                elif nome_imagem:

                    prompt_agente = (
                        f"Analise detalhadamente "
                        f"a imagem '{nome_imagem}'."
                    )

                elif pergunta:

                    prompt_agente = pergunta

                else:
                    self._json({
                        "success": False,
                        "error": (
                            "Envie uma pergunta "
                            "ou uma imagem."
                        ),
                    }, 400)

                    return

                print(
                    f"\n[API Chat] Prompt → "
                    f"'{prompt_agente}'"
                )

                # ─────────────────────────────────────────────
                # 3. Verificar agente
                # ─────────────────────────────────────────────

                if orquestrador is None:

                    self._json({
                        "success": False,
                        "error": (
                            "Agente VisionMind "
                            "não está disponível."
                        ),
                    }, 503)

                    return

                # ─────────────────────────────────────────────
                # 4. Executar agente
                # ─────────────────────────────────────────────

                inicio = time.time()

                resposta = orquestrador.invoke({
                    "input": prompt_agente,
                })

                duracao = round(
                    time.time() - inicio,
                    2,
                )

                output_texto = _output_para_texto(
                    resposta
                )

                print(
                    f"[API Chat] "
                    f"Concluído em {duracao}s"
                )

                # ─────────────────────────────────────────────
                # 5. Resposta ao frontend
                # ─────────────────────────────────────────────

                self._json({
                    "success": True,
                    "output": output_texto,
                    "tempo": duracao,
                    "prompt_usado": prompt_agente,
                    "imagem_usada": nome_imagem,
                })

            except json.JSONDecodeError:

                self._json({
                    "success": False,
                    "error": "JSON inválido.",
                }, 400)

            except Exception as e:

                traceback.print_exc()

                self._json({
                    "success": False,
                    "error": str(e),
                }, 500)

            return

        # ─────────────────────────────────────────────────────
        # Rota não encontrada
        # ─────────────────────────────────────────────────────

        self._json({
            "success": False,
            "error": "Rota não encontrada.",
        }, 404)


# ─────────────────────────────────────────────────────────────
# Servidor
# ─────────────────────────────────────────────────────────────

def run(port: int = 8000):

    server_address = (
        "",
        port,
    )

    httpd = HTTPServer(
        server_address,
        VisionMindHTTPRequestHandler,
    )

    status_agente = (
        "OK"
        if orquestrador
        else "INDISPONÍVEL"
    )

    print(
        f"""
╔══════════════════════════════════════════════════╗
║       VisionMind · GenLabs Design System        ║
╠══════════════════════════════════════════════════╣
║  Acesse: http://localhost:{port:<22}║
║  Agente: {status_agente:<40}║
║  Pressione Ctrl+C para encerrar                 ║
╚══════════════════════════════════════════════════╝
"""
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

    porta = 8000

    if len(sys.argv) > 1:
        try:
            porta = int(
                sys.argv[1]
            )

        except ValueError:
            print(
                "[AVISO] Porta inválida. "
                "Usando porta 8000."
            )

    run(porta)