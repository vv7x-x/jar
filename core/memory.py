import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")


class VectorMemory:
    def __init__(self, dim: int = 384, index_path: str = "./memory.index"):
        self.dim = dim
        self.index_path = index_path
        try:
            self.encoder = SentenceTransformer(MODEL_NAME)
            self.dim = self.encoder.get_sentence_embedding_dimension()
        except Exception:
            self.encoder = None
        self.index = faiss.IndexFlatL2(self.dim)
        self.items: List[Tuple[int, str]] = []

    def embed(self, text: str) -> np.ndarray:
        if self.encoder:
            vec = self.encoder.encode([text])[0]
            return np.asarray(vec, dtype=np.float32)
        # fallback: random but deterministic hash-based vector
        h = abs(hash(text)) % (10 ** 8)
        rng = np.random.RandomState(h)
        return rng.rand(self.dim).astype(np.float32)

    def add(self, text: str):
        vec = self.embed(text)
        self.index.add(vec.reshape(1, -1))
        self.items.append((len(self.items), text))

    def search(self, text: str, k: int = 5):
        vec = self.embed(text).reshape(1, -1)
        if self.index.ntotal == 0:
            return []
        D, I = self.index.search(vec, k)
        results = []
        for idx in I[0]:
            if idx < len(self.items):
                results.append(self.items[idx][1])
        return results
