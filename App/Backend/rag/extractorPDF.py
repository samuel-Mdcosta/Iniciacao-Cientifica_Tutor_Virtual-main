import fitz
import os

class ExtractorPDF():
    
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
