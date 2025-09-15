# Improved ECS Task Definition Registration Script
# This handles nulls and uses UTF-8 encoding

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ECS Task Definition Registration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if taskdef-new.json exists
if (!(Test-Path ".\taskdef-new.json")) {
    Write-Host "ERROR: taskdef-new.json not found!" -ForegroundColor Red
    Write-Host "Please create it first with your updated image" -ForegroundColor Yellow
    exit 1
}

# Load the edited taskdef (with your NEW image)
Write-Host "`nLoading task definition..." -ForegroundColor Yellow
$td = Get-Content .\taskdef-new.json | ConvertFrom-Json

# Keep only fields allowed by register-task-definition
# Remove nulls to avoid issues
$payload = [ordered]@{
    family = $td.family
}

# Add non-null fields only
if ($td.taskRoleArn) { $payload.taskRoleArn = $td.taskRoleArn }
if ($td.executionRoleArn) { $payload.executionRoleArn = $td.executionRoleArn }
if ($td.networkMode) { $payload.networkMode = $td.networkMode }
if ($td.containerDefinitions) { $payload.containerDefinitions = $td.containerDefinitions }
if ($td.volumes -and $td.volumes.Count -gt 0) { $payload.volumes = $td.volumes }
if ($td.placementConstraints -and $td.placementConstraints.Count -gt 0) { $payload.placementConstraints = $td.placementConstraints }
if ($td.requiresCompatibilities) { $payload.requiresCompatibilities = $td.requiresCompatibilities }
if ($td.cpu) { $payload.cpu = $td.cpu }
if ($td.memory) { $payload.memory = $td.memory }
if ($td.pidMode) { $payload.pidMode = $td.pidMode }
if ($td.ipcMode) { $payload.ipcMode = $td.ipcMode }
if ($td.proxyConfiguration) { $payload.proxyConfiguration = $td.proxyConfiguration }
if ($td.inferenceAccelerators -and $td.inferenceAccelerators.Count -gt 0) { $payload.inferenceAccelerators = $td.inferenceAccelerators }
if ($td.ephemeralStorage) { $payload.ephemeralStorage = $td.ephemeralStorage }
if ($td.runtimePlatform) { $payload.runtimePlatform = $td.runtimePlatform }

# Show what image we're deploying
$imageName = $payload.containerDefinitions[0].image
Write-Host "`nDeploying image: $imageName" -ForegroundColor Green

# Write clean JSON with UTF-8 encoding (safer than ASCII)
Write-Host "`nWriting cleaned task definition..." -ForegroundColor Yellow
$payload | ConvertTo-Json -Depth 50 | Set-Content .\taskdef-min.json -Encoding UTF8

# Show the command we're about to run
Write-Host "`nRegistering new task definition revision..." -ForegroundColor Yellow

# Register new revision
try {
    $result = aws ecs register-task-definition --cli-input-json file://taskdef-min.json --region eu-north-1 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $resultObj = $result | ConvertFrom-Json
        $NEW_TD_ARN = $resultObj.taskDefinition.taskDefinitionArn
        $NEW_REVISION = $resultObj.taskDefinition.revision
        
        Write-Host "`n✅ SUCCESS!" -ForegroundColor Green
        Write-Host "New Task Definition ARN:" -ForegroundColor Cyan
        Write-Host $NEW_TD_ARN -ForegroundColor White
        Write-Host "`nRevision: $NEW_REVISION" -ForegroundColor Cyan
        
        # Save ARN for next step
        $NEW_TD_ARN | Set-Content .\new-taskdef-arn.txt
        
        Write-Host "`n========================================" -ForegroundColor Cyan
        Write-Host "NEXT STEP: Update your service" -ForegroundColor Yellow
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Run this command:" -ForegroundColor Yellow
        Write-Host "aws ecs update-service --cluster babyshield-cluster --service babyshield-backend --task-definition $($td.family):$NEW_REVISION --force-new-deployment --region eu-north-1" -ForegroundColor White
        
    } else {
        Write-Host "`n❌ ERROR registering task definition!" -ForegroundColor Red
        Write-Host $result -ForegroundColor Red
    }
} catch {
    Write-Host "`n❌ ERROR: $_" -ForegroundColor Red
}
