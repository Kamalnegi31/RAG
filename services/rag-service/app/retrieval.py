"""
Retrieval Module - Vector Search and Re-ranking
Supports: Multi-query, Re-ranking, Hierarchical retrieval
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import get_settings
from shared.models.database import DocumentChunk, Document

settings = get_settings()


class VectorRetriever:
    """Handles vector similarity search with PostgreSQL pgvector."""

    def __init__(self, db: Session):
        self.db = db

    async def similarity_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search using cosine similarity.

        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            document_type: Optional filter by document type

        Returns:
            List of chunks with similarity scores
        """
        # Build query
        query = """
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_text,
                dc.chunk_summary,
                dc.chunk_index,
                dc.chunk_metadata,
                dc.hierarchy_level,
                dc.parent_chunk_id,
                d.document_type,
                d.file_name,
                d.source,
                1 - (dc.embedding <=> :embedding::vector) AS similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.is_active = true
                AND d.processing_status = 'completed'
        """

        params = {"embedding": str(query_embedding)}

        if document_type:
            query += " AND d.document_type = :doc_type"
            params["doc_type"] = document_type

        query += " ORDER BY dc.embedding <=> :embedding::vector LIMIT :limit"
        params["limit"] = top_k

        result = self.db.execute(text(query), params)
        rows = result.fetchall()

        return [
            {
                "id": str(row[0]),
                "document_id": str(row[1]),
                "chunk_text": row[2],
                "chunk_summary": row[3],
                "chunk_index": row[4],
                "chunk_metadata": row[5],
                "hierarchy_level": row[6],
                "parent_chunk_id": str(row[7]) if row[7] else None,
                "document_type": row[8],
                "file_name": row[9],
                "source": row[10],
                "similarity": float(row[11])
            }
            for row in rows
        ]


class ReRanker:
    """Re-ranks search results using cross-encoder model."""

    def __init__(self):
        if settings.reranking_enabled:
            try:
                from sentence_transformers import CrossEncoder
                self.model = CrossEncoder(settings.reranking_model)
                self.enabled = True
            except ImportError:
                print("CrossEncoder not available, re-ranking disabled")
                self.enabled = False
        else:
            self.enabled = False

    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Re-rank chunks using cross-encoder model.

        Args:
            query: User query
            chunks: List of chunks from initial retrieval
            top_k: Number of top results to return after re-ranking

        Returns:
            Re-ranked list of chunks
        """
        if not self.enabled or not chunks:
            return chunks[:top_k]

        # Prepare pairs for re-ranking
        pairs = [[query, chunk["chunk_text"]] for chunk in chunks]

        # Get re-ranking scores
        scores = self.model.predict(pairs)

        # Add scores to chunks
        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        # Sort by rerank score
        reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

        return reranked[:top_k]


class HierarchicalRetriever:
    """Retrieves parent chunks for context expansion."""

    def __init__(self, db: Session):
        self.db = db

    async def get_parent_chunks(
        self,
        chunk_ids: List[str],
        max_levels: int = 2
    ) -> Dict[str, Any]:
        """
        Retrieve parent chunks for hierarchical context.

        Args:
            chunk_ids: List of chunk IDs
            max_levels: Maximum number of parent levels to retrieve

        Returns:
            Dictionary mapping chunk IDs to their parent chunks
        """
        result = {}

        for chunk_id in chunk_ids:
            parents = []
            current_id = chunk_id
            level = 0

            while level < max_levels:
                chunk = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id == current_id
                ).first()

                if not chunk or not chunk.parent_chunk_id:
                    break

                parent = self.db.query(DocumentChunk).filter(
                    DocumentChunk.id == chunk.parent_chunk_id
                ).first()

                if parent:
                    parents.append({
                        "id": str(parent.id),
                        "text": parent.chunk_text,
                        "level": level + 1
                    })
                    current_id = parent.id
                    level += 1
                else:
                    break

            result[chunk_id] = parents

        return result

    async def get_full_document(self, document_id: str) -> Optional[str]:
        """Retrieve full document content."""
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        return document.content if document else None


class MultiQueryExpander:
    """Expands user query into multiple variants for comprehensive retrieval."""

    def __init__(self, llm_manager):
        self.llm_manager = llm_manager

    async def expand_query(
        self,
        query: str,
        num_queries: int = 4
    ) -> List[str]:
        """
        Generate multiple query variants.

        Args:
            query: Original user query
            num_queries: Number of variant queries to generate

        Returns:
            List of query variants including original
        """
        if not settings.multi_query_enabled:
            return [query]

        system_prompt = """You are an expert at generating search queries for a commercial lending RAG system.
