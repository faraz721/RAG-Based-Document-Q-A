import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from utils.config import (
    FLASK_SECRET_KEY,
    MAX_CONTENT_LENGTH,
    ROOT_DIR,
    GROQ_API_KEY,
    SESSION_TTL_MINUTES,
)
from utils.session import cleanup_expired_sessions
from rag.vector_store import get_store
from routes.documents import documents_bp
from routes.qa import qa_bp

FRONTEND_DIR = ROOT_DIR / "frontend"


def create_app():
    app = Flask(__name__, static_folder=None)
    app.secret_key = FLASK_SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        expose_headers=["X-Session-Id"],
        allow_headers=["Content-Type", "X-Session-Id"],
    )

    app.register_blueprint(documents_bp, url_prefix="/api/documents")
    app.register_blueprint(qa_bp, url_prefix="/api/qa")

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/css/<path:filename>")
    def serve_css(filename):
        return send_from_directory(FRONTEND_DIR / "css", filename)

    @app.route("/js/<path:filename>")
    def serve_js(filename):
        return send_from_directory(FRONTEND_DIR / "js", filename)

    @app.route("/health")
    def health():
        # Cleanup expired sessions when health is pinged (e.g. UptimeRobot every 5 min)
        cleaned = 0
        try:
            cleaned = cleanup_expired_sessions(get_store())
        except Exception:
            pass
        return jsonify(
            {
                "status": "ok",
                "groq_configured": bool(GROQ_API_KEY),
                "session_ttl_minutes": SESSION_TTL_MINUTES,
                "sessions_cleaned": cleaned,
            }
        )

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File is too large. Please upload a smaller document."}), 413

    @app.errorhandler(404)
    def not_found(e):
        path = request.path or ""
        if path.startswith("/api/") or path.startswith("/css/") or path.startswith("/js/"):
            return jsonify({"error": "Not found.", "path": path}), 404
        return send_from_directory(FRONTEND_DIR, "index.html")

    return app


app = create_app()

if __name__ == "__main__":
    print(f"Frontend dir: {FRONTEND_DIR} (exists={FRONTEND_DIR.exists()})")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=True)
