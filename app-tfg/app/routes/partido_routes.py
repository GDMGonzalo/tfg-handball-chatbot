from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, Response
from models import db, Partido, Equipo, Liga, Temporada, Jugador, Convocado, JugadorEnPista, Video, Evento, TipoEvento
from datetime import datetime
import os
from sqlalchemy.orm import joinedload
import csv
from io import StringIO
from flask import Response
import csv
from sqlalchemy import text

partido_routes = Blueprint('partido_routes', __name__)

# Función auxiliar para calcular el resultado basado en eventos de gol
def calcular_resultado_partido(partido_id):
    """
    Calcula el resultado del partido basado en los eventos de gol registrados.
    Retorna una tupla (goles_local, goles_visitante)
    """
    # Obtener el partido para conocer los equipos
    partido = Partido.query.get(partido_id)
    if not partido:
        return (0, 0)
    
    equipo_local_id = partido.equipo_local_id
    equipo_visitante_id = partido.equipo_visitante_id
    
    # Obtener todos los eventos de gol del partido
    # Incluir: tipo 13 (gol 7 metros) y tipo 37 (tiro) con resultado "gol"
    # El tipo 1 ya no es un evento de gol
    eventos_gol = Evento.query.filter(
        Evento.partido_id == partido_id,
        db.or_(
            Evento.tipo_evento_id == 13,  # Goles 7 metros
            db.and_(
                Evento.tipo_evento_id == 37,  # Eventos de tiro
                Evento.resultado_tiro == 'gol'  # Con resultado gol
            )
        )
    ).all()
    
    # Contar goles por equipo
    goles_local = sum(1 for e in eventos_gol if e.equipo_id == equipo_local_id)
    goles_visitante = sum(1 for e in eventos_gol if e.equipo_id == equipo_visitante_id)
    
    return (goles_local, goles_visitante)

