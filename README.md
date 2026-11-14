# Tutor Virtual de Neurociência — Motor de IA (RAG)

Motor de IA do Tutor Virtual de Neurociência, projeto de Iniciação Científica com foco no ensino de Neurociência Aplicada.

Usa **RAG (Retrieval-Augmented Generation)** para fundamentar o que o modelo diz em materiais didáticos (PDFs), reduzindo
alucinações. É um serviço FastAPI **chamado pelo backend Laravel** ([ragiaic](https://github.com/samuel-Mdcosta/ragiaic)),
nunca direto pelo aluno ou pelo front.

## Papel no sistema

```
Front (React)  →  ragiaic (Laravel)  →  este motor (FastAPI)  →  Gemini / MongoDB Atlas
```

- As **questões do quiz** vêm do banco de questões do Laravel (revisadas pelo docente), não são mais geradas aqui na hora.
- Este motor gera o **feedback de desempenho** do aluno (`POST /feedback`), que é o endpoint em uso. `/quizz` e `/llm`
  continuam disponíveis (geração de questões ao vivo e chat), mas o front atual não os usa.
- **Quem controla a fila e os limites é o Laravel.** Ele escolhe a chave e o modelo de cada chamada, respeita os limites por
  minuto e por dia e repete a tentativa quando preciso. O motor só gera.

---

## Arquitetura e Tecnologias

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.10+ |
| API Web | FastAPI + Uvicorn |
| LLM generativo | Google Gemini via SDK `google-genai`. Modelo padrão: `gemini-flash-lite-latest` (constante `MODEL` em `main.py`) |
| Embeddings | Gemini `gemini-embedding-2`, 3072 dimensões (mesmo SDK e mesma chave do LLM) |
| Banco vetorial | MongoDB Atlas (Vector Search) |
| PDF | PyMuPDF (`fitz`) + chunking estático |
| Testes | pytest + httpx |

---

## Estrutura do Projeto

```
├── App/
│   ├── Backend/
│   │   ├── config/instructions.py       # Prompts de sistema: 01 chat, 02 quiz, 03 feedback de desempenho
│   │   ├── database/vectorStore.py      # MongoDB Atlas: inserção e busca vetorial
│   │   ├── embedding/embedGenerate.py   # Embeddings via Gemini
│   │   ├── engine/
│   │   │   ├── ragGenerate.py           # Recuperação: embedding da pergunta + busca vetorial
│   │   │   └── feedbackDesempenho.py    # Monta consultas e contexto, interpreta e sanitiza o JSON do feedback
│   │   └── rag/
│   │       ├── extractorPDF.py          # Extração de texto dos PDFs da pasta files/
│   │       └── chunkGenerate.py         # Chunking estático
│   └── Fontend/                         # Interface legada (Flask e CLI); não faz parte do sistema atual
├── tests/                               # test_feedback.py (feedback, chaves, modelos, contexto pronto)
├── main.py                              # Servidor FastAPI (/feedback, /quizz, /llm)
├── ingestao.py                          # ETL: PDFs → chunks → embeddings → MongoDB
├── requirements.txt / requirements-dev.txt
└── .env                                 # Variáveis de ambiente (não versionado)
```

A pasta `files/` (PDFs para ingestão) não é versionada: crie-a antes de rodar a ingestão.

---

## Como Funciona

### Pipeline RAG

```
Texto (pergunta, tema ou áreas do aluno)
      │
      ▼
[EmbedGenerate]     →  vetor da consulta (gemini-embedding-2)
      │
      ▼
[VectorStoreMongo]  →  até 4 chunks mais similares, só os com score >= 0.75
      │
      ▼
[Instructions]      →  contexto recuperado entra no prompt de sistema
      │
      ▼
[Gemini]            →  resposta em JSON, fundamentada no contexto
```

### Chunking

Estático: chunks de 1000 caracteres com overlap de 100 caracteres.

### Feedback de desempenho

O Laravel envia os números já calculados (taxas, nível, tendência) e as áreas prioritárias. O LLM não recalcula nada: só
diagnostica o padrão dos erros e indica o que, por que e onde estudar. Dois modos de contexto:

- **Com `contexto`** (o usado pelo Laravel hoje): o pedido já traz o material de apoio, montado das justificativas e dos
  livros das questões que o aluno errou. O motor **não consulta o Atlas** e usa essas fontes. `citacoes` troca o título do
  livro pela citação completa.
- **Sem `contexto`:** o motor faz uma busca vetorial por área prioritária, com o tema e os subtemas errados.

Em ambos, `onde_estudar` só aceita materiais que vieram do contexto; referências inventadas pelo modelo são descartadas.

---

## Configuração e Instalação

### 1. Pré-requisitos

- Python 3.10+
- Cluster no [MongoDB Atlas](https://www.mongodb.com/atlas) com a coleção de chunks já ingerida
- Chave de API do [Google AI Studio](https://aistudio.google.com/) (Gemini)

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Variáveis de ambiente

Crie um `.env` na raiz (modelo em `.env.example`):

| Variável | Descrição |
|---|---|
| `GEMINI_API_KEY` | Chave principal do Gemini (rótulo `principal`) |
| `GEMINI_API_KEY_BACKUP` | Chave reserva (rótulo `reserva`). Sem ela, um pedido com `chave: "reserva"` recebe 422 |
| `GEMINI_MODEL`, `GEMINI_MODEL_FALLBACK` | Modelos aceitos no campo `modelo` do `/feedback`, além do padrão do motor. Devem ser os mesmos configurados no Laravel |
| `SHARED_SECRET` | Segredo do serviço. Deve ser idêntico a `PYTHON_SERVICE_SECRET` no `.env` do Laravel |
| `MONGO_ADDRESS` | Connection string do MongoDB Atlas |
| `MONGO_DB` | Nome do banco |
| `MONGO_COLLECTION` | Coleção dos chunks e vetores |

As chaves do Gemini **nunca trafegam**: o Laravel só manda o rótulo (`principal` ou `reserva`) e o motor busca a chave
no próprio ambiente.

### 4. Índice de Vector Search no Atlas

Na coleção configurada, crie um índice chamado `vector-search-index` no campo `vector`:

```json
{
  "fields": [
    { "type": "vector", "path": "vector", "numDimensions": 3072, "similarity": "cosine" }
  ]
}
```

---

## Ingestão dos Dados

Coloque os PDFs em `files/` e execute:

```bash
python ingestao.py
```

O script extrai o texto, gera os chunks, cria os embeddings e salva tudo no MongoDB Atlas. **Não rode a ingestão sobre uma
coleção que já está populada**: os documentos seriam duplicados.

---

## Executando o Servidor

```bash
uvicorn main:app --reload
```

Sobe em `http://localhost:8000`.

---

## Endpoints da API

Todos exigem o cabeçalho `X-API-Key` com o valor de `SHARED_SECRET`; sem ele a resposta é 401.

### `POST /feedback` (em uso)

Gera o feedback de desempenho do aluno.

**Request (resumido):**
```json
{
  "desempenho_por_tema": [
    { "tema": "Hipocampo e memória espacial", "tentativas": 2, "questoes": 20, "acertos": 8, "erros": 12,
      "taxa_acerto": 40.0, "taxa_recente": 40.0, "nivel": "critico", "tendencia": "melhorando" }
  ],
  "areas_prioritarias": [
    { "tema": "Hipocampo e memória espacial",
      "questoes_erradas": [{ "pergunta": "...", "subtema": "Circuito de Papez", "resposta_escolhida": "...", "resposta_correta": "..." }],
      "subtemas_acertados": ["Amígdala e emoção"] }
  ],
  "temas_nao_praticados": ["Sistemas e processos da memória"],
  "chave": "principal",
  "modelo": "gemini-3.5-flash-lite",
  "contexto": "### Área: ...\n[Fonte: Neuroanatomia Funcional]\n...",
  "fontes_por_tema": { "Hipocampo e memória espacial": ["Neuroanatomia Funcional"] },
  "citacoes": { "Neuroanatomia Funcional": "MACHADO, A. Neuroanatomia funcional. ..." }
}
```

`chave` (`principal` ou `reserva`, padrão `principal`), `modelo`, `contexto`, `fontes_por_tema` e `citacoes` são opcionais.

**Response:**
```json
{
  "feedback": {
    "resumo_geral": "...",
    "areas_prioritarias": [
      { "tema": "Hipocampo e memória espacial", "diagnostico": "...", "o_que_estudar": ["Circuito de Papez"],
        "por_que_estudar": "...", "onde_estudar": ["Neuroanatomia Funcional"] }
    ],
    "pontos_fortes": ["..."],
    "proximos_passos": ["..."]
  },
  "uso_tokens": { "entrada": 0, "saida": 0, "total": 0 }
}
```

**Erros:**

| Código | Quando |
|---|---|
| 401 | `X-API-Key` ausente ou errada |
| 422 | `modelo` fora da lista permitida, ou `chave: "reserva"` sem `GEMINI_API_KEY_BACKUP` |
| 502 | Falha do Gemini, resposta bloqueada ou JSON inválido. Quando vem do Gemini, o corpo traz `status_gemini` (ex.: 429), que o Laravel usa para decidir a nova tentativa |
| 503 | Banco de vetores indisponível (só nos modos que consultam o Atlas) |

### `POST /quizz` (legado)

Gera questões de múltipla escolha de um tema com base nos materiais. Body: `{ "texto": "Potencial de ação" }`. Cada questão
traz `pergunta`, `opcoes` (5 alternativas, embaralhadas pelo motor), `correta` (índice 0 a 4), `explicacao`, `subtema` e `referencias`.
Retorna `{ "tema", "quizz_gerado_llm", "uso_tokens" }`, com as questões em `quizz_gerado_llm.questoes`.

### `POST /llm` (legado)

Pergunta ao tutor, com resposta fundamentada nos materiais. Body: `{ "texto": "O que é a sinapse química?" }`. Retorna
`{ "pergunta", "resposta_tutor", "documentos_utilizados", "uso_tokens" }`.

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes não usam rede: o Gemini e o Atlas são substituídos por dublês.
