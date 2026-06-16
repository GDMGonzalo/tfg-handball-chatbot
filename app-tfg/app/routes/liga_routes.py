from flask import Blueprint, request, jsonify, render_template, session, redirect, flash
from models import db, Liga, Temporada, Categoria, Equipo, EquipoLiga

liga_routes = Blueprint('liga_routes', __name__)

@liga_routes.route('/<username>/ligas', methods=['GET'])
def listar_ligas(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Obtener filtros
    temporada_id = request.args.get('temporada_id')
    categoria_id = request.args.get('categoria_id')
    
    # Consulta base
    query = Liga.query.join(Temporada).filter(Temporada.user_id == user_id)
    
    # Aplicar filtros
    if temporada_id:
        query = query.filter(Liga.temporada_id == temporada_id)
    
    if categoria_id:
        query = query.filter(Liga.categoria_id == categoria_id)
    
    # Obtener ligas
    ligas = query.all()
    
    # Obtener temporadas y categorías para los filtros
    temporadas = Temporada.query.filter_by(user_id=user_id).all()
    categorias = Categoria.query.all()
    
    return render_template(
        "dashboard/ligas/index.html",
        username=username,
        ligas=ligas,
        temporadas=temporadas,
        categorias=categorias,
        temporada_id=temporada_id,
        categoria_id=categoria_id
    )

@liga_routes.route('/<username>/liga/nueva', methods=['GET', 'POST'])
def nueva_liga(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')
    
    user_id = session['user_id']
    temporada_id = request.args.get('temporada_id')
    
    # Obtener todas las temporadas del usuario
    temporadas = Temporada.query.filter_by(user_id=user_id).all()
    if not temporadas:
        flash("Debes crear al menos una temporada antes de crear una liga", "error")
        return redirect(f"/{username}/temporadas")
    
    if request.method == 'POST':
        data = request.form
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        temporada_id = data.get('temporada_id')
        categoria_id = data.get('categoria_id')
        
        # Verificar que la temporada pertenece al usuario
        temporada = Temporada.query.filter_by(id=temporada_id, user_id=user_id).first()
        if not temporada:
            flash("Temporada no válida", "error")
            return render_template(
                "dashboard/ligas/create.html", 
                username=username, 
                temporadas=temporadas,
                temporada_id=temporada_id,
                categorias=Categoria.query.all()
            )

        # Verificar si ya existe una liga con el mismo nombre en esta temporada
        existing_liga = Liga.query.filter_by(temporada_id=temporada_id, nombre=nombre).first()
        if existing_liga:
            flash("Ya existe una liga con este nombre en esta temporada", "error")
            return render_template(
                "dashboard/ligas/create.html", 
                username=username, 
                temporadas=temporadas,
                temporada_id=temporada_id,
                categorias=Categoria.query.all()
            )

        try:
            nueva_liga = Liga(
                temporada_id=temporada_id,
                categoria_id=categoria_id,
                nombre=nombre,
                descripcion=descripcion
            )
            db.session.add(nueva_liga)
            db.session.commit()
            flash("Liga creada con éxito", "success")
            return redirect(f"/{username}/temporada/{temporada_id}")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear la liga: {e}", "error")
            return render_template(
                "dashboard/ligas/create.html", 
                username=username, 
                temporadas=temporadas,
                temporada_id=temporada_id,
                categorias=Categoria.query.all()
            )

    categorias = Categoria.query.all()
    return render_template(
        "dashboard/ligas/create.html", 
        username=username, 
        temporadas=temporadas,
        temporada_id=temporada_id,
        categorias=categorias
    )

@liga_routes.route('/<username>/temporada/<int:temporada_id>/liga/nueva', methods=['GET', 'POST'])
def nueva_liga_temporada(username, temporada_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    temporada = Temporada.query.filter_by(id=temporada_id, user_id=session['user_id']).first()
    if not temporada:
        flash("Temporada no encontrada", "error")
        return redirect(f"/{username}/temporadas")
    
    # Redirigir a la ruta general con el parámetro de temporada
    return redirect(f"/{username}/liga/nueva?temporada_id={temporada_id}")

@liga_routes.route('/<username>/liga/<int:liga_id>/editar', methods=['GET', 'POST'])
def editar_liga(username, liga_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']
    liga = Liga.query.get_or_404(liga_id)
    
    # Verificar que la liga pertenece al usuario a través de la temporada
    temporada = Temporada.query.get_or_404(liga.temporada_id)
    if temporada.user_id != user_id:
        flash("No tienes permiso para editar esta liga", "error")
        return redirect(f"/{username}/ligas")

    # Obtener todas las temporadas del usuario
    temporadas = Temporada.query.filter_by(user_id=user_id).all()

    if request.method == 'POST':
        data = request.form
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        temporada_id = data.get('temporada_id')
        categoria_id = data.get('categoria_id')
        
        # Verificar que la nueva temporada pertenece al usuario
        nueva_temporada = Temporada.query.filter_by(id=temporada_id, user_id=user_id).first()
        if not nueva_temporada:
            flash("Temporada no válida", "error")
            return render_template(
                "dashboard/ligas/edit.html", 
                username=username, 
                liga=liga, 
                temporadas=temporadas,
                categorias=Categoria.query.all()
            )

        # Verificar si ya existe otra liga con el mismo nombre en esta temporada
        existing_liga = Liga.query.filter(
            Liga.temporada_id == temporada_id,
            Liga.nombre == nombre,
            Liga.id != liga_id
        ).first()
        
        if existing_liga:
            flash("Ya existe una liga con este nombre en esta temporada", "error")
            return render_template(
                "dashboard/ligas/edit.html", 
                username=username, 
                liga=liga, 
                temporadas=temporadas,
                categorias=Categoria.query.all()
            )

        try:
            liga.nombre = nombre
            liga.descripcion = descripcion
            liga.temporada_id = temporada_id
            liga.categoria_id = categoria_id
            db.session.commit()
            flash("Liga actualizada con éxito", "success")
            return redirect(f"/{username}/liga/{liga_id}")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar la liga: {e}", "error")
            return render_template(
                "dashboard/ligas/edit.html", 
                username=username, 
                liga=liga, 
                temporadas=temporadas,
                categorias=Categoria.query.all()
            )

    categorias = Categoria.query.all()
    return render_template(
        "dashboard/ligas/edit.html", 
        username=username, 
        liga=liga, 
        temporadas=temporadas,
        categorias=categorias
    )

@liga_routes.route('/<username>/liga/<int:liga_id>', methods=['GET'])
def ver_liga(username, liga_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    liga = Liga.query.get_or_404(liga_id)
    temporada = Temporada.query.get_or_404(liga.temporada_id)
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para ver esta liga", "error")
        return redirect(f"/{username}/ligas")

    # Obtener equipos de la liga
    equipos_liga = EquipoLiga.query.filter_by(liga_id=liga_id).all()
    equipos = [el.equipo for el in equipos_liga]
    
    # Obtener partidos de la liga
    partidos = liga.partidos

    return render_template(
        "dashboard/ligas/view.html", 
        username=username, 
        liga=liga, 
        temporada=temporada, 
        equipos=equipos, 
        partidos=partidos
    )

@liga_routes.route('/<username>/liga/<int:liga_id>/eliminar', methods=['POST'])
def eliminar_liga(username, liga_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    liga = Liga.query.get_or_404(liga_id)
    temporada = Temporada.query.get_or_404(liga.temporada_id)
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para eliminar esta liga", "error")
        return redirect(f"/{username}/ligas")

    temporada_id = liga.temporada_id
    
    try:
        db.session.delete(liga)
        db.session.commit()
        flash("Liga eliminada con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar la liga: {e}", "error")

    return redirect(f"/{username}/temporada/{temporada_id}")

@liga_routes.route('/<username>/liga/<int:liga_id>/agregar_equipo', methods=['GET', 'POST'])
def agregar_equipo_liga(username, liga_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    liga = Liga.query.get_or_404(liga_id)
    temporada = Temporada.query.get_or_404(liga.temporada_id)
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para modificar esta liga", "error")
        return redirect(f"/{username}/ligas")

    if request.method == 'POST':
        equipo_id = request.form.get('equipo_id')
        
        # Verificar si el equipo ya está en la liga
        existing = EquipoLiga.query.filter_by(liga_id=liga_id, equipo_id=equipo_id).first()
        if existing:
            flash("Este equipo ya está en la liga", "error")
        else:
            try:
                nuevo_equipo_liga = EquipoLiga(
                    liga_id=liga_id,
                    equipo_id=equipo_id
                )
                db.session.add(nuevo_equipo_liga)
                db.session.commit()
                flash("Equipo agregado a la liga con éxito", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Error al agregar el equipo a la liga: {e}", "error")
        
        return redirect(f"/{username}/liga/{liga_id}")

    # Obtener equipos que no están en la liga y pertenecen al usuario actual
    equipos_en_liga = db.session.query(EquipoLiga.equipo_id).filter_by(liga_id=liga_id).subquery()
    equipos_disponibles = Equipo.query.filter(
        ~Equipo.id.in_(equipos_en_liga),
        Equipo.user_id == session['user_id']
    ).all()

    return render_template(
        "dashboard/ligas/agregar_equipo.html", 
        username=username, 
        liga=liga, 
        temporada=temporada, 
        equipos=equipos_disponibles
    )

@liga_routes.route('/<username>/liga/<int:liga_id>/eliminar_equipo/<int:equipo_id>', methods=['POST'])
def eliminar_equipo_liga(username, liga_id, equipo_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    liga = Liga.query.get_or_404(liga_id)
    temporada = Temporada.query.get_or_404(liga.temporada_id)
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para modificar esta liga", "error")
        return redirect(f"/{username}/ligas")

    equipo_liga = EquipoLiga.query.filter_by(liga_id=liga_id, equipo_id=equipo_id).first()
    if not equipo_liga:
        flash("Este equipo no está en la liga", "error")
    else:
        try:
            db.session.delete(equipo_liga)
            db.session.commit()
            flash("Equipo eliminado de la liga con éxito", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al eliminar el equipo de la liga: {e}", "error")
    
    return redirect(f"/{username}/liga/{liga_id}")
