from flask import Flask, render_template, request, jsonify, redirect, session, url_for, send_file, send_from_directory,  flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_migrate import Migrate
from flask_mail import Mail, Message
from azure.storage.blob import BlobServiceClient
from reportlab.pdfgen import canvas
from flask_babel import Babel
from flask_babel import gettext as _
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
from datetime import datetime
import logging
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
from celery import Celery
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from transformers import pipeline
from nltk.sentiment import SentimentIntensityAnalyzer
from translations import get_translation, get_translations, LANGUAGES 
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from deep_translator import GoogleTranslator
from textblob import TextBlob 
import cursor
from transformers import pipeline
import numpy as np
import openai
import nltk
import base64
import bcrypt
import pyodbc
import hashlib
import shutil


# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)

# App Configurations
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SIGNATURE_FILE'] = 'static/download.png'  # Update this to your stamp/logo image
app.config['DOWNLOAD_FOLDER'] = 'static/downloads'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'

# Additional security & limits
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    MAX_CONTENT_LENGTH=1024 * 1024 * 1024  # 1GB
)

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Babel setup for multilingual support
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
babel = Babel(app)

# OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# Azure Speech-to-Text configuration
speech_key = os.getenv('AZURE_SPEECH_KEY')
speech_region = os.getenv('AZURE_REGION')

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)
babel = Babel(app)
from celery import Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)  # Bind LoginManager to your app
login_manager.login_view = "login"  # Define the login route

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

nltk.download('vader_lexicon')
from nltk.sentiment import SentimentIntensityAnalyzer
sia = SentimentIntensityAnalyzer()
from transformers import pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
translator = pipeline("translation_en_to_fr", model="Helsinki-NLP/opus-mt-en-fr")


# Models
from models import User, Case, Document

# Utility functions
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'mp4', 'mp3', 'wav', 'pdf', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def validate_file_size(file):
    max_size = 1024 
    if file.content_length > max_size:
        return False
    return True

def generate_reference_number():
    return f"CASE-{uuid.uuid4().hex[:6].upper()}"

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(input_password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hash.encode('utf-8'))

# Example Usage
new_password = "admin123"
hashed_password = hash_password(new_password)
print(f"Hashed Password: {hashed_password}")

# Verify password
is_valid = verify_password("admin123", hashed_password)
print(f"Password Valid: {is_valid}")


def get_image(case):
    if case.picture:
        return f"data:image/jpeg;base64,{base64.b64encode(case.picture).decode('utf-8')}"
    return None

def upload_to_blob(file_path, file_name):
    try:
        blob_service = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)
        blob_client = blob_service.get_blob_client(container=BLOB_CONTAINER_NAME, blob=file_name)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        return blob_client.url
    except Exception as e:
        logging.error(f"Error uploading to blob: {e}")
        return None

def voice_to_text(file_path, language='en-US'):
    try:
        speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
        audio_input = speechsdk.AudioConfig(filename=file_path)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
        result = speech_recognizer.recognize_once_async().get()
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        return "Speech not recognized"
    except Exception as e:
        logging.error(f"Error in voice-to-text conversion: {e}")
        return None

print(get_translation('en', 'title'))  # SAPS Digital Services
print(get_translation('af', 'title'))  # SAPS Digitale Dienste
print(get_translation('zu', 'title'))  # Izinsiza ze-SAPS eziku-inthanethi

