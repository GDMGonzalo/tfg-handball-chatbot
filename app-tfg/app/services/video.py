import cv2, os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Descarga
from config import Config  
import datetime

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)


def render_video_with_boxes(input_video, mot_file, output_video, descarga_id, blur_faces=False, jugadoresTracking = {}):
    session = Session()
    try:
    # Verificar que el archivo MOT existe
        if not os.path.exists(mot_file):
            raise FileNotFoundError(f"No se encontró {mot_file}")

        # Cargar el video original
        cap = cv2.VideoCapture(input_video)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Configurar el escritor de video
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec para MP4
        out = cv2.VideoWriter(output_video, fourcc, fps, (frame_width, frame_height))

        # Leer las anotaciones de MOT
        annotations = {}
        descarga = session.query(Descarga).get(descarga_id)
        if not descarga:
            return
        with open(mot_file, "r") as f:
            for line in f:
                values = line.strip().split(',')
                if len(values) < 7:
                    continue  # Evitar líneas incompletas

                frame_id = int(float(values[0]))
                track_id = int(float(values[1]))
                x, y, w, h = map(float, values[2:6])
                confidence = float(values[6])

                if frame_id not in annotations:
                    annotations[frame_id] = []
                annotations[frame_id].append((track_id, x, y, w, h, confidence))

        # Procesar frame a frame
        frame_id = 0
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break  # Fin del video

            if frame_id in annotations:
                for track_id, x, y, w, h, confidence in annotations[frame_id]:
                    # Coordenadas MOT -> OpenCV
                    x1 = int(x)
                    y1 = int(y)
                    x2 = int(x + w)
                    y2 = int(y + h)

                    # Dibujar caja y texto
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    if jugadoresTracking.get(int(track_id)):
                        cv2.putText(frame, str(jugadoresTracking.get(int(track_id))), 
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                                (0, 255, 0), 2)
                    else:
                        cv2.putText(frame, f"ID: {track_id} ({confidence:.2f})", 
                                (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, 
                                (0, 255, 0), 2)

                    # Si se pide, aplicar blur en la cara (30% superior del box)
                    if blur_faces:
                        face_h = int(0.3 * h)  # 30% superior
                        face_region = frame[y1:y1+face_h, x1:x2]

                        if face_region.size > 0:
                            # Aplicar blur
                            blurred = cv2.GaussianBlur(face_region, (51, 51), 30)
                            frame[y1:y1+face_h, x1:x2] = blurred

            # Guardar frame procesado
            out.write(frame)

            if frame_id % 10 == 0:
                descarga.progreso = int((frame_id / (cap.get(cv2.CAP_PROP_FRAME_COUNT))) * 100)
                session.commit()
            frame_id += 1
            


        # Liberar recursos
        cap.release()
        out.release()
        descarga.progreso = 100
        descarga.estado = 1
        descarga.fecha_completada = datetime.datetime.now()
        session.commit()
    except Exception as e:
        print(e)
        descarga = session.query(Descarga).get(descarga_id)
        descarga.estado = 3
        descarga.fecha_completada = datetime.datetime.now()
        session.commit()
    finally:
        session.close()

    print(f"Video guardado en {output_video}")
