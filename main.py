from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from App.Backend.config.instructions import Instructions
import os
import json
import random
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from App.Backend.engine.ragGenerate import RagGenerate

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-lite-latest"


def montar_uso_tokens(usage):
    """Extrai a contagem real de tokens; usage pode ser None em respostas bloqueadas."""
    return {
        "entrada": usage.prompt_token_count if usage else None,
        "saida": usage.candidates_token_count if usage else None,
        "total": usage.total_token_count if usage else None,
    }


def montar_contexto(relevant_docs):
    """Monta o texto de contexto (RAG) a partir dos documentos recuperados."""
    context_text = ""
    if 'documents' in relevant_docs and relevant_docs['documents']:
        for doc in relevant_docs['documents']:
            context_text += f"[Fonte: {doc['file_name']}]\n{doc['chunk']}\n\n"
    return context_text


def embaralhar_alternativas(quizz_estruturado):
    questoes = quizz_estruturado.get("questoes") if isinstance(quizz_estruturado, dict) else None
    if not isinstance(questoes, list):
        return quizz_estruturado

    for questao in questoes:
        if not isinstance(questao, dict):
            continue
        opcoes = questao.get("opcoes")
        correta = questao.get("correta")
        if not isinstance(opcoes, list) or not isinstance(correta, int):
            continue
        if not (0 <= correta < len(opcoes)):
            continue

        indices = list(range(len(opcoes)))
        random.shuffle(indices)
        questao["opcoes"] = [opcoes[i] for i in indices]
        questao["correta"] = indices.index(correta)

    return quizz_estruturado


def build_config(system_instruction):
    """Config do Gemini com a instrução do sistema separada do input do usuário."""
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.1,
        max_output_tokens=2048,
    )


def conteudo_usuario(texto):
    """Encapsula o input do usuário como turno de role 'user' (mitiga prompt injection)."""
    return [types.Content(role="user", parts=[types.Part(text=texto)])]


class RequisicaoQuizz(BaseModel):
    texto: str = Field(..., min_length=3, max_length=1000)


class RequisicaoLlm(BaseModel):
    texto: str = Field(..., min_length=3, max_length=1000)


class Menu():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.instructions = Instructions()
        self.recovery = RagGenerate()


sistema_tutor = Menu()

app = FastAPI()


@app.post("/quizz")
async def perguntas(req: RequisicaoQuizz):
    instrucao_quiz = sistema_tutor.instructions.get_instructions("02")

    relevant_docs = sistema_tutor.recovery.compare_vector(req.texto)
    context_text = montar_contexto(relevant_docs)

    json_response = sistema_tutor.client.models.generate_content(
        model=MODEL,
        contents=conteudo_usuario(req.texto),
        config=build_config(instrucao_quiz.format(CONTEXT=context_text)),
    )

    texto_nformatado = json_response.text
    if texto_nformatado is None:
        return JSONResponse(
            status_code=502,
            content={"erro": "Resposta bloqueada pelo filtro de segurança do modelo"}
        )

    texto_formatado = texto_nformatado.replace("```json", "").replace("```", "").strip()

    try:
        quizz_estruturado = json.loads(texto_formatado)
    except json.JSONDecodeError as e:
        logger.warning("LLM retornou JSON inválido em /quizz: %s | raw=%.200s", e, texto_nformatado)
        return JSONResponse(
            status_code=502,
            content={"erro": "Formato inválido gerado pela IA", "texto_nformatado": texto_nformatado}
        )

    quizz_estruturado = embaralhar_alternativas(quizz_estruturado)

    return {
        "tema": req.texto,
        "quizz_gerado_llm": quizz_estruturado,
        "uso_tokens": montar_uso_tokens(json_response.usage_metadata),
    }


@app.post("/llm")
async def llm_response(req: RequisicaoLlm):
    response_prompt = sistema_tutor.instructions.get_instructions("01")

    relevant_docs = sistema_tutor.recovery.compare_vector(req.texto)
    context_text = montar_contexto(relevant_docs)

    response = sistema_tutor.client.models.generate_content(
        model=MODEL,
        contents=conteudo_usuario(req.texto),
        config=build_config(response_prompt.format(CONTEXT=context_text)),
    )

    texto_nformatado = response.text
    if texto_nformatado is None:
        return JSONResponse(
            status_code=502,
            content={"erro": "Resposta bloqueada pelo filtro de segurança do modelo"}
        )

    texto_formatado = texto_nformatado.replace("```json", "").replace("```", "").strip()

    try:
        resposta_estruturada = json.loads(texto_formatado)
    except json.JSONDecodeError as e:
        logger.warning("LLM retornou JSON inválido em /llm: %s | raw=%.200s", e, texto_nformatado)
        return JSONResponse(
            status_code=502,
            content={"erro": "Formato inválido gerado pela IA", "texto_nformatado": texto_nformatado}
        )

    return {
        "pergunta": req.texto,
        "resposta_tutor": resposta_estruturada,
        "documentos_utilizados": relevant_docs,
        "uso_tokens": montar_uso_tokens(response.usage_metadata),
    }
