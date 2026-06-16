from flask import Blueprint, request, jsonify, render_template, session, redirect, flash
from models import db, Equipo, Jugador, Posicion, EquipoLiga, Liga, Categoria, Temporada

equipo_routes = Blueprint('equipo_routes', __name__)

@equipo_routes.route('/<username>/equipos', methods=['GET'])
def ver_equipos(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    # Obtener filtros
    tipo = request.args.get('tipo')
    liga_id = request.args.get('liga_id')

    # Obtener el ID del usuario actual
    user_id = session['user_id']
    
    # Obtener solo las ligas del usuario actual para el filtro
    ligas = Liga.query.join(Temporada).filter(Temporada.user_id == user_id).all()
    
    # Obtener TODOS los equipos del usuario actual
    equipos_query = Equipo.query.filter(Equipo.user_id == user_id)
    
    # Aplicar filtro de tipo si existe
    if tipo:
        equipos_query = equipos_query.filter(Equipo.tipo == tipo)
    
    # Si hay filtro de liga, filtrar por equipos que están en esa liga específica
    if liga_id:
        equipos_query = equipos_query.join(EquipoLiga).join(Liga).filter(
            Liga.id == int(liga_id)
        )
    
    equipos = equipos_query.all()
    
    # Obtener las ligas para cada equipo (solo las del usuario actual)
    equipos_con_ligas = []
    for equipo in equipos:
        ligas_equipo = db.session.query(Liga).join(EquipoLiga).join(Temporada).filter(
            EquipoLiga.equipo_id == equipo.id,
            Temporada.user_id == user_id
        ).all()
        
        equipos_con_ligas.append({
            'equipo': equipo,
            'ligas': ligas_equipo
        })

    return render_template(
        "dashboard/equipos/index.html",
        username=username,
        equipos_con_ligas=equipos_con_ligas,
        tipo=tipo,
        ligas=ligas,
        liga_id=liga_id
    )

@equipo_routes.route('/<username>/equipos/nuevo', methods=['GET', 'POST'])
def nuevo_equipo(username):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    if request.method == 'POST':
        data = request.form
        nombre = data.get('nombre')
        tipo = data.get('tipo')
        
        # Verificar si ya existe un equipo con el mismo nombre para este usuario
        user_id = session['user_id']
        existing_equipo = Equipo.query.filter(
            Equipo.user_id == user_id,
            Equipo.nombre == nombre
        ).first()
        
        if existing_equipo:
            flash("Ya tienes un equipo con este nombre", "error")
            return render_template("dashboard/equipos/create.html", username=username)

        try:
            nuevo_equipo = Equipo(
                user_id=user_id,  # Asignar el ID del usuario actual
                nombre=nombre,
                tipo=tipo
            )
            db.session.add(nuevo_equipo)
            db.session.commit()
            flash("Equipo creado exitosamente", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear el equipo: {e}", "error")

        return redirect(f"/{username}/equipos")

    return render_template("dashboard/equipos/create.html", username=username)

@equipo_routes.route('/<username>/equipo/<int:equipo_id>/editar', methods=['POST'])
def editar_equipo(username, equipo_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']
    
    # Verificar que el equipo pertenece al usuario actual
    equipo = Equipo.query.filter(
        Equipo.id == equipo_id,
        Equipo.user_id == user_id
    ).first()
    
    if not equipo:
        flash("Equipo no encontrado o no tienes permisos para editarlo", "error")
        return redirect(f"/{username}/equipos")
    
    # Obtener datos del formulario
    nombre = request.form.get('nombre')
    tipo = request.form.get('tipo')
    
    # Validar que el nombre no esté vacío
    if not nombre:
        flash("El nombre del equipo no puede estar vacío", "error")
        return redirect(f"/{username}/equipos")
    
    try:
        # Verificar si ya existe un equipo con ese nombre para este usuario (excepto el actual)
        equipo_existente = Equipo.query.filter(
            Equipo.nombre == nombre,
            Equipo.id != equipo_id,
            Equipo.user_id == user_id
        ).first()
        
        if equipo_existente:
            flash(f"Ya tienes un equipo con el nombre '{nombre}'", "error")
            return redirect(f"/{username}/equipos")
        
        # Actualizar el equipo
        equipo.nombre = nombre
        equipo.tipo = tipo
        db.session.commit()
        flash("Equipo actualizado con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar el equipo: {e}", "error")
    
    return redirect(f"/{username}/equipo/{equipo_id}")

@equipo_routes.route('/<username>/equipo/<int:equipo_id>', methods=['GET', 'POST'])
def ver_equipo(username, equipo_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']
    
    # Verificar que el equipo pertenece al usuario actual
    equipo = Equipo.query.filter(
        Equipo.id == equipo_id,
        Equipo.user_id == user_id
    ).first()
    
    if not equipo:
        flash("Equipo no encontrado o no tienes permisos para verlo", "error")
        return redirect(f"/{username}/equipos")

    jugadores = Jugador.query.filter_by(equipo_id=equipo_id).order_by(
        db.case((Jugador.rol == 'entrenador', 0), else_=1),  # Entrenadores primero
        Jugador.dorsal
    ).all()
    
    # Obtener todas las posiciones para los dropdowns
    posiciones = Posicion.query.all()
    
    # Obtener solo las ligas del usuario actual en las que participa el equipo
    ligas_equipo = db.session.query(Liga).join(EquipoLiga).join(Temporada).filter(
        EquipoLiga.equipo_id == equipo_id,
        Temporada.user_id == user_id
    ).all()

    if request.method == 'POST':
        # Agregar un nuevo jugador
        data = request.form
        rol = data.get('rol')

        # Validar que el dorsal sea obligatorio solo si no es un entrenador
        dorsal = data.get('dorsal')
        if rol != 'entrenador' and (not dorsal or not dorsal.isdigit()):
            flash('El dorsal es obligatorio para jugadores.', 'error')
            return redirect(f'/{username}/equipo/{equipo_id}')

        nuevo_jugador = Jugador(
            nombre=data.get('nombre'),
            apellido=data.get('apellido'),
            dorsal=int(dorsal) if dorsal else None,
            rol=rol,
            es_capitan=True if data.get('es_capitan') else False,
            posicion_id=data.get('posicion_id') if data.get('posicion_id') else None,
            equipo_id=equipo_id
        )
        try:
            db.session.add(nuevo_jugador)
            db.session.commit()
            flash('Jugador añadido con éxito', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al añadir jugador: {e}', 'error')

        return redirect(f'/{username}/equipo/{equipo_id}')

    return render_template(
        "dashboard/equipos/view.html", 
        username=username, 
        equipo=equipo, 
        jugadores=jugadores, 
        posiciones=posiciones,
        ligas=ligas_equipo
    )

@equipo_routes.route('/<username>/equipo/<int:equipo_id>/jugadores/actualizar', methods=['POST'])
def actualizar_jugadores(username, equipo_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Verificar que el equipo pertenece al usuario actual
    equipo = Equipo.query.filter(
        Equipo.id == equipo_id,
        Equipo.user_id == user_id
    ).first()
    
    if not equipo:
        flash("Equipo no encontrado o no tienes permisos para editarlo", "error")
        return redirect(f"/{username}/equipos")
        
    # Obtener todos los jugadores del equipo
    jugadores = Jugador.query.filter_by(equipo_id=equipo_id).all()
    
    try:
        # Actualizar cada jugador con los datos del formulario
        for jugador in jugadores:
            jugador_id = jugador.id
            
            # Obtener los datos del formulario para este jugador
            nombre = request.form.get(f'nombre_{jugador_id}')
            apellido = request.form.get(f'apellido_{jugador_id}')
            dorsal = request.form.get(f'dorsal_{jugador_id}')
            rol = request.form.get(f'rol_{jugador_id}')
            es_capitan = True if request.form.get(f'es_capitan_{jugador_id}') else False
            posicion_id = request.form.get(f'posicion_id_{jugador_id}')
            
            # Actualizar el jugador
            jugador.nombre = nombre
            jugador.apellido = apellido
            jugador.dorsal = int(dorsal) if dorsal and dorsal.strip() else None
            jugador.rol = rol
            jugador.es_capitan = es_capitan
            jugador.posicion_id = posicion_id if posicion_id else None
        
        # Guardar todos los cambios
        db.session.commit()
        flash('Todos los jugadores actualizados con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al actualizar jugadores: {e}', 'error')
    
    return redirect(f'/{username}/equipo/{equipo_id}')

@equipo_routes.route('/<username>/equipo/<int:equipo_id>/eliminar', methods=['POST'])
def eliminar_equipo(username, equipo_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']
    
    # Verificar que el equipo pertenece al usuario actual
    equipo = Equipo.query.filter(
        Equipo.id == equipo_id,
        Equipo.user_id == user_id
    ).first()
    
    if not equipo:
        flash("Equipo no encontrado o no tienes permisos para eliminarlo", "error")
        return redirect(f"/{username}/equipos")

    try:
        # Eliminar las relaciones con ligas
        EquipoLiga.query.filter_by(equipo_id=equipo_id).delete()
        
        # Eliminar los jugadores asociados
        Jugador.query.filter_by(equipo_id=equipo_id).delete()
        
        # Eliminar el equipo
        db.session.delete(equipo)
        
        db.session.commit()
        flash('Equipo eliminado con éxito', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el equipo: {e}', 'error')

    return redirect(f'/{username}/equipos')

@equipo_routes.route('/<username>/equipo/<int:equipo_id>/jugador/<int:jugador_id>/eliminar', methods=['POST'])
def eliminar_jugador(username, equipo_id, jugador_id):
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']
    
    # Verificar que el equipo pertenece al usuario actual
    equipo = Equipo.query.filter(
        Equipo.id == equipo_id,
        Equipo.user_id == user_id
    ).first()
    
    if not equipo:
        return 'No tienes permisos para realizar esta acción', 403

    jugador = Jugador.query.get_or_404(jugador_id)

    try:
        db.session.delete(jugador)
        db.session.commit()
        return '', 200  # Respuesta vacía para JavaScript
    except Exception as e:
        db.session.rollback()
        return str(e), 400
