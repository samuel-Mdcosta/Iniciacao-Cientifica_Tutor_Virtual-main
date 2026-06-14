from google import genai
from google.genai import types
from pydantic import BaseModel
from App.Backend.config.instructions import Instructions
import os
import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from App.Backend.engine.ragGenerate import RagGenerate

load_dotenv()


def montar_uso_tokens(usage):
    """Extrai a contagem real de tokens; usage pode ser None em respostas bloqueadas."""
    return {
        "entrada": usage.prompt_token_count if usage else None,
        "saida": usage.candidates_token_count if usage else None,
        "total": usage.total_token_count if usage else None,
    }

class RequisicaoQuizz(BaseModel):
    texto: str

class RequisicaoLlm(BaseModel):
    texto: str

MODEL = "gemini-flash-lite-latest"
GENERATE_CONFIG = types.GenerateContentConfig(temperature=0.1, max_output_tokens=2048)

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
    
    relevant_docs = sistema_tutor.recovery.compair_vector(req.texto)
    
    context_text = ""
    if 'documents' in relevant_docs and relevant_docs['documents']:
        for doc in relevant_docs['documents']:
            context_text += f"[Fonte: {doc['file_name']}]\n{doc['chunk']}\n\n"

    full_prompt = f"""{instrucao_quiz.format(CONTEXT=context_text)}
    Tema solicitado: {req.texto}
    """
    
    json_response = sistema_tutor.client.models.generate_content(
        model=MODEL, contents=full_prompt, config=GENERATE_CONFIG
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
    except json.JSONDecodeError:
        quizz_estruturado = {"erro": "Formato inválido gerado pela IA", "texto_nformatado": texto_nformatado}

    return {
        "tema": req.texto,
        "quizz_gerado_llm": quizz_estruturado,
        "uso_tokens": montar_uso_tokens(json_response.usage_metadata),
    }

@app.post("/llm")
async def llm_response(req: RequisicaoLlm):
    response_prompt = sistema_tutor.instructions.get_instructions("01")
    relevant_docs = sistema_tutor.recovery.compair_vector(req.texto)
    context_text = ""
    if 'documents' in relevant_docs and relevant_docs['documents']:
        for doc in relevant_docs['documents']:
            context_text += f"[Fonte: {doc['file_name']}]\n{doc['chunk']}\n\n"

    full_prompt = f"""{response_prompt.format(CONTEXT=context_text)}

        Pergunta do aluno: {req.texto}
        """
        
    response = sistema_tutor.client.models.generate_content(
        model=MODEL, contents=full_prompt, config=GENERATE_CONFIG
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
    except json.JSONDecodeError:
        resposta_estruturada = {"erro": "Formato inválido gerado pela IA", "texto_nformatado": texto_nformatado}

    return {
        "pergunta": req.texto,
        "resposta_tutor": resposta_estruturada,
        "documentos_utilizados": relevant_docs,
        "uso_tokens": montar_uso_tokens(response.usage_metadata),
    }
