from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fk9lratv'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://reach_2_user:LPxy8sWuWo9zIAWOzfBMe09ko2QL1QDD@dpg-d6as17rh46gs738kng4g-a.singapore-postgres.render.com/reach_2'
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
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # Detailed student information
            contact_number = request.form.get('contact_number', '').strip()
            address = request.form.get('address', '').strip()
            emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
            emergency_contact = request.form.get('emergency_contact', '').strip()
            adviser = request.form.get('adviser', '').strip()
            mental_health_concern = request.form.get('mental_health_concern', '').strip()
            help_types = request.form.getlist('help_type')
            preferred_guidance_advocate_id = request.form.get('preferred_guidance_advocate_id', '').strip()
            
            # Handle grade and section
            grade = None
            section = None
            
            if preferred_guidance_advocate_id:
                # Get advocate's grade and section
                advocate = Teacher.query.get(int(preferred_guidance_advocate_id))
                if not advocate:
                    flash('Selected guidance advocate not found', 'error')
                    return redirect(url_for('register'))
                # Use advocate's grade and section if available, otherwise None
                grade = advocate.handling_grade
                section = advocate.handling_section
            else:
                grade_str = request.form.get('grade', '').strip()
                if not grade_str:
                    flash('Grade is required if you do not select a guidance advocate', 'error')
                    return redirect(url_for('register'))
                grade = int(grade_str)
                
                section = request.form.get('section', '').strip().upper()
                if not section:
                    flash('Section is required if you do not select a guidance advocate', 'error')
                    return redirect(url_for('register'))
            
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
                section=section,
                contact_number=contact_number if contact_number else None,
                address=address if address else None,
                emergency_contact_name=emergency_contact_name if emergency_contact_name else None,
                emergency_contact=emergency_contact if emergency_contact else None,
                adviser=adviser if adviser else None,
                mental_health_concern=mental_health_concern if mental_health_concern else None,
                help_types=','.join(help_types) if help_types else None,
                preferred_guidance_advocate_id=int(preferred_guidance_advocate_id) if preferred_guidance_advocate_id else None
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
            password = request.form.get('password')
            
            # Guidance Advocate fields
            is_guidance_advocate = request.form.get('is_guidance_advocate') == 'on'
            
            if is_guidance_advocate:
                handling_grade = None
                handling_section = None
                availability = request.form.get('availability', '').strip()
                specialization = request.form.get('specialization', '').strip()
            else:
                handling_grade_str = request.form.get('handling_grade', '').strip()
                if not handling_grade_str:
                    flash('Grade is required for regular teachers', 'error')
                    return redirect(url_for('register'))
                handling_grade = int(handling_grade_str)
                
                handling_section = request.form.get('handling_section', '').strip().upper()
                if not handling_section:
                    flash('Section is required for regular teachers', 'error')
                    return redirect(url_for('register'))
                
                # Check if a teacher is already registered for this grade and section
                existing_teacher = Teacher.query.filter_by(
                    handling_grade=handling_grade,
                    handling_section=handling_section,
                    is_guidance_advocate=False
                ).first()
                if existing_teacher:
                    flash('This section have already registered teacher', 'error')
                    return redirect(url_for('register'))
                
                availability = None
                specialization = None
            
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
                handling_section=handling_section,
                is_guidance_advocate=is_guidance_advocate,
                availability=availability,
                specialization=specialization
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

@app.route('/api/guidance-advocates')
def get_guidance_advocates():
    advocates = Teacher.query.filter_by(is_guidance_advocate=True).all()
    advocates_data = [
        {
            'id': advocate.id,
            'name': advocate.full_name(),
            'email': advocate.user.email,
            'availability': advocate.availability,
            'specialization': advocate.specialization,
            'handling_section': advocate.handling_section,
            'handling_grade': advocate.handling_grade
        }
        for advocate in advocates
    ]
    return jsonify({'advocates': advocates_data})

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
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        help_types = request.form.getlist('help_type')
        message = request.form.get('message')
        
        # Create subject from category and subcategory, replace underscores with spaces
        formatted_category = category.replace('_', ' ').title() if category else 'Unknown'
        formatted_subcategory = subcategory.replace('_', ' ').title() if subcategory else 'Unknown'
        
        # Remove redundant category from subcategory if it starts with the same word
        category_word = formatted_category.split()[0].lower() if formatted_category else ''
        subcategory_word = formatted_subcategory.split()[0].lower() if formatted_subcategory else ''
        
        if category_word == subcategory_word:
            # If they start with the same word, just use the subcategory
            subject = formatted_subcategory
        else:
            subject = f"{formatted_category} - {formatted_subcategory}"
        
        # Format help types: replace underscores with spaces
        formatted_help_types = [help_type.replace('_', ' ').title() for help_type in help_types]
        help_types_str = ', '.join(formatted_help_types) if formatted_help_types else 'Not specified'
        
        # Determine teacher for consultation
        teacher = None
        
        # If student has a preferred guidance advocate, send consultation to them
        if student.preferred_guidance_advocate_id:
            teacher = Teacher.query.get(student.preferred_guidance_advocate_id)
        else:
            # Otherwise, find teacher handling this student's grade and section
            teacher = Teacher.query.filter_by(
                handling_grade=student.grade,
                handling_section=student.section
            ).first()
        
        if not teacher:
            if student.preferred_guidance_advocate_id:
                flash('Your selected guidance advocate is no longer available', 'error')
            else:
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
            message=f"Help Types: {help_types_str}\n\n{message}"
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
    
    # Get students based on teacher role
    if teacher.is_guidance_advocate:
        # If guidance advocate, get students who selected this teacher as their advocate
        students = Student.query.filter_by(preferred_guidance_advocate_id=teacher.id).all()
    else:
        # If regular teacher, get students by grade and section
        students = Student.query.filter_by(
            grade=teacher.handling_grade,
            section=teacher.handling_section
        ).all()
    
    # Get all consultations for this teacher
    consultations = Consultation.query.filter_by(teacher_id=teacher.id).order_by(Consultation.created_at.desc()).all()
    
    # Count pending consultations
    pending_count = Consultation.query.filter_by(teacher_id=teacher.id, status='pending').count()
    
    return render_template('teacher_dashboard.html', teacher=teacher, students=students, consultations=consultations, pending_count=pending_count)

