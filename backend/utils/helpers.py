import re
import uuid
from pathlib import Path
from werkzeug.utils import secure_filename
from .config import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def safe_filename(original_name: str) -> str:
    """Create a safe unique filename while preserving extension."""
    name = secure_filename(original_name)
    if not name:
        name = "document"
    stem = Path(name).stem[:80]
    ext = Path(name).suffix.lower()
    unique = uuid.uuid4().hex[:10]
    return f"{stem}_{unique}{ext}"


def is_safe_path(base_dir: Path, target: Path) -> bool:
    """Prevent path traversal."""
    try:
        base = base_dir.resolve()
        target_resolved = target.resolve()
        return str(target_resolved).startswith(str(base))
    except Exception:
        return False


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
