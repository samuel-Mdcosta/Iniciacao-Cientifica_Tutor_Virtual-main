from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.chunkGenerate import ChunkGenerate
from embedding.embedGenerate import EmbedGenerate

load_dotenv()

_mongo_client = None

def _get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(os.getenv("MONGO_ADDRESS"), server_api=ServerApi('1'))
    return _mongo_client

class VectorStoreMongo:
    def __init__(self):
        client = _get_mongo_client()
        self.db_access = client[os.getenv("MONGO_DB")]
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
                    "numCandidates": 150,
                    "limit": limit,
                    "index": "vector-search-index"
                }
            },
            {"$project": {"_id": 0, "chunk": 1, "score": {"$meta": "vectorSearchScore"}}}
        ]
        resultados = list(self.collection_access.aggregate(pipeline))
        textos_encontrados = [doc.get("chunk", "") for doc in resultados]
        return textos_encontrados