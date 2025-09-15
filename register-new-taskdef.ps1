# PowerShell script to register new task definition with api-v1-fixed image

Write-Host "Registering new task definition with api-v1-fixed image..." -ForegroundColor Green

# Get the current task definition
$taskDef = aws ecs describe-task-definition `
    --task-definition babyshield-backend-task `
    --region eu-north-1 `
    --output json | ConvertFrom-Json

# Update the image
$taskDef.taskDefinition.containerDefinitions[0].image = "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:api-v1-fixed"

# Remove fields that can't be in registration
$newTaskDef = @{
    family = $taskDef.taskDefinition.family
    taskRoleArn = $taskDef.taskDefinition.taskRoleArn
    executionRoleArn = $taskDef.taskDefinition.executionRoleArn
    networkMode = $taskDef.taskDefinition.networkMode
    containerDefinitions = $taskDef.taskDefinition.containerDefinitions
    requiresCompatibilities = $taskDef.taskDefinition.requiresCompatibilities
    cpu = $taskDef.taskDefinition.cpu
    memory = $taskDef.taskDefinition.memory
}

# Save to file
$newTaskDef | ConvertTo-Json -Depth 10 | Set-Content -Path "new-taskdef.json" -Encoding UTF8

# Register the new task definition
Write-Host "Registering new task definition..." -ForegroundColor Yellow
$result = aws ecs register-task-definition `
    --cli-input-json file://new-taskdef.json `
    --region eu-north-1 `
    --query "taskDefinition.taskDefinitionArn" `
    --output text

Write-Host "New task definition registered: $result" -ForegroundColor Green

# Update the service to use the new task definition
Write-Host "Updating service with new task definition..." -ForegroundColor Yellow
aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-bv5v69zq `
    --task-definition $result `
    --force-new-deployment `
    --region eu-north-1 `
    --query "service.serviceName" `
    --output text

Write-Host "Service updated! Deployment in progress..." -ForegroundColor Green
