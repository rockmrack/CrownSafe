# Deploy pg_trgm Fix to Production
# This script deploys the image with the admin endpoint to enable pg_trgm

Write-Host "`n🚀 Deploying pg_trgm Fix to Production`n" -ForegroundColor Cyan

$IMAGE_TAG = "main-20251016-1520-b6d2fea"
$CLUSTER = "babyshield-cluster"
$SERVICE = "babyshield-backend-task-service-0l41s2a9"
$REGION = "eu-north-1"

Write-Host "📦 Image: $IMAGE_TAG" -ForegroundColor White
Write-Host "🎯 Cluster: $CLUSTER" -ForegroundColor White
Write-Host "🔧 Service: $SERVICE" -ForegroundColor White
Write-Host ""

# Step 1: Register new task definition
Write-Host "Step 1: Registering new task definition..." -ForegroundColor Yellow

$taskDefArn = aws ecs register-task-definition `
    --family babyshield-backend-task `
    --execution-role-arn arn:aws:iam::180703226577:role/ecsTaskExecutionRole `
    --task-role-arn arn:aws:iam::180703226577:role/BabyshieldECSTaskRole `
    --network-mode awsvpc `
    --requires-compatibilities FARGATE `
    --cpu 1024 `
    --memory 2048 `
    --container-definitions "[{
        \`"name\`": \`"babyshield-backend\`",
        \`"image\`": \`"180703226577.dkr.ecr.$REGION.amazonaws.com/babyshield-backend:$IMAGE_TAG\`",
        \`"essential\`": true,
        \`"portMappings\`": [{
            \`"containerPort\`": 8001,
            \`"protocol\`": \`"tcp\`"
        }],
        \`"environment\`": [
            {\`"name\`": \`"ENVIRONMENT\`", \`"value\`": \`"production\`"},
            {\`"name\`": \`"PORT\`", \`"value\`": \`"8001\`"}
        ],
        \`"secrets\`": [
            {\`"name\`": \`"DATABASE_URL\`", \`"valueFrom\`": \`"arn:aws:secretsmanager:$REGION:180703226577:secret:babyshield/database-url\`"},
            {\`"name\`": \`"SECRET_KEY\`", \`"valueFrom\`": \`"arn:aws:secretsmanager:$REGION:180703226577:secret:babyshield/secret-key\`"},
            {\`"name\`": \`"REDIS_URL\`", \`"valueFrom\`": \`"arn:aws:secretsmanager:$REGION:180703226577:secret:babyshield/redis-url\`"}
        ],
        \`"logConfiguration\`": {
            \`"logDriver\`": \`"awslogs\`",
            \`"options\`": {
                \`"awslogs-group\`": \`"/ecs/babyshield-backend\`",
                \`"awslogs-region\`": \`"$REGION\`",
                \`"awslogs-stream-prefix\`": \`"ecs\`"
            }
        },
        \`"healthCheck\`": {
            \`"command\`": [\`"CMD-SHELL\`", \`"curl -f http://localhost:8001/healthz || exit 1\`"],
            \`"interval\`": 30,
            \`"timeout\`": 5,
            \`"retries\`": 3,
            \`"startPeriod\`": 60
        }
    }]" `
    --region $REGION `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to register task definition" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Task definition registered: $taskDefArn" -ForegroundColor Green
Write-Host ""

# Step 2: Update service
Write-Host "Step 2: Updating ECS service..." -ForegroundColor Yellow

aws ecs update-service `
    --cluster $CLUSTER `
    --service $SERVICE `
    --task-definition $taskDefArn `
    --region $REGION `
    --force-new-deployment | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to update service" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Service update initiated" -ForegroundColor Green
Write-Host ""

# Step 3: Monitor deployment
Write-Host "Step 3: Monitoring deployment..." -ForegroundColor Yellow
Write-Host "(This may take 3-5 minutes)" -ForegroundColor Gray
Write-Host ""

$maxWaitTime = 600  # 10 minutes
$startTime = Get-Date
$deployed = $false

while (-not $deployed -and ((Get-Date) - $startTime).TotalSeconds -lt $maxWaitTime) {
    Start-Sleep -Seconds 10
    
    $deployments = aws ecs describe-services `
        --cluster $CLUSTER `
        --services $SERVICE `
        --region $REGION `
        --query 'services[0].deployments[*].[status,taskDefinition,desiredCount,runningCount]' `
        --output json | ConvertFrom-Json
    
    Write-Host "  Deployment status:" -ForegroundColor Cyan
    foreach ($deployment in $deployments) {
        $status = $deployment[0]
        $taskDef = $deployment[1] -replace '.*:', ''
        $desired = $deployment[2]
        $running = $deployment[3]
        
        $color = if ($status -eq "PRIMARY") { "Green" } else { "Yellow" }
        Write-Host "    [$status] Task :$taskDef - Running: $running/$desired" -ForegroundColor $color
    }
    
    # Check if PRIMARY deployment is stable
    $primary = $deployments | Where-Object { $_[0] -eq "PRIMARY" }
    if ($primary -and $primary[2] -eq $primary[3]) {
        $deployed = $true
        Write-Host ""
        Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
    }
    else {
        Write-Host "  Waiting for deployment to stabilize..." -ForegroundColor Gray
    }
}

if (-not $deployed) {
    Write-Host "⚠️  Deployment taking longer than expected. Check AWS Console." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "📦 Image: $IMAGE_TAG" -ForegroundColor White
Write-Host "🎯 Task Definition: $taskDefArn" -ForegroundColor White
Write-Host ""
Write-Host "🔍 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Run scripts\enable_pg_trgm_via_api.ps1 to enable the extension" -ForegroundColor White
Write-Host "  2. Test search endpoint" -ForegroundColor White
Write-Host "  3. Check CloudWatch logs (pg_trgm warning should disappear)" -ForegroundColor White
Write-Host ""
Write-Host "📚 Documentation: PG_TRGM_FIX_COMPLETE.md" -ForegroundColor White
Write-Host ""
