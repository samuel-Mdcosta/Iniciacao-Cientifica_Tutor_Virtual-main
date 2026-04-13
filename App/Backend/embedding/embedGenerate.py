import nomic
from nomic import embed
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
from rag.chunkGenerate import ChunkGenerate

load_dotenv()

class EmbedGenerate:
    def __init__(self):
        self.chunks = ChunkGenerate()
        nomic_key = os.getenv("NOMIC_API_KEY")
        if nomic_key:
            nomic.login(token=nomic_key)
        else:
            raise ValueError("A chave NOMIC_API_KEY não foi encontrada no arquivo .env!")
    
    def embed_text(self):
        dict_chunk = self.chunks.create_static_chunk()
        dict_embed = {}

        for key, value in dict_chunk.items():

            output = embed.text(
                texts=value,
                model='nomic-embed-text-v1.5',
                task_type='search_document'
            )['embeddings']

            dict_embed[key] = output

        return dict_embed
    
    def embed_query(self, query: str):
        output = embed.text(
            texts=[query],
            model='nomic-embed-text-v1.5',
            task_type='search_query'
        )['embeddings']
        return output
