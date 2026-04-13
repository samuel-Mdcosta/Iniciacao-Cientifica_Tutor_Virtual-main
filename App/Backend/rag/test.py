from chunkGenerate import ChunkGenerate

A = ChunkGenerate()

chunks = A.create_static_chunk_dict()

for chave, valor in chunks.items():
    print(f"Chave -> {chave}")
    print(f"Tamanho -> {len(valor)}")
    for i in range(len(valor)):
        print(f"Frase -> {valor[i]}")
    print("*******************")