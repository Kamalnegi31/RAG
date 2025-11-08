"""
Common Pydantic schemas used across all services.
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class UserRole(str, Enum):
    """User roles for RBAC."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"
    COMPLIANCE_OFFICER = "compliance"
    READ_ONLY = "read_only"


class DocumentType(str, Enum):
    """Document types for categorization."""
    LOAN_POLICY = "loan_policy"
    REGULATION = "regulation"
    APPLICATION = "application"
    FINANCIAL_STATEMENT = "financial_statement"
    COLLATERAL_DOC = "collateral_doc"
    CREDIT_REPORT = "credit_report"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"


class LoanType(str, Enum):
    """Loan types."""
    TERM_LOAN = "term_loan"
    LINE_OF_CREDIT = "line_of_credit"
    SBA_LOAN = "sba_loan"
    COMMERCIAL_MORTGAGE = "commercial_mortgage"
    EQUIPMENT_FINANCING = "equipment_financing"


# =============================================================================
# BASE SCHEMAS
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole = UserRole.READ_ONLY


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase, TimestampSchema):
    """User schema as stored in database."""
    id: UUID
    is_active: bool
    last_login: Optional[datetime] = None


class UserPublic(UserBase):
    """Public user schema (no sensitive data)."""
    id: UUID
    is_active: bool
    full_name: Optional[str] = None


# =============================================================================
# AUTHENTICATION SCHEMAS
# =============================================================================

class Token(BaseSchema):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseSchema):
    """Token payload data."""
    user_id: UUID
    email: str
    role: UserRole


class LoginRequest(BaseSchema):
    """Login request schema."""
    email: EmailStr
    password: str


class PasswordChange(BaseSchema):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# =============================================================================
# DOCUMENT SCHEMAS
# =============================================================================

class DocumentBase(BaseSchema):
    """Base document schema."""
    document_type: DocumentType
    file_name: str
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""
    pass


class DocumentUpdate(BaseSchema):
    """Schema for updating a document."""
    document_type: Optional[DocumentType] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DocumentInDB(DocumentBase, TimestampSchema):
    """Document schema as stored in database."""
    id: UUID
    file_path: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    processing_status: ProcessingStatus
    error_message: Optional[str] = None
    version: int
    uploaded_by: Optional[UUID] = None
    is_active: bool


class DocumentPublic(BaseSchema):
    """Public document schema."""
    id: UUID
    document_type: DocumentType
    file_name: str
    file_size_bytes: Optional[int] = None
    processing_status: ProcessingStatus
    created_at: datetime
    summary: Optional[str] = None


class DocumentChunkPublic(BaseSchema):
    """Public document chunk schema."""
    id: UUID
    document_id: UUID
    chunk_index: int
    chunk_text: str
    chunk_summary: Optional[str] = None
    hierarchy_level: int


# =============================================================================
# RAG SCHEMAS
# =============================================================================

class RAGQueryRequest(BaseSchema):
    """RAG query request schema."""
    query: str = Field(..., min_length=1, max_length=5000)
    session_id: Optional[UUID] = None
    context: Optional[Dict[str, Any]] = None
    llm_provider: Optional[LLMProvider] = None
    llm_model: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class RAGQueryResponse(BaseSchema):
    """RAG query response schema."""
    response: str
    confidence_score: Optional[float] = None
    source_chunks: List[Dict[str, Any]] = []
    strategies_used: List[str] = []
    session_id: UUID
    llm_provider: str
    llm_model: str
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None


class RAGConfigStrategies(BaseSchema):
    """RAG strategies configuration."""
    reranking: Dict[str, Any] = {"enabled": True, "model": "cross-encoder/ms-marco-MiniLM-L-6-v2", "top_k": 5}
    multi_query: Dict[str, Any] = {"enabled": True, "num_queries": 4}
    contextual_retrieval: Dict[str, Any] = {"enabled": False, "document_types": []}
    hierarchical_rag: Dict[str, Any] = {"enabled": True, "max_parent_levels": 2}
    agentic_rag: Dict[str, Any] = {"enabled": True}
    self_reflective_rag: Dict[str, Any] = {"enabled": False, "confidence_threshold": 0.7}


class RAGConfigLLMProviders(BaseSchema):
    """LLM providers configuration."""
    default: LLMProvider = LLMProvider.OPENAI
    fallback: List[LLMProvider] = [LLMProvider.ANTHROPIC]
    configs: Dict[str, Dict[str, Any]] = {}


class RAGConfiguration(BaseSchema):
    """Complete RAG configuration."""
    config_name: str
    is_active: bool = False
    strategies: RAGConfigStrategies
    llm_providers: RAGConfigLLMProviders
    embeddings_config: Dict[str, Any]


# =============================================================================
# FEATURE FLAG SCHEMAS
# =============================================================================

