from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field, StringConstraints
from typing import Annotated, List, Literal, Optional
from App.Backend.config.instructions import Instructions
import os
import json
import random
import logging
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from pymongo.errors import PyMongoError
from App.Backend.engine.ragGenerate import RagGenerate
from App.Backend.engine.feedbackDesempenho import (
    interpretar_json_llm,
    montar_consulta_area,
    montar_contexto_areas,
    montar_dados_aluno,
    recuperar_documentos as recuperar_documentos_por_tema,
    sanitizar_feedback,
)

load_dotenv()

logger = logging.getLogger(__name__)

MODEL = "gemini-flash-lite-latest"

# Limite de tokens de saída por endpoint. O chat fica em 2048 para economizar.
# O quiz (10 questões com alternativas, explicação e subtema) e o feedback de
# desempenho passam disso: com 2048 a resposta era cortada no meio e o JSON
# ficava inválido (502). O Gemini cobra só o que gera, então um teto maior não
# encarece respostas curtas.
MAX_TOKENS_CHAT = 2048
MAX_TOKENS_QUIZ = 8192
MAX_TOKENS_FEEDBACK = 4096


def verificar_chave_servico(x_api_key: str = Header(default=None)):
    chave_esperada = os.getenv("SHARED_SECRET")
    if not chave_esperada or x_api_key != chave_esperada:
        raise HTTPException(status_code=401, detail="Chave de acesso inválida")


def montar_uso_tokens(usage):
    return {
        "entrada": usage.prompt_token_count if usage else None,
        "saida": usage.candidates_token_count if usage else None,
        "total": usage.total_token_count if usage else None,
    }


def recuperar_documentos(texto):
    try:
        return sistema_tutor.recovery.compare_vector(texto), None
    except PyMongoError as e:
        logger.error("Falha ao consultar o MongoDB: %s", e)
        return None, JSONResponse(
            status_code=503,
            content={"erro": "Banco de vetores indisponível no momento"},
        )


def montar_contexto(relevant_docs):
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


def build_config(system_instruction, max_output_tokens=MAX_TOKENS_CHAT):
    return types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.1,
        max_output_tokens=max_output_tokens,
    )


def conteudo_usuario(texto):
    return [types.Content(role="user", parts=[types.Part(text=texto)])]


class RequisicaoQuizz(BaseModel):
    texto: str = Field(..., min_length=3, max_length=1000)


class RequisicaoLlm(BaseModel):
    texto: str = Field(..., min_length=3, max_length=1000)


TextoCurto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class DesempenhoTema(BaseModel):
    tema: TextoCurto
    tentativas: int = Field(..., ge=0)
    questoes: int = Field(..., ge=0)
    acertos: int = Field(..., ge=0)
    erros: int = Field(..., ge=0)
    taxa_acerto: float = Field(..., ge=0, le=100)
    taxa_recente: float = Field(..., ge=0, le=100)
    nivel: Literal["critico", "atencao", "bom"]
    tendencia: Optional[Literal["melhorando", "piorando", "estavel"]] = None


class QuestaoErrada(BaseModel):
    pergunta: str = Field(..., min_length=1, max_length=2000)
    subtema: Optional[str] = Field(None, max_length=255)
    resposta_escolhida: Optional[str] = Field(None, max_length=1000)
    resposta_correta: Optional[str] = Field(None, max_length=1000)


class AreaPrioritaria(BaseModel):
    tema: TextoCurto
    questoes_erradas: List[QuestaoErrada] = Field(default_factory=list, max_length=15)
    subtemas_acertados: List[TextoCurto] = Field(default_factory=list, max_length=10)


class RequisicaoFeedback(BaseModel):
    desempenho_por_tema: List[DesempenhoTema] = Field(..., min_length=1, max_length=50)
    areas_prioritarias: List[AreaPrioritaria] = Field(default_factory=list, max_length=3)
    temas_nao_praticados: List[TextoCurto] = Field(default_factory=list, max_length=20)


