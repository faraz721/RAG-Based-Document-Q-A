"""Low-memory embeddings for free-tier hosts (e.g. Render 512MB)."""
from typing import List
import os

# Reduce native thread / allocator pressure before heavy imports
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np

_model = None
_backend = None  # "fastembed" | "st"


def _get_model():
    """Lazy-load the smallest practical embedding backend."""
    global _model, _backend
    if _model is not None:
        return _model, _backend

    # Prefer fastembed (ONNX) — much lower RAM than full PyTorch sentence-transformers
    try:
        from fastembed import TextEmbedding

        _model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        _backend = "fastembed"
        return _model, _backend
    except Exception:
        pass

    # Fallback: sentence-transformers (heavier)
    from sentence_transformers import SentenceTransformer
    from utils.config import EMBEDDING_MODEL_NAME

    try:
        import torch

        torch.set_num_threads(1)
    except Exception:
        pass

    _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    _backend = "st"
    return _model, _backend


def embed_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.array([], dtype=np.float32).reshape(0, 384)

    model, backend = _get_model()

    if backend == "fastembed":
        # fastembed returns a generator of vectors
        vectors = list(model.embed(texts))
        arr = np.array(vectors, dtype=np.float32)
        # L2 normalize for cosine / inner-product FAISS
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        arr = arr / norms
        return arr

    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=8,
    )
    return embeddings.astype(np.float32)


def embed_query(query: str) -> np.ndarray:
    return embed_texts([query])[0]
