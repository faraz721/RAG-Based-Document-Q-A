import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")

MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))
MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
TOP_K = int(os.getenv("TOP_K", "5"))

# Session TTL in minutes — inactive sessions (and their files) are deleted
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "45"))

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
MIME_MAP = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}

DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
INDEX_DIR = DATA_DIR / "indexes"
METADATA_FILE = DATA_DIR / "metadata.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
