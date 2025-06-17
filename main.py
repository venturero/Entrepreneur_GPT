#mainpy
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from openai import OpenAI
from werkzeug.utils import secure_filename
import datetime
import json
import PyPDF2
import pandas as pd
from PIL import Image
import pytesseract
import logging
import socket
from pathlib import Path
from flask_cors import CORS
from file_qa import FileQA
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
#from langchain_core.pydantic_v1 import Field
from langchain_openai import OpenAIEmbeddings, ChatOpenAI


BASE_DIR = Path(__file__).resolve().parent

LOGS_DIR = BASE_DIR / 'logs'
UPLOADS_DIR = BASE_DIR / 'uploads'
LOGS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

def setup_logging():
    logging.basicConfig(level=logging.INFO)
    
    chat_handler = logging.FileHandler(LOGS_DIR / 'chat_logs.log')
    chat_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    action_handler = logging.FileHandler(LOGS_DIR / 'action_logs.log')
    action_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    logger = logging.getLogger()
    logger.addHandler(chat_handler)
    logger.addHandler(action_handler)

ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE)

app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSIONS = {'pdf', 'csv'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size

app.config['UPLOAD_FOLDER'] = str(UPLOADS_DIR)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

print("Initializing OpenAI client...")
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
print("OpenAI client initialized successfully")

file_qa = FileQA()
print("FileQA initialized successfully")

# Data model for question grading
class QuestionGrade(BaseModel):
    """Binary score for relevance check on questions."""
    is_entrepreneurship: str = Field(
        description="Question is related to entrepreneurship, 'yes' or 'no'"
    )

# Initialize question grader
llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
structured_llm_grader = llm.with_structured_output(QuestionGrade)

# Prompt for question grading
system = """You are a grader assessing if a question is related to entrepreneurship. 
The question should be about business, startups, funding, product development, market analysis, 
team building, growth strategies, or other entrepreneurship-related topics.
Give a binary score 'yes' or 'no' to indicate whether the question is related to entrepreneurship.
If the question is about general knowledge, personal advice, or other non-business topics, grade it as 'no'."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "User question: {question}"),
    ]
)

question_grader = grade_prompt | structured_llm_grader

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text() + '\n'
            return text
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {str(e)}")
        return None

def extract_text_from_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        logging.error(f"Error extracting text from image: {str(e)}")
        return None

def read_text_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Error reading text file: {str(e)}")
        return None

def extract_file_content(file_path):
    file_extension = file_path.lower().split('.')[-1]
    
    if file_extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension in ['png', 'jpg', 'jpeg', 'gif']:
        return extract_text_from_image(file_path)
    elif file_extension == 'txt':
        return read_text_file(file_path)
    return None

# Chat history file path
CHAT_HISTORY_FILE = LOGS_DIR / 'chat_history.json'

def save_chat_history(chat_data):
    try:
        with open(CHAT_HISTORY_FILE, 'w') as f:
            json.dump(chat_data, f)
    except Exception as e:
        logging.error(f"Error saving chat history: {str(e)}")

def load_chat_history():
    try:
        with open(CHAT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logging.error(f"Error loading chat history: {str(e)}")
        return []

def log_chat(message, response, files=None):
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'user_message': message,
        'assistant_response': response,
        'files': [f.filename for f in files] if files else []
    }
    logging.info(json.dumps(log_entry))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    
    try:
        grade = question_grader.invoke({"question": message})
        
        if grade.is_entrepreneurship.lower() != 'yes':
            return jsonify({"response": "I am a chatbot only for entrepreneurship. I can't answer other topics."})
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a very helpful assistant. You need to reply ONLY to questions related to entrepreneurship. You MUST NOT reply to other topics. You can use the already uploaded documents for your responses. Use a tone similar to that of Y Combinator. Imagine someone is speaking with you during Y Combinator VC's office hours and asking for advice. Respond like a YC Partner advising YC founders."},
                {"role": "user", "content": message}
            ]
        )
        return jsonify({"response": response.choices[0].message.content})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF and CSV files are supported"}), 400
    
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        print("Processing file...")
        if filename.lower().endswith('.pdf'):
            file_qa.process_pdf(file_path)
        elif filename.lower().endswith('.csv'): 
            file_qa.process_csv(file_path)
        print("File processed finished")
        
        os.remove(file_path)
        
        return jsonify({"message": "File processed successfully"})
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/clear-file', methods=['POST'])
def clear_file():
    """Clear the currently processed file."""
    try:
        file_qa.clear()
        return jsonify({"message": "File cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data.get('question')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    try:
        print("Getting answer for question...")
        answer = file_qa.get_answer(question)
        print("Answer generated successfully")
        return jsonify({"response": answer})
    except Exception as e:
        print(f"Error getting answer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/check-file', methods=['GET'])
def check_file():
    """Check if a file has been processed."""
    try:
        has_file = file_qa.vectorstore is not None
        return jsonify({"has_file": has_file})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    # Setup logging
    setup_logging()
    
    port = 5000
    local_ip = get_ip()
    
    # Only print the startup message in the main process
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("""
        ╔════════════════════════════════════════════╗
        ║            EntrepreneurGPT Clone Server            ║
        ╚════════════════════════════════════════════╝
        """)
        print(f"""
        🚀 Server is running!
        
        💻 Local URL:     http://localhost:{port}
        🌐 Network URL:   http://{local_ip}:{port}
        
        📁 Upload folder: {UPLOADS_DIR.absolute()}
        📝 Log files:     {LOGS_DIR.absolute()}
        
        ⌛ Waiting for requests...
        
        Press Ctrl+C to quit.
        """)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
