#!/usr/bin/env python
from app import app, db
from models import User, Case, Document
from werkzeug.security import generate_password_hash

def run_tests():
    with app.app_context():
        # Ensure tables are created
        db.create_all()
        # Create default user if not exists
        if not User.query.filter_by(email='admin@example.com').first():
            user = User(
                username='admin',
                email='admin@example.com',
                password_hash=generate_password_hash('admin123', method='pbkdf2:sha256')
            )
            db.session.add(user)
            db.session.commit()
            print("Default user created.")
        else:
            print("Default user already exists.")
    
    client = app.test_client()

    # Test Login Page (GET)
    response = client.get('/login')
    print("GET /login status code:", response.status_code)
    if b"Login" in response.data:
        print("Login page loaded successfully.")
    else:
        print("Login page did not load correctly.")

    # Test Login with default credentials (POST)
    login_data = {
        'email': 'admin@example.com',
        'password': 'admin123'
    }
    response = client.post('/login', data=login_data, follow_redirects=True)
    print("POST /login status code:", response.status_code)
    if b"Dashboard" in response.data or b"admin_dashboard" in response.data:
        print("Login succeeded and dashboard loaded.")
    else:
        print("Login failed or dashboard did not load.")

    # Test Registration Page (GET)
    response = client.get('/register')
    print("GET /register status code:", response.status_code)
    if b"Register" in response.data:
        print("Registration page loaded successfully.")
    else:
        print("Registration page did not load correctly.")

    # Test Submit Case Page (GET)
    response = client.get('/submit_case')
    print("GET /submit_case status code:", response.status_code)
    if b"Log a Case" in response.data or b"Submit Case" in response.data:
        print("Submit Case page loaded successfully.")
    else:
        print("Submit Case page did not load correctly.")

    # Test Certification Page (GET)
    response = client.get('/certification')
    print("GET /certification status code:", response.status_code)
    if b"Certification" in response.data:
        print("Certification page loaded successfully.")
    else:
        print("Certification page did not load correctly.")

if __name__ == '__main__':
    run_tests()
