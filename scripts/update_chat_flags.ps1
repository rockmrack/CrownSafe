# PowerShell script to enable chat flags in ECS
# Run this to automatically update your ECS task definition

$CLUSTER = "babyshield-cluster"
$SERVICE = "babyshield-backend-task-service-0l41s2a9"
$REGION = "eu-north-1"

Write-Host "🚀 Enabling Chat Feature Flags in ECS..." -ForegroundColor Green

# Get current task definition
Write-Host "📋 Getting current task definition..." -ForegroundColor Yellow
$currentTaskDef = aws ecs describe-task-definition --task-definition babyshield-backend --region $REGION | ConvertFrom-Json

# Extract the container definition
$containerDef = $currentTaskDef.taskDefinition.containerDefinitions[0]

# Add/update environment variables
$envVars = @($containerDef.environment)
$envVars += @{name="BS_FEATURE_CHAT_ENABLED"; value="true"}
$envVars += @{name="BS_FEATURE_CHAT_ROLLOUT_PCT"; value="1.0"}

# Create new task definition JSON
$newTaskDef = @{
    family = $currentTaskDef.taskDefinition.family
    networkMode = $currentTaskDef.taskDefinition.networkMode
    requiresCompatibilities = $currentTaskDef.taskDefinition.requiresCompatibilities
    cpu = $currentTaskDef.taskDefinition.cpu
    memory = $currentTaskDef.taskDefinition.memory
    executionRoleArn = $currentTaskDef.taskDefinition.executionRoleArn
    taskRoleArn = $currentTaskDef.taskDefinition.taskRoleArn
    containerDefinitions = @(
        @{
            name = $containerDef.name
            image = $containerDef.image
            portMappings = $containerDef.portMappings
            essential = $containerDef.essential
            environment = $envVars
            logConfiguration = $containerDef.logConfiguration
        }
    )
}

# Save to temp file
$tempFile = "temp-task-def.json"
$newTaskDef | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding UTF8

Write-Host "📝 Registering new task definition with chat flags enabled..." -ForegroundColor Yellow
aws ecs register-task-definition --cli-input-json file://$tempFile --region $REGION

Write-Host "🔄 Updating service to use new task definition..." -ForegroundColor Yellow
aws ecs update-service --cluster $CLUSTER --service $SERVICE --force-new-deployment --region $REGION

Write-Host "✅ Chat flags should be enabled in ~2-3 minutes!" -ForegroundColor Green
Write-Host "🧪 Test again with:" -ForegroundColor Cyan
Write-Host "   Invoke-RestMethod -Uri `"https://babyshield.cureviax.ai/api/v1/chat/flags`"" -ForegroundColor White

# Cleanup
Remove-Item $tempFile -ErrorAction SilentlyContinue
