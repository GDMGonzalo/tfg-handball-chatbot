from flask import Blueprint, request, jsonify, session, redirect, flash, render_template
from models import db, Evento, TipoEvento, Video, Partido, Temporada, Equipo, Jugador, CategoriaEvento, JugadorEnPista, Posicion, EventoPersonalizado, EventosSeleccionadosVideo

evento_routes = Blueprint('evento_routes', __name__)

@evento_routes.route('/<username>/video/<int:video_id>/evento/nuevo', methods=['POST'])
def crear_evento(username, video_id):
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.json
    video = Video.query.get_or_404(video_id)
    partido = video.partido
    temporada = partido.temporada

    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401

    try:
        print("Datos recibidos:", data)
        tiempo_seg = data.get('tiempo')
        jugador_id = data.get('jugador_id')
        equipo_tipo = data.get('equipo_tipo')
        descripcion = data.get('descripcion', '')

        # Campos específicos para eventos de tiro
        zona_tiro = data.get('zona_tiro')
        resultado_tiro = data.get('resultado_tiro')

        # Verificar si es evento base o personalizado
        tipo_evento_id = data.get('tipo_evento_id')
        evento_personalizado_id = data.get('evento_personalizado_id')

        if not tipo_evento_id and not evento_personalizado_id:
            return jsonify({'error': 'Debe especificar un tipo de evento o evento personalizado'}), 400

        if tipo_evento_id and evento_personalizado_id:
            return jsonify({'error': 'No se puede especificar tanto tipo de evento como evento personalizado'}), 400

        if tiempo_seg is None:
            return jsonify({'error': 'El tiempo es requerido'}), 400

        # Obtener información del evento (base o personalizado)
        if tipo_evento_id:
            # Evento base
            tipo_evento = TipoEvento.query.get(tipo_evento_id)
            if not tipo_evento:
                return jsonify({'error': f'El tipo de evento con ID {tipo_evento_id} no existe'}), 400
            
            es_equipo = tipo_evento.es_equipo
            es_global = tipo_evento.es_global
            es_jugador = tipo_evento.es_jugador
            nombre_evento = tipo_evento.nombre
            
        else:
            # Evento personalizado
            evento_personalizado = EventoPersonalizado.query.filter_by(
                id=evento_personalizado_id,
                user_id=session['user_id']
            ).first()
            
            if not evento_personalizado:
                return jsonify({'error': f'El evento personalizado con ID {evento_personalizado_id} no existe o no te pertenece'}), 400
            
            es_equipo = evento_personalizado.es_equipo
            es_global = evento_personalizado.es_global
            es_jugador = evento_personalizado.es_jugador
            nombre_evento = evento_personalizado.nombre

        # Validaciones según el tipo de evento
        equipo_id = None
        if equipo_tipo == 'local':
            equipo_id = partido.equipo_local_id
        elif equipo_tipo == 'visitante':
            equipo_id = partido.equipo_visitante_id

        if es_equipo and not equipo_id:
            return jsonify({'error': 'Este tipo de evento requiere un equipo'}), 400

        if es_jugador and not jugador_id:
            return jsonify({'error': 'Este tipo de evento requiere un jugador'}), 400

        if jugador_id:
            jugador = Jugador.query.get(jugador_id)
            if not jugador:
                return jsonify({'error': f'Jugador con ID {jugador_id} no encontrado'}), 404
            if equipo_id and jugador.equipo_id != int(equipo_id):
                return jsonify({'error': 'El jugador no pertenece al equipo seleccionado'}), 400
            if not equipo_id:
                equipo_id = jugador.equipo_id

        # Crear el evento con el nuevo modelo
        nuevo_evento = Evento(
            video_id=video_id,
            tiempo_seg=tiempo_seg,
            partido_id=partido.id,
            equipo_id=equipo_id,
            jugador_id=jugador_id,
            descripcion=nombre_evento,
            zona_tiro = zona_tiro,
            resultado_tiro = resultado_tiro
        )
        
        # Asignar campos específicos de tiro si están presentes
        if zona_tiro:
            nuevo_evento.zona_tiro = zona_tiro
        if resultado_tiro:
            nuevo_evento.resultado_tiro = resultado_tiro
        
        # Asignar el tipo de evento según sea base o personalizado
        if tipo_evento_id:
            nuevo_evento.tipo_evento_id = tipo_evento_id
            nuevo_evento.evento_personalizado_id = None
        else:
            nuevo_evento.tipo_evento_id = None
            nuevo_evento.evento_personalizado_id = evento_personalizado_id
        
        db.session.add(nuevo_evento)
        db.session.commit()
        
        # Variable para almacenar el ID del evento estadístico generado (si se crea)
        evento_estadistico_id = None

        # Lógica para crear automáticamente eventos estadísticos para tiros parados
        es_tiro_parado = False
        es_7metros = False

        # Verificar si es un tiro parado
        if tipo_evento_id:
            # Para eventos de penaltis (7 metros) - ID específico
            if int(tipo_evento_id) == 15:  # Tiro parado 7 metros
                es_tiro_parado = True
                es_7metros = True
            # Para tiros normales - verificar resultado_tiro
            elif resultado_tiro and resultado_tiro.lower() == "parado":
                es_tiro_parado = True
                es_7metros = False

        if es_tiro_parado:
            # Determinar el equipo contrario
            equipo_contrario_id = None
            if equipo_id == partido.equipo_local_id:
                equipo_contrario_id = partido.equipo_visitante_id
            elif equipo_id == partido.equipo_visitante_id:
                equipo_contrario_id = partido.equipo_local_id
            
            if not equipo_contrario_id:
                print("No se pudo determinar el equipo contrario")
                return jsonify({
                    'success': True,
                    'evento_id': nuevo_evento.id,
                    'message': 'Evento registrado con éxito, pero no se pudo crear el evento estadístico automático'
                }), 201
            
            # Buscar un portero en pista del equipo contrario
            posicion_portero = Posicion.query.filter_by(nombre='Portero').first()
            
            if not posicion_portero:
                print("No se encontró la posición de Portero en la base de datos")
                return jsonify({
                    'success': True,
                    'evento_id': nuevo_evento.id,
                    'message': 'Evento registrado con éxito, pero no se pudo crear el evento estadístico automático'
                }), 201
            
            # Buscar jugadores en pista del equipo contrario que sean porteros
            porteros_en_pista = db.session.query(Jugador).join(
                JugadorEnPista, JugadorEnPista.jugador_id == Jugador.id
            ).filter(
                JugadorEnPista.partido_id == partido.id,
                JugadorEnPista.equipo_id == equipo_contrario_id,
                Jugador.posicion_id == posicion_portero.id
            ).all()
            
            if not porteros_en_pista:
                return jsonify({
                    'success': True,
                    'evento_id': nuevo_evento.id,
                    'warning': 'No se puede registrar el evento estadístico. Asigna un jugador con posición \'Portero\' al campo del equipo contrario.'
                }), 201
            
            # Tomar el primer portero encontrado
            portero = porteros_en_pista[0]
            
            # Determinar el tipo de evento estadístico a crear
            tipo_evento_estadistico_id = 29 if es_7metros else 28  # 29 para paradas de 7m, 28 para paradas normales
            
            # Crear descripción de la parada
            if es_7metros:
                descripcion_parada = "Parada de 7 metros (Portero)"
                zona_parada = "7m"
            else:
                descripcion_parada = f"Parada de {zona_tiro if zona_tiro else 'tiro'} (Portero)"
                zona_parada = zona_tiro
            
            # Crear el evento estadístico automático
            evento_estadistico = Evento(
                video_id=video_id,
                tiempo_seg=tiempo_seg,
                tipo_evento_id=tipo_evento_estadistico_id,
                evento_personalizado_id=None,
                partido_id=partido.id,
                equipo_id=equipo_contrario_id,
                jugador_id=portero.id,
                descripcion=descripcion_parada,
                zona_tiro=zona_parada,
                resultado_tiro="Parado"
            )
            
            db.session.add(evento_estadistico)
            db.session.commit()
            
            evento_estadistico_id = evento_estadistico.id
            print(f"Evento estadístico automático creado con ID {evento_estadistico_id} ({'7m' if es_7metros else 'normal'})")

        return jsonify({
            'success': True,
            'evento_id': nuevo_evento.id,
            'evento_estadistico_id': evento_estadistico_id,
            'message': 'Evento registrado con éxito'
        }), 201

    except Exception as e:
        db.session.rollback()
        print("Error al registrar evento:", str(e))
        return jsonify({'error': f'Error al registrar el evento: {str(e)}'}), 500


