from flask import redirect, render_template, Blueprint, request, url_for, flash, jsonify, Request
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, Task
from extensions import db
from sqlalchemy.exc import IntegrityError
from flask_login import login_user, login_required, logout_user, current_user

bp = Blueprint('main', __name__) 

@bp.route("/")
@bp.route("/index")
@login_required
def index():
    return render_template('index.html', name=current_user.first_name)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('Email')
        password = request.form.get('Password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()
        if user:
            if user.password_hash:
                if check_password_hash(user.password_hash, password):
                    login_user(user, remember=remember)
                    return redirect(url_for('main.index'))
                else:
                    flash('Invalid password. Please try again.')
            else:
                flash('User account is invalid. Please contact support.')
        else:
            flash('Email not found. Please check your login details and try again.')
    
    return render_template('login.html')

@bp.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        first_name = request.form.get('First name')
        surname = request.form.get('Surname')
        email = request.form.get('Email')
        phone_number = request.form.get('Phone number')
        password = request.form.get('Password')
        confirm_password = request.form.get('Confirm password')

        # Input validation
        if not all([first_name, surname, email, phone_number, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('sign-up.html')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('sign-up.html')

        # Check if user already exists
        existing_user = User.query.filter((User.email == email) | (User.phone_number == phone_number)).first()
        if existing_user:
            if existing_user.email == email:
                flash('Email address already exists', 'error')
            elif existing_user.phone_number == phone_number:
                flash('Phone number already exists', 'error')
            return render_template('sign-up.html')

        # Create new user
        new_user = User(
            first_name=first_name,
            surname=surname,
            email=email,
            phone_number=phone_number,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully. Please log in.', 'success')
            return redirect(url_for('main.login'))
        except IntegrityError as e:
            db.session.rollback()
            if "UNIQUE constraint failed: user.email" in str(e):
                flash('An account with this email already exists.', 'error')
            elif "UNIQUE constraint failed: user.phone_number" in str(e):
                flash('An account with this phone number already exists.', 'error')
            else:
                flash('An error occurred while creating your account. Please try again.', 'error')
            return render_template('sign-up.html')
        except Exception as e:
            db.session.rollback()
            flash('An unexpected error occurred. Please try again.', 'error')
            return render_template('sign-up.html')

    return render_template('sign-up.html')

@bp.route('/about')
@login_required
def about():
   return render_template('about.html', name=current_user.first_name)

@bp.route('/contact')
@login_required
def contact_us():
    return render_template('contact.html', name=current_user.first_name)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/tasks', methods=['GET'])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(author=current_user).all()
    return jsonify([task.to_dict() for task in tasks])

@bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.json
    task = Task(
        description=data['description'],
        category=data['category'],
        completed=data.get('completed', False),
        author=current_user
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201

@bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    task.description = data.get('description', task.description)
    task.category = data.get('category', task.category)
    task.completed = data.get('completed', task.completed)
    db.session.commit()
    return jsonify(task.to_dict())

@bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.author != current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(task)
    db.session.commit()
    return '', 204