from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# Initialize models after db is created

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'student' or 'teacher'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    grade = db.Column(db.Integer, nullable=True)  # Nullable if assigned to Guidance Advocate only
    section = db.Column(db.String(10), nullable=True)  # Nullable if assigned to Guidance Advocate only
    contact_number = db.Column(db.String(20), nullable=True)
    emergency_contact = db.Column(db.String(20), nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    adviser = db.Column(db.String(100), nullable=True)
    mental_health_concern = db.Column(db.String(100), nullable=True)
    help_types = db.Column(db.Text, nullable=True)  # Comma-separated values
    preferred_guidance_advocate_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=True)
    archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='student_profile')
    consultations = db.relationship('Consultation', backref='student', lazy=True)
    preferred_advocate = db.relationship('Teacher', backref='preferred_students', foreign_keys=[preferred_guidance_advocate_id])
    
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    handling_grade = db.Column(db.Integer, nullable=True)  # Nullable for Guidance Advocates
    handling_section = db.Column(db.String(10), nullable=True)  # Nullable for Guidance Advocates
    is_guidance_advocate = db.Column(db.Boolean, default=False)
    availability = db.Column(db.Text, nullable=True)  # e.g., "Monday-Friday 9AM-5PM"
    specialization = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='teacher_profile')
    consultations = db.relationship('Consultation', backref='teacher', lazy=True)
    
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'read', 'responded'
    deleted = db.Column(db.Boolean, default=False)
    deleted_by = db.Column(db.String(20), nullable=True)  # 'student' or 'teacher'
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = db.relationship('ConsultationMessage', backref='consultation', lazy=True, cascade='all, delete-orphan')

class ConsultationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consultation_id = db.Column(db.Integer, db.ForeignKey('consultation.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)  # 'student' or 'teacher'
    sender_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    attachment_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

