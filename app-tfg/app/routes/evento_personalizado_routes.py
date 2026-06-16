from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from models import db, EventoPersonalizado, CategoriaEvento, EventosSeleccionadosVideo, Video
from sqlalchemy import and_

evento_personalizado_routes = Blueprint('evento_personalizado_routes', __name__)

@evento_personalizado_routes.route('/<username>/eventos-personalizados')
def listar_eventos_personalizados(username):
    """Listar todos los eventos personalizados del usuario"""
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('user_routes.login'))
    
    user_id = session['user_id']
    
    # Obtener eventos personalizados del usuario
    eventos_personalizados = EventoPersonalizado.query.filter_by(user_id=user_id).all()
    
    # Obtener categorías disponibles
    categorias = CategoriaEvento.query.all()
    
    return render_template('dashboard/eventos_personalizados/index.html', 
                         username=username,
                         eventos_personalizados=eventos_personalizados,
                         categorias=categorias)

@evento_personalizado_routes.route('/<username>/eventos-personalizados/nuevo', methods=['GET', 'POST'])
def crear_evento_personalizado(username):
    """Crear un nuevo evento personalizado"""
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('user_routes.login'))
    
    if request.method == 'POST':
        try:
            user_id = session['user_id']
            nombre = request.form.get('nombre', '').strip()
            categoria_id = request.form.get('categoria_id')
            
            # Validaciones
            if not nombre:
                flash('El nombre del evento es requerido', 'error')
                return redirect(request.url)
            
            if not categoria_id:
                flash('La categoría es requerida', 'error')
                return redirect(request.url)
            
            # Verificar que la categoría existe
            categoria = CategoriaEvento.query.get(categoria_id)
            if not categoria:
                flash('Categoría no válida', 'error')
                return redirect(request.url)
            
            # Verificar que no existe un evento con el mismo nombre para este usuario
            evento_existente = EventoPersonalizado.query.filter_by(
                user_id=user_id,
                nombre=nombre
            ).first()
            
            if evento_existente:
                flash('Ya tienes un evento personalizado con ese nombre', 'error')
                return redirect(request.url)
            
            # Asignar tipos según la categoría
            es_equipo = categoria.nombre.lower() == 'táctica'
            es_global = categoria.nombre.lower() == 'global'
            es_jugador = not (es_equipo or es_global)
            
            estadistica_tipo = request.form.get('estadistica_tipo')
            # Si está vacío, convertir a None
            if estadistica_tipo == '':
                estadistica_tipo = None
            
            # Crear el evento personalizado
            evento = EventoPersonalizado(
                user_id=user_id,
                categoria_evento_id=int(categoria_id),
                nombre=nombre,
                es_equipo=es_equipo,
                es_global=es_global,
                es_jugador=es_jugador,
                estadistica_tipo=estadistica_tipo
            )
            
            db.session.add(evento)
            db.session.commit()
            flash('Evento personalizado creado exitosamente', 'success')
            return redirect(url_for('evento_personalizado_routes.listar_eventos_personalizados', username=username))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al crear el evento personalizado: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET request - mostrar formulario
    categorias = CategoriaEvento.query.all()
    return render_template('dashboard/eventos_personalizados/create.html', 
                         username=username, 
                         categorias=categorias)

@evento_personalizado_routes.route('/<username>/eventos-personalizados/<int:evento_id>/eliminar', methods=['POST'])
def eliminar_evento_personalizado(username, evento_id):
    """Eliminar un evento personalizado"""
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('user_routes.login'))
    
    user_id = session['user_id']
    evento = EventoPersonalizado.query.filter_by(id=evento_id, user_id=user_id).first()
    
    if not evento:
        flash('Evento no encontrado', 'error')
        return redirect(url_for('evento_personalizado_routes.listar_eventos_personalizados', username=username))
    
    try:
        # Eliminar referencias en eventos_seleccionados_video
        EventosSeleccionadosVideo.query.filter_by(
            evento_personalizado_id=evento_id,
            user_id=user_id
        ).delete()
        
        # Eliminar el evento
        db.session.delete(evento)
        db.session.commit()
        flash('Evento personalizado eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el evento personalizado', 'error')
    
    return redirect(url_for('evento_personalizado_routes.listar_eventos_personalizados', username=username))

