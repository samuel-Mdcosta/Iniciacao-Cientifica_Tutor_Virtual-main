# 🧠 Tutor Virtual de Neurociência (Sistema RAG)

Este repositório contém o backend de um Tutor Virtual baseado em Inteligência Artificial, desenvolvido como projeto de pesquisa universitária focado no ensino de Neurociência Aplicada.

O sistema utiliza a arquitetura **RAG (Retrieval-Augmented Generation)** para mitigar alucinações de LLMs, garantindo que as respostas do tutor sejam estritamente fundamentadas na literatura acadêmica e em materiais didáticos fornecidos (PDFs).

## 🚀 Arquitetura e Tecnologias

O projeto foi construído priorizando modularidade e desempenho:

- **Linguagem:** Python 3.10+
- **Motor Generativo (LLM):** Google Gemini (Modelo `gemma-3-27b-it` via `google-genai` SDK)
- **Vetorização (Embeddings):** Nomic (`nomic-embed-text-v1.5`)
- **Banco de Dados Vetorial:** MongoDB Atlas (Vector Search)
- **API Web:** FastAPI + Uvicorn
- **Processamento de Dados:** PyMuPDF (Fitz) com algoritmo customizado de _chunking_ dinâmico por contexto semântico.

## 📁 Estrutura do Projeto

O código está organizado seguindo o padrão de separação de responsabilidades (Clean Code):

```text
INICIACAO-CIENTIFICA_TUTOR_VIRTUAL/
│
├── data/
│   └── raw/                 # PDFs originais e literatura acadêmica
│
├── src/
│   ├── config/              # Configurações de ambiente e Prompts de Sistema (Personas)
│   ├── database/            # Conexão e operações CRUD/Vector Search no MongoDB Atlas
│   ├── embedding/           # Integração com a API do Nomic para geração de vetores
│   ├── engine/              # Orquestração do RAG (Recuperação e Geração)
│   ├── rag/           # ETL: Extração de texto de PDFs e fragmentação (chunking)
│   └── frontend/           # Pontos de entrada (API FastAPI e CLI)
│
├── main.py                  # Script principal para iniciar a aplicação
├── requirements.txt         # Dependências do projeto
└── .env                     # Variáveis de ambiente (não versionado)
```
