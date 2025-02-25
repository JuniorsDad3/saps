from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin 
from app import db

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class Case(db.Model):
    __tablename__ = 'cases'
    case_id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    crime_type = db.Column(db.String(100), nullable=True, default="Unknown")
    is_live = db.Column(db.Boolean, default=False, server_default="false")
    status = db.Column(db.String(50), nullable=False, default="Pending")
    submitted_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('user.id')) 
    voice_note = db.Column(db.LargeBinary, nullable=True)
    picture = db.Column(db.LargeBinary, nullable=True)

    def __repr__(self):
        return f'<Case {self.case_number}>'

class Document(db.Model):
    __tablename__ = 'documents'
    document_id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    document_url = db.Column(db.String(200))
    document_type = db.Column(db.String(200))
    submitted_at = db.Column(db.DateTime, default=db.func.current_timestamp())