class FeatureFlagBase(BaseSchema):
    """Base feature flag schema."""
    name: str
    description: Optional[str] = None
    enabled: bool = False
    rollout_percentage: int = Field(default=100, ge=0, le=100)
    user_segments: List[str] = []
    config: Dict[str, Any] = {}


class FeatureFlagCreate(FeatureFlagBase):
    """Schema for creating a feature flag."""
    pass


class FeatureFlagUpdate(BaseSchema):
    """Schema for updating a feature flag."""
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    user_segments: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class FeatureFlagInDB(FeatureFlagBase, TimestampSchema):
    """Feature flag as stored in database."""
    id: UUID
    created_by: Optional[UUID] = None


# =============================================================================
# UNDERWRITING SCHEMAS
# =============================================================================

class BorrowerInfo(BaseSchema):
    """Borrower information."""
    credit_score: int = Field(..., ge=300, le=850)
    annual_revenue: float = Field(..., gt=0)
    ebitda: float
    existing_debt: float = Field(..., ge=0)
    years_in_business: Optional[int] = Field(None, ge=0)


class LoanDetails(BaseSchema):
    """Loan details."""
    requested_amount: float = Field(..., gt=0)
    loan_type: LoanType
    term_months: int = Field(..., gt=0)
    interest_rate: Optional[float] = Field(None, ge=0, le=100)
    purpose: Optional[str] = None


class CollateralInfo(BaseSchema):
    """Collateral information."""
    type: str
    appraised_value: float = Field(..., gt=0)
    description: Optional[str] = None


class UnderwritingRequest(BaseSchema):
    """Underwriting analysis request."""
    loan_application: LoanDetails
    borrower: BorrowerInfo
    collateral: Optional[CollateralInfo] = None


class FinancialMetrics(BaseSchema):
    """Calculated financial metrics."""
    dscr: Optional[float] = None
    ltv: Optional[float] = None
    dti: Optional[float] = None
    debt_yield: Optional[float] = None


class UnderwritingResponse(BaseSchema):
    """Underwriting analysis response."""
    risk_score: float = Field(..., ge=0, le=100)
    recommendation: str
    metrics: FinancialMetrics
    conditions: List[str] = []
    max_loan_amount: Optional[float] = None
    reasoning: Optional[str] = None


# =============================================================================
# COMPLIANCE SCHEMAS
# =============================================================================

class ComplianceCheckRequest(BaseSchema):
    """Compliance check request."""
    loan_application_id: Optional[UUID] = None
    data: Dict[str, Any]
    regulations: List[str] = []


class ComplianceViolation(BaseSchema):
    """Compliance violation details."""
    regulation: str
    violation_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    required_action: Optional[str] = None


class ComplianceCheckResponse(BaseSchema):
    """Compliance check response."""
    compliant: bool
    violations: List[ComplianceViolation] = []
    warnings: List[Dict[str, Any]] = []
    required_actions: List[str] = []


# =============================================================================
# ANALYTICS SCHEMAS
# =============================================================================

class QueryAnalytics(BaseSchema):
    """Query analytics data."""
    total_queries: int
    avg_response_time_ms: float
    success_rate: float
    avg_confidence_score: Optional[float] = None
    total_cost_usd: float


class CostBreakdown(BaseSchema):
    """Cost breakdown by provider."""
    total_cost_usd: float
    by_provider: Dict[str, float]
    by_model: Dict[str, float]


class SystemHealth(BaseSchema):
    """System health status."""
    status: str
    services: Dict[str, bool]
    database: bool
    cache: bool
    timestamp: datetime


# =============================================================================
# ERROR SCHEMAS
# =============================================================================

class ErrorResponse(BaseSchema):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationError(BaseSchema):
    """Validation error details."""
    field: str
    message: str
    type: str


__all__ = [
    # Enums
    "UserRole",
    "DocumentType",
    "ProcessingStatus",
    "LLMProvider",
    "LoanType",
    # User
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserPublic",
    # Auth
    "Token",
    "TokenData",
    "LoginRequest",
    "PasswordChange",
    # Documents
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentInDB",
    "DocumentPublic",
    "DocumentChunkPublic",
    # RAG
    "RAGQueryRequest",
    "RAGQueryResponse",
    "RAGConfiguration",
    # Feature Flags
    "FeatureFlagCreate",
    "FeatureFlagUpdate",
    "FeatureFlagInDB",
    # Underwriting
    "UnderwritingRequest",
    "UnderwritingResponse",
    "FinancialMetrics",
    # Compliance
    "ComplianceCheckRequest",
    "ComplianceCheckResponse",
    # Analytics
    "QueryAnalytics",
    "CostBreakdown",
    "SystemHealth",
    # Errors
    "ErrorResponse",
]
