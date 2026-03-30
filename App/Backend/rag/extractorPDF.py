import fitz
import os

class ExtractorPDF():
    def __init__(self):
        self.pdf_path = "files_test/Texto 01.pdf"
        self.pdf_file = fitz.open(self.pdf_path)

    def extract_text_from_pdf(self):
        text = ""

        for page in self.pdf_file:
            text += page.get_text("text")

            text = text.replace("\n", " ")
            text = " ".join(text.split())
            
        return text
    
    def extract_token_from_pdf(self):
        tokens = []
        initial_point = 0
        count = 0
        text = self.extract_text_from_pdf()

        for i in text:
            if i in [" ", "."]:
                token = text[initial_point:count + 1]
                initial_point = count + 1
                tokens.append(token)
            count += 1

        return tokens
    
    def extract_text_from_docs(self):    
        doc = "files"
        doc_files = [file for file in os.listdir(doc)]
        file_name = ""
        dict_files = {}

        for i in range(len(doc_files)):
            text = ""
            file_name = doc_files[i]
            for page in fitz.open("files/" + doc_files[i]):
                text += page.get_text("text")

                text = text.replace("\n", " ")
                text = " ".join(text.split())
            dict_files[file_name] = text

        return dict_files
