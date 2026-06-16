import cv2
import os

def generate_dataset(video_path, output_path):
    # Crear carpeta si no existe
    if os.path.exists(output_path):
        # Limpiar carpeta existente
        for f in os.listdir(output_path):
            os.remove(os.path.join(output_path, f))
    os.makedirs(output_path, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    frame_id = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_name = f"{output_path}/img{frame_id:06d}.jpg"
        cv2.imwrite(frame_name, frame)
        frame_id += 1

    cap.release()
    print(f"Frames extraídos en {output_path}")
