-- =============================================================================
-- CommLoan RAG System - Database Initialization Script
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL DEFAULT 'read_only',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- =============================================================================
-- FEATURE FLAGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT false,
    rollout_percentage INTEGER DEFAULT 100,
    user_segments JSONB DEFAULT '[]',
    config JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_name ON feature_flags(name);
CREATE INDEX IF NOT EXISTS idx_feature_flags_enabled ON feature_flags(enabled);

-- =============================================================================
-- RAG CONFIGURATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS rag_configurations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    config_name VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT false,
    strategies JSONB NOT NULL,
    llm_providers JSONB NOT NULL,
    embeddings_config JSONB NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rag_config_active ON rag_configurations(is_active);

-- =============================================================================
-- DOCUMENTS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_type VARCHAR(50) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),
    source VARCHAR(255),
    content TEXT,
    summary TEXT,
    metadata JSONB,
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    version INTEGER DEFAULT 1,
    parent_document_id UUID REFERENCES documents(id),
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING gin(metadata);

-- =============================================================================
-- DOCUMENT CHUNKS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_summary TEXT,
    chunk_metadata JSONB,
    embedding vector(384),
    embedding_model VARCHAR(50),
    parent_chunk_id UUID REFERENCES document_chunks(id),
    hierarchy_level INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_parent ON document_chunks(parent_chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1000);

-- =============================================================================
-- QUERY LOGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL,
    user_id UUID REFERENCES users(id),
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),
    strategies_used JSONB,
    retrieved_chunks JSONB,
    response_text TEXT,
    confidence_score DECIMAL(3, 2),
    llm_provider VARCHAR(50),
    llm_model VARCHAR(100),
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6),
    response_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_user ON query_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_query_logs_provider ON query_logs(llm_provider);

-- =============================================================================
-- AUDIT LOGS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- =============================================================================
-- COMPLIANCE CHECKS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS compliance_checks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_application_id UUID,
    check_type VARCHAR(100) NOT NULL,
    regulation VARCHAR(100),
    compliant BOOLEAN,
    violations JSONB,
    warnings JSONB,
    details JSONB,
    checked_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_compliance_loan_id ON compliance_checks(loan_application_id);
CREATE INDEX IF NOT EXISTS idx_compliance_type ON compliance_checks(check_type);

-- =============================================================================
-- LOAN APPLICATIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS loan_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_number VARCHAR(50) UNIQUE NOT NULL,
    borrower_id UUID NOT NULL,
    loan_type VARCHAR(50) NOT NULL,
    requested_amount DECIMAL(15, 2),
    status VARCHAR(50) DEFAULT 'draft',
    application_data JSONB,
    risk_score DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_loan_app_status ON loan_applications(status);
CREATE INDEX IF NOT EXISTS idx_loan_app_borrower ON loan_applications(borrower_id);
CREATE INDEX IF NOT EXISTS idx_loan_app_number ON loan_applications(application_number);

-- =============================================================================
-- INSERT DEFAULT DATA
-- =============================================================================

-- Create default admin user (password: admin123 - CHANGE IN PRODUCTION!)
-- Password hash for 'admin123' using bcrypt
INSERT INTO users (email, password_hash, first_name, last_name, role, is_active)
VALUES (
    'admin@commloan.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5tdcBvrtmRwBS',
    'Admin',
    'User',
    'super_admin',
    true
) ON CONFLICT (email) DO NOTHING;

-- Create default RAG configuration
INSERT INTO rag_configurations (config_name, is_active, strategies, llm_providers, embeddings_config)
VALUES (
    'default_config',
    true,
    '{"reranking": {"enabled": true, "model": "cross-encoder/ms-marco-MiniLM-L-6-v2", "top_k": 5}, "multi_query": {"enabled": true, "num_queries": 4}, "hierarchical_rag": {"enabled": true}}'::jsonb,
    '{"default": "openai", "fallback": ["anthropic", "bedrock"]}'::jsonb,
    '{"model": "sentence-transformers/all-MiniLM-L6-v2", "dimension": 384}'::jsonb
) ON CONFLICT (config_name) DO NOTHING;

-- Create default feature flags
INSERT INTO feature_flags (name, description, enabled)
VALUES
    ('enable_knowledge_graph', 'Enable knowledge graph search', false),
    ('enable_streaming_responses', 'Enable streaming LLM responses', true),
    ('enable_compliance_checks', 'Enable automatic compliance checks', true),
    ('enable_cost_optimization', 'Enable cost optimization strategies', true),
    ('enable_pii_detection', 'Enable PII detection and masking', true)
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- VIEWS FOR ANALYTICS
-- =============================================================================

-- View for query analytics
CREATE OR REPLACE VIEW query_analytics AS
SELECT
    DATE(created_at) as query_date,
    COUNT(*) as total_queries,
    AVG(response_time_ms) as avg_response_time_ms,
    SUM(CASE WHEN success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate,
    AVG(confidence_score) as avg_confidence_score,
    SUM(cost_usd) as total_cost_usd,
    llm_provider
FROM query_logs
GROUP BY DATE(created_at), llm_provider
ORDER BY query_date DESC;

-- View for document statistics
CREATE OR REPLACE VIEW document_statistics AS
SELECT
    document_type,
    COUNT(*) as total_documents,
    SUM(file_size_bytes) as total_size_bytes,
    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as completed_count,
    COUNT(CASE WHEN processing_status = 'failed' THEN 1 END) as failed_count,
    COUNT(CASE WHEN processing_status = 'pending' THEN 1 END) as pending_count
FROM documents
WHERE is_active = true
GROUP BY document_type;

-- =============================================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rag_config_updated_at BEFORE UPDATE ON rag_configurations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_feature_flags_updated_at BEFORE UPDATE ON feature_flags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- GRANT PERMISSIONS (adjust as needed for your setup)
-- =============================================================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO commloan_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO commloan_user;

COMMENT ON DATABASE commloan_db IS 'CommLoan RAG System Database';
