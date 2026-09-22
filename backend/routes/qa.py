from flask import Blueprint, request, jsonify
from services import qa_service
from utils.session import valid_session_id

qa_bp = Blueprint("qa", __name__)


@qa_bp.route("/ask", methods=["POST"])
def ask():
    try:
        sid = (request.headers.get("X-Session-Id") or "").strip()
        if not valid_session_id(sid):
            return jsonify({"error": "Invalid or missing session. Please refresh the page."}), 400

        data = request.get_json(silent=True) or {}
        doc_id = (data.get("doc_id") or "").strip()
        question = (data.get("question") or "").strip()

        if not doc_id:
            return jsonify({"error": "Please select a document first."}), 400
        if not question:
            return jsonify({"error": "Please enter a question."}), 400

        result = qa_service.answer_question(doc_id, question, sid)
        return jsonify({"success": True, **result})

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "An unexpected error occurred while generating the answer."}), 500
