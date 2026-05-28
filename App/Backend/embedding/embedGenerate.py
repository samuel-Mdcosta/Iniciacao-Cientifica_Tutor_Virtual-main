from google import genai
from google.genai import types
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.chunkGenerate import ChunkGenerate

load_dotenv()

class EmbedGenerate:
    def __init__(self):
        self.chunks = ChunkGenerate()
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    def embed_text(self):
        dict_chunk = self.chunks.create_static_chunk()
        dict_embed = {}

        for key, value in dict_chunk.items():
            lista_de_vetores = []
            
            for chunk in value:
                output = self.client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=chunk,
                    config=types.EmbedContentConfig(output_dimensionality=3072)
                )
                
                lista_de_vetores.append(output.embeddings[0].values)
                
            dict_embed[key] = lista_de_vetores
            
        return dict_embed
    
    def embed_query(self, query: str):
        output = self.client.models.embed_content(
            model="gemini-embedding-2",
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=3072)
            )
        
        [embedding_obj] = output.embeddings

        return embedding_obj.values
