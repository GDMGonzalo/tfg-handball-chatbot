from flask import Blueprint, render_template, request, jsonify, session, redirect
from services.chatbot_service import ChatbotService

chatbot_bp = Blueprint("chatbot", __name__)


def _session_ok(username: str) -> bool:
    return session.get("user_id") is not None and session.get("username") == username


@chatbot_bp.route("/<username>/chatbot", methods=["GET"])
def chatbot_index(username):
    if not _session_ok(username):
        return redirect("/login")
    return render_template("chatbot/index.html", username=username)


@chatbot_bp.route("/<username>/chatbot/query", methods=["POST"])
def chatbot_query(username):
    if not _session_ok(username):
        return jsonify({"error": "No autorizado"}), 401

    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "La pregunta no puede estar vacía"}), 400

    service = ChatbotService(session["user_id"])
    answer = service.process_question(question)

    return jsonify({"answer": answer})