def generate_case_summary(description):
    try:
        summary = summarizer(description, max_length=130, min_length=30, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        logging.error(f"Error generating case summary: {e}")
        return description[:100] + "..."  # Fallback to first 100 characters

def analyze_sentiment(description):
    try:
        sentiment = sia.polarity_scores(description)
        return sentiment['compound']  # Returns a score between -1 (negative) and 1 (positive)
    except Exception as e:
        logging.error(f"Error analyzing sentiment: {e}")
        return 0  # Neutral sentiment as fallback

def analyze_case_description(text):
    analysis = TextBlob(text)
    return {
        'sentiment': analysis.sentiment.polarity,
        'urgency': 'high' if analysis.sentiment.polarity < -0.5 else 'medium'
    }

def translate_text(text, dest_lang='fr'):
    try:
        translation = GoogleTranslator(source='auto', target=dest_lang).translate(text)
        return translation
        translation = translator(text, src_lang='en', tgt_lang=dest_lang)
        return translation[0]['translation_text']
    except Exception as e:
        logging.error(f"Error translating text: {e}")
        return text  # Fallback to original text

def prioritize_case(case):
    # Example prioritization logic (can be replaced with a trained ML model)
    if case.crime_type in ['assault', 'burglary']:
        return 'High'
    elif case.crime_type in ['fraud', 'theft']:
        return 'Medium'
    else:
        return 'Low'

def generate_crime_report(case):
    try:
        report = f"""
        Case Report:
        - Reference Number: {case.reference_number}
        - Name: {case.name} {case.surname}
        - Crime Type: {case.crime_type}
        - Description: {case.description}
        - Sentiment: {'Positive' if analyze_sentiment(case.description) > 0 else 'Negative'}
        - Priority: {prioritize_case(case)}
        """
        return report
    except Exception as e:
        logging.error(f"Error generating crime report: {e}")
        return "Failed to generate report."

def detect_anomalies(cases):
    try:
        # Example anomaly detection logic (can be replaced with a trained ML model)
        crime_counts = {}
        for case in cases:
            crime_counts[case.crime_type] = crime_counts.get(case.crime_type, 0) + 1
        anomalies = [crime for crime, count in crime_counts.items() if count > 5]  # Threshold for anomalies
        return anomalies
    except Exception as e:
        logging.error(f"Error detecting anomalies: {e}")
        return []

def predict_crime_risk(location_data):
    # Implement ML model here (sample dummy function)
    from sklearn.externals import joblib
    model = joblib.load('crime_prediction_model.pkl')
    return model.predict([location_data])[0]

@celery.task
def send_async_email(msg):
    with app.app_context():
        mail.send(msg)

def send_status_notification(self):
    try:
        msg = Message("Case Status Update", sender=app.config['MAIL_USERNAME'], recipients=[self.email])
        msg.body = f"Your case ({self.reference_number}) status has been updated to {self.case_state}."
        send_async_email.delay(msg)
    except Exception as e:
        logging.error(f"Error sending email notification: {e}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def certify_document(file_path, signature_path):
    try:
        file_ext = file_path.rsplit('.', 1)[-1].lower()
        # Process only image files for now
        if file_ext in ['png', 'jpg', 'jpeg']:
            from PIL import Image
            img = Image.open(file_path)
            signature = Image.open(signature_path)
            # Resize signature to fit properly
            signature.thumbnail((150, 80))
            img.paste(signature, (img.width - 180, img.height - 100), signature)
            certified_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], os.path.basename(file_path))
            img.save(certified_file_path)
            return certified_file_path
        return None
    except Exception as e:
        logging.error(f"Error certifying document: {e}")
        return None

@celery.task
def send_async_email(msg):
    with app.app_context():
        mail.send(msg)

# Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Authenticate user
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user, remember=True)  # **Ensure user is logged in**
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
        else:
            flash('Login failed. Please check your credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) if user_id else None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password_hash=hashed)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/')
def index():
    # If a user is already logged in, redirect to the admin dashboard.
    # Otherwise, redirect to the login page.
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500

@app.route('/transcribe-audio', methods=['POST'])
def transcribe_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    from azure.cognitiveservices.speech import SpeechConfig, AudioConfig, SpeechRecognizer
    audio_file = request.files['audio']
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(audio_file.filename))
    audio_file.save(audio_path)
    speech_config = SpeechConfig(subscription=os.getenv('AZURE_SPEECH_KEY'), region=os.getenv('AZURE_REGION'))
    audio_input = AudioConfig(filename=audio_path)
    speech_recognizer = SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
    result = speech_recognizer.recognize_once_async().get()
    if result.reason == result.ResultReason.RecognizedSpeech:
        return jsonify({'transcription': result.text})
    else:
        return jsonify({'error': 'Speech not recognized'}), 400

