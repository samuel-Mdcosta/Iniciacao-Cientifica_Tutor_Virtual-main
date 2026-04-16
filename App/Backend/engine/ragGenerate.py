import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.vectorStore import VectorStoreMongo
from embedding.embedGenerate import EmbedGenerate

class RagGenerate():
    def __init__(self):
        self.vector_store = VectorStoreMongo()
        self.embed = EmbedGenerate()
    
    def compair_vector(self, question: str):
        query = self.embed.embed_query(question)
        query_vector = query[0]
        textos_similares = self.vector_store.search_vector(query_vector)
        
        return {"documents": textos_similares}
    