from flask import Blueprint, request, jsonify, render_template, session, redirect, flash
from models import db, Temporada, Liga, Equipo, Partido, Video, Jugador, EquipoLiga, EventoPersonalizado

dashboard_routes = Blueprint('dashboard_routes', __name__)

@dashboard_routes.route('/<username>/dashboard', methods=['GET'])
def dashboard(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Obtener datos para el dashboard
    temporadas = Temporada.query.filter_by(user_id=user_id).all()
    
    # Obtener todas las ligas del usuario
    ligas = Liga.query.join(Temporada).filter(Temporada.user_id == user_id).all()
    
    # Obtener solo los equipos que pertenecen a ligas del usuario actual
    equipos = db.session.query(Equipo).join(EquipoLiga).join(Liga).join(Temporada).filter(
        Temporada.user_id == user_id
    ).distinct().all()
    
    # Obtener todos los partidos del usuario
    partidos = Partido.query.join(Liga).join(Temporada).filter(Temporada.user_id == user_id).all()
    
    # Obtener todos los videos del usuario
    videos = Video.query.join(Partido).join(Liga).join(Temporada).filter(Temporada.user_id == user_id).all()
    
    # Obtener partidos recientes (últimos 5)
    partidos_recientes = Partido.query.join(Liga).join(Temporada).filter(
        Temporada.user_id == user_id
    ).order_by(Partido.fecha_hora.desc()).limit(5).all()
    
    # Obtener videos recientes (últimos 4)
    videos_recientes = Video.query.join(Partido).join(Liga).join(Temporada).filter(
        Temporada.user_id == user_id
    ).order_by(Video.uploaded_at.desc()).limit(4).all()
    
    # Obtener eventos personalizados del usuario
    eventos_personalizados = EventoPersonalizado.query.filter_by(user_id=user_id).all()
    
    return render_template(
        "dashboard/index.html",
        username=username,
        temporadas=temporadas,
        ligas=ligas,
        equipos=equipos,
        partidos=partidos,
        videos=videos,
        partidos_recientes=partidos_recientes,
        videos_recientes=videos_recientes,
        eventos_personalizados=eventos_personalizados
    )
