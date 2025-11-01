# CrownSafe Local Docker Testing Guide

## Current Setup Status

### ✅ What's Working
- CrownSafe API running at `http://localhost:8002`
- Health checks passing (`/healthz`, `/docs`)
- FastAPI uvicorn server running
- Container healthy and responsive

### ⚠️ Expected Warnings (Non-Critical)
- **Redis unavailable**: Cache disabled, falling back gracefully
- **SQLite database**: Using `/tmp/crownsafe_dev.db` instead of Postgres
- **Empty product table**: No hair products seeded yet

## Seeding Demo Product

### Step 1: Copy seed script to container
```powershell
docker cp scripts/seed_demo_product.py crownsafe-api:/app/seed_demo_product.py
```

### Step 2: Run seed script inside container
```powershell
docker exec crownsafe-api python /app/seed_demo_product.py
```

You should see:
```
✅ Database tables created/verified
✅ Inserted demo product: Moisture Repair Leave-In
   Barcode: 012345678905
   Crown Score: 82
```

### Step 3: Test barcode scan endpoint
```powershell
$body = @{
    user_id = 1
    barcode = "012345678905"
    scan_method = "manual"
} | ConvertTo-Json

Invoke-WebRequest -UseBasicParsing `
  -Uri "http://localhost:8002/api/v1/crown-safe/barcode/scan" `
  -Method POST `
  -Body $body `
  -ContentType "application/json" |
Select-Object -Expand Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

Expected response:
```json
{
  "crown_score": 82,
  "product_name": "Moisture Repair Leave-In",
  "brand": "Crown Labs",
  "category": "leave-in conditioner",
  "recommendations": [...],
  "scan_id": 1
}
```

## Testing Other Endpoints

### Get default hair profile
```powershell
Invoke-WebRequest -UseBasicParsing "http://localhost:8002/api/crown/profile/default" |
Select-Object -Expand Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Health check
```powershell
Invoke-WebRequest -UseBasicParsing "http://localhost:8002/healthz" |
Select-Object -Expand Content
```

### API documentation
Open in browser: `http://localhost:8002/docs`

## Next Steps for Production

### Azure Migration Checklist
- [ ] Set `DATABASE_URL` to Azure Postgres Flexible Server
- [ ] Set `REDIS_URL` to Azure Cache for Redis
- [ ] Configure Azure Blob Storage for product images
- [ ] Set up Azure Key Vault for secrets
- [ ] Enable Application Insights for monitoring
- [ ] Configure CORS for production domains
- [ ] Set up CI/CD pipeline to Azure Container Registry

### Environment Variables Needed
```bash
DATABASE_URL=postgresql://user:pass@azure-postgres.postgres.database.azure.com:5432/crownsafe
REDIS_URL=rediss://azure-redis.redis.cache.windows.net:6380?ssl_cert_reqs=required
AZURE_STORAGE_ACCOUNT_NAME=crownsafe
AZURE_STORAGE_ACCOUNT_KEY=...
```

## Troubleshooting

### Container not starting
```powershell
docker logs crownsafe-api
```

### Check running containers
```powershell
docker ps -a
```

### Restart container
```powershell
docker restart crownsafe-api
```

### Rebuild after code changes
```powershell
docker build -t crownsafe-api:latest .
docker stop crownsafe-api
docker rm crownsafe-api
docker run -d -p 8002:8001 --name crownsafe-api crownsafe-api:latest
```

### Access container shell
```powershell
docker exec -it crownsafe-api /bin/bash
```

### View logs in real-time
```powershell
docker logs -f crownsafe-api
```
