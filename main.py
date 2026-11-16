import time

from agente.orquestrador import AgenteOrquestrador
from my_helper import configurar_console


def main():
    configurar_console()

    agente = AgenteOrquestrador()

    historico = []

    print("""
    === Assistente IA ===

    Exemplos:
    - Explique o que são desvios condicionais
    - Faça uma análise da imagem exemplo_grafico.jpg

    Digite 'sair' para encerrar.
    """)

    while True:
        pergunta = input("Você: ").strip()

        if not pergunta:
            continue

        if pergunta.lower() in ["sair", "exit", "quit"]:
            print("Até logo!")
            break

        try:
            inicio = time.time()

            resposta = agente.responder(pergunta, historico)

            fim = time.time()

            historico.append((pergunta, resposta))
            historico = historico[-6:]

            print("\nAssistente:")
            print(resposta)
            print(f"\n⏱ Tempo: {fim - inicio:.2f}s")

        except Exception as e:
            print(f"\nErro: {e}\n")


if __name__ == "__main__":
    main()
