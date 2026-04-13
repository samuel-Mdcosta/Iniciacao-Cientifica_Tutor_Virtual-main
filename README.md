# Tutor Virtual de Neurociência — Sistema RAG

Backend de um Tutor Virtual baseado em Inteligência Artificial, desenvolvido como projeto de Iniciação Científica com foco no ensino de Neurociência Aplicada.

O sistema utiliza a arquitetura **RAG (Retrieval-Augmented Generation)** para fundamentar as respostas do tutor exclusivamente em materiais didáticos fornecidos (PDFs), mitigando alucinações do modelo de linguagem.

---

## Arquitetura e Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| API Web | FastAPI + Uvicorn |
| LLM Generativo | Google Gemini (`gemma-3-27b-it`) via `google-genai` SDK |
| Embeddings | Nomic (`nomic-embed-text-v1.5`) |
| Banco de Dados Vetorial | MongoDB Atlas (Vector Search) |
| Processamento de PDF | PyMuPDF (`fitz`) + algoritmo de chunking customizado |

---

## Estrutura do Projeto

```
Iniciacao-Cientifica_Tutor_Virtual/
│
├── App/
│   ├── Backend/
│   │   ├── config/
│   │   │   └── instructions.py      # Prompts de sistema (personas do tutor e do quizz)
│   │   ├── database/
│   │   │   └── vectorStore.py       # Conexão com MongoDB Atlas e operações de Vector Search
│   │   ├── embedding/
│   │   │   └── embedGenerate.py     # Geração de embeddings via API do Nomic
│   │   ├── engine/
│   │   │   └── ragGenerate.py       # Orquestração do pipeline RAG (recuperação + geração)
│   │   └── rag/
│   │       ├── extractorPDF.py      # Extração de texto de PDFs
│   │       └── chunkGenerate.py     # Fragmentação de texto (chunking estático e dinâmico)
│   └── Fontend/
│       ├── api.py                   # Servidor Flask (interface legada)
│       ├── menu.py                  # Lógica de menu e sessão de chat
│       └── menuCMD.py               # Interface de linha de comando (CLI)
│
├── files/                           # PDFs dos materiais didáticos para ingestão
├── files_test/                      # PDFs para testes
├── main.py                          # Servidor FastAPI principal (endpoints /llm e /quizz)
├── ingestao.py                      # Script de ETL: lê PDFs, gera chunks e salva no MongoDB
├── requirements.txt                 # Dependências do projeto
└── .env                             # Variáveis de ambiente (não versionado)
```

---

## Como Funciona

### Pipeline RAG

```
Pergunta do Aluno
      │
      ▼
[EmbedGenerate]  →  Gera vetor da pergunta (Nomic)
      │
      ▼
[VectorStoreMongo]  →  Busca os 8 chunks mais similares (MongoDB Vector Search)
      │
      ▼
[Instructions]  →  Injeta contexto recuperado no prompt de sistema
      │
      ▼
[Gemini LLM]  →  Gera resposta fundamentada no contexto
      │
      ▼
Resposta estruturada (JSON)
```

### Chunking

O sistema suporta dois modos de fragmentação de texto:

- **Estático:** chunks de 500 caracteres com overlap de 50 caracteres.
- **Dinâmico:** fragmentação por fronteiras de sentenças (ponto final), com overlap de 10 palavras para manter coerência semântica entre chunks.

---

## Configuração e Instalação

### 1. Pré-requisitos

- Python 3.10+
- Conta no [MongoDB Atlas](https://www.mongodb.com/atlas) com um cluster configurado
- Chave de API do [Google AI Studio](https://aistudio.google.com/) (Gemini)
- Chave de API do [Nomic](https://nomic.ai/)

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
GEMINI_API_KEY=sua_chave_gemini
NOMIC_API_KEY=sua_chave_nomic
MONGO_ADDRESS=sua_connection_string_mongodb
MONGO_DB=nome_do_banco
MONGO_COLLECTION=nome_da_colecao
```

### 4. Configurar o índice de Vector Search no MongoDB Atlas

No MongoDB Atlas, crie um índice de Vector Search na coleção configurada com o nome `vector-search-index` apontando para o campo `vector`.

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "vector",
      "numDimensions": 768,
      "similarity": "cosine"
    }
  ]
}
```

---

## Ingestão dos Dados

Coloque os PDFs dos materiais didáticos na pasta `files/` e execute:

```bash
python ingestao.py
```

O script irá:
1. Extrair o texto de todos os PDFs
2. Fragmentar o texto em chunks
3. Gerar embeddings via Nomic
4. Salvar os vetores e chunks no MongoDB Atlas

---

## Executando o Servidor

```bash
uvicorn main:app --reload
```

O servidor sobe em `http://localhost:8000`.

---

## Endpoints da API

### `POST /llm`

Envia uma pergunta ao tutor e recebe uma resposta fundamentada nos materiais didáticos.

**Request:**
```json
{
  "texto": "O que é a sinapse química?"
}
```

**Response:**
```json
{
  "pergunta": "O que é a sinapse química?",
  "resposta_tutor": "...",
  "documentos_utilizados": { "documents": [[...]] }
}
```

---

### `POST /quizz`

Gera uma lista de questões de múltipla escolha (5 alternativas: a, b, c, d, e) sobre um tema, com base no conteúdo dos materiais. A alternativa correta é distribuída aleatoriamente entre as letras a cada questão.

**Request:**
```json
{
  "texto": "Potencial de ação"
}
```

**Response:**
```json
{
  "tema": "Potencial de ação",
  "quizz_gerado_llm": [
    {
      "question": "Enunciado da questão",
      "options": {
        "a": "...",
        "b": "...",
        "c": "...",
        "d": "...",
        "e": "..."
      }
    }
  ]
}
```

---

## Variáveis de Ambiente

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave de API do Google Gemini |
| `NOMIC_API_KEY` | Chave de API do Nomic para geração de embeddings |
| `MONGO_ADDRESS` | Connection string do MongoDB Atlas |
| `MONGO_DB` | Nome do banco de dados |
| `MONGO_COLLECTION` | Nome da coleção onde os chunks/vetores são armazenados |
