import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

from utils.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from utils.helpers import allowed_file, get_extension, safe_filename, is_safe_path
from utils.session import valid_session_id, touch_session, cleanup_expired_sessions
from rag.document_loader import extract_text
from rag.chunker import create_chunks
from rag.embeddings import embed_texts
from rag.vector_store import get_store


def process_upload(file_storage, session_id: str) -> Dict[str, Any]:
    if not valid_session_id(session_id):
        raise ValueError("Invalid or missing session. Please refresh the page.")

    cleanup_expired_sessions(get_store())
    touch_session(session_id)

    original_name = file_storage.filename or "document"
    if not allowed_file(original_name):
        raise ValueError("Unsupported file type. Allowed: PDF, DOC, DOCX, TXT.")

    extension = get_extension(original_name)
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file extension.")

    filename = safe_filename(original_name)
    save_path = UPLOAD_DIR / filename
    if not is_safe_path(UPLOAD_DIR, save_path):
        raise ValueError("Invalid file path.")

    file_storage.save(str(save_path))

    try:
        pages = extract_text(save_path, extension)
    except ValueError as e:
        if save_path.exists():
            save_path.unlink()
        raise ValueError(str(e))

    if not pages or all(not p.get("text", "").strip() for p in pages):
        if save_path.exists():
            save_path.unlink()
        raise ValueError("The document appears to be empty or contains no extractable text.")

    doc_id = uuid.uuid4().hex
    chunks = create_chunks(pages, doc_id, original_name)
    if not chunks:
        if save_path.exists():
            save_path.unlink()
        raise ValueError("Could not create text chunks from the document.")

    try:
        texts = [c["text"] for c in chunks]
        embeddings = embed_texts(texts)
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise ValueError(f"Failed to generate embeddings: {str(e)}")

    uploaded_at = datetime.now(timezone.utc).isoformat()
    store = get_store()
    try:
        store.add_document(
            doc_id=doc_id,
            original_name=original_name,
            filename=filename,
            extension=extension,
            chunks=chunks,
            embeddings=embeddings,
            uploaded_at=uploaded_at,
            session_id=session_id,
        )
    except Exception as e:
        if save_path.exists():
            save_path.unlink()
        raise ValueError(f"Failed to index document: {str(e)}")

    return {
        "id": doc_id,
        "filename": filename,
        "original_name": original_name,
        "extension": extension,
        "num_chunks": len(chunks),
        "uploaded_at": uploaded_at,
        "status": "ready",
    }


def list_documents(session_id: str) -> List[Dict[str, Any]]:
    if not valid_session_id(session_id):
        raise ValueError("Invalid or missing session. Please refresh the page.")
    cleanup_expired_sessions(get_store())
    touch_session(session_id)
    return get_store().list_documents(session_id=session_id)


def get_document(doc_id: str, session_id: str) -> Dict[str, Any]:
    if not valid_session_id(session_id):
        raise ValueError("Invalid or missing session. Please refresh the page.")
    touch_session(session_id)
    doc = get_store().get_document(doc_id, session_id=session_id)
    if not doc:
        raise ValueError("Document not found.")
    return doc


def delete_documents(doc_ids: List[str], session_id: str) -> Dict[str, Any]:
    if not valid_session_id(session_id):
        raise ValueError("Invalid or missing session. Please refresh the page.")
    if not doc_ids:
        raise ValueError("No documents selected for deletion.")
    touch_session(session_id)
    actually_deleted = get_store().delete_documents(doc_ids, session_id=session_id)
    return {"deleted": actually_deleted, "count": len(actually_deleted)}