@evento_personalizado_routes.route('/<username>/video/<int:video_id>/configurar-eventos')
def configurar_eventos_video(username, video_id):
    """Configurar eventos para un video específico"""
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('user_routes.login'))
    
    user_id = session['user_id']
    video = Video.query.get_or_404(video_id)
    
    # Verificar que el video pertenece al usuario
    if video.partido.temporada.user_id != user_id:
        flash('No tienes permisos para acceder a este video', 'error')
        return redirect(url_for('video_routes.listar_videos', username=username))
    
    # Obtener el partido del video
    partido = video.partido
    
    # Obtener eventos ya seleccionados para este video
    eventos_seleccionados = EventosSeleccionadosVideo.query.filter_by(
        video_id=video_id, 
        user_id=user_id
    ).all()
    
    # Crear listas de IDs seleccionados
    estandar_seleccionados = [e.tipo_evento_id for e in eventos_seleccionados if e.tipo_evento_id]
    personalizados_seleccionados = [e.evento_personalizado_id for e in eventos_seleccionados if e.evento_personalizado_id]
    
    # Obtener eventos personalizados del usuario
    eventos_personalizados = EventoPersonalizado.query.filter_by(user_id=user_id).all()
    
    # Obtener categorías
    categorias = CategoriaEvento.query.all()
    
    # Obtener eventos base organizados por categoría
    from models import TipoEvento
    eventos_por_categoria = {}

    for categoria in categorias:
        eventos_base = TipoEvento.query.filter_by(categoria_evento_id=categoria.id).all()
        
        # Marcar eventos como seleccionados
        for evento in eventos_base:
            evento.seleccionado = evento.id in estandar_seleccionados
        
        eventos_por_categoria[categoria.nombre] = {
            'eventos_base': eventos_base,
            'categoria': categoria
        }

    # Debug: imprimir información para verificar
    print(f"Categorías encontradas: {[c.nombre for c in categorias]}")
    for cat_nombre, datos in eventos_por_categoria.items():
        print(f"Categoría {cat_nombre}: {len(datos['eventos_base'])} eventos")
        for evento in datos['eventos_base']:
            print(f"  - {evento.nombre} (ID: {evento.id})")
    
    return render_template('dashboard/eventos_personalizados/configurar_video.html',
                         username=username,
                         video=video,
                         partido=partido,
                         eventos_seleccionados=eventos_seleccionados,
                         eventos_personalizados=eventos_personalizados,
                         categorias=categorias,
                         eventos_por_categoria=eventos_por_categoria,
                         personalizados_seleccionados=personalizados_seleccionados)

@evento_personalizado_routes.route('/<username>/video/<int:video_id>/guardar-eventos', methods=['POST'])
def guardar_eventos_video(username, video_id):
    """Guardar la configuración de eventos para un video"""
    if 'username' not in session or session['username'] != username:
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    user_id = session['user_id']
    video = Video.query.get_or_404(video_id)
    
    # Verificar que el video pertenece al usuario
    if video.partido.temporada.user_id != user_id:
        return jsonify({'success': False, 'message': 'No tienes permisos para este video'})
    
    try:
        # Eliminar configuración anterior
        deleted_count = EventosSeleccionadosVideo.query.filter_by(
            video_id=video_id, 
            user_id=user_id
        ).delete()
        print(f"Eliminados {deleted_count} eventos anteriores")
        
        # Obtener eventos seleccionados del formulario
        eventos_estandar = request.form.getlist('eventos_estandar')
        eventos_personalizados = request.form.getlist('eventos_personalizados')
        
        print(f"Eventos estándar seleccionados: {eventos_estandar}")
        print(f"Eventos personalizados seleccionados: {eventos_personalizados}")
        
        # Guardar eventos estándar seleccionados
        for tipo_evento_id in eventos_estandar:
            evento_seleccionado = EventosSeleccionadosVideo(
                video_id=video_id,
                user_id=user_id,
                tipo_evento_id=int(tipo_evento_id)
            )
            db.session.add(evento_seleccionado)
            print(f"Añadido evento estándar: {tipo_evento_id}")
        
        # Guardar eventos personalizados seleccionados
        for evento_personalizado_id in eventos_personalizados:
            evento_seleccionado = EventosSeleccionadosVideo(
                video_id=video_id,
                user_id=user_id,
                evento_personalizado_id=int(evento_personalizado_id)
            )
            db.session.add(evento_seleccionado)
            print(f"Añadido evento personalizado: {evento_personalizado_id}")
        
        db.session.commit()
        print("Configuración guardada exitosamente en la base de datos")
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Configuración guardada exitosamente'})
        else:
            flash('Configuración de eventos guardada exitosamente', 'success')
            return redirect(url_for('video_routes.ver_video', username=username, video_id=video_id))
            
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar configuración: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error al guardar la configuración: {str(e)}'})
        else:
            flash(f'Error al guardar la configuración de eventos: {str(e)}', 'error')
            return redirect(url_for('evento_personalizado_routes.configurar_eventos_video', 
                               username=username, video_id=video_id))

