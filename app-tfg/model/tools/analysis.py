import os
import os.path as osp
import numpy as np
import time
import cv2
import torch
import sys
from argparse import Namespace
from config import Config
import requests

sys.path.append('.')

from loguru import logger

from yolox.data.data_augment import preproc
from yolox.exp import get_exp
from yolox.utils import fuse_model, get_model_info, postprocess
from yolox.utils.visualize import plot_tracking
from yolox.tracking_utils.timer import Timer

from tracker.Deep_EIoU import Deep_EIoU
from reid.torchreid.utils import FeatureExtractor
import torchvision.transforms as T
import mysql.connector

IMAGE_EXT = [".jpg", ".jpeg", ".webp", ".bmp", ".png"]
ID_TAREA = None
POSTPROCESADO = True
MODEL_PARAMS = None

conn = mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )

def get_image_list(path):
    image_names = []
    for maindir, subdir, file_name_list in os.walk(path):
        for filename in file_name_list:
            apath = osp.join(maindir, filename)
            ext = osp.splitext(apath)[1]
            if ext in IMAGE_EXT:
                image_names.append(apath)
    return image_names


def write_results(filename, results):
    save_format = '{frame},{id},{x1},{y1},{w},{h},{s},-1,-1,-1\n'
    with open(filename, 'w') as f:
        for frame_id, tlwhs, track_ids, scores in results:
            for tlwh, track_id, score in zip(tlwhs, track_ids, scores):
                if track_id < 0:
                    continue
                x1, y1, w, h = tlwh
                line = save_format.format(frame=frame_id, id=track_id, x1=round(x1, 1), y1=round(y1, 1), w=round(w, 1), h=round(h, 1), s=round(score, 2))
                f.write(line)
    logger.info('save results to {}'.format(filename))


class Predictor(object):
    def __init__(
        self,
        model,
        exp,
        trt_file=None,
        decoder=None,
        device="cuda" if torch.cuda.is_available() else "cpu",
        fp16=False
    ):
        self.model = model
        self.decoder = decoder
        self.num_classes = exp.num_classes
        self.confthre = exp.test_conf
        self.nmsthre = exp.nmsthre
        self.test_size = exp.test_size
        self.device = device
        self.fp16 = fp16
        self.rgb_means = (0.485, 0.456, 0.406)
        self.std = (0.229, 0.224, 0.225)

    def inference(self, img, timer):
        img_info = {"id": 0}
        if isinstance(img, str):
            img_info["file_name"] = osp.basename(img)
            img = cv2.imread(img)
        else:
            img_info["file_name"] = None

        height, width = img.shape[:2]
        img_info["height"] = height
        img_info["width"] = width
        img_info["raw_img"] = img

        img, ratio = preproc(img, self.test_size, self.rgb_means, self.std)
        img_info["ratio"] = ratio
        img = torch.from_numpy(img).unsqueeze(0).float().to(self.device)
        if self.fp16:
            img = img.half()  # to FP16

        with torch.no_grad():
            timer.tic()
            outputs = self.model(img)
            if self.decoder is not None:
                outputs = self.decoder(outputs, dtype=outputs.type())
            outputs = postprocess(
                outputs, self.num_classes, self.confthre, self.nmsthre
            )
        return outputs, img_info

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

def nombre_video(id_tarea):
    cursor = conn.cursor()
    query = "SELECT filename from videos v JOIN tareas t ON v.id = t.video_id where t.id = %s"
    cursor.execute(query, (id_tarea,))
    result = cursor.fetchone()
    cursor.close()
    if result:
        return result[0]
    return None

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

