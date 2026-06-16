from flask import Blueprint, request, jsonify, render_template, get_flashed_messages, flash, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Temporada, Equipo, Categoria, Jugador, Posicion

user_routes = Blueprint('user_routes', __name__)

@user_routes.route('/register', methods=['GET'])
def show_register():
    return render_template("register.html")

@user_routes.route('/register', methods=['POST'])
def register():
    data = request.form

    # Verificar que los campos estén completos
    if not data.get('username') or not data.get('password') or not data.get('confirm_password'):
        return render_template("register.html", error="Todos los campos son obligatorios", username=data.get('username'))

    # Verificar que las contraseñas coincidan
    if data['password'] != data['confirm_password']:
        return render_template("register.html", error="Las contraseñas no coinciden", username=data.get('username'))

    # Validar el formato del nombre de usuario
    username = data['username']
    if ' ' in username or '/' in username or '\\' in username:
        return render_template("register.html", error="El nombre de usuario no puede contener espacios ni barras (/ o \\)", username=data.get('username'))

    # Verificar si el usuario ya existe
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return render_template("register.html", error="El nombre de usuario ya está registrado", username=data.get('username'))

    try:
        # Hashear la contraseña antes de guardarla
        hashed_password = generate_password_hash(data['password'], method='sha256')

        # Crear el nuevo usuario
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return render_template("register.html", error=f"Error al registrar el usuario: {str(e)}", username=data.get('username'))

    return redirect(f"/{username}/dashboard")

@user_routes.route('/login', methods=['GET'])
def show_login():
    messages = get_flashed_messages(with_categories=True)
    return render_template("login.html")

@user_routes.route('/login', methods=['POST'])
def login():
    data = request.form
    existing_user = User.query.filter_by(username=data['username']).first()

    if existing_user and check_password_hash(existing_user.password, data['password']):
        session['user_id'] = existing_user.id
        session['username'] = existing_user.username
        flash("Inicio de sesión exitoso", "success")
        return redirect(f"/{existing_user.username}/dashboard")
    else:
        flash("Usuario o contraseña incorrectos", "error")
        return render_template("login.html")

@user_routes.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada con éxito", "success")
    return redirect('/')

@user_routes.route('/<username>/home', methods=['GET'])
def user_home(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')
    # Redirigir al nuevo dashboard
    return redirect(f"/{username}/dashboard")
