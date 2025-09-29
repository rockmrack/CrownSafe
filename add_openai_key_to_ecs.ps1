# PowerShell script to add OPENAI_API_KEY to ECS task definition
# This will update your current task definition to include the OpenAI API key

$CLUSTER = "babyshield-cluster"
$SERVICE = "babyshield-backend-task-service-0l41s2a9"
$REGION = "eu-north-1"

Write-Host "🔑 Adding OPENAI_API_KEY to ECS Task Definition..." -ForegroundColor Green

# Get current task definition
Write-Host "📋 Getting current task definition..." -ForegroundColor Yellow
$currentTaskDef = aws ecs describe-task-definition --task-definition babyshield-backend --region $REGION | ConvertFrom-Json

if (-not $currentTaskDef) {
    Write-Host "❌ Failed to get task definition" -ForegroundColor Red
    exit 1
}

# Extract the container definition
$containerDef = $currentTaskDef.taskDefinition.containerDefinitions[0]
Write-Host "📦 Container: $($containerDef.name)" -ForegroundColor Cyan

# Get existing environment variables
$envVars = @()
if ($containerDef.environment) {
    $envVars = @($containerDef.environment)
}

# Check if OPENAI_API_KEY already exists
$hasOpenAI = $envVars | Where-Object { $_.name -eq "OPENAI_API_KEY" }
if ($hasOpenAI) {
    Write-Host "✅ OPENAI_API_KEY already exists in task definition" -ForegroundColor Green
    Write-Host "Current value: $($hasOpenAI.value)" -ForegroundColor Yellow
} else {
    Write-Host "❌ OPENAI_API_KEY missing from task definition" -ForegroundColor Red
}

# Prompt for OpenAI API key
$openaiKey = Read-Host "🔑 Enter your OpenAI API key (starts with sk-)"

if (-not $openaiKey -or -not $openaiKey.StartsWith("sk-")) {
    Write-Host "❌ Invalid OpenAI API key format" -ForegroundColor Red
    exit 1
}

# Add or update the OpenAI API key
if ($hasOpenAI) {
    # Update existing
    $envVars | ForEach-Object { 
        if ($_.name -eq "OPENAI_API_KEY") { 
            $_.value = $openaiKey 
        } 
    }
} else {
    # Add new
    $envVars += @{name="OPENAI_API_KEY"; value=$openaiKey}
}

# Create new task definition
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
$tempFile = "temp-task-def-openai.json"
$newTaskDef | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding UTF8

Write-Host "📝 Registering new task definition with OpenAI API key..." -ForegroundColor Yellow
$registerResult = aws ecs register-task-definition --cli-input-json file://$tempFile --region $REGION

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Task definition updated successfully!" -ForegroundColor Green
    
    Write-Host "🔄 Updating service to use new task definition..." -ForegroundColor Yellow
    aws ecs update-service --cluster $CLUSTER --service $SERVICE --force-new-deployment --region $REGION
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "🚀 Service deployment started!" -ForegroundColor Green
        Write-Host "⏱️  Wait 2-3 minutes then test:" -ForegroundColor Cyan
        Write-Host '   $Body = @{ scan_id="test"; user_query="Is this safe?" } | ConvertTo-Json' -ForegroundColor White
        Write-Host '   Invoke-RestMethod "https://babyshield.cureviax.ai/api/v1/chat/demo" -Method Post -Headers @{"Content-Type"="application/json"} -Body $Body' -ForegroundColor White
    } else {
        Write-Host "❌ Failed to update service" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Failed to register task definition" -ForegroundColor Red
}

# Cleanup
Remove-Item $tempFile -ErrorAction SilentlyContinue