Generate diverse search queries that cover different aspects of the user's question.
Focus on different angles: credit requirements, collateral, loan terms, compliance, etc."""

        prompt = f"""Original query: "{query}"

Generate {num_queries - 1} alternative search queries that would help retrieve comprehensive information to answer this question.
Return ONLY the queries, one per line, without numbering or explanation.
"""

        try:
            result = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=200
            )

            # Parse generated queries
            queries = [q.strip() for q in result["text"].split("\n") if q.strip()]
            queries = [query] + queries[:num_queries - 1]  # Include original

            return queries

        except Exception as e:
            print(f"Multi-query expansion failed: {e}")
            return [query]


class RAGRetriever:
    """Main retrieval orchestrator combining all strategies."""

    def __init__(self, db: Session, llm_manager):
        self.db = db
        self.llm_manager = llm_manager
        self.vector_retriever = VectorRetriever(db)
        self.reranker = ReRanker()
        self.hierarchical_retriever = HierarchicalRetriever(db)
        self.multi_query_expander = MultiQueryExpander(llm_manager)

    async def retrieve(
        self,
        query: str,
        query_embedding: List[float],
        strategies: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform retrieval using configured strategies.

        Args:
            query: User query text
            query_embedding: Query vector embedding
            strategies: Optional strategy configuration override

        Returns:
            Dictionary with retrieved chunks and metadata
        """
        # Default strategies from settings
        use_multi_query = strategies.get("multi_query", settings.multi_query_enabled) if strategies else settings.multi_query_enabled
        use_reranking = strategies.get("reranking", settings.reranking_enabled) if strategies else settings.reranking_enabled
        use_hierarchical = strategies.get("hierarchical", settings.hierarchical_rag_enabled) if strategies else settings.hierarchical_rag_enabled

        initial_k = strategies.get("initial_k", settings.reranking_initial_k) if strategies else settings.reranking_initial_k
        final_k = strategies.get("final_k", settings.reranking_top_k) if strategies else settings.reranking_top_k

        all_chunks = []
        queries_used = [query]

        # Multi-query expansion
        if use_multi_query:
            queries_used = await self.multi_query_expander.expand_query(
                query,
                num_queries=settings.multi_query_num_queries
            )

            # Search with each query variant
            for q in queries_used:
                chunks = await self.vector_retriever.similarity_search(
                    query_embedding=query_embedding,
                    top_k=initial_k // len(queries_used)
                )
                all_chunks.extend(chunks)

            # Deduplicate chunks
            seen = set()
            unique_chunks = []
            for chunk in all_chunks:
                if chunk["id"] not in seen:
                    seen.add(chunk["id"])
                    unique_chunks.append(chunk)
            all_chunks = unique_chunks

        else:
            # Single query search
            all_chunks = await self.vector_retriever.similarity_search(
                query_embedding=query_embedding,
                top_k=initial_k
            )

        # Re-ranking
        if use_reranking and self.reranker.enabled:
            all_chunks = self.reranker.rerank(query, all_chunks, top_k=final_k)
        else:
            all_chunks = all_chunks[:final_k]

        # Hierarchical context expansion
        parent_chunks = {}
        if use_hierarchical:
            chunk_ids = [chunk["id"] for chunk in all_chunks]
            parent_chunks = await self.hierarchical_retriever.get_parent_chunks(
                chunk_ids,
                max_levels=settings.hierarchical_max_parent_levels
            )

        return {
            "chunks": all_chunks,
            "parent_chunks": parent_chunks,
            "queries_used": queries_used,
            "strategies_applied": {
                "multi_query": use_multi_query,
                "reranking": use_reranking,
                "hierarchical": use_hierarchical
            },
            "total_chunks_retrieved": len(all_chunks)
        }
