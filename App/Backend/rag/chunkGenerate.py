from rag.extractorPDF import ExtractorPDF

class ChunkGenerate():
    def __init__(self):
        self.extractor = ExtractorPDF()
        self.chunk_static_size = 1000
        self.overlap_static_size = 100

    def create_static_chunk(self):
        dict_files = self.extractor.extract_text_from_docs()
        dict_chunks = {}

        for key, value in dict_files.items():
            text = value   
            chunks = []
            start = 0
            text_length = len(text)

            while start < text_length:
                end = min(start + self.chunk_static_size, text_length)
                chunk = text[start:end]
                chunks.append(chunk)
                
                if end >= text_length:
                    break
                    
                start += self.chunk_static_size - self.overlap_static_size
                
                if self.overlap_static_size >= self.chunk_static_size:
                    start = end

            dict_chunks[key] = chunks

        return dict_chunks
    