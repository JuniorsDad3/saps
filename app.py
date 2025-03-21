# app.py
from flask import Flask, render_template, request, jsonify, redirect, session, url_for, send_file, send_from_directory, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
import os, uuid, logging, gc
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename  
import bcrypt
import pyodbc
import shutil
import openai
import nltk
import base64
import hashlib
# Import our db from extensions
from extensions import db
# Load models (make sure models.py is in the same directory)
from models import User, Case, Document, CertifiedDocument


# Load environment variables
load_dotenv()

app = Flask(__name__)

# App Configurations
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['SIGNATURE_FILE'] = 'static/download.png'  # Your stamp/logo image
app.config['DOWNLOAD_FOLDER'] = 'static/downloads'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"implicit_returning": False}
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

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
from flask_babel import Babel
babel = Babel(app)

# OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# Azure Speech-to-Text configuration
speech_key = os.getenv('AZURE_SPEECH_KEY')
speech_region = os.getenv('AZURE_REGION')

# Database, Migrate, Mail, and Celery setup
db.init_app(app)
migrate = Migrate(app, db)
mail = Mail(app)
from celery import Celery
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"

# Set port from environment or default
port = int(os.environ.get("PORT", 30000))

# Download required NLTK data
nltk.download('vader_lexicon')
from nltk.sentiment import SentimentIntensityAnalyzer
sia = SentimentIntensityAnalyzer()

# Transformers pipelines
from transformers import pipeline
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
translator_pipeline = pipeline("translation_en_to_fr", model="Helsinki-NLP/opus-mt-en-fr")

# Utility Functions
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'mp4', 'mp3', 'wav', 'pdf', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_reference_number():
    return f"CASE-{uuid.uuid4().hex[:6].upper()}"

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(input_password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(input_password.encode('utf-8'), stored_hash.encode('utf-8'))

def get_image(case):
    if case.picture:
        return f"data:image/jpeg;base64,{base64.b64encode(case.picture).decode('utf-8')}"
    return None

def certify_document(file_path, signature_file):
    """
    Applies a certification stamp (signature/logo) to a document.

    :param file_path: Path of the uploaded document
    :param signature_file: Path to the stamp/signature image
    :return: Path to the certified document
    """
    try:
        from PIL import Image, ImageDraw
        document = Image.open(file_path).convert("RGBA")
        draw = ImageDraw.Draw(document)

        signature = Image.open(signature_file).convert("RGBA")
        signature = signature.resize((150, 75))  

        doc_width, doc_height = document.size
        sig_width, sig_height = signature.size
        position = (doc_width - sig_width - 20, doc_height - sig_height - 20)

        document.paste(signature, position, signature)

        download_folder = app.config['DOWNLOAD_FOLDER']
        os.makedirs(download_folder, exist_ok=True)

        certified_path = os.path.join(download_folder, os.path.basename(file_path))
        document.save(certified_path, format="PNG")

        return certified_path

    except Exception as e:
        logging.error(f"Certification failed: {e}")
        return None

# Email functions
def send_confirmation_email(case):
    try:
        msg = Message(
            subject="Case Submission Confirmation",
            sender=app.config['MAIL_USERNAME'],
            recipients=[case.email]
        )
        msg.body = f"""Dear {case.first_name} {case.surname},

Your case has been successfully submitted!
Reference Number: {case.case_number}

Thank you for using SAPS Digital Services.
"""
        mail.send(msg)
        logging.info(f"Confirmation email sent to {case.email}")
    except Exception as e:
        logging.error(f"Error sending confirmation email: {str(e)}")

@celery.task
def send_async_email(msg):
    with app.app_context():
        mail.send(msg)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) if user_id else None

# Routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user, remember=True)
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
    from flask import session
    if lang in ['en', 'af', 'zu']:  # adjust to your supported languages
        session['language'] = lang
    return redirect(url_for('index'))