@app.route('/set_language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['language'] = lang
    return redirect(url_for('index'))

@app.route('/submit_case', methods=['GET', 'POST'])
def submit_case():
    if request.method == 'POST':
        try:
            # Capture data from the form fields (matching your HTML input names)
            form_data = {
                'first_name': request.form.get('name'),
                'surname': request.form.get('surname'),
                'id_number': request.form.get('idNumber'),
                'cell_number': request.form.get('cellNumber'),
                'email': request.form.get('email'),
                'street_number': request.form.get('streetNumber'),
                'street_name': request.form.get('streetName'),
                'suburb': request.form.get('suburb'),
                'province': request.form.get('province'),
                'postal_code': request.form.get('postalCode'),
                'crime_type': request.form.get('incidentType'),
                'description': request.form.get('caseDescription'),
                'audio_file': request.files.get('audioFile'),
                'evidence_files': request.files.getlist('evidenceFiles')
            }
            
            # Validate required fields (adjust as needed)
            required_fields = ['first_name', 'surname', 'id_number', 'cell_number', 'email',
                               'street_number', 'street_name', 'suburb', 'province', 'postal_code',
                               'crime_type', 'description']
            if not all(form_data.get(field) for field in required_fields):
                flash("Missing required fields", "error")
                return render_template('submit_case.html'), 400

            # Process the audio file if provided
            voice_note_data = None
            if form_data['audio_file'] and allowed_file(form_data['audio_file'].filename):
                # You can either save the file and store the path or store the binary data
                voice_note_data = form_data['audio_file'].read()

            # Generate a unique case reference number
            case_number = generate_reference_number()

            # Create a new Case instance; update the model fields accordingly
            new_case = Case(
                case_number=case_number,
                first_name=form_data['first_name'],
                surname=form_data['surname'],
                id_number=form_data['id_number'],
                cell_number=form_data['cell_number'],
                email=form_data['email'],
                street_number=form_data['street_number'],
                street_name=form_data['street_name'],
                suburb=form_data['suburb'],
                province=form_data['province'],
                postal_code=form_data['postal_code'],
                crime_type=form_data['crime_type'],
                description=form_data['description'],
                submitted_at=datetime.datetime.utcnow(),
                status="Open",
                voice_note=voice_note_data
            )
            db.session.add(new_case)
            db.session.commit()

            # Process evidence files if provided
            for file in form_data['evidence_files']:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    # Optionally, create a Document or CertifiedDocument record here

            # Optionally, send a confirmation email
            send_confirmation_email(new_case)

            flash("Case submitted successfully!", "success")
            return redirect(url_for('case_confirmation', ref=new_case.case_number))
        except Exception as e:
            logging.error(f"Case submission error: {e}")
            db.session.rollback()
            flash("An error occurred while submitting your case.", "error")
            return render_template('500.html'), 500

    return render_template('submit_case.html')

@app.route('/case_confirmation/<ref>')
def case_confirmation(ref):
    # Query the case using the unique case number (reference)
    case = Case.query.filter_by(case_number=ref).first_or_404()
    return render_template('case_confirmation.html', case=case)

### Function to Send Confirmation Email ###
def send_confirmation_email(case):
    try:
        msg = Message(
            subject="Case Submission Confirmation",
            sender=app.config['MAIL_USERNAME'],
            recipients=[case.email]  # Assumes the Case model stores the submitter's email
        )
        msg.body = f"""Dear {case.first_name} {case.surname},

Your case has been submitted successfully!
Reference Number: {case.case_number}

Thank you for using SAPS Digital Services.
"""
        mail.send(msg)
    except Exception as e:
        logging.error(f"Error sending confirmation email: {e}")

@app.route('/certification', methods=['GET', 'POST'])
def certification():
    # Ensure the user is logged in (adjust according to your authentication system)
    if 'user_id' not in session or not current_user.is_authenticated:
        flash("Session expired, please log in again.", "warning")
        return redirect(url_for('login'))
    
    # Retrieve all certified documents (assuming a CertifiedDocument model exists)
    documents = CertifiedDocument.query.all()

    if request.method == 'POST':
        if 'documentFile' not in request.files:
            flash("No file provided.", "danger")
            return redirect(url_for('certification'))
        
        file = request.files['documentFile']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(url_for('certification'))

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # certify_document() should be a function that applies your certification stamp/logo
            certified_file_path = certify_document(file_path, app.config['SIGNATURE_FILE'])
            if not certified_file_path:
                flash("Failed to certify document.", "danger")
                return redirect(url_for('certification'))
            return redirect(url_for('certification_download', filename=os.path.basename(certified_file_path)))

    return render_template('certification.html', documents=documents)

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    app.logger.info(f"Current user: {current_user}")

    # Search functionality
    search_ref = request.args.get('search_ref')
    if search_ref:
        cases = Case.query.filter_by(case_number=search_ref).all()
    else:
        cases = Case.query.order_by(Case.submitted_at.desc()).all()

    return render_template('admin_dashboard.html', cases=cases, user=current_user)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/update-status/<int:case_id>', methods=['POST'])
@login_required
def update_status(case_id):
    if not current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    case = Case.query.get_or_404(case_id)
    case.status = request.form['status']
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/certification-download/<filename>')
def certification_download(filename):
    try:
        certified_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        print(f"Attempting to send file: {certified_file_path}")
        if not os.path.exists(certified_file_path):
            flash("File not found.", "danger")
            return redirect(url_for('certification'))
        return send_file(certified_file_path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading certified document: {e}")
        flash("An error occurred while downloading the file.", "danger")
        return redirect(url_for('certification'))


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

@app.context_processor
def inject_navbar():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(navbar_html=f"""
    <nav class='navbar navbar-expand-lg navbar-dark bg-primary'>
        <a class='navbar-brand' href='/'>
            <img src='{{{{ url_for('static', filename='favicon.png') }}}}' alt='Logo' style='height:40px;'>
            SAPS Digital Services
        </a>
        <button class='navbar-toggler' type='button' data-toggle='collapse' data-target='#navbarNav'>
            <span class='navbar-toggler-icon'></span>
        </button>
        <div class='collapse navbar-collapse' id='navbarNav'>
            <ul class='navbar-nav'>
                <li class='nav-item'><a class='nav-link' href='/'>Home</a></li>
                {f"<li class='nav-item'><a class='nav-link' href='/admin'>Dashboard</a></li><li class='nav-item'><a class='nav-link' href='/logout'>Logout</a></li>" if user else "<li class='nav-item'><a class='nav-link' href='/login'>Login</a></li>"}
            </ul>
        </div>
    </nav>
    """)

# Main entry point
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        default_user = User.query.filter_by(email='admin@example.com').first()
        if not default_user:
            from werkzeug.security import generate_password_hash
            default_user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256')
            )
            db.session.add(default_user)
            db.session.commit()
            print("Default user created!")
        else:
            print("Default user already exists!")
    app.run(debug=True)