@app.route('/teacher/statistics')
def teacher_statistics():
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
    consultations = Consultation.query.filter_by(teacher_id=teacher.id).all()
    
    # Calculate statistics
    total_students = len(students)
    total_consultations = len(consultations)
    
    # Count consultations by status
    pending_consultations = Consultation.query.filter_by(teacher_id=teacher.id, status='pending').count()
    read_consultations = Consultation.query.filter_by(teacher_id=teacher.id, status='read').count()
    responded_consultations = Consultation.query.filter_by(teacher_id=teacher.id, status='responded').count()
    
    # Get unique sections
    unique_sections = db.session.query(Student.section).filter_by(
        grade=teacher.handling_grade,
        section=teacher.handling_section
    ).distinct().count()
    
    # Get consultation frequency (students with consultations)
    students_with_consultations = db.session.query(Consultation.student_id).filter_by(
        teacher_id=teacher.id
    ).distinct().count()
    
    # Get average consultations per student
    avg_consultations = total_consultations / total_students if total_students > 0 else 0
    
    # Get list of students with their consultation counts
    student_consultation_stats = []
    for student in students:
        count = Consultation.query.filter_by(student_id=student.id, teacher_id=teacher.id).count()
        student_consultation_stats.append({
            'student': student,
            'consultation_count': count
        })
    
    # Sort by consultation count descending
    student_consultation_stats.sort(key=lambda x: x['consultation_count'], reverse=True)
    
    # Get consultation status breakdown for chart
    status_breakdown = {
        'pending': pending_consultations,
        'read': read_consultations,
        'responded': responded_consultations
    }
    
    statistics = {
        'total_students': total_students,
        'total_consultations': total_consultations,
        'pending_consultations': pending_consultations,
        'read_consultations': read_consultations,
        'responded_consultations': responded_consultations,
        'unique_sections': unique_sections,
        'students_with_consultations': students_with_consultations,
        'avg_consultations': round(avg_consultations, 2),
        'students_without_consultations': total_students - students_with_consultations,
        'status_breakdown': status_breakdown
    }
    
    return render_template('teacher_statistics.html', teacher=teacher, statistics=statistics, student_stats=student_consultation_stats, consultations=consultations)

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



@app.route('/teacher/student/<int:student_id>/delete', methods=['POST'])
def delete_student(student_id):
    if 'user_id' not in session or session.get('user_type') != 'teacher':
        flash('Unauthorized access', 'error')
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    if not teacher:
        flash('Teacher not found', 'error')
        return redirect(url_for('login'))
    
    student = Student.query.get_or_404(student_id)
    
    # Check if student is under this teacher's supervision
    if student.grade != teacher.handling_grade or student.section != teacher.handling_section:
        flash('Unauthorized access', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    try:
        # Get user associated with student
        user = student.user
        
        # Delete all consultations and messages for this student
        consultations = Consultation.query.filter_by(student_id=student.id).all()
        for consultation in consultations:
            # Delete consultation messages
            ConsultationMessage.query.filter_by(consultation_id=consultation.id).delete()
            # Delete consultation
            db.session.delete(consultation)
        
        # Delete the student record
        db.session.delete(student)
        
        # Delete the user account
        db.session.delete(user)
        
        db.session.commit()
        
        flash(f'Student {student.first_name} {student.last_name} has been deleted successfully', 'success')
        return redirect(url_for('teacher_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error deleting student: {str(e)}')
        flash('An error occurred while deleting the student. Please try again.', 'error')
        return redirect(url_for('view_student', student_id=student_id))

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
        
        # Update emergency contact information
        emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
        student.emergency_contact_name = emergency_contact_name if emergency_contact_name else None
        
        emergency_contact = request.form.get('emergency_contact', '').strip()
        student.emergency_contact = emergency_contact if emergency_contact else None
        
        # Update preferred guidance advocate
        preferred_guidance_advocate_id = request.form.get('preferred_guidance_advocate_id', '').strip()
        if preferred_guidance_advocate_id:
            student.preferred_guidance_advocate_id = int(preferred_guidance_advocate_id)
        else:
            student.preferred_guidance_advocate_id = None
        
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

@app.route('/teacher/edit', methods=['GET', 'POST'])
def edit_teacher():
    if 'user_id' not in session or session.get('user_type') != 'teacher':
        return redirect(url_for('login'))
    
    teacher = Teacher.query.filter_by(user_id=session['user_id']).first()
    if not teacher:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Update teacher information
        teacher.first_name = request.form.get('first_name', '').strip()
        teacher.last_name = request.form.get('last_name', '').strip()
        teacher.middle_name = request.form.get('middle_name', '').strip() or None
        
        # Update guidance advocate specific fields
        if teacher.is_guidance_advocate:
            teacher.specialization = request.form.get('specialization', '').strip() or None
            teacher.availability = request.form.get('availability', '').strip() or None
        
        db.session.commit()
        flash('Teacher information updated successfully', 'success')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('edit_teacher.html', teacher=teacher)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], 'attachments', filename), as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        # Drop all tables and recreate them (for development)
        # Remove this in production and use proper migrations

        db.create_all()
        print("Database tables created/updated successfully!")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

