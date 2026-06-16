from flask import Blueprint
from routes.user_routes import user_routes
from routes.dashboard_routes import dashboard_routes
from routes.temporada_routes import temporada_routes
from routes.liga_routes import liga_routes
from routes.equipo_routes import equipo_routes
from routes.partido_routes import partido_routes
from routes.video_routes import video_routes
from routes.evento_routes import evento_routes
from routes.evento_personalizado_routes import evento_personalizado_routes
from routes.chatbot_routes import chatbot_bp

def register_routes(app):
    """Registra todas las rutas de la aplicación"""
    app.register_blueprint(user_routes)
    app.register_blueprint(dashboard_routes)
    app.register_blueprint(temporada_routes)
    app.register_blueprint(liga_routes)
    app.register_blueprint(equipo_routes)
    app.register_blueprint(partido_routes)
    app.register_blueprint(video_routes)
    app.register_blueprint(evento_routes)
    app.register_blueprint(evento_personalizado_routes)
    app.register_blueprint(chatbot_bp)