@evento_personalizado_routes.route('/<username>/eventos-personalizados/<int:evento_id>/editar', methods=['GET', 'POST'])
def editar_evento_personalizado(username, evento_id):
    """Editar un evento personalizado"""
    if 'username' not in session or session['username'] != username:
        return redirect(url_for('user_routes.login'))
    
    user_id = session['user_id']
    evento = EventoPersonalizado.query.filter_by(id=evento_id, user_id=user_id).first()
    
    if not evento:
        flash('Evento no encontrado', 'error')
        return redirect(url_for('evento_personalizado_routes.listar_eventos_personalizados', username=username))
    
    if request.method == 'POST':
        try:
            nombre = request.form.get('nombre', '').strip()
            categoria_id = request.form.get('categoria_id')
            estadistica_tipo = request.form.get('estadistica_tipo')
            
            # Si está vacío, convertir a None
            if estadistica_tipo == '':
                estadistica_tipo = None
            
            # Validaciones
            if not nombre:
                flash('El nombre del evento es requerido', 'error')
                return redirect(request.url)
            
            if not categoria_id:
                flash('La categoría es requerida', 'error')
                return redirect(request.url)
            
            # Verificar que la categoría existe
            categoria = CategoriaEvento.query.get(categoria_id)
            if not categoria:
                flash('Categoría no válida', 'error')
                return redirect(request.url)
            
            # Verificar que no existe otro evento con el mismo nombre para este usuario
            evento_existente = EventoPersonalizado.query.filter_by(
                user_id=user_id,
                nombre=nombre
            ).filter(EventoPersonalizado.id != evento_id).first()
            
            if evento_existente:
                flash('Ya tienes un evento personalizado con ese nombre', 'error')
                return redirect(request.url)
            
            # Asignar tipos según la categoría
            es_equipo = categoria.nombre.lower() == 'táctica'
            es_global = categoria.nombre.lower() == 'global'
            es_jugador = not (es_equipo or es_global)
            
            # Actualizar el evento
            evento.nombre = nombre
            evento.categoria_evento_id = int(categoria_id)
            evento.es_equipo = es_equipo
            evento.es_global = es_global
            evento.es_jugador = es_jugador
            evento.estadistica_tipo = estadistica_tipo
            
            db.session.commit()
            flash('Evento personalizado actualizado exitosamente', 'success')
            return redirect(url_for('evento_personalizado_routes.listar_eventos_personalizados', username=username))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar el evento personalizado: {str(e)}', 'error')
            return redirect(request.url)
    
    # GET request - mostrar formulario
    categorias = CategoriaEvento.query.all()
    return render_template('dashboard/eventos_personalizados/edit.html', 
                         username=username, 
                         evento=evento,
                         categorias=categorias)

@evento_personalizado_routes.route('/<username>/video/<int:video_id>/eventos-disponibles')
def obtener_eventos_disponibles(username, video_id):
    """API para obtener eventos disponibles para un video organizados por categorías"""
    if 'username' not in session or session['username'] != username:
        return jsonify({'success': False, 'message': 'No autorizado'})
    
    user_id = session['user_id']
    
    # Obtener eventos seleccionados para este video
    eventos_seleccionados = EventosSeleccionadosVideo.query.filter_by(
        video_id=video_id,
        user_id=user_id
    ).all()
    
    # Obtener todas las categorías
    categorias = CategoriaEvento.query.all()
    
    # Organizar eventos por categorías
    categorias_con_eventos = []
    
    for categoria in categorias:
        tipos_evento = []
        
        # Obtener eventos estándar de esta categoría que están seleccionados
        for evento_sel in eventos_seleccionados:
            if evento_sel.tipo_evento_id:
                tipo_evento = evento_sel.tipo_evento
                if tipo_evento and tipo_evento.categoria_evento_id == categoria.id:
                    tipos_evento.append({
                        'id': tipo_evento.id,
                        'nombre': tipo_evento.nombre,
                        'tipo_asignacion': 'jugador' if tipo_evento.es_jugador else ('equipo' if tipo_evento.es_equipo else 'global'),
                        'es_equipo': tipo_evento.es_equipo,
                        'es_global': tipo_evento.es_global,
                        'es_jugador': tipo_evento.es_jugador,
                        'tipo': 'estandar'
                    })
        
        # Obtener eventos personalizados de esta categoría que están seleccionados
        for evento_sel in eventos_seleccionados:
            if evento_sel.evento_personalizado_id:
                evento_personalizado = evento_sel.evento_personalizado
                if evento_personalizado and evento_personalizado.categoria_evento_id == categoria.id:
                    tipos_evento.append({
                        'id': f'personalizado_{evento_personalizado.id}',
                        'nombre': evento_personalizado.nombre,
                        'tipo_asignacion': 'jugador' if evento_personalizado.es_jugador else ('equipo' if evento_personalizado.es_equipo else 'global'),
                        'es_equipo': evento_personalizado.es_equipo,
                        'es_global': evento_personalizado.es_global,
                        'es_jugador': evento_personalizado.es_jugador,
                        'tipo': 'personalizado'
                    })
        
        # Solo añadir la categoría si tiene eventos
        if tipos_evento:
            categorias_con_eventos.append({
                'id': categoria.id,
                'nombre': categoria.nombre,
                'icono': f'fa-{categoria.nombre.lower()}',  # Icono por defecto
                'tipos_evento': tipos_evento
            })
    
    
    
    return jsonify(categorias_con_eventos)
