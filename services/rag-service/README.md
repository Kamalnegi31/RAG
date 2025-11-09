# RAG Service

Multi-LLM provider Retrieval-Augmented Generation service with advanced strategies.

## Features

- ✅ Multi-LLM provider support (OpenAI, Anthropic, AWS Bedrock, OpenRouter)
- ✅ Multi-query expansion for comprehensive retrieval
- ✅ Re-ranking with CrossEncoder for precision
- ✅ Hierarchical context expansion
- ✅ Streaming responses (SSE)
- ✅ Query session management
- ✅ Automatic fallback between providers
- ✅ Complete query logging
- ✅ Cost tracking

## API Endpoints

### Query Processing
- `POST /api/v1/rag/query` - Process RAG query
- `POST /api/v1/rag/query/stream` - Stream RAG query (SSE)
- `GET /api/v1/rag/session/{id}` - Get session queries
- `DELETE /api/v1/rag/session/{id}` - Delete session

### Configuration
- `GET /api/v1/rag/providers` - List available providers

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check

## RAG Strategies

### 1. Multi-Query Expansion
Expands user query into multiple variants for comprehensive retrieval:
```
Original: "What are loan requirements?"
Variants:
- "Credit score requirements for commercial loans"
- "Collateral requirements for business loans"
- "Documentation needed for loan application"
```

### 2. Re-Ranking
Two-stage retrieval:
1. Retrieve 50 chunks with vector search
2. Re-rank with CrossEncoder
3. Return top 5 most relevant

### 3. Hierarchical Retrieval
- Search precise chunks
- Expand to parent sections for context
- Retrieve full documents when needed

### 4. Provider Fallback
Automatic fallback:
1. Try default provider (OpenAI)
2. If fails, try Anthropic
3. If fails, try Bedrock
4. Return error if all fail

## LLM Providers

### OpenAI
```bash
export OPENAI_API_KEY=your-key
export OPENAI_MODEL=gpt-4-turbo-preview
```

### Anthropic
```bash
export ANTHROPIC_API_KEY=your-key
export ANTHROPIC_MODEL=claude-3-opus-20240229
```

### AWS Bedrock
```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

### OpenRouter
```bash
export OPENROUTER_API_KEY=your-key
export OPENROUTER_MODEL=anthropic/claude-3-opus
```

## Running Locally

```bash
# Install dependencies
pip install -r ../../requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/commloan_db
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your-key

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## Docker

```bash
# Build image
docker build -t commloan/rag-service .

# Run container
docker run -p 8003:8003 \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/commloan_db \
  -e OPENAI_API_KEY=your-key \
  commloan/rag-service
```

## Example Usage

### Basic Query
```bash
curl -X POST http://localhost:8003/api/v1/rag/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the requirements for a $500k commercial loan?",
    "llm_provider": "openai"
  }'
```

Response:
```json
{
  "response": "Based on our loan policies, a $500k commercial loan requires...",
  "confidence_score": 0.92,
  "source_chunks": [
    {
      "id": "chunk-uuid",
      "text": "Commercial loans over $250k require...",
      "file_name": "commercial_loan_policy_2024.pdf",
      "similarity": 0.94
    }
  ],
  "strategies_used": ["multi_query", "reranking", "hierarchical"],
  "session_id": "session-uuid",
  "llm_provider": "openai",
  "llm_model": "gpt-4-turbo-preview",
  "tokens_used": 1234,
  "response_time_ms": 2500
}
```

### Streaming Query
```bash
curl -X POST http://localhost:8003/api/v1/rag/query/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is DSCR and how is it calculated?",
    "llm_provider": "anthropic"
  }'
```

Returns Server-Sent Events stream.

### Specify Provider
```bash
curl -X POST http://localhost:8003/api/v1/rag/query \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain loan covenants",
    "llm_provider": "bedrock",
    "options": {
      "multi_query": true,
      "reranking": true,
      "initial_k": 30,
      "final_k": 5
    }
  }'
```

### Get Session History
```bash
curl -X GET http://localhost:8003/api/v1/rag/session/{session_id} \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Configuration

Configure RAG strategies via environment variables or Admin Service:

```bash
# Enable/disable strategies
RERANKING_ENABLED=true
MULTI_QUERY_ENABLED=true
HIERARCHICAL_RAG_ENABLED=true

# Strategy parameters
RERANKING_TOP_K=5
RERANKING_INITIAL_K=50
MULTI_QUERY_NUM_QUERIES=4
HIERARCHICAL_MAX_PARENT_LEVELS=2

# Embedding model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

## Performance

**Target Metrics:**
- Response time: < 2s (p95)
- Streaming first token: < 500ms
- Accuracy: > 90% confidence
- Availability: 99.9%

**Optimization:**
- Embedding caching with Redis
- Batch embedding generation
- Connection pooling
- Provider fallback

## Monitoring

Tracked metrics:
- Query count per provider
- Response times
- Token usage
- Costs per provider
- Success/error rates
- Confidence scores

## Security

- JWT authentication required
- User-specific query sessions
- Query logging for audit
- PII detection (optional)
- Rate limiting per user

## Troubleshooting

### No providers available
Check API keys are set correctly:
```bash
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY
```

### Low confidence scores
- Check document quality
- Verify embeddings are generated
- Try different strategies
- Increase initial_k parameter

### Slow responses
- Enable re-ranking (improves quality, slight speed cost)
- Reduce initial_k parameter
- Use faster LLM model
- Enable caching

## Integration

Other services can call the RAG Service:

```python
import httpx

async def query_rag(query: str, token: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://rag-service:8003/api/v1/rag/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": query}
        )
        data = response.json()
        return data["response"]
```

## Testing

```bash
pytest tests/
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc
