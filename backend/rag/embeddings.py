from typing import List
import numpy as np

_model = None


def get_embedding_model():
    """Lazy-load SentenceTransformer model (singleton)."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from utils.config import EMBEDDING_MODEL_NAME

        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def embed_texts(texts: List[str]) -> np.ndarray:
    """Generate embeddings for a list of texts. Returns float32 numpy array."""
    if not texts:
        return np.array([], dtype=np.float32).reshape(0, 384)

    model = get_embedding_model()
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string."""
    return embed_texts([query])[0]
