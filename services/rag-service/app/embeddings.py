"""
Embedding generation for RAG queries and documents.
"""

from typing import List
from functools import lru_cache
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_embedding_model():
    """Get cached embedding model."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text.

    Args:
        text: Input text to embed

    Returns:
        Embedding vector as list of floats
    """
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts in batch.

    Args:
        texts: List of input texts

    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_tensor=False, batch_size=settings.embedding_batch_size)
    return [emb.tolist() for emb in embeddings]