class Menu():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.instructions = Instructions()
        self.recovery = RagGenerate()


sistema_tutor = Menu()

app = FastAPI()


@app.post("/quizz", dependencies=[Depends(verificar_chave_servico)])
async def perguntas(req: RequisicaoQuizz):
    instrucao_quiz = sistema_tutor.instructions.get_instructions("02")

    relevant_docs, erro = recuperar_documentos(req.texto)
    if erro is not None:
        return erro
    context_text = montar_contexto(relevant_docs)

    json_response = sistema_tutor.client.models.generate_content(
        model=MODEL,
        contents=conteudo_usuario(req.texto),
        config=build_config(instrucao_quiz.format(CONTEXT=context_text), max_output_tokens=MAX_TOKENS_QUIZ),
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


@app.post("/llm", dependencies=[Depends(verificar_chave_servico)])
async def llm_response(req: RequisicaoLlm):
    response_prompt = sistema_tutor.instructions.get_instructions("01")

    relevant_docs, erro = recuperar_documentos(req.texto)
    if erro is not None:
        return erro
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


# Feedback de desempenho: analisa o rendimento do aluno (não questões isoladas).
# Os números e a escolha das áreas prioritárias vêm calculados do backend; o LLM
# diagnostica o padrão dos erros e indica o que, onde e por que estudar, com base no RAG.
# Rota síncrona (def) para o FastAPI rodar as chamadas bloqueantes (Gemini/Mongo) no threadpool.
@app.post("/feedback", dependencies=[Depends(verificar_chave_servico)])
def feedback_desempenho(req: RequisicaoFeedback):
    instrucao_feedback = sistema_tutor.instructions.get_instructions("03")

    consultas = {
        area.tema: montar_consulta_area(area.tema, [q.subtema for q in area.questoes_erradas])
        for area in req.areas_prioritarias
    }
    documentos_por_tema = recuperar_documentos_por_tema(consultas, sistema_tutor.recovery)
    context_text, fontes_por_tema = montar_contexto_areas(documentos_por_tema)

    try:
        response = sistema_tutor.client.models.generate_content(
            model=MODEL,
            contents=conteudo_usuario(montar_dados_aluno(req.model_dump())),
            config=build_config(instrucao_feedback.format(
                CONTEXT=context_text or "Nenhum trecho do material foi recuperado."
            ), max_output_tokens=MAX_TOKENS_FEEDBACK),
        )
    except genai_errors.APIError as e:
        logger.warning("Falha na chamada ao LLM em /feedback: %s", e)
        return JSONResponse(
            status_code=502,
            content={"erro": "Não foi possível gerar o feedback com a IA"}
        )

    texto_nformatado = response.text
    if texto_nformatado is None:
        return JSONResponse(
            status_code=502,
            content={"erro": "Resposta bloqueada pelo filtro de segurança do modelo"}
        )

    try:
        feedback_bruto = interpretar_json_llm(texto_nformatado)
    except json.JSONDecodeError as e:
        logger.warning("LLM retornou JSON inválido em /feedback: %s | raw=%.200s", e, texto_nformatado)
        return JSONResponse(
            status_code=502,
            content={"erro": "Formato inválido gerado pela IA"}
        )

    temas_prioritarios = [area.tema for area in req.areas_prioritarias]
    feedback = sanitizar_feedback(feedback_bruto, temas_prioritarios, fontes_por_tema)

    if not feedback["resumo_geral"] and not feedback["areas_prioritarias"]:
        logger.warning("LLM retornou feedback vazio em /feedback | raw=%.200s", texto_nformatado)
        return JSONResponse(
            status_code=502,
            content={"erro": "Formato inválido gerado pela IA"}
        )

    return {
        "feedback": feedback,
        "uso_tokens": montar_uso_tokens(response.usage_metadata),
    }
