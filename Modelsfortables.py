from flask_sqlalchemy import SQLAlchemy

# Import db without causing circular import
from app import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)  # Match DB
    username = db.Column(db.String(100))  # Match 'username'
    email = db.Column(db.String(255), unique=True)  # Match 'email'
    password_hash = db.Column(db.String(255))  # Add password field from DB

class Case(db.Model):
    __tablename__ = 'cases'
    case_id = db.Column(db.Integer, primary_key=True)  # Match DB
    case_number = db.Column(db.String(100), unique=True)
    crime_type = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=db.func.now())  # Fix column name
    is_live = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(100), default='Pending')
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Fix FK

class Document(db.Model):
    __tablename__ = 'documents'
    document_id = db.Column(db.Integer, primary_key=True)  # Match DB
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'))  # Match DB
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Match DB
    document_url = db.Column(db.String(200))  # Fix column name
    document_type = db.Column(db.String(200))
    submitted_at = db.Column(db.DateTime, default=db.func.now())  # Fix column name