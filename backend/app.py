import os
import re
import json
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import pytesseract
from PIL import Image
from flask_migrate import Migrate

# Load environment variables from .env file
load_dotenv()

# Initialize Flask App
app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')

# --- App Configuration ---
# Secret key for session management
app.config['SECRET_KEY'] = 'your-very-secret-key-for-production'
# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Configuration ---
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db = SQLAlchemy(app)

# Add this line
migrate = Migrate(app, db)

# --- Database Model ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(10), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    id_type = db.Column(db.String(10), nullable=False) # AADHAR or PAN
    id_number_input = db.Column(db.String(20), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False)
    # OCR Extracted Data
    ocr_extracted_text = db.Column(db.Text, nullable=True)
    ocr_extracted_name = db.Column(db.String(150), nullable=True)
    ocr_extracted_dob = db.Column(db.String(20), nullable=True)
    ocr_extracted_id_number = db.Column(db.String(20), nullable=True)
    # Verification Status
    name_verified = db.Column(db.Boolean, default=False)
    dob_verified = db.Column(db.Boolean, default=False)
    id_verified = db.Column(db.Boolean, default=False)
    registration_timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.full_name}>'

# --- OCR and Verification Logic ---
def perform_ocr(image_path):
    """Performs OCR on an image and extracts text."""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"Error during OCR: {e}")
        return ""

def extract_details_from_text(text, id_type):
    """Uses regex to find Name, DOB, and ID numbers from OCR text."""
    details = {
        'name': None,
        'dob': None,
        'id_number': None
    }
    
    # Regex for Aadhaar (12 digits, can have spaces)
    aadhaar_regex = r'\b\d{4}\s?\d{4}\s?\d{4}\b'
    # Regex for PAN (10-char alphanumeric: ABCDE1234F)
    pan_regex = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
    # Regex for DOB (DD/MM/YYYY)
    dob_regex = r'\b(\d{2}/\d{2}/\d{4})\b'

    if id_type.lower() == 'aadhar':
        match = re.search(aadhaar_regex, text)
        if match:
            details['id_number'] = match.group(0).replace(" ", "")
    elif id_type.lower() == 'pan':
        match = re.search(pan_regex, text)
        if match:
            details['id_number'] = match.group(0)

    dob_match = re.search(dob_regex, text)
    if dob_match:
        details['dob'] = dob_match.group(1)

    # Name extraction is less reliable; here we just look for lines with alphabetic characters
    # A simple approach could be to find the line containing 'Name' if present
    lines = text.split('\n')
    for line in lines:
        if "Name" in line and len(line.split()) > 1:
             details['name'] = " ".join(line.split()[1:])
             break
             
    return details


# --- Routes ---
@app.route('/')
@app.route('/homepage')
def homepage():
    """Renders the main registration form."""
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    """Handles form submission, OCR, verification, and database storage."""
    # 1. Get form data
    full_name = request.form['fullName']
    phone_number = request.form['phone']
    dob_str = request.form['dob']
    age = request.form['age']
    id_type = request.form['id_type']
    id_number_input = request.form.get('aadhar_number') or request.form.get('pan_number')
    image_file = request.files['id_photo']
    
    # 2. Save the uploaded image
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{image_file.filename}"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image_file.save(image_path)

    # 3. Perform OCR
    ocr_text = perform_ocr(image_path)
    extracted_details = extract_details_from_text(ocr_text, id_type)

    # 4. Perform Verification
    
    # --- Normalize DOB from OCR for comparison ---
    ocr_dob_str = extracted_details.get('dob')
    normalized_ocr_dob_for_comparison = None
    if ocr_dob_str:
        try:
            # Parse the OCR's DD/MM/YYYY date
            ocr_date_obj = datetime.strptime(ocr_dob_str, '%d/%m/%Y').date()
            # Reformat it to YYYY-MM-DD to match the form's input format
            normalized_ocr_dob_for_comparison = ocr_date_obj.strftime('%Y-%m-%d')
        except ValueError:
            # This handles cases where OCR might extract a badly formatted date
            normalized_ocr_dob_for_comparison = None

    # --- Run all comparisons ---
    name_verified = full_name.lower() in ocr_text.lower()
    # Compare the form's date string with our newly normalized OCR date string
    dob_verified = (dob_str == normalized_ocr_dob_for_comparison)
    id_verified = id_number_input == extracted_details.get('id_number')
    

    # 5. Store data in the database
    dob_obj = datetime.strptime(dob_str, '%Y-%m-%d').date()
    new_user = User(
        full_name=full_name,
        phone_number=phone_number,
        dob=dob_obj,
        age=age,
        id_type=id_type,
        id_number_input=id_number_input,
        image_filename=filename,
        ocr_extracted_text=ocr_text,
        ocr_extracted_name=extracted_details.get('name'),
        ocr_extracted_dob=extracted_details.get('dob'),
        ocr_extracted_id_number=extracted_details.get('id_number'),
        name_verified=name_verified,
        dob_verified=dob_verified,
        id_verified=id_verified
    )
    db.session.add(new_user)
    db.session.commit()

    # 6. Store data in a JSON file (as requested)
    user_data_for_json = {
    "id": new_user.id,
    "full_name": new_user.full_name,
    "phone_number": new_user.phone_number,
    "dob": new_user.dob.isoformat(),
    "age": new_user.age,
    "id_type": new_user.id_type,
    "id_number_input": new_user.id_number_input,
    "image_filename": new_user.image_filename,
    "ocr_extracted_text": new_user.ocr_extracted_text,
    "ocr_extracted_name": new_user.ocr_extracted_name,
    "ocr_extracted_dob": new_user.ocr_extracted_dob,
    "ocr_extracted_id_number": new_user.ocr_extracted_id_number,
    "name_verified": new_user.name_verified,
    "dob_verified": new_user.dob_verified,
    "id_verified": new_user.id_verified,
    "registration_timestamp": new_user.registration_timestamp.isoformat()
}
    
    try:
        with open('registrations.json', 'r+') as f:
            data = json.load(f)
            data.append(user_data_for_json)
            f.seek(0)
            json.dump(data, f, indent=4)
    except (FileNotFoundError, json.JSONDecodeError):
        with open('registrations.json', 'w') as f:
            json.dump([user_data_for_json], f, indent=4)

    # 7. Prepare results for the verification page
    verification_results = {
        'name_verified': name_verified,
        'dob_verified': dob_verified,
        'id_verified': id_verified,
        'overall_status': all([name_verified, dob_verified, id_verified]),
        'user_id': new_user.id
    }
    
    # Store results in session to pass to the verification page
    session['verification_results'] = verification_results
    return redirect(url_for('verification'))

@app.route('/verification')
def verification():
    """Displays the verification results to the user."""
    results = session.get('verification_results', None)
    if not results:
        return redirect(url_for('homepage'))
    return render_template('verification.html', results=results)

if __name__ == '__main__':
    with app.app_context():
        # This will create the table if it doesn't exist
        db.create_all()
    app.run(debug=True)