"""
Shared configuration settings for all services.
Loads from environment variables with validation.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # General
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    secret_key: str
    api_version: str = "v1"

    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # Redis
    redis_url: str
    redis_password: Optional[str] = None
    redis_db: int = 0

    # AWS
    aws_region: str = "us-east-1"
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket_name: str
    s3_region: str = "us-east-1"

    # LLM Providers
    default_llm_provider: str = "openai"
    fallback_llm_providers: str = "anthropic,bedrock"

    # Bedrock
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_access_key_id: Optional[str] = None
    bedrock_secret_access_key: Optional[str] = None

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4000

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-opus-20240229"
    anthropic_temperature: float = 0.7
    anthropic_max_tokens: int = 4000

    # OpenRouter
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "anthropic/claude-3-opus"
    openrouter_temperature: float = 0.7

    # Embedding
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    embedding_batch_size: int = 32

    # RAG Configuration
    reranking_enabled: bool = True
    reranking_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranking_top_k: int = 5
    reranking_initial_k: int = 50

    multi_query_enabled: bool = True
    multi_query_num_queries: int = 4

    contextual_retrieval_enabled: bool = False
    contextual_retrieval_doc_types: str = "loan_policy,regulation"

    hierarchical_rag_enabled: bool = True
    hierarchical_max_parent_levels: int = 2

    agentic_rag_enabled: bool = True
    self_reflective_rag_enabled: bool = False
    confidence_threshold: float = 0.7

    # Document Processing
    chunk_size: int = 512
    chunk_overlap: int = 50
    max_chunk_size: int = 1000
    use_docling: bool = True
    supported_file_types: str = "pdf,docx,txt,md"

    celery_broker_url: str
    celery_result_backend: str

    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    password_min_length: int = 8
    bcrypt_rounds: int = 12

    # API Security
    api_rate_limit: str = "100/minute"
    api_key_header: str = "X-API-Key"

    cors_origins: str = "http://localhost:3001,http://localhost:3002"
    cors_allow_credentials: bool = True

    # Feature Flags
    enable_knowledge_graph: bool = False
    enable_streaming_responses: bool = True
    enable_compliance_checks: bool = True
    enable_cost_optimization: bool = True
    enable_pii_detection: bool = True

    # Monitoring
    enable_monitoring: bool = True
    prometheus_port: int = 9090
    sentry_dsn: Optional[str] = None
    sentry_environment: str = "development"
    cloudwatch_enabled: bool = False
    cloudwatch_log_group: str = "/commloan/rag-system"

    # Underwriting
    min_credit_score: int = 680
    min_dscr: float = 1.25
    max_ltv: float = 0.80
    max_dti: float = 0.43
    min_loan_amount: int = 50000
    max_loan_amount: int = 5000000

    # Compliance
    pii_detection_enabled: bool = True
    audit_log_retention_days: int = 2555  # 7 years
    enable_ofac_screening: bool = False

    # Performance
    worker_concurrency: int = 4
    max_connections: int = 100
    connection_timeout: int = 30
    request_timeout: int = 60

    cache_ttl_embeddings: int = 86400
    cache_ttl_queries: int = 3600
    cache_ttl_config: int = 300

    # Development
    reload: bool = True
    enable_profiler: bool = False
    enable_sql_echo: bool = False
    mock_llm_apis: bool = False
    mock_aws_services: bool = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def fallback_providers_list(self) -> List[str]:
        """Parse fallback LLM providers into a list."""
        return [provider.strip() for provider in self.fallback_llm_providers.split(",")]

    @property
    def supported_file_types_list(self) -> List[str]:
        """Parse supported file types into a list."""
        return [ft.strip() for ft in self.supported_file_types.split(",")]

    @property
    def contextual_retrieval_doc_types_list(self) -> List[str]:
        """Parse contextual retrieval document types into a list."""
        return [dt.strip() for dt in self.contextual_retrieval_doc_types.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
