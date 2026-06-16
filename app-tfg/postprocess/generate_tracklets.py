# This script produces tracklets given tracking results and original sequence frame as RGB images.
import argparse
from torchreid.utils import FeatureExtractor

import os, shutil
from tqdm import tqdm
from loguru import logger
from PIL import Image

import pickle
import numpy as np
import glob

import torch
import torchvision.transforms as T
from Tracklet import Tracklet
from tools.generate_dataset import generate_dataset
from config import Config
from refine_tracklets import main as refine
import mysql.connector

conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )

TAREA_ID = None
def esta_cancelada(id_tarea):
    cursor = conn.cursor()
    query = "SELECT estado FROM tareas WHERE id = %s"
    cursor.execute(query, (id_tarea,))
    result = cursor.fetchone()
    cursor.close()
    
    if result and result[0] == 2:
        return True
    return False
def actualizar_porcentaje(id_tarea, porcentaje):
    cursor = conn.cursor()
    query = "UPDATE tareas SET progreso = %s WHERE id = %s"
    cursor.execute(query, (porcentaje, id_tarea))
    conn.commit()
    cursor.close()

def actualizar_estado(id_tarea, estado):
    cursor = conn.cursor()
    query = "UPDATE tareas SET estado = %s WHERE id = %s"
    cursor.execute(query, (estado, id_tarea))
    conn.commit()
    cursor.close()

def actualizar_fecha_fin(id_tarea):
    cursor = conn.cursor()
    query = "UPDATE tareas SET fecha_completada = NOW() WHERE id = %s"
    cursor.execute(query, (id_tarea,))
    conn.commit()
    cursor.close()

def obtener_nombre_mot(tarea_id):
    cursor = conn.cursor()
    query = " SELECT u.username, l.temporada_id, l.id, v.partido_id, v.filename FROM videos v  JOIN partidos p ON v.partido_id = p.id JOIN liga l ON p.liga_id = l.id JOIN tareas t ON t.video_id = v.id  JOIN users u ON t.user_id = u.id WHERE t.id = %s"
    cursor.execute(query, (tarea_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

def main(data_path, pred_dir):
    # load feature extractor:
    val_transforms = T.Compose([
            T.Resize([256, 128]),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    extractor = FeatureExtractor(
        model_name='osnet_x1_0',
        model_path = os.path.join(os.path.pardir, "reid_checkpoints/sports_model.pth.tar-60"),
        device=device
    )

    output_dir = Config.UPLOAD_FOLDER  # output directory for sequences' tracklets
    os.makedirs(output_dir, exist_ok=True)

    # seqs = sorted([file for file in os.listdir(pred_dir) if file.endswith('.txt')])
    filename = os.path.basename(pred_dir)
    seqs = sorted([filename])

    for s_id, seq in tqdm(enumerate(seqs, 1), total=len(seqs), desc='Processing Seqs'):
        seq = seq.replace('.txt','')
        imgs = sorted(glob.glob(os.path.join(data_path, '*')))   # assuming data is organized in MOT convention
        # track_res = np.genfromtxt(os.path.join(pred_dir, f'{seq}.txt'),dtype=float, delimiter=',')
        track_res = np.genfromtxt(pred_dir, dtype=float, delimiter=',')

        last_frame = int(track_res[-1][0])
        seq_tracks = {}

        for frame_id in range(1, last_frame+1):
            if frame_id%100 == 0:
                logger.info(f'Processing frame {frame_id}/{last_frame}')
                if esta_cancelada(TAREA_ID):
                    logger.info(f'Tarea {TAREA_ID} cancelada. Abortando procesamiento.')
                    return None
                porcentaje = 50 + (frame_id / last_frame) * (75 - 50)
                actualizar_porcentaje(TAREA_ID, porcentaje)
            # query all track_res for current frame
            inds = track_res[:,0] == frame_id
            frame_res = track_res[inds]
            img = Image.open(imgs[int(frame_id)-1])
            
            input_batch = None    # input batch to speed up processing
            tid2idx = {}
            
            # NOTE MOT annotation format:
            # <frame>, <id>, <bb_left>, <bb_top>, <bb_width>, <bb_height>, <conf>, <x>, <y>, <z>
            for idx, (frame, track_id, l, t, w, h, score, _, _, _) in enumerate(frame_res):
                # Update tracklet with detection
                bbox = [l, t, w, h]
                if track_id not in seq_tracks:
                    seq_tracks[track_id] = Tracklet(track_id, frame, score, bbox)
                else:
                    seq_tracks[track_id].append_det(frame, score, bbox)
                tid2idx[track_id] = idx

                im = img.crop((l, t, l+w, t+h)).convert('RGB')
                im = val_transforms(im).unsqueeze(0)
                if input_batch is None:
                        input_batch = im
                else:
                    input_batch = torch.cat([input_batch, im], dim=0)
            
            if input_batch is not None:
                features = extractor(input_batch)    # len(features) == len(frame_res)
                feats = features.cpu().detach().numpy()
                
                # update tracklets with feature
                for tid, idx in tid2idx.items():
                    feat = feats[tid2idx[tid]]
                    feat /= np.linalg.norm(feat)
                    seq_tracks[tid].append_feat(feat)
            else:
                print(f"No detection at frame: {frame_id}")
        
        # save seq_tracks into pickle file
        output_path = os.path.join(output_dir, seq)
        track_output_path = os.path.join(output_dir, seq, f'{seq}.pkl')
        if not os.path.exists(os.path.dirname(track_output_path)):
            os.makedirs(os.path.dirname(track_output_path))
        with open(track_output_path, 'wb') as f:
            pickle.dump(seq_tracks, f)
        logger.info(f"save tracklets info to {track_output_path}")
        actualizar_porcentaje(TAREA_ID, 75)
        return output_path



def lanzar_analisis(tareaid, params):
    global TAREA_ID
    TAREA_ID = tareaid
    try:
        path = obtener_nombre_mot(tareaid)
        video_path = os.path.join(Config.UPLOAD_FOLDER, path[0], f"temporada_{path[1]}", f"liga_{path[2]}", f"partido_{path[3]}", path[4])
        generate_dataset(video_path, f"{Config.UPLOAD_FOLDER}/data/{tareaid}")
        mot_path = os.path.join(os.path.dirname(video_path), f"{os.path.basename(video_path).replace('.mp4','')}_{tareaid}_mot.txt")
        tracklets = main(f"{Config.UPLOAD_FOLDER}/data/{tareaid}", mot_path)
        if os.path.exists(f"{Config.UPLOAD_FOLDER}/data/{tareaid}"):
            shutil.rmtree(f"{Config.UPLOAD_FOLDER}/data/{tareaid}")
        if tracklets is not None:
            output_path = os.path.join(Config.UPLOAD_FOLDER, path[0], f"temporada_{path[1]}", f"liga_{path[2]}", f"partido_{path[3]}", f"{path[4].replace('.mp4',f'_{tareaid}_mot.txt')}")
            if os.path.exists(output_path):
                os.remove(output_path)
            refine(tracklets, output_path, params)
            actualizar_porcentaje(tareaid, 100)
            actualizar_estado(tareaid, 1)
            actualizar_fecha_fin(tareaid)
    except Exception as e:
        logger.error(f"Error en la tarea {tareaid}: {e}")
        actualizar_estado(tareaid, 4)
        actualizar_fecha_fin(tareaid)