@evento_routes.route('/<username>/evento/<int:evento_id>/eliminar', methods=['POST'])
def eliminar_evento(username, evento_id):
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    try:
        evento = Evento.query.get_or_404(evento_id)
        video = Video.query.get_or_404(evento.video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        
        # Verificar que el partido pertenece a una liga y la liga a una temporada
        if not partido.liga:
            return jsonify({'error': 'El partido no está asociado a una liga'}), 400
        
        temporada = partido.liga.temporada

        if temporada.user_id != session['user_id']:
            return jsonify({'error': 'No autorizado'}), 401

        # Eliminar evento estadístico relacionado si aplica
        # Ahora verificamos si el resultado_tiro es "Parado" en lugar de verificar solo el tipo de evento
        es_tiro_parado = False
        
        # Verificar si es un tiro parado por resultado_tiro
        if hasattr(evento, 'resultado_tiro') and evento.resultado_tiro and evento.resultado_tiro.lower() == "parado":
            es_tiro_parado = True
        # Mantener compatibilidad con ID 15 (tiro 7m parado) si aún existe
        elif evento.tipo_evento_id == 15:
            es_tiro_parado = True

        if es_tiro_parado:
            # Buscar eventos estadísticos de parada en el mismo tiempo
            eventos_estadisticos = Evento.query.filter(
                Evento.video_id == evento.video_id,
                Evento.tiempo_seg == evento.tiempo_seg,
                Evento.tipo_evento_id.in_([28, 29])  # IDs para paradas normales y de 7m
            ).all()
            
            # Eliminar los eventos estadísticos encontrados
            for ev_estadistico in eventos_estadisticos:
                db.session.delete(ev_estadistico)

        # Eliminar el evento original
        db.session.delete(evento)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Evento eliminado con éxito'}), 200

    except Exception as e:
        db.session.rollback()
        print("Error al eliminar evento:", str(e))  # Depuración
        return jsonify({'error': f'Error al eliminar el evento: {str(e)}'}), 500


@evento_routes.route('/<username>/video/<int:video_id>/eventos', methods=['GET'])
def obtener_eventos(username, video_id):
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    try:
        print(f"Obteniendo eventos para el video {video_id} del usuario {username}")
        
        video = Video.query.get_or_404(video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        
        # Verificar que el partido pertenece a una temporada
        temporada = None
        if partido.liga:
            temporada = partido.liga.temporada
        else:
            temporada = Temporada.query.get_or_404(partido.temporada_id)
        
        if temporada.user_id != session['user_id']:
            return jsonify({'error': 'No autorizado'}), 401

        # Obtener todos los eventos asociados a este video, excluyendo los de la categoría Paradas (id=8)
        eventos = Evento.query.outerjoin(TipoEvento).filter(
            Evento.video_id == video_id,
            db.or_(
                TipoEvento.categoria_evento_id.is_(None),
                ~TipoEvento.categoria_evento_id.in_([8])  # Excluir eventos de la categoría Paradas
            )
        ).order_by(Evento.tiempo_seg).all()
        
        print(f"Se encontraron {len(eventos)} eventos (excluyendo categoría Paradas)")
        
        eventos_data = []
        
        for evento in eventos:
            #print(f"Procesando evento {evento.id} - tiempo: {evento.tiempo_seg}- evento: {evento.tipo_evento_id}")
            
            evento_data = {
                'id': evento.id,
                'tiempo_seg': evento.tiempo_seg,
                'tipo_evento_id': evento.tipo_evento_id,
                'evento_personalizado_id': evento.evento_personalizado_id,
                'descripcion': evento.descripcion,
                'partido_id': evento.partido_id,
                'video_id': evento.video_id,
                'zona_tiro': evento.zona_tiro,
                'resultado_tiro': evento.resultado_tiro,
            }
            
            # Añadir información del tipo de evento (base o personalizado)
            if evento.tipo_evento_id:
                try:
                    tipo_evento = TipoEvento.query.get(evento.tipo_evento_id)
                    if tipo_evento:
                        evento_data['tipo_evento'] = {
                            'id': tipo_evento.id,
                            'nombre': tipo_evento.nombre,
                            'categoria_id': tipo_evento.categoria_evento_id
                        }
                except Exception as e:
                    print(f"Error al obtener tipo de evento: {str(e)}")
            elif evento.evento_personalizado_id:
                try:
                    evento_personalizado = EventoPersonalizado.query.get(evento.evento_personalizado_id)
                    if evento_personalizado:
                        # Incluir toda la información del evento personalizado
                        evento_data['evento_personalizado'] = {
                            'id': evento_personalizado.id,
                            'nombre': evento_personalizado.nombre,
                            'categoria_id': evento_personalizado.categoria_evento_id,
                            'es_personalizado': True,
                            'estadistica_tipo': evento_personalizado.estadistica_tipo,
                            'es_equipo': evento_personalizado.es_equipo,
                            'es_global': evento_personalizado.es_global,
                            'es_jugador': evento_personalizado.es_jugador
                        }
                        
                        # También incluir en tipo_evento para mantener compatibilidad
                        evento_data['tipo_evento'] = {
                            'id': f"personalizado_{evento_personalizado.id}",
                            'nombre': evento_personalizado.nombre,
                            'categoria_id': evento_personalizado.categoria_evento_id,
                            'es_personalizado': True
                        }
                except Exception as e:
                    print(f"Error al obtener evento personalizado: {str(e)}")
            
            # Añadir información del equipo
            if evento.equipo_id:
                try:
                    equipo = Equipo.query.get(evento.equipo_id)
                    if equipo:
                        evento_data['equipo'] = {
                            'id': equipo.id,
                            'nombre': equipo.nombre
                        }
                except Exception as e:
                    print(f"Error al obtener equipo: {str(e)}")
            
            # Añadir información del jugador
            if evento.jugador_id:
                try:
                    jugador = Jugador.query.get(evento.jugador_id)
                    if jugador:
                        evento_data['jugador'] = {
                            'id': jugador.id,
                            'nombre': jugador.nombre,
                            'apellido': jugador.apellido,
                            'dorsal': jugador.dorsal
                        }
                except Exception as e:
                    print(f"Error al obtener jugador: {str(e)}")
            
            eventos_data.append(evento_data)
        
        return jsonify({'success': True, 'eventos': eventos_data}), 200
    
    except Exception as e:
        print(f"Error al obtener eventos: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al obtener eventos: {str(e)}'}), 500


# Nuevas rutas para categorías y tipos de eventos
@evento_routes.route('/<username>/categorias_eventos', methods=['GET'])
def get_event_categories(username):
    """Obtener todas las categorías de eventos"""
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401
        
    try:
        categorias = CategoriaEvento.query.all()
        
        # Mapear iconos para cada categoría
        iconos = {
            'Tiro': 'fa-basketball-ball',
            'Falta': 'fa-hand-paper',
            'Sanción': 'fa-exclamation-triangle',
            'Sustitución': 'fa-exchange-alt',
            'Global': 'fa-globe',
            'Táctica': 'fa-chalkboard-teacher',
            'Penaltis': 'fa-bullseye',
            'Paradas': 'fa-hand-paper',
            'Perdidas': 'fa-times',
            'Defensa': 'fa-shield-alt',  
            'Asistencias': 'fa-hands-helping'  
        }
        
        result = []
        for categoria in categorias:
            icono = iconos.get(categoria.nombre, 'fa-circle')
            result.append({
                'id': categoria.id,
                'nombre': categoria.nombre,
                'icono': icono
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error al obtener categorías de eventos: {str(e)}")
        return jsonify([])

@evento_routes.route('/<username>/tipos_eventos', methods=['GET'])
def get_event_types(username):
    """Obtener tipos de eventos por categoría"""
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401
        
    try:
        categoria_id = request.args.get('categoria_id', type=int)
        if not categoria_id:
            return jsonify([])
        
        tipos = TipoEvento.query.filter_by(categoria_evento_id=categoria_id).all()
        
        result = []
        for tipo in tipos:
            result.append({
                'id': tipo.id,
                'nombre': tipo.nombre,
                'es_equipo': tipo.es_equipo,
                'es_global': tipo.es_global,
                'es_jugador': tipo.es_jugador
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error al obtener tipos de eventos: {str(e)}")
        return jsonify([])

@evento_routes.route('/<username>/video/<int:video_id>/eventos-disponibles', methods=['GET'])
def obtener_eventos_disponibles(username, video_id):
    """Obtener eventos disponibles para un video específico (solo los seleccionados)"""
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401
        
    try:
        print(f"Obteniendo eventos disponibles para video {video_id}")
        
        # Verificar que el video pertenece al usuario
        video = Video.query.get_or_404(video_id)
        partido = video.partido
        temporada = None
        if partido.liga:
            temporada = partido.liga.temporada
        else:
            temporada = Temporada.query.get_or_404(partido.temporada_id)
        
        if temporada.user_id != session['user_id']:
            return jsonify({'error': 'No autorizado'}), 401

        # Obtener los eventos seleccionados para este video
        eventos_seleccionados = EventosSeleccionadosVideo.query.filter_by(video_id=video_id).all()
        
        if not eventos_seleccionados:
            print(f"No hay eventos seleccionados para el video {video_id}")
            return jsonify([])
        
        # Separar eventos estándar y personalizados
        tipos_evento_ids = []
        eventos_personalizados_ids = []
        
        for evento_sel in eventos_seleccionados:
            if evento_sel.tipo_evento_id:
                tipos_evento_ids.append(evento_sel.tipo_evento_id)
            if evento_sel.evento_personalizado_id:
                eventos_personalizados_ids.append(evento_sel.evento_personalizado_id)
        
        print(f"Tipos de evento seleccionados: {tipos_evento_ids}")
        print(f"Eventos personalizados seleccionados: {eventos_personalizados_ids}")
        
        # Obtener todas las categorías
        categorias = CategoriaEvento.query.all()
        
        # Preparar resultado agrupado por categorías
        resultado = []
        
        for categoria in categorias:
            tipos_evento = []
            
            # Obtener tipos de eventos estándar seleccionados para esta categoría
            if tipos_evento_ids:
                tipos_base = TipoEvento.query.filter(
                    TipoEvento.id.in_(tipos_evento_ids),
                    TipoEvento.categoria_evento_id == categoria.id
                ).all()
                
                for tipo in tipos_base:
                    tipos_evento.append({
                        'id': tipo.id,
                        'nombre': tipo.nombre,
                        'es_equipo': tipo.es_equipo,
                        'es_global': tipo.es_global,
                        'es_jugador': tipo.es_jugador,
                        'tipo_asignacion': 'base'
                    })
            
            # Obtener eventos personalizados seleccionados para esta categoría
            if eventos_personalizados_ids:
                eventos_personalizados = EventoPersonalizado.query.filter(
                    EventoPersonalizado.id.in_(eventos_personalizados_ids),
                    EventoPersonalizado.categoria_evento_id == categoria.id,
                    EventoPersonalizado.user_id == session['user_id']
                ).all()
                
                for evento in eventos_personalizados:
                    tipos_evento.append({
                        'id': f"personalizado_{evento.id}",
                        'nombre': evento.nombre,
                        'es_equipo': evento.es_equipo,
                        'es_global': evento.es_global,
                        'es_jugador': evento.es_jugador,
                        'tipo_asignacion': 'personalizado',
                        'estadistica_tipo': evento.estadistica_tipo
                    })
            
            # Solo incluir categorías que tengan al menos un tipo de evento seleccionado
            if tipos_evento:
                resultado.append({
                    'id': categoria.id,
                    'nombre': categoria.nombre,
                    'tipos_evento': tipos_evento
                })
        
        print(f"Devolviendo {len(resultado)} categorías con eventos seleccionados")
        return jsonify(resultado)
        
    except Exception as e:
        print(f"Error al obtener eventos disponibles: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@evento_routes.route('/<username>/partido/<int:partido_id>/eventos', methods=['GET'])
def obtener_eventos_partido(username, partido_id):
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    try:
        print(f"Obteniendo eventos para el partido {partido_id} del usuario {username}")
        
        partido = Partido.query.get_or_404(partido_id)
        
        # Verificar que el partido pertenece a una temporada del usuario
        temporada = None
        if partido.liga:
            temporada = partido.liga.temporada
        else:
            temporada = Temporada.query.get_or_404(partido.temporada_id)
        
        if temporada.user_id != session['user_id']:
            return jsonify({'error': 'No autorizado'}), 401

        # Obtener todos los eventos asociados a este partido, excluyendo los de la categoría Paradas (id=8)
        eventos = Evento.query.outerjoin(TipoEvento).filter(
            Evento.partido_id == partido_id,
            db.or_(
                TipoEvento.categoria_evento_id.is_(None),
                ~TipoEvento.categoria_evento_id.in_([8])  # Excluir eventos de la categoría Paradas
            )
        ).order_by(Evento.tiempo_seg).all()
        
        print(f"Se encontraron {len(eventos)} eventos (excluyendo categoría Paradas)")
        
        eventos_data = []
        
        for evento in eventos:
            evento_data = {
                'id': evento.id,
                'tiempo_seg': evento.tiempo_seg,
                'tipo_evento_id': evento.tipo_evento_id,
                'evento_personalizado_id': evento.evento_personalizado_id,
                'descripcion': evento.descripcion,
                'partido_id': evento.partido_id,
                'equipo_id': evento.equipo_id,
                'zona_tiro': evento.zona_tiro,
                'resultado_tiro': evento.resultado_tiro
            }
            
            # Añadir información del tipo de evento (base o personalizado)
            if evento.tipo_evento_id:
                try:
                    tipo_evento = TipoEvento.query.get(evento.tipo_evento_id)
                    if tipo_evento:
                        evento_data['tipo_evento'] = {
                            'id': tipo_evento.id,
                            'nombre': tipo_evento.nombre,
                            'categoria_id': tipo_evento.categoria_evento_id
                        }
                except Exception as e:
                    print(f"Error al obtener tipo de evento: {str(e)}")
            elif evento.evento_personalizado_id:
                try:
                    evento_personalizado = EventoPersonalizado.query.get(evento.evento_personalizado_id)
                    if evento_personalizado:
                        evento_data['tipo_evento'] = {
                            'id': f"personalizado_{evento_personalizado.id}",
                            'nombre': evento_personalizado.nombre,
                            'categoria_id': evento_personalizado.categoria_evento_id,
                            'es_personalizado': True
                        }
                except Exception as e:
                    print(f"Error al obtener evento personalizado: {str(e)}")
            
            # Añadir información del equipo
            if evento.equipo_id:
                try:
                    equipo = Equipo.query.get(evento.equipo_id)
                    if equipo:
                        evento_data['equipo'] = {
                            'id': equipo.id,
                            'nombre': equipo.nombre
                        }
                except Exception as e:
                    print(f"Error al obtener equipo: {str(e)}")
            
            # Añadir información del jugador
            if evento.jugador_id:
                try:
                    jugador = Jugador.query.get(evento.jugador_id)
                    if jugador:
                        evento_data['jugador'] = {
                            'id': jugador.id,
                            'nombre': jugador.nombre,
                            'apellido': jugador.apellido,
                            'dorsal': jugador.dorsal
                        }
                except Exception as e:
                    print(f"Error al obtener jugador: {str(e)}")
            
            eventos_data.append(evento_data)
        
        return jsonify({'success': True, 'eventos': eventos_data}), 200
    
    except Exception as e:
        print(f"Error al obtener eventos del partido: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al obtener eventos: {str(e)}'}), 500
