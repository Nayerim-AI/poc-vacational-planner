import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import numpy as np

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    faiss = None

logger = logging.getLogger(__name__)


@dataclass
class RAGDocument:
    doc_id: str
    text: str


def _simple_embed(text: str, dim: int = 128) -> np.ndarray:
    """
    Lightweight embedding: hash text to a deterministic vector.
    This is not semantic but sufficient for PoC similarity + FAISS demo.
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # Repeat/crop to dim and normalize
    vals = np.frombuffer(digest * ((dim // len(digest)) + 1), dtype=np.uint8)[:dim]
    vec = vals.astype("float32")
    norm = np.linalg.norm(vec) or 1.0
    return vec / norm


class RAGTool:
    def __init__(self, store_path: str | Path, dim: int = 128):
        self.store_path = Path(store_path)
        self.dim = dim
        self.documents: List[RAGDocument] = []
        self.index = None
        self.use_faiss = faiss is not None
        self.gpu_enabled = False
        self.use_gpu_flag = os.getenv("RAG_USE_GPU", "0").lower() in {"1", "true", "yes"}

    def load_dir(self, glob: str = "*.txt") -> None:
        if not self.store_path.exists():
            logger.info("RAG path %s does not exist, skipping", self.store_path)
            return
        docs = []
        for path in self.store_path.glob(glob):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            docs.append(RAGDocument(doc_id=path.name, text=text))
        if docs:
            self.add_documents(docs)
            logger.info("RAG indexed %d documents from %s", len(docs), self.store_path)

    def add_documents(self, docs: Sequence[RAGDocument]) -> None:
        if not docs:
            return
        embeddings = np.vstack([_simple_embed(doc.text, self.dim) for doc in docs])
        self.documents.extend(docs)
        if self.use_faiss:
            if self.index is None:
                base_index = faiss.IndexFlatIP(self.dim)
                # Try GPU device 1; fallback to CPU if unavailable or GPU bindings missing.
                if self.use_gpu_flag and hasattr(faiss, "StandardGpuResources"):
                    try:
                        res = faiss.StandardGpuResources()
                        self.index = faiss.index_cpu_to_gpu(res, 1, base_index)
                        self.gpu_enabled = True
                        logger.info("RAG FAISS using GPU device 1")
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("FAISS GPU unavailable, falling back to CPU: %s", exc)
                        self.index = base_index
                else:
                    self.index = base_index
            self.index.add(embeddings)
        else:
            # Fallback: store embeddings for manual similarity
            self.index = embeddings if self.index is None else np.vstack([self.index, embeddings])

    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if self.index is None or not self.documents:
            return []
        q_vec = _simple_embed(query, self.dim).reshape(1, -1)
        if self.use_faiss:
            scores, indices = self.index.search(q_vec, top_k)
            hits = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                hits.append((self.documents[idx].text, float(score)))
            return hits
        # Fallback cosine on numpy
        doc_vecs = self.index
        scores = (doc_vecs @ q_vec.T).flatten()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(self.documents[i].text, float(scores[i])) for i in top_idx]
