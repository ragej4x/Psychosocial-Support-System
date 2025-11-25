from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///psychosocial.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'attachments'), exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

# Import models after app config
from models import db, User, Teacher, Student, Consultation, ConsultationMessage
db.init_app(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database initialization will happen in main block

@app.route('/')
def index():
    if 'user_id' in session:
        user_type = session.get('user_type')
        if user_type == 'student':
            return redirect(url_for('student_dashboard'))
        elif user_type == 'teacher':
            return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        
        if user_type == 'student':
            # Student registration
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            middle_name = request.form.get('middle_name', '').strip()
            email = request.form.get('email').lower().strip()
            grade = int(request.form.get('grade'))
            section = request.form.get('section').upper()
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return redirect(url_for('register'))
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return redirect(url_for('register'))
            
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                user_type='student'
            )
            db.session.add(user)
            db.session.flush()
            
            student = Student(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name if middle_name else None,
                grade=grade,
                section=section
            )
            db.session.add(student)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        
        elif user_type == 'teacher':
            # Teacher registration
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            middle_name = request.form.get('middle_name', '').strip()
            email = request.form.get('email').lower().strip()
            handling_grade = int(request.form.get('handling_grade'))
            handling_section = request.form.get('handling_section').upper()
            password = request.form.get('password')
            
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'error')
                return redirect(url_for('register'))
            
            user = User(
                email=email,
                password_hash=generate_password_hash(password),
                user_type='teacher'
            )
            db.session.add(user)
            db.session.flush()
            
            teacher = Teacher(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name if middle_name else None,
                handling_grade=handling_grade,
                handling_section=handling_section
            )
            db.session.add(teacher)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password', 'error')
            return render_template('login.html')
        
        # Try exact match first, then case-insensitive
        user = User.query.filter_by(email=email).first()
        if not user:
            # Try case-insensitive search for emails stored before normalization
            user = User.query.filter(db.func.lower(User.email) == email).first()
        
        if user:
            # Check password
            password_valid = check_password_hash(user.password_hash, password)
            if password_valid:
                session['user_id'] = user.id
                session['user_type'] = user.user_type
                session['user_email'] = user.email
                
                if user.user_type == 'student':
                    return redirect(url_for('student_dashboard'))
                elif user.user_type == 'teacher':
                    return redirect(url_for('teacher_dashboard'))
            else:
                flash('Invalid email or password', 'error')
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/api/sections/<int:grade>')
def get_sections(grade):
    sections = db.session.query(Student.section).filter_by(grade=grade).distinct().all()
    section_list = [s[0] for s in sections]
    # Add common sections if none exist
    if not section_list:
        section_list = ['A', 'B', 'C', 'D', 'E']
    return jsonify({'sections': sorted(section_list)})

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=session['user_id']).first()
    if not student:
        return redirect(url_for('login'))
    
    consultations = Consultation.query.filter_by(student_id=student.id).order_by(Consultation.created_at.desc()).all()
    
    return render_template('student_dashboard.html', student=student, consultations=consultations)

@app.route('/student/consultation/new', methods=['GET', 'POST'])
def new_consultation():
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('login'))
    
    student = Student.query.filter_by(user_id=session['user_id']).first()
    if not student:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Find teacher handling this student's grade and section
        teacher = Teacher.query.filter_by(
            handling_grade=student.grade,
            handling_section=student.section
        ).first()
        
        if not teacher:
            flash('No teacher assigned to your grade and section', 'error')
            return redirect(url_for('student_dashboard'))
        
        consultation = Consultation(
            student_id=student.id,
            teacher_id=teacher.id,
            subject=subject,
            status='pending'
        )
        db.session.add(consultation)
        db.session.flush()
        
        consultation_message = ConsultationMessage(
            consultation_id=consultation.id,
            sender_type='student',
            sender_id=student.id,
            message=message
        )
        db.session.add(consultation_message)
        db.session.commit()
        
        flash('Consultation created successfully', 'success')
        return redirect(url_for('view_consultation', consultation_id=consultation.id))
    
    return render_template('new_consultation.html', student=student)

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'teacher':
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    if not teacher:
        return redirect(url_for('login'))
    
    # Get all students under this teacher
    students = Student.query.filter_by(
        grade=teacher.handling_grade,
        section=teacher.handling_section
    ).all()
    
    # Get all consultations for this teacher
    consultations = Consultation.query.filter_by(teacher_id=teacher.id).order_by(Consultation.created_at.desc()).all()
    
    # Count pending consultations
    pending_count = Consultation.query.filter_by(teacher_id=teacher.id, status='pending').count()
    
    return render_template('teacher_dashboard.html', teacher=teacher, students=students, consultations=consultations, pending_count=pending_count)

