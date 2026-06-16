import os

class Config:
    # Configuración de la base de datos MySQL usando variables de entorno
    MYSQL_USER = os.environ.get("MYSQL_USER", "tfg")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "tfg1234")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "mikel")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", 3306)
    # Carpeta de subidas (apunta a la carpeta compartida por Docker)
    UPLOAD_FOLDER = os.environ.get("SHARED_DIR", os.path.abspath("../app/Almacenamiento/uploads"))
    USE_SPLIT = os.environ.get("USE_SPLIT", False)
    MIN_LEN = int(os.environ.get("MIN_LEN", 100))
    EPS = float(os.environ.get("EPS", 0.7))
    MIN_SAMPLES = int(os.environ.get("MIN_SAMPLES", 4))
    MAX_K = int(os.environ.get("MAX_K", 3))
    USE_CONNECT = os.environ.get("USE_CONNECT", True)
    SPATIAL_FACTOR = float(os.environ.get("SPATIAL_FACTOR", 1.0))
    MERGE_DIST_THRESH = float(os.environ.get("MERGE_DIST_THRESH", 0.4))

    print(f"Conectando a MySQL en {MYSQL_HOST}:{MYSQL_PORT}")
    print(f"Base de datos: {MYSQL_DATABASE}")
    print(f"Carpeta de subidas: {UPLOAD_FOLDER}")           
