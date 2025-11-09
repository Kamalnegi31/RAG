"""
RAG Service - Multi-LLM Provider RAG with Advanced Strategies
FastAPI microservice for CommLoan RAG System
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import asyncio
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import get_settings
from shared.models.database import get_db, User, QueryLog
from shared.schemas.common import RAGQueryRequest, RAGQueryResponse

from .llm_manager import LLMManager, LLMProvider
from .retrieval import RAGRetriever
from .auth_client import get_current_user
from .embeddings import get_embedding

settings = get_settings()

app = FastAPI(
    title="CommLoan RAG Service",
    description="Retrieval-Augmented Generation with multi-LLM provider support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM Manager
llm_manager = LLMManager()


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "rag-service",
        "timestamp": datetime.utcnow().isoformat(),
        "available_providers": llm_manager.get_available_providers()
    }


@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check endpoint."""
    try:
        db.execute("SELECT 1")
        return {
            "status": "ready",
            "database": "connected",
            "llm_providers": llm_manager.get_available_providers()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


# =============================================================================
# RAG QUERY ENDPOINTS
# =============================================================================

@app.post("/api/v1/rag/query", response_model=RAGQueryResponse)
async def query_rag(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process RAG query with retrieval and generation.

    **Strategies Used:**
    - Multi-query expansion (if enabled)
    - Vector similarity search
    - Re-ranking with CrossEncoder (if enabled)
    - Hierarchical context expansion (if enabled)
    - LLM generation with retrieved context

    **Supported LLM Providers:**
    - OpenAI
    - Anthropic
    - AWS Bedrock
    - OpenRouter
    """
    start_time = time.time()
    session_id = request.session_id or uuid4()

    try:
        # Generate embedding for query
        query_embedding = await get_embedding(request.query)

        # Initialize retriever
        retriever = RAGRetriever(db, llm_manager)

        # Retrieve relevant chunks
        retrieval_result = await retriever.retrieve(
            query=request.query,
            query_embedding=query_embedding,
            strategies=request.options
        )

        # Build context from retrieved chunks
        context_parts = []
        for idx, chunk in enumerate(retrieval_result["chunks"], 1):
            context_parts.append(
                f"[{idx}] From {chunk['file_name']}:\n{chunk['chunk_text']}\n"
            )

        context = "\n".join(context_parts)

        # Build prompt for LLM
        system_prompt = """You are an expert commercial lending assistant for CommLoan.com.
Answer questions accurately based ONLY on the provided context.
If the context doesn't contain enough information, say so clearly.
Always cite which source document you're referencing.
Be precise with numbers and requirements."""

        user_prompt = f"""Context from knowledge base:
{context}

Question: {request.query}

Answer:"""

        # Generate response
        llm_provider = LLMProvider(request.llm_provider) if request.llm_provider else None

        llm_response = await llm_manager.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            provider=llm_provider,
            temperature=0.7,
            max_tokens=4000
        )

        # Calculate cost (simple estimation)
        cost_per_1k_tokens = 0.002  # Simplified estimate
        cost_usd = (llm_response["tokens_used"] / 1000) * cost_per_1k_tokens

        # Calculate confidence score (based on retrieval similarity)
        avg_similarity = sum(c["similarity"] for c in retrieval_result["chunks"]) / len(retrieval_result["chunks"]) if retrieval_result["chunks"] else 0

        # Log query
        query_log = QueryLog(
            session_id=session_id,
            user_id=current_user.id,
            query_text=request.query,
            query_type="rag_query",
            strategies_used=retrieval_result["strategies_applied"],
            retrieved_chunks=[{
                "id": c["id"],
                "file_name": c["file_name"],
                "similarity": c["similarity"]
            } for c in retrieval_result["chunks"]],
            response_text=llm_response["text"],
            confidence_score=avg_similarity,
            llm_provider=llm_response["provider"],
            llm_model=llm_response["model"],
            tokens_used=llm_response["tokens_used"],
            cost_usd=cost_usd,
            response_time_ms=int((time.time() - start_time) * 1000),
            success=True
        )

        db.add(query_log)
        db.commit()

        # Build response
        return RAGQueryResponse(
            response=llm_response["text"],
            confidence_score=round(avg_similarity, 2),
            source_chunks=[
                {
                    "id": c["id"],
                    "text": c["chunk_text"],
                    "file_name": c["file_name"],
                    "document_type": c["document_type"],
                    "similarity": c["similarity"]
                }
                for c in retrieval_result["chunks"]
            ],
            strategies_used=list(retrieval_result["strategies_applied"].keys()),
            session_id=session_id,
            llm_provider=llm_response["provider"],
            llm_model=llm_response["model"],
            tokens_used=llm_response["tokens_used"],
            response_time_ms=int((time.time() - start_time) * 1000)
        )

    except Exception as e:
        # Log failed query
        query_log = QueryLog(
            session_id=session_id,
            user_id=current_user.id,
            query_text=request.query,
            success=False,
            error_message=str(e),
            response_time_ms=int((time.time() - start_time) * 1000)
        )
        db.add(query_log)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )


@app.post("/api/v1/rag/query/stream")
async def query_rag_stream(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process RAG query with streaming response.

    Returns Server-Sent Events (SSE) stream of the LLM response.
    """
    if not settings.enable_streaming_responses:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Streaming responses are disabled"
        )

    async def stream_generator():
        try:
            # Generate embedding for query
            query_embedding = await get_embedding(request.query)

            # Initialize retriever
            retriever = RAGRetriever(db, llm_manager)

            # Retrieve relevant chunks
            retrieval_result = await retriever.retrieve(
                query=request.query,
                query_embedding=query_embedding,
                strategies=request.options
            )

            # Build context
            context_parts = []
            for idx, chunk in enumerate(retrieval_result["chunks"], 1):
                context_parts.append(
                    f"[{idx}] From {chunk['file_name']}:\n{chunk['chunk_text']}\n"
                )

            context = "\n".join(context_parts)

            # Build prompt
            system_prompt = """You are an expert commercial lending assistant for CommLoan.com.
Answer questions accurately based ONLY on the provided context."""

            user_prompt = f"""Context:\n{context}\n\nQuestion: {request.query}\n\nAnswer:"""

            # Stream response
            llm_provider = LLMProvider(request.llm_provider) if request.llm_provider else None

            async for chunk in llm_manager.generate_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                provider=llm_provider,
                temperature=0.7,
                max_tokens=4000
            ):
                yield f"data: {chunk}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream"
    )


