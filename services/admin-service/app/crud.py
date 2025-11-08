"""
CRUD operations for Admin Service.
Handles feature flags, RAG configurations, and system settings.
"""

from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.models.database import FeatureFlag, RAGConfiguration
from shared.schemas.common import (
    FeatureFlagCreate, FeatureFlagUpdate,
    RAGConfiguration as RAGConfigSchema
)


# =============================================================================
# FEATURE FLAGS CRUD
# =============================================================================

def get_feature_flag_by_name(db: Session, name: str) -> Optional[FeatureFlag]:
    """Get feature flag by name."""
    return db.query(FeatureFlag).filter(FeatureFlag.name == name).first()


def get_feature_flag_by_id(db: Session, flag_id: UUID) -> Optional[FeatureFlag]:
    """Get feature flag by ID."""
    return db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()


def list_feature_flags(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    enabled_only: Optional[bool] = None
) -> List[FeatureFlag]:
    """List all feature flags with optional filtering."""
    query = db.query(FeatureFlag)

    if enabled_only is not None:
        query = query.filter(FeatureFlag.enabled == enabled_only)

    return query.offset(skip).limit(limit).all()


def create_feature_flag(
    db: Session,
    flag_data: FeatureFlagCreate,
    created_by: UUID
) -> FeatureFlag:
    """Create a new feature flag."""
    db_flag = FeatureFlag(
        name=flag_data.name,
        description=flag_data.description,
        enabled=flag_data.enabled,
        rollout_percentage=flag_data.rollout_percentage,
        user_segments=flag_data.user_segments,
        config=flag_data.config,
        created_by=created_by
    )

    db.add(db_flag)
    db.commit()
    db.refresh(db_flag)

    return db_flag


def update_feature_flag(
    db: Session,
    flag: FeatureFlag,
    flag_data: FeatureFlagUpdate
) -> FeatureFlag:
    """Update a feature flag."""
    if flag_data.description is not None:
        flag.description = flag_data.description

    if flag_data.enabled is not None:
        flag.enabled = flag_data.enabled

    if flag_data.rollout_percentage is not None:
        flag.rollout_percentage = flag_data.rollout_percentage

    if flag_data.user_segments is not None:
        flag.user_segments = flag_data.user_segments

    if flag_data.config is not None:
        flag.config = flag_data.config

    db.commit()
    db.refresh(flag)

    return flag


def delete_feature_flag(db: Session, flag_id: UUID) -> bool:
    """Delete a feature flag."""
    flag = get_feature_flag_by_id(db, flag_id)

    if not flag:
        return False

    db.delete(flag)
    db.commit()

    return True


def is_feature_enabled(
    db: Session,
    feature_name: str,
    user_id: Optional[UUID] = None
) -> bool:
    """
    Check if a feature is enabled for a user.
    Handles rollout percentage and user segments.
    """
    flag = get_feature_flag_by_name(db, feature_name)

    if not flag:
        return False

    if not flag.enabled:
        return False

    # Check rollout percentage
    if flag.rollout_percentage < 100:
        # Simple hash-based rollout (can be improved)
        if user_id:
            user_hash = hash(str(user_id)) % 100
            if user_hash >= flag.rollout_percentage:
                return False

    # Check user segments (if specified)
    if flag.user_segments and user_id:
        # Would need user segment information to validate
        # For now, just pass through
        pass

    return True


# =============================================================================
# RAG CONFIGURATION CRUD
# =============================================================================

def get_active_rag_config(db: Session) -> Optional[RAGConfiguration]:
    """Get the currently active RAG configuration."""
    return db.query(RAGConfiguration).filter(
        RAGConfiguration.is_active == True
    ).first()


def get_rag_config_by_id(db: Session, config_id: UUID) -> Optional[RAGConfiguration]:
    """Get RAG configuration by ID."""
    return db.query(RAGConfiguration).filter(RAGConfiguration.id == config_id).first()


def get_rag_config_by_name(db: Session, config_name: str) -> Optional[RAGConfiguration]:
    """Get RAG configuration by name."""
    return db.query(RAGConfiguration).filter(
        RAGConfiguration.config_name == config_name
    ).first()


def list_rag_configs(db: Session, skip: int = 0, limit: int = 100) -> List[RAGConfiguration]:
    """List all RAG configurations."""
    return db.query(RAGConfiguration).offset(skip).limit(limit).all()


def create_rag_config(
    db: Session,
    config_data: RAGConfigSchema,
    created_by: UUID
) -> RAGConfiguration:
    """Create a new RAG configuration."""
    db_config = RAGConfiguration(
        config_name=config_data.config_name,
        is_active=config_data.is_active,
        strategies=config_data.strategies.dict(),
        llm_providers=config_data.llm_providers.dict(),
        embeddings_config=config_data.embeddings_config,
        created_by=created_by
    )

    # If this config is set as active, deactivate all others
    if config_data.is_active:
        db.query(RAGConfiguration).update({"is_active": False})

    db.add(db_config)
    db.commit()
    db.refresh(db_config)

    return db_config


def update_rag_config(
    db: Session,
    config: RAGConfiguration,
    config_data: RAGConfigSchema
) -> RAGConfiguration:
    """Update a RAG configuration."""
    config.strategies = config_data.strategies.dict()
    config.llm_providers = config_data.llm_providers.dict()
    config.embeddings_config = config_data.embeddings_config

    if config_data.is_active and not config.is_active:
        # Deactivate all other configs
        db.query(RAGConfiguration).update({"is_active": False})
        config.is_active = True

    db.commit()
    db.refresh(config)

    return config


def activate_rag_config(db: Session, config_id: UUID) -> bool:
    """Activate a RAG configuration (deactivates all others)."""
    config = get_rag_config_by_id(db, config_id)

    if not config:
        return False

    # Deactivate all configs
    db.query(RAGConfiguration).update({"is_active": False})

    # Activate this config
    config.is_active = True
    db.commit()

    return True


def delete_rag_config(db: Session, config_id: UUID) -> bool:
    """Delete a RAG configuration (cannot delete active config)."""
    config = get_rag_config_by_id(db, config_id)

    if not config:
        return False

    if config.is_active:
        return False  # Cannot delete active config

    db.delete(config)
    db.commit()

    return True