@app.route('/consultation/<int:consultation_id>')
def view_consultation(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_type = session.get('user_type')
    user_id = session['user_id']
    
    # Check authorization
    if user_type == 'student':
        student = Student.query.filter_by(user_id=user_id).first()
        if consultation.student_id != student.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('student_dashboard'))
    elif user_type == 'teacher':
        teacher = Teacher.query.filter_by(user_id=user_id).first()
        if consultation.teacher_id != teacher.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('login'))
    
    messages = ConsultationMessage.query.filter_by(consultation_id=consultation_id).order_by(ConsultationMessage.created_at.asc()).all()
    
    # Mark as read if teacher views it
    if user_type == 'teacher' and consultation.status == 'pending':
        consultation.status = 'read'
        db.session.commit()
    
    if user_type == 'student':
        student = Student.query.filter_by(user_id=user_id).first()
        return render_template('view_consultation.html', consultation=consultation, messages=messages, current_user=student, user_type='student')
    else:
        teacher = Teacher.query.filter_by(user_id=user_id).first()
        student = Student.query.get(consultation.student_id)
        return render_template('view_consultation.html', consultation=consultation, messages=messages, current_user=teacher, user_type='teacher', student=student)

@app.route('/consultation/<int:consultation_id>/reply', methods=['POST'])
def reply_consultation(consultation_id):
    consultation = Consultation.query.get_or_404(consultation_id)
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_type = session.get('user_type')
    user_id = session['user_id']
    
    # Check authorization
    if user_type == 'student':
        student = Student.query.filter_by(user_id=user_id).first()
        if consultation.student_id != student.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('student_dashboard'))
        sender_id = student.id
    elif user_type == 'teacher':
        teacher = Teacher.query.filter_by(user_id=user_id).first()
        if consultation.teacher_id != teacher.id:
            flash('Unauthorized access', 'error')
            return redirect(url_for('teacher_dashboard'))
        sender_id = teacher.id
    else:
        return redirect(url_for('login'))
    
    message_text = request.form.get('message')
    file = request.files.get('attachment')
    
    filename = None
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'attachments', filename)
        file.save(file_path)
    
    consultation_message = ConsultationMessage(
        consultation_id=consultation_id,
        sender_type=user_type,
        sender_id=sender_id,
        message=message_text,
        attachment_filename=filename
    )
    
    # Update consultation status
    if user_type == 'teacher':
        consultation.status = 'responded'
    else:
        consultation.status = 'pending'
    
    db.session.add(consultation_message)
    db.session.commit()
    
    flash('Reply sent successfully', 'success')
    return redirect(url_for('view_consultation', consultation_id=consultation_id))


@app.route('/consultation/<int:consultation_id>/delete', methods=['POST'])
def delete_consultation(consultation_id):
    if 'user_id' not in session or session.get('user_type') != 'student':
        return redirect(url_for('login'))

    student = Student.query.filter_by(user_id=session['user_id']).first()
    consultation = Consultation.query.get_or_404(consultation_id)

    if consultation.student_id != student.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('student_dashboard'))

    db.session.delete(consultation)
    db.session.commit()

    flash('Consultation deleted successfully', 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/teacher/student/<int:student_id>')
def view_student(student_id):
    if 'user_id' not in session or session.get('user_type') != 'teacher':
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    if not teacher:
        return redirect(url_for('login'))
    
    student = Student.query.get_or_404(student_id)
    
    # Check if student is under this teacher's supervision
    if student.grade != teacher.handling_grade or student.section != teacher.handling_section:
        flash('Unauthorized access', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    user = student.user
    consultations = Consultation.query.filter_by(student_id=student.id).order_by(Consultation.created_at.desc()).all()
    
    return render_template('view_student.html', student=student, user=user, teacher=teacher, consultations=consultations)

@app.route('/teacher/student/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    if 'user_id' not in session or session.get('user_type') != 'teacher':
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    if not teacher:
        return redirect(url_for('login'))
    
    student = Student.query.get_or_404(student_id)
    
    # Check if student is under this teacher's supervision
    if student.grade != teacher.handling_grade or student.section != teacher.handling_section:
        flash('Unauthorized access', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    user = student.user
    
    if request.method == 'POST':
        # Update student information
        student.first_name = request.form.get('first_name', student.first_name)
        student.last_name = request.form.get('last_name', student.last_name)
        middle_name = request.form.get('middle_name', '').strip()
        student.middle_name = middle_name if middle_name else None
        student.grade = int(request.form.get('grade', student.grade))
        student.section = request.form.get('section', student.section).upper()
        
        # Update email
        new_email = request.form.get('email', '').lower().strip()
        if new_email and new_email != user.email:
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user and existing_user.id != user.id:
                flash('Email already registered to another account', 'error')
                return redirect(url_for('edit_student', student_id=student_id))
            user.email = new_email
        
        # Update password if provided
        new_password = request.form.get('password', '').strip()
        if new_password:
            if len(new_password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return redirect(url_for('edit_student', student_id=student_id))
            user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        flash('Student information updated successfully', 'success')
        return redirect(url_for('view_student', student_id=student_id))
    
    return render_template('edit_student.html', student=student, user=user, teacher=teacher)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], 'attachments', filename), as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        # Drop all tables and recreate them (for development)
        # Remove this in production and use proper migrations
        db.drop_all()
        db.create_all()
        print("Database tables created/updated successfully!")
    app.run(debug=True)