def imageflow_demo(predictor, extractor, vis_folder, current_time, args):
    if not osp.exists(args.path):
        raise FileNotFoundError(f"Path {args.path} does not exist.")
    cap = cv2.VideoCapture(args.path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # float
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # float
    print(f"Video resolution: {width}x{height}")
    timestamp = time.strftime("%Y_%m_%d_%H_%M_%S", current_time)
    save_folder = osp.join(vis_folder, timestamp)
    os.makedirs(save_folder, exist_ok=True)
    save_path = osp.join(save_folder, args.path.split("/")[-1])
    logger.info(f"video save_path is {save_path}")
    tracker = Deep_EIoU(args, frame_rate=30)
    timer = Timer()
    frame_id = 0
    results = []
    while not esta_cancelada(ID_TAREA):
        if frame_id % 30 == 0:
            logger.info('Processing frame {} ({:.2f} fps)'.format(frame_id, 1. / max(1e-5, timer.average_time)))
            actualizar_porcentaje(ID_TAREA, round(frame_id / cap.get(cv2.CAP_PROP_FRAME_COUNT) * 50, 2))
        ret_val, frame = cap.read()
        if ret_val:
            outputs, _ = predictor.inference(frame, timer)
            if outputs[0] is not None:
                det = outputs[0].cpu().detach().numpy()
                scale = min(1440/width, 800/height)
                det /= scale
                rows_to_remove = np.any(det[:, 0:4] < 1, axis=1) # remove edge detection
                det = det[~rows_to_remove]
                cropped_imgs = [frame[max(0,int(y1)):min(height,int(y2)),max(0,int(x1)):min(width,int(x2))] for x1,y1,x2,y2,_,_,_ in det]
                embs = extractor(cropped_imgs)
                embs = embs.cpu().detach().numpy()
                online_targets = tracker.update(det, embs)
                online_tlwhs = []
                online_ids = []
                online_scores = []
                for t in online_targets:
                    tlwh = t.last_tlwh
                    tid = t.track_id
                    if tlwh[2] * tlwh[3] > args.min_box_area:
                        online_tlwhs.append(tlwh)
                        online_ids.append(tid)
                        online_scores.append(t.score)
                        results.append(
                            f"{frame_id},{tid},{tlwh[0]:.2f},{tlwh[1]:.2f},{tlwh[2]:.2f},{tlwh[3]:.2f},{t.score:.2f},-1,-1,-1\n"
                        )
                timer.toc()
            else:
                timer.toc()
        else:
            break
        frame_id += 1
    nombre = nombre_video(ID_TAREA).replace(".mp4", "")
    remove_ext = os.path.dirname(args.path)
    res_file = osp.join(remove_ext, f"{nombre}_{ID_TAREA}_mot.txt")
    with open(res_file, 'w') as f:
        f.writelines(results)
    logger.info(f"save results to {res_file}")
    if esta_cancelada(ID_TAREA):
        logger.info(f"Tarea {ID_TAREA} cancelada, no se procesará el video.")
        return
    print(f"Postprocesado: {POSTPROCESADO}")
    if POSTPROCESADO == 1:
        actualizar_porcentaje(ID_TAREA, 50)
        actualizar_estado(ID_TAREA, 3)
        postprocess_video()
    else:
        actualizar_porcentaje(ID_TAREA, 100)
        actualizar_estado(ID_TAREA, 1)
        actualizar_fecha_fin(ID_TAREA)


def postprocess_video():
    req = requests.post(Config.POSTPROCESS_URL, json={
        **MODEL_PARAMS['postprocess_params'],
        'tarea_id': ID_TAREA,
    })
    if req.status_code == 202:
        print("Postprocesado iniciado en background")
    else:
        actualizar_estado(ID_TAREA, 4)
        actualizar_fecha_fin(ID_TAREA)


def main(exp, args):
    if not args.experiment_name:
        args.experiment_name = exp.exp_name

    output_dir = osp.join(exp.output_dir, args.experiment_name)
    os.makedirs(output_dir, exist_ok=True)

    vis_folder = osp.join(output_dir, "track_vis")
    os.makedirs(vis_folder, exist_ok=True)

    
    args.device = torch.device("cuda" if args.device == "gpu" else "cpu")

    logger.info("Args: {}".format(args))

    if args.conf is not None:
        exp.test_conf = args.conf
    if args.nms is not None:
        exp.nmsthre = args.nms
    if args.tsize is not None:
        exp.test_size = (args.tsize, args.tsize)

    model = exp.get_model().to(args.device)
    logger.info("Model Summary: {}".format(get_model_info(model, exp.test_size)))
    model.eval()

    if not args.trt:
        if args.ckpt is None:
            ckpt_file = "checkpoints/best_ckpt.pth.tar"
        else:
            ckpt_file = args.ckpt
        logger.info("loading checkpoint")
        ckpt = torch.load(ckpt_file, map_location="cpu")
        # load the model state dict
        model.load_state_dict(ckpt["model"])
        logger.info("loaded checkpoint done.")

    if args.fuse:
        logger.info("\tFusing model...")
        model = fuse_model(model)

    if args.fp16:
        model = model.half()  # to FP16

    if args.trt:
        assert not args.fuse, "TensorRT model is not support model fusing!"
        trt_file = osp.join(output_dir, "model_trt.pth")
        assert osp.exists(
            trt_file
        ), "TensorRT model is not found!\n Run python3 tools/trt.py first!"
        model.head.decode_in_inference = False
        decoder = model.head.decode_outputs
        logger.info("Using TensorRT to inference")
    else:
        trt_file = None
        decoder = None

    predictor = Predictor(model, exp, trt_file, decoder, args.device, args.fp16)
    current_time = time.localtime()
    
    extractor = FeatureExtractor(
        model_name='osnet_x1_0',
        model_path = 'checkpoints/sports_model.pth.tar-60',
        device='cuda' if torch.cuda.is_available() else 'cpu'
    )   

    imageflow_demo(predictor, extractor, vis_folder, current_time, args)

def obtener_nombre_mot(tarea_id):
    cursor = conn.cursor()
    query = " SELECT u.username, l.temporada_id, l.id, v.partido_id, v.filename FROM videos v  JOIN partidos p ON v.partido_id = p.id JOIN liga l ON p.liga_id = l.id JOIN tareas t ON t.video_id = v.id  JOIN users u ON t.user_id = u.id WHERE t.id = %s"
    cursor.execute(query, (tarea_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

def lanzar_analisis(params, id_tarea ):
    data = obtener_nombre_mot(id_tarea)
    path_video = os.path.join(Config.UPLOAD_FOLDER, data[0], f"temporada_{data[1]}", f"liga_{data[2]}", f"partido_{data[3]}", data[4])
    args = Namespace(
        experiment_name="DeepEIoU",
        name="DeepEIoU",
        path=path_video,
        save_result=True,
        exp_file="yolox/yolox_x_ch_sportsmot.py",
        ckpt="checkpoints/best_ckpt.pth.tar",
        device="cuda" if torch.cuda.is_available() else "cpu",
        conf=None,
        nms=None,
        tsize=None,
        fps=30,
        fp16=False,
        fuse=False,
        trt=False,
        track_high_thresh=params.get("TRACK_HIGH_THRESH", Config.TRACK_HIGH_THRESH),
        track_low_thresh=params.get("TRACK_LOW_THRESH", Config.TRACK_LOW_THRESH),
        new_track_thresh=params.get("NEW_TRACK_THRESH", Config.NEW_TRACK_THRESH),
        track_buffer=params.get("TRACK_BUFFER", Config.TRACK_BUFFER),
        match_thresh=params.get("MATCH_THRESH", Config.MATCH_THRESH),
        aspect_ratio_thresh=params.get("ASPECT_RATIO_THRESH", Config.ASPECT_RATIO_THRESH),
        min_box_area=params.get("MIN_BOX_AREA", Config.MIN_BOX_AREA),
        nms_thres=params.get("NMS_THRES", Config.NMS_THRES),
        mot20=Config.MOT20,
        with_reid=Config.WITH_REID,
        proximity_thresh=params.get("PROXIMITY_THRESH", Config.PROXIMITY_THRESH),
        appearance_thresh=params.get("APPEARANCE_THRESH", Config.APPEARANCE_THRESH)
    )
    global ID_TAREA
    global POSTPROCESADO
    global MODEL_PARAMS
    ID_TAREA = id_tarea
    POSTPROCESADO = params.get("postprocess", False)
    MODEL_PARAMS = params
    print(f"ID_TAREA: {ID_TAREA}")
    print(f"args: {args}")
    try:
        exp = get_exp(args.exp_file, args.name)
        main(exp, args)
    except Exception as e:
        print(f"Error en el análisis: {e}")
        actualizar_estado(ID_TAREA, 4)
        actualizar_fecha_fin(ID_TAREA)
