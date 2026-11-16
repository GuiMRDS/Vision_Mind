# 🧠 VisionMind

Assistente multimodal desenvolvido com **Python, LangChain e Google Gemini**, capaz de analisar imagens, responder perguntas, explicar conceitos e utilizar ferramentas inteligentes através de um agente orquestrador.

---

## 📸 Interface
![Tela Principal](imagem/VisionMind.jpg)

---

## 🚀 Funcionalidades

- 🤖 Assistente conversacional
- 🖼️ Análise de imagens com Gemini Vision
- 🧠 Explicação de conceitos e conteúdos
- 🔧 Agente Orquestrador com LangChain
- 📤 Upload de imagens pela interface
- 🌐 Aplicação Web responsiva
- 📡 Comunicação Frontend ↔ Backend

---

## 🏗️ Arquitetura

```text
Usuário
   ↓
Frontend (HTML + JavaScript)
   ↓
Servidor Python
   ↓
Agente Orquestrador
   ↓
 ┌─────────────────────────┐
 │ Ferramenta Explicadora  │
 └─────────────────────────┘

 ┌─────────────────────────┐
 │ Ferramenta Analisadora  │
 │ de Imagens              │
 └─────────────────────────┘
   ↓
Google Gemini
```

---

## 🛠️ Tecnologias

### Backend

- Python
- LangChain
- Google Gemini
- Pillow
- HTTPServer

### Frontend

- HTML5
- Tailwind CSS
- JavaScript

### IA

- Gemini Flash
- Gemini Vision

---

## ⚙️ Instalação

### Clonar repositório

```bash
git clone https://github.com/GuiMRDS/Vision_Mind.git
cd Vision_Mind
```

### Criar ambiente virtual

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuração

Crie um arquivo `.env`:

```env
GEMINI_API_KEY="SUA_CHAVE"
```

---

## ▶️ Executando

### Interface Web

```bash
python server.py
```

Acesse:

```text
http://localhost:8000
```

Por padrão o servidor só aceita conexões do próprio computador. Para usar outra porta ou abrir na rede local:

```bash
python server.py 8080
python server.py --host 0.0.0.0   # qualquer pessoa na rede poderá usar sua chave
```

### Terminal

```bash
python main.py
```

---

## 🧪 Testes

Testes automatizados (não acessam a internet nem gastam cota da API):

```bash
python -m unittest discover -s testes -t . -p "test_*.py"
```

Scripts manuais que chamam o Gemini de verdade:

```bash
python -m testes.listar_modelos
python -m testes.teste_modelos
```

---

## 📄 Licença

Este projeto está sob a licença MIT.
