# Auth Service

JWT-based authentication and user management service for CommLoan RAG System.

## Features

- ✅ JWT token authentication (access + refresh tokens)
- ✅ User registration and management
- ✅ Role-based access control (RBAC)
- ✅ Password hashing with bcrypt
- ✅ Token verification
- ✅ Admin user management
- ✅ Password change functionality

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/logout` - Logout (client discards tokens)
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/verify` - Verify token validity
- `GET /api/v1/auth/me` - Get current user info

### User Management
- `POST /api/v1/auth/users` - Create new user (admin only)
- `GET /api/v1/auth/users` - List all users (admin only)
- `PUT /api/v1/auth/users/{user_id}` - Update user
- `POST /api/v1/auth/change-password` - Change password

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check

## User Roles

1. **super_admin** - Full system access
2. **admin** - User and configuration management
3. **loan_officer** - Loan processing and RAG queries
4. **compliance** - Compliance and audit access
5. **read_only** - Read-only access

## Default Credentials

```
Email: admin@commloan.com
Password: admin123
```

**⚠️ CHANGE THESE IN PRODUCTION!**

## Running Locally

```bash
# Install dependencies
pip install -r ../../requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/commloan_db
export JWT_SECRET_KEY=your-secret-key
export SECRET_KEY=your-secret-key

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Docker

```bash
# Build image
docker build -t commloan/auth-service .

# Run container
docker run -p 8001:8001 \
  -e DATABASE_URL=postgresql://user:pass@postgres:5432/commloan_db \
  -e JWT_SECRET_KEY=your-secret-key \
  commloan/auth-service
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Example Usage

### Login
```bash
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@commloan.com",
    "password": "admin123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Get Current User
```bash
curl -X GET http://localhost:8001/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create User (Admin Only)
```bash
curl -X POST http://localhost:8001/api/v1/auth/users \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "first_name": "John",
    "last_name": "Doe",
    "role": "loan_officer"
  }'
```

## Testing

```bash
pytest tests/
```

## Environment Variables

See `../../.env.example` for all configuration options.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET_KEY` - Secret for JWT signing
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: 30)
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration (default: 7)
- `CORS_ORIGINS` - Allowed CORS origins

## Security

- Passwords hashed with bcrypt (12 rounds)
- JWT tokens signed with HS256
- Token expiration enforced
- Inactive users cannot login
- Role hierarchy enforced
- HTTPS recommended for production
