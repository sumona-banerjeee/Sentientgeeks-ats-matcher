import fitz  # PyMuPDF
import os

class PDFProcessor:
    def __init__(self):
        pass
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        # Extract text from PDF file using PyMuPDF
        try:
            doc = fitz.open(file_path)
            text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
            
            doc.close()
            return text.strip()
        
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def is_valid_pdf(self, file_path: str) -> bool:
        # Check if the file is a valid PDF
        try:
            doc = fitz.open(file_path)
            doc.close()
            return True
        except:
            return False
