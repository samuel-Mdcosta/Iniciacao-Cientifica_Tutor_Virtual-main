import os

# main.py instancia o cliente Gemini e o Mongo ao ser importado; nos testes
# eles são substituídos por dublês, então bastam valores fictícios.
os.environ.setdefault("GEMINI_API_KEY", "chave-de-teste")
os.environ.setdefault("MONGO_ADDRESS", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "teste")
os.environ.setdefault("MONGO_COLLECTION", "teste")
