#file qa
import os
import io
from PyPDF2 import PdfReader
import pytesseract
from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import pandas as pd
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.vectorstores import InMemoryVectorStore
from PIL import Image
import fitz  # PyMuPDF
from langchain.schema import Document, SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser


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
            # Extract text from PDF using PyPDF2
            text = ""
            with open(file_path, 'rb') as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            # If no text was extracted, try OCR using PyMuPDF
            if not text.strip():
                doc = fitz.open(file_path)
                for page in doc:
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    pytesseract.pytesseract.tesseract_cmd = r'C:\\YOUR_PATH\\tesseract.exe'
                    text += pytesseract.image_to_string(img)
                doc.close()
            
            if not text.strip():
                raise ValueError("Could not extract any text from the PDF")
            
            texts = self.text_splitter.split_text(text)
            
            self.vectorstore = FAISS.from_texts(texts, self.embeddings)
            
        except Exception as e:
            raise Exception(f"Error processing PDF: {str(e)}")

    def process_csv(self, file_path):
        """Process a CSV file and create a vector store."""
        try:
            df = pd.read_csv(file_path)
            text = df.to_string()
            
            chunks = self.text_splitter.split_text(text)
            documents = [Document(page_content=chunk) for chunk in chunks]
            self.vectorstore = InMemoryVectorStore.from_documents(documents, self.embeddings)
            return len(documents)
            
        except Exception as e:
            raise Exception(f"Error processing CSV: {str(e)}")

    def get_answer(self, question):
        """Get answer for a question based on the processed file."""
        if not self.vectorstore:
            return "Please upload a document first."
        
        try:
            relevant_docs = self.vectorstore.similarity_search(question, k=3)
            context_from_docs = "\n\n".join([doc.page_content for doc in relevant_docs])

            messages = [
                SystemMessage(
                    content=f"Use the following context to answer my question: {context_from_docs}"
                ),
                HumanMessage(content=question),
            ]
            parser = StrOutputParser()
            chain = self.llm | parser
            return chain.invoke(messages)
            
        except Exception as e:
            return f"Error processing question: {str(e)}"

    def clear(self):
        """Clear the current vector store."""
        self.vectorstore = None 