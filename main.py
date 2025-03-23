from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from openai import OpenAI
from werkzeug.utils import secure_filename
import datetime
import json
import PyPDF2
from PIL import Image
import pytesseract
import logging
import socket
from pathlib import Path

# Get the directory containing main.py
BASE_DIR = Path(__file__).resolve().parent

# Create necessary directories
LOGS_DIR = BASE_DIR / 'logs'
UPLOADS_DIR = BASE_DIR / 'uploads'
LOGS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Configure logging
def setup_logging():
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Chat logs handler
    chat_handler = logging.FileHandler(LOGS_DIR / 'chat_logs.log')
    chat_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    # Action logs handler
    action_handler = logging.FileHandler(LOGS_DIR / 'action_logs.log')
    action_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    
    # Get logger and add handlers
    logger = logging.getLogger()
    logger.addHandler(chat_handler)
    logger.addHandler(action_handler)

# Load API key from .env file
ENV_FILE = BASE_DIR / '.env'
load_dotenv(ENV_FILE)

# Initialize Flask app
app = Flask(__name__)

# App configurations
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size

app.config['UPLOAD_FOLDER'] = str(UPLOADS_DIR)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)

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
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        
        # Create chat completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": message}
            ]
        )

        # Extract the response
        ai_response = response.choices[0].message.content

        # Log the chat
        log_chat(message, ai_response, None)

        return jsonify({"response": ai_response})
    except Exception as e:
        error_message = str(e)
        logging.error(f"Error in chat endpoint: {error_message}")
        return jsonify({"error": error_message}), 500

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
        ║            ChatGPT Clone Server            ║
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
