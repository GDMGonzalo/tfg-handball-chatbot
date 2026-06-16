from flask import Flask, request, jsonify
from threading import Thread
from generate_tracklets import lanzar_analisis

app = Flask(__name__)

@app.get("/healthz")
def healthz():
    return jsonify(status="ok"), 200

@app.route("/postprocesado", methods=["POST"])
def postprocesado():
    try:
        params = request.get_json()
        campos_obligatorios = [
            'tarea_id',
            "USE_SPLIT",
            "MIN_LEN",
            "EPS",
            "MIN_SAMPLES",
            "MAX_K",
            "USE_CONNECT",
            "SPATIAL_FACTOR",
            "MERGE_DIST_THRESH"
        ]
        for campo in campos_obligatorios:
            if campo not in params:
                print(f"Campo faltante: {campo}")
                return jsonify({'error': f'Falta el campo: {campo}'}), 400

        thread = Thread(target=lanzar_analisis, args=(
            params['tarea_id'],
            params
        ))
        thread.start()

        return jsonify({
            "mensaje": "Inferencia iniciada en background"
        }), 202

    except Exception as e:
        print(f"Error al iniciar la inferencia: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
