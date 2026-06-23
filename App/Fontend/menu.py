import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from Backend.config.instructions import Instructions
from Backend.engine.ragGenerate import RagGenerate

load_dotenv()

class Menu():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-flash-lite-latest"
        self.instructions = Instructions()
        self.recovery = RagGenerate()

    def post_message_rag(self, question):
        relevant_docs = self.recovery.compare_vector(question)

        context_text = ""
        if 'documents' in relevant_docs and relevant_docs['documents']:
            for doc in relevant_docs['documents']:
                context_text += f"{doc['chunk']}\n\n"

        if not context_text:
            return "Não foi possível responder sua pergunta, pois não há contexto na base de dados."

        full_prompt = f"""
            Responda com base nas seguintes informações:
            {context_text}
            Se as informações não tiverem relação com a pergunta a seguir, desconsidere o uso delas.
            Pergunta: {question}
            """

        response = self.client.models.generate_content(
            model=self.model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                system_instruction=self.instructions.get_instructions("01"),
            ),
        )
        return response.text
