from rag.extractorPDF import ExtractorPDF

class ChunkGenerate():
    def __init__(self):
        self.extractor = ExtractorPDF()
        self.chunk_static_size = 500
        self.overlap_static_size = 50
        self.overlap_dinamic_size = 10

    def create_static_chunk(self):
        text = self.extractor.extract_text_from_pdf()
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
        
        return chunks

    def create_dinamic_chunk(self):
            dict_files = self.extractor.extract_text_from_docs()
            dict_chunks = {}

            for key, value in dict_files.items():
                text = value
                
                chunks = []
                overlap = ""
                count = 0
                index_letter = 0
                index_start = 0
                index_overlap = 1
                
                while index_letter < len(text):
                    if text[index_letter] == ".":
                        chunk = text[index_start:index_letter + 1]
                        index_start = index_letter + 2
                        chunks.append(overlap + chunk)

                        while count < self.overlap_dinamic_size:
                            if index_overlap > len(chunk): 
                                break

                            if chunk[-index_overlap] in [" ", ","]:
                                count += 1
                            
                            if index_overlap == len(chunk):
                                break

                            index_overlap += 1

                        overlap = chunk[-index_overlap + 1:]
                        count = 1
                        index_overlap = 0

                    index_letter += 1

                dict_chunks[key] = chunks

            return dict_chunks
        