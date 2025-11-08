"""
Admin Service - Configuration Management and Feature Flags
FastAPI microservice for CommLoan RAG System
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config import get_settings
from shared.models.database import get_db, User, FeatureFlag, RAGConfiguration
from shared.schemas.common import (
    FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagInDB,
    RAGConfiguration as RAGConfigSchema,
    UserPublic, SystemHealth
)
from .auth_client import get_current_user, get_current_active_admin
from .crud import (
    create_feature_flag, update_feature_flag, get_feature_flag_by_name,
    list_feature_flags, delete_feature_flag,
    create_rag_config, update_rag_config, get_active_rag_config,
    list_rag_configs, activate_rag_config
)

settings = get_settings()

app = FastAPI(
    title="CommLoan Admin Service",
    description="Configuration management, feature flags, and admin operations",
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


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "admin-service",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Readiness check endpoint."""
    try:
        db.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database not ready: {str(e)}"
        )


# =============================================================================
# FEATURE FLAGS ENDPOINTS
# =============================================================================

@app.get("/api/v1/admin/features", response_model=List[FeatureFlagInDB])
async def list_features(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all feature flags."""
    flags = list_feature_flags(db, skip, limit)
    return flags


@app.get("/api/v1/admin/features/{feature_name}", response_model=FeatureFlagInDB)
async def get_feature(
    feature_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific feature flag by name."""
    flag = get_feature_flag_by_name(db, feature_name)
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feature flag '{feature_name}' not found"
        )
    return flag


@app.post("/api/v1/admin/features", response_model=FeatureFlagInDB, status_code=status.HTTP_201_CREATED)
async def create_feature(
    feature_data: FeatureFlagCreate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Create a new feature flag (admin only)."""
    # Check if feature already exists
    existing = get_feature_flag_by_name(db, feature_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feature flag '{feature_data.name}' already exists"
        )

    flag = create_feature_flag(db, feature_data, current_user.id)
    return flag


@app.put("/api/v1/admin/features/{feature_id}", response_model=FeatureFlagInDB)
async def update_feature(
    feature_id: UUID,
    feature_data: FeatureFlagUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Update a feature flag (admin only)."""
    flag = db.query(FeatureFlag).filter(FeatureFlag.id == feature_id).first()

    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found"
        )

    updated_flag = update_feature_flag(db, flag, feature_data)
    return updated_flag


@app.delete("/api/v1/admin/features/{feature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature(
    feature_id: UUID,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Delete a feature flag (admin only)."""
    success = delete_feature_flag(db, feature_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature flag not found"
        )
    return None


# =============================================================================
# RAG CONFIGURATION ENDPOINTS
# =============================================================================

@app.get("/api/v1/admin/rag/config")
async def get_rag_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active RAG configuration."""
    config = get_active_rag_config(db)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active RAG configuration found"
        )
    return config


@app.get("/api/v1/admin/rag/configs")
async def list_rag_configurations(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """List all RAG configurations (admin only)."""
    configs = list_rag_configs(db, skip, limit)
    return configs


@app.post("/api/v1/admin/rag/config", status_code=status.HTTP_201_CREATED)
async def create_rag_configuration(
    config_data: RAGConfigSchema,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Create a new RAG configuration (admin only)."""
    # Check if config name already exists
    existing = db.query(RAGConfiguration).filter(
        RAGConfiguration.config_name == config_data.config_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration '{config_data.config_name}' already exists"
        )

    config = create_rag_config(db, config_data, current_user.id)
    return config


@app.put("/api/v1/admin/rag/config/{config_id}")
async def update_rag_configuration(
    config_id: UUID,
    config_data: RAGConfigSchema,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Update RAG configuration (admin only)."""
    config = db.query(RAGConfiguration).filter(RAGConfiguration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    updated_config = update_rag_config(db, config, config_data)
    return updated_config


@app.post("/api/v1/admin/rag/config/{config_id}/activate")
async def activate_rag_configuration(
    config_id: UUID,
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Activate a RAG configuration (deactivates all others)."""
    config = db.query(RAGConfiguration).filter(RAGConfiguration.id == config_id).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found"
        )

    activate_rag_config(db, config_id)
    return {"message": f"Configuration '{config.config_name}' activated successfully"}


# =============================================================================
# SYSTEM HEALTH & METRICS
# =============================================================================

@app.get("/api/v1/admin/health/services", response_model=SystemHealth)
async def check_services_health(
    current_user: User = Depends(get_current_active_admin),
    db: Session = Depends(get_db)
):
    """Check health of all services (admin only)."""
    import httpx

    services = {
        "auth_service": f"http://auth-service:{settings.auth_service_port if hasattr(settings, 'auth_service_port') else 8001}/health",
        "rag_service": f"http://rag-service:{settings.rag_service_port if hasattr(settings, 'rag_service_port') else 8003}/health",
        "document_service": f"http://document-service:{settings.document_service_port if hasattr(settings, 'document_service_port') else 8004}/health",
    }

    service_status = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, url in services.items():
            try:
                response = await client.get(url)
                service_status[service_name] = response.status_code == 200
            except:
                service_status[service_name] = False

    # Check database
    try:
        db.execute("SELECT 1")
        database_status = True
    except:
        database_status = False

    # Check cache (Redis)
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        cache_status = True
    except:
        cache_status = False

    overall_status = "healthy" if all(service_status.values()) and database_status else "degraded"

    return SystemHealth(
        status=overall_status,
        services=service_status,
        database=database_status,
        cache=cache_status,
        timestamp=datetime.utcnow()
    )


@app.get("/api/v1/admin/settings")
async def get_system_settings(
    current_user: User = Depends(get_current_active_admin)
):
    """Get system settings (admin only)."""
    return {
        "environment": settings.environment,
        "debug": settings.debug,
        "api_version": settings.api_version,
        "cors_origins": settings.cors_origins_list,
        "llm_providers": {
            "default": settings.default_llm_provider,
            "fallback": settings.fallback_providers_list
        },
        "rag_config": {
            "reranking_enabled": settings.reranking_enabled,
            "multi_query_enabled": settings.multi_query_enabled,
            "hierarchical_rag_enabled": settings.hierarchical_rag_enabled,
            "agentic_rag_enabled": settings.agentic_rag_enabled
        },
        "feature_flags": {
            "knowledge_graph": settings.enable_knowledge_graph,
            "streaming_responses": settings.enable_streaming_responses,
            "compliance_checks": settings.enable_compliance_checks,
            "cost_optimization": settings.enable_cost_optimization
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
