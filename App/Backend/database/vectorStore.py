from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
from rag.chunkGenerate import ChunkGenerate
from embedding.embedGenerate import EmbedGenerate

load_dotenv()

class VectorStoreMongo:
    def __init__(self):
        self.mongo_client = MongoClient(os.getenv("MONGO_ADDRESS"), server_api=ServerApi('1'))
        self.db_access = self.mongo_client[os.getenv("MONGO_DB")]
        self.collection_access = self.db_access[os.getenv("MONGO_COLLECTION")]
        
        self.embedding = EmbedGenerate()
        self.chunking = ChunkGenerate()

    def insert_several(self):
        chunk_collection = self.chunking.create_static_chunk()
        embed_collection = self.embedding.embed_text()

        for file_name, text in chunk_collection.items():

            documentos = [{
                'vector': embed_collection[file_name][i],
                'chunk': chunk_collection[file_name][i],
                'file_name': file_name}
                for i in range(len(text))]
            
            self.collection_access.insert_many(documentos)

    def search_vector(self, query_vector, limit=8):
        pipeline = [
            {
                "$vectorSearch": {
                    "queryVector": query_vector,
                    "path": "vector",
                    "numCandidates": 15,
                    "limit": limit,
                    "index": "vector-search-index"
                }
            },
            {"$project": {"_id": 0, "chunk": 1, "score": {"$meta": "vectorSearchScore"}}}
        ]
        resultados = list(self.collection_access.aggregate(pipeline))
        textos_encontrados = [doc.get("chunk", "") for doc in resultados]
        return textos_encontrados
    

A = VectorStoreMongo()

test = A.insert_several()

print("Dados inseridos!!")