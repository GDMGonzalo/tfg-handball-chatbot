from flask import Flask, request, jsonify
from threading import Thread
from tools.analysis import lanzar_analisis

app = Flask(__name__)

@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200

@app.route("/analizar", methods=["POST"])
def analizar():
    try:
        params = request.get_json()
        print(f"Parámetros recibidos: {params}")

        # Campos obligatorios comunes
        campos_obligatorios = [
            "modelo",
            "id_tarea",
            "postprocess",
            "TRACK_HIGH_THRESH",
            "TRACK_LOW_THRESH",
            "NEW_TRACK_THRESH",
            "TRACK_BUFFER",
            "MATCH_THRESH",
            "ASPECT_RATIO_THRESH",
            "MIN_BOX_AREA",
            "NMS_THRES",
            "PROXIMITY_THRESH",
            "APPEARANCE_THRESH"
        ]

        for campo in campos_obligatorios:
            if campo not in params:
                print(f"Campo faltante: {campo}")
                return jsonify({"error": f"Falta el campo: {campo}"}), 400

        if params.get("postprocess"):
            if "postprocess_params" not in params:
                return jsonify({"error": "Falta el bloque postprocess_params"}), 400

            campos_post = [
                "USE_SPLIT",
                "MIN_LEN",
                "EPS",
                "MIN_SAMPLES",
                "MAX_K",
                "USE_CONNECT",
                "SPATIAL_FACTOR",
                "MERGE_DIST_THRESH",
            ]
            for campo in campos_post:
                if campo not in params["postprocess_params"]:
                    return jsonify({"error": f"Falta el campo de postprocesado: {campo}"}), 400

        thread = Thread(target=lanzar_analisis, args=(params, params["id_tarea"]))
        thread.start()

        return jsonify({
            "mensaje": "Inferencia iniciada en background"
        }), 202

    except Exception as e:
        print(f"Error al iniciar la inferencia: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)