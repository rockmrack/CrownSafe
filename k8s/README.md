# Crown Safe Kubernetes Deployment Guide

This guide covers deploying Crown Safe API to Kubernetes (AKS, EKS, or GKE).

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x
- Azure Container Registry access

## Quick Start

### 1. Create Namespace and Configure Secrets

```bash
# Apply namespace and config
kubectl apply -f k8s/config.yaml

# Update secrets with actual values
kubectl edit secret crownsafe-secrets -n crownsafe
```

### 2. Configure Docker Registry Secret

```bash
# Create ACR secret for pulling images
kubectl create secret docker-registry acr-secret \
  --namespace=crownsafe \
  --docker-server=crownsaferegistry.azurecr.io \
  --docker-username=<ACR_USERNAME> \
  --docker-password=<ACR_PASSWORD>
```

### 3. Deploy Application

```bash
# Deploy API
kubectl apply -f k8s/deployment.yaml

# Verify deployment
kubectl get pods -n crownsafe
kubectl get svc -n crownsafe
```

## Configuration

### Environment Variables

Edit `k8s/config.yaml` to configure:

- `ENVIRONMENT`: `production`, `staging`, or `development`
- `LOG_LEVEL`: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `API_PORT`: API server port (default: 8001)
- `ALLOWED_ORIGINS`: CORS allowed origins

### Secrets Management

**Important**: Never commit real secrets to version control!

Update secrets using:

```bash
kubectl edit secret crownsafe-secrets -n crownsafe
```

Or create from files:

```bash
kubectl create secret generic crownsafe-secrets \
  --namespace=crownsafe \
  --from-literal=database-url="postgresql://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=azure-storage-connection-string="..." \
  --from-literal=secret-key="..."
```

### Resource Limits

Default resource allocation per pod:

- **Requests**: 500m CPU, 512Mi memory
- **Limits**: 2000m CPU, 2Gi memory

Adjust in `k8s/deployment.yaml` based on workload.

### Scaling Configuration

#### Horizontal Pod Autoscaler (HPA)

- **Min replicas**: 3
- **Max replicas**: 10
- **CPU target**: 70% utilization
- **Memory target**: 80% utilization

Scale manually:

```bash
kubectl scale deployment crownsafe-api -n crownsafe --replicas=5
```

## Monitoring

### Health Checks

- **Liveness probe**: `/health` (every 10s)
- **Readiness probe**: `/api/healthz` (every 5s)

### View Logs

```bash
# All pods
kubectl logs -f -l app=crownsafe-api -n crownsafe

# Specific pod
kubectl logs -f <pod-name> -n crownsafe

# Previous crashed pod
kubectl logs <pod-name> -n crownsafe --previous
```

### Pod Status

```bash
# List pods
kubectl get pods -n crownsafe

# Describe pod
kubectl describe pod <pod-name> -n crownsafe

# Get events
kubectl get events -n crownsafe --sort-by='.lastTimestamp'
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n crownsafe

# Check logs
kubectl logs <pod-name> -n crownsafe

# Check events
kubectl get events -n crownsafe
```

Common issues:
- **ImagePullBackOff**: Check ACR credentials
- **CrashLoopBackOff**: Check logs for application errors
- **Pending**: Check resource availability

### Database Connection Issues

```bash
# Test database connectivity from pod
kubectl exec -it <pod-name> -n crownsafe -- bash
python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"
```

### Service Not Accessible

```bash
# Check service
kubectl get svc crownsafe-api -n crownsafe

# Check endpoints
kubectl get endpoints crownsafe-api -n crownsafe

# Port forward for testing
kubectl port-forward svc/crownsafe-api 8001:80 -n crownsafe
```

## Rolling Updates

### Update Image

```bash
# Update deployment image
kubectl set image deployment/crownsafe-api \
  api=crownsaferegistry.azurecr.io/crownsafe-api:v2.0.0 \
  -n crownsafe

# Check rollout status
kubectl rollout status deployment/crownsafe-api -n crownsafe
```

### Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/crownsafe-api -n crownsafe

# Rollback to specific revision
kubectl rollout undo deployment/crownsafe-api --to-revision=2 -n crownsafe

# View rollout history
kubectl rollout history deployment/crownsafe-api -n crownsafe
```

## Backup and Disaster Recovery

### Database Backup

Run manual backup:

```bash
kubectl run backup-job --rm -it --restart=Never \
  --image=crownsaferegistry.azurecr.io/crownsafe-api:latest \
  --namespace=crownsafe \
  --env="DATABASE_URL=$DATABASE_URL" \
  -- python scripts/automated_backup.py
```

### Automated Backups

Backups run daily via CronJob (see CI/CD pipeline).

### Restore from Backup

```bash
# Download backup from Azure Blob Storage
az storage blob download \
  --container-name crownsafe-backups \
  --name backup_file.sql.gz \
  --file backup.sql.gz

# Restore to database
gunzip -c backup.sql.gz | psql $DATABASE_URL
```

## Security Best Practices

1. **Use Network Policies**: Restrict pod-to-pod communication
2. **Enable Pod Security Standards**: Use restricted pod security
3. **Rotate Secrets Regularly**: Update secrets at least quarterly
4. **Use RBAC**: Limit service account permissions
5. **Enable Audit Logging**: Track cluster access
6. **Scan Images**: Use vulnerability scanning tools

## Performance Tuning

### Connection Pooling

Adjust pool size based on load:

```yaml
env:
- name: DB_POOL_SIZE
  value: "20"
- name: DB_MAX_OVERFLOW
  value: "10"
```

### Redis Cache

Monitor cache performance:

```bash
kubectl exec -it <pod-name> -n crownsafe -- \
  curl http://localhost:8001/api/v1/monitoring/azure-cache-stats
```

### Load Testing

Run load tests against cluster:

```bash
# Port forward service
kubectl port-forward svc/crownsafe-api 8001:80 -n crownsafe

# Run load tests
python tests/performance/load_test.py
```

## Production Checklist

Before going to production:

- [ ] Secrets configured (not default values)
- [ ] Resource limits appropriate for workload
- [ ] HPA configured and tested
- [ ] Ingress TLS certificate configured
- [ ] Database backups automated
- [ ] Monitoring and alerting configured
- [ ] Log aggregation enabled
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Disaster recovery plan documented

## Support

- 📧 DevOps: devops@crownsafe.com
- 🛡️ Security: security@crownsafe.com
- 📚 Documentation: https://docs.crownsafe.com