@app.get("/api/v1/rag/session/{session_id}")
async def get_session_queries(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all queries in a session."""
    queries = db.query(QueryLog).filter(
        QueryLog.session_id == session_id,
        QueryLog.user_id == current_user.id
    ).order_by(QueryLog.created_at).all()

    return {
        "session_id": str(session_id),
        "total_queries": len(queries),
        "queries": [
            {
                "id": str(q.id),
                "query_text": q.query_text,
                "response_text": q.response_text,
                "confidence_score": float(q.confidence_score) if q.confidence_score else None,
                "llm_provider": q.llm_provider,
                "tokens_used": q.tokens_used,
                "cost_usd": float(q.cost_usd) if q.cost_usd else None,
                "success": q.success,
                "created_at": q.created_at.isoformat()
            }
            for q in queries
        ]
    }


@app.delete("/api/v1/rag/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a session (clears query history)."""
    db.query(QueryLog).filter(
        QueryLog.session_id == session_id,
        QueryLog.user_id == current_user.id
    ).delete()

    db.commit()
    return None


@app.get("/api/v1/rag/providers")
async def list_providers(current_user: User = Depends(get_current_user)):
    """List available LLM providers."""
    return {
        "providers": llm_manager.get_available_providers(),
        "default_provider": settings.default_llm_provider,
        "fallback_providers": settings.fallback_providers_list
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
