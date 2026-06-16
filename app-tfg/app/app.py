from flask import Flask, render_template, jsonify, send_from_directory, session, redirect, flash
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from routes import register_routes
from models import db
import os
from datetime import datetime

# Inicializar la aplicación Flask
app = Flask(__name__) 
app.config.from_object(Config)

# Inicializar SQLAlchemy
db.init_app(app)

# Registrar las rutas (esto ya incluye evento_personalizado_routes)
register_routes(app)

app.config['SQLALCHEMY_ECHO'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# Sistema de subida por fragmentos - sin límite de tamaño total
# Para subidas por fragmentos, el límite se aplica a cada fragmento, no al archivo completo

# Probar la conexión con la base de datos
with app.app_context():
    try:
        db.session.execute(text('SELECT 1'))
        print("Conexión exitosa con la base de datos")
    except Exception as e:
        print(f"Error al conectar con la base de datos: {e}")

@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200

# Ruta raíz del proyecto
@app.route('/')
def home():
    return render_template("index.html")

# Manejar error 404
@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template("404.html"), 404

# Filtro personalizado para formatear fecha y hora
@app.template_filter('datetime') 
def format_datetime(value, format='%Y-%m-%dT%H:%M'):
    if value is None:
        return ""
    return value.strftime(format)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/images', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    port = int(os.environ.get("APP_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
