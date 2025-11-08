# CommLoan RAG System - Production Ready

A production-ready, microservices-based Retrieval-Augmented Generation (RAG) system for commercial lending, featuring multi-LLM provider support, advanced RAG strategies, and comprehensive admin panel.

## 🏗️ Architecture

### Microservices
- **API Gateway** - Kong-based routing, authentication, rate limiting
- **Auth Service** - JWT authentication, user management
- **RAG Service** - Multi-query, re-ranking, hierarchical retrieval
- **Document Service** - Upload, chunking (Docling), embedding, vector storage
- **Underwriting Service** - Financial calculations, risk scoring
- **Compliance Service** - Regulatory checks, audit logging
- **Admin Service** - Configuration management, feature flags
- **Analytics Service** - Metrics, cost tracking, reporting

### Technology Stack
- **Backend:** FastAPI, Python 3.11+
- **Frontend:** React 18 + TypeScript, Material-UI
- **Database:** PostgreSQL 16 + pgvector
- **Cache:** Redis
- **Storage:** AWS S3
- **Queue:** RabbitMQ
- **Orchestration:** Docker Compose (dev), AWS ECS/EKS (prod)
- **LLM Providers:** AWS Bedrock, OpenRouter, OpenAI, Anthropic

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+
- AWS Account (for production deployment)

### Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd RAG

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec admin-service alembic upgrade head

# Access the applications
# Admin Dashboard: http://localhost:3001
# User Portal: http://localhost:3002
# API Gateway: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## 📁 Project Structure

```
commloan-rag/
├── services/                    # Backend microservices
│   ├── auth-service/
│   ├── admin-service/
│   ├── rag-service/
│   ├── document-service/
│   ├── underwriting-service/
│   ├── compliance-service/
│   └── analytics-service/
├── frontend/                    # Frontend applications
│   ├── admin-dashboard/
│   └── user-portal/
├── shared/                      # Shared utilities
│   ├── models/
│   ├── utils/
│   └── config/
├── infrastructure/              # Infrastructure as Code
│   ├── docker/
│   ├── kubernetes/
│   └── terraform/
├── scripts/                     # Utility scripts
├── docs/                        # Documentation
├── docker-compose.yml
└── README.md
```

## 🎨 CommLoan Theme

The application uses CommLoan's brand identity:
- **Primary Color:** #FFA41B (Orange)
- **Secondary Color:** #2E2E2E (Dark Gray)
- **Background:** #F5F5F5 (Light Gray)
- **Text:** #141131 (Dark)

## 📚 Documentation

- [API Documentation](docs/api.md)
- [Architecture Guide](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [Admin Panel User Guide](docs/admin-guide.md)
- [RAG Strategies](docs/rag-strategies.md)

## 🔐 Security

- JWT-based authentication
- Role-based access control (RBAC)
- API rate limiting
- PII detection and masking
- Comprehensive audit logging
- Encryption at rest and in transit

## 📊 Features

### Admin Panel
- ✅ RAG configuration management (toggle strategies)
- ✅ Multi-LLM provider configuration
- ✅ Document management
- ✅ User & role management
- ✅ Feature flags
- ✅ Analytics dashboard
- ✅ Cost tracking
- ✅ Audit logs

### RAG Strategies
- ✅ Re-ranking with CrossEncoder
- ✅ Multi-query expansion
- ✅ Agentic RAG (multiple search tools)
- ✅ Context-aware chunking (Docling)
- ✅ Hierarchical retrieval
- ✅ Contextual retrieval (configurable)
- ✅ Self-reflective RAG

### Underwriting Features
- ✅ DSCR calculation
- ✅ LTV calculation
- ✅ Risk scoring
- ✅ Loan recommendations
- ✅ What-if analysis

## 🌐 API Integration

The system provides REST APIs for integration with other applications:

```bash
# Example: Query RAG system
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the requirements for a $500k term loan?",
    "llm_provider": "openai"
  }'
```

## 🚢 Deployment

### AWS Deployment
See [AWS Deployment Guide](docs/deployment-aws.md) for detailed instructions.

**Services Used:**
- ECS/EKS for container orchestration
- RDS PostgreSQL with pgvector
- ElastiCache Redis
- S3 for document storage
- Application Load Balancer
- CloudWatch for monitoring

## 📈 Monitoring

- Prometheus metrics
- Grafana dashboards
- CloudWatch integration
- Cost tracking per LLM provider
- Performance metrics
- Error tracking

## 🧪 Testing

```bash
# Run all tests
docker-compose exec rag-service pytest

# Run with coverage
docker-compose exec rag-service pytest --cov=app tests/
```

## 📝 License

Proprietary - CommLoan.com

## 👥 Contributors

Built for CommLoan.com commercial lending platform.

## 🆘 Support

For issues and questions, please contact the development team.
