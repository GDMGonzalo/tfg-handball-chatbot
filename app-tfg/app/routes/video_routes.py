from flask import Blueprint, request, jsonify, session, redirect, flash, render_template, send_file, abort
import os
from datetime import datetime
from models import db, Video, Partido, Temporada, Jugador, Evento, TipoEvento, Convocado, Equipo, Liga, Tarea, Descarga, JugadorTracking, JugadorEnPista
from sqlalchemy.sql import text
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
import requests
import shutil
import json
from werkzeug.utils import secure_filename
import cv2
from threading import Thread
from config import Config
from services.video import render_video_with_boxes

video_routes = Blueprint('video_routes', __name__)

ALLOWED_EXTENSIONS = {'mp4'}
UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def allowed_file(filename):
    """
    Verifica si el archivo tiene una extensión permitida.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


    


def get_video_duration(file_path):
    """
    Calcula la duración de un video en segundos usando FFmpeg.
    :param file_path: Ruta completa al archivo de video.
    :return: Duración del video en segundos.
    """
    try:
        video = cv2.VideoCapture(file_path)
        duration = video.get(cv2.CAP_PROP_FRAME_COUNT) / \
            video.get(cv2.CAP_PROP_FPS)
        return duration
    except Exception as e:
        print(f"Error al calcular la duración del video: {e}")
        return 0

def get_fps(file_path):
    """
    Calcula los fotogramas por segundo (FPS) de un video usando FFmpeg.
    :param file_path: Ruta completa al archivo de video.
    :return: FPS del video.
    """
    try:
        video = cv2.VideoCapture(file_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        return fps
    except Exception as e:
        print(f"Error al calcular los FPS del video: {e}")
        return 0

def process_thumbnail(video_path, thumbnail_path):
    """
    Genera una miniatura para un video dado.
    :param video_path: Ruta completa del archivo de video.
    :param thumbnail_path: Ruta donde se guardará la miniatura.
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"No se pudo abrir el video: {video_path}")
        else:
            ret, frame = cap.read()
            if ret:
                cv2.imwrite(thumbnail_path, frame)
                print(f"Miniatura generada exitosamente: {thumbnail_path}")
            else:
                print(f"No se pudo generar la miniatura para: {video_path}")
                raise Exception(
                    f"No se pudo leer el frame del video: {video_path}")
    except Exception as e:
        print(f"Error al generar la miniatura: {e}")
        raise


@video_routes.route('/<username>/videos', methods=['GET'])
def listar_videos(username):
    """Listar todos los videos del usuario con filtros opcionales"""
    if 'user_id' not in session or session.get('username') != username:
        return redirect('/login')

    user_id = session['user_id']

    # Obtener filtros
    temporada_id = request.args.get('temporada_id')
    partido_id = request.args.get('partido_id')
    equipo_id = request.args.get('equipo_id')

    # Consulta base
    query = Video.query.join(Partido).join(Liga).join(
        Temporada).filter(Temporada.user_id == user_id)

    # Aplicar filtros
    if temporada_id:
        query = query.filter(Temporada.id == temporada_id)

    if partido_id:
        query = query.filter(Video.partido_id == partido_id)

    if equipo_id:
        query = query.filter(or_(Partido.equipo_local_id ==
                             equipo_id, Partido.equipo_visitante_id == equipo_id))

    # Obtener videos ordenados por fecha (más recientes primero)
    videos = query.order_by(Video.uploaded_at.desc()).all()

    # Obtener temporadas, partidos y equipos para los filtros
    temporadas = Temporada.query.filter_by(user_id=user_id).all()
    partidos = Partido.query.join(Liga).join(
        Temporada).filter(Temporada.user_id == user_id).all()

    equipos = Equipo.query.filter_by(user_id=user_id).all()

    return render_template(
        "dashboard/videos/index.html",
        username=username,
        videos=videos,
        temporadas=temporadas,
        partidos=partidos,
        equipos=equipos,
        temporada_id=temporada_id,
        partido_id=partido_id,
        equipo_id=equipo_id
    )


@video_routes.route('/<username>/partido/<int:partido_id>/upload/chunked', methods=['POST'])
def upload_chunked_to_partido(username, partido_id):
    """
    Recibe un fragmento de un archivo de video y lo guarda temporalmente.
    Este es el ÚNICO método de subida soportado.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({"error": "No autorizado"}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada

    if temporada.user_id != session['user_id']:
        return jsonify({"error": "No tienes permiso para este partido"}), 403

    # Verificar que se haya enviado un archivo
    if 'file' not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    file_chunk = request.files['file']
    upload_id = request.form.get('upload_id')
    chunk_index = request.form.get('chunk_index')
    total_chunks = request.form.get('total_chunks')
    filename = request.form.get('filename')

    if not all([upload_id, chunk_index, total_chunks, filename]):
        return jsonify({"error": "Faltan parámetros requeridos"}), 400

    # Verificar formato de archivo
    if not allowed_file(filename):
        return jsonify({
            "error": f"Formato de archivo no permitido. Solo se permiten: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    try:
        # Crear directorio temporal para los fragmentos si no existe
        temp_dir = os.path.join(UPLOAD_FOLDER, 'temp', upload_id)
        os.makedirs(temp_dir, exist_ok=True)
        # Guardar el fragmento
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
        file_chunk.save(chunk_path)

        # Guardar metadatos del fragmento
        metadata = {
            'filename': secure_filename(filename),
            'total_chunks': int(total_chunks),
            'partido_id': partido_id,
            'upload_time': datetime.utcnow().isoformat(),
            'user_id': session['user_id'],
            'username': username
        }

        with open(os.path.join(temp_dir, 'metadata.json'), 'w') as f:
            json.dump(metadata, f)

        print(
            f"Fragmento {chunk_index}/{total_chunks} recibido para {filename}")

        return jsonify({
            "success": True,
            "message": f"Fragmento {chunk_index} de {total_chunks} recibido correctamente",
            "upload_id": upload_id,
            "chunk_index": chunk_index,
            "progress": round((int(chunk_index) + 1) / int(total_chunks) * 100, 2)
        })

    except Exception as e:
        print(f"Error al procesar fragmento: {str(e)}")
        return jsonify({"error": f"Error al procesar fragmento: {str(e)}"}), 500


@video_routes.route('/<username>/partido/<int:partido_id>/upload/chunked/finalize', methods=['POST'])
def finalize_chunked_upload(username, partido_id):
    """
    Finaliza la subida por fragmentos, combinando todos los fragmentos en un único archivo.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({"error": "No autorizado"}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada
    liga = partido.liga

    if temporada.user_id != session['user_id']:
        return jsonify({"error": "No tienes permiso para este partido"}), 403

    # Obtener datos de la solicitud
    data = request.json
    upload_id = data.get('upload_id')
    filename = data.get('filename')
    total_chunks = data.get('total_chunks')

    if not all([upload_id, filename, total_chunks]):
        return jsonify({"error": "Faltan parámetros requeridos"}), 400

    try:
        # Directorio temporal donde están los fragmentos
        temp_dir = os.path.join(UPLOAD_FOLDER, 'temp', upload_id)

        if not os.path.exists(temp_dir):
            return jsonify({"error": "No se encontraron los fragmentos del archivo"}), 400

        # Verificar que existan todos los fragmentos
        missing_chunks = []
        for i in range(int(total_chunks)):
            chunk_path = os.path.join(temp_dir, f"chunk_{i}")
            if not os.path.exists(chunk_path):
                missing_chunks.append(i)

        if missing_chunks:
            return jsonify({
                "error": f"Faltan los fragmentos: {', '.join(map(str, missing_chunks))}"
            }), 400

        # Crear estructura de carpetas para el video final
        user_folder = os.path.join(UPLOAD_FOLDER, username)
        temporada_folder = os.path.join(
            user_folder, f"temporada_{temporada.id}")

        # Si el partido tiene liga, incluirla en la ruta
        if liga:
            liga_folder = os.path.join(temporada_folder, f"liga_{liga.id}")
            partido_folder = os.path.join(liga_folder, f"partido_{partido_id}")
        else:
            # Si no tiene liga, usar una carpeta "sin_liga"
            liga_folder = os.path.join(temporada_folder, "sin_liga")
            partido_folder = os.path.join(liga_folder, f"partido_{partido_id}")

        # Crear las carpetas si no existen
        os.makedirs(partido_folder, exist_ok=True)

        # Nombre seguro para el archivo
        secure_name = secure_filename(filename)

        # Verificar si ya existe un archivo con el mismo nombre
        base_name, ext = os.path.splitext(secure_name)
        counter = 1
        while os.path.exists(os.path.join(partido_folder, secure_name)):
            secure_name = f"{base_name}_{counter}{ext}"
            counter += 1

        video_path = os.path.join(partido_folder, secure_name)
        thumbnail_path = os.path.join(
            partido_folder, f"{os.path.splitext(secure_name)[0]}_thumb.jpg")

        print(f"Combinando {total_chunks} fragmentos en: {video_path}")

        # Combinar fragmentos en un solo archivo
        with open(video_path, 'wb') as outfile:
            for i in range(int(total_chunks)):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}")
                with open(chunk_path, 'rb') as infile:
                    shutil.copyfileobj(infile, outfile)

        print(f"Video combinado guardado en: {video_path}")
        print(f"Tamaño final del archivo: {os.path.getsize(video_path)} bytes")

        # Calcular la duración del video
        video_duration = get_video_duration(video_path)
        print(f"Duración del video: {video_duration} segundos")
        fps=get_fps(video_path)
        print(f"FPS del video: {fps}")
        # Generar la miniatura
        try:
            process_thumbnail(video_path, thumbnail_path)
        except Exception as e:
            print(f"Error al generar miniatura: {e}")
            # No fallar si no se puede generar la miniatura

        # Registrar en la base de datos
        new_video = Video(
            partido_id=partido_id,
            filename=secure_name,
            uploaded_at=datetime.utcnow(),
            duracion_segundos=video_duration,
            fps=fps
        )
        db.session.add(new_video)
        db.session.commit()

        print(f"Video registrado en BD con ID: {new_video.id}")

        # Limpiar archivos temporales
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"Archivos temporales limpiados: {temp_dir}")
        except Exception as e:
            print(f"Error al limpiar archivos temporales: {e}")

        return jsonify({
            "success": True,
            "message": "Video subido y procesado con éxito",
            "filename": secure_name,
            "video_id": new_video.id,
            "duration": video_duration,
            "file_size": os.path.getsize(video_path)
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error al finalizar la subida: {str(e)}")

        # Intentar limpiar archivos temporales en caso de error
        try:
            temp_dir = os.path.join(UPLOAD_FOLDER, 'temp', upload_id)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

        return jsonify({"error": f"Error al finalizar la subida: {str(e)}"}), 500


@video_routes.route('/<username>/video/<int:video_id>', methods=['GET'])
def ver_video(username, video_id):
    """
    Página para ver un video específico.
    """
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para ver este video", "error")
        return redirect(f"/{username}/login")

    video = Video.query.get_or_404(video_id)
    partido = Partido.query.get_or_404(video.partido_id)
    temporada = partido.temporada

    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para ver este video", "error")
        return redirect(f"/{username}/home")

    # Obtener eventos del video con información adicional para tiros
    eventos = db.session.query(Evento).filter_by(
        video_id=video_id).order_by(Evento.tiempo_seg).all()

    # Procesar eventos para incluir información de goles
    eventos_procesados = []
    for evento in eventos:
        evento_dict = {
            'id': evento.id,
            'tipo_evento_id': evento.tipo_evento_id,
            'tiempo_seg': evento.tiempo_seg,
            'jugador_id': evento.jugador_id,
            'equipo_id': evento.equipo_id,
            'descripcion': evento.descripcion,
            'resultado_tiro': getattr(evento, 'resultado_tiro', None),
            'es_gol': False  # Por defecto no es gol
        }

        # Determinar si es gol basado en la nueva lógica
        if evento.tipo_evento_id == 13:  # Gol 7 metros
            evento_dict['es_gol'] = True
        # Tiro que resultó en gol
        elif evento.tipo_evento_id == 37 and hasattr(evento, 'resultado_tiro') and evento.resultado_tiro == 'gol':
            evento_dict['es_gol'] = True
        # Evento personalizado de gol
        elif hasattr(evento, 'estadistica_tipo') and evento.estadistica_tipo == 'gol':
            evento_dict['es_gol'] = True

        eventos_procesados.append(evento_dict)

    # Obtener tipos de eventos
    tipos_evento = TipoEvento.query.all()
    tareas = (
        Tarea.query
        .options(joinedload(Tarea.user))
        .outerjoin(Descarga, Tarea.id == Descarga.tarea_id)
        .filter(Tarea.video_id == video_id)
        .add_entity(Descarga)
        .all()
    )

    return render_template(
        "dashboard/videos/view.html",
        username=username,
        video=video,
        partido=partido,
        temporada=temporada,
        eventos=eventos_procesados,
        tipos_evento=tipos_evento,
        tareas=tareas
    )


@video_routes.route('/<username>/video/<int:video_id>/eliminar', methods=['POST'])
def eliminar_video(username, video_id):
    """Eliminar un video y todos sus archivos asociados"""
    if 'user_id' not in session or session.get('username') != username:
        flash("Debes iniciar sesión para eliminar videos", "error")
        return redirect(f"/{username}/login")

    video = Video.query.get_or_404(video_id)
    partido = Partido.query.get_or_404(video.partido_id)
    temporada = partido.temporada

    if temporada.user_id != session['user_id']:
        flash("No tienes permiso para eliminar este video", "error")
        return redirect(f"/{username}/home")

    try:
        # Construir la ruta al archivo
        liga_path = f"liga_{partido.liga.id}" if partido.liga else "sin_liga"
        video_folder = os.path.join(
            UPLOAD_FOLDER, username, f"temporada_{temporada.id}", liga_path, f"partido_{partido.id}")
        video_path = os.path.join(video_folder, video.filename)
        thumbnail_path = os.path.join(
            video_folder, f"{os.path.splitext(video.filename)[0]}_thumb.jpg")
        for file in os.listdir(video_folder):
            if file.startswith(os.path.splitext(video.filename)[0]):
                os.remove(os.path.join(video_folder, file))
        # Eliminar archivos físicos
        files_deleted = []
        if os.path.exists(video_path):
            os.remove(video_path)
            files_deleted.append("video")

        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
            files_deleted.append("miniatura")

        # Eliminar el video de la base de datos (esto eliminará en cascada los eventos)
        db.session.delete(video)
        tareas = Tarea.query.filter_by(video_id=video_id).all()
        for tarea in tareas:
            db.session.delete(tarea)
        db.session.commit()
        message = f"Video eliminado con éxito"
        if files_deleted:
            message += f" (archivos eliminados: {', '.join(files_deleted)})"

        flash(message, "success")
        print(f"Video {video_id} eliminado por usuario {username}")

    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar video {video_id}: {str(e)}")
        flash(f"Error al eliminar el video: {str(e)}", "error")

    return redirect(f"/{username}/videos")


@video_routes.route('/uploads/<username>/temporada_<int:temporada_id>/<liga_path>/partido_<int:partido_id>/<filename>', methods=['GET'])
def serve_video_files(username, temporada_id, liga_path, partido_id, filename):
    """
    Ruta para servir archivos de video desde el almacenamiento del servidor.
    """
    if 'user_id' not in session or session.get('username') != username:
        abort(403)

    temporada = Temporada.query.filter_by(
        id=temporada_id, user_id=session['user_id']).first()
    if not temporada:
        abort(403)

    partido = Partido.query.filter_by(id=partido_id).first()
    if not partido:
        abort(404)

    # Construir la ruta al archivo
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    print(f"User folder: {user_folder}")
    temporada_folder = os.path.join(user_folder, f"temporada_{temporada_id}")
    partido_folder = os.path.join(
        temporada_folder, liga_path, f"partido_{partido_id}")
    file_path = os.path.join(partido_folder, filename)

    if not os.path.exists(file_path):
        print(f"Archivo no encontrado: {file_path}")
        abort(404)

    # Información de depuración
    print(f"Sirviendo archivo: {file_path}")
    print(f"Tamaño del archivo: {os.path.getsize(file_path)} bytes")

    # Usar send_file para servir el archivo
    return send_file(file_path)


@video_routes.route('/<username>/partido/<int:partido_id>/equipo/<int:equipo_id>/jugadores', methods=['GET'])
def get_jugadores_equipo(username, partido_id, equipo_id):
    """
    Obtener los jugadores de un equipo para un partido específico.
    """
    if 'user_id' not in session or session.get('username') != username:
        return jsonify({'error': 'No autorizado'}), 401

    partido = Partido.query.get_or_404(partido_id)
    temporada = partido.temporada

    if temporada.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 401

    # Obtener jugadores convocados del equipo
    convocados = Convocado.query.filter_by(partido_id=partido_id).join(
        Jugador).filter(Jugador.equipo_id == equipo_id).all()

    jugadores = []
    for convocado in convocados:
        jugador = convocado.jugador
        jugadores.append({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'apellido': jugador.apellido,
            'dorsal': jugador.dorsal,
            'rol': jugador.rol,
            'es_capitan': jugador.es_capitan
        })

    return jsonify({'jugadores': jugadores})


@video_routes.route('/video/<int:video_id>/analisis-automatico', methods=['POST'])
def analisis_automatico(video_id):
    """
    Inicia el análisis automático de un video.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        # Comprobamos si el vídeo existe
        video = Video.query.get_or_404(video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        temporada = partido.temporada
        if temporada.user_id != session['user_id']:
            return jsonify({'error': 'No autorizado'}), 403
        tarea_existente = Tarea.query.filter(
            and_(Tarea.video_id == video_id, Tarea.fecha_completada == None)).first()

        if tarea_existente:
            return jsonify({'error': 'Ya hay un análisis en proceso'}), 400
        # Crear una nueva tarea de análisis automático
        nueva_tarea = Tarea(
            video_id=video_id,
            user_id=session['user_id'],
            fecha_creacion=datetime.utcnow(),
            fecha_completada=None,
            estado=0,  # Estado 0: En progreso
            progreso=0.0,
        )
        db.session.add(nueva_tarea)
        db.session.commit()
        from config import Config
        data = request.get_json()
        print(nueva_tarea)
        req = requests.post(
            f'{Config.MODEL_URL}/analizar',
            json={
                **data,
                'id_tarea': nueva_tarea.id,
            }
        )
        if req.status_code != 202:
            db.session.rollback()
            return jsonify({'error': 'Error al iniciar el análisis automático'}), 500
        print(
            f"Tarea de análisis automático creada para el video {video_id} del partido {partido.id}")
        print(
            f"Iniciando análisis automático para el video {video_id} del partido {partido.id}")
        return jsonify({'success': True, 'message': 'Análisis automático completado con éxito', 
            'progreso': 0.0,
            'id': nueva_tarea.id,
            'fecha': nueva_tarea.fecha_creacion.isoformat(),
            'estado': 0
        })

    except Exception as e:
        print(f"Error durante el análisis automático: {str(e)}")
        return jsonify({'error': f'Error durante el análisis automático: {str(e)}'}), 500


@video_routes.route('/video/<int:tarea_id>/tareas/estado', methods=['GET'])
def estado_tarea(tarea_id):
    print(f"Obteniendo estado de la tarea {tarea_id}")
    """
    Obtiene el estado de una tarea de análisis automático.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    tarea = Tarea.query.get_or_404(tarea_id)

    if tarea.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 403

    estado = {
        'id': tarea.id,
        'video_id': tarea.video_id,
        'fecha_creacion': tarea.fecha_creacion.isoformat(),
        'fecha_completada': tarea.fecha_completada.isoformat() if tarea.fecha_completada else None,
        'estado': tarea.estado,
        'progreso': tarea.progreso
    }

    return jsonify(estado)


@video_routes.route('/video/<int:render_id>/render/estado', methods=['GET'])
def estado_descarga(render_id):
    """
    Obtiene el estado de la descarga de un video.
    """
    print(f"Obteniendo estado de la descarga {render_id}")
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    descarga = Descarga.query.get(render_id)
    if not descarga:
        return jsonify({'error': 'Descarga no encontrada'}), 404

    estado = {
        'id': descarga.id,
        'tarea_id': descarga.tarea_id,
        'fecha_creacion': descarga.fecha_creacion.isoformat(),
        'fecha_completada': descarga.fecha_completada.isoformat() if descarga.fecha_completada else None,
        'estado': descarga.estado,
        'progreso': descarga.progreso
    }

    return jsonify(estado)


@video_routes.route('/video/analisis-automatico/<int:tarea_id>', methods=['DELETE'])
def cancelar_tarea(tarea_id):
    """
    Cancela una tarea de análisis automático.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    tarea = Tarea.query.get_or_404(tarea_id)

    print(tarea)

    if tarea.user_id != session['user_id']:
        return jsonify({'error': 'No autorizado'}), 403

    if tarea.estado != 0 and tarea.estado != 3:  # Si la tarea ya está completada
        return jsonify({'error': 'La tarea ya está completada'}), 400

    tarea.fecha_completada = datetime.utcnow()
    tarea.estado = 2  # Estado 2 Cancelada
    db.session.commit()

    print(f"Tarea {tarea_id} cancelada por el usuario {session['username']}")

    return jsonify({'success': True, 'message': 'Tarea cancelada con éxito'})


@video_routes.route('/<username>/analisis-automatico/<int:tarea_id>/mot', methods=['GET'])
def ver_resultados_analisis(username, tarea_id):
    """
    Muestra los resultados del análisis automático de un video.
    """

    print(
        f"Resultados del análisis automático para la tarea {tarea_id} obtenidos correctamente")
    tarea = Tarea.query.get_or_404(tarea_id)
    if tarea.user_id != session['user_id']:
        flash("No tienes permiso para ver los resultados de esta tarea", "error")
        return redirect(f"/{username}/home")

    video = Video.query.get_or_404(tarea.video_id)
    partido = Partido.query.get_or_404(video.partido_id)
    temporada = partido.temporada
    # Construir la ruta al archivo
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    temporada_folder = os.path.join(user_folder, f"temporada_{temporada.id}")
    liga_path = f"liga_{partido.liga.id}" if partido.liga else "sin_liga"
    partido_folder = os.path.join(
        temporada_folder, liga_path, f"partido_{partido.id}")
    file_path = os.path.join(
        partido_folder, video.filename.replace(".mp4", f"_{tarea.id}_mot.txt"))
    #get video duration with os

    if not os.path.exists(file_path):
        print(f"Archivo no encontrado: {file_path}")
    with open(file_path, 'r', encoding="utf-8") as f:
        motTxt = f.read().splitlines()
    indexedByFrame = {}
    for line in motTxt:
        frame_id = int(float(line.split(",")[0]))

        if frame_id not in indexedByFrame:
            indexedByFrame[frame_id] = []
        indexedByFrame[frame_id].append(line)
    jugadores_tracking = JugadorTracking.query.filter_by(tarea_id = tarea_id).all()
    print(jugadores_tracking)
    jugadores_tracking_data = {}
    for jugador in jugadores_tracking:
        jug = Jugador.query.get(jugador.jugador_id)
        if jug:
            jugadores_tracking_data[int(jugador.id)] = jug.nombre
    return jsonify({
        'motTxt': indexedByFrame,
        'fps': video.fps,
        'jugadores_tracking': jugadores_tracking_data
    })


def aplicar_cambios_mot(mot_path, cambios):
    # Leer todas las líneas
    with open(mot_path, "r") as f:
        lineas = f.readlines()

    nuevas_lineas = []
    for linea in lineas:
        partes = linea.strip().split(",")

        if len(partes) < 2:  # línea inválida
            nuevas_lineas.append(linea)
            continue

        frame = int(partes[0])
        obj_id = partes[1]

        for cambio in cambios:
            if frame >= cambio["startFrame"] and obj_id == str(cambio["oldId"]):
                partes[1] = str(cambio["newId"])  # reemplazar el ID
                break  # aplicar solo el primer cambio que coincida

        nuevas_lineas.append(",".join(partes) + "\n")

    # Guardar archivo actualizado (sobreescribe)
    with open(mot_path, "w") as f:
        f.writelines(nuevas_lineas)


@video_routes.route('/video/analisis-automatico/<int:analisis_id>', methods=['POST'])
def actualizar_analisis(analisis_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        raw = request.get_data()  # bytes

        # (Opcional) Soportar gzip si lo mandas comprimido
        if request.headers.get('Content-Encoding') == 'gzip':
            import gzip
            raw = gzip.decompress(raw)

        text = raw.decode('utf-8', errors='replace')  # str

        tarea = Tarea.query.get_or_404(analisis_id)
        video = Video.query.get_or_404(tarea.video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        temporada = partido.temporada

        user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
        temporada_folder = os.path.join(user_folder, f"temporada_{temporada.id}")
        liga_path = f"liga_{partido.liga.id}" if partido.liga else "sin_liga"
        partido_folder = os.path.join(temporada_folder, liga_path, f"partido_{partido.id}")
        os.makedirs(partido_folder, exist_ok=True)  # asegúrate de que exista

        file_path = os.path.join(partido_folder, video.filename.replace(".mp4", f"_{tarea.id}_mot.txt"))
        print(f"Guardando análisis actualizado en: {file_path}")
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    except Exception as e:
        print(f"Error al actualizar análisis {analisis_id}: {e}")
        return jsonify({'error': 'Error al actualizar análisis'}), 500

    return jsonify({'success': True, 'message': 'Análisis actualizado con éxito'})



@video_routes.route('/video/analisis-automatico/<int:analisis_id>/renderizar', methods=['POST'])
def renderizar_analisis(analisis_id):
    """
    Renderiza los resultados del análisis automático de un video.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        blur = request.get_json().get("blur", False)
        tarea = Tarea.query.get_or_404(analisis_id)
        video = Video.query.get_or_404(tarea.video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        temporada = partido.temporada
        # Construir la ruta al archivo
        user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
        temporada_folder = os.path.join(
            user_folder, f"temporada_{temporada.id}")
        liga_path = f"liga_{partido.liga.id}" if partido.liga else "sin_liga"
        partido_folder = os.path.join(
            temporada_folder, liga_path, f"partido_{partido.id}")
        file_path = os.path.join(
            partido_folder, video.filename.replace(".mp4", f"_{analisis_id}_mot.txt"))
        output_path = os.path.join(partido_folder, video.filename.replace(
            ".mp4", f"_output_{tarea.id}.mp4"))
        if os.path.exists(output_path):
            os.remove(output_path)

        nueva_descarga = Descarga(
            user_id=session['user_id'],
            tarea_id=tarea.id,
            estado=0
        )
        db.session.add(nueva_descarga)
        db.session.commit()
        print(f"Render iniciada: {nueva_descarga.id}")
        print(
            f"Ruta de entrada: {os.path.join(partido_folder, video.filename)}")
        print(f"Ruta de MOT: {file_path}")
        print(f"Ruta de salida: {output_path}")
        print(f"Blur: {blur}")
        jugadores_track = JugadorTracking.query.filter_by(tarea_id = tarea.id).all()
        datos_jugadores = {}
        for jugador_track in jugadores_track:
            jugadorObj = Jugador.query.get(jugador_track.jugador_id)
            if jugadorObj:
                datos_jugadores[jugador_track.id] = jugadorObj.nombre
        thread = Thread(target=render_video_with_boxes, args=(os.path.join(
            partido_folder, video.filename), file_path, output_path, nueva_descarga.id, blur, datos_jugadores))
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Renderizado iniciado con éxito',
            'id': nueva_descarga.id
        }), 202
    except Exception as e:
        print(f"Error al renderizar análisis {analisis_id}: {e}")
        return jsonify({'error': 'Error al renderizar análisis'}), 500


@video_routes.route('/video/descarga/<int:descarga_id>/archivo', methods=['GET'])
def descargar_render(descarga_id):
    """
    Descarga el archivo de renderizado de un video.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        descarga = Descarga.query.get_or_404(descarga_id)
        if descarga.estado != 1:
            return jsonify({'error': 'El renderizado no está completo'}), 400
        tarea = Tarea.query.get_or_404(descarga.tarea_id)
        video = Video.query.get_or_404(tarea.video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        temporada = partido.temporada
        user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
        temporada_folder = os.path.join(
            user_folder, f"temporada_{temporada.id}")
        liga_path = f"liga_{partido.liga.id}" if partido.liga else "sin_liga"
        partido_folder = os.path.join(
            temporada_folder, liga_path, f"partido_{partido.id}")
        output_path = os.path.join(
            partido_folder, f"{video.filename.replace('.mp4', '')}_output_{tarea.id}.mp4")
        print(f"Descargando archivo: {output_path}")
        if not os.path.exists(output_path):
            return jsonify({'error': 'Archivo no encontrado'}), 404
        print(f"Archivo encontrado: {output_path}")
        return send_file(
            os.path.abspath(output_path),
            as_attachment=True,
            download_name=f"video_{descarga_id}.mp4"
        )

    except Exception as e:
        print(f"Error al descargar render {descarga_id}: {e}")
        return jsonify({'error': 'Error al descargar render'}), 500


@video_routes.route('/video/descarga/<int:descarga_id>/archivo', methods=['DELETE'])
def eliminar_render(descarga_id):
    """
    Elimina el archivo de renderizado de un video.
    """
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        descarga = Descarga.query.get_or_404(descarga_id)
        if descarga.estado == 3:
            db.session.delete(descarga)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Render eliminado'}), 200
        if descarga.estado != 1:
            return jsonify({'error': 'El renderizado no está completo'}), 400
        tarea = Tarea.query.get_or_404(descarga.tarea_id)
        video = Video.query.get_or_404(tarea.video_id)
        partido = Partido.query.get_or_404(video.partido_id)
        temporada = partido.temporada
        user_folder = os.path.join(UPLOAD_FOLDER, session['username'])
        temporada_folder = os.path.join(
            user_folder, f"temporada_{temporada.id}")
        liga_path = f"liga_{partido.liga.id}" if partido.liga else "sin_liga"
        partido_folder = os.path.join(
            temporada_folder, liga_path, f"partido_{partido.id}")
        output_path = os.path.join(
            partido_folder, f"{video.filename.replace('.mp4', '')}_output_{tarea.id}.mp4")
        print(f"Eliminando archivo: {output_path}")
        db.session.delete(descarga)
        db.session.commit()
        if os.path.exists(output_path):
            os.remove(output_path)
        return jsonify({'success': True, 'message': 'Archivo eliminado'}), 200

    except Exception as e:
        print(f"Error al eliminar render {descarga_id}: {e}")
        return jsonify({'error': 'Error al eliminar render'}), 500


@video_routes.route('/video/analisis-automatico/<int:tarea_id>/jugadores-asignados', methods=['GET'])
def obtenerJugadoresAsignados(tarea_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        tarea = Tarea.query.get_or_404(tarea_id)
        if tarea.user_id != session['user_id']:
            return jsonify({'error': 'No autorizado'}), 403
        jugadores_asignados = JugadorTracking.query.filter_by(tarea_id=tarea.id).all()
        jugadores = {}
        for jugador in jugadores_asignados:
            if jugador.jugador_id not in jugadores:
                jugadores[jugador.jugador_id] = []
            jugadores[jugador.jugador_id].append(jugador.id)
        return jsonify({'success': True, 'jugadores_asignados': jugadores}), 200
    except Exception as e:
        print(f"Error al obtener jugadores asignados para la tarea {tarea_id}: {e}")
        return jsonify({'error': 'Error al obtener jugadores asignados'}), 500

@video_routes.route('/video/analisis-automatico/<int:tarea_id>/jugadores-asignados', methods=['POST'])
def guardar_asignaciones(tarea_id):
    if 'user_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        data = request.get_json()
        JugadorTracking.query.filter_by(tarea_id=tarea_id).delete()
        db.session.commit()

        for jugador_id, tracking_ids in data.items():
            for tracking_id in tracking_ids:
                nuevo_tracking = JugadorTracking(jugador_id=jugador_id, tarea_id=tarea_id, id=tracking_id)
                db.session.add(nuevo_tracking)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asignaciones guardadas'}), 200
    except Exception as e:
        print(f"Error al guardar asignaciones para la tarea {tarea_id}: {e}")
        return jsonify({'error': 'Error al guardar asignaciones'}), 500
