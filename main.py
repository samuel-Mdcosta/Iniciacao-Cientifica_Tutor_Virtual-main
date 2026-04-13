from contextlib import asynccontextmanager
from google import genai
from google.genai import types
from pydantic import BaseModel
from App.Backend.config.instructions import Instructions
import os
import json
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from App.Backend.engine.ragGenerate import RagGenerate

load_dotenv()

class RequisicaoQuizz(BaseModel):
    texto: str

class RequisicaoLlm(BaseModel):
    texto: str

class Menu():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.chat = self.client.chats.create(
            model="gemma-3-27b-it", 
            config= types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2048,
            )
        )
        self.instructions = Instructions()
        self.recovery = RagGenerate()
        self.collection_name = "Chunk_Dinamic_NoOverlap"

sistema_tutor = Menu()

class MongoDb:
    def connect(self):
        addr = os.getenv("MONGO_ADDRESS")
        db_name = os.getenv("MONGO_DB")
        coll_name = os.getenv("MONGO_COLLECTION")
        self.mongo_client = MongoClient(addr, server_api=ServerApi('1'))
        self.db_access = self.mongo_client[db_name]
        self.collection_access = self.db_access[coll_name]

    def disconnect(self):
        if self.mongo_client:
            self.mongo_client.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_db = MongoDb()
    mongo_db.connect()
    app.state.db = mongo_db
    try:
        yield
    finally:
        mongo_db.disconnect()

def get_collection(request: Request):
    return request.app.state.db.collection_access

app = FastAPI(lifespan=lifespan)


@app.post("/quizz")
async def perguntas(req: RequisicaoQuizz):
    instrucao_quiz = sistema_tutor.instructions.get_instructions("02")
    
    relevant_docs = sistema_tutor.recovery.compair_vector(req.texto)
    
    context_text = ""
    if 'documents' in relevant_docs and relevant_docs['documents']:
        for doc_list in relevant_docs['documents']:
            for doc in doc_list:
                context_text += f"{doc}\n\n"

    full_prompt = f"""{instrucao_quiz}
    {instrucao_quiz}
    Responda com base nas seguintes informações:
    {context_text} 
    Tema solicitado: {req.texto}
    """
    
    json_response = sistema_tutor.chat.send_message(full_prompt)
    texto_nformatado = json_response.text
    texto_formatado = texto_nformatado.replace("```json", "").replace("```", "").strip()

    try:
        quizz_estruturado = json.loads(texto_formatado)
    except json.JSONDecodeError:
        quizz_estruturado = {"erro": "Formato inválido gerado pela IA", "texto_nformatado": texto_nformatado}

    return {
        "tema": req.texto,
        "quizz_gerado_llm": quizz_estruturado
    }

@app.post("/llm")
async def llm_response(req: RequisicaoLlm):
    response_prompt = sistema_tutor.instructions.get_instructions("01")
    relevant_docs = sistema_tutor.recovery.compair_vector(req.texto)
    context_text = ""
    if 'documents' in relevant_docs and relevant_docs['documents']:
        for doc_list in relevant_docs['documents']:
            for doc in doc_list:
                context_text += f"{doc}\n\n"

    full_prompt = f"""{response_prompt}
        
        Responda EXCLUSIVAMENTE com base nas seguintes informações do material didático:
        {context_text} 
        
        Pergunta do aluno: {req.texto}
        """
        
    response = sistema_tutor.chat.send_message(full_prompt)

    return {
        "pergunta": req.texto, 
        "resposta_tutor": response.text,
        "documentos_utilizados": relevant_docs
    }