@partido_routes.route('/<username>/partido/<int:partido_id>/exportar-csv', methods=['GET'])
def exportar_timeline_csv(username, partido_id):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para exportar datos", "error")
        return redirect('/login')

    partido = Partido.query.get_or_404(partido_id)
    fecha_partido = partido.fecha_hora.strftime('%d/%m/%Y')
    nombre_partido = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre} ({fecha_partido})"

    # Obtén todos los eventos ordenados por tiempo
    eventos = (
        db.session.query(Evento)
        .options(
            joinedload(Evento.tipo_evento),
            joinedload(Evento.equipo),
            joinedload(Evento.jugador)
        )
        .filter(Evento.partido_id == partido_id)
        .order_by(Evento.tiempo_seg)
        .all()
    )

    output = StringIO()
    writer = csv.writer(output, delimiter=';')

    # Encabezado principal
    writer.writerow([f"TIMELINE DE EVENTOS - {nombre_partido}"])
    writer.writerow([])

    # Cabecera de columnas
    writer.writerow([
        "Minuto",
        "Evento",
        "Jugador",
        "Equipo",
        "Descripción"
    ])

    # Rellena cada fila del timeline
    for evento in eventos:
        minutos = evento.tiempo_seg // 60
        segundos = evento.tiempo_seg % 60
        tiempo_formateado = f"{minutos:02d}:{segundos:02d}"

        nombre_evento = evento.tipo_evento.nombre if evento.tipo_evento else ""
        nombre_jugador = ""
        if evento.jugador:
            nombre_jugador = f"{evento.jugador.nombre} {evento.jugador.apellido}"
            if evento.jugador.dorsal:
                nombre_jugador = f"{nombre_jugador} (#{evento.jugador.dorsal})"
        nombre_equipo = evento.equipo.nombre if evento.equipo else ""
        descripcion = evento.descripcion or ""

        writer.writerow([
            tiempo_formateado,
            nombre_evento,
            nombre_jugador,
            nombre_equipo,
            descripcion
        ])

    output.seek(0)
    filename = f"timeline_{partido.equipo_local.nombre}_vs_{partido.equipo_visitante.nombre}_{partido.fecha_hora.strftime('%Y%m%d')}.csv"

    return Response(
        '\ufeff' + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


def proteger_texto(val):
    if isinstance(val, str) and '/' in val:
        return f'="{val}"'
    return val

@partido_routes.route('/<username>/partido/<int:partido_id>/estadisticas-csv', methods=['GET'])
def exportar_estadisticas_csv(username, partido_id):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para exportar datos", "error")
        return redirect('/login')

    # Obtener datos de la vista actualizada
    sql = """
        SELECT
            equipo_jugador,
            jugador,
            tiros_campo,
            tiros_7m,
            perdidas,
            recuperaciones,
            faltas_cometidas,
            faltas_recibidas,
            asistencias
        FROM v_estadisticas_jugador_partido
        WHERE partido_id = :partido_id
        ORDER BY equipo_jugador, jugador
    """
    result = db.session.execute(text(sql), {'partido_id': partido_id})
    datos = result.fetchall()

    partido = Partido.query.get_or_404(partido_id)
    fecha_partido = partido.fecha_hora.strftime('%d/%m/%Y')
    nombre_partido = f"{partido.equipo_local.nombre} vs {partido.equipo_visitante.nombre} ({fecha_partido})"

    output = StringIO()
    writer = csv.writer(output, delimiter=';')

    # Encabezado principal
    writer.writerow([f"ESTADÍSTICAS DE JUGADORES - {nombre_partido}"])
    writer.writerow([])

    # Agrupar datos por equipo
    equipos_datos = {}
    for row in datos:
        equipo = row[0]  # equipo_jugador
        if equipo not in equipos_datos:
            equipos_datos[equipo] = []
        equipos_datos[equipo].append(row)

    # Variables para totales generales
    total_goles_campo = 0
    total_tiros_campo = 0
    total_goles_7m = 0
    total_perdidas = 0
    total_recuperaciones = 0
    total_faltas_cometidas = 0
    total_faltas_recibidas = 0
    total_asistencias = 0

    # Procesar cada equipo
    for equipo_nombre, jugadores in equipos_datos.items():
        # Título del equipo
        writer.writerow([f"=== {equipo_nombre.upper()} ==="])
        writer.writerow([])
        
        # Cabecera de columnas
        writer.writerow([
            "Jugador",
            "Tiros campo (goles/total)",
            "Tiros 7m",
            "Pérdidas",
            "Recuperaciones",
            "Faltas cometidas",
            "Faltas recibidas",
            "Asistencias"
        ])

        # Variables para totales del equipo
        equipo_goles_campo = 0
        equipo_tiros_campo = 0
        equipo_goles_7m = 0
        equipo_perdidas = 0
        equipo_recuperaciones = 0
        equipo_faltas_cometidas = 0
        equipo_faltas_recibidas = 0
        equipo_asistencias = 0

        # Datos de jugadores
        for jugador in jugadores:
            # Parsear tiros de campo (formato "goles/total")
            tiros_campo = jugador[2] or "0/0"
            if '/' in str(tiros_campo):
                goles_campo, total_campo = map(int, str(tiros_campo).split('/'))
            else:
                goles_campo, total_campo = 0, 0

            # Convertir todos los valores a enteros, manejando None y strings
            def safe_int(value):
                if value is None:
                    return 0
                if isinstance(value, str):
                    # Si es string con formato "X/Y", tomar solo el primer número
                    if '/' in value:
                        return int(value.split('/')[0])
                    # Si es string numérico
                    try:
                        return int(value)
                    except ValueError:
                        return 0
                return int(value)

            tiros_7m = safe_int(jugador[3])
            perdidas = safe_int(jugador[4])
            recuperaciones = safe_int(jugador[5])
            faltas_cometidas = safe_int(jugador[6])
            faltas_recibidas = safe_int(jugador[7])
            asistencias = safe_int(jugador[8])

            # Acumular estadísticas del equipo
            equipo_goles_campo += goles_campo
            equipo_tiros_campo += total_campo
            equipo_goles_7m += tiros_7m
            equipo_perdidas += perdidas
            equipo_recuperaciones += recuperaciones
            equipo_faltas_cometidas += faltas_cometidas
            equipo_faltas_recibidas += faltas_recibidas
            equipo_asistencias += asistencias

            writer.writerow([
                jugador[1],  # jugador
                proteger_texto(jugador[2] or "0/0"),  # tiros_campo
                tiros_7m,  # tiros_7m
                perdidas,  # perdidas
                recuperaciones,  # recuperaciones
                faltas_cometidas,  # faltas_cometidas
                faltas_recibidas,  # faltas_recibidas
                asistencias   # asistencias
            ])

        # Línea separadora
        writer.writerow([])
        
        # Totales del equipo
        writer.writerow([
            "TOTALES EQUIPO",
            proteger_texto(f"{equipo_goles_campo}/{equipo_tiros_campo}"),
            equipo_goles_7m,
            equipo_perdidas,
            equipo_recuperaciones,
            equipo_faltas_cometidas,
            equipo_faltas_recibidas,
            equipo_asistencias
        ])

        # Efectividad del equipo
        efectividad_campo = (equipo_goles_campo / equipo_tiros_campo * 100) if equipo_tiros_campo > 0 else 0
        writer.writerow([
            "EFECTIVIDAD CAMPO",
            f"{efectividad_campo:.1f}%",
            "",
            "",
            "",
            "",
            "",
            ""
        ])

        # Acumular para totales generales
        total_goles_campo += equipo_goles_campo
        total_tiros_campo += equipo_tiros_campo
        total_goles_7m += equipo_goles_7m
        total_perdidas += equipo_perdidas
        total_recuperaciones += equipo_recuperaciones
        total_faltas_cometidas += equipo_faltas_cometidas
        total_faltas_recibidas += equipo_faltas_recibidas
        total_asistencias += equipo_asistencias

        # Espacios entre equipos
        writer.writerow([])
        writer.writerow([])

    # Resumen general del partido
    writer.writerow(["=== RESUMEN DEL PARTIDO ==="])
    writer.writerow([])
    writer.writerow(["Estadística", "Total Partido"])
    writer.writerow(["Goles de campo", total_goles_campo])
    writer.writerow(["Tiros de campo", total_tiros_campo])
    
    efectividad_general = (total_goles_campo / total_tiros_campo * 100) if total_tiros_campo > 0 else 0
    writer.writerow(["Efectividad campo", f"{efectividad_general:.1f}%"])
    
    writer.writerow(["Goles 7 metros", total_goles_7m])
    writer.writerow(["Pérdidas totales", total_perdidas])
    writer.writerow(["Recuperaciones totales", total_recuperaciones])
    writer.writerow(["Faltas cometidas", total_faltas_cometidas])
    writer.writerow(["Faltas recibidas", total_faltas_recibidas])
    writer.writerow(["Asistencias totales", total_asistencias])

    output.seek(0)
    filename = f"estadisticas_{partido.equipo_local.nombre}_vs_{partido.equipo_visitante.nombre}_{partido.fecha_hora.strftime('%Y%m%d')}.csv"

    return Response(
        '\ufeff' + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@partido_routes.route('/<username>/partidos', methods=['GET'])
def listar_partidos(username):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para ver esta página", "error")
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Obtener filtros
    temporada_id = request.args.get('temporada_id')
    liga_id = request.args.get('liga_id')
    equipo_id = request.args.get('equipo_id')
    
    # Consulta base
    from sqlalchemy.orm import joinedload

    query = (
        db.session.query(Partido)
        .join(Liga, Partido.liga_id == Liga.id)
        .join(Temporada, Liga.temporada_id == Temporada.id)
        .filter(Temporada.user_id == user_id)
    )

    
    # Aplicar filtros
    if temporada_id:
        query = query.filter(Partido.temporada_id == temporada_id)
    
    if liga_id:
        query = query.filter(Partido.liga_id == liga_id)
    
    if equipo_id:
        query = query.filter((Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id))
    
    # Obtener partidos ordenados por fecha (más recientes primero)
    partidos = query.order_by(Partido.fecha_hora.desc()).all()
    
    # Calcular resultados para cada partido
    for partido in partidos:
        goles_local, goles_visitante = calcular_resultado_partido(partido.id)
        partido.goles_local_calculado = goles_local
        partido.goles_visitante_calculado = goles_visitante
    
    # Obtener temporadas, ligas y equipos para los filtros
    temporadas = Temporada.query.filter_by(user_id=user_id).all()
    ligas = Liga.query.join(Temporada).filter(Temporada.user_id == user_id).all()
    equipos = Equipo.query.filter_by(user_id=user_id).all()
    
    return render_template(
        "dashboard/partidos/index.html",
        username=username,
        partidos=partidos,
        temporadas=temporadas,
        ligas=ligas,
        equipos=equipos,
        temporada_id=temporada_id,
        liga_id=liga_id,
        equipo_id=equipo_id
    )

@partido_routes.route('/<username>/partido/<int:partido_id>', methods=['GET'])
def ver_partido(username, partido_id):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para ver esta página", "error")
        return redirect('/login')
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para ver este partido", "error")
        return redirect(f"/{username}/partidos")
    
    # Obtener convocados
    convocados_local = (
        db.session.query(Convocado)
        .join(Jugador)
        .filter(Convocado.partido_id == partido_id, Jugador.equipo_id == partido.equipo_local_id)
        .all()
    )
    convocados_visitante = (
        db.session.query(Convocado)
        .join(Jugador)
        .filter(Convocado.partido_id == partido_id, Jugador.equipo_id == partido.equipo_visitante_id)
        .all()
    )

    # Obtener jugadores de ambos equipos
    jugadores_local = Jugador.query.filter_by(equipo_id=partido.equipo_local_id).all()
    jugadores_visitante = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id).all()
    
    # Obtener videos asociados al partido
    videos = Video.query.filter_by(partido_id=partido_id).all()
    
    # Calcular resultado basado en eventos
    resultado_calculado = calcular_resultado_partido(partido_id)
    
    return render_template(
        "dashboard/partidos/view.html",
        username=username,
        partido=partido,
        convocados_local=convocados_local,
        convocados_visitante=convocados_visitante,
        jugadores_local=jugadores_local,
        jugadores_visitante=jugadores_visitante,
        temporada=temporada,
        videos=videos,
        resultado_calculado=resultado_calculado
    )

@partido_routes.route('/<username>/partido/<int:partido_id>/eventos', methods=['GET'])
def obtener_eventos_partido(username, partido_id):
    """
    Obtener todos los eventos de un partido en formato JSON para la timeline.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401
    
    # Obtener todos los eventos del partido con sus relaciones
    eventos = (
        db.session.query(Evento)
        .options(
            joinedload(Evento.tipo_evento),
            joinedload(Evento.equipo),
            joinedload(Evento.jugador)
        )
        .filter(Evento.partido_id == partido_id)
        .order_by(Evento.tiempo_seg)
        .all()
    )
    
    # Formatear los eventos para la respuesta JSON
    eventos_formateados = []
    for evento in eventos:
        evento_dict = {
            'id': evento.id,
            'tiempo_seg': evento.tiempo_seg,
            'tipo_evento_id': evento.tipo_evento_id,
            'evento_personalizado_id': evento.evento_personalizado_id,
            'equipo_id': evento.equipo_id,
            'descripcion': evento.descripcion,
            'zona_tiro': evento.zona_tiro,
            'resultado_tiro': evento.resultado_tiro
        }
        
        # Añadir información del tipo de evento (base o personalizado)
        if evento.tipo_evento_id:
            # Evento base
            if evento.tipo_evento:
                evento_dict['tipo_evento'] = {
                    'id': evento.tipo_evento.id,
                    'nombre': evento.tipo_evento.nombre,
                    'categoria_id': evento.tipo_evento.categoria_evento_id
                }
        elif evento.evento_personalizado_id:
            # Evento personalizado - consultar la base de datos para obtener la información completa
            from models import EventoPersonalizado
            evento_personalizado = EventoPersonalizado.query.get(evento.evento_personalizado_id)
            if evento_personalizado:
                evento_dict['tipo_evento'] = {
                    'id': f"personalizado_{evento_personalizado.id}",
                    'nombre': evento_personalizado.nombre,
                    'categoria_id': evento_personalizado.categoria_evento_id,
                    'es_personalizado': True
                }
        
        # Añadir información del jugador si existe
        if evento.jugador:
            evento_dict['jugador'] = {
                'id': evento.jugador.id,
                'nombre': evento.jugador.nombre,
                'apellido': evento.jugador.apellido,
                'dorsal': evento.jugador.dorsal,
                'es_capitan': evento.jugador.es_capitan,
                'rol': evento.jugador.rol
            }
        
        # Añadir información del equipo si existe
        if evento.equipo:
            evento_dict['equipo'] = {
                'id': evento.equipo.id,
                'nombre': evento.equipo.nombre
            }
        
        eventos_formateados.append(evento_dict)
    
    # Calcular resultado basado en eventos
    goles_local, goles_visitante = calcular_resultado_partido(partido_id)
    
    return jsonify({
        'partido_id': partido_id,
        'eventos': eventos_formateados,
        'resultado_calculado': {
            'local': goles_local,
            'visitante': goles_visitante
        }
    })

# Eliminar la ruta de actualización manual del resultado
# @partido_routes.route('/<username>/partido/<int:partido_id>/resultado', methods=['POST'])

# Eliminar la ruta de sincronización del resultado
# @partido_routes.route('/<username>/partido/<int:partido_id>/sincronizar-resultado', methods=['POST'])

# El resto de las rutas se mantienen igual
@partido_routes.route('/<username>/partido/<int:partido_id>/convocados', methods=['GET'])
def get_convocados(username, partido_id):
    """
    Obtener los jugadores convocados para un partido específico.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401

    convocados_local = (
        db.session.query(Convocado)
        .join(Jugador)
        .filter(Convocado.partido_id == partido_id, Jugador.equipo_id == partido.equipo_local_id)
        .all()
    )
    convocados_visitante = (
        db.session.query(Convocado)
        .join(Jugador)
        .filter(Convocado.partido_id == partido_id, Jugador.equipo_id == partido.equipo_visitante_id)
        .all()
    )

    # Preparar datos de jugadores convocados
    local = []
    for convocado in convocados_local:
        jugador = convocado.jugador
        local.append({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'apellido': jugador.apellido,
            'dorsal': jugador.dorsal,
            'rol': jugador.rol,
            'es_capitan': jugador.es_capitan,
            'equipo_id': jugador.equipo_id,
            'posicion': jugador.posicion.nombre if jugador.posicion else None

        })
    
    visitante = []
    for convocado in convocados_visitante:
        jugador = convocado.jugador
        visitante.append({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'apellido': jugador.apellido,
            'dorsal': jugador.dorsal,
            'rol': jugador.rol,
            'es_capitan': jugador.es_capitan,
            'equipo_id': jugador.equipo_id,
            'posicion': jugador.posicion.nombre if jugador.posicion else None

        })
    
    return jsonify({
        'local': local,
        'visitante': visitante
    })

# Añadir esta nueva ruta para manejar solicitudes GET a la página de gestión de convocatoria
@partido_routes.route('/<username>/partido/<int:partido_id>/convocatoria', methods=['GET'])
def gestionar_convocatoria(username, partido_id):
    """
    Mostrar la página para gestionar la convocatoria de jugadores para un partido.
    """
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para gestionar la convocatoria", "error")
        return redirect('/login')
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para gestionar este partido", "error")
        return redirect(f"/{username}/partidos")
    
    # Obtener jugadores de ambos equipos
    jugadores_local = Jugador.query.filter_by(equipo_id=partido.equipo_local_id).all()
    jugadores_visitante = Jugador.query.filter_by(equipo_id=partido.equipo_visitante_id).all()
    
    # Obtener IDs de jugadores convocados
    convocados = Convocado.query.filter_by(partido_id=partido_id).all()
    convocados_ids = [c.jugador_id for c in convocados]
    
    return render_template(
        "gestionar_convocatoria.html",
        username=username,
        partido=partido,
        jugadores_local=jugadores_local,
        jugadores_visitante=jugadores_visitante,
        convocados_ids=convocados_ids
    )

# Modificar la ruta POST existente para que use el mismo nombre de función
@partido_routes.route('/<username>/partido/<int:partido_id>/convocatoria', methods=['POST'])
def guardar_convocatoria(username, partido_id):
    """
    Guardar la convocatoria de jugadores para un partido.
    """
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para gestionar la convocatoria", "error")
        return redirect('/login')
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para gestionar este partido", "error")
        return redirect(f"/{username}/partidos")
    
    # Procesar solicitud de formulario normal
    equipo_id = request.form.get('equipo_id')
    jugadores_ids = request.form.getlist('jugadores_ids')
    
    # Validar que el equipo pertenezca al partido
    if int(equipo_id) != partido.equipo_local_id and int(equipo_id) != partido.equipo_visitante_id:
        flash("El equipo no pertenece a este partido", "error")
        return redirect(f"/{username}/partido/{partido_id}/convocatoria")
    
    try:
        # Obtener los jugadores actualmente convocados para este equipo
        convocados_actuales = (
            db.session.query(Convocado)
            .join(Jugador)
            .filter(Convocado.partido_id == partido_id, Jugador.equipo_id == equipo_id)
            .all()
        )
        
        # Crear conjuntos para facilitar las comparaciones
        ids_actuales = {c.jugador_id for c in convocados_actuales}
        ids_nuevos = set(map(int, jugadores_ids)) if jugadores_ids else set()
        
        # Jugadores a añadir (están en la nueva lista pero no en la actual)
        ids_a_añadir = ids_nuevos - ids_actuales
        
        # Jugadores a eliminar (están en la actual pero no en la nueva)
        ids_a_eliminar = ids_actuales - ids_nuevos
        
        # Procesar eliminaciones
        errores = []
        for jugador_id in ids_a_eliminar:
            # Verificar si el jugador tiene eventos asociados
            tiene_eventos = db.session.query(Evento).filter(
                Evento.partido_id == partido_id,
                Evento.jugador_id == jugador_id
            ).first() is not None
            
            # Verificar si el jugador está en pista
            esta_en_pista = db.session.query(JugadorEnPista).filter(
                JugadorEnPista.partido_id == partido_id,
                JugadorEnPista.jugador_id == jugador_id
            ).first() is not None
            
            if tiene_eventos or esta_en_pista:
                # No eliminar y registrar el error
                jugador = Jugador.query.get(jugador_id)
                nombre_completo = f"{jugador.nombre} {jugador.apellido}"
                razon = []
                if tiene_eventos:
                    razon.append("tiene eventos registrados")
                if esta_en_pista:
                    razon.append("está en pista")
                
                errores.append(f"No se puede eliminar a {nombre_completo} porque {' y '.join(razon)}")
                # Mantener este jugador en la lista de convocados
                ids_nuevos.add(jugador_id)
            else:
                # Eliminar la convocatoria
                convocado = db.session.query(Convocado).filter(
                    Convocado.partido_id == partido_id,
                    Convocado.jugador_id == jugador_id
                ).first()
                if convocado:
                    db.session.delete(convocado)
        
        # Procesar adiciones
        for jugador_id in ids_a_añadir:
            # Verificar que el jugador no esté ya convocado
            convocado_existente = db.session.query(Convocado).filter(
                Convocado.partido_id == partido_id,
                Convocado.jugador_id == jugador_id
            ).first()
            
            if not convocado_existente:
                convocado = Convocado(
                    partido_id=partido_id,
                    jugador_id=jugador_id
                )
                db.session.add(convocado)
        
        db.session.commit()
        
        # Mostrar mensajes (solo uno por tipo)
        if errores:
            # Mostrar solo un mensaje de advertencia por jugador
            mostrados = set()
            for error in errores:
                if error not in mostrados:
                    flash(error, "warning")
                    mostrados.add(error)
            
            # Mostrar mensaje general solo una vez
            flash("Convocatoria guardada con advertencias", "warning")
        else:
            flash("Convocatoria guardada con éxito", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al guardar la convocatoria: {str(e)}", "error")
    
    return redirect(f"/{username}/partido/{partido_id}/convocatoria")

@partido_routes.route('/<username>/equipo/<int:equipo_id>/jugadores', methods=['GET'])
def get_jugadores_equipo(username, equipo_id):
    """
    Obtener los jugadores de un equipo.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401
    
    # Verificar que el equipo pertenece al usuario
    equipo = Equipo.query.filter_by(id=equipo_id, user_id=session['user_id']).first()
    if not equipo:
        return jsonify({'error': 'Equipo no encontrado o no autorizado'}), 404
    
    partido_id = request.args.get('partido_id')
    
    # Obtener todos los jugadores del equipo
    jugadores = Jugador.query.filter_by(equipo_id=equipo_id).all()
    
    # Preparar datos de jugadores
    jugadores_data = []
    for jugador in jugadores:
        jugadores_data.append({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'apellido': jugador.apellido,
            'dorsal': jugador.dorsal,
            'rol': jugador.rol,
            'es_capitan': jugador.es_capitan,
            'posicion': jugador.posicion
        })
    
    return jsonify({'jugadores': jugadores_data})

@partido_routes.route('/<username>/temporada/<int:temporada_id>/partido/nuevo', methods=['GET', 'POST'])
def nuevo_partido(username, temporada_id):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para crear un partido", "error")
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Verificar que la temporada pertenezca al usuario
    temporada = Temporada.query.filter_by(id=temporada_id, user_id=user_id).first()
    if not temporada:
        flash("Temporada no encontrada", "error")
        return redirect(f"/{username}/temporadas")
    
    if request.method == 'POST':
        liga_id = request.form.get('liga_id')
        fecha_hora = request.form.get('fecha_hora')
        equipo_local_id = request.form.get('equipo_local_id')
        equipo_visitante_id = request.form.get('equipo_visitante_id')
        
        # Validar que los equipos sean diferentes
        if equipo_local_id == equipo_visitante_id:
            flash("El equipo local y visitante no pueden ser el mismo", "error")
            return redirect(f"/{username}/temporada/{temporada_id}/partido/nuevo")
        
        # Validar formato de fecha y hora
        try:
            fecha_hora_obj = datetime.strptime(fecha_hora, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash("El formato de fecha y hora es incorrecto. Utiliza el formato YYYY-MM-DDTHH:MM", "error")
            return redirect(f"/{username}/temporada/{temporada_id}/partido/nuevo")
        
        # Verificar que la liga pertenezca a la temporada
        if liga_id:
            liga = Liga.query.get(liga_id)
            if not liga or liga.temporada_id != temporada_id:
                flash("La liga seleccionada no es válida", "error")
                return redirect(f"/{username}/temporada/{temporada_id}/partido/nuevo")
        
        # Crear el partido
        nuevo_partido = Partido(
            liga_id=liga_id if liga_id else None,
            fecha_hora=fecha_hora_obj,
            equipo_local_id=equipo_local_id,
            equipo_visitante_id=equipo_visitante_id
        )
        
        try:
            db.session.add(nuevo_partido)
            db.session.commit()
            flash("Partido creado con éxito", "success")
            return redirect(f"/{username}/temporada/{temporada_id}")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al crear el partido: {str(e)}", "error")
            return redirect(f"/{username}/temporada/{temporada_id}/partido/nuevo")
    
    # GET: Mostrar formulario
    ligas = Liga.query.filter_by(temporada_id=temporada_id).all()
    equipos = Equipo.query.filter_by(user_id=user_id).all()
    
    return render_template(
        "dashboard/partidos/create.html",
        username=username,
        temporada=temporada,
        ligas=ligas,
        equipos=equipos
    )

@partido_routes.route('/<username>/partido/<int:partido_id>/editar', methods=['GET', 'POST'])
def editar_partido(username, partido_id):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para editar un partido", "error")
        return redirect('/login')
    
    user_id = session['user_id']
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != user_id:
        flash("No tienes permiso para editar este partido", "error")
        return redirect(f"/{username}/partidos")
    
    if request.method == 'POST':
        liga_id = request.form.get('liga_id')
        fecha_hora = request.form.get('fecha_hora')
        equipo_local_id = request.form.get('equipo_local_id')
        equipo_visitante_id = request.form.get('equipo_visitante_id')
        goles_local = request.form.get('goles_local')
        goles_visitante = request.form.get('goles_visitante')
        
        # Validar que los equipos sean diferentes
        if equipo_local_id == equipo_visitante_id:
            flash("El equipo local y visitante no pueden ser el mismo", "error")
            return redirect(f"/{username}/partido/{partido_id}/editar")
        
        # Validar formato de fecha y hora
        try:
            fecha_hora_obj = datetime.strptime(fecha_hora, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash("El formato de fecha y hora es incorrecto. Utiliza el formato YYYY-MM-DDTHH:MM", "error")
            return redirect(f"/{username}/partido/{partido_id}/editar")
        
        # Verificar que la liga pertenezca al usuario
        if liga_id:
            liga = Liga.query.get(liga_id)
            if not liga or liga.temporada.user_id != user_id:
                flash("La liga seleccionada no es válida", "error")
                return redirect(f"/{username}/partido/{partido_id}/editar")
        
        # Actualizar el partido
        partido.liga_id = liga_id if liga_id else None
        partido.fecha_hora = fecha_hora_obj
        partido.equipo_local_id = equipo_local_id
        partido.equipo_visitante_id = equipo_visitante_id
        
        # Actualizar goles si se proporcionaron
        if goles_local:
            partido.goles_local = int(goles_local)
        else:
            partido.goles_local = None
            
        if goles_visitante:
            partido.goles_visitante = int(goles_visitante)
        else:
            partido.goles_visitante = None
        
        try:
            db.session.commit()
            flash("Partido actualizado con éxito", "success")
            return redirect(f"/{username}/partido/{partido_id}")
        except Exception as e:
            db.session.rollback()
            flash(f"Error al actualizar el partido: {str(e)}", "error")
            return redirect(f"/{username}/partido/{partido_id}/editar")
    
    # GET: Mostrar formulario
    ligas = Liga.query.join(Temporada).filter(Temporada.user_id == user_id).all()
    equipos = Equipo.query.filter_by(user_id=user_id).all()
    
    return render_template(
        "dashboard/partidos/edit.html",
        username=username,
        partido=partido,
        ligas=ligas,
        equipos=equipos
    )

@partido_routes.route('/<username>/partido/<int:partido_id>/eliminar', methods=['POST'])
def eliminar_partido(username, partido_id):
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para eliminar un partido", "error")
        return redirect('/login')
    
    user_id = session['user_id']
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != user_id:
        flash("No tienes permiso para eliminar este partido", "error")
        return redirect(f"/{username}/partidos")
    
    try:
        # Eliminar el partido (esto eliminará en cascada convocados, jugadores en pista, etc.)
        db.session.delete(partido)
        db.session.commit()
        flash("Partido eliminado con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar el partido: {str(e)}", "error")
    
    return redirect(f"/{username}/partidos")

@partido_routes.route('/<username>/partido/<int:partido_id>/jugadores-pista', methods=['GET'])
def get_jugadores_pista(username, partido_id):
    """
    Obtener los jugadores que están actualmente en pista para un partido.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401

    # Obtener el tiempo actual del video si se proporciona
    tiempo_actual = request.args.get('tiempo', 0, type=int)
    
    # Obtener jugadores en pista para el equipo local
    jugadores_local = db.session.query(JugadorEnPista).filter(
        JugadorEnPista.partido_id == partido_id,
        JugadorEnPista.equipo_id == partido.equipo_local_id
    ).all()
    
    # Obtener jugadores en pista para el equipo visitante
    jugadores_visitante = db.session.query(JugadorEnPista).filter(
        JugadorEnPista.partido_id == partido_id,
        JugadorEnPista.equipo_id == partido.equipo_visitante_id
    ).all()
    
    # Formatear datos
    local = []
    for jp in jugadores_local:
        jugador = jp.jugador
        local.append({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'apellido': jugador.apellido,
            'dorsal': jugador.dorsal,
            'rol': jugador.rol,
            'es_capitan': jugador.es_capitan,
            'equipo_id': jugador.equipo_id,
            'posicion': jugador.posicion.nombre if jugador.posicion else None
        })
    
    visitante = []
    for jp in jugadores_visitante:
        jugador = jp.jugador
        visitante.append({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'apellido': jugador.apellido,
            'dorsal': jugador.dorsal,
            'rol': jugador.rol,
            'es_capitan': jugador.es_capitan,
            'equipo_id': jugador.equipo_id,
            'posicion': jugador.posicion.nombre if jugador.posicion else None
        })
    
    return jsonify({
        'local': local,
        'visitante': visitante
    })

@partido_routes.route('/<username>/partido/<int:partido_id>/jugadores-pista', methods=['POST'])
def actualizar_jugadores_pista(username, partido_id):
    """
    Actualizar los jugadores que están en pista para un partido.
    Solo procesa los cambios (jugadores que entran y salen).
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.json
    equipo_id = data.get('equipo_id')
    jugadores_entran = data.get('jugadores_entran', [])
    jugadores_salen = data.get('jugadores_salen', [])
    
    # Validar que el equipo pertenezca al partido
    if int(equipo_id) != partido.equipo_local_id and int(equipo_id) != partido.equipo_visitante_id:
        return jsonify({'error': 'El equipo no pertenece a este partido'}), 400
    
    try:
        # Eliminar solo los jugadores que salen de la pista
        for jugador_id in jugadores_salen:
            jp = db.session.query(JugadorEnPista).filter(
                JugadorEnPista.partido_id == partido_id,
                JugadorEnPista.jugador_id == jugador_id,
                JugadorEnPista.equipo_id == equipo_id
            ).first()
            
            if jp:
                db.session.delete(jp)
        
        # Añadir solo los nuevos jugadores a la pista
        for jugador_id in jugadores_entran:
            # Verificar si el jugador ya está en pista
            existe = db.session.query(JugadorEnPista).filter(
                JugadorEnPista.partido_id == partido_id,
                JugadorEnPista.jugador_id == jugador_id,
                JugadorEnPista.equipo_id == equipo_id
            ).first()
            
            # Solo añadir si no existe
            if not existe:
                nuevo_jp = JugadorEnPista(
                    partido_id=partido_id,
                    jugador_id=jugador_id,
                    equipo_id=equipo_id
                )
                db.session.add(nuevo_jp)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Jugadores en pista actualizados con éxito'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Error al actualizar jugadores en pista: {str(e)}'
        }), 500

@partido_routes.route('/<username>/partido/<int:partido_id>/sustitucion', methods=['POST'])
def realizar_sustitucion(username, partido_id):
    """
    Realizar una sustitución: un jugador entra y otro sale.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401

    data = request.json
    equipo_id = data.get('equipo_id')
    jugador_entra_id = data.get('jugador_entra_id')
    jugador_sale_id = data.get('jugador_sale_id')
    
    # Validar que el equipo pertenezca al partido
    if int(equipo_id) != partido.equipo_local_id and int(equipo_id) != partido.equipo_visitante_id:
        return jsonify({'error': 'El equipo no pertenece a este partido'}), 400
    
    try:
        # Eliminar al jugador que sale
        jugador_sale = db.session.query(JugadorEnPista).filter(
            JugadorEnPista.partido_id == partido_id,
            JugadorEnPista.jugador_id == jugador_sale_id
        ).first()
        
        if not jugador_sale:
            return jsonify({'error': 'El jugador que sale no está en pista'}), 400
        
        db.session.delete(jugador_sale)
        
        # Añadir al jugador que entra
        nuevo_jp = JugadorEnPista(
            partido_id=partido_id,
            jugador_id=jugador_entra_id,
            equipo_id=equipo_id
        )
        db.session.add(nuevo_jp)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Sustitución realizada con éxito'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Error al realizar la sustitución: {str(e)}'
        }), 500

@partido_routes.route('/<username>/partido/<int:partido_id>/resultado', methods=['POST'])
def actualizar_resultado(username, partido_id):
    """
    Actualizar el resultado de un partido.
    """
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para actualizar el resultado", "error")
        return redirect('/login')
    
    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    
    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para actualizar este partido", "error")
        return redirect(f"/{username}/partidos")
    
    goles_local = request.form.get('goles_local')
    goles_visitante = request.form.get('goles_visitante')
    
    try:
        if goles_local:
            partido.goles_local = int(goles_local)
        else:
            partido.goles_local = None
            
        if goles_visitante:
            partido.goles_visitante = int(goles_visitante)
        else:
            partido.goles_visitante = None
        
        db.session.commit()
        flash("Resultado actualizado con éxito", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar el resultado: {str(e)}", "error")
    
    return redirect(f"/{username}/partido/{partido_id}")
