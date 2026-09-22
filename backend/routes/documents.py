from flask import Blueprint, request, jsonify
from services import document_service
from utils.session import valid_session_id

documents_bp = Blueprint("documents", __name__)


def _session_id():
    return (request.headers.get("X-Session-Id") or "").strip()


@documents_bp.route("/upload", methods=["POST"])
def upload():
    try:
        sid = _session_id()
        if not valid_session_id(sid):
            return jsonify({"error": "Invalid or missing session. Please refresh the page."}), 400

        if "file" not in request.files:
            return jsonify({"error": "No file provided."}), 400

        file = request.files["file"]
        if not file or not file.filename:
            return jsonify({"error": "No file selected."}), 400

        result = document_service.process_upload(file, sid)
        return jsonify({"success": True, "document": result}), 201

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "An unexpected error occurred while uploading the document."}), 500


@documents_bp.route("/list", methods=["GET"])
def list_docs():
    try:
        sid = _session_id()
        if not valid_session_id(sid):
            return jsonify({"error": "Invalid or missing session. Please refresh the page."}), 400
        docs = document_service.list_documents(sid)
        return jsonify({"documents": docs})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to list documents."}), 500


@documents_bp.route("/<doc_id>", methods=["GET"])
def get_doc(doc_id):
    try:
        sid = _session_id()
        if not valid_session_id(sid):
            return jsonify({"error": "Invalid or missing session. Please refresh the page."}), 400
        doc = document_service.get_document(doc_id, sid)
        return jsonify({"document": doc})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception:
        return jsonify({"error": "Failed to get document."}), 500


@documents_bp.route("/delete", methods=["POST"])
def delete_docs():
    try:
        sid = _session_id()
        if not valid_session_id(sid):
            return jsonify({"error": "Invalid or missing session. Please refresh the page."}), 400

        data = request.get_json(silent=True) or {}
        doc_ids = data.get("doc_ids") or data.get("ids") or []
        if not isinstance(doc_ids, list):
            return jsonify({"error": "doc_ids must be a list."}), 400

        result = document_service.delete_documents(doc_ids, sid)
        return jsonify({"success": True, **result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        return jsonify({"error": "Failed to delete documents."}), 500
