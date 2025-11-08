# Admin Service

Configuration management, feature flags, and system administration for CommLoan RAG System.

## Features

- ✅ Feature flag management
- ✅ RAG configuration management
- ✅ System health monitoring
- ✅ Service status checks
- ✅ Settings management
- ✅ Gradual feature rollout
- ✅ A/B testing support

## API Endpoints

### Feature Flags
- `GET /api/v1/admin/features` - List all feature flags
- `GET /api/v1/admin/features/{name}` - Get specific feature flag
- `POST /api/v1/admin/features` - Create feature flag (admin)
- `PUT /api/v1/admin/features/{id}` - Update feature flag (admin)
- `DELETE /api/v1/admin/features/{id}` - Delete feature flag (admin)

### RAG Configuration
- `GET /api/v1/admin/rag/config` - Get active RAG configuration
- `GET /api/v1/admin/rag/configs` - List all configurations (admin)
- `POST /api/v1/admin/rag/config` - Create configuration (admin)
- `PUT /api/v1/admin/rag/config/{id}` - Update configuration (admin)
- `POST /api/v1/admin/rag/config/{id}/activate` - Activate configuration (admin)

### System Management
- `GET /api/v1/admin/health/services` - Check all services health (admin)
- `GET /api/v1/admin/settings` - Get system settings (admin)

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check

## Feature Flags

Feature flags allow you to:
- Enable/disable features without code deployment
- Gradually roll out features to a percentage of users
- Target specific user segments
- A/B test different configurations

**Default Feature Flags:**
- `enable_knowledge_graph` - Knowledge graph search
- `enable_streaming_responses` - Streaming LLM responses
- `enable_compliance_checks` - Automatic compliance checks
- `enable_cost_optimization` - Cost optimization strategies
- `enable_pii_detection` - PII detection and masking

## RAG Configuration

Manage RAG strategies dynamically:

```json
{
  "config_name": "production_config",
  "is_active": true,
  "strategies": {
    "reranking": {
      "enabled": true,
      "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
      "top_k": 5
    },
    "multi_query": {
      "enabled": true,
      "num_queries": 4
    },
    "hierarchical_rag": {
      "enabled": true,
      "max_parent_levels": 2
    }
  },
  "llm_providers": {
    "default": "openai",
    "fallback": ["anthropic", "bedrock"]
  },
  "embeddings_config": {
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "dimension": 384
  }
}
```

## Running Locally

```bash
# Install dependencies
pip install -r ../../requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/commloan_db
export JWT_SECRET_KEY=your-secret-key

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## Docker

```bash
# Build image
docker build -t commloan/admin-service .

# Run container
docker run -p 8002:8002 \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/commloan_db \
  -e JWT_SECRET_KEY=your-secret-key \
  commloan/admin-service
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

## Example Usage

### Create Feature Flag
```bash
curl -X POST http://localhost:8002/api/v1/admin/features \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "enable_new_feature",
    "description": "Enable new experimental feature",
    "enabled": true,
    "rollout_percentage": 50,
    "user_segments": ["beta_testers"]
  }'
```

### Update Feature Flag (Enable for all users)
```bash
curl -X PUT http://localhost:8002/api/v1/admin/features/{feature_id} \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": true,
    "rollout_percentage": 100
  }'
```

### Get Active RAG Configuration
```bash
curl -X GET http://localhost:8002/api/v1/admin/rag/config \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Check System Health
```bash
curl -X GET http://localhost:8002/api/v1/admin/health/services \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Testing

```bash
pytest tests/
```

## Environment Variables

See `../../.env.example` for all configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT verification
- `REDIS_URL` - Redis connection string

## Security

- **Admin only access** for most operations
- **Token authentication** required
- **Audit logging** for all configuration changes
- **Role-based access control** (RBAC)
- **Input validation** on all endpoints

## Monitoring

The admin service provides:
- Health checks for all microservices
- Database connectivity monitoring
- Cache (Redis) status monitoring
- System configuration overview
- Real-time service status

## Best Practices

### Feature Flags
1. **Start small**: Roll out to 10-20% of users first
2. **Monitor**: Watch metrics during rollout
3. **Have a kill switch**: Be ready to disable if issues arise
4. **Clean up**: Remove flags after full rollout

### RAG Configuration
1. **Test first**: Create and test before activating
2. **Version control**: Keep track of configuration changes
3. **Document**: Add descriptions explaining why settings changed
4. **Backup**: Keep previous working configurations

## Integration

Other services can check feature flags:

```python
import httpx

async def is_feature_enabled(feature_name: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://admin-service:8002/api/v1/admin/features/{feature_name}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            data = response.json()
            return data["enabled"]
        return False
```
