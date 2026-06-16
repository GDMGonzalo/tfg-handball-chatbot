from flask import Blueprint, request, jsonify, render_template, session, redirect, flash
import os
from models import db, Temporada, Liga, Partido, Video, Categoria, Equipo
from sqlalchemy import func

temporada_routes = Blueprint('temporada_routes', __name__)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'Almacenamiento', 'uploads')

@temporada_routes.route('/<username>/temporadas', methods=['GET'])
def listar_temporadas(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']
    temporadas = Temporada.query.filter_by(user_id=user_id).all()
    
    # Contar videos por temporada
    videos_por_temporada = {}
    for temporada in temporadas:
        count = Video.query.join(Partido).join(Liga).filter(Liga.temporada_id == temporada.id).count()
        videos_por_temporada[temporada.id] = count
    
    return render_template(
        "dashboard/temporadas/index.html",
        username=username,
        temporadas=temporadas,
        videos_por_temporada=videos_por_temporada
    )

@temporada_routes.route('/<username>/temporada/nueva', methods=['GET', 'POST'])
def nueva_temporada(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    if request.method == 'POST':
        data = request.form
        user_id = session['user_id']

        # Verificar si ya existe una temporada con el mismo nombre
        existing_temporada = Temporada.query.filter_by(user_id=user_id, nombre=data.get('nombre')).first()
        if existing_temporada:
            flash("Ya tienes una temporada con este nombre.", "error")
            return render_template(
                "dashboard/temporadas/create.html",
                username=username
            )

        try:
            nueva_temporada = Temporada(
                user_id=user_id,
                nombre=data.get('nombre'),
                descripcion=data.get('descripcion')
            )
            db.session.add(nueva_temporada)
            db.session.commit()
            flash("Temporada creada con éxito", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear la temporada: {str(e)}", "error")
            return render_template(
                "dashboard/temporadas/create.html",
                username=username
            )

        return redirect(f"/{username}/temporadas")

    return render_template("dashboard/temporadas/create.html", username=username)

@temporada_routes.route('/<username>/temporada/<int:temporada_id>', methods=['GET'])
def ver_temporada(username, temporada_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    temporada = Temporada.query.filter_by(id=temporada_id, user_id=session['user_id']).first()
    if not temporada:
        flash("Temporada no encontrada", "error")
        return redirect(f"/{username}/temporadas")

    # Obtener ligas, partidos y videos relacionados con la temporada
    ligas = Liga.query.filter_by(temporada_id=temporada_id).all()
    partidos = Partido.query.join(Liga).filter(Liga.temporada_id == temporada_id).all()
    videos = Video.query.join(Partido).join(Liga).filter(Liga.temporada_id == temporada_id).all()
    categorias = Categoria.query.all()

    # Renderizar la plantilla
    return render_template(
        "dashboard/temporadas/view.html",
        temporada=temporada,
        username=username,
        ligas=ligas,
        partidos=partidos,
        videos=videos,
        categorias=categorias
    )

@temporada_routes.route('/<username>/temporada/<int:temporada_id>/editar', methods=['GET', 'POST'])
def editar_temporada(username, temporada_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    temporada = Temporada.query.get_or_404(temporada_id)
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para editar esta temporada", "error")
        return redirect(f"/{username}/temporadas")

    if request.method == 'POST':
        data = request.form
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')

        # Validar que el nuevo nombre no sea duplicado, salvo el caso actual
        temporada_duplicada = Temporada.query.filter_by(user_id=session['user_id']).filter(
            func.lower(Temporada.nombre) == nombre.lower(),
            Temporada.id != temporada.id
        ).first()
        
        if temporada_duplicada:
            flash(f"Ya tienes una temporada con este nombre: '{nombre}'", "error")
            return render_template(
                "dashboard/temporadas/edit.html",
                username=username,
                temporada=temporada
            )

        temporada.nombre = nombre
        temporada.descripcion = descripcion
        
        try:
            db.session.commit()
            flash("Temporada actualizada correctamente", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar la temporada: {e}", "error")

        return redirect(f"/{username}/temporada/{temporada_id}")

    return render_template('dashboard/temporadas/edit.html', username=username, temporada=temporada)

@temporada_routes.route('/<username>/temporada/<int:temporada_id>/eliminar', methods=['POST'])
def eliminar_temporada(username, temporada_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    temporada = Temporada.query.get_or_404(temporada_id)
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para eliminar esta temporada", "error")
        return redirect(f"/{username}/temporadas")

    try:
        # Eliminar todos los archivos asociados a esta temporada
        user_folder = os.path.join(UPLOAD_FOLDER, username)
        temporada_folder = os.path.join(user_folder, f"temporada_{temporada_id}")
        
        if os.path.exists(temporada_folder):
            import shutil
            shutil.rmtree(temporada_folder)
        
        # Eliminar la temporada (esto eliminará en cascada ligas, partidos, videos, etc.)
        db.session.delete(temporada)
        db.session.commit()
        flash('Temporada eliminada con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la temporada: {e}', 'error')

    return redirect(f'/{username}/temporadas')
