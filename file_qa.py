import os
import io
from PyPDF2 import PdfReader
import pytesseract
from pdf2image import convert_from_bytes
from langchain_community.chat_models import ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
import pandas as pd

class FileQA:
    def __init__(self):
        self.vectorstore = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(temperature=0)

    def process_pdf(self, file_path):
        """Process a PDF file and create a vector store."""
        try:
            # Extract text from PDF
            text = ""
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            # If no text was extracted, try OCR
            if not text.strip():
                with open(file_path, 'rb') as pdf_file:
                    images = convert_from_bytes(pdf_file.read())
                    for image in images:
                        pytesseract.pytesseract.tesseract_cmd = r'C:\\Users\\rvent\\Desktop\\code\\tesseract.exe'
                        text += pytesseract.image_to_string(image)
            
            if not text.strip():
                raise ValueError("Could not extract any text from the PDF")
            
            # Split text into chunks
            texts = self.text_splitter.split_text(text)
            
            # Create vector store
            self.vectorstore = FAISS.from_texts(texts, self.embeddings)
            
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")

    def process_csv(self, file_path):
        """Process a CSV file and create a vector store."""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Convert DataFrame to text
            text = df.to_string()
            
            # Split text into chunks
            texts = self.text_splitter.split_text(text)
            
            # Create vector store
            self.vectorstore = FAISS.from_texts(texts, self.embeddings)
            
        except Exception as e:
            raise Exception(f"Error processing CSV: {str(e)}")

    def get_answer(self, question):
        """Get answer for a question based on the processed file."""
        if not self.vectorstore:
            return "Please upload a document first."
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever()
        )
        
        return qa_chain.run(question)

    def clear(self):
        """Clear the current vector store."""
        self.vectorstore = None 