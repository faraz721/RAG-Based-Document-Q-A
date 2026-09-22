import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss

from utils.config import INDEX_DIR, METADATA_FILE, UPLOAD_DIR
from utils.helpers import is_safe_path


class DocumentStore:
    """Per-document FAISS indexes with session isolation."""

    def __init__(self):
        self.metadata: Dict[str, Any] = {}
        self._load_metadata()

    def _load_metadata(self):
        if METADATA_FILE.exists():
            try:
                self.metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
            except Exception:
                self.metadata = {}
        else:
            self.metadata = {}

    def _save_metadata(self):
        METADATA_FILE.write_text(
            json.dumps(self.metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _index_path(self, doc_id: str) -> Path:
        return INDEX_DIR / f"{doc_id}.faiss"

    def _chunks_path(self, doc_id: str) -> Path:
        return INDEX_DIR / f"{doc_id}_chunks.json"

    def list_documents(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        docs = []
        for doc_id, info in self.metadata.items():
            if session_id and info.get("session_id") != session_id:
                continue
            docs.append(
                {
                    "id": doc_id,
                    "filename": info.get("filename", "unknown"),
                    "original_name": info.get("original_name", info.get("filename", "unknown")),
                    "extension": info.get("extension", ""),
                    "num_chunks": info.get("num_chunks", 0),
                    "uploaded_at": info.get("uploaded_at", ""),
                    "status": info.get("status", "ready"),
                }
            )
        docs.sort(key=lambda x: x.get("uploaded_at", ""), reverse=True)
        return docs

    def get_document(self, doc_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if doc_id not in self.metadata:
            return None
        info = self.metadata[doc_id]
        if session_id and info.get("session_id") != session_id:
            return None
        return {
            "id": doc_id,
            "filename": info.get("filename"),
            "original_name": info.get("original_name", info.get("filename")),
            "extension": info.get("extension"),
            "num_chunks": info.get("num_chunks", 0),
            "uploaded_at": info.get("uploaded_at"),
            "status": info.get("status", "ready"),
            "session_id": info.get("session_id"),
        }

    def document_exists(self, doc_id: str, session_id: Optional[str] = None) -> bool:
        if doc_id not in self.metadata:
            return False
        if session_id and self.metadata[doc_id].get("session_id") != session_id:
            return False
        return True

    def add_document(
        self,
        doc_id: str,
        original_name: str,
        filename: str,
        extension: str,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray,
        uploaded_at: str,
        session_id: str,
    ):
        if embeddings is None or len(embeddings) == 0:
            raise ValueError("No embeddings to index")

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)

        faiss.write_index(index, str(self._index_path(doc_id)))
        self._chunks_path(doc_id).write_text(
            json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        self.metadata[doc_id] = {
            "filename": filename,
            "original_name": original_name,
            "extension": extension,
            "num_chunks": len(chunks),
            "uploaded_at": uploaded_at,
            "status": "ready",
            "embedding_dim": dim,
            "session_id": session_id,
        }
        self._save_metadata()

    def _delete_one(self, doc_id: str) -> bool:
        if doc_id not in self.metadata:
            return False
        info = self.metadata[doc_id]
        filename = info.get("filename")
        if filename:
            path = UPLOAD_DIR / filename
            if path.exists() and is_safe_path(UPLOAD_DIR, path):
                try:
                    path.unlink()
                except Exception:
                    pass
        try:
            idx = self._index_path(doc_id)
            chunks = self._chunks_path(doc_id)
            if idx.exists():
                idx.unlink()
            if chunks.exists():
                chunks.unlink()
        except Exception:
            pass
        del self.metadata[doc_id]
        return True

    def delete_documents(self, doc_ids: List[str], session_id: Optional[str] = None) -> List[str]:
        deleted = []
        for doc_id in doc_ids:
            if doc_id not in self.metadata:
                continue
            if session_id and self.metadata[doc_id].get("session_id") != session_id:
                continue
            if self._delete_one(doc_id):
                deleted.append(doc_id)
        self._save_metadata()
        return deleted

    def delete_documents_for_session(self, session_id: str) -> List[str]:
        ids = [
            doc_id
            for doc_id, info in self.metadata.items()
            if info.get("session_id") == session_id
        ]
        return self.delete_documents(ids, session_id=session_id)

    def search(
        self, doc_id: str, query_embedding: np.ndarray, top_k: int = 5, session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if doc_id not in self.metadata:
            raise ValueError("Document not found")
        if session_id and self.metadata[doc_id].get("session_id") != session_id:
            raise ValueError("Document not found for this session")

        index_path = self._index_path(doc_id)
        chunks_path = self._chunks_path(doc_id)
        if not index_path.exists() or not chunks_path.exists():
            raise ValueError("Document index is missing or corrupted")

        index = faiss.read_index(str(index_path))
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        if index.ntotal == 0:
            return []

        k = min(top_k, index.ntotal)
        query = query_embedding.reshape(1, -1).astype(np.float32)
        scores, indices = index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(chunks):
                continue
            chunk = chunks[idx]
            results.append(
                {
                    "text": chunk.get("text", ""),
                    "page": chunk.get("page"),
                    "chunk_index": chunk.get("chunk_index"),
                    "filename": chunk.get("filename"),
                    "score": float(score),
                }
            )
        return results


_store: Optional[DocumentStore] = None


def get_store() -> DocumentStore:
    global _store
    if _store is None:
        _store = DocumentStore()
    return _store