@app.route('/submit_case', methods=['GET', 'POST'])
def submit_case():
    if request.method == 'POST':
        try:
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

            required_fields = ['first_name', 'surname', 'id_number', 'cell_number', 'email',
                               'street_number', 'street_name', 'suburb', 'province', 'postal_code',
                               'crime_type', 'description']
            if not all(form_data.get(field) for field in required_fields):
                flash("Missing required fields", "error")
                return render_template('submit_case.html'), 400

            # Check for authenticated user
            customer_id = current_user.id if current_user.is_authenticated else None
            if customer_id is None:
                flash("You must be logged in to submit a case.", "error")
                return redirect(url_for('login'))  # Redirect to login if not authenticated

            voice_note_data = None
            if form_data['audio_file'] and allowed_file(form_data['audio_file'].filename):
                voice_note_data = form_data['audio_file'].read()

            case_number = generate_reference_number()

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
                submitted_at=datetime.now(),
                is_live=False,
                status="Open",
                assigned_user_id=None,
                customer_id=customer_id,  # ✅ FIXED: Added customer_id
                voice_note=voice_note_data,
                picture=None
            )

            db.session.add(new_case)
            db.session.commit()  # Flush is not needed; commit is enough.

            for file in form_data['evidence_files']:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    # Optionally, create a Document or CertifiedDocument record here

            send_confirmation_email(new_case)
            flash("Case submitted successfully!", "success")
            return redirect(url_for('case_confirmation', ref=case_number))
        except Exception as e:
            logging.error(f"Case submission error: {e}")
            db.session.rollback()
            flash("An error occurred while submitting your case.", "error")
            return redirect(url_for('submit_case'))
    return render_template('submit_case.html')

@app.route('/case_confirmation/<ref>')
def case_confirmation(ref):
    case = Case.query.filter_by(case_number=ref).first_or_404()
    return render_template('case_confirmation.html', case=case)

@app.route('/upload-certification', methods=['POST'])
@login_required
def upload_certification():
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

        # Apply certification stamp

        certified_file_path = certify_document(file_path, app.config['SIGNATURE_FILE'])

        if not certified_file_path:
            flash("Failed to certify document.", "danger")
            return redirect(url_for('certification'))

        flash("Document certified successfully!", "success")
        return redirect(url_for('certification_download', filename=os.path.basename(certified_file_path)))

    flash("Invalid file format.", "danger")
    return redirect(url_for('certification'))


@app.route('/certification', methods=['GET', 'POST'])
@login_required
def certification():
    documents = CertifiedDocument.query.all()
    return render_template('certification.html', documents=documents)

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    app.logger.info(f"Current user: {current_user}")
    search_ref = request.args.get('search_ref')
    if search_ref:
        cases = Case.query.filter_by(case_number=search_ref).all()
    else:
        cases = Case.query.order_by(Case.submitted_at.desc()).all()
    return render_template('admin_dashboard.html', cases=cases, user=current_user)

@app.route('/certification-download/<filename>')
def certification_download(filename):
    try:
        certified_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        if not os.path.exists(certified_file_path):
            flash("File not found.", "danger")
            return redirect(url_for('certification'))
        return send_file(certified_file_path, as_attachment=True)
    except Exception as e:
        logging.error(f"Error downloading certified document: {e}")
        flash("An error occurred while downloading the file.", "danger")
        return render_template('certification_download.html', document_filename=filename)

@app.route('/certify-document', methods=['POST'])
@login_required
def certify_document_route():
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

        # Apply certification stamp
        certified_file_path = certify_document(file_path, app.config['SIGNATURE_FILE'])

        if not certified_file_path:
            flash("Failed to certify document.", "danger")
            return redirect(url_for('certification'))

        flash("Document certified successfully!", "success")
        return redirect(url_for('certification_download', filename=os.path.basename(certified_file_path)))

    flash("Invalid file format.", "danger")
    return redirect(url_for('certification'))

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

@app.route('/case_details/<int:case_id>')
@login_required
def case_details(case_id):
    case = Case.query.get_or_404(case_id)
    return render_template('case_details.html', case=case)


@app.context_processor
def inject_navbar():
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    navbar_html = f"""
    <nav class='navbar navbar-expand-lg navbar-dark bg-primary'>
        <a class='navbar-brand' href='/'><img src='{url_for('static', filename='favicon.png')}' alt='Logo' style='height:40px;'> SAPS Digital Services</a>
        <button class='navbar-toggler' type='button' data-toggle='collapse' data-target='#navbarNav'>
            <span class='navbar-toggler-icon'></span>
        </button>
        <div class='collapse navbar-collapse' id='navbarNav'>
            <ul class='navbar-nav'>
                <li class='nav-item'><a class='nav-link' href='/'>Home</a></li>
                {("<li class='nav-item'><a class='nav-link' href='/admin_dashboard'>Dashboard</a></li><li class='nav-item'><a class='nav-link' href='/logout'>Logout</a></li>" if user else "<li class='nav-item'><a class='nav-link' href='/login'>Login</a></li>")}
            </ul>
        </div>
    </nav>
    """
    return dict(navbar_html=navbar_html)

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
    gc.collect()
    print(f"Starting app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
