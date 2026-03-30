import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Backend.engine.ragGenerate import RagGenerate
from Backend.config.instructions import Instructions
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

class MenuBackend():
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self.client.chats.create
        self.chat = self.client.chats.create(model="gemma-3-27b-it", 
                                             config= types.GenerateContentConfig(
                                                 temperature=0.1,
                                                 top_p=1,
                                                 max_output_tokens=1000,
                                                 top_k=20))
        self.recovery = RagGenerate()
        self.instructions = Instructions()

    def get_menu(self):
        while True:
            print("\n*****Seja bem vindo!!*****")
            print("\nEscolha uma das seguintes opções para continuar: ")
            opt = input("""\n01 - Iniciar uma conversa com o tutor
                        \n02 - Solicitar a criação de uma lista de exercícios
                        \n03 - Iniciar conversa sem utilizar o RAG
                        \n04 - Sair\n""")
            match opt:
                case "01" | "1":
                    self.talk_with_tutor("1")
                    break

                case "02" | "2":
                    self.talk_with_tutor("2")
                    break

                case "03" | "3":
                    self.talk_with_tutor("3")
                    break

                case "04" | "4":
                    print("\nAté breve!!")
                    break
                
                case _:
                    print("\nOpção não encontrada, tente novamente")

    def talk_with_tutor(self, opt):
        persona = self.instructions.get_instructions("01")

        if opt == "1":
            instruction = self.instructions.get_instructions("01")
            print("\n*****Hora de falar com o tutor, diga quais são suas dúvidas aqui e se quiser sair é digitar ""sair"" a qualquer momento*****")
        
        if opt == "2":
            instruction = self.instructions.get_instructions("02")
            print("\n*****Hora de praticar com o tutor, descreva que tipo de exercícios quer exercitar e se quiser sair é digitar ""sair"" a qualquer momento*****")
        
        if opt == "3":
            instruction = self.instructions.get_instructions("01")
            print("\n*****Hora de falar com o tutor sobre temas específicos, diga quais são suas dúvidas aqui e se quiser sair é digitar ""sair"" a qualquer momento*****")
        
        i = 0

        while True:
            print("\n[User]: ")
            question = input()

            if question == "voltar":
                self.get_menu()
                break

            if opt != "3":

                relevant_docs = self.recovery.compair_vector(question)

                context_text = ""
                if 'documents' in relevant_docs and relevant_docs['documents']:
                    for doc_list in relevant_docs['documents']:
                        for doc in doc_list:
                            context_text += f"{doc}\n\n"

                full_prompt = f"""{persona}
                    {instruction}
                    Responda com base nas seguintes informações:
                    {context_text} 
                    Se as informações não tiverem relação com a pergunta a seguir, desconsidere o uso delas.
                    Pergunta: {question}
                    """
                
                response = self.chat.send_message(full_prompt)

                print(f"\n[Tutor]:\n{response.text}")


                print("***********************************")
                print(f"\nContexto Extraido: {context_text}")
                
                i += 2

            else:
                full_prompt = f"""{persona}
                    {instruction}
                    Pergunta: {question}
                    """
                
                response = self.chat.send_message(full_prompt)

                print(f"\n[Tutor]:\n{response.text}")
                i += 2

A = MenuBackend()

A.get_menu()