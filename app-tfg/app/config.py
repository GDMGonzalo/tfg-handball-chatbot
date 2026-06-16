import os

class Config:
    # Configuración de la base de datos MySQL usando variables de entorno
    MYSQL_USER = os.environ.get("MYSQL_USER", "tfg")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "tfg1234")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", 3306)
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "mikel")
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MODEL_URL = os.environ.get("MODEL_URL", "http://localhost:5004")

    # Carpeta de subidas (apunta a la carpeta compartida por Docker)
    UPLOAD_FOLDER = os.environ.get("SHARED_DIR", "Almacenamiento/uploads")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # Tamaño máximo: 500 MB

    # Configuración de Flask-Login
    LOGIN_VIEW = "show_login"
    LOGIN_MESSAGE = "Por favor, inicia sesión para acceder a esta página."

    # Clave secreta 
    SECRET_KEY = "c82421a4f91a8f782df5be9b4c8f3efc1596dc62d85f4e6b821a1345"

    
    print(f"Conectando a MySQL en {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"Base de datos: {MYSQL_DATABASE}")
    print(f"Carpeta de subidas: {UPLOAD_FOLDER}")           
