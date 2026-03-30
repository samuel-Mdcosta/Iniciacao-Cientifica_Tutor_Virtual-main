# 🧠 Neuroscience Virtual Tutor — RAG-based AI Tutoring System

> **Academic research project (Iniciação Científica) at Universidade Uniderp.** A virtual tutor powered by Retrieval-Augmented Generation (RAG) that answers neuroscience questions and generates quizzes grounded strictly in curated academic literature — not LLM hallucinations.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas_Vector_Search-47A248?style=flat&logo=mongodb&logoColor=white)](https://mongodb.com/atlas)
[![Gemini](<https://img.shields.io/badge/LLM-Gemma_3_27B_(Gemini)-4285F4?style=flat&logo=google&logoColor=white>)](https://ai.google.dev)
[![Nomic](https://img.shields.io/badge/Embeddings-Nomic_v1.5-8B5CF6?style=flat)](https://nomic.ai)
[![Status](https://img.shields.io/badge/status-research_prototype-yellow?style=flat)]()

---

## Research context

This system was built as a collaborative research initiative between undergraduate students and a master's student at Universidade Uniderp, with the goal of exploring AI-assisted education for **Applied Neuroscience**.

The core research question: _can a RAG-based tutor reduce the hallucination problem common in general-purpose LLMs when applied to a specialized, high-stakes academic domain?_

The answer implemented here: yes — by grounding every response in vector-retrieved chunks from verified academic PDFs, the system constrains the LLM to only answer from the provided knowledge base. Students get answers tied to real literature, not confident fabrications.

---

## How RAG works in this system

Standard LLMs generate responses from parametric memory (training data), which can hallucinate facts, especially in specialized domains. RAG augments generation with a retrieval step: the model only synthesizes what it can actually find in the knowledge base.

```
                    ┌─────────────────────────────────┐
                    │         INGESTION PIPELINE       │
                    │                                 │
  Academic PDFs ──► │  PyMuPDF extraction             │
  (files/)          │       │                         │
                    │       ▼                         │
                    │  Dynamic semantic chunking       │
                    │  (sentence-boundary aware)       │
                    │       │                         │
                    │       ▼                         │
                    │  Nomic embed-text-v1.5          │
                    │  (vector embeddings)             │
                    │       │                         │
                    │       ▼                         │
                    │  MongoDB Atlas Vector Index      │
                    └─────────────────────────────────┘

                    ┌─────────────────────────────────┐
                    │         QUERY PIPELINE          │
                    │                                 │
  Student asks ───► │  Nomic embed (question)         │
  a question        │       │                         │
                    │       ▼                         │
                    │  MongoDB Vector Search          │
                    │  (top-8 similar chunks)         │
                    │       │                         │
                    │       ▼                         │
                    │  Context + prompt assembly      │
                    │       │                         │
                    │       ▼                         │
                    │  Gemma 3 27B (via Gemini API)   │
                    │       │                         │
                    │       ▼                         │
                    └──── Grounded answer ────────────┘
```

---

## Key technical decisions

**Why Nomic `embed-text-v1.5` for embeddings?**
Nomic's model is purpose-built for document retrieval with high-quality semantic representations at a competitive cost. It handles domain-specific academic language better than general embedding models at similar size.

**Why dynamic semantic chunking instead of fixed-size chunks?**
Fixed-size chunking (e.g. 512 tokens) splits mid-sentence and destroys semantic coherence. The custom `create_dinamic_chunk` algorithm respects sentence boundaries, preserving the meaning of each chunk and improving retrieval precision for technical content.

**Why top-8 retrieval?**
Neuroscience topics often require cross-referencing multiple sources (e.g. a question about synaptic plasticity may span neurochemistry, anatomy, and behavioral research chapters). Retrieving 8 chunks gives the LLM enough context without overwhelming the prompt window.

**Why MongoDB Atlas instead of a dedicated vector DB (Pinecone, Weaviate)?**
The project runs in a university research context where operational simplicity matters. MongoDB Atlas combines standard document persistence and vector search in a single managed service — no extra infrastructure, one connection string.

---

## Tech stack

| Component      | Technology                                           |
| -------------- | ---------------------------------------------------- |
| API framework  | FastAPI + Uvicorn                                    |
| LLM            | Gemma 3 27B (`gemma-3-27b-it`) via Google Gemini API |
| Embeddings     | Nomic `nomic-embed-text-v1.5`                        |
| Vector store   | MongoDB Atlas Vector Search                          |
| PDF extraction | PyMuPDF (Fitz)                                       |
| Chunking       | Custom semantic algorithm (sentence-boundary aware)  |
| Dev interface  | CLI (`menuCMD.py`)                                   |

---

## Project structure

```
Iniciacao-Cientifica_Tutor_Virtual/
├── App/
│   └── Backend/
│       ├── config/
│       │   └── instructions.py      # Tutor personas & system prompts
│       ├── database/
│       │   └── vectorStore.py       # MongoDB Atlas connection & vector search
│       ├── embedding/
│       │   └── embedGenerate.py     # Nomic API integration
│       ├── engine/
│       │   └── ragGenerate.py       # RAG orchestrator (retrieval + generation)
│       └── rag/
│           ├── chunkGenerate.py     # Semantic chunking logic
│           └── extractorPDF.py      # PDF text extraction (PyMuPDF)
│   └── Frontend/
│       └── menuCMD.py               # CLI dev interface
├── files/                           # Academic PDFs (knowledge base)
├── files_test/                      # Test PDFs
├── main.py                          # FastAPI entry point
├── ingestao.py                      # Ingestion pipeline script
└── requirements.txt
```

---

## Getting started

### Prerequisites

- Python 3.10+
- MongoDB Atlas cluster with Vector Search enabled
- Google Gemini API key
- Nomic API key (or `nomic login` via CLI)

### Installation

```bash
git clone https://github.com/samuel-Mdcosta/Iniciacao-Cientifica_Tutor_Virtual-main.git
cd Iniciacao-Cientifica_Tutor_Virtual-main

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
MONGO_ADDRESS=your_mongodb_atlas_connection_string
MONGO_DB=your_database_name
MONGO_COLLECTION=your_collection_name
NOMIC_API_KEY=your_nomic_api_key
```

### Step 1 — Ingest your academic PDFs

Place your neuroscience PDFs in the `files/` directory, then run the ingestion pipeline:

```bash
python ingestao.py
```

This extracts text from each PDF, splits it into semantic chunks, generates Nomic embeddings, and stores everything in MongoDB Atlas with a vector index.

### Step 2 — Start the API server

```bash
uvicorn main:app --reload
```

API available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Step 3 (optional) — Use the CLI interface

```bash
python App/Frontend/menuCMD.py
```

---

## API endpoints

### `POST /llm` — Ask a question

```http
POST /llm
Content-Type: application/json

{
  "texto": "What is the role of the hippocampus in long-term memory formation?"
}
```

The system retrieves the 8 most semantically similar chunks from the knowledge base and passes them as context to Gemma 3 27B, which generates a grounded answer citing the retrieved material.

### `POST /quizz` — Generate a quiz

```http
POST /quizz
Content-Type: application/json

{
  "texto": "synaptic plasticity"
}
```

Returns multiple-choice questions generated by the LLM, grounded in retrieved academic content on the requested topic.

---

## MongoDB Atlas setup

This system requires a Vector Search index on your collection. Create it via the Atlas UI or CLI with the following configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    }
  ]
}
```

> `numDimensions: 768` matches the output size of Nomic `embed-text-v1.5`.

---

## Research status

This is an active research prototype developed as part of an Iniciação Científica at Universidade Uniderp. The system is under ongoing development as part of the research group's work on AI-assisted neuroscience education.

The backend orchestration layer (user management, engagement tracking, quiz attempt recording) is handled by a companion service: [ragiaic](https://github.com/samuel-Mdcosta/ragiaic).

---

## Author

**Samuel M. Costa** — Backend Developer | Python · AI & LLMs · RAG Systems

- LinkedIn: [linkedin.com/in/samuelmdcosta](https://linkedin.com/in/samuelmdcosta)
- Email: costadev19@gmail.com
- GitHub: [github.com/samuel-Mdcosta](https://github.com/samuel-Mdcosta)
