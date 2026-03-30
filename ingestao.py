import sys
import os
# Adicionando o caminho raiz para evitar problemas de importação
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from App.Backend.database.vectorStore import VectorStoreMongo

def popular_banco():
    print("Iniciando o processo de Ingestão de Dados...")
    
    banco = VectorStoreMongo()
    
    print("Lendo o PDF, criando os chunks e gerando os embeddings (isso pode demorar um pouco)...")
    banco.insert_several()
    
    print("Os chunks e vetores estão salvos")

if __name__ == "__main__":
    popular_banco()